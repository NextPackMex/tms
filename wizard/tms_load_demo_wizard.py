# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
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
        
        # Usamos convert_file de Odoo tools
        # convert_file(env, module, filename, idref, mode='update', noupdate=False)
        try:
            # Obtenemos la ruta absoluta del archivo usando get_module_resource si fuera necesario, 
            # pero convert_file suele manejar rutas relativas si se pasa el package correcto.
            # Sin embargo, convert_file espera 'filename' como ruta absoluta o relativa manejada por el framework.
            # La forma más segura llamando desde código es obtener path.
            
            from odoo.modules.module import get_module_resource
            fp = get_module_resource(module_name, filename)
            
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
            raise models.ValidationError(_("Ocurrió un error al cargar los datos: %s") % str(e))
