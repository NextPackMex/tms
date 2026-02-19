/Users/macbookpro/odoo/odoo19ce/venv/bin/python3 /Users/macbookpro/odoo/odoo19ce/odoo-19.0/odoo-bin shell \
    -c /Users/macbookpro/odoo/odoo19ce/proyectos/tms/odoo.conf \
    -d tms_nuevo \
    --no-http \
    --shell-interface=python \
    < /Users/macbookpro/odoo/odoo19ce/proyectos/tms/verify_tms_fixes.py \
    > /Users/macbookpro/odoo/odoo19ce/proyectos/tms/verify_tms_fixes.log 2>&1

/Users/macbookpro/odoo/odoo19ce/venv/bin/python3 /Users/macbookpro/odoo/odoo19ce/odoo-19.0/odoo-bin shell \
    -c /Users/macbookpro/odoo/odoo19ce/proyectos/tms/odoo.conf \
    -d tms_nuevo \
    --no-http \
    --shell-interface=python \
    < /Users/macbookpro/odoo/odoo19ce/proyectos/tms/verify_etapa_2_0_2.py \
    > /Users/macbookpro/odoo/odoo19ce/proyectos/tms/verify_etapa_2_0_2.log 2>&1
