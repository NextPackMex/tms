# -*- coding: utf-8 -*-
from odoo import models, fields

class TmsFuelHistory(models.Model):
    _name = 'tms.fuel.history'
    _description = 'Historial de Precios de Diesel'
    _order = 'date desc, id desc'
    _check_company_auto = True

    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today
    )
    price = fields.Float(
        string='Precio por Litro',
        required=True,
        digits=(10, 2)
    )
    notes = fields.Char(string='Notas')

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company
    )
