
import odoo
from odoo import api, SUPERUSER_ID
import sys

try:
    conf_file = '/Users/macbookpro/odoo/odoo19ce/proyectos/tms/odoo.conf'
    odoo.tools.config.parse_config(['-c', conf_file])
    db_name = 'tms_nuevo'

    registry = odoo.registry(db_name)
    with registry.cursor() as cr:
        uid = SUPERUSER_ID
        env = api.Environment(cr, uid, {})
        
        print("Updating module list...")
        env['ir.module.module'].update_list()
        print("Module list updated.")
        
        tms = env['ir.module.module'].search([('name', '=', 'tms')])
        if tms:
            print(f"TMS Module Found: {tms.state}")
            print(f"Installable: {tms.state != 'uninstallable'}")
            if tms.state == 'uninstalled':
                print("Installing TMS...")
                tms.button_immediate_install()
                # Committing to save changes
                env.cr.commit()
                print("TMS Module Installed.")
            else:
                print(f"TMS already in state: {tms.state}")
        else:
            print("TMS Module NOT FOUND after update.")
            
except Exception as e:
    print(f"ERROR: {e}")
