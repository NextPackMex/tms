# CLAUDE.md — TMS "Hombre Camión" & Carta Porte 3.1

# ══════════════════════════════════════════════════════════════

# CONTEXTO PARA CLAUDE CODE / ANTIGRAVITY / CLAUDE WEB

# Última actualización: 2026-02-10

# ══════════════════════════════════════════════════════════════

## 1. Resumen del Proyecto

**Nombre:** TMS & Carta Porte 3.1 (SaaS Multi-Empresa)
**Nombre comercial:** Hombre Camión
**Versión Odoo:** 19 Community Edition
**Autor:** NextPack (nextpack.mx)
**Licencia:** LGPL-3
**Versión módulo:** 19.0.1.0.0

**Qué es:** Módulo vertical completo para gestión de transporte de carga en México.
Cubre desde cotización hasta facturación, con cumplimiento fiscal (Carta Porte 3.1 / CFDI 4.0).

**Arquitectura clave:** Single Document Flow — `tms.waybill` es el modelo maestro
que fusiona Cotización + Operación + Carta Porte en un solo registro.

---

## 2. Stack Tecnológico

- **Backend:** Python 3.12+, Odoo 19 CE
- **BD:** PostgreSQL 16+
- **Frontend:** OWL (Odoo Web Library), QWeb templates
- **APIs externas:** Google Routes API, TollGuru API (opcionales)
- **Fiscal:** SAT Carta Porte 3.1, CFDI 4.0

---

## 3. Arquitectura SaaS Multi-Empresa

### Regla de oro:

- **Catálogos SAT** → GLOBALES (sin `company_id`) → Compartidos entre empresas
- **Datos operativos** → PRIVADOS (con `company_id` obligatorio) → Aislados por empresa

### Modelos GLOBALES (sin company_id):

- `tms.sat.clave.prod` — Productos SAT
- `tms.sat.clave.unidad` — Unidades SAT
- `tms.sat.codigo.postal` — Códigos Postales
- `tms.sat.colonia` — Colonias
- `tms.sat.localidad` — Localidades
- `tms.sat.municipio` — Municipios
- `tms.sat.config.autotransporte` — Configuración Vehicular
- `tms.sat.tipo.permiso` — Permisos SCT
- `tms.sat.embalaje` — Embalajes
- `tms.sat.material.peligroso` — Materiales Peligrosos
- `tms.sat.figura.transporte` — Figuras de Transporte

### Modelos PRIVADOS (con company_id + Record Rules):

- `tms.waybill` — Viaje / Carta Porte (MODELO MAESTRO)
- `tms.waybill.line` — Mercancías del viaje
- `tms.destination` — Rutas comerciales frecuentes
- `fleet.vehicle` — Vehículos (extensión del nativo)
- `tms.fuel.history` — Historial de precios diesel
- `tms.tracking.event` — Eventos GPS / bitácora

### Modelos EXTENDIDOS (herencia \_inherit):

- `fleet.vehicle` — Agrega campos TMS (is_trailer, SAT, seguros)
- `hr.employee` — Agrega campos de chofer (licencia, RFC, régimen)
- `res.partner` — Agrega campos SAT (CP, colonia, municipio, régimen fiscal)
- `res.company` — Agrega defaults de seguros y CFDI
- `res.config.settings` — Agrega configuración de APIs y seguros

---

## 4. Modelo Maestro: tms.waybill

### Concepto

Un solo documento que atraviesa todo el ciclo de vida:
Cotización → Confirmación → Asignación → Carta Porte → Ruta → Entrega → Facturación

### Workflow de Estados

```
draft ──→ en_pedido ──→ assigned ──→ waybill ──→ in_transit ──→ arrived ──→ closed
  │                                                                          │
  └──→ rejected (portal)                                     cancel ←────────┘
```

