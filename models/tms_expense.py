# -*- coding: utf-8 -*-
"""
Modelo tms.expense — Gasto Real del Viaje

Registra gastos reales (diesel, casetas, reparaciones, etc.) posteriores a la estimación.
Se usa para calcular la utilidad neta comparando costo estimado vs costo real.

V2.3.3 — Expense Tracking
"""

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class TmsExpense(models.Model):
    _name = 'tms.expense'
    _description = 'Gasto Real del Viaje'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    # ════════════════════════════════════════════════════════════════
    # RELACIONES
    # ════════════════════════════════════════════════════════════════

    waybill_id = fields.Many2one(
        'tms.waybill',
        string='Viaje',
        required=True,
        ondelete='cascade',
        check_company=True,
        tracking=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        related='waybill_id.company_id',
        store=True,
        readonly=True
    )

    driver_id = fields.Many2one(
        'hr.employee',
        string='Chofer',
        tracking=True,
        help='Chofer responsable del gasto (opcional)'
    )

    # ════════════════════════════════════════════════════════════════
    # DATOS PRINCIPALES
    # ════════════════════════════════════════════════════════════════

    date = fields.Date(
        string='Fecha del Gasto',
        default=fields.Date.today,
        required=True,
        tracking=True
    )

    expense_type_id = fields.Many2one(
        'tms.expense.type',
        string='Tipo de Gasto',
        required=True,
        ondelete='restrict',
        tracking=True,
        help='Clasificación del gasto para análisis de costos'
    )

    description = fields.Char(
        string='Descripción',
        help='Detalles adicionales del gasto (ej: "Reparación alternador", "Caseta México-Querétaro")'
    )

    amount = fields.Monetary(
        string='Monto',
        required=True,
        currency_field='currency_id',
        tracking=True,
        help='Monto del gasto en moneda local'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='waybill_id.currency_id',
        store=True,
        readonly=True
    )

    # ════════════════════════════════════════════════════════════════
    # COMPROBANTES Y ESTADO
    # ════════════════════════════════════════════════════════════════

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'tms_expense_attachment_rel',
        'expense_id',
        'attachment_id',
        string='Comprobantes',
        help='Facturas, recibos, fotos del gasto'
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('approved', 'Aprobado'),
            ('paid', 'Pagado'),
        ],
        string='Estado',
        default='draft',
        tracking=True,
        help='Flujo: Borrador → Aprobado → Pagado'
    )

    # ════════════════════════════════════════════════════════════════
    # DEFAULTS
    # ════════════════════════════════════════════════════════════════

    @api.model
    def default_get(self, fields_list):
        """Prellenar chofer del viaje al crear gasto desde liquidación."""
        res = super().default_get(fields_list)
        if res.get('waybill_id'):
            waybill = self.env['tms.waybill'].browse(res['waybill_id'])
            res['driver_id'] = self.env.context.get('default_driver_id') or waybill.driver_id.id
        return res

    # ════════════════════════════════════════════════════════════════
    # ACCIONES
    # ════════════════════════════════════════════════════════════════

    def action_approve(self):
        """Aprueba el gasto (solo manager o administrador)."""
        if not self.user_has_groups('tms.group_tms_manager'):
            raise UserError(_('Solo el manager puede aprobar gastos.'))
        self.state = 'approved'

    def action_pay(self):
        """Marca el gasto como pagado."""
        self.state = 'paid'

    def action_reset(self):
        """Vuelve el gasto a estado borrador."""
        self.state = 'draft'

    # ════════════════════════════════════════════════════════════════
    # VALIDACIONES
    # ════════════════════════════════════════════════════════════════

    @api.constrains('amount')
    def _check_positive_amount(self):
        """Valida que el monto sea positivo."""
        for record in self:
            if record.amount <= 0:
                raise UserError(_('El monto debe ser mayor a $0.'))

    @api.constrains('expense_type', 'date', 'waybill_id')
    def _check_not_closed_waybill(self):
        """Valida que el waybill no esté cerrado."""
        for record in self:
            if record.waybill_id.state == 'closed':
                raise UserError(_('No se pueden agregar gastos a un viaje facturado/cerrado.'))
