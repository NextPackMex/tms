# -*- coding: utf-8 -*-
"""
Hooks de inicialización para el módulo TMS.

Se ejecutan durante la instalación y actualización del módulo.
"""


def post_init_hook(cr, registry):
    """
    Hook post-inicialización: ejecutado después de instalar/actualizar TMS.

    - Elimina fleet_group_user de usuarios que solo tienen group_tms_user
    - Asegura que los menús estén correctamente restringidos
    """
    from odoo.api import Environment

    env = Environment(cr, 1, {})  # superuser
    users_model = env['res.users']

    # Remover fleet_group_user de usuarios TMS
    users_model._remove_fleet_group_from_tms_users()

    return True
