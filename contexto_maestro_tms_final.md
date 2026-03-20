# 🚛 CONTEXTO MAESTRO — TMS Hombre Camión

# Archivo único para Proyecto TMS en Claude Web

> Versión módulo: 19.0.2.2 | Actualizado: 2026-03-20

---

## 1. IDENTIDAD DEL PROYECTO

| Campo                | Valor                                                                             |
| -------------------- | --------------------------------------------------------------------------------- |
| **Módulo**           | TMS "Hombre Camión" (`tms/`)                                                      |
| **Nombre comercial** | Hombre Camión                                                                     |
| **Repo**             | github.com/NextPackMex/tms                                                        |
| **Stack**            | Python 3.12+, Odoo 19 CE, PostgreSQL, JavaScript, OWL, QWeb                       |
| **Arquitectura**     | Single Document Flow — `tms.waybill` fusiona Cotización + Operación + Carta Porte |
| **APIs externas**    | TollGuru API v2 (activa), Google Routes API (disponible)                          |
| **PAC**              | Formas Digitales (forsedi.facturacfdi.mx — contrato activo)                       |
| **Fiscal**           | SAT Carta Porte 3.1, CFDI 4.0                                                     |
| **Autor**            | NextPack (nextpack.mx)                                                            |
| **Licencia**         | LGPL-3                                                                            |

---

## 2. ARQUITECTURA SAAS MULTI-EMPRESA

### Regla de oro:

- **Catálogos SAT** → GLOBALES (sin `company_id`) → Compartidos entre empresas
- **Datos operativos** → PRIVADOS (con `company_id` obligatorio) → Aislados por empresa
- **APIs de rutas** → GLOBALES via `config_parameter`
- **Seguros Carta Porte** → POR EMPRESA via `related='company_id.campo'`

### Record Rule res.partner (CRÍTICA):

```python
# SIEMPRE usar este dominio para partners
['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]
```

### Modelos SIN company_id (globales SAT):

```
tms.sat.clave.prod, tms.sat.clave.unidad, tms.sat.codigo.postal,
tms.sat.colonia, tms.sat.localidad, tms.sat.municipio,
tms.sat.config.autotransporte, tms.sat.tipo.permiso, tms.sat.embalaje,
tms.sat.material.peligroso, tms.sat.figura.transporte,
tms.sat.regimen.fiscal
```

### Modelos CON company_id (privados):

```
tms.waybill, tms.waybill.line, tms.destination,
fleet.vehicle, tms.fuel.history, tms.tracking.event
```

---

## 3. MODELO MAESTRO: tms.waybill

### Workflow de Estados — ÚNICOS VÁLIDOS

```
cotizado → aprobado → draft → en_pedido → assigned →
waybill → in_transit → arrived → closed
                                         ↓
                                       cancel
rejected (portal)
```

| Estado      | Clave        | Descripción                                          |
| ----------- | ------------ | ---------------------------------------------------- |
| Cotizado    | `cotizado`   | Wizard generó pre-cotización, cliente no ha aprobado |
| Aprobado    | `aprobado`   | Cliente aprobó precio, pendiente datos completos     |
| Solicitud   | `draft`      | Datos completos capturados                           |
| En Pedido   | `en_pedido`  | Cliente confirma / operador confirma                 |
| Por Asignar | `assigned`   | Asignar vehículo, chofer, remolques                  |
| Carta Porte | `waybill`    | Valida cumplimiento CP 3.1 completo                  |
| En Tránsito | `in_transit` | Ruta iniciada                                        |
| En Destino  | `arrived`    | Llegó al destino                                     |
| Facturado   | `closed`     | Factura creada, viaje cerrado                        |
| Cancelado   | `cancel`     | Anulado                                              |
| Rechazado   | `rejected`   | Rechazado desde portal                               |

⚠️ PROHIBIDO usar: `'transit'`, `'destination'`, `'carta_porte'` → ValueError

### Motor de Cotización — 3 Propuestas

**A) Por KM:** `(distancia + km_extras) × precio_km`
**B) Por Viaje:** `(diesel + casetas + chofer + maniobras + otros + comisión) / (1 - margen%)`
**C) Precio Directo:** monto capturado manualmente

