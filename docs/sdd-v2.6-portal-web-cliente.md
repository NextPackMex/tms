# SDD — V2.6: Portal Web Cliente

**Módulo:** tms  
**Fecha:** 2026-05-07  
**Branch:** `feat/v2.6-portal-cliente`  
**Prioridad:** Alta — prerequisito para V2.8 (SaaS)  
**Modelo sugerido:** `claude-opus-4-7`

---

## AUDITORÍA PREVIA — QUÉ YA EXISTE

| Componente | Estado | Archivo |
|---|---|---|
| Ruta `/my/waybills/<id>` — detalle | ✅ Existe | `controllers/portal.py` |
| Firma digital (canvas + modal) | ✅ Existe | `tms_portal_templates.xml` |
| Rechazo con motivo | ✅ Existe | `controllers/portal.py` |
| Descarga PDF | ✅ Existe | `controllers/portal.py` |
| `tms.tracking.event` (8 tipos, lat/long) | ✅ Existe | `models/tms_tracking_event.py` |
| `portal.mixin` en tms.waybill | ✅ Existe | `models/tms_waybill.py` |
| `account_move_tms.py` (vínculo waybill↔factura) | ✅ Existe | `models/account_move_tms.py` |
| **Lista de viajes `/my/waybills`** | ❌ No existe | — |
| **Línea de tiempo tracking en portal** | ❌ No existe | — |
| **Descarga XML CFDI Ingreso** | ❌ No existe | — |
| **Contador en home portal** | ⚠️ Parcial — solo count | `controllers/portal.py` |

---

## PROBLEMA

El cliente (receptor de flete) no puede:
1. Ver el historial completo de sus viajes desde el portal
2. Ver el estado de avance en tiempo real (tracking)
3. Descargar el XML del CFDI Ingreso para su contabilidad

---

## SOLUCIÓN

Tres adiciones mínimas y precisas sobre la infraestructura existente:

### 1. Lista de viajes (`/my/waybills`)
Nueva ruta que muestra todos los viajes del cliente con paginación, filtros de estado y búsqueda por folio. Sin tocar la ruta de detalle existente.

### 2. Línea de tiempo de tracking en detalle
Nueva sección en `tms_portal_templates.xml` que muestra los `tms.tracking.event` del waybill ordenados cronológicamente como timeline vertical. Solo visible cuando `state in ('in_transit', 'arrived', 'closed')`.

### 3. Descarga XML del CFDI Ingreso
Nueva ruta `/my/waybills/<id>/xml` que retorna el XML del CFDI Ingreso si existe, validando acceso + empresa. Botón en sidebar del detalle, visible solo cuando hay factura timbrada vinculada.

---

## CAMBIOS

### controllers/portal.py — MODIFICAR

#### Método nuevo: `portal_my_waybills_list`
```python
@http.route(['/my/waybills', '/my/waybills/page/<int:page>'],
            type='http', auth='user', website=True)
def portal_my_waybills_list(self, page=1, state=None, search=None, **kw):
    """
    Lista paginada de viajes del cliente en el portal.
    Filtra por partner_invoice_id del usuario logueado.
    Soporta filtro por estado y búsqueda por folio.
    """
```

**Campos que pasa al template:**
- `waybills` — recordset paginado (10 por página)
- `page_count` — total de páginas
- `pager` — objeto pager estándar de Odoo
- `state_filter` — estado seleccionado
- `search` — texto de búsqueda
- `states` — lista de estados para el filtro

#### Método nuevo: `portal_waybill_xml`
```python
@http.route(['/my/waybills/<int:waybill_id>/xml'],
            type='http', auth='public', website=True)
def portal_waybill_xml(self, waybill_id, access_token=None, **kw):
    """
    Descarga el XML del CFDI Ingreso vinculado al waybill.
    Valida acceso + empresa. Solo disponible si existe factura timbrada.
    Retorna el archivo con Content-Disposition: attachment.
    Nombre del archivo: {folio}-cfdi.xml
    """
```

#### Modificar: `portal_my_waybill`
Agregar al dict `values`:
```python
# Buscar factura TMS timbrada vinculada al waybill
# IMPORTANTE: verificar nombre exacto del campo con grep antes de implementar
invoice = waybill_sudo.tms_invoice_ids.filtered(
    lambda m: m.tms_cfdi_status == 'timbrado'
).sorted('id', reverse=True)[:1]
values['waybill_has_cfdi_ingreso'] = bool(invoice and invoice.tms_cfdi_xml)
```

### views/tms_portal_templates.xml — MODIFICAR

#### Template nuevo: `portal_my_waybills_list`
Lista de viajes con:
- Tabla responsiva: Folio | Ruta | Estado (badge) | Fecha | Total | Acción
- Filtros de estado (select o tabs)
- Buscador por folio
- Paginador estándar Odoo (`request.website.pager()`)
- Mensaje vacío si no hay viajes

#### Sección nueva en `portal_my_waybill`: timeline de tracking
Insertar antes de la sección "Comunicación":
```xml
<t t-if="waybill.state in ('in_transit', 'arrived', 'closed')
         and waybill.tracking_event_ids">
    <!-- Timeline vertical de eventos -->
</t>
```

Cada evento muestra:
- Ícono según tipo (fa-play inicio, fa-map-marker ubicación, fa-flag-checkered destino, fa-warning problema)
- Fecha y hora formateada
- Descripción del tipo + notas
- Si tiene lat/long → enlace "Ver en mapa" a `maps.google.com/maps?q=lat,lon`

