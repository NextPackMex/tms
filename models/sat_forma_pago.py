# -*- coding: utf-8 -*-
from odoo import api, models, fields


class TmsSatFormaPago(models.Model):
    """Catálogo SAT c_FormaPago — Formas de pago vigentes para CFDI 4.0.

    Modelo global: sin company_id, compartido entre todas las empresas.
    Alimenta el campo forma_pago_id en el wizard de facturación y en account.move.
    El SAT requiere este campo en el nodo Comprobante de todo CFDI 4.0.
    """

    _name = 'tms.sat.forma.pago'
    _description = 'Catálogo SAT — Forma de Pago c_FormaPago'
    _order = 'code'
    # SIN company_id — catálogo global compartido entre empresas

    code = fields.Char(
        string='Código SAT',
        size=2,
        required=True,
        index=True,
        help='Código numérico del SAT (ej. 03 = Transferencia, 99 = Por definir)'
    )
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción oficial del SAT'
    )
    full_name = fields.Char(
        string='Forma de Pago',
        compute='_compute_full_name',
        store=True,
        help='Código + descripción para mostrar en selectores'
    )

    _rec_name = 'full_name'
    _rec_names_search = ['code', 'name', 'full_name']

    @api.depends('code', 'name')
    def _compute_full_name(self):
        """Genera la etiqueta completa para los selectores.

        Formato: '03 - Transferencia electrónica de fondos'
        Permite identificar la forma de pago por código y descripción.
        """
        for rec in self:
            rec.full_name = '%s - %s' % (rec.code, rec.name) if rec.code else rec.name