`selected_proposal` determina cuál se aplica a `amount_untaxed`

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

## 4. ESTRUCTURA DE ARCHIVOS

```
tms/
├── __init__.py
├── __manifest__.py
├── AGENTS.md                       # Reglas del agente IA
├── CLAUDE.md                       # Contexto Claude Code CLI
├── ORCHESTRATOR.md                 # Orquestador multi-agente
├── contexto_maestro_tms_final.md   # ESTE ARCHIVO
├── models/
│   ├── tms_waybill.py              # MODELO MAESTRO
│   ├── tms_destination.py          # Rutas (caché TollGuru)
│   ├── tms_fleet_vehicle.py        # _inherit fleet.vehicle
│   ├── tms_vehicle_type.py         # Catálogo tipos vehículo
│   ├── tms_fuel_history.py         # Historial diesel
│   ├── tms_tracking_event.py       # Bitácora GPS
│   ├── hr_employee.py              # _inherit chofer
│   ├── res_partner_tms.py          # _inherit contactos SAT
│   ├── res_company.py              # _inherit empresa
│   ├── res_config_settings.py      # _inherit APIs + seguros
│   ├── sat_regimen_fiscal.py       # Catálogo tms.sat.regimen.fiscal ← NUEVO PR#10
│   └── sat_*.py                    # 11 catálogos SAT
├── views/
│   ├── tms_waybill_views.xml       # Form + Kanban + List + Search
│   ├── tms_fleet_vehicle_views.xml
│   ├── tms_destination_views.xml
│   └── res_config_settings_views.xml
├── wizard/
│   ├── tms_cotizacion_wizard.py    # Wizard cotización 2 pasos
│   ├── tms_cotizacion_wizard_views.xml
│   ├── tms_onboarding_wizard.py    # Onboarding 6 pasos
│   └── tms_onboarding_wizard_views.xml
├── services/
│   ├── xml_builder.py              # Constructor XML CFDI + CP 3.1
│   ├── xml_signer.py               # Firmado CSD
│   └── pac_manager.py              # Orquestador PAC
├── reports/
│   ├── tms_waybill_report.xml
│   ├── tms_cotizacion_report.xml
│   ├── tms_cotizacion_report_template.xml
│   ├── tms_carta_porte_report.xml
│   └── tms_carta_porte_report_template.xml
├── data/
│   ├── sat_regimen_fiscal.xml      # 20 registros c_RegimenFiscal ← NUEVO PR#10
│   └── mail_template_cotizacion.xml
├── security/
│   ├── tms_security.xml
│   └── ir.model.access.csv
├── tests/
│   └── test_tms_waybill.py
└── docs/
    └── etapa-X.X.X.md
```

---

## 5. GRUPOS DE SEGURIDAD

| Grupo       | XML ID              | Permisos                                  |
| ----------- | ------------------- | ----------------------------------------- |
| Usuario TMS | `group_tms_user`    | CRUD operaciones (sin delete waybill)     |
| Manager TMS | `group_tms_manager` | CRUD completo + configuración             |
| Chofer TMS  | `group_tms_driver`  | Solo lectura waybill + escritura tracking |

---

## 6. WIZARD DE COTIZACIÓN (V2.1.4)

### Modelo: `tms.cotizacion.wizard` (TransientModel)

- **Paso 1:** CP origen/destino + variables → calcular → 3 propuestas (NO hay cliente aún)
- **Paso 2:** Cliente + vehículo + chofer + mercancías → crear waybill

### Paso 1 — campos:

```python
origin_zip, dest_zip        # CPs para TollGuru
num_axles                   # Ejes del vehículo
# Propuesta B — costos operativos
diesel_price, fuel_performance
driver_salary, maneuvers, other_costs, commission
# Propuesta A — por km
price_per_km, margin_percent
# Propuesta C — directo
direct_price
# Resultado calculado
distance_km, duration_hours, toll_cost
proposal_km_total, proposal_trip_total
selected_proposal
# Botones (visibles solo si distance_km > 0)
action_download_pdf, action_send_email
```

