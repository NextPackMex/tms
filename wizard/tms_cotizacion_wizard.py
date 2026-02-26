# -*- coding: utf-8 -*-
import logging
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class TmsCotizacionWizard(models.TransientModel):
    """
    Wizard de Cotización Multi-Paso — Etapa 2.1.4

    PASO 1: Cotización Rápida
    - Ruta (origin_zip, dest_zip, num_axles)
    - Variables de costo (diésel, casetas, chofer, etc.)
    - Botón "Calcular Ruta" → llama TollGuru
    - Muestra 3 propuestas de precio
    - Botón "Aprobar y Continuar" → avanza al Paso 2

    PASO 2: Datos Completos del Viaje
    - Cliente, remitente, destinatario
    - Líneas de mercancía
    - Vehículo, chofer, remolques
    - Botón "Crear Viaje" → crea tms.waybill en estado draft
    - Botón "Atrás" → regresa al Paso 1
    """

    _name = 'tms.cotizacion.wizard'
    _description = 'Wizard de Cotización Rápida (Multi-Paso)'

    # ============================================================
    # CONTROL DE PASO
    # ============================================================

    step = fields.Selection(
        selection=[('1', 'Paso 1: Cotización Rápida'), ('2', 'Paso 2: Datos del Viaje')],
        string='Paso',
        default='1',
        required=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )

    # ============================================================
    # PASO 1 — CAMPOS DE RUTA
    # ============================================================

    origin_zip = fields.Char(
        string='CP Origen',
        size=5,
        required=True,
        help='Código postal de origen (5 dígitos)',
    )

    dest_zip = fields.Char(
        string='CP Destino',
        size=5,
        required=True,
        help='Código postal de destino (5 dígitos)',
    )

    num_axles = fields.Integer(
        string='No. de Ejes',
        default=5,
        required=True,
        help='Número total de ejes del convoy (tracto + remolques)',
    )

    # ============================================================
    # PASO 1 — VARIABLES DE COSTO
    # ============================================================

    fuel_price = fields.Float(
        string='Precio Diésel ($/L)',
        digits=(10, 4),
        default=lambda self: self._default_fuel_price(),
        required=True,
    )

    fuel_performance = fields.Float(
        string='Rendimiento (Km/L)',
        digits=(10, 2),
        default=3.5,
        required=True,
    )

    cost_driver = fields.Float(
        string='Costo Chofer ($)',
        digits=(10, 2),
        default=0.0,
    )

    cost_maneuver = fields.Float(
        string='Maniobras ($)',
        digits=(10, 2),
        default=0.0,
    )

    cost_other = fields.Float(
        string='Otros Costos ($)',
        digits=(10, 2),
        default=0.0,
    )

    cost_commission = fields.Float(
        string='Comisión ($)',
        digits=(10, 2),
        default=0.0,
    )

    profit_margin_percent = fields.Float(
        string='Margen de Utilidad (%)',
        digits=(5, 2),
        default=20.0,
        help='Porcentaje de margen para la propuesta "Por Viaje"',
    )

    price_per_km = fields.Float(
        string='Precio por KM ($)',
        digits=(10, 4),
        default=0.0,
        help='Precio base por kilómetro para la propuesta "Por KM"',
    )

    direct_price = fields.Float(
        string='Precio Directo ($)',
        digits=(10, 2),
        required=True,
        default=0.0,
        help='Precio fijo manual para la propuesta "Directo"',
    )

    # ============================================================
    # PASO 1 — RESULTADOS (readonly, calculados por action_calcular_ruta)
    # ============================================================

    ruta_calculada = fields.Boolean(
        string='Ruta Calculada',
        default=False,
    )

    distance_km = fields.Float(
        string='Distancia (Km)',
        digits=(10, 2),
        readonly=True,
    )

    duration_hours = fields.Float(
        string='Duración (Hrs)',
        digits=(10, 2),
        readonly=True,
    )

    extra_km = fields.Float(
        string='Km Extras',
        digits=(10, 2),
        default=0.0,
        help='Kilómetros adicionales cobrables'
    )

    toll_cost = fields.Float(
        string='Casetas ($)',
        digits=(10, 2),
        readonly=True,
    )

    cost_diesel_total = fields.Float(
        string='Costo Diésel Total ($)',
        compute='_compute_costos',
        digits=(10, 2),
    )

    cost_total_estimated = fields.Float(
        string='Costo Total Estimado ($)',
        compute='_compute_costos',
        digits=(10, 2),
    )

    proposal_km_total = fields.Monetary(
        string='Propuesta KM ($)',
        compute='_compute_proposals',
        currency_field='currency_id',
    )

    proposal_trip_total = fields.Monetary(
        string='Propuesta Viaje ($)',
        compute='_compute_proposals',
        currency_field='currency_id',
    )

    selected_proposal = fields.Selection(
        selection=[
            ('km', 'Por Kilómetro'),
            ('trip', 'Por Viaje'),
            ('direct', 'Precio Directo'),
        ],
        string='Propuesta Seleccionada',
        default='direct',
    )

    amount_approved = fields.Monetary(
        string='Monto Aprobado ($)',
        currency_field='currency_id',
        readonly=True,
        help='Monto de la propuesta aprobada para el viaje',
    )

    # ============================================================
    # PASO 2 — ACTORES DEL VIAJE
    # ============================================================

    partner_invoice_id = fields.Many2one(
        'res.partner',
        string='Cliente Facturación',
        domain="[('type', 'in', ['invoice', 'contact'])]",
        help='Cliente al que se facturará el servicio',
    )

    partner_invoice_street = fields.Char(
        compute='_compute_partner_streets',
        string='Domicilio Fiscal'
    )

    partner_origin_id = fields.Many2one(
        'res.partner',
        string='Remitente (Origen)',
        domain="[('type', '!=', 'private')]",
        help='Contacto que entrega la mercancía',
    )

    partner_origin_street = fields.Char(
        compute='_compute_partner_streets',
        string='Dirección Origen'
    )

    origin_address = fields.Char(string='Dirección Origen')

    partner_dest_id = fields.Many2one(
        'res.partner',
        string='Destinatario',
        domain="[('type', '!=', 'private')]",
        help='Contacto que recibe la mercancía',
    )

    partner_dest_street = fields.Char(
        compute='_compute_partner_streets',
        string='Dirección Destino'
    )

    dest_address = fields.Char(string='Dirección Destino')

    @api.depends('partner_invoice_id', 'partner_origin_id', 'partner_dest_id')
    def _compute_partner_streets(self):
        # Concatenar calle + ciudad + CP de cada partner
        for rec in self:
            rec.partner_invoice_street = rec.partner_invoice_id.street or ''
            rec.partner_origin_street = rec.partner_origin_id.street or ''
            rec.partner_dest_street = rec.partner_dest_id.street or ''

    # ============================================================
    # PASO 2 — UNIDAD
    # ============================================================

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo (Tractor)',
        domain="[('tms_is_trailer', '=', False), ('company_id', '=', company_id)]",
        help='Tractocamión asignado al viaje',
    )

    driver_id = fields.Many2one(
        'hr.employee',
        string='Chofer',
        domain="[('tms_is_driver', '=', True)]",
        help='Conductor asignado (debe ser empleado marcado como Chofer)',
    )

    require_trailer = fields.Boolean(
        string='Lleva Remolque',
        default=False,
    )

    trailer1_id = fields.Many2one(
        'fleet.vehicle',
        string='Remolque 1',
        domain="[('tms_is_trailer', '=', True), ('company_id', '=', company_id)]",
    )

    dolly_id = fields.Many2one(
        'fleet.vehicle',
        string='Dolly',
        domain="[('tms_is_trailer', '=', True), ('company_id', '=', company_id)]",
    )

    trailer2_id = fields.Many2one(
        'fleet.vehicle',
        string='Remolque 2',
        domain="[('tms_is_trailer', '=', True), ('company_id', '=', company_id)]",
    )

    # ============================================================
    # PASO 2 — MERCANCÍAS
    # ============================================================

    line_ids = fields.One2many(
        'tms.cotizacion.wizard.line',
        'wizard_id',
        string='Mercancías',
    )

    cp_type = fields.Selection(
        selection=[
            ('ingreso', 'Ingreso (Flete Cobrado)'),
            ('traslado', 'Traslado (Sin Cobro)'),
        ],
        string='Tipo de Carta Porte',
        default='ingreso',
    )

    notes = fields.Text(string='Notas / Observaciones')

    # ============================================================
    # DEFAULTS
    # ============================================================

    def _default_fuel_price(self):
        """Obtiene el último precio de diésel registrado en tms.fuel.history."""
        last = self.env['tms.fuel.history'].search(
            [('company_id', '=', self.env.company.id)],
            order='date desc',
            limit=1,
        )
        return last.price if last else 0.0

    # ============================================================
    # COMPUTES
    # ============================================================

    @api.depends('distance_km', 'fuel_price', 'fuel_performance',
                 'toll_cost', 'cost_driver', 'cost_maneuver',
                 'cost_other', 'cost_commission')
    def _compute_costos(self):
        for rec in self:
            if rec.fuel_performance > 0:
                rec.cost_diesel_total = rec.distance_km / rec.fuel_performance * rec.fuel_price
            else:
                rec.cost_diesel_total = 0.0
            rec.cost_total_estimated = (
                rec.cost_diesel_total
                + rec.toll_cost
                + rec.cost_driver
                + rec.cost_maneuver
                + rec.cost_other
                + rec.cost_commission
            )

    @api.depends('distance_km', 'extra_km', 'price_per_km', 'cost_total_estimated',
                 'profit_margin_percent', 'direct_price', 'partner_invoice_id', 'partner_invoice_id.is_company')
    def _compute_proposals(self):
        for rec in self:
            # Propuesta 1: Por KM
            total_km = rec.distance_km + rec.extra_km
            rec.proposal_km_total = total_km * rec.price_per_km

            # Propuesta 2: Por Viaje (costos / (1 - margen))
            factor = 1 - (rec.profit_margin_percent / 100)
            
            # Retención 4% solo si cliente es persona moral
            if rec.partner_invoice_id and rec.partner_invoice_id.is_company:
                factor -= 0.04
                
            if factor > 0:
                rec.proposal_trip_total = rec.cost_total_estimated / factor
            else:
                rec.proposal_trip_total = rec.cost_total_estimated

    # ============================================================
    # ACCIONES — PASO 1
    # ============================================================

    def action_calcular_ruta(self):
        """
        Llama a TollGuru para calcular distancia, duración y casetas.
        Adapta la lógica de tms_waybill._fetch_tollguru_api() para
        operar sin un waybill existente.
        """
        self.ensure_one()

        if not self.origin_zip or len(self.origin_zip) != 5:
            raise UserError(_("El CP Origen debe tener 5 dígitos."))
        if not self.dest_zip or len(self.dest_zip) != 5:
            raise UserError(_("El CP Destino debe tener 5 dígitos."))
        if self.num_axles < 2:
            raise UserError(_("El número de ejes debe ser al menos 2."))

        # Mapeo ejes → tipo vehículo TollGuru (igual que tms_waybill)
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
        vehicle_type = TOLLGURU_AXLES_MAP.get(self.num_axles, "5AxlesTruck")

        api_key = self.env['ir.config_parameter'].sudo().get_param('tms.tollguru_api_key')
        if not api_key:
            raise UserError(_("Falta configurar la TollGuru API Key en Ajustes TMS."))

        url = "https://apis.tollguru.com/toll/v2/origin-destination-waypoints"
        headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json',
        }
        payload = {
            "from": {"address": f"{self.origin_zip}, Mexico"},
            "to":   {"address": f"{self.dest_zip}, Mexico"},
            "vehicle": {
                "type": vehicle_type,
                "weight": {"value": 15000, "unit": "kg"},
                "axles": self.num_axles,
                "height": {"value": 4.5, "unit": "meter"},
            },
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                api_data = response.json()
                routes = api_data.get('routes', [])
                if not routes:
                    raise UserError(_("TollGuru no devolvió rutas para los CPs indicados."))

                route = routes[0]
                summary = route.get('summary', {})
                costs = route.get('costs', {})

                distance_m = summary.get('distance', {}).get('value', 0)
                duration_s = summary.get('duration', {}).get('value', 0)
                toll_cost = costs.get('tag', costs.get('cash', 0.0))

                self.write({
                    'distance_km': round(distance_m / 1000.0, 2),
                    'duration_hours': round(duration_s / 3600.0, 2),
                    'toll_cost': toll_cost,
                    'ruta_calculada': True,
                })
            else:
                _logger.error("TollGuru Error [%s]: %s", response.status_code, response.text)
                raise UserError(_("Error al consultar TollGuru (HTTP %s):\n%s") % (
                    response.status_code, response.text[:500]))
        except requests.exceptions.Timeout:
            raise UserError(_("Tiempo de espera agotado al conectar con TollGuru. Intenta nuevamente."))
        except UserError:
            raise
        except Exception as e:
            raise UserError(_("Error de conexión con TollGuru: %s") % str(e))

        # Reabrir el wizard en el mismo paso para mostrar resultados
        return self._reopen_wizard()

    def action_aprobar_propuesta(self):
        """
        Aprueba la propuesta seleccionada y avanza al Paso 2.
        """
        self.ensure_one()

        if not self.ruta_calculada:
            raise UserError(_("Primero calcula la ruta antes de aprobar una propuesta."))

        # Calcular el monto aprobado según la propuesta seleccionada
        if self.selected_proposal == 'km':
            approved = self.proposal_km_total
        elif self.selected_proposal == 'trip':
            approved = self.proposal_trip_total
        else:
            approved = self.direct_price

        if approved <= 0:
            raise UserError(_("El monto de la propuesta seleccionada debe ser mayor a $0.00."))

        self.write({
            'amount_approved': approved,
            'step': '2',
        })
        return self._reopen_wizard()

    def action_volver_paso1(self):
        """Regresa al Paso 1 sin perder los datos calculados."""
        self.ensure_one()
        self.write({'step': '1'})
        return self._reopen_wizard()

    # ============================================================
    # ACCIONES — PASO 2
    # ============================================================

    def action_crear_waybill(self):
        """
        Crea el tms.waybill en estado 'draft' con todos los datos
        capturados en ambos pasos del wizard.
        """
        self.ensure_one()

        # Validaciones básicas del Paso 2
        if not self.partner_invoice_id:
            raise UserError(_("Selecciona el Cliente de Facturación."))

        # Construir vals del waybill
        vals = {
            'company_id': self.company_id.id,
            'state': 'draft',
            'cp_type': self.cp_type,
            'waybill_type': 'income' if self.cp_type == 'ingreso' else 'transfer',
            # Ruta
            'origin_zip': self.origin_zip,
            'dest_zip': self.dest_zip,
            'distance_km': self.distance_km + self.extra_km,
            'duration_hours': self.duration_hours,
            # Costos
            'fuel_price_liter': self.fuel_price,
            'fuel_performance': self.fuel_performance,
            'cost_tolls': self.toll_cost,
            'cost_driver': self.cost_driver,
            'cost_maneuver': self.cost_maneuver,
            'cost_other': self.cost_other,
            'cost_commission': self.cost_commission,
            'profit_margin_percent': self.profit_margin_percent,
            'price_per_km': self.price_per_km,
            'proposal_direct_amount': self.direct_price,
            # Propuesta aprobada
            'selected_proposal': self.selected_proposal,
            'amount_untaxed': self.amount_approved,
            # Actores
            'partner_invoice_id': self.partner_invoice_id.id,
            'partner_origin_id': self.partner_origin_id.id if self.partner_origin_id else False,
            'origin_address': self.origin_address or False,
            'partner_dest_id': self.partner_dest_id.id if self.partner_dest_id else False,
            'dest_address': self.dest_address or False,
            # Unidad
            'vehicle_id': self.vehicle_id.id if self.vehicle_id else False,
            'driver_id': self.driver_id.id if self.driver_id else False,
            'require_trailer': self.require_trailer,
            'trailer1_id': self.trailer1_id.id if self.require_trailer and self.trailer1_id else False,
            'dolly_id': self.dolly_id.id if self.require_trailer and self.dolly_id else False,
            'trailer2_id': self.trailer2_id.id if self.require_trailer and self.trailer2_id else False,
        }

        # Líneas de mercancía
        line_vals = []
        for line in self.line_ids:
            line_vals.append((0, 0, {
                'product_sat_id': line.product_sat_id.id if line.product_sat_id else False,
                'description': line.description,
                'quantity': line.quantity,
                'uom_sat_id': line.uom_sat_id.id if line.uom_sat_id else False,
                'weight_kg': line.weight_kg,
                'is_dangerous': line.is_dangerous,
                'material_peligroso_id': line.material_peligroso_id.id if line.material_peligroso_id else False,
                'embalaje_id': line.embalaje_id.id if line.embalaje_id else False,
                'sec_cofepris': line.sec_cofepris,
                'ing_activo': line.ing_activo,
            }))
        if line_vals:
            vals['line_ids'] = line_vals

        waybill = self.env['tms.waybill'].create(vals)

        # Abrir el waybill recién creado
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tms.waybill',
            'res_id': waybill.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ============================================================
    # HELPERS
    # ============================================================

    def _reopen_wizard(self):
        """Retorna la acción para reabrir el wizard en su estado actual."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tms.cotizacion.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class TmsCotizacionWizardLine(models.TransientModel):
    """
    Líneas de mercancía temporales del Wizard de Cotización.
    Se crearán como tms.waybill.line al crear el viaje.
    """

    _name = 'tms.cotizacion.wizard.line'
    _description = 'Línea de Mercancía — Wizard Cotización'
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        'tms.cotizacion.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )

    sequence = fields.Integer(string='Secuencia', default=10)

    product_sat_id = fields.Many2one(
        'tms.sat.clave.prod',
        string='Clave SAT',
    )

    description = fields.Char(
        string='Descripción',
        required=True,
    )

    quantity = fields.Float(
        string='Cantidad',
        digits=(10, 3),
        default=1.0,
    )

    uom_sat_id = fields.Many2one(
        'tms.sat.clave.unidad',
        string='Unidad SAT',
        default=lambda self: self.env['tms.sat.clave.unidad'].search([('code', '=', 'KGM')], limit=1),
    )

    weight_kg = fields.Float(
        string='Peso (Kg)',
        digits=(10, 3),
        default=0.0,
    )

    is_dangerous = fields.Boolean(
        string='Material Peligroso',
        default=False,
    )

    material_peligroso_id = fields.Many2one(
        'tms.sat.material.peligroso',
        string='Cve. Material Peligroso',
    )

    embalaje_id = fields.Many2one(
        'tms.sat.embalaje',
        string='Cve. Embalaje',
    )

    sec_cofepris = fields.Char(
        string='Sector COFEPRIS',
    )

    ing_activo = fields.Char(
        string='Ingrediente Activo',
    )
