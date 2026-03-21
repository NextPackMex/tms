# SDD — Etapa 2.5: Data Integrity + Limpieza Final

**Módulo:** `tms/` | **Fecha:** 2026-03-20 | **Prioridad:** Media | **Branch:** `feat/etapa-2.5-limpieza`
**Herramienta:** Antigravity | **Modo:** `Fast + Flash`

---

## GIT (solo primer prompt de etapa)

```bash
cd ~/odoo/proyectos/tms
git checkout main && git pull origin main
git checkout -b feat/etapa-2.5-limpieza
```

---

## PROBLEMA

La auditoría V2.5 del 2026-03-20 identificó 3 inconsistencias:

1. **Doble set de campos de licencia en `hr.employee`** — el onboarding (Paso 4) guarda en campos `tms_license_*` (Set 2) que nunca aparecen en la ficha del chofer. La ficha muestra `tms_driver_license_*` (Set 1). El usuario captura la licencia en onboarding y nunca la ve en la ficha.

2. **`t-esc` legacy en 11 líneas de reportes** — funcional pero deprecado en Odoo 19. Debe ser `t-out`.

3. **`tms_rfc` y `tms_driver_rfc` coexisten en `hr.employee`** — campo directo vs campo `related`. `xml_builder.py` usa `tms_rfc` correctamente, pero `tms_driver_rfc` es redundante y confuso.

4. **Estados waybill: 11 definidos, solo 6 deben ser visibles al usuario** — `draft`, `en_pedido`, `assigned` son estados internos de transición que no aportan valor al transportista. Deben ocultarse del Kanban y de los filtros de búsqueda, pero NO eliminarse del código (el flujo interno los sigue usando).

---

## SOLUCIÓN

### FIX-1: Unificar campos de licencia en `hr.employee`

**Campos a ELIMINAR** (Set 2 — solo en onboarding, nunca en vistas):
```python
tms_license_number      # L134
tms_license_type        # L138
tms_license_expiry      # L145
```

**Campos a CONSERVAR** (Set 1 — en vistas y en onboarding después del fix):
```python
tms_driver_license            # campo oficial
tms_driver_license_type       # campo oficial
tms_driver_license_expiration # campo oficial
```

**Cambio en onboarding:** `wizard/tms_onboarding_wizard.py` Paso 4 debe mapear a los campos del Set 1.

---

### FIX-2: Reemplazar `t-esc` por `t-out` en reportes

Archivos a modificar:
- `reports/tms_cotizacion_report_template.xml` — líneas 54, 132, 138, 144, 179, 183, 189, 195, 205
- `reports/tms_waybill_report.xml` — líneas 54, 68

Cambio: `t-esc=` → `t-out=` (solo el atributo, el valor no cambia)

---

### FIX-3: Eliminar `tms_driver_rfc` de `hr.employee`

`tms_driver_rfc` es un campo `related` redundante. `xml_builder.py` ya usa `tms_rfc` directamente.

**Acción:**
- Eliminar definición de `tms_driver_rfc` en `models/hr_employee.py`
- Verificar que ninguna vista o reporte lo referencie antes de eliminar:
```bash
grep -rn "tms_driver_rfc" views/ reports/ wizard/ services/
```
- Si alguna vista lo usa → reemplazar por `tms_rfc`

---

### FIX-4: Simplificar estados visibles en Kanban y filtros

**Estados que se OCULTAN** de la UI (no se eliminan del código):

| Estado | Clave |
|---|---|
| Solicitud | `draft` |
| En Pedido | `en_pedido` |
| Por Asignar | `assigned` |

**Estados VISIBLES** (los 6 del transportista):

| # | Estado | Clave |
|---|---|---|
| 1 | Cotizado | `cotizado` |
| 2 | Aprobado | `aprobado` |
| 3 | Carta Porte | `waybill` |
| 4 | En Tránsito | `in_transit` |
| 5 | En Destino | `arrived` |
| 6 | Facturado | `closed` |