| Estado      | Clave        | Quién actúa                 | Qué pasa                                      |
| ----------- | ------------ | --------------------------- | --------------------------------------------- |
| Solicitud   | `draft`      | Operador                    | Captura cotización, elige propuesta de precio |
| En Pedido   | `en_pedido`  | Cliente (portal) o Operador | Cliente firma/acepta o operador confirma      |
| Por Asignar | `assigned`   | Operador                    | Asigna vehículo, chofer, remolque             |
| Carta Porte | `waybill`    | Sistema                     | Valida cumplimiento CP 3.1 completo           |
| En Trayecto | `in_transit` | Chofer (app) o Operador     | Registra inicio de ruta + GPS                 |
| En Destino  | `arrived`    | Chofer (app) o Operador     | Registra llegada + GPS                        |
| Facturado   | `closed`     | Operador                    | Crea factura, cierra viaje                    |
| Cancelado   | `cancel`     | Operador                    | Anula el viaje                                |
| Rechazado   | `rejected`   | Cliente (portal)            | Rechaza cotización con motivo                 |

### Motor de Cotización (3 Propuestas)

**Propuesta A — Por Kilómetro:**

```
Total = (Distancia Base + Km Extras) × Precio/KM
```

**Propuesta B — Por Viaje (Costos + Margen):**

```
Costo Diesel = (Distancia / Rendimiento) × Precio Diesel
Costo Total = Diesel + Casetas + Chofer + Maniobras + Otros + Comisión
Precio Venta = Costo Total / (1 - Margen%)
```

**Propuesta C — Precio Directo:**

```
Total = Monto capturado manualmente
```

El campo `selected_proposal` determina cuál se aplica al `amount_untaxed`.
Impuestos: IVA 16%, Retención IVA 4%.

### Cálculo de Ruta Inteligente

1. Busca en caché (`tms.destination`) por CP Origen + CP Destino + Tipo Vehículo
2. Si no existe, llama a Google Routes API o TollGuru API
3. Guarda resultado en caché para futuros usos
4. Considera ejes totales del tren vehicular para cálculo de casetas

---

## 5. Estructura de Archivos

