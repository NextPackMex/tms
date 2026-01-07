import odoo
from odoo import api, SUPERUSER_ID

conf_file = '/Users/macbookpro/odoo/odoo19ce/proyectos/tms/odoo.conf'
odoo.tools.config.parse_config(['-c', conf_file])
db_name = 'tms'

registry = odoo.registry(db_name)
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    user = env['res.users'].browse(2)
    if user.exists():
        user.password = 'admin'
        cr.commit()
        print(f"EXITO: Contraseña de {user.login} cambiada a 'admin'")
    else:
        print("ERROR: El usuario ID 2 no existe.")
