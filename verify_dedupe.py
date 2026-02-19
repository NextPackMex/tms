import sys
import os
import odoo
from odoo import api, SUPERUSER_ID

def run_verification():
    try:
        # Initialize Odoo
        db_name = 'tms_nuevo' # Hardcoded from context
        odoo.tools.config['addons_path'] = '/Users/macbookpro/odoo/odoo19ce/odoo-19.0/addons,/Users/macbookpro/odoo/odoo19ce/proyectos'
        registry = odoo.registry(db_name)
        
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            print("Successfully connected to database.")
            
            # Check TmsWaybill model
            if 'tms.waybill' not in env:
                print("ERROR: tms.waybill model not found.")
                return
            
            waybill_model = env['tms.waybill']
            print("tms.waybill model found.")
            
            # Check for methods
            methods_to_check = ['action_send_email', '_check_waybill_validity', '_onchange_route_id']
            for method in methods_to_check:
                if hasattr(waybill_model, method):
                    print(f"Method {method} exists.")
                else:
                    print(f"ERROR: Method {method} missing.")

            # Attempt to instantiate (not create in DB, just new()) to check basics
            try:
                wb = waybill_model.new({})
                print("Successfully created provisional waybill.")
            except Exception as e:
                print(f"ERROR creating waybill: {e}")

            # Check TmsFleetVehicle
            fleet_model = env['fleet.vehicle']
            if 'company_id' in fleet_model._fields:
                 print("fleet.vehicle has company_id.")
            else:
                 print("ERROR: fleet.vehicle missing company_id.")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
