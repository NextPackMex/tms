# -*- coding: utf-8 -*-
"""
Modelo tms.driver.advance — Anticipo al Chofer

Registra anticipos en efectivo otorgados a choferes durante un viaje.
Se utiliza para liquidación final: Anticipo − Gastos Reales = Saldo.

V2.3.3 — Driver Settlement
"""

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class TmsDriverAdvance(models.Model):
    _name = 'tms.driver.advance'
    _description = 'Anticipo al Chofer'
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
        required=True,
        tracking=True,
        help='Chofer beneficiario del anticipo'
    )

    # ════════════════════════════════════════════════════════════════
    # DATOS PRINCIPALES
    # ════════════════════════════════════════════════════════════════

    date = fields.Date(
        string='Fecha Anticipo',
        default=fields.Date.today,
        required=True,
        tracking=True
    )

    amount = fields.Monetary(
        string='Monto',
        required=True,
        currency_field='currency_id',
        tracking=True,
        help='Cantidad otorgada en anticipo'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='waybill_id.currency_id',
        store=True,
        readonly=True
    )

    notes = fields.Char(
        string='Concepto',
        help='Motivo o descripción del anticipo (ej: "Alimentación", "Peaje")'
    )

    # ════════════════════════════════════════════════════════════════
    # COMPROBANTES Y ESTADO
    # ════════════════════════════════════════════════════════════════

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'tms_driver_advance_attachment_rel',
        'advance_id',
        'attachment_id',
        string='Vale de Anticipo',
        help='Documentos que respaldan el anticipo entregado'
    )

    state = fields.Selection(
        selection=[
            ('pendiente', 'Pendiente'),
            ('entregado', 'Entregado'),
            ('liquidado', 'Liquidado'),
        ],
        string='Estado',
        default='pendiente',
        tracking=True,
        help='Flujo: Pendiente → Entregado → Liquidado'
    )

    # ════════════════════════════════════════════════════════════════
    # DEFAULTS
    # ════════════════════════════════════════════════════════════════

    @api.model
    def default_get(self, fields_list):
        """Prellenar chofer del viaje al crear anticipo desde liquidación."""
        res = super().default_get(fields_list)
        if res.get('waybill_id'):
            waybill = self.env['tms.waybill'].browse(res['waybill_id'])
            res['driver_id'] = self.env.context.get('default_driver_id') or waybill.driver_id.id
        return res

    # ════════════════════════════════════════════════════════════════
    # ACCIONES
    # ════════════════════════════════════════════════════════════════

    def action_confirm_delivery(self):
        """Marca el anticipo como entregado al chofer."""
        if not self.env.user.has_group('tms.group_tms_manager'):
            raise UserError(_('Solo el manager puede confirmar entregas de anticipo.'))
        self.state = 'entregado'

    def action_liquidate(self):
        """Marca el anticipo como liquidado en cierre de viaje."""
        self.state = 'liquidado'

    def action_reset(self):
        """Vuelve el anticipo a estado pendiente."""
        self.state = 'pendiente'

    def action_open_form(self):
        """Abre el formulario completo del anticipo en una nueva ventana."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tms.driver.advance',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ════════════════════════════════════════════════════════════════
    # VALIDACIONES
    # ════════════════════════════════════════════════════════════════

    @api.constrains('amount')
    def _check_positive_amount(self):
        """Valida que el monto sea positivo."""
        for record in self:
            if record.amount <= 0:
                raise UserError(_('El monto del anticipo debe ser mayor a $0.'))

    @api.constrains('driver_id', 'date', 'waybill_id')
    def _check_not_closed_waybill(self):
        """Valida que el waybill no esté cerrado."""
        for record in self:
            if record.waybill_id.state == 'closed':
                raise UserError(_('No se pueden agregar anticipos a un viaje facturado/cerrado.'))
