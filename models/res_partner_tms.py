# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # 🔒 SEGURIDAD SAAS
    # default=lambda self: self.env.company -> Asigna la empresa del usuario logueado.
    company_id = fields.Many2one(
        'res.company',
        'Compañía',
        default=lambda self: self.env.company,
        required=False,
        index=True,
        help="El contacto pertenece a esta empresa (Si vacío, es Global/Público)."
    )

    tms_cp_id = fields.Many2one('tms.sat.codigo.postal', string='Código Postal SAT')

    # Campo Auxiliar para Dominios XML (Store=False es suficiente si es compute on the fly, o True si prefieres búsquedas)
    tms_sat_state_code = fields.Char(compute='_compute_tms_sat_state_code', store=True)

    # Campos SAT
    l10n_mx_edi_colonia_sat_id = fields.Many2one('tms.sat.colonia', string='Colonia')
    l10n_mx_edi_municipio_sat_id = fields.Many2one('tms.sat.municipio', string='Municipio')
    l10n_mx_edi_localidad_sat_id = fields.Many2one('tms.sat.localidad', string='Localidad')

    # CFDI 4.0 - Requeridos
    l10n_mx_edi_fiscal_regime = fields.Selection(
        selection=[
            ('601', 'General de Ley Personas Morales'),
            ('603', 'Personas Morales con Fines no Lucrativos'),
            ('605', 'Sueldos y Salarios e Ingresos Asimilados a Salarios'),
            ('606', 'Arrendamiento'),
            ('607', 'Régimen de Enajenación o Adquisición de Bienes'),
            ('608', 'Demás ingresos'),
            ('610', 'Residentes en el Extranjero sin Establecimiento Permanente en México'),
            ('611', 'Ingresos por Dividendos (socios y accionistas)'),
            ('612', 'Personas Físicas con Actividades Empresariales y Profesionales'),
            ('614', 'Ingresos por intereses'),
            ('615', 'Régimen de los ingresos por obtención de premios'),
            ('616', 'Sin obligaciones fiscales'),
            ('620', 'Sociedades Cooperativas de Producción que optan por diferir sus ingresos'),
            ('621', 'Incorporación Fiscal'),
            ('622', 'Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras'),
            ('623', 'Opcional para Grupos de Sociedades'),
            ('624', 'Coordinados'),
            ('625', 'Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas'),
            ('626', 'Régimen Simplificado de Confianza'),
        ],
        string='Régimen Fiscal',
        help='Es el régimen bajo el cual el contribuyente está registrado ante el SAT.'
    )

    l10n_mx_edi_usage = fields.Selection(
        selection=[
            ('G01', 'Adquisición de mercancías'),
            ('G02', 'Devoluciones, descuentos o bonificaciones'),
            ('G03', 'Gastos en general'),
            ('I01', 'Construcciones'),
            ('I02', 'Mobilario y equipo de oficina por inversiones'),
            ('I03', 'Equipo de transporte'),
            ('I04', 'Equipo de computo y accesorios'),
            ('I05', 'Dados, troqueles, moldes, matrices y herramental'),
            ('I06', 'Comunicaciones telefónicas'),
            ('I07', 'Comunicaciones satelitales'),
            ('I08', 'Otra maquinaria y equipo'),
            ('P01', 'Por definir'),
            ('CP01', 'Pagos'),
            ('CN01', 'Nómina'),
            ('S01', 'Sin efectos fiscales'),
        ],
        string='Uso del CFDI',
        default='S01',
        help='Clave que corresponde al uso que le dará el receptor al comprobante.'
    )

    def action_tms_normalize_name_40(self):
        """
        Normaliza el nombre para CFDI 4.0:
        1. Todo a MAYÚSCULAS
        2. Elimina regímenes societarios (S.A. DE C.V., S. DE R.L., etc.) solo si es Compañía.
        """
        for partner in self:
            if not partner.name: continue
            
            new_name = partner.name.upper()
            
            if partner.is_company:
                # Lista común de regímenes a eliminar según guías del SAT para 4.0
                regimenes = [
                    ' S.A. DE C.V.', ' SA DE CV', 
                    ' S. DE R.L. DE C.V.', ' S DE RL DE CV',
                    ' S.A.P.I. DE C.V.', ' SAPI DE CV',
                    ' S.A.', ' SA',
                    ' S.C.', ' SC',
                    ' A.C.', ' AC'
                ]
                for r in regimenes:
                    new_name = new_name.replace(r, '')
            
            partner.name = new_name.strip()

    @api.depends('state_id', 'state_id.code')
    def _compute_tms_sat_state_code(self):
        """Limpia el código de estado para coincidir con catálogos SAT (MX-JAL -> JAL)"""
        for record in self:
            if record.state_id and record.state_id.code:
                record.tms_sat_state_code = record.state_id.code.replace('MX-', '')
            else:
                record.tms_sat_state_code = False

    @api.onchange('tms_cp_id')
    def _on_cp_change(self):
        """Solo lógica de asignación y autocompletado"""
        if not self.tms_cp_id: return

        cp = self.tms_cp_id
        self.zip = cp.code

        # Asignar Estado (Esto disparará el compute de tms_sat_state_code)
        if cp.estado:
            domain = ['|', ('code', '=', cp.estado), ('code', '=', f'MX-{cp.estado}')]
            state = self.env['res.country.state'].search(domain + [('country_id.code', '=', 'MX')], limit=1)
            if state: self.state_id = state

        # Limpiar dependientes
        self.l10n_mx_edi_colonia_sat_id = False
        self.l10n_mx_edi_municipio_sat_id = False
        self.l10n_mx_edi_localidad_sat_id = False

        # Pre-llenado si el CP es específico
        if self.tms_sat_state_code:
            state_code = self.tms_sat_state_code
            if cp.municipio:
                # Intento match por nombre (lo más probable en CP -> Muni)
                muni = self.env['tms.sat.municipio'].search([('name', '=', cp.municipio), ('estado', '=', state_code)], limit=1)
                # Fallback por código si existiera
                if not muni:
                     muni = self.env['tms.sat.municipio'].search([('code', '=', cp.municipio), ('estado', '=', state_code)], limit=1)

                if muni:
                    self.l10n_mx_edi_municipio_sat_id = muni
                    self.city = muni.name

            if cp.localidad:
                loc = self.env['tms.sat.localidad'].search([('name', '=', cp.localidad), ('estado', '=', state_code)], limit=1)
                if not loc:
                    loc = self.env['tms.sat.localidad'].search([('code', '=', cp.localidad), ('estado', '=', state_code)], limit=1)

                if loc: self.l10n_mx_edi_localidad_sat_id = loc

    @api.onchange('l10n_mx_edi_municipio_sat_id', 'l10n_mx_edi_localidad_sat_id')
    def _on_geo_change(self):
        """Sync Ciudad nativa al elegir Mun/Loc"""
        if self.l10n_mx_edi_localidad_sat_id:
            self.city = self.l10n_mx_edi_localidad_sat_id.name
        elif self.l10n_mx_edi_municipio_sat_id:
            self.city = self.l10n_mx_edi_municipio_sat_id.name