### Paso 2 — campos:

```python
partner_invoice_id                      # Cliente (required)
partner_origin_id, partner_dest_id      # Remitente/Destinatario
vehicle_id, trailer1_id, dolly_id, trailer2_id
driver_id
line_ids                                # Mercancías completas con Clave SAT
```

### Flujo UI:

1. Botón "Nueva Cotización" en vista LISTA (no en formulario)
2. Wizard crea waybill en estado `cotizado`
3. Waybill cotizado muestra solo: cliente + precio
4. Botón "Aprobar Cotización" → estado `aprobado`
5. Estado aprobado → formulario completo visible
6. "Confirmar Pedido" → estado `draft`/`en_pedido`

---

## 7. ESTADO ACTUAL DEL ROADMAP

### ✅ V1.0 — Base Funcional (COMPLETO)

### ✅ V2.0 — Estabilización (COMPLETO — 9/9 etapas)

### ✅ V2.1 — Pulido UX (COMPLETO)

| Etapa  | Nombre                            | Estado                   |
| ------ | --------------------------------- | ------------------------ |
| 2.1.1  | Formulario por estado             | ✅                       |
| 2.1.2  | Smart buttons                     | ✅                       |
| 2.1.3  | Kanban polish                     | ✅                       |
| 2.1.4a | Wizard cotización base 2 pasos    | ✅                       |
| 2.1.4b | Rediseño UX 3 columnas propuestas | ✅                       |
| 2.1.4c | Estados cotizado+aprobado         | ✅                       |
| 2.1.4d | Mercancías simplificadas Paso 1   | ✅                       |
| 2.1.4e | Wizard desde lista, no desde form | ✅                       |
| 2.1.4f | Fix direcciones + botón form      | ✅ 2026-03-13            |
| 2.1.5  | Onboarding wizard 6 pasos         | ✅ Confirmado 2026-03-19 |
| 2.1.6  | PDF pre-cotización + email        | ✅ Confirmado 2026-03-19 |

### ✅ V2.2 — Carta Porte 3.1 + Timbrado (COMPLETO)

| Sub-etapa     | Nombre                                           | Estado                                        |
| ------------- | ------------------------------------------------ | --------------------------------------------- |
| 2.2 core      | Timbrado CFDI 4.0 + CP 3.1 Formas Digitales      | ✅ UUID: 97367659-43B7-40E2-9AEB-731A014F9D46 |
| 2.2.1         | PDF Carta Porte timbrada (7 secciones + QR SAT)  | ✅ Confirmado 2026-03-19                      |
| 2.2 migración | tms_regimen_fiscal → tms.sat.regimen.fiscal      | ✅ PR #10 2026-03-20                          |
| FIX-A         | Auditoría SAT xml_builder (5 helpers, 11 campos) | ✅ PR #9 2026-03-19                           |
| FIX-B         | Auto-sustitución fiscal en pruebas               | ✅ Ya existía en \_get_datos_fiscales()       |
| FIX-C         | Waybill readonly post-timbrado (doble capa)      | ✅ Ya existía                                 |
| FIX-D         | Onboarding sincroniza company.partner_id         | ✅ PR #9 2026-03-19                           |
| FIX-D2        | CP en onboarding Paso 1                          | ✅ PR #9 2026-03-19                           |
| FIX-D3        | Dirección fiscal en reporte cotización           | ✅ PR #9 2026-03-19                           |

> **Nota 2026-03-19:** Auditoría completa confirmó que V2.2.1, 2.1.5, 2.1.6
> y fixes B/C ya estaban implementados. El proyecto estaba más avanzado
> de lo que el roadmap indicaba. Versión real en main: 19.0.2.2

### 📋 Pendientes — en orden de prioridad

| Etapa | Nombre                              | Herramienta                   | Complejidad |
| ----- | ----------------------------------- | ----------------------------- | ----------- |
| V2.3  | Facturación real (account.move)     | Claude Code CLI + Orquestador | Muy alta    |
| V2.4  | KPIs y reportes / Portal aprobación | Antigravity Planning+Low      | Media       |
| V2.5  | Limpieza final "Modo Hombre Camión" | Claude Web + Antigravity      | Baja        |
| V3.0  | App Flutter chofer + SaaS           | Arquitectura separada         | Muy alta    |

