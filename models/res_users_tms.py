# -*- coding: utf-8 -*-
"""
Extensión de res.users para TMS.

Gestiona la asignación de grupos y permisos para usuarios TMS.
"""

from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _remove_fleet_group_from_tms_users(self):
        """
        Elimina fleet_group_user de usuarios que solo tienen group_tms_user.

        Lógica:
        - Si el usuario tiene group_tms_manager → dejar fleet_group_user (managers pueden ver todo)
        - Si el usuario tiene solo group_tms_user → quitar fleet_group_user (users no ven Fleet)

        Se llama desde __manifest__.py post_init_hook en cada actualización del módulo.
        """
        # Obtener los grupos
        group_tms_user = self.env.ref('tms.group_tms_user', raise_if_not_found=False)
        group_tms_manager = self.env.ref('tms.group_tms_manager', raise_if_not_found=False)
        group_fleet_user = self.env.ref('fleet.fleet_group_user', raise_if_not_found=False)

        if not (group_tms_user and group_fleet_user):
            return False

        # Usuarios que tienen group_tms_user pero NO group_tms_manager
        users_to_fix = self.env['res.users'].search([
            ('group_ids', '=', group_tms_user.id),
        ])

        # Filtrar: excluir los que tiene group_tms_manager
        if group_tms_manager:
            users_to_fix = users_to_fix.filtered(
                lambda u: group_tms_manager not in u.group_ids
            )

        # Quitar fleet_group_user de esos usuarios
        if users_to_fix:
            users_to_fix.write({
                'group_ids': [(3, group_fleet_user.id, 0)]  # 3 = remove
            })

        return True
