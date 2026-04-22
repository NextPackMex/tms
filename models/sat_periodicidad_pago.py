# -*- coding: utf-8 -*-
from odoo import api, models, fields


class TmsSatPeriodicidadPago(models.Model):
    """Catálogo SAT c_Periodicidad — Periodicidades de pago para complemento de pago CFDI 4.0.

    Modelo global: sin company_id, compartido entre todas las empresas.
    Utilizado cuando se emiten CFDIs de pago con complemento de pago 2.0.
    Identifica la frecuencia con la que el receptor paga al emisor.
    """

    _name = 'tms.sat.periodicidad.pago'
    _description = 'Catálogo SAT — Periodicidad de Pago c_Periodicidad'
    _order = 'code'
    # SIN company_id — catálogo global compartido entre empresas

    code = fields.Char(
        string='Código SAT',
        size=2,
        required=True,
        index=True,
        help='Código numérico del SAT (ej. 04 = Mensual)'
    )
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción oficial del SAT'
    )
    full_name = fields.Char(
        string='Periodicidad de Pago',
        compute='_compute_full_name',
        store=True,
        help='Código + descripción para mostrar en selectores'
    )

    _rec_name = 'full_name'
    _rec_names_search = ['code', 'name', 'full_name']

    @api.depends('code', 'name')
    def _compute_full_name(self):
        """Genera la etiqueta completa para los selectores.

        Formato: '04 - Mensual'
        Permite identificar la periodicidad por código y descripción.
        """
        for rec in self:
            rec.full_name = '%s - %s' % (rec.code, rec.name) if rec.code else rec.name
