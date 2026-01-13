import odoo
from odoo import api, SUPERUSER_ID
from odoo.tools import convert_file

conf_file = '/Users/macbookpro/odoo/odoo19ce/proyectos/tms/odoo.conf'
odoo.tools.config.parse_config(['-c', conf_file])
db_name = 'tms_nuevo'

registry = odoo.modules.registry.Registry.new(db_name)
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Path to the file matches the module structure relative to addons_path or absolute
    # We use absolute for certainty in this script context, or relative if mapped correctly.
    # The file is at: /Users/macbookpro/odoo/odoo19ce/proyectos/tms/demo/tms_expanded_demo.xml
    
    filename = '/Users/macbookpro/odoo/odoo19ce/proyectos/tms/demo/tms_expanded_demo.xml'
    
    print(f"Loading {filename} into {db_name}...")
    try:
        convert_file(env.cr, 'tms', filename, {}, mode='init', kind='data')
        print("SUCCESS: Demo data loaded.")
    except Exception as e:
        print(f"ERROR: {e}")
