# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # ============================================================
    # CARTA PORTE 3.1 - OPERADOR (FiguraTransporte: 01)
    # ============================================================

    # --- Licencia federal (Carta Porte 3.1) ---
    tms_rfc = fields.Char(string='RFC del chofer', size=13)
    tms_curp = fields.Char(string='CURP del chofer', size=18)
    tms_license_number = fields.Char(string='Número licencia federal')
    tms_license_type = fields.Selection(
        selection=[
            ('A', 'Tipo A - Vehículos ligeros'),
            ('B', 'Tipo B - Vehículos pesados'),
            ('C', 'Tipo C - Doble articulado'),
            ('D', 'Tipo D - Materiales peligrosos'),
            ('E', 'Tipo E - Doble articulado + peligrosos'),
        ],
        string='Tipo licencia federal',
    )
    tms_license_expiry = fields.Date(string='Vigencia licencia')
