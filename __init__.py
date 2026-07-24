# -*- coding: utf-8 -*-
from . import models
from . import controllers
from . import wizard
from . import services

# Exponer el hook post-instalación a nivel de paquete para que Odoo lo
# encuentre (manifest: 'post_init_hook': 'post_init_hook').
from .__init_hooks__ import post_init_hook
