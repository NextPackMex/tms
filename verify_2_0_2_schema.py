import sys
import odoo
from odoo import api, SUPERUSER_ID

def run_verification():
    try:
        db_name = 'tms_nuevo'
        odoo.tools.config['addons_path'] = '/Users/macbookpro/odoo/odoo19ce/odoo-19.0/addons,/Users/macbookpro/odoo/odoo19ce/proyectos'
        registry = odoo.registry(db_name)
        
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            print("Successfully connected to database.")
            
            # Check fields
            if 'tms_num_axles' in env['fleet.vehicle']._fields:
                print("SUCCESS: tms_num_axles field found in fleet.vehicle model definition.")
                # Verify column in DB
                cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='fleet_vehicle' AND column_name='tms_num_axles'")
                if cr.fetchone():
                     print("SUCCESS: tms_num_axles column found in database table fleet_vehicle.")
                     sys.exit(0) # Success
                else:
                     print("ERROR: tms_num_axles column MISSING in database table fleet_vehicle.")
                     sys.exit(1) # Failure
            else:
                print("ERROR: tms_num_axles field MISSING in fleet.vehicle model definition.")
                sys.exit(1) # Failure

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
