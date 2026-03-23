# -*- coding: utf-8 -*-
import base64
import io
import logging
import re
import requests
import json
import uuid
from lxml import etree as lxml_etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, MissingError, ValidationError
from datetime import timedelta

_logger = logging.getLogger(__name__)


def _generate_id_ccp(self=None):
    """
    Genera un IdCCP válido según el formato del SAT para Carta Porte 3.1.

    Patrón requerido: CCC[5hex]-[4hex]-[4hex]-[4hex]-[12hex]
    Ejemplo:          CCC12345-abcd-1234-abcd-123456789012

    Se define a nivel de módulo (no como lambda) para que Odoo
    pueda serializarla correctamente en default de fields.Char.
    """
    raw = uuid.uuid4().hex  # 32 caracteres hex sin guiones
    return f"CCC{raw[0:5]}-{raw[5:9]}-{raw[9:13]}-{raw[13:17]}-{raw[17:29]}"


# Campos que SÍ se pueden escribir cuando cfdi_status == 'timbrado'.
# Todo lo demás queda bloqueado para proteger la integridad del CFDI sellado.
TIMBRADO_WRITABLE_FIELDS = {
    # Campos CFDI — el sistema los escribe internamente al timbrar/cancelar
    'cfdi_uuid', 'cfdi_xml', 'cfdi_xml_fname', 'cfdi_fecha',
    'cfdi_pac', 'cfdi_no_cert_sat', 'cfdi_status', 'cfdi_error_msg',
    # Estado del workflow (ej. cerrar viaje después del timbrado)
    'state', 'message_main_attachment_id',
    # Mensajería y actividades de Odoo (chatter, log notes, etc.)
    'message_ids', 'message_follower_ids', 'message_partner_ids',
    'activity_ids', 'activity_state', 'activity_user_id',
    'activity_type_id', 'activity_date_deadline',
    'activity_summary', 'activity_exception_decoration',
    # Bitácora GPS — siempre editable aunque el CFDI esté timbrado
    'tracking_event_ids',
}


