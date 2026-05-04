# HANDOFF.md — Fix PR #20 Blockers
# Generado por Claude Web — 2026-05-04
# Ejecutar en: /Users/macbookpro/odoo/odoo19ce/proyectos/tms
# Rama: feat/v2.3.3-liquidacion

## CONTEXTO

PR #20 tiene 4 blockers identificados en code review. Este prompt los corrige
uno por uno antes de mergear a main.

NO hacer commit hasta que Mois confirme que todo está bien.

---

## BLOCKER 1 — Eliminar fix_views.sh y corregir causa raíz

### Problema
`fix_views.sh` parcha la BD con SQL crudo porque Odoo no carga la vista
correcta de `tms.liquidacion`. La causa raíz es que hay conflicto de
`view_id` en el `ir.act_window` de liquidación.

### Fix
1. Leer `views/tms_liquidacion_views.xml` — verificar que el `action_tms_liquidaciones`
   NO tiene `<field name="view_id">` hardcodeado (eso causaría el conflicto).
2. Si lo tiene: eliminar esa línea del XML.
3. Verificar que `view_tms_liquidacion_form` tiene `priority` razonable (ya tiene 1, está bien).
4. Eliminar `fix_views.sh` del repo.

```bash
# Verificar si el action tiene view_id hardcodeado
grep -n "view_id" views/tms_liquidacion_views.xml

# Eliminar fix_views.sh
rm fix_views.sh
git rm fix_views.sh
```

---

## BLOCKER 2 — Bug @api.constrains campo inexistente en tms_expense.py

### Problema
```python
# LÍNEA INCORRECTA en models/tms_expense.py:
@api.constrains('expense_type', 'date', 'waybill_id')
# 'expense_type' no existe — el campo se llama 'expense_type_id'
# El constraint nunca se dispara → validación silenciosamente muerta
```

### Fix
En `models/tms_expense.py`, método `_check_not_closed_waybill`:

BUSCAR:
```python
@api.constrains('expense_type', 'date', 'waybill_id')
def _check_not_closed_waybill(self):
```

REEMPLAZAR CON:
```python
@api.constrains('expense_type_id', 'date', 'waybill_id')
def _check_not_closed_waybill(self):
```

Verificar con:
```bash
python3 -m py_compile models/tms_expense.py && echo "OK"
```

---

## BLOCKER 3 — Duplicación de cómputos waybill/liquidación

### Problema
`net_profit`, `profit_margin`, `advance_total`, `expense_total`, `settlement_balance`
están calculados de forma independiente en AMBOS modelos:
- `tms_waybill.py` → incluye gastos en estado `draft` en `cost_real_total`
- `tms_liquidacion.py` → solo incluye gastos `approved`+`paid`

Esto produce números distintos para el mismo viaje según dónde se mire.

### Fix — Unificar criterio en tms_waybill.py

El waybill debe ser consistente con la liquidación: solo contar gastos
`approved` y `paid` (no `draft`) en `_compute_cost_real_total`.

En `models/tms_waybill.py`, método `_compute_cost_real_total`:

BUSCAR:
```python
        for record in self:
            total = sum(
                expense.amount
                for expense in record.expense_ids
                if expense.state in ['draft', 'approved', 'paid']
            )
            record.cost_real_total = total
```

REEMPLAZAR CON:
```python
        for record in self:
            # Solo gastos aprobados y pagados — consistente con tms.liquidacion
            total = sum(
                expense.amount
                for expense in record.expense_ids
                if expense.state in ['approved', 'paid']
            )
            record.cost_real_total = total
```

Verificar con:
```bash
python3 -m py_compile models/tms_waybill.py && echo "OK"
```

---

## BLOCKER 4 — res_config_settings_views.xml grupo incorrecto

### Problema
```xml
<!-- El PR cambió esto: -->
groups="base.group_system"   ← ORIGINAL correcto
<!-- A esto: -->
groups="tms.group_tms_user"  ← INCORRECTO — expone API keys a todos los usuarios
```

Cualquier usuario TMS puede ver las credenciales del PAC, TollGuru API key,
certificados CSD. Es un problema de seguridad grave.

### Fix
En `views/res_config_settings_views.xml`, última línea:

BUSCAR:
```xml
    <menuitem id="menu_tms_config_settings" name="Ajustes" parent="menu_tms_config" sequence="0" action="action_tms_config_settings" groups="tms.group_tms_user"/>
```

REEMPLAZAR CON:
```xml
    <menuitem id="menu_tms_config_settings" name="Ajustes" parent="menu_tms_config" sequence="0" action="action_tms_config_settings" groups="tms.group_tms_manager"/>
```

Nota: Se cambia a `tms.group_tms_manager` (no `base.group_system`) para que
el manager TMS pueda configurar las APIs sin necesitar ser admin del sistema.

---

## BONUS — Limpiezas adicionales (warnings del review)

### W1 — Eliminar ir_ui_menu_tms.py (archivo muerto)
```bash
rm models/ir_ui_menu_tms.py
git rm models/ir_ui_menu_tms.py
# Quitar también de models/__init__.py si está importado
grep -n "ir_ui_menu_tms" models/__init__.py
```

### W2 — Agregar mail.thread a tms_driver_advance o quitar tracking
Dos opciones — elegir la más simple:

**Opción A (recomendada): Quitar tracking=True** — el modelo es simple, no necesita chatter
En `models/tms_driver_advance.py`:
- Eliminar `tracking=True` de todos los campos
- NO agregar `_inherit = ['mail.thread', 'mail.activity.mixin']`

**Opción B: Agregar mail.thread** — si se quiere historial de cambios
```python
_inherit = ['mail.thread', 'mail.activity.mixin']
```
Y agregar chatter en la vista de anticipo.

---

## VALIDACIÓN FINAL

Después de los 4 fixes + limpiezas:

```bash
# 1. Verificar compilación Python
python3 -m py_compile models/tms_expense.py
python3 -m py_compile models/tms_waybill.py
python3 -m py_compile models/tms_liquidacion.py
python3 -m py_compile models/tms_driver_advance.py

# 2. Verificar que fix_views.sh y ir_ui_menu_tms.py no existen
ls fix_views.sh 2>&1        # debe decir "No such file"
ls models/ir_ui_menu_tms.py 2>&1   # debe decir "No such file"

# 3. Actualizar módulo
cd /Users/macbookpro/odoo/odoo19ce
odoo-19.0/.venv/bin/python odoo-19.0/odoo-bin -c proyectos/tms/odoo.conf -u tms -d tms_v2 --stop-after-init

# 4. Revisar log
grep -n "ERROR\|WARNING" proyectos/tms/odoo.log | tail -30

# 5. Verificar manualmente en browser localhost:8019:
# - Menú Operaciones → Liquidaciones carga sin error
# - Abrir un waybill en in_transit → tiene smart button Liquidación
# - Menú Configuración → Ajustes NO visible para usuario normal (solo manager)
# - Crear un gasto en estado draft → NO aparece en cost_real_total del waybill
```

## REPORTE ESPERADO

Al terminar cada bloque, reportar:
✅ BLOCKER 1 resuelto: fix_views.sh eliminado, causa raíz corregida
✅ BLOCKER 2 resuelto: expense_type_id corregido en constrains
✅ BLOCKER 3 resuelto: cost_real_total unificado (solo approved+paid)
✅ BLOCKER 4 resuelto: Ajustes restaurado a group_tms_manager
✅ W1 resuelto: ir_ui_menu_tms.py eliminado
✅ W2 resuelto: tracking limpiado en tms_driver_advance

NO hacer commit ni push hasta confirmación de Mois.
