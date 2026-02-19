from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tms_use_google_maps = fields.Boolean(string="Integración con Mapas", config_parameter='tms.use_google_maps')
    tms_google_maps_api_key = fields.Char(string="Google Maps API Key", config_parameter='tms.google_maps_api_key')
    tms_tollguru_api_key = fields.Char(string="TollGuru API Key", config_parameter='tms.tollguru_api_key')
    tms_tollguru_debug = fields.Boolean(
        string='Debug TollGuru (Log respuestas API)',
        config_parameter='tms.tollguru_debug',
        help='Activa logs detallados de TollGuru en el servidor. Desactivar en producción.'
    )
    tms_route_provider = fields.Selection([
        ('std', 'Manual / Estándar'),
        ('google', 'Google Maps API'),
        ('tollguru', 'TollGuru'),
    ], string="Proveedor de Rutas", default='std', config_parameter='tms.route_provider')

    # ============================================================
    # SEGUROS DEFAULT (Relacionados a res.company)
    # ============================================================
    tms_def_insurance_civil_liability = fields.Char(related='company_id.tms_def_insurance_civil_liability', readonly=False, string="Póliza")
    tms_def_insurance_civil_liability_mx = fields.Char(related='company_id.tms_def_insurance_civil_liability_mx', readonly=False, string="Aseguradora")

    tms_def_insurance_environmental = fields.Char(related='company_id.tms_def_insurance_environmental', readonly=False, string="Póliza")
    tms_def_insurance_environmental_mx = fields.Char(related='company_id.tms_def_insurance_environmental_mx', readonly=False, string="Aseguradora")

    tms_def_insurance_cargo = fields.Char(related='company_id.tms_def_insurance_cargo', readonly=False, string="Póliza")
    tms_def_insurance_cargo_mx = fields.Char(related='company_id.tms_def_insurance_cargo_mx', readonly=False, string="Aseguradora")

    # CFDI 4.0
    tms_def_l10n_mx_edi_tax_object = fields.Selection(related='company_id.tms_def_l10n_mx_edi_tax_object', readonly=False, string="Objeto de Impuesto por Defecto (CFDI 4.0)")