**Cambios en vistas:**
- `views/tms_waybill_views.xml` — En la vista Kanban, agregar `invisible="state in ('draft', 'en_pedido', 'assigned')"` a las columnas de esos estados
- En el `<search>` — los filtros de estado solo muestran los 6 visibles

> ⚠️ El flujo interno (`action_confirm`, `action_assign`, etc.) sigue usando los estados ocultos sin cambio. Solo cambia la presentación.

---

## ARCHIVOS A MODIFICAR

| Archivo | Tipo de cambio |
|---|---|
| `models/hr_employee.py` | Eliminar Set 2 licencia (3 campos) + eliminar `tms_driver_rfc` |
| `wizard/tms_onboarding_wizard.py` | Paso 4 → mapear a campos Set 1 |
| `wizard/tms_onboarding_wizard_views.xml` | Actualizar nombres de campo en el XML del Paso 4 |
| `reports/tms_cotizacion_report_template.xml` | 9× `t-esc` → `t-out` |
| `reports/tms_waybill_report.xml` | 2× `t-esc` → `t-out` |
| `views/tms_waybill_views.xml` | Kanban + filtros → solo 6 estados visibles |

**NO tocar:** `services/xml_builder.py`, `models/tms_waybill.py` (estados), `security/`

---

## ACCEPTANCE CRITERIA

| ID | Criterio |
|---|---|
| AC-01 | El onboarding Paso 4 captura licencia del chofer y los datos aparecen en la ficha `hr.employee` sin reescribir |
| AC-02 | No existe `tms_license_number`, `tms_license_type`, `tms_license_expiry` en ningún archivo Python ni XML |
| AC-03 | No existe `tms_driver_rfc` en ningún archivo Python ni XML |
| AC-04 | Los 11 reportes con `t-esc` usan `t-out` y los PDFs siguen generándose correctamente |
| AC-05 | El Kanban de waybills muestra solo 6 columnas (sin draft/en_pedido/assigned) |
| AC-06 | Los filtros de búsqueda por estado muestran solo los 6 estados del transportista |
| AC-07 | El flujo interno de estados sigue funcionando sin errores (crear cotización → timbrar → cerrar) |
| AC-08 | `python3 -m py_compile` sin errores en todos los archivos modificados |
| AC-09 | Odoo arranca sin WARNING ni ERROR en `odoo.log` |

---

## UPGRADE COMMAND

```bash
# Cambios de campos → requiere actualización
python3 odoo-bin -c odoo.conf -u tms -d tms_v2 --stop-after-init
python3 odoo-bin -c odoo.conf
```

---

## ROLLBACK

```bash
git checkout main
python3 odoo-bin -c odoo.conf -u tms -d tms_v2 --stop-after-init
```

---

## Context Blueprint

### File Manifest

| Archivo | Acción |
|---|---|
| `models/hr_employee.py` | Modificar — eliminar 4 campos |
| `wizard/tms_onboarding_wizard.py` | Modificar — Paso 4 |
| `wizard/tms_onboarding_wizard_views.xml` | Modificar — nombres de campos |
| `reports/tms_cotizacion_report_template.xml` | Modificar — t-esc → t-out |
| `reports/tms_waybill_report.xml` | Modificar — t-esc → t-out |
| `views/tms_waybill_views.xml` | Modificar — Kanban + Search |

### Campos eliminados

```python
# hr_employee.py — ELIMINAR estos 4 campos:
tms_license_number       # Set 2, redundante
tms_license_type         # Set 2, redundante
tms_license_expiry       # Set 2, redundante
tms_driver_rfc           # related redundante de tms_rfc
```

### Campos oficiales que permanecen

```python
# hr_employee.py — CONSERVAR:
tms_rfc                       # RFC directo del chofer (usado en xml_builder)
tms_driver_license            # Número de licencia oficial
tms_driver_license_type       # Tipo de licencia oficial
tms_driver_license_expiration # Vencimiento oficial
```
