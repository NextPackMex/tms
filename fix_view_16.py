import psycopg2
import json

conn = psycopg2.connect('dbname=tms')
cur = conn.cursor()

arch_dict = {
    "en_US": """<form string="Server Action">
                    <header invisible="context.get('is_modal')">
                        <button name="create_action" string="Create Contextual Action" type="object"
                                class="btn-primary"
                                invisible="binding_model_id"
                                help="Display an option in the 'More' top-menu in order to run this action."/>
                        <button name="unlink_action" string="Remove Contextual Action" type="object"
                                invisible="not binding_model_id"
                                help="Remove 'More' top-menu contextual action related to this action"/>
                        <button name="run" string="Run" type="object"
                                class="btn-primary"
                                invisible="model_name != 'ir.actions.server' or state != 'code'"
                                help="Run this action manually."/>
                        <button name="history_wizard_action" string="Code History" type="object"
                                invisible="not show_code_history"
                                help="View code history and restore a previous version"/>
                    </header>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                        </div>
                        <h1 class="oe_title">
                            <field name="automated_name" invisible="1"/>
                            <field name="name" placeholder="Set an explicit name"/>
                        </h1>
                    </sheet>
                </form>"""
}

cur.execute('UPDATE ir_ui_view SET arch_db = %s WHERE id = 16', (json.dumps(arch_dict),))
conn.commit()
cur.close()
conn.close()
print("View 16 updated successfully")