---

## 8. PRÓXIMA ETAPA — V2.3 Facturación Real

**Objetivo:** CFDI de ingreso vinculado al waybill via `account.move`.
**Herramienta:** Claude Code CLI + Orquestador | **Modo:** `Planning + High`
**⚠️ Regla:** Auditar primero qué está implementado antes de construir.
**Metodología:** Verificar → SDD → implementar (igual que sesión 2026-03-19).

---

## 9. FLUJO DE TRABAJO — CURSO IA 2026

### Metodología SDD

Antes de cada etapa nueva:

1. **Claude Web** genera el SDD en `docs/etapa-X.X.X.md`
2. El SDD define: walkthrough + campos + contratos + acceptance criteria
3. Los agentes reciben el SDD como fuente de verdad

### Flujo multi-agente con orquestador

```bash
cd ~/odoo/proyectos/tms
claude "Lee ORCHESTRATOR.md y docs/etapa-X.X.X.md y ejecuta el flujo multi-agente"
```

### 4 sub-agentes en paralelo (Git Worktrees)

| Agente | Tarea                      | Rama                      |
| ------ | -------------------------- | ------------------------- |
| A      | Modelos Python (`models/`) | `feat/etapa-X.X.X-models` |
| B      | Vistas XML (`views/`)      | `feat/etapa-X.X.X-views`  |
| C      | Tests unitarios (`tests/`) | `feat/etapa-X.X.X-tests`  |
| D      | Auditoría seguridad        | Sin rama — solo audita    |

### Cuándo usar cada herramienta

| Tarea                            | Herramienta                   | Modo Antigravity  |
| -------------------------------- | ----------------------------- | ----------------- |
| Generar SDD, revisar, documentos | Claude Web                    | —                 |
| Fix quirúrgico 1-2 archivos, XML | Antigravity                   | `Fast + Flash`    |
| Bug complejo, lógica Python      | Antigravity                   | `Planning + Low`  |
| Etapa nueva completa             | Claude Code CLI + Orquestador | `Planning + High` |

### GitHub — reglas activas desde 2026-03-13

- ✅ Branch protection en `main`
- ✅ Solo merge vía Pull Request
- ✅ Block force pushes
- ✅ Nunca push directo a `main`

### Pendientes de configurar

- [ ] `.github/workflows/ci.yml` — lint + tests automáticos
- [ ] `.github/workflows/security.yml` — claude-code-security-review
- [ ] Release Please — versionado automático

---

## 10. REGLAS ABSOLUTAS — NUNCA ROMPER

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
13. Vistas: `<list>` (NO `<tree>`), `invisible=` (NO `attrs=`)

---

## 11. BUGS CONOCIDOS — NO REPETIR

| ID     | Descripción                                       | Estado                 |
| ------ | ------------------------------------------------- | ---------------------- |
| FIX-01 | widget monetary sin currency_field en wizard      | ✅ Resuelto            |
| FIX-02 | is_dangerous no definido en wizard.line           | ✅ Resuelto            |
| FIX-03 | Direcciones origen/destino no llegaban al waybill | ✅ Resuelto 2026-03-13 |
| FIX-04 | Retención 4% no considera is_company              | ✅ Resuelto            |

### Problemas históricos — nunca repetir

