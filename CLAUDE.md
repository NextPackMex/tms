# CLAUDE.md — TMS "Hombre Camión" & Carta Porte 3.1

# ══════════════════════════════════════════════════════════════
# CONTEXTO PARA CLAUDE CODE / ANTIGRAVITY / CLAUDE WEB
# Última actualización: 2026-03-23 — V2.2.2 COMPLETADA (Refuerzo Timbrado)
# ══════════════════════════════════════════════════════════════

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
**Versión módulo:** 19.0.2.2
**Progreso actual:** ~65% — V2.2.2 completado

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
- **Python binary:** `odoo-19.0/.venv/bin/python odoo-19.0/odoo-bin`
- **Config:** `proyectos/tms/odoo.conf`
- **Addons path:** `/proyectos/theme` (MUK) + `/proyectos/tms`

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
cotizado → aprobado → draft → en_pedido → assigned →
waybill → in_transit → arrived → closed
                                          ↓
                                        cancel
rejected (portal)
```

| Estado | Clave | Descripción |
|---|---|---|
| Cotizado | `cotizado` | Wizard generó pre-cotización, cliente no ha aprobado |
| Aprobado | `aprobado` | Cliente aprobó precio, pendiente datos completos |
| Solicitud | `draft` | Datos completos capturados |
| En Pedido | `en_pedido` | Cliente confirma / operador confirma |
| Por Asignar | `assigned` | Asignar vehículo, chofer, remolques |
| Carta Porte | `waybill` | Valida cumplimiento CP 3.1 completo |
| En Tránsito | `in_transit` | Ruta iniciada |
| En Destino | `arrived` | Llegó al destino |
| Facturado | `closed` | Factura creada, viaje cerrado |
| Cancelado | `cancel` | Anulado |
| Rechazado | `rejected` | Rechazado desde portal |

⚠️ NUNCA usar: `'transit'`, `'destination'`, `'carta_porte'` — NO EXISTEN → ValueError

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

### Hook al cerrar viaje (sembrar en V2.3)
```python
def write(self, vals):
    res = super().write(vals)
    if vals.get('state') == 'closed':
        self.env['tms.route.analytics']._update_from_waybill(self)
    return res
```

---

## 5. Estructura de Archivos — Completa

```
tms/                                    # Módulo principal
├── __init__.py
├── __manifest__.py
├── CLAUDE.md                           # ESTE ARCHIVO
├── contexto_maestro_tms_final.md       # Contexto estratégico completo
├── AGENTS.md                           # Reglas del agente IA
├── ORCHESTRATOR.md                     # Orquestador multi-agente
├── models/
│   ├── tms_waybill.py                  # MODELO MAESTRO
│   ├── tms_destination.py              # Rutas (caché TollGuru)
│   ├── tms_fleet_vehicle.py            # _inherit fleet.vehicle
│   ├── tms_vehicle_type.py             # Catálogo tipos vehículo
│   ├── tms_fuel_history.py             # Historial diesel (legacy)
│   ├── tms_tracking_event.py           # Bitácora GPS
│   ├── tms_evidence.py                 # Evidencia fotográfica (V2.4b) 🆕
│   ├── hr_employee.py                  # _inherit chofer
│   ├── res_partner_tms.py              # _inherit contactos SAT
│   ├── res_company.py                  # _inherit empresa
│   ├── res_config_settings.py          # _inherit APIs + seguros
│   └── sat_*.py                        # 11 catálogos SAT
├── views/
│   ├── tms_waybill_views.xml
│   ├── tms_fleet_vehicle_views.xml
│   ├── tms_destination_views.xml
│   └── res_config_settings_views.xml
├── reports/
│   ├── tms_waybill_report.xml
│   ├── tms_cotizacion_report.xml
│   ├── tms_cotizacion_report_template.xml
│   ├── tms_carta_porte_report.xml          # Acción reporte PDF CP timbrada (V2.2.1)
│   └── tms_carta_porte_report_template.xml # Template QWeb PDF CP timbrada (V2.2.1)
├── wizard/
│   ├── tms_cotizacion_wizard.py        # Wizard cotización 2 pasos
│   └── tms_cotizacion_wizard_views.xml
├── security/
│   ├── tms_security.xml
│   └── ir.model.access.csv
├── tests/
│   └── test_tms_waybill.py
└── docs/
    └── etapa-X.X.X.md                  # SDDs de cada etapa

