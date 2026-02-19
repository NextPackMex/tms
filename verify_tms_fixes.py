import logging
import sys
# Initialize logger
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

def run_verification(env):
    """
    Verifica que el módulo TMS esté instalado y los fixes funcionen.
    """
    with open('/Users/macbookpro/odoo/odoo19ce/proyectos/tms/verification_result.txt', 'w') as f:
        f.write(">>> INICIANDO VERIFICACIÓN DE FIXES TMS <<<\n")
        
        # 1. Verificar si el módulo está instalado
        tms_module = env['ir.module.module'].search([('name', '=', 'tms')])
        if not tms_module:
            f.write("!!! Módulo TMS no encontrado en ir.module.module !!!\n")
            return
        
        f.write(f"Estado del módulo TMS: {tms_module.state}\n")
        
        if tms_module.state != 'installed':
            f.write("Intentando instalar/actualizar módulo TMS...\n")
            try:
                tms_module.button_immediate_upgrade()
                env.cr.commit()
                f.write("Instalación/Actualización solicitada correctamente.\n")
            except Exception as e:
                f.write(f"Error al intentar instalar: {e}\n")
                
        # 2. Verificar Modelos Clave
        try:
            env['tms.waybill']
            f.write("Modelo tms.waybill: OK\n")
        except KeyError:
            f.write("Modelo tms.waybill: FALTA\n")
            return

        try:
            env['tms.waybill.line']
            f.write("Modelo tms.waybill.line: OK\n")
        except KeyError:
            f.write("Modelo tms.waybill.line: FALTA\n")

        # 4. Crear un Waybill de prueba
        f.write("Intentando crear un Waybill de prueba...\n")
        try:
            company = env.company
            partner = env['res.partner'].search([], limit=1)
            vehicle = env['fleet.vehicle'].search([('tms_is_trailer', '=', False)], limit=1)
            
            if not partner:
                partner = env['res.partner'].create({'name': 'Test Partner', 'company_id': False})
                
            waybill = env['tms.waybill'].create({
                'partner_invoice_id': partner.id,
                'partner_origin_id': partner.id,
                'partner_dest_id': partner.id,
                'vehicle_id': vehicle.id if vehicle else False,
            })
            f.write(f"Waybill creado exitosamente: {waybill.name} (ID: {waybill.id})\n")
            f.write(f"Estado inicial: {waybill.state}\n")
            
            line_vals = {
                'waybill_id': waybill.id,
                'description': 'Mercancía de prueba',
                'weight_kg': 100,
            }
            # Verificar campos nuevos
            if hasattr(env['tms.waybill.line'], 'material_peligroso_id'):
                 f.write("Campo material_peligroso_id: OK\n")
            else:
                 f.write("Campo material_peligroso_id: FALTA\n")

            line = env['tms.waybill.line'].create(line_vals)
            f.write("Línea creada exitosamente.\n")

            env.cr.rollback()
            f.write("Rollback realizado. Test finalizado.\n")

        except Exception as e:
            f.write(f"Error durante la prueba de creación: {e}\n")
            import traceback
            traceback.print_exc(file=f)

        f.write(">>> FIN DE VERIFICACIÓN <<<\n")

if __name__ == '__main__':
    # Boilerplate para ejecutar en shell de Odoo
    # Se asume que este script se corre con: odoo-bin shell ... < verify_tms_fixes.py
    # O se importa. 
    # Para simplificar, usaremos el objeto 'env' que ya está disponible en el shell de Odoo.
    if 'env' in globals():
        run_verification(env)
