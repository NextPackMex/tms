# -*- coding: utf-8 -*-
"""
Hooks de inicialización para el módulo TMS.
Se ejecutan durante la instalación del módulo.

Nota: el recompute de cost_real_total V2.3.3 vive en
migrations/19.0.2.3.3/post-migrate.py (ejecutado por Odoo en cada -u tms).
"""

# Menús Odoo a restringir para usuarios TMS: quedan visibles solo para
# group_tms_manager + base.group_system. Se aplica en post_init con refs
# TOLERANTES: si el módulo dueño del menú no está instalado, se omite
# (así una instalación limpia no truena por un menú ausente).
_MENUS_TO_RESTRICT = [
    'fleet.menu_root',
    'sale.sale_menu_root',
    'spreadsheet_dashboard.spreadsheet_dashboard_menu_root',
    'project.menu_main_pm',
    'website.menu_website_configuration',
    'mass_mailing.mass_mailing_menu_root',
    'survey.menu_surveys',
    'utm.menu_link_tracker_root',
    'project_todo.menu_todo_todos',
    'mail.main_menu_discuss',
    'base.menu_apps',
    'base_setup.menu_config',
    'base.menu_administration',
    'hr.menu_hr_root',
]


def _restrict_odoo_menus(env):
    """Oculta menús Odoo irrelevantes dejándolos solo para manager + admin.

    Tolerante a módulos no instalados: cada ref usa raise_if_not_found=False,
    de modo que un menú ausente simplemente se salta.
    """
    manager = env.ref('tms.group_tms_manager', raise_if_not_found=False)
    system = env.ref('base.group_system', raise_if_not_found=False)
    group_ids = [g.id for g in (manager, system) if g]
    if not group_ids:
        return
    for xmlid in _MENUS_TO_RESTRICT:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.write({'group_ids': [(6, 0, group_ids)]})


def post_init_hook(env):
    """Hook post-instalación (Odoo 19 pasa `env`). Solo al instalar (-i tms).

    - Quita fleet_group_user a usuarios que solo tienen group_tms_user.
    - Restringe menús Odoo irrelevantes (antes en data/tms_menu_cleanup.xml,
      movido aquí para tolerar módulos ausentes en instalación limpia).
    """
    env['res.users']._remove_fleet_group_from_tms_users()
    _restrict_odoo_menus(env)
    return True
