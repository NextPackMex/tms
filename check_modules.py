
try:
    with open('/Users/macbookpro/odoo/odoo19ce/proyectos/tms/module_status.txt', 'w') as f:
        tms = env['ir.module.module'].search([('name', '=', 'tms')])
        if tms:
            f.write(f"TMS: state={tms.state}\n")
        else:
            f.write("TMS: Not found in database\n")

        deps = ['base', 'fleet', 'account', 'contacts', 'board', 'mail', 'portal', 'web', 'website', 'sale_management', 'hr', 'web_tour']
        for dep in deps:
            mod = env['ir.module.module'].search([('name', '=', dep)])
            if mod:
                f.write(f"Dep {dep}: state={mod.state}\n")
            else:
                f.write(f"Dep {dep}: Not found in database\n")
except Exception as e:
    with open('/Users/macbookpro/odoo/odoo19ce/proyectos/tms/module_status.txt', 'w') as f:
        f.write(f"ERROR: {e}\n")
import sys
sys.exit()
