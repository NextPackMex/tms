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
