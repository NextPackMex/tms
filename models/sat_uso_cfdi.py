# -*- coding: utf-8 -*-
from odoo import api, models, fields


class TmsSatUsoCfdi(models.Model):
    """Catálogo SAT c_UsoCFDI — Usos del CFDI vigentes para CFDI 4.0.

    Modelo global: sin company_id, compartido entre todas las empresas.
    Alimenta el campo uso_cfdi_id en el wizard de facturación y en account.move.
    El SAT requiere este campo en el nodo Receptor de todo CFDI 4.0.
    """

    _name = 'tms.sat.uso.cfdi'
    _description = 'Catálogo SAT — Uso CFDI c_UsoCFDI'
    _order = 'code'
    # SIN company_id — catálogo global compartido entre empresas

    code = fields.Char(
        string='Código SAT',
        size=4,
        required=True,
        index=True,
        help='Código alfanumérico del SAT (ej. G03, CP01)'
    )
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción oficial del SAT'
    )
    full_name = fields.Char(
        string='Uso CFDI',
        compute='_compute_full_name',
        store=True,
        help='Código + descripción para mostrar en selectores'
    )

    _rec_name = 'full_name'
    _rec_names_search = ['code', 'name', 'full_name']

    @api.depends('code', 'name')
    def _compute_full_name(self):
        """Genera la etiqueta completa para los selectores.

        Formato: 'G03 - Gastos en general'
        Permite identificar el uso por código y descripción.
        """
        for rec in self:
            rec.full_name = '%s - %s' % (rec.code, rec.name) if rec.code else rec.name
