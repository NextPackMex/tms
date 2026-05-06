# -*- coding: utf-8 -*-
"""
Modelo de Liquidación de Viajes.

Centraliza la gestión de anticipos y gastos reales de un viaje,
permitiendo generar liquidaciones formales para el chofer.

Se crea automáticamente cuando un waybill pasa a estado in_transit.
"""
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TmsLiquidacion(models.Model):
    """
    Liquidación de un viaje: Consolidación de anticipos, gastos reales y utilidad neta.

    WORKFLOW:
    borrador → en_proceso → liquidado
    """
    _name = 'tms.liquidacion'
    _description = 'Liquidación de Viaje'
    _order = 'date_liquidacion desc, id desc'
    _rec_name = 'name'

    # ============================================================
    # IDENTIFICACIÓN
    # ============================================================

    name = fields.Char(
        string='Folio Liquidación',
        compute='_compute_name',
        store=True,
        readonly=True,
        help='Código único: LIQ-{folio_viaje}'
    )

    waybill_id = fields.Many2one(
        'tms.waybill',
        string='Viaje',
        required=True,
        ondelete='cascade',
        check_company=True,
        help='Viaje asociado a esta liquidación'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        related='waybill_id.company_id',
        store=True,
        readonly=True,
        check_company=True
    )

    driver_id = fields.Many2one(
        'hr.employee',
        string='Chofer',
        related='waybill_id.driver_id',
        store=True,
        readonly=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        related='waybill_id.partner_invoice_id',
        store=True,
        readonly=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='waybill_id.currency_id',
        store=True,
        readonly=True
    )

    # ============================================================
    # DATOS DEL VIAJE (READONLY)
    # ============================================================

    waybill_state = fields.Selection(
        related='waybill_id.state',
        string='Estado del Viaje',
        store=True,
        readonly=True
    )

    ingreso = fields.Monetary(
        string='Ingreso del Viaje',
        related='waybill_id.amount_untaxed',
        store=True,
        readonly=True,
        currency_field='currency_id',
        help='Precio total del viaje sin impuestos'
    )

    # ============================================================
    # ANTICIPOS Y GASTOS (One2many)
    # ============================================================

    advance_ids = fields.One2many(
        'tms.driver.advance',
        'waybill_id',
        string='Anticipos al Chofer',
        readonly=True,
        help='Anticipos en efectivo otorgados al chofer'
    )

    expense_ids = fields.One2many(
        'tms.expense',
        'waybill_id',
        string='Gastos Reales del Viaje',
        readonly=True,
        help='Gastos reales incurridos durante el viaje'
    )

    # ============================================================
    # TOTALES Y CÁLCULOS
    # ============================================================

    advance_total = fields.Monetary(
        string='Total Anticipos',
        compute='_compute_totales',
        store=True,
        currency_field='currency_id',
        help='Suma de anticipos entregados y liquidados'
    )

    expense_total = fields.Monetary(
        string='Total Gastos Reales',
        compute='_compute_totales',
        store=True,
        currency_field='currency_id',
        help='Suma de gastos aprobados y pagados'
    )

    settlement_balance = fields.Monetary(
        string='Saldo Liquidación Chofer',
        compute='_compute_totales',
        store=True,
        currency_field='currency_id',
        help='Anticipos - Gastos (positivo=chofer devuelve, negativo=empresa paga)'
    )

    net_profit = fields.Monetary(
        string='Utilidad Neta del Viaje',
        compute='_compute_totales',
        store=True,
        currency_field='currency_id',
        help='Ingreso - Gastos Reales'
    )

    profit_margin = fields.Float(
        string='Margen de Utilidad (%)',
        compute='_compute_totales',
        store=True,
        digits=(5, 2),
        help='Porcentaje de utilidad sobre ingreso total'
    )

    # ============================================================
    # FLUJO Y AUDITORÍA
    # ============================================================

    state = fields.Selection(
        [
            ('borrador', 'Borrador'),
            ('en_proceso', 'En Proceso'),
            ('liquidado', 'Liquidado'),
        ],
        string='Estado Liquidación',
        default='borrador',
        help='Ciclo de vida de la liquidación'
    )

    date_created = fields.Date(
        string='Fecha Creación',
        default=fields.Date.today,
        readonly=True,
        help='Fecha de creación de la liquidación'
    )

    date_liquidacion = fields.Date(
        string='Fecha Liquidación',
        help='Fecha en que se completó la liquidación'
    )

    notes = fields.Text(
        string='Notas',
        help='Observaciones sobre la liquidación'
    )

    # ============================================================
    # MÉTODOS DE CREACIÓN Y LIFECYCLE
    # ============================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Crea liquidación y fuerza compute del nombre."""
        records = super().create(vals_list)
        records._compute_name()
        return records

    # ============================================================
    # MÉTODOS COMPUTE
    # ============================================================

    @api.depends('waybill_id')
    def _compute_name(self):
        """Genera folio: LIQ-{waybill.name}."""
        for rec in self:
            if rec.waybill_id:
                rec.name = f"LIQ-{rec.waybill_id.name}"
            else:
                rec.name = 'LIQ-NUEVA'

    @api.depends(
        'advance_ids.amount',
        'advance_ids.state',
        'expense_ids.amount',
        'expense_ids.state',
        'ingreso'
    )
    def _compute_totales(self):
        """
        Calcula totales de anticipos, gastos, saldo y margen de utilidad.

        - advance_total: suma anticipos en estado 'entregado' o 'liquidado'
        - expense_total: suma gastos en estado 'approved' o 'paid'
        - settlement_balance: advance_total - expense_total
        - net_profit: ingreso - expense_total
        - profit_margin: (net_profit / ingreso * 100) si ingreso > 0
        """
        for rec in self:
            # Anticipos liquidados (entregado + liquidado)
            advance_total = sum(
                adv.amount
                for adv in rec.advance_ids
                if adv.state in ['entregado', 'liquidado']
            )
            rec.advance_total = advance_total

            # Gastos aprobados (approved + paid)
            expense_total = sum(
                exp.amount
                for exp in rec.expense_ids
                if exp.state in ['approved', 'paid']
            )
            rec.expense_total = expense_total

            # Saldo del chofer: positivo = devuelve, negativo = empresa paga
            rec.settlement_balance = advance_total - expense_total

            # Utilidad neta: ingreso - gastos reales
            rec.net_profit = rec.ingreso - expense_total

            # Margen: utilidad / ingreso * 100
            if rec.ingreso > 0:
                rec.profit_margin = (rec.net_profit / rec.ingreso) * 100
            else:
                rec.profit_margin = 0.0

    # ============================================================
    # ACCIONES DEL WORKFLOW
    # ============================================================

    def action_iniciar(self):
        """Inicia la liquidación: borrador → en_proceso."""
        for rec in self:
            if rec.state != 'borrador':
                raise UserError(f"Solo se puede iniciar liquidaciones en borrador. Estado actual: {rec.state}")
            rec.state = 'en_proceso'

    def action_liquidar(self):
        """Completa la liquidación: en_proceso → liquidado."""
        for rec in self:
            if rec.state != 'en_proceso':
                raise UserError(f"Solo se puede liquidar en estado 'En Proceso'. Estado actual: {rec.state}")
            rec.state = 'liquidado'
            rec.date_liquidacion = fields.Date.today()
            # Actualizar estadísticas de ruta
            rec._update_route_stats()

    def action_reabrir(self):
        """Reabre una liquidación liquidada: liquidado → en_proceso."""
        for rec in self:
            if rec.state == 'borrador':
                raise UserError("Ya está en borrador. Usa 'Iniciar' para pasar a 'En Proceso'.")
            rec.state = 'en_proceso'
            rec.date_liquidacion = None

    def _update_route_stats(self):
        """
        Actualiza o crea registro en tms.route.stats con datos del viaje liquidado.

        Busca por (origin_zip, dest_zip, company_id).
        Si existe: actualiza acumuladores.
        Si no existe: crea registro nuevo.
        """
        for rec in self:
            if not rec.waybill_id:
                continue

            wb = rec.waybill_id
            origin_zip = wb.origin_zip
            dest_zip = wb.dest_zip

            if not origin_zip or not dest_zip:
                _logger.warning(
                    f"Liquidación {rec.name}: No se puede actualizar ruta sin CPs origen/destino"
                )
                continue

            # Buscar estadísticas existentes de la ruta
            route_stats = self.env['tms.route.stats'].search([
                ('origin_zip', '=', origin_zip),
                ('dest_zip', '=', dest_zip),
                ('company_id', '=', rec.company_id.id),
            ], limit=1)

            # Datos a acumular
            route_name = f"{wb.origin_city_name or origin_zip} → {wb.dest_city_name or dest_zip}"

            if route_stats:
                # Actualizar registro existente
                route_stats.update({
                    'total_viajes': route_stats.total_viajes + 1,
                    'ingreso_total': route_stats.ingreso_total + rec.ingreso,
                    'last_price': rec.ingreso,
                    'last_waybill_date': fields.Date.today(),
                    'distance_km': wb.distance_km or 0.0,
                    'route_name': route_name,
                })
            else:
                # Crear registro nuevo
                self.env['tms.route.stats'].create({
                    'origin_zip': origin_zip,
                    'dest_zip': dest_zip,
                    'company_id': rec.company_id.id,
                    'route_name': route_name,
                    'total_viajes': 1,
                    'ingreso_total': rec.ingreso,
                    'last_price': rec.ingreso,
                    'last_waybill_date': fields.Date.today(),
                    'distance_km': wb.distance_km or 0.0,
                })

            _logger.info(f"Liquidación {rec.name}: Estadísticas de ruta actualizadas")
