# -*- coding: utf-8 -*-
import os
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.modules.module import get_module_path
from odoo.tools import convert_file
import logging

_logger = logging.getLogger(__name__)

class TmsLoadDemoWizard(models.TransientModel):
    _name = 'tms.load.demo.wizard'
    _description = 'Wizard para Cargar Datos Demo TMS'

    message = fields.Text(
        string="Información", 
        readonly=True, 
        default="Este asistente cargará datos de prueba (Choferes, Tractores, Remolques, Rutas, etc.) en su sistema.\n\n"
                "Úselo si NO seleccionó 'Cargar datos de prueba' al crear la base de datos o si desea regenerar los datos."
    )

    def action_load_demo_data(self):
        """
        Carga programática del archivo de demo expanded.
        """
        self.ensure_one()
        _logger.info("Iniciando carga manual de datos demo TMS...")
        
        # Nombre del módulo
        module_name = 'tms'
        # Ruta relativa del archivo dentro del módulo
        filename = 'demo/tms_expanded_demo.xml'
        
        try:
            # Obtener la ruta del módulo y construir la ruta completa al archivo
            module_path = get_module_path(module_name)
            fp = os.path.join(module_path, filename)
            
            if not fp:
                raise UserError(_("No se encontró el archivo de datos demo: %s") % filename)
                
            convert_file(self.env, module_name, fp, {}, mode='init', noupdate=False)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Éxito'),
                    'message': _('Datos demo cargados correctamente.'),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
            
        except Exception as e:
            _logger.error("Error cargando datos demo TMS: %s", str(e))
            raise ValidationError(_("Ocurrió un error al cargar los datos: %s") % str(e))