```
tms/
├── __init__.py
├── __manifest__.py
├── CLAUDE.md                           ← ESTE ARCHIVO
│
├── models/
│   ├── __init__.py
│   ├── tms_waybill.py                  # MODELO MAESTRO (waybill + line + customs)
│   ├── tms_destination.py              # Rutas comerciales (caché)
│   ├── tms_fleet_vehicle.py            # Extensión fleet.vehicle
│   ├── tms_vehicle_type.py             # Catálogo tipos vehículo
│   ├── tms_fuel_history.py             # Historial diesel
│   ├── tms_tracking_event.py           # Bitácora GPS
│   ├── hr_employee.py                  # Extensión chofer
│   ├── res_partner.py                  # Extensión contactos SAT
│   ├── res_company.py                  # Defaults empresa
│   ├── res_config_settings.py          # Configuración APIs
│   ├── sat_clave_prod.py               # Catálogo SAT
│   ├── sat_clave_unidad.py             # Catálogo SAT
│   ├── sat_codigo_postal.py            # Catálogo SAT
│   ├── sat_colonia.py                  # Catálogo SAT
│   ├── sat_localidad.py                # Catálogo SAT
│   ├── sat_municipio.py                # Catálogo SAT
│   ├── sat_config_autotransporte.py    # Catálogo SAT
│   ├── sat_tipo_permiso.py             # Catálogo SAT
│   ├── sat_embalaje.py                 # Catálogo SAT
│   ├── sat_material_peligroso.py       # Catálogo SAT
│   └── sat_figura_transporte.py        # Catálogo SAT
│
├── controllers/
│   ├── __init__.py
│   └── portal.py                       # Portal web (firma, rechazo, PDF)
│
├── wizard/
│   ├── __init__.py
│   ├── sat_import_wizard.py            # Importador catálogos SAT
│   ├── sat_import_wizard_views.xml
│   ├── partner_assign_company_wizard.py
│   ├── partner_assign_company_wizard_views.xml
│   ├── tms_load_demo_wizard.py
│   └── tms_load_demo_wizard_view.xml
│
├── views/
│   ├── tms_waybill_views.xml           # Form + Kanban + List + Search
│   ├── tms_fleet_vehicle_views.xml     # Vehículos/Remolques
│   ├── tms_destination_views.xml       # Rutas
│   ├── tms_vehicle_type_view.xml       # Tipos vehículo
│   ├── tms_fuel_history_views.xml      # Historial diesel
│   ├── tms_dashboard_views.xml         # Dashboard
│   ├── tms_portal_templates.xml        # Templates portal web
│   ├── res_partner_tms_view.xml        # Extensión contactos
│   ├── res_partner_tms_modals_view.xml # Modales contactos
│   ├── hr_employee_views.xml           # Vista choferes
│   ├── res_config_settings_views.xml   # Configuración
│   ├── sat_*_views.xml                 # 11 vistas catálogos SAT
│   ├── tms_menus.xml                   # Menús operativos
│   └── sat_menus.xml                   # Menús catálogos SAT
│
├── reports/
│   └── tms_waybill_report.xml          # PDF cotización/carta porte
│
├── security/
│   ├── tms_security.xml                # Grupos + Record Rules
│   └── ir.model.access.csv             # ACLs (~32 líneas)
│
├── data/
│   ├── tms_sequence_data.xml           # Secuencia VJ/0001
│   ├── tms_data.xml                    # Datos iniciales
│   └── mail_template_data.xml          # Plantilla email cotización
│
├── demo/
│   ├── tms_demo_data.xml
│   ├── tms_quickstart_demo.xml
│   └── tms_expanded_demo.xml
│
└── static/
    ├── description/
    │   ├── icon.png
    │   └── icon.svg
    └── src/
        ├── js/
        │   ├── tms_portal_link_handler.js
        │   ├── tms_tour.js
        │   └── tms_command.js
        └── css/
            └── tms_portal_signature_modal.css
```

---

## 6. Grupos de Seguridad

| Grupo       | XML ID              | Hereda de         | Permisos                                  |
| ----------- | ------------------- | ----------------- | ----------------------------------------- |
| Usuario TMS | `group_tms_user`    | `base.group_user` | CRUD en operaciones (sin delete waybill)  |
| Manager TMS | `group_tms_manager` | `group_tms_user`  | CRUD completo + configuración             |
| Chofer TMS  | `group_tms_driver`  | `base.group_user` | Solo lectura waybill + escritura tracking |

Portal (`base.group_portal`): Lectura waybill + firma + rechazo.

---

## 7. Dependencias del Módulo

```python
'depends': ['base', 'fleet', 'account', 'contacts', 'board', 'mail',
            'portal', 'web', 'website', 'sale_management', 'hr', 'web_tour']
```

**Críticas:** base, fleet, account, mail, portal, hr, contacts
**A evaluar:** sale_management (¿solo estética?), website (pesado), web_tour (solo onboarding), board

---

## 8. Menús

```
TMS (menu_tms_root)
├── Dashboard (action_tms_home)
├── Operaciones
│   ├── Viajes / Tablero (action_tms_waybill) ← KANBAN PRINCIPAL
│   ├── Vehículos (action_tms_vehicles)
│   ├── Remolques (action_tms_trailers)
│   ├── Operadores (action_tms_drivers)
│   ├── Destinos (action_tms_destination)
│   └── Historial Diesel (action_tms_fuel_history)
└── Configuración
    ├── Flota
    │   └── Tipos de Vehículo
    ├── Ajustes (res.config.settings)
    └── Catálogos SAT
        ├── Importar Catálogos (wizard)
        └── [11 catálogos...]
```

---

## 9. Roadmap Completo

### ✅ RELEASE V1.0 — Base Funcional (COMPLETADO)

