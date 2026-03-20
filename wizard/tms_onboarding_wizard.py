# -*- coding: utf-8 -*-
"""
Wizard de Onboarding TMS — Configuración Inicial en 6 Pasos.
Guía al usuario nuevo hasta dejar el sistema listo para crear su primer viaje.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError


class TmsOnboardingWizard(models.TransientModel):
    """
    Wizard de onboarding para configuración inicial del TMS.
    Guía al usuario nuevo en 6 pasos hasta crear su primer viaje.
    """
    _name = 'tms.onboarding.wizard'
    _description = 'Onboarding TMS - Configuración Inicial'

    # --- Control del wizard ---
    step = fields.Integer(
        string='Paso actual',
        default=1,
        help='Controla en qué paso del onboarding está el usuario'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        default=lambda self: self.env.company,
        required=True,
    )

    # --- Paso 1: Empresa ---
    company_name = fields.Char(
        string='Nombre de la empresa',
        help='Razón social como aparece en el SAT'
    )
    company_rfc = fields.Char(
        string='RFC',
        size=13,
        help='RFC del emisor (12 o 13 caracteres)'
    )
    company_logo = fields.Binary(
        string='Logo de la empresa',
        help='Logo que aparecerá en documentos y Carta Porte'
    )
    csd_cer_file = fields.Binary(
        string='Archivo CSD (.cer)',
        help='Certificado de Sello Digital del SAT'
    )
    csd_cer_filename = fields.Char(string='Nombre archivo .cer')
    csd_key_file = fields.Binary(
        string='Archivo CSD (.key)',
        help='Llave privada del Certificado de Sello Digital'
    )
    csd_key_filename = fields.Char(string='Nombre archivo .key')
    csd_password = fields.Char(
        string='Contraseña CSD',
        help='Contraseña de la llave privada del CSD'
    )
    regimen_fiscal_id = fields.Many2one(
        'tms.sat.regimen.fiscal',
        string='Régimen Fiscal',
        help='Régimen fiscal SAT de la empresa. Catálogo c_RegimenFiscal.'
    )
    company_street = fields.Char(
        string='Calle y número',
        help='Dirección fiscal de la empresa para reportes PDF'
    )
    company_zip = fields.Char(
        string='Código Postal',
        size=5,
        default=lambda self: self.env.company.zip or '',
        help='CP fiscal de la empresa. Se usa en LugarExpedicion del CFDI '
             'y en los reportes PDF.'
    )
    company_state_id = fields.Many2one(
        'res.country.state',
        string='Estado',
        domain="[('country_id.code', '=', 'MX')]",
        help='Estado de la república para dirección fiscal'
    )

    # --- Paso 2: Vehículo ---
    vehicle_name = fields.Char(
        string='Nombre del vehículo',
        help='Ej: Kenworth T680 2022, Freightliner Cascadia'
    )
    vehicle_plate = fields.Char(
        string='Placas',
        help='Placas del tracto/camión'
    )
    vehicle_year = fields.Char(
        string='Año/Modelo',
        size=4,
        help='Año del modelo del vehículo'
    )
    vehicle_config_id = fields.Many2one(
        'tms.sat.config.autotransporte',
        string='Configuración vehicular SCT',
        help='Tipo de configuración según catálogo SAT (ej: C2, C3, T3S2)'
    )
    vehicle_permit_type_id = fields.Many2one(
        'tms.sat.tipo.permiso',
        string='Tipo de permiso SCT',
        help='Tipo de permiso SCT del vehículo'
    )
    vehicle_permit_number = fields.Char(
        string='Número de permiso SCT',
        help='Número del permiso SCT vigente'
    )
    has_trailer = fields.Boolean(
        string='¿Tiene remolque?',
        default=False,
    )
    trailer_name = fields.Char(string='Nombre del remolque')
    trailer_plate = fields.Char(string='Placas del remolque')
    trailer_sub_type = fields.Many2one(
        'tms.sat.config.autotransporte',
        string='Subtipo remolque SCT',
        help='Configuración del remolque según catálogo SAT'
    )
    has_dolly = fields.Boolean(
        string='¿Tiene dolly?',
        default=False,
    )
    dolly_name = fields.Char(string='Nombre del dolly')
    dolly_plate = fields.Char(string='Placas del dolly')

    # --- Paso 3: Seguros ---
    insurance_rc_company = fields.Char(
        string='Aseguradora RC',
        help='Nombre de la aseguradora de Responsabilidad Civil'
    )
    insurance_rc_policy = fields.Char(
        string='Póliza RC',
        help='Número de póliza de Responsabilidad Civil'
    )
    insurance_rc_expiry = fields.Date(
        string='Vigencia RC',
        help='Fecha de vencimiento de la póliza RC'
    )
    insurance_cargo_company = fields.Char(
        string='Aseguradora Carga',
        help='Nombre de la aseguradora de la carga'
    )
    insurance_cargo_policy = fields.Char(
        string='Póliza Carga',
        help='Número de póliza de seguro de carga'
    )
    insurance_cargo_expiry = fields.Date(
        string='Vigencia Carga',
        help='Fecha de vencimiento del seguro de carga'
    )
    insurance_env_company = fields.Char(
        string='Aseguradora Ambiental',
        help='Solo requerido si transportas materiales peligrosos'
    )
    insurance_env_policy = fields.Char(string='Póliza Ambiental')
    insurance_env_expiry = fields.Date(string='Vigencia Ambiental')

    # --- Paso 4: Chofer ---
    driver_name = fields.Char(
        string='Nombre del chofer',
        help='Nombre completo del operador'
    )
    driver_rfc = fields.Char(
        string='RFC del chofer',
        size=13,
    )
    driver_curp = fields.Char(
        string='CURP del chofer',
        size=18,
    )
    driver_license_number = fields.Char(
        string='Número de licencia federal',
        help='Número de la licencia federal de conducir'
    )
    driver_license_type = fields.Selection(
        selection=[
            ('A', 'Tipo A - Vehículos ligeros'),
            ('B', 'Tipo B - Vehículos pesados'),
            ('C', 'Tipo C - Doble articulado'),
            ('D', 'Tipo D - Materiales peligrosos'),
            ('E', 'Tipo E - Doble articulado + peligrosos'),
        ],
        string='Tipo de licencia',
        help='Tipo de licencia federal de conducir SCT'
    )
    driver_license_expiry = fields.Date(
        string='Vigencia licencia',
        help='Fecha de vencimiento de la licencia federal'
    )

    # --- Paso 5: Primer cliente ---
    client_name = fields.Char(
        string='Nombre o razón social del cliente',
        help='Nombre del primer cliente al que le vas a facturar'
    )
    client_rfc = fields.Char(
        string='RFC del cliente',
        size=13,
        help='RFC para facturación'
    )
    client_email = fields.Char(
        string='Email del cliente',
        help='Email para envío de facturas y Carta Porte'
    )
    client_phone = fields.Char(string='Teléfono del cliente')
    client_street = fields.Char(string='Calle y número')
    client_city = fields.Char(string='Ciudad')
    client_state_id = fields.Many2one(
        'res.country.state',
        string='Estado',
        domain="[('country_id.code', '=', 'MX')]",
    )
    client_zip = fields.Char(string='Código Postal', size=5)
    client_is_company = fields.Boolean(
        string='¿Es persona moral?',
        default=True,
        help='Marca si el cliente es empresa (persona moral). Afecta la retención de IVA 4%.'
    )

    # --- Paso 6: Resumen (campos computed) ---
    summary_company = fields.Char(
        string='Empresa configurada',
        compute='_compute_summary',
    )
    summary_vehicle = fields.Char(
        string='Vehículo configurado',
        compute='_compute_summary',
    )
    summary_driver = fields.Char(
        string='Chofer configurado',
        compute='_compute_summary',
    )
    summary_client = fields.Char(
        string='Cliente configurado',
        compute='_compute_summary',
    )
    summary_insurance = fields.Char(
        string='Seguros configurados',
        compute='_compute_summary',
    )

    @api.depends('company_name', 'vehicle_name', 'driver_name',
                 'client_name', 'insurance_rc_policy',
                 'insurance_cargo_policy', 'insurance_env_policy')
    def _compute_summary(self):
        """Calcula el texto de resumen para el paso 6."""
        for rec in self:
            rec.summary_company = rec.company_name or 'Sin configurar'
            rec.summary_vehicle = rec.vehicle_name or 'Sin configurar'
            rec.summary_driver = rec.driver_name or 'Sin configurar'
            rec.summary_client = rec.client_name or 'Sin configurar'
            count = sum([
                bool(rec.insurance_rc_policy),
                bool(rec.insurance_cargo_policy),
                bool(rec.insurance_env_policy),
            ])
            rec.summary_insurance = f'{count}/3 seguros configurados'

    # ============================================================
    # NAVEGACIÓN
    # ============================================================

    def action_next_step(self):
        """Avanza al siguiente paso del wizard."""
        self.ensure_one()
        if self.step < 6:
            self.step += 1
        return self._reopen_wizard()

    def action_prev_step(self):
        """Regresa al paso anterior del wizard."""
        self.ensure_one()
        if self.step > 1:
            self.step -= 1
        return self._reopen_wizard()

    def _reopen_wizard(self):
        """Reabre el wizard en el paso actual."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tms.onboarding.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ============================================================
    # GUARDADO POR PASO
    # ============================================================

    def action_save_step_1(self):
        """Guarda datos de empresa en res.company: RFC, logo, régimen fiscal y archivos CSD."""
        self.ensure_one()
        company = self.company_id
        vals = {}
        if self.company_name:
            vals['name'] = self.company_name
        if self.company_rfc:
            vals['vat'] = self.company_rfc
        if self.company_logo:
            vals['logo'] = self.company_logo
        if self.regimen_fiscal_id:
            vals['tms_regimen_fiscal_id'] = self.regimen_fiscal_id.id
        if self.csd_cer_file:
            vals['tms_csd_cer'] = self.csd_cer_file
        if self.csd_key_file:
            vals['tms_csd_key'] = self.csd_key_file
        if self.csd_password:
            vals['tms_csd_password'] = self.csd_password
        # País México por defecto (requerido para CFDI y Carta Porte)
        mx = self.env.ref('base.mx', raise_if_not_found=False)
        if mx:
            vals['country_id'] = mx.id
        # Moneda MXN por defecto
        mxn = self.env.ref('base.MXN', raise_if_not_found=False)
        if mxn:
            vals['currency_id'] = mxn.id
        # Dirección fiscal — se escribe en company para que Bloque A la propague a partner_id
        if self.company_street:
            vals['street'] = self.company_street
        if self.company_zip:
            vals['zip'] = self.company_zip
        if self.company_state_id:
            vals['state_id'] = self.company_state_id.id
        if vals:
            company.write(vals)

            # ── Bloque A: Sincronizar partner asociado a la empresa ──
            # Los reportes PDF (external_layout) usan partner_id para nombre, RFC, dirección.
            # res.company usa _inherits pero Odoo 19 no siempre propaga todos los campos.
            if company.partner_id:
                partner_vals = {
                    'name': company.name,
                    'country_id': company.country_id.id,
                    'city': company.city,
                    'zip': company.zip,
                }
                if company.state_id:
                    partner_vals['state_id'] = company.state_id.id
                if company.street:
                    partner_vals['street'] = company.street
                if company.phone:
                    partner_vals['phone'] = company.phone
                if company.email:
                    partner_vals['email'] = company.email
                if company.vat:
                    partner_vals['vat'] = company.vat
                company.partner_id.write(partner_vals)

            # ── Bloque B: Limpiar company_details ──
            # El campo company_details puede tener datos del setup inicial incorrectos
            # (nombre de empresa viejo, país incorrecto, etc.).
            # Vaciarlo forza al external_layout a leer partner_id directamente,
            # donde Bloque A ya escribió los datos correctos.
            company.write({'company_details': False})

        return self.action_next_step()

    def _get_or_create_vehicle_model(self, name):
        """
        Busca o crea un fleet.vehicle.model con el nombre dado.
        fleet.vehicle.model requiere brand_id (fleet.vehicle.model.brand).
        Busca o crea también la marca genérica 'TMS' (idempotente, no toca catálogos SAT).
        """
        # CORRECTO: el modelo de marca se llama 'fleet.vehicle.model.brand' (no 'fleet.vehicle.brand')
        Brand = self.env['fleet.vehicle.model.brand']
        Model = self.env['fleet.vehicle.model']

        # Buscar o crear marca genérica TMS (una sola, compartida entre todas las unidades)
        brand = Brand.search([('name', '=', 'TMS')], limit=1)
        if not brand:
            brand = Brand.create({'name': 'TMS'})

        # Buscar o crear modelo con ese nombre bajo la marca TMS
        model = Model.search([
            ('name', '=', name),
            ('brand_id', '=', brand.id)
        ], limit=1)
        if not model:
            model = Model.create({
                'name': name,
                'brand_id': brand.id,
            })
        return model

    def _get_vehicle_type(self, xml_ref, is_trailer):
        """
        Retorna el tms.vehicle.type indicado por xml_ref.
        Si no existe, hace fallback al primer tipo disponible con el is_trailer indicado.
        Esto garantiza que tms_vehicle_type_id (required=True) siempre tenga valor.
        """
        vtype = self.env.ref(xml_ref, raise_if_not_found=False)
        if not vtype:
            # Fallback: buscar primer tipo con la clasificación correcta
            vtype = self.env['tms.vehicle.type'].search(
                [('is_trailer', '=', is_trailer)], limit=1
            )
        return vtype

    def action_save_step_2(self):
        """Crea el vehículo principal (tracto) y opcionalmente remolque y dolly en fleet.vehicle."""
        self.ensure_one()
        Vehicle = self.env['fleet.vehicle']
        if self.vehicle_name:
            tractor_type = self._get_vehicle_type('tms.tms_vehicle_type_tractor', False)
            # 'name' es campo computed en fleet.vehicle → no incluir en vals (se genera automáticamente)
            # 'no_economico' captura el nombre descriptivo ingresado por el usuario
            tracto_vals = {
                'no_economico': self.vehicle_name,
                'model_id': self._get_or_create_vehicle_model(self.vehicle_name).id,
                'license_plate': self.vehicle_plate or '',
                'company_id': self.company_id.id,
            }
            # model_year es Selection → solo incluir si hay valor ('' es inválido)
            if self.vehicle_year:
                tracto_vals['model_year'] = self.vehicle_year
            if tractor_type:
                tracto_vals['tms_vehicle_type_id'] = tractor_type.id
            if self.vehicle_config_id:
                tracto_vals['sat_config_id'] = self.vehicle_config_id.id
            if self.vehicle_permit_type_id:
                tracto_vals['sat_permiso_sct_id'] = self.vehicle_permit_type_id.id
            if self.vehicle_permit_number:
                tracto_vals['permiso_sct_number'] = self.vehicle_permit_number
            Vehicle.create(tracto_vals)
        if self.has_trailer and self.trailer_name:
            trailer_type = self._get_vehicle_type('tms.tms_vehicle_type_trailer', True)
            trailer_vals = {
                'no_economico': self.trailer_name,
                'model_id': self._get_or_create_vehicle_model(self.trailer_name).id,
                'license_plate': self.trailer_plate or '',
                'company_id': self.company_id.id,
            }
            if trailer_type:
                trailer_vals['tms_vehicle_type_id'] = trailer_type.id
            if self.trailer_sub_type:
                trailer_vals['sat_config_id'] = self.trailer_sub_type.id
            Vehicle.create(trailer_vals)
        if self.has_dolly and self.dolly_name:
            dolly_type = self._get_vehicle_type('tms.tms_vehicle_type_dolly', True)
            dolly_vals = {
                'no_economico': self.dolly_name,
                'model_id': self._get_or_create_vehicle_model(self.dolly_name).id,
                'license_plate': self.dolly_plate or '',
                'company_id': self.company_id.id,
            }
            if dolly_type:
                dolly_vals['tms_vehicle_type_id'] = dolly_type.id
            Vehicle.create(dolly_vals)
        return self.action_next_step()

    def action_save_step_3(self):
        """Guarda datos de seguros RC, Carga y Ambiental en res.company."""
        self.ensure_one()
        company = self.company_id
        vals = {}
        if self.insurance_rc_company:
            vals['tms_insurance_rc_company'] = self.insurance_rc_company
        if self.insurance_rc_policy:
            vals['tms_insurance_rc_policy'] = self.insurance_rc_policy
        if self.insurance_rc_expiry:
            vals['tms_insurance_rc_expiry'] = self.insurance_rc_expiry
        if self.insurance_cargo_company:
            vals['tms_insurance_cargo_company'] = self.insurance_cargo_company
        if self.insurance_cargo_policy:
            vals['tms_insurance_cargo_policy'] = self.insurance_cargo_policy
        if self.insurance_cargo_expiry:
            vals['tms_insurance_cargo_expiry'] = self.insurance_cargo_expiry
        if self.insurance_env_company:
            vals['tms_insurance_env_company'] = self.insurance_env_company
        if self.insurance_env_policy:
            vals['tms_insurance_env_policy'] = self.insurance_env_policy
        if self.insurance_env_expiry:
            vals['tms_insurance_env_expiry'] = self.insurance_env_expiry
        if vals:
            company.write(vals)
        return self.action_next_step()

    def action_save_step_4(self):
        """Crea el chofer como hr.employee con datos de licencia federal."""
        self.ensure_one()
        if self.driver_name:
            emp_vals = {
                'name': self.driver_name,
                'company_id': self.company_id.id,
            }
            if self.driver_rfc:
                emp_vals['tms_rfc'] = self.driver_rfc
            if self.driver_curp:
                emp_vals['tms_curp'] = self.driver_curp
            if self.driver_license_number:
                emp_vals['tms_license_number'] = self.driver_license_number
            if self.driver_license_type:
                emp_vals['tms_license_type'] = self.driver_license_type
            if self.driver_license_expiry:
                emp_vals['tms_license_expiry'] = self.driver_license_expiry
            self.env['hr.employee'].create(emp_vals)
        return self.action_next_step()

    def action_save_step_5(self):
        """Crea el primer cliente como res.partner. País siempre México."""
        self.ensure_one()
        if self.client_name:
            partner_vals = {
                'name': self.client_name,
                'is_company': self.client_is_company,
                'company_type': 'company' if self.client_is_company else 'person',
            }
            if self.client_rfc:
                partner_vals['vat'] = self.client_rfc
            if self.client_email:
                partner_vals['email'] = self.client_email
            if self.client_phone:
                partner_vals['phone'] = self.client_phone
            if self.client_street:
                partner_vals['street'] = self.client_street
            if self.client_city:
                partner_vals['city'] = self.client_city
            if self.client_state_id:
                partner_vals['state_id'] = self.client_state_id.id
            if self.client_zip:
                partner_vals['zip'] = self.client_zip
            mx = self.env.ref('base.mx', raise_if_not_found=False)
            if mx:
                partner_vals['country_id'] = mx.id
            self.env['res.partner'].create(partner_vals)
        return self.action_next_step()

    def action_create_first_trip(self):
        """Cierra el onboarding y abre el wizard de cotización para crear el primer viaje."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tms.cotizacion.wizard',
            'view_mode': 'form',
            'target': 'new',
            'name': '¡Crea tu primer viaje!',
        }
