import psycopg2
import json

conn = psycopg2.connect('dbname=tms')
cur = conn.cursor()

arch_dict = {
    "en_US": """<form string="Scheduled Action">
                </form>"""
}

cur.execute('UPDATE ir_ui_view SET arch_db = %s WHERE id = 30', (json.dumps(arch_dict),))
conn.commit()
cur.close()
conn.close()
print("View 30 updated successfully")