- Etapa 1: Catálogos SAT (11 catálogos + wizard importación)
- Etapa 2: Gestión de Flota (extensión fleet.vehicle)
- Etapa 3: Destinos y Rutas
- Etapa 4: Cotizador Inteligente (3 propuestas)
- Etapa 5: Dashboard Kanban + Workflow
- Etapa 6: Portal Web (firma digital, rechazo, PDF)

### 🚧 RELEASE V2.0 — ESTABILIZACIÓN (PENDIENTE)

> Meta: Módulo instala limpio, workflow funcional end-to-end

| Etapa | Nombre                          | Descripción                                |
| ----- | ------------------------------- | ------------------------------------------ |
| 2.0.1 | Eliminar duplicados Python      | company_id ×2, vehicle_type ×2, methods ×2 |
| 2.0.2 | Fix res.partner                 | Quitar required=True, corregir Record Rule |
| 2.0.3 | Normalizar estados workflow     | Alinear Selection con métodos de acción    |
| 2.0.4 | Fix vehicle_id domain           | tms_is_trailer=False para tractores        |
| 2.0.5 | Unificar cp_type/waybill_type   | Elegir uno, eliminar el otro               |
| 2.0.6 | Fix amount_untaxed compute      | Resolver store=True vs compute store=False |
| 2.0.7 | Limpiar constraints redundantes | Unificar \_check duplicados                |
| 2.0.8 | Auditar dependencias manifest   | Evaluar sale_management, website, web_tour |
| 2.0.9 | QA — Instalar en base limpia    | Test completo en Odoo 19 CE                |

### 📋 RELEASE V2.1 — PULIDO UX

| Etapa | Nombre                 | Descripción                  |
| ----- | ---------------------- | ---------------------------- |
| 2.1.1 | Simplificar formulario | Campos visibles según estado |
| 2.1.2 | Smart buttons          | Contadores rápidos           |
| 2.1.3 | Kanban polish          | Colores, iconos              |
| 2.1.4 | Filtros y agrupaciones | Búsqueda optimizada          |
| 2.1.5 | Onboarding wizard      | Tour guiado primer uso       |

### 📋 RELEASE V2.2 — CARTA PORTE 3.1 COMPLETA

| Etapa | Nombre                 | Descripción                |
| ----- | ---------------------- | -------------------------- |
| 2.2.1 | Generador XML CP 3.1   | Template XML según XSD SAT |
| 2.2.2 | Validador pre-timbrado | Checklist visual           |
| 2.2.3 | Integración PAC        | Finkok/SW timbrado         |
| 2.2.4 | Cancelación CFDI       | Flujo con motivo           |
| 2.2.5 | PDF fiscal             | QR + cadena original       |

### 📋 RELEASE V2.3 — FACTURACIÓN REAL

| Etapa | Nombre                      | Descripción               |
| ----- | --------------------------- | ------------------------- |
| 2.3.1 | Crear factura desde waybill | Genera account.move       |
| 2.3.2 | Facturación masiva          | N waybills → 1 factura    |
| 2.3.3 | Conciliación pagos          | Vincular pagos con viajes |

### 📋 RELEASE V2.4 — INTELIGENCIA

| Etapa | Nombre              | Descripción               |
| ----- | ------------------- | ------------------------- |
| 2.4.1 | Dashboard KPIs      | Viajes/mes, utilidad, km  |
| 2.4.2 | Reporte utilidad    | Ingreso vs costos reales  |
| 2.4.3 | Alertas automáticas | Licencias, mantenimientos |
| 2.4.4 | Cron rutas          | Re-calcular rutas viejas  |

---

## 10. Issues Conocidos (V2.0 Backlog)