1. Código duplicado — Python usa la última definición silenciosamente
2. Estados desalineados — Selection vs métodos → ValueError
3. Campos fantasma — onchange referencia campos inexistentes → AttributeError
4. `required=True` en modelos heredados — rompe registros del sistema
5. `compute store=False` escribiendo `store=True` — no persiste en BD
6. `_fetch_tollguru_api` duplicada — verificar con grep antes de agregar
7. Leer mal JSON TollGuru — usar `routes[0]`, no `route` ni `metric`
8. widget monetary sin `currency_field` — OWL error en Odoo 19
9. `column_invisible` con campo inexistente — EvalError en OWL
10. `on_create` en kanban agrupado — no funciona en Odoo 19 con group_by activo
11. `fields.Selection` → `fields.Char` mismo nombre en Odoo 19 — crashea con `AttributeError: 'Char' object has no attribute 'ondelete'`. Solución: usar Many2one + actualizar referencias directamente al nuevo campo `.id`.
12. `name_get()` deprecated en Odoo 19 — no afecta dropdowns correctamente. Solución: campo `full_name = fields.Char(compute=..., store=True)` con `_rec_name = 'full_name'` y `_rec_names_search = ['code', 'name', 'full_name']`.

---

## 12. COMANDOS CLAVE

```bash
# Reinicio según tipo de cambio:
# SOLO REINICIAR: cambios Python sin campos nuevos
python3 odoo-bin -c odoo.conf

# ACTUALIZAR: campos nuevos, XML, manifest, seguridad
python3 odoo-bin -c odoo.conf -u tms -d tms_v2 --stop-after-init
python3 odoo-bin -c odoo.conf

# REINSTALAR: modelo nuevo o errores graves de caché
python3 odoo-bin -c odoo.conf -i tms -d tms_v2 --stop-after-init

# Validar Python antes de commit
python3 -m py_compile models/archivo.py

# Buscar duplicados antes de agregar
grep -rn "def nombre_metodo" models/
grep -rn "record id=" views/

# Git — flujo correcto
git checkout main && git pull origin main
git checkout -b feat/etapa-X.X.X-nombre
git add .
git commit -m "feat(X.X.X): descripción en español"
git push origin feat/etapa-X.X.X-nombre
# → abrir PR en GitHub → merge vía PR (NUNCA push directo a main)
```

---

## 13. CONVENCIÓN DE COMMITS

```
feat(X.X.X): descripción    ← nueva funcionalidad
fix(X.X.X): descripción     ← corrección de bug
chore: descripción           ← mantenimiento
```

---

## 14. CÓMO SE EJECUTA CADA ETAPA

### Regla general

**Antes de ejecutar cualquier etapa: AUDITAR primero qué está implementado.**
Metodología confirmada 2026-03-19 — varias etapas ya estaban completas.

### Por etapa específica:

| Etapa    | Herramienta                   | Modo              | Por qué                                    |
| -------- | ----------------------------- | ----------------- | ------------------------------------------ |
| **V2.3** | Claude Code CLI + Orquestador | `Planning + High` | account.move, modelos nuevos, muy delicado |
| **V2.4** | Antigravity                   | `Planning + Low`  | KPIs y portal, sin modelos core nuevos     |
| **V2.5** | Claude Web + Antigravity      | `Fast + Flash`    | Limpieza, 0 lógica nueva                   |
| **V3.0** | Arquitectura separada         | —                 | Flutter/Dart, contexto aislado de Odoo     |

### Flujo completo para etapas con Orquestador (V2.3)

```
PASO 1 — Auditoría previa (Claude Code CLI)
→ Verificar qué ya está implementado antes de construir

PASO 2 — Claude Web (este chat)
→ "Genera el SDD de la etapa X.X.X"
→ Guardar output en docs/etapa-X.X.X.md del repo

PASO 3 — Terminal (Claude Code CLI)
→ cd ~/odoo/proyectos/tms
→ claude "Lee ORCHESTRATOR.md y docs/etapa-X.X.X.md
   y ejecuta el flujo multi-agente completo"

PASO 4 — Los 4 agentes trabajan en paralelo
→ Agente A: models/ en rama feat/etapa-X.X.X-models
→ Agente B: views/ en rama feat/etapa-X.X.X-views
→ Agente C: tests/ en rama feat/etapa-X.X.X-tests
→ Agente D: auditoría seguridad (sin rama)

PASO 5 — Update + reinicio Odoo
→ python3 odoo-bin -c odoo.conf -u tms -d tms_v2 --stop-after-init
→ python3 odoo-bin -c odoo.conf

PASO 6 — PR a main
→ GitHub Actions valida automáticamente (cuando esté configurado)
→ Merge vía PR — NUNCA push directo a main
```

