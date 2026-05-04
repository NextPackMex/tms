# -*- coding: utf-8 -*-
"""
Modelo tms.expense.type — Tipo de Gasto de Viaje

Catálogo de tipos de gastos (diesel, casetas, viáticos, etc.)
para clasificación de gastos reales en viajes.

V2.3.3 — Expense Tracking
"""

from odoo import fields, models


class TmsExpenseType(models.Model):
    _name = 'tms.expense.type'
    _description = 'Tipo de Gasto de Viaje'
    _order = 'sequence, name'

    # ════════════════════════════════════════════════════════════════
    # CAMPOS
    # ════════════════════════════════════════════════════════════════

    name = fields.Char(
        string='Nombre',
        required=True,
        help='Tipo de gasto (ej: Diesel, Casetas, Viáticos)'
    )

    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de visualización en listas'
    )

    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Si está inactivo, no aparecerá en selecciones'
    )

    notes = fields.Char(
        string='Notas',
        help='Notas internas sobre este tipo de gasto'
    )
