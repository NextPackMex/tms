# CLAUDE.md — TMS "Hombre Camión" & Carta Porte 3.1

# ══════════════════════════════════════════════════════════════
# CONTEXTO PARA CLAUDE CODE TERMINAL / CLAUDE WEB
# Última actualización: 2026-05-07 — V2.6 Portal Web Cliente completado
# ══════════════════════════════════════════════════════════════

## 0. 🤖 Modelos de IA — Cuándo usar cuál

> Leer esto PRIMERO. El ejecutor es **Claude Code terminal** (ya NO Antigravity).

> 📌 **REGLA OBLIGATORIA — Modelo en respuesta:** Indicar el modelo en uso al inicio de CADA respuesta.
> Formato: `**Modelo:** claude-sonnet-4-6` (o el que corresponda).
> Aplica a todas las respuestas sin excepción.

> 📌 **REGLA OBLIGATORIA — Selección de modelo:** Claude Code debe inferir el modelo correcto
> según el esfuerzo de la tarea usando la tabla siguiente, SIN esperar instrucción explícita del usuario.
> Si la tarea es ambigua, elegir el modelo más capaz (Opus 4.7).

> 📌 **REGLA — Cuándo leer CLAUDE.md:**
> Leer CLAUDE.md SOLO en estos dos casos:
> 1. Al INICIO de una sesión nueva (primera vez que arranca Claude Code)
> 2. Después de `/compact` (el contexto se comprimió)
> NO leer CLAUDE.md en prompts de fix o tareas dentro de una sesión activa —
> es gasto innecesario de tokens. El contexto ya está cargado.

| Situación | Modelo |
|-----------|--------|
| Módulo nuevo, etapa completa, orquestador multi-agente | `claude-opus-4-7` |
| Integraciones API (TollGuru, PAC, CFDI, xml_builder) | `claude-opus-4-7` |
| Bug difícil, refactor tms_waybill.py, deuda técnica | `claude-opus-4-7` |
| Fix puntual, un solo archivo, campo simple | `claude-sonnet-4-6` |
| Ajuste de vista XML, label, color, fix una línea | `claude-sonnet-4-6` |
| Verificaciones, limpieza, comentarios | `claude-sonnet-4-6` |
| Commits, documentación, chores | `claude-haiku-4-5` |

```bash
# Tarea grande (etapa completa, orquestador, API)
claude --model claude-opus-4-7 "ejecuta etapa X.X.X..."

# Fix rápido (un archivo, vista, campo)
claude --model claude-sonnet-4-6 "Corrige el label del campo X en archivo Y"

# Commit / chore
claude --model claude-haiku-4-5 "git add -A && git commit -m '...'"
```

> ⚠️ Ya NO se usa Antigravity. Ejecutor: **Claude Code terminal**.
> Para imágenes / diseño visual → **Gemini Flash**.

> 📋 **Contexto estratégico completo** (roadmap, fases, módulos, semillas, ingresos):
> Lee `contexto_maestro_tms_final.md` — es la fuente de verdad del proyecto.
> Para ver el roadmap visual interactivo: abrir Claude Web y escribir "Muéstrame el roadmap".

---

## 1. Resumen del Proyecto

**Nombre:** TMS & Carta Porte 3.1 (SaaS Multi-Empresa)
**Nombre comercial:** Hombre Camión
**Versión Odoo:** 19 Community Edition
**Autor:** NextPack (nextpack.mx)
**Licencia:** LGPL-3
**Versión módulo:** 19.0.2.4.4
**Progreso actual:** ~90% — V2.6 Portal Web Cliente completado

**Qué es:** Módulo vertical completo para gestión de transporte de carga en México.
Cubre desde cotización hasta facturación, con cumplimiento fiscal (Carta Porte 3.1 / CFDI 4.0).

**Arquitectura clave:** Single Document Flow — `tms.waybill` es el modelo maestro
que fusiona Cotización + Operación + Carta Porte en un solo registro.

**Principio de negocio:** NextPack cobra por acceso, información y confianza —
nunca por intermediar dinero entre partes. Sin factoraje, sin seguros intermediados.

---

## 2. Stack Tecnológico