### Flujo para etapas con Antigravity (V2.4, V2.5)

```
PASO 1 — Auditoría previa
→ Verificar qué ya está implementado

PASO 2 — Claude Web (este chat)
→ "Genera el SDD de la etapa X.X.X"
→ Copiar el SDD al prompt de Antigravity

PASO 3 — Antigravity implementa
→ NO hace commit hasta que Mois lo indique

PASO 4 — Update + reinicio Odoo
→ python3 odoo-bin -c odoo.conf -u tms -d tms_v2 --stop-after-init

PASO 5 — Verificar en navegador y hacer PR
```

---

## 15. DETALLE ETAPAS PENDIENTES

### V2.3 — Facturación Real

**Herramienta:** Claude Code CLI + Orquestador | **Modo:** `Planning + High`

- CFDI de ingreso vinculado al waybill via `account.move`
- Retención 4% IVA automática
- IVA 0% para receptores en zonas ZEDE (Istmo de Tehuantepec — validar `receptor.zip`)
- Modelo `tms.expense` para liquidación de gastos (diesel, comidas, maniobras + foto ticket)
- Beneficio Neto del Viaje = Ingreso − Casetas − Diesel − Comisiones − Otros

### V2.4 — KPIs, Reportes y Portal de Clientes

**Herramienta:** Antigravity | **Modo:** `Planning + Low`

- Dashboard rentabilidad por viaje (usa datos de `tms.expense`)
- Portal web cliente: Carta Porte descargable, XML, estatus, mapa tracking

### V2.5 — Data Integrity + Limpieza Final

**Herramienta:** Claude Web + Antigravity | **Modo:** `Fast + Flash`

- Auditoría de flujo de campos entre todos los modelos
- Simplificación estados waybill a 6 visibles
- 0 warnings, 0 métodos huérfanos, lenguaje transportista
- QA: usuario nuevo < 10 min primera Carta Porte

### V3.0 — App Flutter Chofer + SaaS

**Herramienta:** Arquitectura separada — contexto AISLADO de Odoo

- Stack: Flutter, Dart, Riverpod, API REST Odoo
- Estados: En Origen → Cargando → En Tránsito → En Destino → Descargando → Liberado
- Botones: "Iniciar Viaje", "Llegada a Cliente", "Cerrar Viaje"
- Subida de foto de remisión firmada como evidencia de entrega
- Onboarding SaaS automático, MercadoPago/Stripe

---

## 16. FORMATO SDD OBLIGATORIO (para cada etapa nueva)

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

- Modelos \_name
- File Manifest (ruta + Crear/Modificar)
- Decoradores + campos nuevos
- Seguridad (access.csv + groups)
```

---

## 17. FIXES POST-V2.2 (PR #9 — mergeado 2026-03-19)

| Fix    | Descripción                                                                                                       | Archivo tocado                               |
| ------ | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| FIX-A  | Normalización campos SAT en xml_builder (5 helpers, 11 .set() normalizados, validador \_validate_required_fields) | `services/xml_builder.py`                    |
| FIX-B  | Auto-sustitución fiscal en pruebas                                                                                | Ya existía — no se tocó                      |
| FIX-C  | Waybill readonly post-timbrado                                                                                    | Ya existía — no se tocó                      |
| FIX-D  | Onboarding sincroniza company.partner_id (nombre, street, zip, state_id)                                          | `wizard/tms_onboarding_wizard.py` + views    |
| FIX-D2 | Campo company_zip agregado al Paso 1 del onboarding                                                               | `wizard/tms_onboarding_wizard.py` + views    |
| FIX-D3 | Dirección fiscal (street, zip, ciudad, estado) en reporte cotización                                              | `reports/tms_cotizacion_report_template.xml` |

---

_Archivo único — reemplaza versiones anteriores_
_Actualizado: 2026-03-20_
_Versión módulo en main: 19.0.2.2 (PR #9 + PR #10)_
_Próxima sesión: auditar V2.3, V2.4, V2.5 antes de construir_
