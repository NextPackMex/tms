# -*- coding: utf-8 -*-
"""
Hooks de inicialización para el módulo TMS.
Se ejecutan durante la instalación del módulo.

Nota: el recompute de cost_real_total V2.3.3 vive en
migrations/19.0.2.3.3/post-migrate.py (ejecutado por Odoo en cada -u tms).
"""


def post_init_hook(cr, registry):
    """
    Hook post-instalación: ejecutado solo al instalar TMS por primera vez (-i tms).
    Elimina fleet_group_user de usuarios que solo tienen group_tms_user,
    para que los usuarios TMS no vean el menú de Flota de Odoo.
    """
    from odoo.api import Environment

    env = Environment(cr, 1, {})
    env['res.users']._remove_fleet_group_from_tms_users()
    return True