| ID   | Severidad | Descripción                                                 | Archivo              |
| ---- | --------- | ----------------------------------------------------------- | -------------------- |
| I-01 | 🔴        | company_id required=True en res.partner                     | res_partner.py       |
| I-02 | 🔴        | Record Rule partner sin fallback False                      | tms_security.xml     |
| I-03 | 🔴        | company_id duplicado en fleet_vehicle                       | tms_fleet_vehicle.py |
| I-04 | 🔴        | TmsVehicleType clase duplicada                              | tms_vehicle_type.py  |
| I-05 | 🔴        | \_check_waybill_constraints duplicado                       | tms_waybill.py       |
| I-06 | 🔴        | \_check_waybill_validity duplicado                          | tms_waybill.py       |
| I-07 | 🔴        | action_send_email ×3 (2 en waybill, 1 en line)              | tms_waybill.py       |
| I-08 | 🔴        | \_onchange_route_id ×2, v2 usa campos inexistentes          | tms_waybill.py       |
| I-09 | 🟡        | Estados inconsistentes (transit vs in_transit, etc.)        | tms_waybill.py       |
| I-10 | 🟡        | vehicle_id domain incorrecto (is_trailer=True)              | tms_waybill.py       |
| I-11 | 🟡        | cp_type vs waybill_type duplicados                          | tms_waybill.py       |
| I-12 | 🟡        | \_expand_states orden ilógico                               | tms_waybill.py       |
| I-13 | 🟡        | amount_untaxed store=True escrito desde compute store=False | tms_waybill.py       |
| I-14 | 🟢        | \_check_financials redundante                               | tms_waybill.py       |
| I-15 | 🟢        | Dependencias excesivas en manifest                          | **manifest**.py      |
| I-16 | 🟢        | Comentarios repetitivos                                     | Varios               |
| I-17 | 🟢        | action_send_email en WaybillLine sin sentido                | tms_waybill.py       |

---

## 11. Problemas Históricos (Evitar Repetir)

1. **Código duplicado:** Métodos y campos definidos múltiples veces en el mismo archivo
2. **Estados desalineados:** Selection dice una cosa, métodos escriben otra
3. **Campos fantasma:** onchange que referencia campos que no existen en el modelo
4. **required=True en modelos heredados:** Puede romper registros existentes del sistema
5. **compute store=False escribiendo en store=True:** No persiste en Odoo

---

## 12. Convenciones de Código

```python
# ═══════════════════════════════════════════════════════════════
# SIEMPRE:
# - _name, _description, _order en cada modelo nuevo
# - company_id obligatorio en modelos operativos
# - Docstrings en español
# - Comentarios explicando el "por qué", no solo el "qué"
# - Seguir naming: tms.modelo.submodelo
# - index=True en campos de búsqueda frecuente
# - check_company=True en Many2one a modelos con company_id
# - tracking=True en campos importantes para auditoría
#
# NUNCA:
# - Crear modelo nuevo si se puede extender uno nativo (_inherit)
# - company_id en catálogos SAT (son globales)
# - Definir el mismo campo o método dos veces
# - Escribir en campos store=True desde un compute store=False
# - required=True en campos heredados de módulos base
# - Referenciar campos que no existen en el modelo
# ═══════════════════════════════════════════════════════════════

# Ejemplo de estilo esperado:
class TmsWaybill(models.Model):
    """
    Modelo Maestro: Viaje / Carta Porte (Single Document Flow).
    Fusiona Cotización + Operación + Carta Porte en un solo documento.
    """
    _name = 'tms.waybill'
    _description = 'Viaje / Carta Porte'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'date_created desc, id desc'

    # --- SaaS ---
    company_id = fields.Many2one(
        'res.company', string='Compañía',
        required=True, default=lambda self: self.env.company,
        index=True,
    )

    # --- Workflow ---
    state = fields.Selection([...], tracking=True, group_expand='_expand_states')
```

---

## 13. Dev Workflow y Versionamiento Git

### Repositorio

- **Remoto:** GitHub
- **Rama principal:** `main` (código estable y validado)
- **Estrategia:** Feature branch → merge a main (simple)

### Flujo obligatorio por etapa