class TmsWaybill(models.Model):
    """
    Modelo Maestro: Viaje / Carta Porte (SINGLE DOCUMENT FLOW).

    CONCEPTO: Fusiona Cotización + Operación + Carta Porte en un solo documento.

    WORKFLOW (8 Etapas Reales):
    1. Solicitud (draft)          → Cotización inicial / borrador
    2. En Pedido (en_pedido)      → Pedido confirmado por cliente
    3. Por Asignar (assigned)     → Confirmada, asignar vehículo/chofer
    4. Carta Porte (waybill)      → CP lista para timbrar
    5. En Trayecto (in_transit)   → Chofer en camino
    6. En Destino (arrived)       → Entregado
    7. Facturado (closed)         → Cerrado/Facturado
    8. Cancelado (cancel)         → Anulado
    9. Rechazado (rejected)       → Rechazado desde portal

    ARQUITECTURA HÍBRIDA:
    - Plan A: App Móvil reporta GPS (action_driver_report API)
    - Plan B: Operación Manual desde Odoo (botones action_*_manual)

    ARQUITECTURA SAAS: company_id obligatorio.
    """

    _name = 'tms.waybill'
    _description = 'Viaje / Carta Porte (Maestro)'
    # Herencia de mixins: mail.thread (chatter), mail.activity.mixin (actividades), portal.mixin (portal web)
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'date_created desc, id desc'

    # ============================================================
    # CAMPO CRÍTICO SAAS
    # ============================================================

    # Many2one: compañía propietaria del viaje
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        help='Compañía propietaria del viaje (CRÍTICO para multi-empresa)'
    )

    company_name = fields.Char(related='company_id.name', string="Nombre Empresa", store=True, readonly=True)

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True,
        store=True,
    )

    # 🚀 OPTIMIZACIÓN ODOO 19
    _main_search_idx = models.Index("(company_id, state, date_created)")
    _folio_idx = models.Index("(company_id, name)")

    # ============================================================
    # CONTROL DE WORKFLOW
    # ============================================================

    # Char: folio del viaje (secuencia automática)
    name = fields.Char(
        string='Folio',
        required=True,
        readonly=True,
        copy=False,
        default='Nuevo',
        tracking=True,
        help='Número de folio del viaje (VJ/0001, VJ/0002, etc.)'
    )

    # Selection: estado del viaje (8 etapas, agregado 'rejected' para portal)
    # group_expand: asegura que todas las columnas aparezcan en Kanban
    state = fields.Selection(
        string='Estado',
        selection=[
            ('cotizado', 'Cotizado'),
            ('aprobado', 'Aprobado'),
            ('waybill', 'Carta Porte Lista'),
            ('in_transit', 'En Trayecto'),
            ('arrived', 'En Destino'),
            ('closed', 'Facturado / Cerrado'),
            ('cancel', 'Cancelado'),
            ('rejected', 'Rechazado'),
        ],
        default='cotizado',
        required=True,
        tracking=True,
        group_expand='_expand_states',
        help='Estado actual del viaje en el workflow'
    )

    # Date: fecha de creación
    date_created = fields.Date(
        string='Fecha de Solicitud',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )

    # ============================================================
    # ACCIONES DE LIMPIEZA (CLEAR BUTTONS)
    # ============================================================
    # ACCIONES DE LIMPIEZA (TRIGGERS CLIENT-SIDE)
    # ============================================================
    # Se usan campos booleanos con onchange para limpiar datos
    # sin disparar el "Save" (validador) que provocan los botones type="object".

    # ============================================================
    # CARTA PORTE 3.1 - CAMPOS ESPECÍFICOS
    # ============================================================

    tms_id_ccp = fields.Char(
        string='IdCCP',
        copy=False,
        readonly=True,
        help='Identificador único del Complemento Carta Porte (especificación 3.1). '
             'Formato SAT: CCC[5hex]-[4hex]-[4hex]-[4hex]-[12hex]. '
             'Se genera automáticamente al momento de timbrar (no al crear el waybill), '
             'garantizando un IdCCP fresco y único por intento de timbrado.',
    )

    l10n_mx_edi_is_international = fields.Boolean(
        string='Transporte Internacional',
        help='Indica si el transporte es internacional.'
    )

    l10n_mx_edi_logistica_inversa = fields.Boolean(
        string='Logística Inversa',
        help='Marcar si el movimiento corresponde a logística inversa (Retorno de mercancía/envases).'
    )

    l10n_mx_edi_customs_regime_ids = fields.One2many(
        'tms.waybill.customs.regime',
        'waybill_id',
        string='Regímenes Aduaneros (CCP 3.1)',
        help='Hasta 10 regímenes aduaneros aplicables a este viaje.'
    )

    tms_gross_vehicle_weight = fields.Float(
        string='Peso Bruto Vehicular',
        compute='_compute_gross_weight',
        store=True,
        help='Peso total estimado (Vehículo + Remolques + Mercancía) para CCP 3.1.'
    )

    @api.depends('vehicle_id', 'trailer1_id', 'trailer2_id', 'line_ids.weight_kg')
    def _compute_gross_weight(self):
        """
        Calcula el Peso Bruto Vehicular (Suma de vehículo + remolques + carga).
        En CCP 3.1, este valor es requerido para el transporte federal.
        """
        for rec in self:
            total = 0.0
            if rec.vehicle_id:
                total += rec.vehicle_id.tms_gross_vehicle_weight
            if rec.trailer1_id:
                total += rec.trailer1_id.tms_gross_vehicle_weight
            if rec.trailer2_id:
                total += rec.trailer2_id.tms_gross_vehicle_weight
            
            # Sumar peso de las mercancías (convertido a ton si el campo está en kg)
            total_merchandise = sum(rec.line_ids.mapped('weight_kg')) / 1000.0
            rec.tms_gross_vehicle_weight = total + total_merchandise

    def action_generate_id_ccp(self):
        """
        (Re)genera el IdCCP con el formato oficial del SAT para Carta Porte 3.1.
        Útil para corregir registros con IdCCP vacío o en formato antiguo.
        """
        for rec in self:
            rec.tms_id_ccp = _generate_id_ccp()

    @api.constrains('tms_id_ccp')
    def _check_id_ccp_format(self):
        """
        Valida el formato del IdCCP según el patrón del SAT para Carta Porte 3.1:
        CCC[5hex]-[4hex]-[4hex]-[4hex]-[12hex]
        Ejemplo: CCC12345-abcd-1234-abcd-123456789012
        """
        regex = r'^CCC[a-fA-F0-9]{5}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
        for rec in self:
            if rec.tms_id_ccp and not re.match(regex, rec.tms_id_ccp, re.IGNORECASE):
                raise ValidationError(_(
                    "El IdCCP no cumple el formato requerido por el SAT: "
                    "CCC[5hex]-[4hex]-[4hex]-[4hex]-[12hex]. "
                    "Ejemplo: CCC12345-abcd-1234-abcd-123456789012"
                ))

    # ============================================================
    # CFDI — Campos post-timbrado (V2.2)
    # ============================================================
    cfdi_uuid = fields.Char(
        string='UUID CFDI',
        readonly=True,
        copy=False,
        help='Folio fiscal del CFDI timbrado por el SAT'
    )
    cfdi_xml = fields.Binary(
        string='XML Timbrado',
        readonly=True,
        copy=False,
        attachment=True,
        help='XML del CFDI con el Timbre Fiscal Digital'
    )
    cfdi_xml_fname = fields.Char(
        string='Nombre XML',
        readonly=True
    )
    cfdi_fecha = fields.Datetime(
        string='Fecha timbrado',
        readonly=True
    )
    cfdi_pac = fields.Char(
        string='PAC usado',
        readonly=True,
        help='Nombre del PAC que realizó el timbrado'
    )
    cfdi_no_cert_sat = fields.Char(
        string='No. Certificado SAT',
        readonly=True
    )
    cfdi_status = fields.Selection([
        ('none',      'Sin timbrar'),
        ('timbrado',  'Timbrado'),
        ('cancelado', 'Cancelado'),
        ('error',     'Error'),
    ], string='Estatus CFDI', default='none', readonly=True,
       tracking=True
    )
    cfdi_error_msg = fields.Text(
        string='Último error CFDI',
        readonly=True
    )

    # ============================================================
    # ACCIONES: Clear (Limpieza de Campos)
    # ============================================================

    def action_clear_facturacion(self):
        """ Limpia campos de Facturación """
        self.partner_invoice_id = False

    def action_clear_origen(self):
        """ Limpia campos de Origen """
        self.partner_origin_id = False
        self.origin_address = False
        self.origin_zip = False

    def action_clear_destino(self):
        """ Limpia campos de Destino """
        self.partner_dest_id = False
        self.dest_address = False
        self.dest_zip = False

    # ============================================================
    # CONFIGURACIÓN FISCAL (Carta Porte)
    # ============================================================

    # Selection: tipo de carta porte
    # Determina si es Ingreso (cobro) o Traslado (sin cobro)
    # Requerimiento: Si el campo cp_type no existe → crearlo
    cp_type = fields.Selection([
        ('ingreso','Ingreso (Flete Cobrado)'),
        ('traslado','Traslado (Sin Cobro)'),
    ], string="Tipo de Carta Porte", default='ingreso', tracking=True)

    # Mantener waybill_type por compatibilidad — cp_type es el campo principal CP 3.1
    waybill_type = fields.Selection(
        string='Tipo de Viaje',
        selection=[
            ('income', 'Ingreso (Flete Cobrado)'),
            ('transfer', 'Traslado (Sin Cobro)'),
        ],
        required=True,
        default='income',
        tracking=True,
        help='Tipo de operación: Ingreso (cobra flete) o Traslado (sin cobro)'
    )

    # ============================================================
    # PRIORIDAD Y COLOR KANBAN
    # ============================================================

    # Prioridad del viaje — Se muestra como estrellas en el kanban
    priority = fields.Selection(
        selection=[
            ('0', 'Normal'),
            ('1', 'Urgente'),
            ('2', 'Muy Urgente'),
            ('3', 'Crítico'),
        ],
        string='Prioridad',
        default='0',
        tracking=True,
        index=True,
        help='Nivel de urgencia del viaje. Se muestra como estrellas en el kanban.'
    )

    # Color kanban: entero 0-11 que Odoo mapea a colores de la paleta estándar.
    # Se asigna automáticamente según el estado con un compute.
    color = fields.Integer(
        string='Color Kanban',
        compute='_compute_kanban_color',
        store=True,
        help='Color de la banda lateral en el kanban, calculado desde el estado del viaje.'
    )

    # Mapa estado → color Odoo (paleta 0-11)
    # 0=sin color, 1=rojo, 2=naranja, 3=amarillo, 4=azul claro,
    # 5=morado, 6=salmon, 7=gris medio, 8=azul marino, 9=fucsia,
    # 10=verde, 11=morado oscuro
    _STATE_COLOR_MAP = {
        'cotizado': 0,      # gris
        'aprobado': 4,      # azul claro
        'waybill': 5,       # morado
        'in_transit': 10,   # verde
        'arrived': 10,      # verde (llegó)
        'closed': 7,        # gris medio (cerrado)
        'cancel': 1,        # rojo
        'rejected': 6,      # salmon
    }

    @api.depends('state')
    def _compute_kanban_color(self):
        """Asigna el color de la banda lateral del kanban según el estado del viaje."""
        for rec in self:
            rec.color = self._STATE_COLOR_MAP.get(rec.state, 0)


    # ============================================================
    # ACTORES: CLIENTE DE FACTURACIÓN (Quién Paga)
    # ============================================================

    # Many2one: cliente que paga    # Cliente Facturación
    partner_invoice_id = fields.Many2one(
        'res.partner', string='Cliente Facturación',
        domain="[('type', 'in', ['invoice', 'contact'])]",
        check_company=True,
        tracking=True,
        help='Cliente al que se le facturará el servicio'
    )

    # Char: RFC del cliente (relacionado, readonly)
    invoice_rfc = fields.Char(
        string='RFC Cliente',
        related='partner_invoice_id.vat',
        readonly=True,
        store=False,
    )

    # Char: domicilio fiscal del cliente (computado)
    invoice_address = fields.Char(
        string='Domicilio Fiscal',
        compute='_compute_partner_addresses',
        store=False,
    )

    # ============================================================
    # ACTORES: ORIGEN / REMITENTE (Quien Entrega)
    # ============================================================

    # Many2one: contacto en el origen
    partner_origin_id = fields.Many2one(
        'res.partner', string='Remitente (Origen)',
        domain="[('type', '!=', 'private')]",
        check_company=True,
        help='Contacto que entrega la mercancía'
    )

    # Char: RFC del remitente (relacionado, readonly)
    origin_rfc = fields.Char(
        string='RFC Remitente',
        related='partner_origin_id.vat',
        readonly=True,
        store=False,
    )

    # Many2one: municipio origen (catálogo SAT)
    origin_city_id = fields.Many2one(
        'tms.sat.municipio',
        string='Municipio Origen',
        help='Municipio de origen según catálogo SAT'
    )

    # Char: código postal origen
    origin_zip = fields.Char(
        string='CP Origen',
        size=5,
    )

    origin_city_name = fields.Char(
        string='Ciudad Origen',
        compute='_compute_city_names',
        store=False,
    )

    # Char: dirección origen (calle y número)
    origin_address = fields.Char(
        string='Dirección Origen',
        help='Calle y número de la dirección de origen'
    )

    # ============================================================
    # ACTORES: DESTINO / DESTINATARIO (Quien Recibe)
    # ============================================================

    # Many2one: contacto en el destino
    partner_dest_id = fields.Many2one(
        'res.partner', string='Destinatario',
        domain="[('type', '!=', 'private')]",
        check_company=True,
        help='Contacto que recibe la mercancía'
    )

    # Char: RFC del destinatario (relacionado, readonly)
    dest_rfc = fields.Char(
        string='RFC Destinatario',
        related='partner_dest_id.vat',
        readonly=True,
        store=False,
    )

    # Many2one: municipio destino (catálogo SAT)
    dest_city_id = fields.Many2one(
        'tms.sat.municipio',
        string='Municipio Destino',
        help='Municipio de destino según catálogo SAT'
    )

    # Char: código postal destino
    dest_zip = fields.Char(
        string='CP Destino',
        size=5,
    )

    dest_city_name = fields.Char(
        string='Ciudad Destino',
        compute='_compute_city_names',
        store=False,
    )

    # Char: dirección destino (calle y número)
    dest_address = fields.Char(
        string='Dirección Destino',
        help='Calle y número de la dirección de destino'
    )

    # ============================================================
    # RUTA: DATOS DE DISTANCIA Y DURACIÓN
    # ============================================================

    # Float: distancia en kilómetros (base de la ruta)
    distance_km = fields.Float(
        string='Distancia (Km)',
        digits=(10, 2),
        help='Distancia base en kilómetros de la ruta'
    )

    # Float: kilómetros extras por desvíos o periferia
    # Se suma a distance_km para el cálculo de la propuesta por KM
    extra_distance_km = fields.Float(
        string='Km Extras / Desvío',
        digits=(10, 2),
        default=0.0,
        help='Kilómetros adicionales al centro de la ciudad o por desvíos operativos. Se suman a la distancia base para el cobro.'
    )

    # Float: duración estimada en horas
    duration_hours = fields.Float(
        string='Duración Estimada (Hrs)',
        digits=(10, 2),
        help='Duración estimada del viaje en horas'
    )

    # Char: ruta completa (computado)
    # Formato: "Monterrey → CDMX"
    route_name = fields.Char(
        string='Ruta',
        compute='_compute_route_name',
        store=True,
        help='Ruta en formato: Origen → Destino'
    )

    # Many2one: ruta frecuente seleccionada
    # Al seleccionar una ruta, se auto-llenan origen, destino, distancia y duración
    route_id = fields.Many2one(
        'tms.destination',
        string='Seleccionar Ruta Frecuente',
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        check_company=True,
        tracking=True,
        help='Selecciona una ruta frecuente para auto-completar origen, destino, distancia y duración'
    )

    # ============================================================
    # SELECTOR INTELIGENTE DE RUTAS
    # ============================================================


    @api.constrains('partner_origin_id', 'partner_dest_id', 'state')
    def _check_fiscal_rfc(self):
        """ Valida RFC en partners (Solo en estados cotizado/aprobado no aplica) """
        for record in self:
             if record.state in ['cotizado', 'aprobado', 'cancel', 'rejected']:
                 continue
             if record.partner_origin_id and not record.partner_origin_id.vat:
                raise ValidationError(_("El Remitente seleccionado no tiene RFC configurado."))
             if record.partner_dest_id and not record.partner_dest_id.vat:
                raise ValidationError(_("El Destinatario seleccionado no tiene RFC configurado."))





    @api.constrains('amount_total', 'state')
    def _check_financials(self):
        """ Valida precio final (Solo aplica desde waybill en adelante) """
        for record in self:
            if record.state in ['cotizado', 'aprobado', 'cancel', 'rejected']:
                 continue
            if record.amount_total <= 0:
                raise ValidationError(_("El Precio Final (Total) debe ser mayor a $0.00."))

    @api.onchange('route_id')
    def _onchange_route_id(self):
        """
        Legacy: Si se usa el selector de ruta (aunque está oculto), intentar llenar datos básicos.
        """
        if self.route_id:
            self.route_name = self.route_id.name
            self.distance_km = self.route_id.distance_km
            self.duration_hours = self.route_id.duration_hours
            self.cost_tolls = self.route_id.cost_tolls
        else:
            self.distance_km = 0.0
            self.duration_hours = 0.0
            self.cost_tolls = 0.0

    @api.depends('partner_origin_id', 'partner_dest_id', 'origin_zip', 'dest_zip')
    def _compute_route_name(self):
        """
        Calcula el nombre de la ruta.
        Formato: "Ciudad Origen → Ciudad Destino"
        Fallback: busca ciudad por CP si no hay partner/city.
        """
        for record in self:
            origin = (record.partner_origin_id.city
                      or record.partner_origin_id.name
                      or record._get_city_from_zip(record.origin_zip)
                      or record.origin_zip
                      or "?")
            dest = (record.partner_dest_id.city
                    or record.partner_dest_id.name
                    or record._get_city_from_zip(record.dest_zip)
                    or record.dest_zip
                    or "?")
            record.route_name = f"{origin} → {dest}"

    # ============================================================
    # CONFIGURACIÓN OPERATIVA: VEHÍCULOS Y CHOFER
    # ============================================================

    # Many2one: vehículo asignado (tractor)
    # Many2one: vehículo asignado (tractor)
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo (Tractor)',
        domain="[('tms_is_trailer', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        tracking=True,
        help='Tractocamión asignado al viaje'
    )

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        """
        Al seleccionar vehículo, traer su rendimiento.
        """
        if self.vehicle_id:
            self.fuel_performance = self.vehicle_id.tms_fuel_performance

    # Many2one: chofer asignado (Empleados)
    driver_id = fields.Many2one(
        'hr.employee',
        string='Chofer',
        domain="[('tms_is_driver', '=', True)]",  # Solo empleados marcados como Chofer
        check_company=True,
        tracking=True,
        help='Conductor asignado al viaje (debe estar registrado como Empleado y ser Chofer)'
    )

    # Boolean: Indica si el viaje REQUIERE remolque forzosamente
    # Si es True, no se permite avanzar a Carta Porte sin trailer1_id
    require_trailer = fields.Boolean(
        string='Lleva Remolque',
        default=False,
        help='Si se marca, es obligatorio asignar un remolque antes de generar la Carta Porte.'
    )

    @api.onchange('require_trailer')
    def _onchange_require_trailer(self):
        """
        Si se desmarca 'Lleva Remolque', se limpian todos los campos de remolque
        y se fuerza el recálculo de ejes en la interfaz.
        """
        if not self.require_trailer:
            self.update({
                'trailer1_id': False,
                'dolly_id': False,
                'trailer2_id': False,
            })
            self._compute_total_axles()

    # Many2one: remolque 1
    trailer1_id = fields.Many2one(
        'fleet.vehicle',
        string='Remolque 1',
        domain="[('tms_is_trailer', '=', True), ('company_id', '=', company_id)]",
        check_company=True,
        help='Primer remolque asignado'
    )

    dolly_id = fields.Many2one(
        'fleet.vehicle',
        string='Dolly',
        domain="[('tms_is_trailer', '=', True), ('company_id', '=', company_id)]",
        check_company=True,
        tracking=True,
        help='Dolly: unidad de arrastre que conecta Remolque 1 y Remolque 2',
    )

    # Many2one: remolque 2 (opcional)
    trailer2_id = fields.Many2one(
        'fleet.vehicle',
        string='Remolque 2',
        domain="[('tms_is_trailer', '=', True), ('company_id', '=', company_id)]",
        check_company=True,
        help='Segundo remolque asignado (opcional)'
    )

    # Integer: Total de ejes (Tractor + Remolques)
    # Importante para el cálculo de costos de casetas (Google Maps API)
    total_axles = fields.Integer(
        string='Total Ejes',
        compute='_compute_total_axles',
        store=True,
        help='Suma de ejes del Tractor + Remolque 1 + Remolque 2'
    )

    @api.depends('require_trailer',
                 'vehicle_id.tms_num_axles',
                 'trailer1_id.tms_num_axles',
                 'dolly_id.tms_num_axles',
                 'trailer2_id.tms_num_axles')
    def _compute_total_axles(self):
        """
        Calcula el total de ejes del viaje sumando el tracto y,
        si 'Lleva Remolque' está activo, sus componentes de arrastre.
        """
        for record in self:
            # Primero obtenemos los ejes del tractor (base siempre presente)
            total = record.vehicle_id.tms_num_axles if record.vehicle_id else 0
            
            # Solo se suman remolques si el toggle está activo. 
            # Si está inactivo, ignoramos cualquier valor remanente en los campos.
            if record.require_trailer:
                if record.trailer1_id:
                    total += record.trailer1_id.tms_num_axles or 0
                if record.dolly_id:
                    total += record.dolly_id.tms_num_axles or 0
                if record.trailer2_id:
                    total += record.trailer2_id.tms_num_axles or 0
            
            record.total_axles = total

    # ============================================================
    # BITÁCORA DE TIEMPOS Y GPS (HÍBRIDO: App + Manual)
    # ============================================================
    # IMPORTANTE: Estos campos se llenan automáticamente por la App (Plan A)
    # o manualmente por botones de Odoo (Plan B)

    # ===== PUNTO 1: LLEGADA A ORIGEN =====

    # Datetime: fecha/hora de llegada al punto de origen
    date_arrived_origin = fields.Datetime(
        string='Llegada a Origen',
        help='Fecha y hora en que llegó al punto de carga'
    )

    # Float: latitud GPS de llegada a origen
    lat_arrived_origin = fields.Float(
        string='Latitud Origen',
        digits=(12, 8),
        help='Latitud GPS al llegar a origen (App) o 0.0 (Manual)'
    )

    # Float: longitud GPS de llegada a origen
    long_arrived_origin = fields.Float(
        string='Longitud Origen',
        digits=(12, 8),
        help='Longitud GPS al llegar a origen (App) o 0.0 (Manual)'
    )

    # ===== PUNTO 2: INICIO DE RUTA =====

    # Datetime: fecha/hora de inicio de ruta
    date_started_route = fields.Datetime(
        string='Inicio de Ruta',
        help='Fecha y hora en que inició el trayecto'
    )

    # Float: latitud GPS de inicio de ruta
    lat_started_route = fields.Float(
        string='Latitud Inicio',
        digits=(12, 8),
        help='Latitud GPS al iniciar ruta (App) o 0.0 (Manual)'
    )

    # Float: longitud GPS de inicio de ruta
    long_started_route = fields.Float(
        string='Longitud Inicio',
        digits=(12, 8),
        help='Longitud GPS al iniciar ruta (App) o 0.0 (Manual)'
    )

    # ===== PUNTO 3: LLEGADA A DESTINO =====

    # Datetime: fecha/hora de llegada a destino
    date_arrived_dest = fields.Datetime(
        string='Llegada a Destino',
        help='Fecha y hora en que llegó al punto de entrega'
    )

    # Float: latitud GPS de llegada a destino
    lat_arrived_dest = fields.Float(
        string='Latitud Destino',
        digits=(12, 8),
        help='Latitud GPS al llegar a destino (App) o 0.0 (Manual)'
    )

    # Float: longitud GPS de llegada a destino
    long_arrived_dest = fields.Float(
        string='Longitud Destino',
        digits=(12, 8),
        help='Longitud GPS al llegar a destino (App) o 0.0 (Manual)'
    )

    # ===== TRACKING EN TIEMPO REAL (Solo App) =====

    # Float: última latitud reportada por la app
    last_app_lat = fields.Float(
        string='Última Latitud (App)',
        digits=(12, 8),
        help='Última posición GPS reportada por la app móvil'
    )

    # Float: última longitud reportada por la app
    last_app_long = fields.Float(
        string='Última Longitud (App)',
        digits=(12, 8),
        help='Última posición GPS reportada por la app móvil'
    )

    # Datetime: última actualización de posición
    last_report_date = fields.Datetime(
        string='Última Actualización GPS',
        help='Última vez que la app reportó posición'
    )

    # ============================================================
    # MONTOS Y COSTOS
    # ============================================================

    # Monetary: valor del viaje (monto a cobrar)
    amount_total = fields.Monetary(
        string='Total',
        currency_field='currency_id',
        tracking=True,
        compute='_compute_amount_all',
        store=True,
        help='Monto total a cobrar (Subtotal + Impuestos - Retenciones)'
    )

    amount_untaxed = fields.Monetary(
        string='Subtotal',
        currency_field='currency_id',
        store=True,
        tracking=True,
        help='Base imponible antes de impuestos'
    )

    amount_tax = fields.Monetary(
        string='IVA (16%)',
        currency_field='currency_id',
        store=True,
        compute='_compute_amount_all',
        help='Impuesto al Valor Agregado (16%)'
    )

    amount_retention = fields.Monetary(
        string='Retención (4%)',
        currency_field='currency_id',
        store=True,
        compute='_compute_amount_all',
        help='Retención de IVA (4%)'
    )

    # ==========================================
    # API EXTERNA: CÁLCULO DE RUTA (GOOGLE ROUTES API + CACHÉ)
    # ==========================================
    def action_compute_route_smart(self):
        """
        Método inteligente:
        1. Busca en caché (tms.destination) por CP Origen + CP Destino + Tipo Vehículo.
        2. Si encuentra y es reciente (< 6 meses), usa eso.
        3. Si no, llama a Google Maps Routes API (con Peajes).
        4. Guarda/Actualiza el resultado en tms.destination.
        """
        self.ensure_one()

        # Validar datos mínimos
        if not self.partner_origin_id.zip or not self.partner_dest_id.zip:
            raise UserError(_("Los contactos de Origen y Destino deben tener Código Postal para calcular la ruta."))

        origin_zip = self.partner_origin_id.zip
        dest_zip = self.partner_dest_id.zip
        vehicle_type = self.vehicle_id.tms_vehicle_type_id

        # 1. BUSCAR EN CACHÉ
        cached_route = self.env['tms.destination'].search([
            ('company_id', '=', self.company_id.id),
            ('origin_zip', '=', origin_zip),
            ('dest_zip', '=', dest_zip),
            ('vehicle_type_id', '=', vehicle_type.id if vehicle_type else False)
        ], limit=1)

        # Si existe y es válida (ej. < 6 meses), usarla
        # TODO: Agregar chequeo de fecha si se desea forzar expiración aquí,
        # pero el usuario pidió un cron separado para re-calcular las viejas.
        # Por ahora, si existe, la usamos.
        if cached_route:
             self.write({
                'distance_km': cached_route.distance_km,
                'duration_hours': cached_route.duration_hours,
                'cost_tolls': cached_route.cost_tolls, # Costo de casetas guardado
                'extra_distance_km': 0.0,
            })
             return self._notify_success("Datos obtenidos de Caché interno.", cached_route.distance_km, cached_route.duration_hours, cached_route.cost_tolls)

        # 2. SELECCIONAR PROVEEDOR
        ICPSudo = self.env['ir.config_parameter'].sudo()
        provider = ICPSudo.get_param('tms.route_provider', 'std')

        _logger.info(f"TMS Route Calc: Provider selected = {provider}")
        _logger.info(f"TMS Route Calc: Origin={origin_zip}, Dest={dest_zip}, VehicleType={vehicle_type.name if vehicle_type else 'None'}, TotalAxles={self.total_axles}")

        if provider == 'google':
             return self._fetch_google_routes_api(origin_zip, dest_zip, vehicle_type)
        elif provider == 'tollguru':
             return self._fetch_tollguru_api()

        else:
             # Standard handling or legacy Google Maps fallback if desired (but now we have specific provider)
             raise UserError(_("Seleccione un proveedor de rutas válido en Ajustes (Google o TollGuru). Valor actual: %s") % provider)

    def _fetch_google_routes_api(self, origin_zip, dest_zip, vehicle_type):
        """Consumo directo de Routes API (v1:computeRoutes) para Distancia, Tiempo y PEAJES"""
        ICPSudo = self.env['ir.config_parameter'].sudo()
        api_key = ICPSudo.get_param('tms.google_maps_api_key')

        if not api_key:
            raise UserError(_("Falta API Key de Google Maps en Ajustes."))

        # Endpoint Routes API (POST)
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"

        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters,routes.travelAdvisory.tollInfo'
        }

        # Body del request
        # Usamos CP, País para origen/destino
        payload = {
            "origin": {"address": f"postal code {origin_zip}, Mexico"},
            "destination": {"address": f"postal code {dest_zip}, Mexico"},
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
            "extraComputations": ["TOLLS"],
            "routeModifiers": {
                "vehicleInfo": {
                    "emissionType": "DIESEL"
                }
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            data = response.json()
        except Exception as e:
            raise UserError(_("Error de conexión: %s") % str(e))

        if 'error' in data:
            raise UserError(_("Google API Error: %s") % data['error'].get('message'))

        if not data.get('routes'):
            raise UserError(_("Google no encontró ruta entre %s y %s") % (origin_zip, dest_zip))

        route = data['routes'][0]

        # Extraer datos
        distance_meters = route.get('distanceMeters', 0)
        distance_km = distance_meters / 1000.0

        duration_seconds = int(route.get('duration', '0s').replace('s', ''))
        duration_hours = duration_seconds / 3600.0

        # Peajes (Tolls)
        toll_cost = 0.0
        if route.get('travelAdvisory') and route.get('travelAdvisory').get('tollInfo'):
            toll_info = route['travelAdvisory']['tollInfo']
            # Google puede devolver múltiples monedas, asumimos MXN o convertimos si es necesario?
            # Normalmente devuelve la moneda local del trayecto.
            # Estimación de precio es 'estimatedPrice'.
            for price in toll_info.get('estimatedPrice', []):
                # Sumar si es MXN, o convertir. Simplificamos asumiendo MXN para Mexico.
                if price.get('currencyCode') == 'MXN':
                     toll_cost += float(price.get('units', 0)) + (price.get('nanos', 0) / 1e9)

        # 3. GUARDAR EN CACHÉ (tms.destination)
        self.env['tms.destination'].create({
            'company_id': self.company_id.id,
            'origin_zip': origin_zip,
            'dest_zip': dest_zip,
            'vehicle_type_id': vehicle_type.id if vehicle_type else False,
            'distance_km': distance_km,
            'duration_hours': duration_hours,
            'cost_tolls': toll_cost,
            'last_update': fields.Date.today()
        })

        # 4. ACTUALIZAR WAYBILL
        self.write({
            'distance_km': distance_km,
            'duration_hours': duration_hours,
            'cost_tolls': toll_cost,
            'extra_distance_km': 0.0,
        })

        return self._notify_success("Calculado vía Google API (y guardado)", distance_km, duration_hours, toll_cost)





    def _notify_success(self, source, dist, dur, tolls):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tms.waybill',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'effect': {
                'fadeout': 'slow',
                'message': _('%s\nRuta Actualizada: %.2f km, %.2f hrs, $%s') % (source, dist, dur, tolls),
                'type': 'rainbow_man',
            }
        }

    # ============================================================
    # FIRMA DIGITAL (PORTAL WEB)
    # ============================================================

    # Binary: imagen de la firma del cliente (base64)
    # Se guarda cuando el cliente firma la cotización en el portal
    signature = fields.Image(
        string='Firma Digital',
        copy=False,
        attachment=True,
        help='Firma digital del cliente capturada en el portal web'
    )

    # Char: nombre de la persona que firmó
    # Se captura junto con la firma para identificación
    signed_by = fields.Char(
        string='Firmado Por',
        help='Nombre de la persona que firmó la cotización digitalmente'
    )

    # Datetime: fecha y hora en que se firmó
    # Se establece automáticamente cuando se ejecuta _action_sign()
    signed_on = fields.Datetime(
        string='Fecha de Firma',
        copy=False,
        help='Fecha y hora en que el cliente firmó la cotización'
    )

    # IP y Geolocalización de la firma (Portal)
    signed_ip = fields.Char(string='IP de Firma', copy=False, help='Dirección IP desde donde se firmó')
    signed_latitude = fields.Float(string='Latitud Firma', digits=(10, 7), copy=False)
    signed_longitude = fields.Float(string='Longitud Firma', digits=(10, 7), copy=False)

    # ============================================================
    # TRACKING (Bitácora de Eventos)
    # ============================================================
    tracking_event_ids = fields.One2many(
        'tms.tracking.event',
        'waybill_id',
        string='Bitácora de Eventos'
    )

    # Contador de eventos GPS para el smart button
    tracking_count = fields.Integer(
        string='Eventos GPS',
        compute='_compute_tracking_count',
        store=False,
        help='Número de eventos de rastreo registrados en este viaje'
    )

    @api.depends('tracking_event_ids')
    def _compute_tracking_count(self):
        """Cuenta los eventos GPS para mostrar en el smart button."""
        for rec in self:
            rec.tracking_count = len(rec.tracking_event_ids)

    # Text: motivo de rechazo desde el portal
    # Se captura cuando el cliente rechaza la cotización desde el portal
    rejection_reason = fields.Text(
        string='Motivo de Rechazo',
        copy=False,
        help='Motivo del rechazo capturado desde el portal web'
    )

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Cotizacion-%s' % (self.name)

    def action_preview_waybill(self):
        """Abre la cotización en el portal en una NUEVA pestaña"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',  # <--- 'new' fuerza la nueva pestaña
            'url': self.get_portal_url(),
        }

    def action_approve_quotation(self):
        """Transición cotizado → aprobado. El cliente aceptó el precio."""
        self.ensure_one()
        if self.state != 'cotizado':
            raise UserError(_("Solo se pueden aprobar viajes en estado Cotizado."))
        self.write({'state': 'aprobado'})
        return True

    def _validate_before_confirm(self):
        """
        Valida que el waybill tenga todos los datos mínimos operativos
        antes de confirmar el pedido (transición aprobado → draft → en_pedido).

        Agrupa todos los errores y los muestra juntos para que el usuario
        pueda corregirlos todos de una vez, en lugar de un error por vez.

        NOTA: Los siguientes campos del task NO existen aún y se omiten:
          - fecha_embarque (no definido en el modelo — agregar en V2.2)
          - vehicle_status == 'blocked' (semilla V2.5 — fleet.vehicle)
        """
        errors = []

        # ── GRUPO 1: RUTA ──────────────────────────────────────────────
        if not self.partner_origin_id:
            errors.append("• Remitente (origen del viaje)")
        if not self.partner_dest_id:
            errors.append("• Destinatario")
        if not self.origin_zip:
            errors.append("• Código Postal de origen")
        if not self.dest_zip:
            errors.append("• Código Postal de destino")

        # ── GRUPO 2: VEHÍCULO Y CHOFER ──────────────────────────────────
        if not self.vehicle_id:
            errors.append("• Vehículo (tracto) asignado")
        if not self.driver_id:
            errors.append("• Chofer asignado")

        # ── GRUPO 3: MERCANCÍAS ─────────────────────────────────────────
        if not self.line_ids:
            errors.append("• Al menos una línea de mercancía")
        else:
            for i, line in enumerate(self.line_ids, 1):
                ref = line.description or f'Línea #{i}'
                if not line.description:
                    errors.append(f"• Mercancía #{i}: falta la descripción")
                if not line.quantity or line.quantity <= 0:
                    errors.append(f"• Mercancía #{i} ({ref}): falta la cantidad")
                if not line.weight_kg or line.weight_kg <= 0:
                    errors.append(f"• Mercancía #{i} ({ref}): falta el peso (kg)")
                # product_sat_id = clave SAT del producto (requerida para Carta Porte)
                if not line.product_sat_id:
                    errors.append(
                        f"• Mercancía #{i} ({ref}): falta la Clave SAT del producto"
                    )
                # Dimensiones obligatorias para Carta Porte 3.1
                if line.dim_largo <= 0 or line.dim_ancho <= 0 or line.dim_alto <= 0:
                    errors.append(
                        f"• Mercancía #{i} ({ref}): "
                        f"faltan dimensiones (Largo, Ancho y Alto en cm)"
                    )

        if errors:
            raise UserError(
                _("Para confirmar el pedido, completa los siguientes campos:\n\n")
                + "\n".join(errors)
            )

    def action_confirm_order(self):
        """Transición aprobado → waybill. Delega a action_approve_cp para validación CP 3.1."""
        self.ensure_one()
        if self.state != 'aprobado':
            raise UserError(_("Solo se pueden confirmar viajes en estado Aprobado."))
        return self.action_approve_cp()


    # ============================================================
    # MOTOR DE COTIZACIÓN (Costos y Propuestas)
    # ============================================================

    def _get_default_fuel_price(self):
        """Obtiene el último precio de diesel registrado"""
        last_price = self.env['tms.fuel.history'].search([], limit=1, order='date desc, id desc')
        return last_price.price if last_price else 24.00

    # --- INPUTS DE COSTOS ---
    fuel_price_liter = fields.Float(string='Precio Diesel (L)', default=_get_default_fuel_price, digits=(10,2))

    is_fuel_price_outdated = fields.Boolean(
        string='Precio Diesel Desactualizado',
        compute='_compute_is_fuel_price_outdated',
        help='Indica si el último precio registrado tiene más de una semana.'
    )

    @api.depends('fuel_price_liter', 'company_id')
    def _compute_is_fuel_price_outdated(self):
        """
        Valida si el último precio de diesel tiene más de 7 días.
        También marca como desactualizado si NO existe historial.
        """
        for record in self:
            last_price = self.env['tms.fuel.history'].search([], limit=1, order='date desc, id desc')
            if last_price and last_price.date:
                deadline = fields.Date.today() - timedelta(days=7)
                record.is_fuel_price_outdated = last_price.date < deadline
            else:
                # Si no hay historial, también advertimos
                record.is_fuel_price_outdated = True

    fuel_performance = fields.Float(string='Rendimiento (Km/L)', default=2.5, digits=(10,2), help="Kms por Litro")
    cost_tolls = fields.Float(string='Costo Casetas', digits=(10,2))
    cost_driver = fields.Float(string='Sueldo Chofer', digits=(10,2))
    cost_maneuver = fields.Float(string='Maniobras', digits=(10,2))
    cost_other = fields.Float(string='Otros Gastos', digits=(10,2))
    cost_commission = fields.Float(string='Comisión', digits=(10,2))

    # Costo Diesel Estimado (Calculado y Almacenado)
    # IMPORTANTE: Este campo tiene store=True, por lo que necesita su propio método compute
    # para evitar warnings de Odoo sobre inconsistencia entre campos almacenados y no almacenados
    cost_diesel_total = fields.Float(
        string='Costo Diesel Est.',
        compute='_compute_cost_diesel_total',
        store=True
    )

    cost_total_estimated = fields.Monetary(
        string='Costo Total Estimado',
        currency_field='currency_id',
        compute='_compute_cost_total_estimated',
        store=True,
        help='Suma de todos los costos estimados (Diesel + Casetas + Chofer + Maniobras + Otros + Comisión)'
    )

    # --- PROPUESTA 1: POR KILÓMETRO ---
    price_per_km = fields.Float(string='Precio por Km', digits=(10,2))
    # IMPORTANTE: Este campo NO tiene store=True, usa método separado
    proposal_km_total = fields.Monetary(
        string='Total (Por KM)',
        compute='_compute_proposal_values',
        currency_field='currency_id',
        store=False
    )

    # --- PROPUESTA 2: POR VIAJE (Costos + Utilidad) ---
    profit_margin_percent = fields.Float(string='Margen Utilidad (%)', default=30.0)
    # IMPORTANTE: Este campo NO tiene store=True, usa método separado
    proposal_trip_total = fields.Monetary(
        string='Total (Por Viaje)',
        compute='_compute_proposal_values',
        currency_field='currency_id',
        store=False
    )

    # --- PROPUESTA 3: VENTA DIRECTA ---
    proposal_direct_amount = fields.Monetary(string='Precio Directo', currency_field='currency_id')

    # --- SELECCIÓN ---
    selected_proposal = fields.Selection(
        [('km', 'Por Kilómetro'), ('trip', 'Por Viaje (Costos)'), ('direct', 'Directo')],
        string='Propuesta Seleccionada',
        default='direct',
        tracking=True
    )

    # ============================================================
    # MERCANCÍAS (One2many)
    # ============================================================

    # One2many: líneas de mercancía
    line_ids = fields.One2many(
        'tms.waybill.line',
        'waybill_id',
        string='Mercancías',
        help='Mercancías transportadas en el viaje'
    )

    # Contador de mercancías para el smart button
    line_count = fields.Integer(
        string='Cant. Mercancías',
        compute='_compute_line_count',
        store=False,
        help='Número de líneas de mercancía registradas en este viaje'
    )

    has_dangerous_lines = fields.Boolean(
        compute='_compute_has_dangerous_lines',
        store=False,
    )

    @api.depends('line_ids.is_dangerous')
    def _compute_has_dangerous_lines(self):
        for rec in self:
            rec.has_dangerous_lines = any(l.is_dangerous for l in rec.line_ids)

    @api.depends('line_ids')
    def _compute_line_count(self):
        """Cuenta las líneas de mercancía para mostrar en el smart button."""
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends('amount_untaxed', 'partner_invoice_id', 'partner_invoice_id.is_company')
    def _compute_amount_all(self):
        """
        Calcula impuestos y total final.
        Asume IVA 16% y Retención 4% (sólo si es persona moral).
        """
        for record in self:
            base = record.amount_untaxed
            iva = base * 0.16
            
            # Retención 4% solo si cliente es persona moral
            if record.partner_invoice_id and record.partner_invoice_id.is_company:
                ret = base * 0.04
            else:
                ret = 0.0

            record.amount_tax = iva
            record.amount_retention = ret
            record.amount_total = base + iva - ret

    # ============================================================
    # MÉTODOS COMPUTADOS
    # ============================================================

    @api.depends('distance_km', 'extra_distance_km', 'fuel_price_liter', 'fuel_performance')
    def _compute_cost_diesel_total(self):
        """
        Calcula el costo total de diesel estimado.

        FÓRMULA:
        - Distancia Total = Distancia Base + Km Extras
        - Litros necesarios = Distancia Total (km) / Rendimiento (km/L)
        - Costo Total = Litros necesarios * Precio por Litro

        IMPORTANTE:
        - Este método es SEPARADO porque cost_diesel_total tiene store=True
        - Odoo recomienda separar métodos para campos almacenados y no almacenados
        - Esto evita warnings de inconsistencia en compute_sudo y store
        - Los Km Extras se incluyen en el cálculo de combustible
        """
        for record in self:
            total_distance = record.distance_km + record.extra_distance_km
            if record.fuel_performance > 0:
                liters_needed = total_distance / record.fuel_performance
                record.cost_diesel_total = liters_needed * record.fuel_price_liter
            else:
                record.cost_diesel_total = 0.0

    @api.depends('cost_diesel_total', 'cost_tolls', 'cost_driver', 'cost_maneuver', 'cost_other', 'cost_commission')
    def _compute_cost_total_estimated(self):
        """
        Calcula la suma total de los costos estimados.
        """
        for record in self:
            record.cost_total_estimated = (
                record.cost_diesel_total +
                record.cost_tolls +
                record.cost_driver +
                record.cost_maneuver +
                record.cost_other +
                record.cost_commission
            )

    @api.depends('distance_km', 'extra_distance_km', 'price_per_km', 'cost_diesel_total',
                 'cost_tolls', 'cost_driver', 'cost_maneuver', 'cost_other', 'cost_commission',
                 'profit_margin_percent', 'proposal_direct_amount', 'selected_proposal',
                 'partner_invoice_id', 'partner_invoice_id.is_company')
    def _compute_proposal_values(self):
        """
        Calcula las 3 propuestas de cotización automáticamente.

        PROPUESTA 1 (Por KM): (Distancia Base + Km Extras) * Precio/KM
        PROPUESTA 2 (Por Viaje): (Costos Totales) / (1 - Margen%)
        PROPUESTA 3 (Directa): Monto fijo capturado manualmente

        IMPORTANTE:
        - Este método es para campos NO almacenados (store=False)
        - Depende de cost_diesel_total que SÍ está almacenado
        - Esto evita warnings de inconsistencia en compute_sudo y store
        - Los Km Extras se suman a la distancia base para el cobro por KM
        """
        for record in self:
            # 1. Calcular Propuesta KM
            # Distancia Total = Distancia Base + Km Extras
            # Total = Distancia Total * Precio por KM
            total_distance = record.distance_km + record.extra_distance_km
            record.proposal_km_total = total_distance * record.price_per_km
            # 2. Calcular Propuesta Viaje
            # Costo Total = Diesel + Casetas + Chofer + Maniobras + Otros + Comisión
            total_costs = record.cost_diesel_total + record.cost_tolls + record.cost_driver + record.cost_maneuver + record.cost_other + record.cost_commission
            # Precio Venta = Costo Total / (1 - Margen%)
            margin_factor = 1 - (record.profit_margin_percent / 100)
            
            # Ajuste de Retención 4% si es persona moral
            if record.partner_invoice_id and record.partner_invoice_id.is_company:
                margin_factor -= 0.04
                
            if margin_factor > 0:
                record.proposal_trip_total = total_costs / margin_factor
            else:
                record.proposal_trip_total = total_costs

    def action_apply_proposal(self):
        """
        Aplica el valor de la propuesta de cotización seleccionada al Subtotal.
        Esto asegura que el valor se guarde correctamente en la base de datos.
        """
        self.ensure_one()
        value = 0.0
        if self.selected_proposal == 'km':
            value = self.proposal_km_total
        elif self.selected_proposal == 'trip':
            value = self.proposal_trip_total
        else:
            value = self.proposal_direct_amount
        
        self.write({'amount_untaxed': value})
        return True




    def _compute_access_url(self):
        """
        Sobrescribe el método de portal.mixin para generar la URL del portal.

        ¿QUÉ HACE?
        - portal.mixin genera URLs genéricas por defecto
        - Necesitamos URLs específicas para el controlador /my/waybills/<waybill>

        EJEMPLO:
        - Waybill ID 5 → access_url = '/my/waybills/5'
        - El cliente puede acceder desde el portal usando esta URL
        """
        # Llamar al método padre para mantener la lógica base
        super()._compute_access_url()
        # Asignar URL personalizada para cada waybill
        for waybill in self:
            waybill.access_url = '/my/waybills/%s' % (waybill.id)

    @api.depends('partner_invoice_id', 'partner_invoice_id.street', 'partner_invoice_id.city',
                 'partner_invoice_id.zip', 'partner_invoice_id.state_id')
    def _compute_partner_addresses(self):
        """
        Calcula la dirección completa del cliente de facturación.
        Formato: "Calle, Ciudad, Estado, CP"
        """
        for record in self:
            if record.partner_invoice_id:
                # Construir dirección desde las partes
                parts = []
                if record.partner_invoice_id.street:
                    parts.append(record.partner_invoice_id.street)
                if record.partner_invoice_id.city:
                    parts.append(record.partner_invoice_id.city)
                if record.partner_invoice_id.state_id:
                    parts.append(record.partner_invoice_id.state_id.name)

                # Obtener CP: Si zip está vacío, usar tms_cp_id
                zip_code = record.partner_invoice_id.zip
                if not zip_code and record.partner_invoice_id.tms_cp_id:
                    zip_code = record.partner_invoice_id.tms_cp_id.code

                # CP siempre visible si existe
                address_str = ', '.join(parts) if parts else ''
                if zip_code:
                    if address_str:
                         address_str += f", {zip_code}"
                    else:
                         address_str = zip_code

                record.invoice_address = address_str
            else:
                record.invoice_address = ''

    # ============================================================
    # MÉTODOS ONCHANGE (Autocompletado Inteligente)
    # ============================================================

    @api.onchange('partner_origin_id')
    def _onchange_partner_origin(self):
        """
        AUTOCOMPLETADO DE DATOS DEL REMITENTE.
        Copia dirección, CP y busca municipio SAT.
        Construye dirección completa si falta la calle.
        """
        if self.partner_origin_id:
            # Construir dirección
            parts = []
            if self.partner_origin_id.street:
                parts.append(self.partner_origin_id.street)
            if self.partner_origin_id.street2:
                parts.append(self.partner_origin_id.street2)
            if self.partner_origin_id.city:
                parts.append(self.partner_origin_id.city)
            if self.partner_origin_id.state_id:
                parts.append(self.partner_origin_id.state_id.name)

            # Obtener CP: Si zip está vacío, usar tms_cp_id
            zip_code = self.partner_origin_id.zip
            if not zip_code and self.partner_origin_id.tms_cp_id:
                zip_code = self.partner_origin_id.tms_cp_id.code

            # CP siempre visible si existe
            address_str = ', '.join(parts)
            if zip_code:
                if address_str:
                     address_str += f", {zip_code}"
                else:
                     address_str = zip_code

            self.origin_address = address_str
            self.origin_zip = zip_code or ''

            # Buscar municipio SAT por nombre de ciudad
            if self.partner_origin_id.city:
                municipio = self.env['tms.sat.municipio'].search([
                    ('name', 'ilike', self.partner_origin_id.city),
                ], limit=1)
                if municipio:
                    self.origin_city_id = municipio


    @api.onchange('partner_dest_id')
    def _onchange_partner_dest(self):
        """
        AUTOCOMPLETADO DE DATOS DEL DESTINATARIO.
        Copia dirección, CP y busca municipio SAT.
        Construye dirección completa si falta la calle.
        """
        if self.partner_dest_id:
            # Construir dirección
            parts = []
            if self.partner_dest_id.street:
                parts.append(self.partner_dest_id.street)
            if self.partner_dest_id.street2:
                parts.append(self.partner_dest_id.street2)
            if self.partner_dest_id.city:
                parts.append(self.partner_dest_id.city)
            if self.partner_dest_id.state_id:
                parts.append(self.partner_dest_id.state_id.name)

            # Obtener CP: Si zip está vacío, usar tms_cp_id
            zip_code = self.partner_dest_id.zip
            if not zip_code and self.partner_dest_id.tms_cp_id:
                zip_code = self.partner_dest_id.tms_cp_id.code

            # CP siempre visible si existe
            address_str = ', '.join(parts)
            if zip_code:
                 if address_str:
                      address_str += f", {zip_code}"
                 else:
                      address_str = zip_code

            self.dest_address = address_str
            self.dest_zip = zip_code or ''

            # Buscar municipio SAT por nombre de ciudad
            if self.partner_dest_id.city:
                municipio = self.env['tms.sat.municipio'].search([
                    ('name', 'ilike', self.partner_dest_id.city),
                ], limit=1)
                if municipio:
                    self.dest_city_id = municipio




    # ============================================================
    # COMPUTE: Nombre de ciudad a partir del CP
    # ============================================================

    @api.depends('origin_zip', 'dest_zip')
    def _compute_city_names(self):
        for rec in self:
            rec.origin_city_name = rec._get_city_from_zip(rec.origin_zip)
            rec.dest_city_name = rec._get_city_from_zip(rec.dest_zip)

    def _get_city_from_zip(self, zip_code):
        if not zip_code:
            return ''
        cp = self.env['tms.sat.codigo.postal'].with_context(active_test=False).search(
            [('code', '=', zip_code)], limit=1)
        if not cp:
            return ''
        if cp.municipio and cp.estado:
            muni = self.env['tms.sat.municipio'].search(
                [('code', '=', cp.municipio), ('estado', '=', cp.estado)], limit=1)
            if muni:
                state = self.env['res.country.state'].search(
                    ['|', ('code', '=', cp.estado), ('code', '=', f'MX-{cp.estado}'),
                     ('country_id.code', '=', 'MX')], limit=1)
                state_name = state.name if state else cp.estado
                return f"{muni.name}, {state_name}"
        return cp.estado or ''

    # ============================================================
    # MÉTODO: Group Expand (CRÍTICO para Kanban)
    # ============================================================

    def _expand_states(self, states, domain, order=None):
        """
        Controla qué columnas aparecen en el Kanban agrupado por estado.
        Solo retorna los 6 estados operativos visibles al transportista.
        Los estados internos (draft, en_pedido, assigned, cancel, rejected)
        siguen existiendo en el flujo Python pero no se muestran como columnas.
        """
        return [
            'cotizado',
            'aprobado',
            'waybill',
            'in_transit',
            'arrived',
            'closed',
        ]

    # ============================================================
    # MÉTODOS DE ACCIÓN MANUAL (Plan B: Botones en Odoo)
    # ============================================================
    # IMPORTANTE: Estos métodos son el RESPALDO cuando la App falla
    # o no está disponible. Permiten operar el sistema 100% manualmente.

    # action_confirm es alias de action_approve_cp (V2.5 — estados simplificados).

    # ============================================================
    # SMART BUTTONS — Acciones de navegación rápida
    # ============================================================

    def action_nueva_cotizacion(self, *args, **kwargs):
        """
        Abre el wizard de cotización rápida.
        Al no requerir self.ensure_one(), puede ejecutarse sobre recordsets
        vacíos o múltiples registros desde list/kanban o form nuevo.
        """
        return {
            'name': _('Nueva Cotización'),
            'type': 'ir.actions.act_window',
            'res_model': 'tms.cotizacion.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {},
        }

    def action_view_lines(self):
        """
        Abre la lista de mercancías (tms.waybill.line) de este viaje.
        Accionado desde el smart button de Mercancías.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Mercancías — {self.name}',
            'res_model': 'tms.waybill.line',
            'view_mode': 'list,form',
            'domain': [('waybill_id', '=', self.id)],
            'context': {'default_waybill_id': self.id},
        }

    def action_view_tracking(self):
        """
        Abre la bitácora de eventos GPS (tms.tracking.event) de este viaje.
        Accionado desde el smart button de Bitácora GPS.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Bitácora GPS — {self.name}',
            'res_model': 'tms.tracking.event',
            'view_mode': 'list,form',
            'domain': [('waybill_id', '=', self.id)],
            'context': {'default_waybill_id': self.id},
        }

    def action_view_vehicle(self):
        """
        Abre la ficha del vehículo (fleet.vehicle) asignado a este viaje.
        Accionado desde el smart button de Vehículo.
        """
        self.ensure_one()
        if not self.vehicle_id:
            return {}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehículo',
            'res_model': 'fleet.vehicle',
            'view_mode': 'form',
            'res_id': self.vehicle_id.id,
        }

    def action_confirm(self):
        """
        Alias de action_approve_cp para compatibilidad con llamadas externas.
        Confirma el viaje ejecutando la validación completa CP 3.1.
        """
        self.ensure_one()
        if not self.partner_invoice_id:
            raise UserError(_('Debe seleccionar un cliente antes de confirmar.'))
        return self.action_approve_cp()

    def action_approve_cp(self):
        """
        MANUAL: Aprobar Carta Porte → Carta Porte Lista.
        Se ejecuta cuando el vehículo y chofer están asignados.
        Realizó validación exhustiva para CP 3.1 y CFDI 4.0.
        """
        self.ensure_one()

        # Validaciones de integridad operativa básica
        if not self.vehicle_id:
            raise UserError(_('Debe asignar un vehículo antes de aprobar la CP.'))
        if not self.driver_id:
            raise UserError(_('Debe asignar un chofer antes de aprobar la CP.'))

        # =========================================================
        # VALIDACIÓN OFICIAL CARTA PORTE 3.1 / CFDI 4.0
        # =========================================================
        errors = []

        # 1. EMISOR (Tu Empresa) - res.company
        company = self.company_id
        if not company.zip:
            errors.append("- Emisor: Falta el Código Postal (Lugar de Expedición) en la configuración de la empresa.")
        if not company.vat:
            errors.append("- Emisor: Falta el RFC de tu empresa.")
        if hasattr(company, 'l10n_mx_edi_fiscal_regime') and not company.l10n_mx_edi_fiscal_regime:
            errors.append("- Emisor: Falta el Régimen Fiscal de tu empresa.")

        # 2. RECEPTOR (Cliente Facturación) - res.partner
        client = self.partner_invoice_id
        if not client.vat:
            errors.append(f"- Cliente ({client.name}): Falta el RFC.")
        if not client.zip:
             errors.append(f"- Cliente ({client.name}): Falta el Código Postal (Domicilio Fiscal Receptor).")
        if hasattr(client, 'l10n_mx_edi_fiscal_regime') and not client.l10n_mx_edi_fiscal_regime:
             errors.append(f"- Cliente ({client.name}): Falta el Régimen Fiscal.")
        if hasattr(client, 'l10n_mx_edi_usage') and not client.l10n_mx_edi_usage:
             errors.append(f"- Cliente ({client.name}): Falta el Uso de CFDI.")
        
        # 3. UBICACIONES (Origen y Destino)
        # Origen
        origin = self.partner_origin_id
        if not origin.vat:
             errors.append("- Origen: El remitente no tiene RFC.")
        if not self.origin_zip:
             errors.append("- Origen: Falta el Código Postal.")
        # Opcional: Validar calle, estado, pais si fuera estricto, pero CP es lo mínimo vital para timbre

        # Destino
        dest = self.partner_dest_id
        if not dest.vat:
             errors.append("- Destino: El destinatario no tiene RFC.")
        if not self.dest_zip:
             errors.append("- Destino: Falta el Código Postal.")

        # Distancia
        if self.distance_km <= 0:
            errors.append("- Ruta: La distancia recorrida debe ser mayor a 0 km.")
        
        # 4. MERCANCÍAS
        if not self.line_ids:
             errors.append("- Mercancías: No hay mercancías registradas.")
        else:
            for idx, line in enumerate(self.line_ids, start=1):
                prefix = f"- Mercancía #{idx} ({line.description or 'Sin desc'}):"
                if not line.product_sat_id:
                    errors.append(f"{prefix} Falta Clave Producto SAT (c_ClaveProdServCP).")
                if not line.weight_kg or line.weight_kg <= 0:
                    errors.append(f"{prefix} El peso en Kg es obligatorio y debe ser > 0.")
                if not line.uom_sat_id:
                    errors.append(f"{prefix} Falta Clave Unidad SAT.")
                if not line.quantity or line.quantity <= 0:
                     errors.append(f"{prefix} La cantidad debe ser mayor a 0.")
                
                # Material Peligroso
                if line.is_dangerous:
                    if not line.material_peligroso_id:
                         errors.append(f"{prefix} Marcado como peligroso pero falta especificar la Clave Material Peligroso.")
                    if not line.embalaje_id:
                         errors.append(f"{prefix} Marcado como peligroso pero falta especificar el Tipo de Embalaje.")

        # 5. AUTOTRANSPORTE (Vehículo) - Delegación a fleet.vehicle
        if self.vehicle_id:
             errors.extend(self.vehicle_id.validate_carta_porte_compliance())
        
        # 5b. REMOLQUES (Delegación a fleet.vehicle)
        if self.trailer1_id:
             errors.extend(self.trailer1_id.validate_carta_porte_compliance())
        if self.trailer2_id:
             errors.extend(self.trailer2_id.validate_carta_porte_compliance())

        # 6. FIGURA TRANSPORTE (Chofer) - Delegación a hr.employee
        if self.driver_id:
             errors.extend(self.driver_id.validate_carta_porte_compliance())
        else:
             errors.append("- Chofer: No hay chofer asignado.")

        # LANZAR ERRORES ACUMULADOS
        if errors:
            msg = "No se puede generar la Carta Porte porque faltan datos obligatorios para CP 3.1 / CFDI 4.0:\n\n"
            msg += "\n".join(errors)
            msg += "\n\nPor favor complete la información faltante en los registros correspondientes (Empresa, Cliente, Vehículo, Chofer o Mercancías)."
            raise ValidationError(msg)

        # NO cambiar estado aquí — el estado 'waybill' se asigna solo al timbrar exitosamente.
        # Validación aprobada: el registro queda en 'aprobado', listo para timbrar.

    # ============================================================
    # TIMBRADO CFDI — Acciones (V2.2 / V2.2.2)
    # ============================================================

    def action_stamp_cfdi(self):
        """
        Abre el wizard de validación previa antes de timbrar (V2.2.2).
        Crea el wizard con todos los checks del waybill y lo muestra en diálogo.
        El timbrado real lo ejecuta action_do_stamp_cfdi() si pasa la validación.
        """
        self.ensure_one()
        wizard = self.env['tms.stamp.validation.wizard'].create_for_waybill(self.id)
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'tms.stamp.validation.wizard',
            'res_id':    wizard.id,
            'view_mode': 'form',
            'target':    'new',
            'name':      'Validación previa al timbrado',
        }

    def action_do_stamp_cfdi(self):
        """
        Ejecuta el timbrado real de la Carta Porte 3.1 (V2.2 / V2.2.2).
        Llamado desde TmsStampValidationWizard.action_confirmar_timbrado()
        después de que el usuario revisó y aprobó las validaciones.

        Flujo:
        1. Generar IdCCP fresco (siempre nuevo por intento, no reutilizar)
        2. Construir XML con CartaPorteXmlBuilder
        3. Firmar XML con CfdiSigner usando CSD de la empresa
        4. Enviar a PAC via PacManager (con failover automático)
        5. Guardar UUID, XML, fecha, PAC en campos cfdi_*
        6. Registrar en chatter: UUID + PAC usado
        7. Cambiar cfdi_status a 'timbrado'
        """
        self.ensure_one()
        if self.state not in ('aprobado', 'waybill'):
            raise UserError(_('Solo se puede timbrar una Carta Porte en estado "Aprobado" o "Carta Porte".'))
        if self.cfdi_status == 'timbrado':
            raise UserError(_('Este CFDI ya fue timbrado. UUID: %s') % self.cfdi_uuid)

        company = self.company_id
        if not company.tms_csd_cer or not company.tms_csd_key or not company.tms_csd_password:
            raise UserError(_(
                'Falta el Certificado de Sello Digital (CSD) en la configuración de la empresa.\n'
                'Ve a: Ajustes → TMS → CSD Certificado / Llave / Contraseña.'
            ))

        try:
            from odoo.addons.tms.services.xml_builder import CartaPorteXmlBuilder
            from odoo.addons.tms.services.xml_signer import CfdiSigner
            from odoo.addons.tms.services.pac_manager import PacManager
            import base64

            # fields.Binary en Odoo retorna base64 (str o bytes) o False.
            # Decodificar aquí — el signer recibe DER bytes puros.
            csd_cer_bytes = base64.b64decode(company.tms_csd_cer)
            csd_key_bytes = base64.b64decode(company.tms_csd_key)
            if not csd_cer_bytes or not csd_key_bytes:
                raise UserError(_(
                    'No se pudo leer el CSD. Vuelve a cargar el .cer y .key '
                    'en Ajustes → TMS → Certificados SAT.'
                ))

            # Generar IdCCP fresco en cada intento de timbrado.
            # No reutilizar el IdCCP de intentos fallidos anteriores — cada timbrado
            # debe identificarse de manera única ante el SAT y el PAC.
            self.tms_id_ccp = _generate_id_ccp()
            _logger.info('IdCCP generado para timbrado: %s (waybill %s)', self.tms_id_ccp, self.name)

            # 1. Construir XML
            builder = CartaPorteXmlBuilder()
            xml_sin_sellar = builder.build(self)

            # 2. Firmar XML con CSD (bytes DER ya decodificados)
            signer = CfdiSigner()
            xml_sellado = signer.sign(
                xml_sin_sellar,
                csd_cer_bytes,
                csd_key_bytes,
                company.tms_csd_password,
            )

            # 3. Timbrar via PAC (con failover)
            manager = PacManager(self.env)
            resultado = manager.timbrar(xml_sellado, company)

            # 4. Guardar resultado + avanzar estado a 'waybill' (timbrado exitoso)
            xml_fname = 'CFDI-%s-%s.xml' % (self.name, resultado['uuid'][:8])
            self.write({
                'cfdi_uuid':        resultado['uuid'],
                'cfdi_xml':         base64.b64encode(resultado['xml_timbrado']),
                'cfdi_xml_fname':   xml_fname,
                # Normalizar ISO 8601 con T al formato Odoo Datetime (sin T)
                'cfdi_fecha':       (resultado.get('fecha_timbrado') or resultado.get('fecha', '')).replace('T', ' '),
                'cfdi_pac':         resultado['pac_usado'],
                'cfdi_no_cert_sat': resultado.get('no_cert_sat', ''),
                'cfdi_status':      'timbrado',
                'cfdi_error_msg':   False,
                'state':            'waybill',  # Estado 'waybill' solo al timbrar exitosamente
            })

            # 5. Registrar en chatter
            if hasattr(self, 'message_post'):
                self.message_post(
                    body=_(
                        'Carta Porte timbrada correctamente.\n'
                        'UUID: %(uuid)s\nPAC: %(pac)s'
                    ) % {'uuid': resultado['uuid'], 'pac': resultado['pac_usado']},
                    subject=_('CFDI Timbrado'),
                )

        except UserError:
            raise
        except Exception as e:
            _logger.error('TMS TIMBRADO ERROR waybill %s: %s', self.id, str(e))
            self.write({
                'cfdi_status':    'error',
                'cfdi_error_msg': str(e),
            })
            raise UserError(_('Error al timbrar: %s') % str(e))
        return True

    def action_cancel_cfdi(self):
        """
        Cancela el CFDI timbrado.
        Solo ejecutable cuando cfdi_status='timbrado'.
        V2.3: agregar wizard para seleccionar motivo.
        """
        self.ensure_one()
        if self.cfdi_status != 'timbrado':
            raise UserError(_('Solo se puede cancelar un CFDI en estado "Timbrado".'))

        try:
            from odoo.addons.tms.services.pac_manager import PacManager
            manager = PacManager(self.env)
            # Motivo 03 = no se llevó a cabo la operación (default)
            manager.cancelar(self.cfdi_uuid, '03', self.company_id)

            self.write({'cfdi_status': 'cancelado'})

            if hasattr(self, 'message_post'):
                self.message_post(
                    body=_('CFDI cancelado. UUID: %s') % self.cfdi_uuid,
                    subject=_('CFDI Cancelado'),
                )

        except UserError:
            raise
        except Exception as e:
            _logger.error('TMS CANCELACION ERROR waybill %s: %s', self.id, str(e))
            raise UserError(_('Error al cancelar CFDI: %s') % str(e))

    def action_check_cfdi_status(self):
        """
        Consulta el estatus del CFDI en el SAT.
        Actualiza cfdi_status según respuesta y muestra notificación.
        """
        self.ensure_one()
        if self.cfdi_status == 'none':
            raise UserError(_('Este waybill no tiene CFDI timbrado.'))

        try:
            from odoo.addons.tms.services.pac_manager import PacManager
            manager = PacManager(self.env)
            estatus = manager.consultar_estatus(self.cfdi_uuid, self.company_id)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title':   _('Estatus CFDI'),
                    'message': estatus.get('descripcion', 'Sin información'),
                    'type':    'info',
                    'sticky':  False,
                }
            }

        except UserError:
            raise
        except Exception as e:
            _logger.error('TMS ESTATUS ERROR waybill %s: %s', self.id, str(e))
            raise UserError(_('Error al consultar estatus: %s') % str(e))

    def action_download_cfdi_xml(self):
        """
        Descarga el XML timbrado como archivo adjunto.
        Solo disponible cuando cfdi_status='timbrado'.
        """
        self.ensure_one()
        if self.cfdi_status != 'timbrado' or not self.cfdi_xml:
            raise UserError(_('No hay XML timbrado disponible para descargar.'))

        return {
            'type':   'ir.actions.act_url',
            'url':    '/web/content/%s/%s/cfdi_xml/%s?download=true' % (
                self._name, self.id, self.cfdi_xml_fname or 'cfdi.xml'
            ),
            'target': 'self',
        }

    # ============================================================
    # PDF CARTA PORTE — Helpers para reporte QWeb
    # ============================================================

    def _parse_cfdi_xml(self):
        """
        Parsea el XML timbrado almacenado en cfdi_xml y extrae los datos fiscales
        del CFDI 4.0 y del Timbre Fiscal Digital (TFD).

        Retorna dict con:
          sello_cfdi, sello_sat, no_cert_emisor, no_cert_sat,
          fecha_timbrado, cadena_tfd, rfc_emisor, nombre_emisor,
          regimen_emisor, rfc_receptor, nombre_receptor, uso_cfdi.
        Retorna {} si no hay XML o hay error al parsear.
        """
        self.ensure_one()
        if not self.cfdi_xml:
            return {}
        try:
            xml_bytes = base64.b64decode(self.cfdi_xml)
            root = lxml_etree.fromstring(xml_bytes)

            ns = {
                'cfdi': 'http://www.sat.gob.mx/cfd/4',
                'tfd':  'http://www.sat.gob.mx/TimbreFiscalDigital',
            }

            sello_cfdi    = root.get('Sello', '')
            no_cert_emisor = root.get('NoCertificado', '')

            emisor   = root.find('.//cfdi:Emisor', ns)
            receptor = root.find('.//cfdi:Receptor', ns)
            tfd      = root.find('.//tfd:TimbreFiscalDigital', ns)

            sello_sat     = ''
            no_cert_sat   = ''
            fecha_timbrado = ''
            cadena_tfd    = ''

            if tfd is not None:
                sello_sat      = tfd.get('SelloSAT', '')
                no_cert_sat    = tfd.get('NoCertificadoSAT', '')
                fecha_timbrado = tfd.get('FechaTimbrado', '')
                # Cadena original del TFD según especificación SAT
                cadena_tfd = (
                    '||1.1|{uuid}|{fecha}|{rfc_pac}|{sello_cfdi}|{no_cert_sat}||'
                ).format(
                    uuid=tfd.get('UUID', ''),
                    fecha=fecha_timbrado,
                    rfc_pac=tfd.get('RfcProvCertif', ''),
                    sello_cfdi=sello_cfdi,
                    no_cert_sat=no_cert_sat,
                )

            return {
                'sello_cfdi':     sello_cfdi,
                'sello_sat':      sello_sat,
                'no_cert_emisor': no_cert_emisor,
                'no_cert_sat':    no_cert_sat,
                'fecha_timbrado': fecha_timbrado,
                'cadena_tfd':     cadena_tfd,
                'rfc_emisor':     emisor.get('Rfc', '')    if emisor   is not None else '',
                'nombre_emisor':  emisor.get('Nombre', '') if emisor   is not None else '',
                'regimen_emisor': emisor.get('RegimenFiscal', '') if emisor is not None else '',
                'rfc_receptor':   receptor.get('Rfc', '') if receptor is not None else '',
                'nombre_receptor': receptor.get('Nombre', '') if receptor is not None else '',
                'uso_cfdi':       receptor.get('UsoCFDI', '') if receptor is not None else '',
            }
        except Exception as exc:
            _logger.error('Error parseando XML timbrado en waybill %s: %s', self.name, exc)
            return {}

    def _get_cfdi_qr_url(self):
        """
        Genera la URL de verificación SAT para el código QR del CFDI.

        Formato oficial SAT:
        https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx
        ?id=UUID&re=RFC_EMISOR&rr=RFC_RECEPTOR&tt=0.00&fe=ULTIMOS8_SELLO
        """
        self.ensure_one()
        if not self.cfdi_uuid or not self.cfdi_xml:
            return ''
        datos = self._parse_cfdi_xml()
        if not datos:
            return ''
        sello = datos.get('sello_cfdi', '')
        fe = sello[-8:] if len(sello) >= 8 else sello
        return (
            'https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx'
            '?id={uuid}&re={re}&rr={rr}&tt=0.00&fe={fe}'
        ).format(
            uuid=self.cfdi_uuid,
            re=datos.get('rfc_emisor', ''),
            rr=datos.get('rfc_receptor', ''),
            fe=fe,
        )

    def _get_cfdi_qr_image(self):
        """
        Genera imagen QR en base64 (PNG) con la URL de verificación SAT.
        Usa la librería qrcode[pil]. Si no está instalada, retorna ''.
        """
        self.ensure_one()
        url = self._get_cfdi_qr_url()
        if not url:
            return ''
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=4, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except ImportError:
            _logger.warning(
                'Librería qrcode no instalada — QR omitido en PDF Carta Porte. '
                'Instalar con: pip install qrcode[pil]'
            )
            return ''
        except Exception as exc:
            _logger.warning('Error generando imagen QR para waybill %s: %s', self.name, exc)
            return ''

    def action_print_carta_porte(self):
        """
        Genera el PDF de Carta Porte timbrada.
        Solo disponible cuando cfdi_status='timbrado'.
        """
        self.ensure_one()
        if self.cfdi_status != 'timbrado':
            raise UserError(_('No hay CFDI timbrado para generar el PDF.'))
        return self.env.ref(
            'tms.action_report_carta_porte_timbrada'
        ).report_action(self)

    # ============================================================
    # TOLLGURU API INTEGRATION (Smart Route)
    # ============================================================



    def _fetch_tollguru_api(self):
        """
        Conecta con TollGuru para obtener ruta y actualiza el record.
        Usa mapeo dinámico de ejes para seleccionar el vehículo.
        """
        self.ensure_one()
        # Mapeo ejes -> tipo vehículo TollGuru
        # Tracto(3) + Rem1(2) + Dolly(2) + Rem2(2) = 9 ejes
        TOLLGURU_AXLES_MAP = {
            2: "2AxlesTruck",
            3: "3AxlesTruck",
            4: "4AxlesTruck",
            5: "5AxlesTruck",
            6: "6AxlesTruck",
            7: "7AxlesTruck",
            8: "8AxlesTruck",
            9: "9AxlesTruck",
        }

        # Obtener tipo dinámico, default 5 ejes si no está
        # Se usa total_axles calculado previamente (Tracto + Rem1 + Dolly + Rem2)
        vehicle_type = TOLLGURU_AXLES_MAP.get(self.total_axles, "5AxlesTruck")

        # Configuración
        api_key = self.env['ir.config_parameter'].sudo().get_param('tms.tollguru_api_key')
        if not api_key:
             raise UserError(_("Falta configurar la TollGuru API Key en Ajustes."))

        url = "https://apis.tollguru.com/toll/v2/origin-destination-waypoints"
        
        headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }

        # Payload correcto con ejes dinámicos
        payload = {
            "from": {"address": f"{self.partner_origin_id.zip}, Mexico"},
            "to":   {"address": f"{self.partner_dest_id.zip}, Mexico"},
            "vehicle": {
                "type": vehicle_type,
                "weight": {
                    "value": self.vehicle_id.tms_gross_vehicle_weight or 15000,
                    "unit": "kg"
                },
                "axles": self.total_axles,
                "height": {
                    "value": 4.5,
                    "unit": "meter"
                }
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)

            # Log condicional — activar en Ajustes TMS → Debug TollGuru
            debug_mode = self.env['ir.config_parameter'].sudo().get_param('tms.tollguru_debug', False)
            if debug_mode:
                _logger.info("TollGuru STATUS: %s", response.status_code)
                _logger.info("TollGuru PAYLOAD: %s", payload)
                _logger.info("TollGuru RESPONSE: %s", response.text[:2000])



            if response.status_code == 200:
                api_data = response.json()
                
                # TollGuru devuelve 'routes' como lista
                routes = api_data.get('routes', [])
                if not routes:
                    raise UserError(_("TollGuru no devolvió rutas."))
                
                route = routes[0]
                summary = route.get('summary', {})
                costs = route.get('costs', {})
                
                # Distancia: viene en 'value' (metros)
                distance_m = summary.get('distance', {}).get('value', 0)
                distance_km = round(distance_m / 1000.0, 2)
                
                # Duración: viene en 'value' (segundos)
                duration_s = summary.get('duration', {}).get('value', 0)
                duration_hours = round(duration_s / 3600.0, 2)
                
                # Casetas: tag o cash (en MXN)
                toll_cost = costs.get('tag', costs.get('cash', 0.0))
                
                # Guardar en waybill
                self.write({
                    'distance_km': distance_km,
                    'duration_hours': duration_hours,
                    'cost_tolls': toll_cost,
                })
                
                # Log en chatter
                self.message_post(body=_(
                     "Ruta calculada con TollGuru (%s ejes): "
                    "%s km, %s horas, $%s MXN casetas."
                ) % (self.total_axles, distance_km, 
                     duration_hours, toll_cost))
                
                return self._notify_success("Calculado vía TollGuru", distance_km, duration_hours, toll_cost)
            else:
                _logger.error("TollGuru Error: %s", response.text)
                raise UserError(_("Error TollGuru: %s") % response.text)

        except Exception as e:
            raise UserError(_("Error de conexión con TollGuru: %s") % str(e))

    def _notify_success(self, source, dist, dur, tolls):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tms.waybill',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'effect': {
                'fadeout': 'slow',
                'message': _('%s\nRuta Actualizada: %.2f km, %.2f hrs, $%s') % (source, dist, dur, tolls),
                'type': 'rainbow_man',
            }
        }


    def action_start_route_manual(self):
        """
        MANUAL: Iniciar Ruta → En Trayecto.

        PLAN B (Respaldo Manual):
        - Registra la fecha/hora actual
        - NO registra GPS (lat/long quedan en 0.0)
        - Cambia estado a 'in_transit'

        VENTAJA: El sistema sigue funcionando aunque la App falle.
        """
        self.ensure_one()

        # Registrar fecha/hora actual
        now = fields.Datetime.now()

        # Escribir valores
        # GPS en 0.0 indica operación MANUAL (sin app)
        self.write({
            'date_started_route': now,
            'lat_started_route': 0.0,  # 0.0 = Manual
            'long_started_route': 0.0,  # 0.0 = Manual
            'state': 'in_transit',
        })

    def action_arrived_dest_manual(self):
        """
        MANUAL: Llegada a Destino → En Destino.

        PLAN B (Respaldo Manual):
        - Registra la fecha/hora actual
        - NO registra GPS (lat/long quedan en 0.0)
        - Cambia estado a 'arrived'
        """
        self.ensure_one()

        # Registrar fecha/hora actual
        now = fields.Datetime.now()

        # Escribir valores
        self.write({
            'date_arrived_dest': now,
            'lat_arrived_dest': 0.0,  # 0.0 = Manual
            'long_arrived_dest': 0.0,  # 0.0 = Manual
            'state': 'arrived',
        })

    def action_create_invoice(self):
        """
        MANUAL: Crear Factura → Facturado.
        Marca el viaje como cerrado.
        """
        self.ensure_one()

        # Validar que tenga monto
        if not self.amount_total:
            raise UserError(_('Debe definir el valor del viaje antes de facturar.'))

        # TODO: Aquí se puede integrar la creación real de factura
        # account_invoice = self.env['account.move'].create({...})

        # Cambia el estado a 'closed' (Facturado/Cerrado) - estado declarado en fields.Selection
        self.write({'state': 'closed'})

    def _action_sign(self, signature, signed_by):
        """
        Acción de Firma Digital desde el Portal Web.

        ¿QUÉ HACE?
        1. Guarda la firma (imagen base64) en el campo signature
        2. Guarda el nombre de quien firma en signed_by
        3. Establece signed_on con la fecha/hora actual
        4. Cambia el estado a 'confirmed' (cotización aceptada)
        5. Registra en el chatter un mensaje de confirmación

        PARÁMETROS:
        - signature: String base64 con la imagen de la firma
        - signed_by: String con el nombre de la persona que firma

        VALIDACIONES:
        - Solo se puede firmar si el estado es 'request' (Solicitud)
        - La firma debe ser válida (no vacía)

        USO:
        - Llamado desde el controlador portal.py cuando el cliente firma
        - Se ejecuta con sudo() para permitir acceso desde portal
        """
        self.ensure_one()

        # Validar que esté en estado cotizado o aprobado
        if self.state not in ('cotizado', 'aprobado'):
            raise UserError(_('Solo se pueden firmar cotizaciones en estado Cotizado o Aprobado.'))

        # Validar que la firma no esté vacía
        if not signature:
            raise ValidationError(_('La firma no puede estar vacía.'))

        # Obtener fecha/hora actual
        now = fields.Datetime.now()

        # Guardar firma y datos
        self.write({
            'signature': signature,
            'signed_by': signed_by,
            'signed_on': now,
            'state': 'aprobado',  # Firma digital aprueba la cotización
        })

        # Registrar en el chatter
        self.message_post(
            body=_('✅ Cotización firmada digitalmente por <strong>%s</strong> el %s') % (
                signed_by,
                now.strftime('%d/%m/%Y %H:%M:%S')
            ),
            subject=_('Firma Digital Recibida'),
        )

    def action_cancel(self):
        """Cancela el viaje."""
        self.ensure_one()
        self.write({'state': 'cancel'})

    # ============================================================
    # API PARA APP MÓVIL (Plan A: Automático)
    # ============================================================

    @api.model
    def action_driver_report(self, waybill_id, status, lat, long):
        """
        API para recibir reportes de la App Móvil.

        PLAN A (Automático):
        - La app del chofer reporta su posición GPS
        - Actualiza fecha/hora, latitud y longitud automáticamente
        - Cambia el estado del viaje según el status

        :param waybill_id: ID del viaje (int)
        :param status: Estado reportado ('started_route', 'arrived_dest', 'tracking')
        :param lat: Latitud GPS (float)
        :param long: Longitud GPS (float)
        :return: dict con resultado

        EJEMPLO DE USO (desde la App):
        POST /web/dataset/call_kw/tms.waybill/action_driver_report
        {
            "params": {
                "args": [123, "started_route", 25.6866, -100.3161]
            }
        }
        """
        # Buscar el viaje
        waybill = self.browse(waybill_id)

        if not waybill.exists():
            return {
                'success': False,
                'message': _('Viaje no encontrado')
            }

        # Registrar fecha/hora actual
        now = fields.Datetime.now()

        # Actualizar según el status reportado
        if status == 'started_route':
            # Chofer inició el viaje
            waybill.write({
                'date_started_route': now,
                'lat_started_route': lat,
                'long_started_route': long,
                'last_app_lat': lat,
                'last_app_long': long,
                'last_report_date': now,
                'state': 'in_transit',
            })
            message = _('Ruta iniciada correctamente')

        elif status == 'arrived_dest':
            # Chofer llegó a destino
            waybill.write({
                'date_arrived_dest': now,
                'lat_arrived_dest': lat,
                'long_arrived_dest': long,
                'last_app_lat': lat,
                'last_app_long': long,
                'last_report_date': now,
                'state': 'arrived',
            })
            message = _('Llegada a destino registrada')

        elif status == 'tracking':
            # Actualización de posición (sin cambio de estado)
            waybill.write({
                'last_app_lat': lat,
                'last_app_long': long,
                'last_report_date': now,
            })
            message = _('Posición actualizada')

        else:
            return {
                'success': False,
                'message': _('Status no válido: %s') % status
            }

        return {
            'success': True,
            'message': message,
            'waybill_id': waybill_id,
            'current_state': waybill.state,
        }

    # ============================================================
    # MÉTODO CREATE (Generar folio automático)
    # ============================================================

    def action_send_email(self):
        """ Abre el wizard de correo con la plantilla pre-cargada """
        self.ensure_one()
        # Referencia a la plantilla creada en data/mail_template_data.xml
        template = self.env.ref('tms.email_template_tms_waybill')

        ctx = {
            'default_model': 'tms.waybill',
            'default_res_ids': self.ids,
            'default_use_template': bool(template),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'force_email': True,
        }

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def write(self, vals):
        """
        Dos responsabilidades:
        1. Bloquea escritura de campos operativos cuando el CFDI ya está timbrado.
           Solo permite los campos de TIMBRADO_WRITABLE_FIELDS (definidos a nivel módulo).
        2. Purga de datos técnica: si se desactiva 'require_trailer',
           vacía forzosamente los campos de remolque para mantener integridad.
        """
        # — Protección post-timbrado —
        for record in self:
            if record.cfdi_status == 'timbrado':
                campos_prohibidos = set(vals.keys()) - TIMBRADO_WRITABLE_FIELDS
                if campos_prohibidos:
                    raise UserError(
                        _('No se puede modificar un viaje timbrado. '
                          'Cancele el CFDI primero.\n'
                          'Campos bloqueados: %s') % ', '.join(sorted(campos_prohibidos))
                    )

        # — Limpieza de remolques al desactivar require_trailer —
        if 'require_trailer' in vals and not vals['require_trailer']:
            vals.update({
                'trailer1_id': False,
                'dolly_id': False,
                'trailer2_id': False,
            })

        res = super(TmsWaybill, self).write(vals)
        # SEMILLA V2.3: activar cuando se implemente tms.route.analytics
        # if vals.get('state') == 'closed':
        #     self.env['tms.route.analytics']._update_from_waybill(self)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """
        Validar que los viajes se creen mediante el Wizard de cotización.
        Genera folio automático para cada viaje (VJ/0001, VJ/0002, etc).
        """
        for vals in vals_list:
            # Validación de procedencia
            if not vals.get('partner_invoice_id') and not self.env.context.get('from_wizard'):
                raise UserError(
                    _('Los viajes deben crearse desde el wizard de cotización. '
                      'Use el botón "Nueva Cotización" en el tablero.')
                )

            # Asegurar limpieza inicial si require_trailer viene en False
            if vals.get('require_trailer') is False:
                vals.update({
                    'trailer1_id': False,
                    'dolly_id': False,
                    'trailer2_id': False,
                })
            
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('tms.waybill') or 'Nuevo'
        return super(TmsWaybill, self).create(vals_list)




# ============================================================
# MODELO DE LÍNEAS: Mercancías del Viaje
# ============================================================


class TmsWaybillLine(models.Model):
    """
    Líneas de Mercancía de un Viaje.

    CONCEPTO: Detalla qué mercancías se transportan en el viaje.
    Ejemplo: 100 cajas de refrescos, 50 sacos de cemento, etc.
    """

    _name = 'tms.waybill.line'
    _description = 'Línea de Mercancía (Viaje)'
    _order = 'sequence, id'

    # Many2one: viaje al que pertenece
    waybill_id = fields.Many2one(
        'tms.waybill',
        string='Viaje',
        required=True,
        ondelete='cascade',  # Si se elimina el viaje, se eliminan sus líneas
    )

    # Integer: orden de la línea
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de la mercancía en la lista'
    )

    # Many2one: clave producto SAT
    product_sat_id = fields.Many2one(
        'tms.sat.clave.prod',
        string='Clave Producto SAT',
        help='Clave del catálogo ClaveProdServCP del SAT'
    )

    # Char: descripción de la mercancía
    description = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción de la mercancía transportada'
    )

    # Float: cantidad
    quantity = fields.Float(
        string='Cantidad',
        digits=(10, 2),
        default=1.0,
        help='Cantidad de unidades'
    )

    # Many2one: unidad de medida SAT
    uom_sat_id = fields.Many2one(
        'tms.sat.clave.unidad',
        string='Unidad SAT',
        help='Unidad de medida según catálogo SAT'
    )

    # Float: peso en kilogramos
    weight_kg = fields.Float(
        string='Peso (Kg)',
        digits=(10, 2),
        help='Peso total de la mercancía en kilogramos'
    )

    # Dimensiones (opcional) — SAT Carta Porte 3.1
    # Patrón XSD: ([0-9]{1,3}[/]){2}([0-9]{1,3})(cm|plg)
    dim_largo = fields.Float(
        string='Largo (cm)',
        digits=(6, 0),
        default=0,
    )
    dim_ancho = fields.Float(
        string='Ancho (cm)',
        digits=(6, 0),
        default=0,
    )
    dim_alto = fields.Float(
        string='Alto (cm)',
        digits=(6, 0),
        default=0,
    )
    dimensions = fields.Char(
        string='Dimensiones',
        compute='_compute_dimensions',
        store=True,
        help='Formato SAT: largo/ancho/alto en cm'
    )

    @api.depends('dim_largo', 'dim_ancho', 'dim_alto')
    def _compute_dimensions(self):
        """
        Calcula el campo dimensions en formato SAT
        a partir de los 3 campos numéricos individuales.
        Formato: 000/000/000cm (requerido por Carta Porte 3.1)
        """
        for rec in self:
            rec.dimensions = '{:03.0f}/{:03.0f}/{:03.0f}cm'.format(
                rec.dim_largo or 0,
                rec.dim_ancho or 0,
                rec.dim_alto or 0,
            )

    # Boolean: es material peligroso
    is_dangerous = fields.Boolean(
        string='Material Peligroso',
        default=False,
        help='Indica si la mercancía es material peligroso'
    )

    material_peligroso_id = fields.Many2one(
        'tms.sat.material.peligroso',
        string='Clave Material Peligroso',
        help='Clave del material peligroso según catálogo SAT'
    )

    embalaje_id = fields.Many2one(
        'tms.sat.embalaje',
        string='Tipo de Embalaje',
        help='Clave del tipo de embalaje según catálogo SAT'
    )

    # Objeto de Impuesto (CFDI 4.0)
    l10n_mx_edi_tax_object = fields.Selection(
        selection=[
            ('01', 'No objeto de impuesto'),
            ('02', 'Sí objeto de impuesto'),
            ('03', 'Sí objeto de impuesto y no obligado al desglose'),
            ('04', 'Sí objeto de impuesto y no causa impuesto'),
        ],
        string='Objeto de Impuesto',
        default=lambda self: self.env.company.tms_def_l10n_mx_edi_tax_object or '02',
        help='Indica si la partida es objeto de impuesto para CFDI 4.0.'
    )

    # ============================================================
    # CARTA PORTE 3.1 - SECTOR COFEPRIS
    # ============================================================
    l10n_mx_edi_sector_cofepris = fields.Selection(
        selection=[
            ('01', 'Fármacos y sustancias farmacéuticas'),
            ('02', 'Dispositivos médicos'),
            ('03', 'Fórmulas para lactantes'),
            ('04', 'Suplementos alimenticios'),
            ('05', 'Plaguicidas y nutrientes vegetales'),
            ('06', 'Sustancias tóxicas'),
            ('07', 'Productos de aseo y limpieza'),
            ('08', 'Cosméticos'),
            ('09', 'Alcohol etílico'),
        ],
        string='Sector COFEPRIS',
        help='Requerido para el nodo SectorCOFEPRIS en Carta Porte 3.1'
    )

    l10n_mx_edi_active_ingredient = fields.Char(
        string='Ingrediente Activo',
        help='Nombre del ingrediente activo (requerido para COFEPRIS).'
    )

    l10n_mx_edi_nominal_purity = fields.Float(
        string='Pureza Nominal',
        digits=(10, 6),
        help='Pureza nominal del producto (COFEPRIS).'
    )

    l10n_mx_edi_unit_purity = fields.Char(
        string='Unidad Pureza',
        help='Unidad de medida de la pureza.'
    )



class TmsWaybillCustomsRegime(models.Model):
    _name = 'tms.waybill.customs.regime'
    _description = 'Régimen Aduanero Carta Porte 3.1'

    waybill_id = fields.Many2one('tms.waybill', ondelete='cascade')
    regimen_aduanero = fields.Selection([
        ('IMD', 'IMD - Definitivo de importación'),
        ('EXD', 'EXD - Definitivo de exportación'),
        ('ITR', 'ITR - Temporal de importación para retornar al extranjero en el mismo estado'),
        ('ITE', 'ITE - Temporal de importación para elaboración, transformación o reparación en programas de maquila o de exportación'),
        ('ETR', 'ETR - Temporal de exportación para retornar al país en el mismo estado'),
        ('ETE', 'ETE - Temporal de exportación para elaboración, transformación o reparación'),
        ('DFE', 'DFE - Depósito fiscal'),
        ('TRA', 'TRA - Tránsito de mercancías'),
        ('EFE', 'EFE - Elaboración, transformación o reparación en recinto fiscalizado'),
        ('RFE', 'RFE - Recinto fiscalizado estratégico'),
    ], string='Régimen Aduanero', required=True)

