# -*- coding: utf-8 -*-
"""
Modelo tms.vehicle.performance — Estadísticas acumuladas por vehículo.

Calcula en batch el historial de ingresos cobrados y por cobrar
por unidad (tracto). Se actualiza desde tms_waybill.write() cuando
cambia el estado del viaje.

V2.4.3 — Rendimiento por Vehículo + Cobrado vs Por Cobrar
"""
from collections import defaultdict
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class TmsVehiclePerformance(models.Model):
    _name = 'tms.vehicle.performance'
    _description = 'Estadísticas de rendimiento acumuladas por vehículo'
    _rec_name = 'vehicle_id'
    _order = 'total_revenue desc'

    # ════════════════════════════════════════════════════════════════
    # RELACIONES
    # ════════════════════════════════════════════════════════════════

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        required=True,
        ondelete='cascade',
        index=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True,
    )

    # ════════════════════════════════════════════════════════════════
    # ESTADÍSTICAS ACUMULADAS
    # ════════════════════════════════════════════════════════════════

    total_trips = fields.Integer(
        string='Viajes Cerrados',
        default=0,
        help='Viajes en estado "closed" (facturados con CFDI timbrado)',
    )

    total_km = fields.Float(
        string='Km Recorridos',
        digits=(10, 1),
        default=0.0,
        help='Suma de distance_km de viajes cerrados',
    )

    total_revenue = fields.Monetary(
        string='Ingreso Cobrado',
        currency_field='currency_id',
        default=0.0,
        help='Suma de amount_total de viajes cerrados con CFDI Ingreso timbrado',
    )

    total_revenue_pending = fields.Monetary(
        string='Por Cobrar',
        currency_field='currency_id',
        default=0.0,
        help='Suma de amount_total de viajes en operación sin CFDI Ingreso timbrado',
    )

    avg_revenue_per_trip = fields.Monetary(
        string='Promedio por Viaje',
        currency_field='currency_id',
        default=0.0,
        help='total_revenue / total_trips',
    )

    avg_km_per_trip = fields.Float(
        string='Promedio Km/Viaje',
        digits=(10, 1),
        default=0.0,
        help='total_km / total_trips',
    )

    # ════════════════════════════════════════════════════════════════
    # MÉTODO DE ACTUALIZACIÓN BATCH
    # ════════════════════════════════════════════════════════════════

    @api.model
    def _refresh_vehicle_stats(self, vehicle_ids=None):
        """
        Recalcula estadísticas de rendimiento para los vehículos indicados.

        Si vehicle_ids es None, recalcula todos los vehículos con viajes.
        Se llama desde tms_waybill.write() cuando cambia state.
        Usa búsqueda batch para evitar N+1 queries.
        """
        Waybill = self.env['tms.waybill']
        company_id = self.env.company.id

        domain_base = [('company_id', '=', company_id)]
        if vehicle_ids:
            domain_base.append(('vehicle_id', 'in', vehicle_ids))

        # — Viajes cerrados: cobrado acumulado —
        waybills_closed = Waybill.search(domain_base + [('state', '=', 'closed')])

        # — Viajes en operación: por cobrar —
        estados_pendientes = ['aprobado', 'waybill', 'in_transit', 'arrived']
        waybills_pending = Waybill.search(domain_base + [('state', 'in', estados_pendientes)])

        # Acumular por vehicle_id
        stats = defaultdict(lambda: {
            'total_trips': 0,
            'total_km': 0.0,
            'total_revenue': 0.0,
            'total_revenue_pending': 0.0,
        })

        for wb in waybills_closed:
            vid = wb.vehicle_id.id
            if not vid:
                continue
            stats[vid]['total_trips'] += 1
            stats[vid]['total_km'] += wb.distance_km or 0.0
            # Solo suma ingreso si tiene CFDI Ingreso timbrado
            tiene_cfdi = any(
                inv.tms_cfdi_status == 'timbrada'
                for inv in wb.invoice_ids
            )
            if tiene_cfdi:
                stats[vid]['total_revenue'] += wb.amount_total

        for wb in waybills_pending:
            vid = wb.vehicle_id.id
            if not vid:
                continue
            stats[vid]['total_revenue_pending'] += wb.amount_total

        # Crear o actualizar registros en batch
        for vehicle_id, data in stats.items():
            trips = data['total_trips']
            avg_rev = data['total_revenue'] / trips if trips > 0 else 0.0
            avg_km = data['total_km'] / trips if trips > 0 else 0.0

            vals = {
                'total_trips': trips,
                'total_km': data['total_km'],
                'total_revenue': data['total_revenue'],
                'total_revenue_pending': data['total_revenue_pending'],
                'avg_revenue_per_trip': avg_rev,
                'avg_km_per_trip': avg_km,
            }

            existing = self.search([
                ('vehicle_id', '=', vehicle_id),
                ('company_id', '=', company_id),
            ], limit=1)

            if existing:
                existing.write(vals)
            else:
                self.create({'vehicle_id': vehicle_id, 'company_id': company_id, **vals})

        _logger.info(
            'TMS VehiclePerformance: actualizados %d vehículos',
            len(stats),
        )
