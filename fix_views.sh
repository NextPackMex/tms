#!/bin/bash
# fix_views.sh — Ejecutar después de cada -u tms en desarrollo
echo 'Fixing liquidacion view...'
psql -U odoo -d tms_v2 -c "
UPDATE ir_act_window
SET view_id = (
    SELECT id FROM ir_ui_view
    WHERE model = 'tms.liquidacion'
    AND name = 'tms.liquidacion.form'
    ORDER BY priority ASC
    LIMIT 1
)
WHERE res_model = 'tms.liquidacion';
"
echo 'Done.'