```bash
# ══════════════════════════════════════════════════════════════
# 1. CREAR BRANCH DESDE MAIN
# ══════════════════════════════════════════════════════════════
git checkout main
git pull origin main
git checkout -b etapa-2.0.1-eliminar-duplicados

# ══════════════════════════════════════════════════════════════
# 2. IMPLEMENTAR (Antigravity / Claude Code / Manual)
# ══════════════════════════════════════════════════════════════
# Pegar prompt de la etapa y ejecutar

# ══════════════════════════════════════════════════════════════
# 3. VALIDAR
# ══════════════════════════════════════════════════════════════
# a) Python sin errores de sintaxis
python3 -c "import py_compile; py_compile.compile('models/tms_waybill.py', doraise=True)"

# b) Actualizar módulo en Odoo
python3 odoo-bin -c odoo.conf -u tms -d tms_dev --stop-after-init

# c) Verificar logs: sin WARNING ni ERROR

# d) Test manual: crear waybill, recorrer workflow completo

# ══════════════════════════════════════════════════════════════
# 4. COMMIT + MERGE
# ══════════════════════════════════════════════════════════════
git add -A
git commit -m "etapa 2.0.1: eliminar duplicados python (I-03,I-04,I-05,I-06,I-07,I-08)"
git checkout main
git merge etapa-2.0.1-eliminar-duplicados
git push origin main
git branch -d etapa-2.0.1-eliminar-duplicados
```

### Reglas

- **NUNCA** hacer push directo a `main`
- **SIEMPRE** validar que el módulo actualice sin errores antes de merge
- **SIEMPRE** referenciar IDs de issues en el commit message
- Si el merge rompe algo → `git revert` inmediato

---

## 14. Instrucciones para Claude Code / Antigravity

Al iniciar en este proyecto:

1. **Lee este archivo primero** — es tu contexto base
2. **Revisa `models/`** — identifica qué modelos existen y cómo se relacionan
3. **Revisa `views/`** — identifica menús y vistas para no duplicar XML IDs
4. **Revisa `security/`** — identifica grupos y ACLs
5. **Antes de crear archivos**, verifica que no existan
6. **Antes de modificar vistas**, revisa XML IDs existentes
7. **Todo código** debe seguir las convenciones de la sección 12
8. **Todo entregable** debe pasar el QA de la sección 13
9. **Consulta sección 10** antes de tocar tms_waybill.py — hay bugs conocidos
10. **Los estados del workflow** están en sección 4 — SIEMPRE usar esos valores exactos

### Comandos útiles

```bash
# Actualizar módulo
python3 odoo-bin -c odoo.conf -u tms -d tms_dev --stop-after-init

# Instalar desde cero
python3 odoo-bin -c odoo.conf -i tms -d tms_clean --stop-after-init

# Validar Python
python3 -m py_compile models/tms_waybill.py

# Buscar duplicados de un método
grep -rn "def action_send_email" models/

# Buscar referencias a un estado
grep -rn "'transit'" models/ views/
```

---

## 15. Prompt Template (Para generar etapas)

Cuando Mois diga "siguiente etapa" o "prompt de la X.X", generar:

```markdown
# Etapa X.X — [Nombre]

## Walkthrough

[Explicación de qué se va a hacer y por qué]

## Plan

1. [Paso 1]
2. [Paso 2]
   ...

## Tasks

- [ ] Task 1: [descripción específica]
- [ ] Task 2: [descripción específica]
      ...

## Archivos a modificar

- `models/archivo.py` — [qué cambiar]
- `views/archivo.xml` — [qué cambiar]

## QA (Checklist post-implementación)

- [ ] `python3 -m py_compile models/archivo.py` sin errores
- [ ] `-u tms` sin WARNING ni ERROR en logs
- [ ] [Test funcional específico]
- [ ] [Otro test]

## Rollback

Si algo falla: `git checkout main -- models/archivo.py views/archivo.xml`
```

---

_Este archivo es el cerebro del proyecto. Mantenlo actualizado después de cada release._