- **Backend:** Python 3.12+, Odoo 19 CE
- **BD:** PostgreSQL 16+ (local: `tms_v2`, puerto `localhost:8019`)
- **Frontend:** OWL (Odoo Web Library), QWeb templates
- **APIs externas:** TollGuru API v2 (activa), Google Routes API (disponible)
- **PAC:** Formas Digitales (forsedi.facturacfdi.mx — contrato activo) — para V2.2
- **Fiscal:** SAT Carta Porte 3.1, CFDI 4.0
- **Python binary:** `/Users/macbookpro/odoo/odoo19ce/odoo-19.0/.venv/bin/python /Users/macbookpro/odoo/odoo19ce/odoo-19.0/odoo-bin`
- **Config:** `/Users/macbookpro/odoo/odoo19ce/proyectos/tms/odoo.conf`
- **Upgrade:** `cd /Users/macbookpro/odoo/odoo19ce/odoo-19.0 && /Users/macbookpro/odoo/odoo19ce/odoo-19.0/.venv/bin/python odoo-bin -c /Users/macbookpro/odoo/odoo19ce/proyectos/tms/odoo.conf -u tms -d tms_v2 --stop-after-init`
- **Start:** `cd /Users/macbookpro/odoo/odoo19ce/odoo-19.0 && /Users/macbookpro/odoo/odoo19ce/odoo-19.0/.venv/bin/python odoo-bin -c /Users/macbookpro/odoo/odoo19ce/proyectos/tms/odoo.conf`

---

## 3. Arquitectura SaaS Multi-Empresa

### Regla de oro:
- **Catálogos SAT** → GLOBALES (sin `company_id`) → Compartidos entre empresas
- **Datos operativos** → PRIVADOS (con `company_id` obligatorio) → Aislados por empresa
- **APIs de rutas** → GLOBALES via `config_parameter`
- **Seguros Carta Porte** → POR EMPRESA via `related='company_id.campo'`

### Modelos GLOBALES (sin company_id):
`tms.sat.clave.prod`, `tms.sat.clave.unidad`, `tms.sat.codigo.postal`,
`tms.sat.colonia`, `tms.sat.localidad`, `tms.sat.municipio`,
`tms.sat.config.autotransporte`, `tms.sat.tipo.permiso`,
`tms.sat.embalaje`, `tms.sat.material.peligroso`, `tms.sat.figura.transporte`,
`tms.route.analytics` (datos globales de plataforma — sembrar en V2.2)

### Modelos PRIVADOS (con company_id + Record Rules):
`tms.waybill`, `tms.waybill.line`, `tms.destination`,
`fleet.vehicle`, `tms.fuel.log`, `tms.tracking.event`,
`tms.driver.settlement`, `tms.maintenance.order`, `tms.maintenance.plan`,
`tms.evidence.photo`, `tms.digital.signature`, `tms.subscription`

### Record Rule res.partner (CRÍTICA):
```python
# SIEMPRE usar este dominio para partners
['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]
```

---

## 4. Modelo Maestro: tms.waybill

### Workflow de Estados (ÚNICOS VÁLIDOS)
```
cotizado → aprobado → waybill → in_transit → arrived → closed
                                                           ↓
                                                         cancel
rejected (portal)
```

| Estado | Clave | Descripción |
|---|---|---|
| Cotizado | `cotizado` | Wizard generó pre-cotización, cliente no ha aprobado |
| Aprobado | `aprobado` | Cliente aprobó precio, pendiente datos completos |
| Carta Porte | `waybill` | Valida cumplimiento CP 3.1 completo |
| En Tránsito | `in_transit` | Ruta iniciada |
| En Destino | `arrived` | Llegó al destino |
| Facturado | `closed` | Factura creada, viaje cerrado |
| Cancelado | `cancel` | Anulado |
| Rechazado | `rejected` | Rechazado desde portal |

⚠️ NUNCA usar: `'transit'`, `'destination'`, `'carta_porte'`, `'draft'`, `'en_pedido'`, `'assigned'` — NO EXISTEN → ValueError

### Motor de Cotización (3 Propuestas)

**Propuesta A — Por Kilómetro:**
```
Total = (Distancia Base + Km Extras) × Precio/KM
```

**Propuesta B — Por Viaje (Costos + Margen):**
```
Costo Diesel = (Distancia / Rendimiento) × Precio Diesel
Costo Total  = Diesel + Casetas + Chofer + Maniobras + Otros + Comisión
Precio Venta = Costo Total / (1 - Margen%)
```

**Propuesta C — Precio Directo:**
```
Total = Monto capturado manualmente
```

`selected_proposal` determina cuál se aplica a `amount_untaxed`.

### Retención IVA 4%
Solo aplica cuando `partner_invoice_id.is_company == True`
Fundamento: Art. 1-A LIVA + Art. 3 RLIVA

### TollGuru API v2
- Endpoint: `https://apis.tollguru.com/toll/v2/origin-destination-waypoints`
- Distancia: `routes[0].summary.distance.value` metros → /1000 = km
- Duración: `routes[0].summary.duration.value` segundos → /3600 = horas
- Casetas: `routes[0].costs.tag`
- Caché en: `tms.destination`

