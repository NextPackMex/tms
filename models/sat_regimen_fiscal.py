# -*- coding: utf-8 -*-
from odoo import api, models, fields


class TmsSatRegimenFiscal(models.Model):
    """Catálogo SAT c_RegimenFiscal — Regímenes Fiscales vigentes 2024.

    Modelo global: sin company_id, compartido entre todas las empresas
    del sistema. Alimenta el campo tms_regimen_fiscal_id en res.company
    y es requerido por el SAT para la emisión de CFDI 4.0 / Carta Porte 3.1.
    """

    _name = 'tms.sat.regimen.fiscal'
    _description = 'Catálogo SAT — Régimen Fiscal c_RegimenFiscal'
    _order = 'code'
    # SIN company_id — catálogo global compartido entre empresas

    code = fields.Char(
        string='Código SAT',
        size=3,
        required=True,
        index=True,
        help='Código numérico del SAT (ej. 612)'
    )
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción oficial del SAT'
    )
    full_name = fields.Char(
        string='Régimen Fiscal',
        compute='_compute_full_name',
        store=True,
        help='Código + descripción para mostrar en selectores'
    )

    _rec_name = 'full_name'
    _rec_names_search = ['code', 'name', 'full_name']

    @api.depends('code', 'name')
    def _compute_full_name(self):
        """Genera la etiqueta completa para los selectores.

        Formato: '612 - Personas Físicas con Actividades Empresariales'
        Permite identificar el régimen por código y descripción.
        """
        for rec in self:
            rec.full_name = '%s - %s' % (rec.code, rec.name) if rec.code else rec.name