tms_fuel/                               # Combustible y rendimiento (V2.4) 🆕
tms_signature/                          # Firma digital simple (V2.4c) 🆕
tms_settlement/                         # Liquidación de choferes (V2.4d) 🆕
tms_maintenance/                        # Mantenimiento de unidades (V2.5) 🆕
tms_saas/                               # Multi-tenant + cobro (V2.8)
tms_marketplace/                        # Marketplace de cargas (Fase 2)
tms_api/                                # API REST pública (Fase 2)
tms_analytics/                          # Datos de mercado (Fase 3)
```

---

## 6. Grupos de Seguridad

| Grupo | XML ID | Permisos |
|---|---|---|
| Usuario TMS | `group_tms_user` | CRUD operaciones (sin delete waybill) |
| Manager TMS | `group_tms_manager` | CRUD completo + configuración |
| Chofer TMS | `group_tms_driver` | Solo lectura waybill + escritura tracking |
| Fuel Manager | `group_tms_fuel_mgr` | Ver rendimiento todos los vehículos |
| Settlement Mgr | `group_tms_settle_mgr` | Crear y aprobar liquidaciones |
| Maint. Manager | `group_tms_maint_mgr` | Gestionar órdenes mantenimiento |

---

## 7. Estado del Proyecto

### ✅ V1.0 — Base Funcional (COMPLETADO)

### ✅ V2.0 — Estabilización (COMPLETADO — 9/9 etapas)

| Etapa | Nombre | Estado |
|---|---|---|
| 2.0.1 | Eliminar duplicados Python | ✅ |
| 2.0.2 | Fix estados + Dolly + TollGuru | ✅ |
| 2.0.3 | Campos SAT + ACL regímenes | ✅ |
| 2.0.4 | Fix partner + multi-empresa | ✅ |
| 2.0.5 | Fix domain vehículo + amount_untaxed | ✅ |
| 2.0.6 | Unificar cp_type/waybill_type | ✅ |
| 2.0.7 | Limpiar constraints | ✅ |
| 2.0.8 | Auditar manifest + fix UI remolques | ✅ |
| 2.0.9 | QA BD limpia + datos demo + E2E | ✅ |

### ✅ V2.1 — Pulido UX (COMPLETADO)

| Etapa | Nombre | Estado |
|---|---|---|
| 2.1.1 | Formulario por estado | ✅ |
| 2.1.2 | Smart buttons | ✅ |
| 2.1.3 | Kanban polish | ✅ |
| 2.1.4a | Wizard cotización base 2 pasos | ✅ |
| 2.1.4b | Rediseño UX 3 columnas propuestas | ✅ |
| 2.1.4c | Estados cotizado+aprobado | ✅ |
| 2.1.4d | Mercancías simplificadas Paso 1 | ✅ |
| 2.1.4e | Wizard desde lista, no desde form | ✅ |
| 2.1.4f | Fix direcciones + botón form | ✅ 2026-03-13 |
| 2.1.5 | Onboarding wizard 6 pasos | ✅ |
| 2.1.6 | PDF pre-cotización + email | ✅ |

### ✅ V2.2 — Carta Porte 3.1 + Timbrado Formas Digitales (COMPLETADO)
**PAC:** Formas Digitales (forsedi.facturacfdi.mx) + SW Sapien (respaldo)
**Hitos técnicos:**
- ✅ Core: Timbrado CFDI 4.0 + CP 3.1 (UUID: 97367659-43B7-40E2-9AEC-731A014F9D46)
- ✅ V2.2.1: PDF Carta Porte timbrada (7 secciones + QR SAT)
- ✅ V2.2.2: Refuerzo flujo timbrado + wizard validación (2026-03-23)
- ✅ Migración: `tms_regimen_fiscal` → `tms.sat.regimen.fiscal` (PR #10)
- ✅ Servicios: xml_builder (id_ccp movido), xml_signer, pac_manager
- ✅ Semilla: Modelo `tms.route.analytics` creado

### 📋 V2.3 — Facturación Real
- CFDI de ingreso vinculado al waybill via `account.move`
- ⚠️ SEMILLA: activar hook `waybill.closed → _update_from_waybill()`

### 📋 V2.4 🆕 — Combustible y Rendimiento (`tms_fuel/`)
- `tms.fuel.log`: registro por carga de diesel con foto ticket, odómetro, rendimiento real
- `tms.vehicle.performance`: KPIs acumulados, costo/km real que alimenta wizard cotización
- Alerta automática si rendimiento baja más del 15%

### 📋 V2.4b 🆕 — Evidencia Fotográfica
- `tms.evidence.photo`: 14 tipos de foto con GPS + timestamp inmutable
- Odómetro verificado con foto, alerta si distancia real difiere >20% vs TollGuru

### 📋 V2.4c 🆕 — Firma Digital Simple (`tms_signature/`)
- Canvas firma con dedo, SHA-256 del documento, verificación SMS opcional
- QR público `nextpack.mx/verify/{token}`, PDF con firma incrustada
- 6 tipos: anticipo, checklist salida, carga origen, entrega, liquidación, incidente

### 📋 V2.4d 🆕 — Liquidación de Choferes (`tms_settlement/`)
- `tms.driver.settlement`: flete × % chofer + reembolsos − anticipos − deducciones
- Comprobante PDF firmado digitalmente, saldo arrastrado entre viajes

### 🚧 V2.5 — Limpieza y Data Integrity (EN CURSO — Semillas Pendientes)
- ✅ Estados simplificados a 6 (ciclo vital Hombre Camión)
- ✅ Normalización t-esc → t-out (tracking events)
- ✅ Badges Kanban dinámicos por estado y urgencia
- ❌ PENDIENTE: current_zip (fleet.vehicle) — Matching geográfico Fase 2
- ❌ PENDIENTE: vehicle_status (fleet.vehicle) — Bloquear vehículo en falla ⚠️ RIESGO: Referenciado en comentario action_confirm_order (tms_waybill.py) — si se convierte en código real sin implementar el campo → crash inmediato.
- ❌ PENDIENTE: is_tms_carrier (res.partner) — Filtrar transportistas marketplace

### 📋 V2.6 — KPIs, Reportes y Portal Web
- Dashboard ingresos, rentabilidad por vehículo, rendimiento diesel
- Portal cliente: ver estado de su envío + botón aprobación

### 📋 V2.7 — Limpieza Final "Modo Hombre Camión"
- 0 warnings en logs, 0 métodos huérfanos, menú simplificado
- QA: usuario nuevo < 10 min primera Carta Porte
- Verificar todas las semillas Fase 2 funcionando

### 📋 V2.8 🎯 — SaaS Multi-tenant + Cobro (`tms_saas/`)
- Planes: free ($0) / pro ($990 MXN) / flota ($2,990 MXN)
- MercadoPago webhook, arquitectura PostgreSQL cluster + Redis
- **HITO: PRIMER CLIENTE PAGA AQUÍ**

### 📋 Fase 2 — Marketplace de Cargas (Sep–Dic 2026)
Ver `contexto_maestro_tms_final.md` sección 9 para detalle completo.
- M2.1 Modelos marketplace · M2.2 Matching engine
- M2.3 API REST · M2.4 App Flutter · M2.5 Portal embarcador · M2.6 Notificaciones

### 📋 Fase 3 — Datos, Confianza y Escala (2027)
Ver `contexto_maestro_tms_final.md` sección 9 para detalle completo.
- F3.1 Verificaciones/badges · F3.2 Analytics de mercado
- F3.3 Matching ML · F3.4 API brokers

---

## 8. Wizard Cotización (V2.1.4) — Arquitectura

### Modelo: tms.cotizacion.wizard (TransientModel)
- Paso 1: CP origen/destino + variables → calcular → 3 propuestas
- Paso 2: Datos completos (solo si aprueba) → crear waybill

### Paso 1 campos:
```python
partner_invoice_id          # Cliente (required)
origin_zip, dest_zip        # CPs para TollGuru
num_axles
diesel_price, fuel_performance
driver_salary, maneuvers, other_costs, commission
price_per_km, margin_percent
direct_price
distance_km, duration_hours, toll_cost
proposal_km_total, proposal_trip_total
selected_proposal
```

### Paso 2 campos:
```python
partner_origin_id, partner_dest_id
vehicle_id, trailer1_id, dolly_id, trailer2_id
driver_id
line_ids → tms.cotizacion.wizard.line  # Mercancías completas con Clave SAT
```

### Flujo UI:
1. Botón "Nueva Cotización" en vista LISTA (no en formulario)
2. Wizard crea waybill en estado `cotizado`
3. Waybill cotizado muestra solo: cliente + precio
4. Botón "Aprobar Cotización" → estado `aprobado`
5. Estado aprobado → formulario completo visible
6. "Confirmar Pedido" → estado `draft`/`en_pedido`

---

## 9. Issues Conocidos

| ID | Severidad | Descripción | Estado |
|---|---|---|---|
| FIX-01 | ✅ | widget monetary sin currency_field en wizard | Resuelto |
| FIX-02 | ✅ | is_dangerous no definido en wizard.line | Resuelto |
| FIX-03 | ✅ | Direcciones origen/destino no llegaban al waybill | Resuelto 2026-03-13 |
| FIX-04 | ✅ | Retención 4% no considera is_company | Resuelto |
| FIX-A | ✅ | Normalización SAT xml_builder (5 helpers, 11 campos) | Resuelto |
| FIX-B | ✅ | Auto-sustitución fiscal en pruebas | Resuelto |
| FIX-C | ✅ | Waybill readonly post-timbrado | Resuelto |
| FIX-D | ✅ | Onboarding sincroniza company.partner_id | Resuelto |

## 10. Deuda Técnica Conocida

### Semillas V2.5 — campos pendientes de implementar
Estos campos están documentados en el roadmap pero NO existen en el código. No bloquean V2.3 ni V2.4.

| Campo | Modelo | Para qué | Prioridad |
|---|---|---|---|
| current_zip | fleet.vehicle | Matching geográfico futuro (Fase 2) | Baja |
| vehicle_status | fleet.vehicle | Bloquear wizard si vehículo en falla | Media ⚠️ |
| is_tms_carrier | res.partner | Marketplace: filtrar transportistas | Baja |

Implementar antes de V2.7 / Fase 2.

---

## 11. Problemas Históricos (NUNCA Repetir)

1. **Código duplicado** — Python usa la última definición silenciosamente
2. **Estados desalineados** — Selection vs métodos → ValueError
3. **Campos fantasma** — onchange referencia campos inexistentes → AttributeError
4. **required=True en modelos heredados** — Rompe registros del sistema
5. **compute store=False escribiendo store=True** — No persiste en BD
6. **_fetch_tollguru_api duplicada** — Verificar con grep antes de agregar
7. **Leer mal JSON TollGuru** — Usar `routes[0]`, no `route` ni `metric`
8. **widget monetary sin currency_field** — OWL error en Odoo 19
9. **column_invisible con campo inexistente** — EvalError en OWL
10. **on_create en kanban agrupado** — No funciona en Odoo 19 con group_by activo

---

## 12. Reglas Absolutas de Código

1. SIEMPRE comentar cada función con docstring en **español**
2. SIEMPRE comentar líneas no obvias dentro de los métodos
3. NUNCA definir el mismo campo/método dos veces → `grep -rn "def nombre" models/`
4. NUNCA `required=True` en campos heredados (`res.partner`, `fleet.vehicle`)
5. NUNCA escribir en campos `store=True` desde `compute store=False`
6. NUNCA crear modelo nuevo si puedes extender con `_inherit`
7. NUNCA `company_id` en catálogos SAT (son globales)
8. SIEMPRE `company_id` en modelos operativos
9. SIEMPRE `check_company=True` en Many2one a modelos con `company_id`
10. SIEMPRE `models.Constraint()` — NO `_sql_constraints`
11. SIEMPRE `_rec_names_search` — NO `name_search` override
12. NO crear `verify_*.py` / `fix_*.py` en la raíz del repo
13. NO push directo a `main` — siempre rama + PR
14. Vistas: `<list>` (NO `<tree>`), `invisible=` (NO `attrs=`)

---

## 13. Dev Workflow Git

```bash
# Inicio de cada etapa
git checkout main && git pull origin main
git checkout -b feat/etapa-X.X.X-nombre