### Tren Vehicular
`vehicle_id (tracto) + trailer1_id + dolly_id + trailer2_id`
- `tms_is_trailer = False` → tractores
- `tms_is_trailer = True` → remolques/dollys
- Domain vehicle_id: `[('tms_is_trailer', '=', False)]`

---

## 5. Estructura de Archivos — Completa

```
tms/
├── models/
│   ├── tms_waybill.py                  # MODELO MAESTRO
│   ├── tms_evidence.py                 # Evidencia fotográfica ✅ V2.4b
│   ├── tms_route_stats.py              # Rentabilidad por ruta ✅ V2.4.1
│   ├── tms_vehicle_performance.py      # Rendimiento vehículo ✅ V2.4.3
│   ├── account_move_tms.py             # CFDI Ingreso ✅ V2.3
│   └── sat_*.py                        # 12 catálogos SAT
├── views/
│   ├── tms_waybill_views.xml
│   ├── tms_evidence_views.xml          # ✅ V2.4b
│   ├── tms_portal_templates.xml        # ✅ V2.6
│   └── ...
├── controllers/
│   └── portal.py                       # ✅ V2.6
├── static/src/js/
│   ├── tms_tour.js                     # ✅ V2.5.1
│   ├── tms_help_panel.js               # ✅ V2.5.1
│   └── tms_dashboard.js               # ✅ V2.4.2
└── ...
```

---

## 6. Grupos de Seguridad

| Grupo | XML ID | Permisos |
|---|---|---|
| Usuario TMS | `group_tms_user` | CRUD operaciones (sin delete waybill) |
| Manager TMS | `group_tms_manager` | CRUD completo + configuración |
| Chofer TMS | `group_tms_driver` | Solo lectura waybill + escritura tracking |

---

## 7. Estado del Proyecto

### ✅ V2.1 — Pulido UX (COMPLETADO)
### ✅ V2.2 — Carta Porte 3.1 + Timbrado (COMPLETADO)
### ✅ V2.3 — Facturación Real (COMPLETADO — 2026-04-15)
### ✅ V2.3.2 — Cancelación CFDI Traslado (COMPLETADO — 2026-04-22)

### ✅ V2.4 — Analytics y Rendimiento
| Etapa | Nombre | Estado |
|---|---|---|
| V2.4.1 | Rentabilidad por ruta (`tms.route.stats`) | ✅ 2026-04-22 |
| V2.4.2 | Dashboard operativo + KPIs | ✅ 2026-04-23 |
| V2.4.3 | Rendimiento por vehículo | ✅ 2026-05-06 |
| V2.4b | Evidencia fotográfica (`tms.evidence.photo`) | ✅ 2026-05-06 |
| V2.4c | Firma digital simple | ✅ 2026-05-06 (ya existía) |
| V2.4d | Liquidación de choferes | ✅ 2026-05-06 (ya existía) |

### ✅ V2.5 — Limpieza (COMPLETADO — 2026-04-28)
### ✅ V2.5.1 — Tours Interactivos (COMPLETADO — 2026-05-06)
### ✅ V2.6 — Portal Web Cliente (COMPLETADO — 2026-05-07)
- Lista `/my/waybills` paginada con filtros y búsqueda
- Timeline de tracking en detalle del waybill
- Descarga XML CFDI Ingreso desde portal
- Tile "Mis Viajes" en home del portal

### 📋 Pendiente — en orden de prioridad
| Versión | Nombre | Modelo |
|---------|--------|--------|
| V2.7 | Limpieza final + QA | `claude-sonnet-4-6` |
| **V2.8** | **SaaS — PRIMER CLIENTE** 🎯 | `claude-opus-4-7` |
| V3.0 | App Flutter Chofer | Flutter/Dart |
| Fase 2 | Marketplace de cargas | Sep-Dic 2026 |

---

## 8. Issues Conocidos

| ID | Descripción | Estado |
|---|---|---|
| FIX-01 al FIX-H | Ver historial en commits anteriores | ✅ Todos resueltos |
| FIX-portal-counters | KeyError portal_counters en tile /my | ✅ 2026-05-07 — usar solo `waybill_count` |

---

## 9. Problemas Históricos (NUNCA Repetir)

> 📌 **REGLA PORTAL/FRONTEND:** Si un tile, template o componente del portal/website
> no cuadra visualmente o no funciona, **IR DIRECTO a leer el patrón en Odoo core**
> antes de intentar cualquier fix. Rutas de referencia:
> - `odoo-19.0/addons/{módulo}/views/*portal*.xml`
> - `odoo-19.0/addons/{módulo}/controllers/portal.py`
> **Nunca inventar HTML/Bootstrap custom** cuando Odoo ya tiene el patrón correcto.
> Ejemplo: `portal_docs_entry`, `placeholder_count`, `portal_client_category_enable`.
> Esta regla aplica a cualquier componente frontend, no solo al portal.

