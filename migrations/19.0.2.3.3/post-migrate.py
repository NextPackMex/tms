# migrations/19.0.2.3.3/post-migrate.py
# -*- coding: utf-8 -*-
"""
Migración V2.3.3 — Recompute cost_real_total en waybills existentes.

El filtro de _compute_cost_real_total cambió: antes incluía gastos 'draft',
ahora solo cuenta 'approved' y 'paid' (consistente con tms.liquidacion).
Los campos store=True no se invalidan solos al cambiar la lógica del compute.

Odoo ejecuta este archivo automáticamente con -u tms cuando la versión
del módulo en el manifest es >= 19.0.2.3.3.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Fuerza recompute de cost_real_total y campos dependientes en todos los waybills.
    """
    from odoo.api import Environment
    from odoo import SUPERUSER_ID

    env = Environment(cr, SUPERUSER_ID, {})

    try:
        waybills = env['tms.waybill'].search([])
        count = len(waybills)

        if count:
            # Recomputar en cadena: cost_real_total → net_profit → settlement_balance
            waybills._compute_cost_real_total()
            waybills._compute_net_profit()
            waybills._compute_settlement_balance()
            _logger.info(
                'TMS migración 19.0.2.3.3: cost_real_total recomputado en %d waybills.',
                count
            )
        else:
            _logger.info('TMS migración 19.0.2.3.3: sin waybills existentes.')

    except Exception as e:
        _logger.warning(
            'TMS migración 19.0.2.3.3: error en recompute (no bloquea actualización): %s', e
        )
