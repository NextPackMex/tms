# -*- coding: utf-8 -*-
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    # ============================================================
    # CONFIGURACIÓN DEFAULT: SEGUROS (Carta Porte)
    # ============================================================

    # 1. RESPONSABILIDAD CIVIL
    tms_def_insurance_civil_liability = fields.Char(
        string='Póliza Resp. Civil (Default)',
        help='Valor por defecto para nuevos vehículos: Número de Póliza'
    )
    tms_def_insurance_civil_liability_mx = fields.Char(
        string='Aseguradora Resp. Civil (Default)',
        help='Valor por defecto para nuevos vehículos: Nombre de la Aseguradora'
    )

    # 2. MEDIO AMBIENTE
    tms_def_insurance_environmental = fields.Char(
        string='Póliza Medio Ambiente (Default)',
        help='Valor por defecto para nuevos vehículos: Número de Póliza'
    )
    tms_def_insurance_environmental_mx = fields.Char(
        string='Aseguradora Medio Ambiente (Default)',
        help='Valor por defecto para nuevos vehículos: Nombre de la Aseguradora'
    )

    # 3. CARGA
    tms_def_insurance_cargo = fields.Char(
        string='Póliza Carga (Default)',
        help='Valor por defecto para nuevos vehículos: Número de Póliza'
    )
    tms_def_insurance_cargo_mx = fields.Char(
        string='Aseguradora Carga (Default)',
        help='Valor por defecto para nuevos vehículos: Nombre de la Aseguradora'
    )

    # CFDI 4.0 DEFAULT
    tms_def_l10n_mx_edi_tax_object = fields.Selection(
        selection=[
            ('01', 'No objeto de impuesto'),
            ('02', 'Sí objeto de impuesto'),
            ('03', 'Sí objeto de impuesto y no obligado al desglose'),
            ('04', 'Sí objeto de impuesto y no causa impuesto'),
        ],
        string='Objeto de Impuesto (Default)',
        default='02',
        help='Valor por defecto para las líneas de viaje en CFDI 4.0.'
    )

    # --- CSD para timbrado CFDI ---
    tms_regimen_fiscal_id = fields.Many2one(
        'tms.sat.regimen.fiscal',
        string='Régimen Fiscal',
        help='Régimen fiscal del SAT para el CFDI. Catálogo c_RegimenFiscal.'
    )
    tms_csd_cer_fname = fields.Char(string='Nombre .cer')
    tms_csd_key_fname = fields.Char(string='Nombre .key')
    tms_csd_cer = fields.Binary(string='CSD Certificado (.cer)')
    tms_csd_key = fields.Binary(string='CSD Llave Privada (.key)')
    tms_csd_password = fields.Char(string='Contraseña CSD', copy=False)

    # --- Seguros Carta Porte ---
    tms_insurance_rc_company = fields.Char(string='Aseguradora RC')
    tms_insurance_rc_policy = fields.Char(string='Póliza RC')
    tms_insurance_rc_expiry = fields.Date(string='Vigencia RC')
    tms_insurance_cargo_company = fields.Char(string='Aseguradora Carga')
    tms_insurance_cargo_policy = fields.Char(string='Póliza Carga')
    tms_insurance_cargo_expiry = fields.Date(string='Vigencia Carga')
    tms_insurance_env_company = fields.Char(string='Aseguradora Ambiental')
    tms_insurance_env_policy = fields.Char(string='Póliza Ambiental')
    tms_insurance_env_expiry = fields.Date(string='Vigencia Ambiental')

    # ============================================================
    # PAC FORMAS DIGITALES — Credenciales y ambiente (V2.2)
    # ============================================================
    fd_usuario = fields.Char(
        string='Usuario Formas Digitales',
        help='Usuario de la cuenta en Formas Digitales (forsedi.facturacfdi.mx)'
    )
    fd_password = fields.Char(
        string='Contraseña Formas Digitales',
        copy=False,
    )
    fd_user_id = fields.Char(
        string='User ID Formas Digitales',
        help='ID de usuario proporcionado por Formas Digitales'
    )
    fd_ambiente = fields.Selection([
        ('pruebas',    'Pruebas (dev33)'),
        ('produccion', 'Producción (v33)'),
    ], string='Ambiente FD', default='pruebas')

    # ============================================================
    # PAC SW SAPIEN — Credenciales y ambiente (V2.2)
    # ============================================================
    sw_usuario = fields.Char(
        string='Usuario SW Sapien',
        help='Email de la cuenta en SW Sapien (sw.com.mx)'
    )
    sw_password = fields.Char(
        string='Contraseña SW Sapien',
        copy=False,
    )
    sw_ambiente = fields.Selection([
        ('pruebas',    'Pruebas (test)'),
        ('produccion', 'Producción'),
    ], string='Ambiente SW', default='pruebas')

    # ============================================================
    # CONTROL DUAL PAC (V2.2)
    # ============================================================
    pac_primario = fields.Selection([
        ('formas_digitales', 'Formas Digitales'),
        ('sw_sapien',        'SW Sapien'),
    ], string='PAC Primario', default='formas_digitales',
       help='PAC que se intentará primero al timbrar'
    )
    pac_failover = fields.Boolean(
        string='Activar failover automático',
        default=True,
        help='Si el PAC primario falla, intentar automáticamente con el secundario'
    )

    # ============================================================
    # FACTURACIÓN TMS (V2.3)
    # ============================================================
    tms_sales_journal_id = fields.Many2one(
        'account.journal',
        string='Diario de Ventas TMS',
        domain="[('type', '=', 'sale'), ('company_id', '=', id)]",
        help='Diario contable que se usará al generar facturas (CFDI Ingreso) desde el TMS. '
             'Si no se configura, el wizard permitirá seleccionarlo manualmente.'
    )