1. **Código duplicado** — Python usa la última definición silenciosamente
2. **Estados desalineados** — Selection vs métodos → ValueError
3. **Campos fantasma** — onchange referencia campos inexistentes → AttributeError
4. **required=True en modelos heredados** — Rompe registros del sistema
5. **compute store=False escribiendo store=True** — No persiste en BD
6. **Leer mal JSON TollGuru** — Usar `routes[0]`, no `route` ni `metric`
7. **widget monetary sin currency_field** — OWL error en Odoo 19
8. **Métodos RPC privados desde OWL** — Usar nombre público, nunca `_metodo()`
9. **Kanban sin t-name="card"** — Odoo 19 requiere `card`, no `kanban-box`
10. **kanban_image() no existe** — Usar `widget="image"` en field
11. **view_mode con "tree"** — Usar `"list"` en ir.actions.act_window
12. **`<tree>` en vistas** — Usar `<list>`
13. **`attrs=`** — Usar `invisible=`
14. **`portal_counters` no existe en Odoo 19 CE** — En templates QWeb del portal NO usar `portal_counters.get(...)`. Solo usar variables pasadas directamente por el controlador (ej. `waybill_count`). Causa 500 KeyError en `/my`.
15. **TransactionCase no detecta errores QWeb** — Para tests de rutas HTTP (portal, website, controllers) usar `HttpCase`, NO `TransactionCase`. TransactionCase no levanta servidor y no atrapa KeyError en templates ni errores de renderizado.

---

## 10. Reglas Absolutas de Código

1. SIEMPRE docstring en español en cada función
2. SIEMPRE comentar líneas no obvias
3. NUNCA definir campo/método dos veces → grep antes
4. NUNCA `required=True` en campos heredados
5. NUNCA `company_id` en catálogos SAT
6. SIEMPRE `company_id` en modelos operativos
7. SIEMPRE `check_company=True` en Many2one con `company_id`
8. SIEMPRE `models.Constraint()` — NO `_sql_constraints`
9. SIEMPRE `_rec_names_search` — NO `name_search` override
10. NO push directo a `main` — siempre rama + PR
11. Vistas: `<list>` NO `<tree>`, `invisible=` NO `attrs=`
12. view_mode: `"list"` NO `"tree"`
13. Kanban Odoo 19: `t-name="card"` NO `"kanban-box"`
14. Imágenes kanban: `widget="image"` NO `kanban_image()`

---

## 11. Tests — Reglas por Tipo

### TransactionCase — para lógica de modelos
Usar cuando el test valida cálculos, campos, métodos Python, workflows de estado.
No levanta servidor HTTP. No detecta errores QWeb.

```python
from odoo.tests import TransactionCase, tagged

@tagged('post_install', '-at_install', 'tms')
class TestTmsWaybill(TransactionCase):
    def test_calculo_propuesta_km(self):
        ...
```

### HttpCase — OBLIGATORIO para portal y controllers
Usar cuando el test valida rutas HTTP, templates QWeb, portal, website.
Levanta servidor real. Atrapa 500, KeyError en templates, errores de renderizado.

```python
from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install', 'tms')
class TestPortalTms(HttpCase):
    def test_portal_home_sin_500(self):
        """Verifica que /my carga sin error para usuario portal."""
        self.authenticate('portal_user', 'portal_user')
        res = self.url_open('/my')
        self.assertEqual(res.status_code, 200)

    def test_portal_waybills_list(self):
        """Verifica que /my/waybills carga correctamente."""
        self.authenticate('portal_user', 'portal_user')
        res = self.url_open('/my/waybills')
        self.assertEqual(res.status_code, 200)
```

### Comando para correr tests
```bash
python3 odoo-bin -c odoo.conf --test-enable --test-tags /tms -d tms_v2 --stop-after-init
```

---

## 12. Dev Workflow Git

```bash
git checkout main && git pull origin main
git checkout -b feat/etapa-X.X.X-nombre
# ... implementar ...
git add -A
git commit -m "feat(X.X.X): descripción en español"
git push origin feat/etapa-X.X.X-nombre
# → PR en GitHub → merge — NUNCA push directo a main
```

---

## 13. Próxima etapa
**V2.7 — Limpieza Final + QA** → **V2.8 — SaaS Primer Cliente**

---

_Actualizar después de cada etapa completada._
