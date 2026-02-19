import odoo
from odoo import api, SUPERUSER_ID
import sys

def fix_schema():
    try:
        db_name = 'tms_nuevo'
        # Configure addons path just in case, though strictly not needed for raw SQL if we just use registry
        odoo.tools.config['addons_path'] = '/Users/macbookpro/odoo/odoo19ce/odoo-19.0/addons,/Users/macbookpro/odoo/odoo19ce/proyectos'
        
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            # Check if column exists
            cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='fleet_vehicle' AND column_name='tms_fuel_performance'")
            if cr.fetchone():
                print("Column tms_fuel_performance ALREADY EXISTS.")
            else:
                print("Column missing. Adding it now...")
                cr.execute("ALTER TABLE fleet_vehicle ADD COLUMN tms_fuel_performance double precision DEFAULT 2.5;")
                print("SUCCESS: Column tms_fuel_performance added.")
            
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    fix_schema()