# Validar antes de commit
python3 -m py_compile models/archivo.py
grep -n "WARNING\|ERROR" odoo.log | tail -20

# Update + reinicio Odoo
python3 odoo-bin -c odoo.conf -u tms -d tms_v2 --stop-after-init
python3 odoo-bin -c odoo.conf

# Commit (sin push hasta que Mois lo indique)
git add -A
git commit -m "feat(X.X.X): descripción en español"

# Push y PR
git push origin feat/etapa-X.X.X-nombre
# → abrir PR en GitHub → merge vía PR — NUNCA push directo a main
```

### Convención de commits:
```
feat(X.X.X): descripción    ← nueva funcionalidad
fix(X.X.X): descripción     ← corrección de bug
chore: descripción           ← mantenimiento
```

### GitHub — reglas activas:
- ✅ Branch protection en `main`
- ✅ Solo merge vía Pull Request
- ✅ Block force pushes
- ✅ Nunca push directo a `main`

---

## 14. Reglas de Trabajo por Herramienta

### Claude Code (consola IDE)
- Lee `CLAUDE.md` automáticamente al iniciar
- Modo **Ask** para cambios quirúrgicos y QA
- Modo **Edit** para refactors grandes
- NO hacer commit hasta que Mois lo apruebe explícitamente

### Antigravity
- Primer prompt de cada etapa: incluir SDD completo como contexto
- Prompts siguientes dentro de la misma etapa: NO repetir contexto

### Prioridad de pensamiento Antigravity:
- `Planning + High` → módulos nuevos, integraciones API, orquestador
- `Planning + Low` → lógica Python, bugs complejos, modelos medianos
- `Fast + Flash` → XML, labels, fix una línea, verificaciones, limpieza

### Tabla de herramientas por versión:
| Versión | Herramienta | Modo |
|---|---|---|
| 2.1.5 | Claude Code CLI + Orquestador | Planning + High |
| 2.1.6 | Antigravity | Planning + Low |
| 2.2 | Claude Code CLI + Orquestador | Planning + High |
| 2.3 | Claude Code CLI + Orquestador | Planning + High |
| 2.4 | Antigravity | Planning + Low |
| 2.4b | Antigravity | Planning + Low |
| 2.4c | Claude Code CLI + Orquestador | Planning + High |
| 2.4d | Antigravity | Planning + Low |
| 2.5 | Antigravity | Planning + Low |
| 2.6 | Antigravity | Planning + Low |
| 2.7 | Antigravity | Fast + Flash |
| 2.8 | Claude Code CLI + Orquestador | Planning + High |

---

## 15. Formato SDD Obligatorio

Cada etapa debe tener un SDD en `docs/etapa-X.X.X.md` antes de arrancar:

```markdown
# SDD — Etapa X.X.X: Nombre
Módulo, Fecha, Prioridad, Branch GIT

