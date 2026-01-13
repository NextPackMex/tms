import odoo
from odoo import api, SUPERUSER_ID

conf_file = '/Users/macbookpro/odoo/odoo19ce/proyectos/tms/odoo.conf'
odoo.tools.config.parse_config(['-c', conf_file])
db_name = 'tms_nuevo'

registry = odoo.registry(db_name)
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Intentar con mvelez37@gmail.com
    user = env['res.users'].search([('login', '=', 'mvelez37@gmail.com')], limit=1)
    if not user:
        # Intentar con admin
        user = env['res.users'].search([('login', '=', 'admin')], limit=1)
    
    if user:
        user.password = 'admin'
        cr.commit()
        print(f"EXITO: Contraseña del usuario '{user.login}' (ID: {user.id}) ha sido cambiada a 'admin'")
    else:
        # Mostrar usuarios disponibles para ayudar al usuario
        all_users = env['res.users'].search([])
        print("ERROR: No se encontró al usuario 'mvelez37@gmail.com' ni 'admin'.")
        print("Usuarios encontrados en la base de datos:")
        for u in all_users:
            print(f"- ID: {u.id}, Login: {u.login}, Name: {u.name}")