#### Botón XML en sidebar del detalle
En el bloque de CTAs del sidebar, después del botón PDF:
```xml
<t t-if="waybill_has_cfdi_ingreso">
    <a t-attf-href="/my/waybills/{{ waybill.id }}/xml?access_token={{ token }}"
       class="btn btn-outline-secondary w-100 mt-2">
        <i class="fa fa-file-code-o"/> Descargar XML CFDI
    </a>
</t>
```

---

## ACCEPTANCE CRITERIA

| ID | Criterio |
|---|---|
| AC-01 | Cliente logueado ve `/my/waybills` con lista de sus viajes (solo los suyos) |
| AC-02 | Lista muestra: folio, ruta (origen→destino), estado con badge de color, fecha, total |
| AC-03 | Filtro por estado funciona correctamente |
| AC-04 | Búsqueda por folio retorna resultados correctos |
| AC-05 | Paginación funciona con 10 registros por página |
| AC-06 | Sin viajes muestra mensaje "No tienes viajes registrados" |
| AC-07 | Timeline de tracking visible en estados `in_transit`, `arrived`, `closed` |
| AC-08 | Timeline oculto si no hay eventos de tracking |
| AC-09 | Cada evento muestra tipo, fecha/hora y notas |
| AC-10 | Si evento tiene lat/long, muestra enlace "Ver en mapa" → Google Maps |
| AC-11 | Botón "Descargar XML CFDI" visible solo cuando hay factura timbrada |
| AC-12 | Descarga XML retorna archivo `.xml` con nombre `{folio}-cfdi.xml` |
| AC-13 | Usuario sin acceso al waybill recibe 404 (no 500) |
| AC-14 | Cliente de Empresa A no puede ver waybills de Empresa B (multiempresa) |
| AC-15 | Home portal muestra contador de viajes con enlace a `/my/waybills` |

---

## UPGRADE COMMAND

```bash
# Solo requiere actualizar (XML nuevo + rutas nuevas)
python3 odoo-bin -c odoo.conf -u tms -d tms_v2 --stop-after-init
python3 odoo-bin -c odoo.conf
```

---

## CONTEXT BLUEPRINT PARA CLAUDE CODE

### Modelos involucrados
- `tms.waybill` — modelo principal, ya tiene `portal.mixin`
- `tms.tracking.event` — `waybill_id`, `name`, `date`, `latitude`, `longitude`, `notes`
- `account.move` (extendido) — `tms_waybill_ids`, verificar campos con grep

### File Manifest

| Archivo | Acción | Qué cambiar |
|---|---|---|
| `controllers/portal.py` | Modificar | Agregar `portal_my_waybills_list` y `portal_waybill_xml`. Modificar `portal_my_waybill` para pasar `waybill_has_cfdi_ingreso` |
| `views/tms_portal_templates.xml` | Modificar | Agregar template lista, sección timeline, botón XML en sidebar |

**Solo 2 archivos. Sin modelos nuevos. Sin campos nuevos.**

### Grep OBLIGATORIO antes de implementar
```bash
# Verificar nombre exacto del campo XML en account.move
grep -n "tms_cfdi_xml\|tms_cfdi_status\|cfdi_xml\|cfdi_status" models/account_move_tms.py | head -20

# Verificar Many2many inverso waybill → facturas
grep -n "tms_invoice\|invoice_ids\|move_ids\|tms_waybill_ids" models/tms_waybill.py | head -20

# Verificar campo tracking_event_ids en waybill
grep -n "tracking_event_ids" models/tms_waybill.py | head -5

# Verificar campos de ruta (origin_zip, dest_zip, origin_city_name, dest_city_name)
grep -n "origin_city\|dest_city\|route_name" models/tms_waybill.py | head -10
```

### Seguridad
- Sin cambios en `ir.model.access.csv`
- El controlador ya implementa `_check_waybill_access_and_company`
- Lista `/my/waybills` usa `auth='user'` (requiere login, no access_token)

### Tests mínimos (5 requeridos — DoD NextPack)
1. `test_portal_list_muestra_solo_viajes_propios` — cliente A no ve viajes de cliente B
2. `test_portal_list_paginacion` — más de 10 viajes genera paginación correcta
3. `test_portal_xml_descarga` — retorna bytes XML cuando hay CFDI timbrado
4. `test_portal_xml_sin_cfdi` — retorna 404 cuando no hay factura timbrada
5. `test_portal_tracking_timeline_oculto_sin_eventos` — sección invisible si no hay eventos

---

## NOTAS DE ARQUITECTURA

- **Sin Google Maps embed** — solo enlace externo `maps.google.com/maps?q=lat,lon`. Sin API key, sin costo.
- **Sin WebSocket/push** — tracking estático (recarga manual). Tiempo real con Resser es V3.0.
- **XML descarga directa** — lee `tms_cfdi_xml` del `account.move` y sirve con `Response` de Werkzeug.
- **Paginador Odoo nativo** — usar `request.website.pager()` para consistencia visual.
- **`auth='user'` en lista** — la lista requiere login. El detalle mantiene `auth='public'` + access_token para links por email.

---

*SDD generado: 2026-05-07*  
*Versión módulo base: 19.0.2.4.4*