## GIT (solo primer prompt de etapa)
## PROBLEMA
## SOLUCIÓN
## CAMBIOS (tablas de campos, modelos)
## ACCEPTANCE CRITERIA (AC-01, AC-02...)
## UPGRADE COMMAND
## Context Blueprint
  - Modelos _name
  - File Manifest (ruta + Crear/Modificar)
  - Decoradores + campos nuevos
  - Seguridad (access.csv + groups)
```

---

## 16. Qué Actualizar al Terminar Cada Etapa

### En CLAUDE.md (obligatorio antes del commit):
1. Fecha en el encabezado → fecha actual
2. Versión del módulo → nueva versión
3. Tabla de etapas → marcar como ✅
4. Issues Conocidos → marcar resueltos
5. Problemas Históricos → agregar si se descubrió algo nuevo

### En contexto_maestro_tms_final.md:
1. Sección 9 roadmap → actualizar estado de la etapa completada
2. Sección 10 semillas → marcar las que se sembraron

### Verificar con:
```bash
grep -n "✅\|🚧\|📋\|Última actualización" CLAUDE.md | head -20
```

### Al finalizar cada etapa:
Explicar brevemente los conceptos clave del código generado para que Mois aprenda.

---

## 17. Semillas Entre Fases (No Olvidar)

| Cuándo | Qué | Para qué |
|---|---|---|
| V2.2 | Modelo `tms.route.analytics` vacío | Datos de ruta desde el primer viaje |
| V2.3 | Hook `waybill.closed → _update_from_waybill()` | Alimenta matching engine |
| V2.5 | `fleet.vehicle.current_zip` | Matching engine: proximidad |
| V2.5 | `res.partner.is_tms_carrier` | Marketplace: filtrar transportistas |
| V2.5 | `fleet.vehicle.vehicle_status` bloquea wizard | Sin vehículos con falla |
| V2.7 | Verificar TODAS las semillas | Base lista para Fase 2 |

---

_Este archivo es el contexto técnico del proyecto._
_Para el contexto estratégico completo (roadmap, fases, ingresos): ver `contexto_maestro_tms_final.md`_
_Actualizar después de cada etapa completada._

## Próxima etapa
**Opciones en orden de dificultad:**
- [ ] Fix rápido: ocultar toll_cost en PDF pre-cotización (tms_cotizacion_report_template.xml)
- [ ] Fix rápido: invisible="not vehicle_id" en bloque portal "Unidad Asignada"
- [ ] Fix medio: mover validaciones "Confirmar Pedido" → "Timbrar" y eliminar botón
- [ ] V2.4: KPIs + portal cliente
- [ ] V2.3: Facturación real account.move (más compleja)

