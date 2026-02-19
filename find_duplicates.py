file_path = '/Users/macbookpro/odoo/odoo19ce/proyectos/tms/models/tms_waybill.py'
output_path = '/Users/macbookpro/odoo/odoo19ce/proyectos/tms/dupes.txt'
try:
    with open(file_path, 'r') as f:
        lines = f.readlines()

    with open(output_path, 'w') as out:
        for i, line in enumerate(lines, 1):
            if 'def _onchange_route_id' in line:
                out.write(f"{i}: {line.strip()}\n")
            if 'company_id =' in line: # simplistic check
                 # Need to check fleet vehicle too, but let's focus on waybill
                 pass 

    print(f"Done writing to {output_path}")

except Exception as e:
    with open(output_path, 'w') as out:
        out.write(f"Error: {e}")
