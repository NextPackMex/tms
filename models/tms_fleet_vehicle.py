# -*- coding: utf-8 -*-

# Importamos las clases necesarias de Odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FleetVehicle(models.Model):
    """
    EXTENSIÓN del modelo nativo fleet.vehicle de Odoo.

    VENTAJAS DE HEREDAR EN LUGAR DE CREAR MODELO NUEVO:
    1. Aprovechamos TODO el módulo Fleet nativo:
       - Gestión de mantenimiento (fleet.vehicle.log.services)
       - Costos y contratos (fleet.vehicle.log.contract)
       - Odómetro y combustible
       - Reportes nativos

    2. No duplicamos funcionalidad que Odoo ya tiene

    3. Los usuarios que ya conocen Fleet se sienten cómodos

    ARQUITECTURA:
    - NO usamos _name (porque no creamos tabla nueva)
    - Usamos _inherit para EXTENDER la tabla existente fleet_vehicle
    - Los campos que agregamos aquí se añaden a la tabla fleet_vehicle
    """

    # _inherit: Extendemos el modelo nativo de Fleet
    # Esto AGREGA campos a la tabla existente, NO crea tabla nueva
    _inherit = 'fleet.vehicle'

    # ============================================================
    # ASEGURAMIENTO SAAS: company_id OBLIGATORIO
    # ============================================================
    # El módulo fleet nativo SÍ tiene company_id, pero lo hacemos explícitamente obligatorio
    # para asegurar que TODOS los vehículos pertenezcan a una empresa

    # Sobrescribimos company_id para forzar que sea obligatorio
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,                              # OBLIGATORIO para SaaS
        default=lambda self: self.env.company,      # Compañía del usuario actual
        help='Compañía propietaria del vehículo (CRÍTICO para multi-empresa)'
    )

    # ============================================================
    # ASEGURAMIENTO SAAS: Company ID Obligatorio
    # ============================================================
    # CRÍTICO: Asegura que cada vehículo pertenezca a una empresa
    # Esto permite aislamiento de datos en sistemas multi-empresa

    # Sobrescribimos el campo company_id del módulo Fleet para hacerlo requerido
    # Si el módulo nativo no lo requiere, lo hacemos obligatorio aquí


    # ============================================================
    # CAMPO PRINCIPAL: Diferenciador Tractor vs Remolque
    # ============================================================

    # Boolean: define si este vehículo es un remolque o un tractor
    # CLAVE DE ARQUITECTURA: Con un solo modelo manejamos ambos tipos
    # Identificador de Tipo de Vehículo (Tractor vs Remolque vs Dolly vs Otros)
    tms_vehicle_type_id = fields.Many2one(
        'tms.vehicle.type',
        string="Tipo Vehículo TMS",
        required=True,
        tracking=True,
        help="Define el tipo de vehículo y su comportamiento (si es remolque, motorizado, etc.)"
    )

    # Boolean: define si este vehículo es un remolque
    tms_is_trailer = fields.Boolean(
        string='Es Remolque',
        compute='_compute_vehicle_type_props',
        store=True,
        readonly=False,
        help='Marcar si este vehículo es un remolque/semirremolque.'
    )

    # Boolean: define si este vehículo PUEDE LLEVAR remolque (Tractocamión)
    # Antes se llamaba is_trailer "Es Remolque", ahora SEMÁNTICAMENTE es "Lleva Remolque"
    # Mantenemos el nombre técnico para minimizar breaking changes en Odoo Fleet,
    # pero cambiamos su significado en el contexto de TMS.
    is_trailer = fields.Boolean(
        string='Es Tractocamión',
        compute='_compute_vehicle_type_props',
        store=True,
        readonly=False,
        help='Marcar si este vehículo es un Tractocamión (puede llevar remolques).'
    )

    tms_num_axles = fields.Integer(
        string='Número de Ejes',
        default=0,
        help='Número de ejes de esta unidad (tracto o remolque)',
    )

    tms_fuel_performance = fields.Float(
        string='Rendimiento (Km/L)',
        default=2.5,
        help='Km por litro del vehículo',
    )



    @api.depends('tms_vehicle_type_id', 'tms_vehicle_type_id.is_trailer', 'tms_vehicle_type_id.is_motorized')
    def _compute_vehicle_type_props(self):
        for rec in self:
            if rec.tms_vehicle_type_id:
                # Si es tipo Remolque -> tms_is_trailer = True
                rec.tms_is_trailer = rec.tms_vehicle_type_id.is_trailer

                # Si es Motorizado (Tracto) -> Lleva Remolque (is_trailer) = True
                # (Asumimos por defecto que si es motorizado puede llevar remolque, user puede desmarcar)
                rec.is_trailer = rec.tms_vehicle_type_id.is_motorized
            else:
                # Defaults si no hay tipo
                if not rec.tms_is_trailer:
                    rec.tms_is_trailer = False
                if not rec.is_trailer:
                     rec.is_trailer = False

    # ============================================================
    # CAMPOS GENERALES (Tractor Y Remolque)
    # ============================================================

    # Char: número económico (identificador interno de la empresa)
    # Ejemplo: "ECO-001", "UNIDAD-42", etc.
    no_economico = fields.Char(
        string='No. Económico',
        help='Número de identificación interna del vehículo en la empresa'
    )
    _no_economico_idx = models.Index("(company_id, no_economico)")

    # Many2one: configuración vehicular según catálogo SAT
    # Ejemplos: C2, C3, T3S2, T3S3, etc.
    sat_config_id = fields.Many2one(
        'tms.sat.config.autotransporte',
        string='Configuración SAT',
        help='Configuración vehicular según catálogo c_ConfigAutotransporte del SAT'
    )

    # Integer: ejes totales (relacionado para mostrar)
    num_axles = fields.Integer(
        string='No. Ejes',
        related='sat_config_id.total_axles',
        readonly=True,
        store=True,
        help='Número total de ejes tomado de la configuración SAT'
    )

    # Many2one: tipo de permiso SCT
    # Solo aplica para tractocamiones (no para remolques)
    sat_permiso_sct_id = fields.Many2one(
        'tms.sat.tipo.permiso',
        string='Tipo de Permiso SCT',
        help='Tipo de permiso SCT según catálogo c_TipoPermiso'
    )

    # Char: número del permiso SCT
    permiso_sct_number = fields.Char(
        string='Número de Permiso SCT',
        help='Número del permiso otorgado por la SCT'
    )

    # ============================================================
    # CAMPOS DE SEGURO (para Carta Porte)
    # ============================================================
    # NOTA: Odoo Fleet ya tiene fleet.vehicle.log.contract para contratos/seguros
    # pero para Carta Porte necesitamos campos rápidos accesibles e impresos en el XML

    # 1. RESPONSABILIDAD CIVIL (Obligatorio)
    tms_insurance_civil_liability = fields.Char(
        string='Póliza Resp. Civil',
        help='Número de Póliza de Responsabilidad Civil (Obligatorio)',
        tracking=True,
        default=lambda self: self.env.company.tms_def_insurance_civil_liability
    )
    tms_insurance_civil_liability_mx = fields.Char(
        string='Aseguradora Resp. Civil',
        help='Nombre de la Aseguradora de Responsabilidad Civil',
        tracking=True,
        default=lambda self: self.env.company.tms_def_insurance_civil_liability_mx
    )

    # 2. MEDIO AMBIENTE (Obligatorio para Materiales Peligrosos)
    tms_insurance_environmental = fields.Char(
        string='Póliza Medio Ambiente',
        help='Número de Póliza de Medio Ambiente (Req. Material Peligroso)',
        tracking=True,
        default=lambda self: self.env.company.tms_def_insurance_environmental
    )
    tms_insurance_environmental_mx = fields.Char(
        string='Aseguradora Medio Ambiente',
        help='Nombre de la Aseguradora de Medio Ambiente',
        tracking=True,
        default=lambda self: self.env.company.tms_def_insurance_environmental_mx
    )

    # 3. CARGA (Opcional pero recomendado)
    tms_insurance_cargo = fields.Char(
        string='Póliza Carga',
        help='Número de Póliza de Seguro de Carga',
        tracking=True,
        default=lambda self: self.env.company.tms_def_insurance_cargo
    )
    tms_insurance_cargo_mx = fields.Char(
        string='Aseguradora Carga',
        help='Nombre de la Aseguradora de Carga',
        tracking=True,
        default=lambda self: self.env.company.tms_def_insurance_cargo_mx
    )

    # Peso Bruto Vehicular (Requerido para algunos reportes)
    tms_gross_vehicle_weight = fields.Float(
        string='Peso Bruto Vehicular (Ton)',
        help='Peso bruto vehicular en toneladas (Configuración Vehicular)',
        tracking=True
    )

    # ============================================================
    # CAMPOS ESPECÍFICOS PARA REMOLQUES
    # ============================================================



    # ============================================================
    # CAMPOS ESPECÍFICOS PARA TRACTOCAMIONES (no remolques)
    # ============================================================

    # Many2one: remolque 1 asignado a este tractor
    # Domain: solo remolques DE LA MISMA EMPRESA y que sean ES REMOLQUE
    trailer1_id = fields.Many2one(
        'fleet.vehicle',
        string='Remolque 1',
        domain="[('tms_is_trailer', '=', True), ('company_id', '=', company_id)]",
        help='Primer remolque asignado a este tractocamión (debe ser de la misma empresa)'
    )

    # Many2one: remolque 2 (para doble remolque)
    # Domain: solo remolques DE LA MISMA EMPRESA
    trailer2_id = fields.Many2one(
        'fleet.vehicle',
        string='Remolque 2',
        domain="[('tms_is_trailer', '=', True), ('company_id', '=', company_id)]",
        help='Segundo remolque (para configuraciones de doble remolque - misma empresa)'
    )



    # ============================================================
    # CAMPOS COMPUTADOS
    # ============================================================

    # Char: nombre completo del vehículo
    # Sobrescribimos el compute para mostrar formato personalizado
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('no_economico', 'license_plate', 'model_id', 'tms_is_trailer')
    def _compute_display_name(self):
        """
        Calcula un nombre descriptivo del vehículo.

        Formato:
        - Tractor: "[ECO-001] Volvo FH16 - ABC123"
        - Remolque: "[REM-001] Remolque Caja Seca - XYZ789"
        """
        for vehicle in self:
            # Lista de partes del nombre
            parts = []

            # Agregar No. Económico si existe
            if vehicle.no_economico:
                parts.append(f"[{vehicle.no_economico}]")

            # Agregar modelo si existe
            if vehicle.model_id:
                parts.append(vehicle.model_id.name)
            elif vehicle.tms_is_trailer:
                parts.append("Remolque")
            else:
                parts.append("Tractocamión")

            # Agregar placas si existen
            if vehicle.license_plate:
                parts.append(f"- {vehicle.license_plate}")

            # Unimos las partes con espacios
            vehicle.display_name = ' '.join(parts) if parts else 'Vehículo Sin Nombre'

    # ============================================================
    # VALIDACIONES
    # ============================================================

    @api.constrains('trailer1_id', 'trailer2_id')
    def _check_trailers(self):
        """
        Valida que un tractor no se asigne a sí mismo como remolque.
        Valida que no se asigne el mismo remolque dos veces.
        """
        for vehicle in self:
            # Solo validar si NO es remolque (si es remolque no debe tener campos, pero por seguridad)
            if not vehicle.tms_is_trailer:
                # Validación 1: No puede ser su propio remolque
                if vehicle.trailer1_id == vehicle or vehicle.trailer2_id == vehicle:
                    raise ValidationError(
                        _('Un vehículo no puede asignarse a sí mismo como remolque.')
                    )

                # Validación 2: No puede tener el mismo remolque dos veces
                if vehicle.trailer1_id and vehicle.trailer2_id:
                    if vehicle.trailer1_id == vehicle.trailer2_id:
                        raise ValidationError(
                            _('No puede asignar el mismo remolque en ambas posiciones.')
                        )

    def validate_carta_porte_compliance(self):
        """
        Valida que el vehículo cumpla con los requisitos para Carta Porte 3.1.
        Retorna una lista de errores (strings) si falta algo.
        """
        self.ensure_one()
        errors = []
        prefix = f"Vehículo {self.display_name}:"

        if not self.license_plate:
            errors.append(f"{prefix} Falta la Placa (PlacaVM).")
        
        if not self.model_year:
            errors.append(f"{prefix} Falta el Año del Modelo (AnioModeloVM).")

        if not self.tms_is_trailer:
            # Validaciones para TRACTOR (Autotransporte)
            if not self.sat_config_id:
                errors.append(f"{prefix} Falta Configuración Vehicular (C_ConfigAutotransporte).")
            
            if not self.sat_permiso_sct_id:
                errors.append(f"{prefix} Falta Tipo de Permiso SCT (PermisoSCT).")
            
            if not self.permiso_sct_number:
                errors.append(f"{prefix} Falta Número de Permiso SCT (NumPermisoSCT).")
            
            # Seguros obligatorios para circular
            if not self.tms_insurance_civil_liability or not self.tms_insurance_civil_liability_mx:
                errors.append(f"{prefix} Falta Póliza o Aseguradora de Responsabilidad Civil.")
        else:
             # Validaciones para REMOLQUE
             if not self.sat_config_id:
                  errors.append(f"{prefix} Falta Configuración Vehicular de Remolque (SubTipoRem).")
        
        return errors

    # ============================================================
    # MÉTODOS ONCHANGE
    # ============================================================

    @api.constrains('tms_is_trailer', 'is_trailer')
    def _check_mutually_exclusive_type(self):
        for rec in self:
            if rec.tms_is_trailer and rec.is_trailer:
                raise ValidationError(_("Un vehículo no puede ser 'Remolque' y 'Lleva Remolque' al mismo tiempo."))

    @api.onchange('tms_is_trailer')
    def _onchange_tms_is_trailer(self):
        """
        Si es remolque, limpia campos de tractor.
        """
        if self.tms_is_trailer:
            self.is_trailer = False # No puede llevar remolque
            self.trailer1_id = False
            self.trailer2_id = False
            self.tms_fuel_performance = 0.0

    @api.onchange('is_trailer')
    def _onchange_is_trailer(self):
        """
        Si lleva remolque (Tracto), no puede ser remolque.
        """
        if self.is_trailer:
            self.tms_is_trailer = False

    # ============================================================
    # MÉTODOS DE ACCIÓN (Botones en la Interfaz)
    # ============================================================

    def action_view_services(self):
        """
        Abre los servicios/mantenimientos del vehículo.

        IMPORTANTE: Este método aprovecha el módulo NATIVO de Fleet.
        fleet.vehicle.log.services ya existe en Odoo estándar.
        NO necesitamos crear un modelo nuevo de mantenimiento.

        :return: acción de ventana para mostrar servicios
        """
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': f'Mantenimiento - {self.display_name}',
            'res_model': 'fleet.vehicle.log.services',  # Modelo NATIVO de Odoo
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {
                'default_vehicle_id': self.id,
                'default_amount': 0.0,
            },
        }

