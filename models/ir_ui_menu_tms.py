# -*- coding: utf-8 -*-
"""
DEPRECATED: Enfoque Python para ocultar menús.

La ocultación de menús en Odoo 19 debe hacerse vía XML (data/tms_menu_cleanup.xml),
no mediante métodos @api.model llamados desde <function>.

El archivo data/tms_menu_cleanup.xml contiene la solución funcional que restringe
la visibilidad de menús a group_tms_manager y base.group_system.

Este archivo se deja como referencia histórica pero está vacío.
Ver data/tms_menu_cleanup.xml para la implementación actual.
"""
