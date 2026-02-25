# CLAUDE.md — TMS "Hombre Camión" & Carta Porte 3.1

# ══════════════════════════════════════════════════════════════

# CONTEXTO PARA CLAUDE CODE / ANTIGRAVITY / CLAUDE WEB

# Última actualización: 2026-02-25

# ══════════════════════════════════════════════════════════════

## 1. Resumen del Proyecto

**Nombre:** TMS & Carta Porte 3.1 (SaaS Multi-Empresa)
**Nombre comercial:** Hombre Camión
**Versión Odoo:** 19 Community Edition
**Autor:** NextPack (nextpack.mx)
**Licencia:** LGPL-3
**Versión módulo:** 19.0.2.0.0

**Qué es:** Módulo vertical completo para gestión de transporte de carga en México.
Cubre desde cotización hasta facturación, con cumplimiento fiscal (Carta Porte 3.1 / CFDI 4.0).

**Arquitectura clave:** Single Document Flow — `tms.waybill` es el modelo maestro
que fusiona Cotización + Operación + Carta Porte en un solo registro.

---

## 2. Stack Tecnológico

- **Backend:** Python 3.12+, Odoo 19 CE
- **BD:** PostgreSQL 16+ (local: MariaDB compatible)
- **Frontend:** OWL (Odoo Web Library), QWeb templates
- **APIs externas:** TollGuru API v2 (activa), Google Routes API (disponible)
- **Fiscal:** SAT Carta Porte 3.1, CFDI 4.0

---

## 3. Arquitectura SaaS Multi-Empresa

### Regla de oro:

- **Catálogos SAT** → GLOBALES (sin `company_id`) → Compartidos entre empresas
- **Datos operativos** → PRIVADOS (con `company_id` obligatorio) → Aislados por empresa
- **APIs de rutas** → GLOBALES via `config_parameter` (una cuenta compartida)
- **Seguros Carta Porte** → POR EMPRESA via `related='company_id.campo'`

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
- `tms.destination` — Rutas comerciales frecuentes (caché TollGuru)
- `fleet.vehicle` — Vehículos (extensión del nativo)
- `tms.fuel.history` — Historial de precios diesel
- `tms.tracking.event` — Eventos GPS / bitácora

### Modelos EXTENDIDOS (herencia \_inherit):

- `fleet.vehicle` — Agrega: tms_is_trailer, tms_num_axles, tms_fuel_performance,
  tms_gross_vehicle_weight, campos SAT autotransporte
- `hr.employee` — Agrega campos de chofer (licencia, RFC, régimen)
- `res.partner` — Agrega campos SAT (CP, colonia, municipio, régimen fiscal)
  company_id con default=lambda self: self.env.company, SIN required=True
- `res.company` — Agrega seguros: seguro*rc*_, seguro*ma*_, seguro*carga*\*
- `res.config.settings` — Campos seguros via related, APIs via config_parameter

### Record Rule res.partner (CRÍTICA):

```python
# SIEMPRE usar este dominio para partners — permite globales Y privados
['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]
```

---

## 4. Modelo Maestro: tms.waybill

### Workflow de Estados

```
draft ──→ en_pedido ──→ assigned ──→ waybill ──→ in_transit ──→ arrived ──→ closed
  │                                                                           │
  └──→ rejected (portal)                                      cancel ←───────┘
```

| Estado      | Clave        | Quién actúa                 | Qué pasa                                      |
| ----------- | ------------ | --------------------------- | --------------------------------------------- |
| Solicitud   | `draft`      | Operador                    | Captura cotización, elige propuesta de precio |
| En Pedido   | `en_pedido`  | Cliente (portal) o Operador | Cliente firma/acepta o operador confirma      |
| Por Asignar | `assigned`   | Operador                    | Asigna vehículo, chofer, remolques            |
| Carta Porte | `waybill`    | Sistema                     | Valida cumplimiento CP 3.1 completo           |
| En Trayecto | `in_transit` | Chofer (app) o Operador     | Registra inicio de ruta + GPS                 |
| En Destino  | `arrived`    | Chofer (app) o Operador     | Registra llegada + GPS                        |
| Facturado   | `closed`     | Operador                    | Crea factura, cierra viaje                    |
| Cancelado   | `cancel`     | Operador                    | Anula el viaje                                |
| Rechazado   | `rejected`   | Cliente (portal)            | Rechaza cotización con motivo                 |

⚠️ CRÍTICO: Estos son los ÚNICOS valores válidos del Selection. Nunca usar:
'transit', 'destination', 'carta_porte' — NO EXISTEN y causan ValueError.

### Tren Vehicular (V2.0.2)

```
Tracto (vehicle_id) + Remolque1 (trailer1_id) + Dolly (dolly_id) + Remolque2 (trailer2_id)
```

- `total_axles` = suma de `tms_num_axles` de cada unidad asignada
- `tms_is_trailer = False` → tractores | `tms_is_trailer = True` → remolques/dollys
- `tms_fuel_performance` → Km/L del tracto, se autocompleta al seleccionar vehículo
- Domain correcto para vehicle_id: `[('tms_is_trailer', '=', False)]`

### TollGuru API v2 (Activa)

**Endpoint:** `https://apis.tollguru.com/toll/v2/origin-destination-waypoints`
**Config:** `tms.tollguru_api_key` (global), `tms.tollguru_debug` (opcional)

**Mapeo de ejes:**

```python
TOLLGURU_AXLES_MAP = {
    2: "2AxlesTruck", 3: "3AxlesTruck", 4: "4AxlesTruck",
    5: "5AxlesTruck", 6: "6AxlesTruck", 7: "7AxlesTruck",
    8: "8AxlesTruck", 9: "9AxlesTruck",
}
```

**Estructura de respuesta real TollGuru:**

```json
{
  "routes": [
    {
      "summary": {
        "distance": { "value": 369814 },
        "duration": { "value": 22604 }
      },
      "costs": { "tag": 3255, "cash": 3255, "fuel": 3661.22 }
    }
  ]
}
```

- Distancia: `routes[0].summary.distance.value` (metros → /1000 = km)
- Duración: `routes[0].summary.duration.value` (segundos → /3600 = horas)
- Casetas: `routes[0].costs.tag` (preferir tag sobre cash)

**Caché:** `tms.destination` guarda resultados por CP origen + CP destino + tipo vehículo.
Si existe en caché, NO llama a la API.

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

`selected_proposal` determina cuál se aplica a `amount_untaxed`.
IVA 16%, Retención IVA 4%.

---

## 5. Estructura de Archivos

```
tms/
├── __init__.py
├── __manifest__.py
├── CLAUDE.md                           ← ESTE ARCHIVO
│
├── models/
│   ├── tms_waybill.py                  # MODELO MAESTRO (~2000 líneas)
│   ├── tms_destination.py              # Rutas (caché TollGuru)
│   ├── tms_fleet_vehicle.py            # _inherit fleet.vehicle
│   ├── tms_vehicle_type.py             # Catálogo tipos vehículo
│   ├── tms_fuel_history.py             # Historial diesel
│   ├── tms_tracking_event.py           # Bitácora GPS
│   ├── hr_employee.py                  # _inherit chofer
│   ├── res_partner_tms.py              # _inherit contactos SAT
│   ├── res_company.py                  # _inherit defaults empresa
│   ├── res_config_settings.py          # _inherit configuración APIs
│   ├── sat_clave_prod.py               # Catálogo SAT (GLOBAL)
│   ├── sat_clave_unidad.py             # Catálogo SAT (GLOBAL)
│   ├── sat_codigo_postal.py            # Catálogo SAT (GLOBAL)
│   ├── sat_colonia.py                  # Catálogo SAT (GLOBAL)
│   ├── sat_localidad.py                # Catálogo SAT (GLOBAL)
│   ├── sat_municipio.py                # Catálogo SAT (GLOBAL)
│   ├── sat_config_autotransporte.py    # Catálogo SAT (GLOBAL)
│   ├── sat_tipo_permiso.py             # Catálogo SAT (GLOBAL)
│   ├── sat_embalaje.py                 # Catálogo SAT (GLOBAL)
│   ├── sat_material_peligroso.py       # Catálogo SAT (GLOBAL)
│   └── sat_figura_transporte.py        # Catálogo SAT (GLOBAL)
│
├── views/
│   ├── tms_waybill_views.xml           # Form + Kanban + List + Search
│   ├── tms_fleet_vehicle_views.xml     # Vehículos/Remolques
│   ├── tms_destination_views.xml       # Rutas
│   ├── res_config_settings_views.xml   # Configuración (Global vs Empresa)
│   └── ...resto de vistas
│
├── security/
│   ├── tms_security.xml                # Grupos + Record Rules
│   └── ir.model.access.csv             # ACLs
│
└── static/description/
    ├── icon.png
    └── icon.svg
```

---

## 6. Grupos de Seguridad

| Grupo       | XML ID              | Permisos                                  |
| ----------- | ------------------- | ----------------------------------------- |
| Usuario TMS | `group_tms_user`    | CRUD en operaciones (sin delete waybill)  |
| Manager TMS | `group_tms_manager` | CRUD completo + configuración             |
| Chofer TMS  | `group_tms_driver`  | Solo lectura waybill + escritura tracking |

---

## 7. Estado del Proyecto — V2.0

### ✅ Etapas Completadas

| Etapa | Nombre                               | Issues Resueltos                   |
| ----- | ------------------------------------ | ---------------------------------- |
| 2.0.1 | Eliminar duplicados Python           | I-03,I-04,I-05,I-06,I-07,I-08      |
| 2.0.2 | Fix estados + Dolly + TollGuru       | I-09 + tren vehicular completo     |
| 2.0.3 | Campos SAT + ACL regímenes           | I-10 (verificado, ya existía)      |
| 2.0.4 | Fix partner + multi-empresa          | I-01,I-02 (verificado, ya existía) |
| 2.0.5 | Fix domain vehículo + amount_untaxed | I-10, I-13                         |
| 2.0.6 | Unificar cp_type/waybill_type        | I-11 (Unificado en waybill_type)   |
| 2.0.7 | Limpiar constraints redundantes      | I-14 (Removido \_check_financials) |
| 2.0.8 | Auditar dependencias manifest        | I-15 (Limpieza de dependencias)    |
| 2.0.9 | QA instalar base limpia              | — (Validado pipeline E2E)          |

### 📋 Etapas Próximas (V2.1+)

V2.0 Finalizada. Preparando terreno para automatización de cotización y UX.

---

### Issues Resueltos (NO repetir)

- ✅ I-01: required=True en res.partner → eliminado
- ✅ I-02: Record Rule sin fallback False → corregido
- ✅ I-03: company_id duplicado en fleet_vehicle → eliminado
- ✅ I-04: TmsVehicleType duplicado → eliminado
- ✅ I-05,06,07,08: Métodos duplicados en tms_waybill.py → eliminados
- ✅ I-09: Estados inconsistentes (transit/destination/carta_porte) → corregidos
- ✅ I-10: vehicle_id domain incorrecto (tms_is_trailer=False) → corregido
- ✅ I-11: cp_type vs waybill_type duplicados → unificados
- ✅ I-13: amount_untaxed persistencia con botón aplicar → corregido
- ✅ I-14: \_check_financials redundante → eliminado
- ✅ I-15: Dependencias excesivas en manifest → corregido

---

## 9. Problemas Históricos (NUNCA Repetir)

1. **Código duplicado** — Métodos y campos definidos múltiples veces. Python usa la última definición silenciosamente.
2. **Estados desalineados** — Selection dice una cosa, métodos escriben otra → ValueError
3. **Campos fantasma** — onchange que referencia campos que no existen → AttributeError
4. **required=True en modelos heredados** — Rompe registros existentes del sistema
5. **compute store=False escribiendo en store=True** — No persiste en BD
6. **\_fetch_tollguru_api duplicada** — Ya ocurrió, verificar siempre con grep antes de agregar métodos
7. **Leer mal JSON de TollGuru** — La respuesta usa `routes[0]` no `route`, `summary.distance.value` no `metric`

---

## 10. Convenciones de Código

```python
# ═══════════════════════════════════════════════════════════════
# SIEMPRE:
# - _name, _description, _order en cada modelo nuevo
# - company_id obligatorio en modelos operativos
# - Docstrings y comentarios en ESPAÑOL
# - Comentarios explicando el "por qué", no solo el "qué"
# - Seguir naming: tms.modelo.submodelo
# - index=True en campos de búsqueda frecuente
# - check_company=True en Many2one a modelos con company_id
# - tracking=True en campos importantes para auditoría
# - @api.depends completo con TODOS los campos que disparan el compute
#
# NUNCA:
# - Crear modelo nuevo si se puede extender con _inherit
# - company_id en catálogos SAT (son globales)
# - Definir el mismo campo o método dos veces
# - Escribir en campos store=True desde compute store=False
# - required=True en campos heredados de módulos base
# - Referenciar campos que no existen en el modelo
# - push directo a main
# ═══════════════════════════════════════════════════════════════
```

---

## 11. Reglas de Trabajo con Antigravity

### Prioridad de pensamiento

- `@high` — Lógica compleja: SDDs, cálculos, nuevos modelos, integraciones API
- `@low` — Cambios simples: XML, botones, colores, labels, ajustes visuales

### Idioma

- TODO el walkthrough, comentarios de código y explicaciones → **ESPAÑOL**

### Formato SDD obligatorio

Cada prompt de etapa incluye:

1. GIT (solo primer prompt de la etapa)
2. Walkthrough en español
3. Instrucción de verificar antes de implementar
4. Tasks con checkboxes
5. QA con comandos exactos
6. Rollback
7. Commit (sin push)
8. Context Blueprint para Gemini

### Context Blueprint para Gemini (sección final obligatoria)

```markdown
### 🛠 Context Blueprint para Gemini

Scope Modelos: [_name de modelos involucrados]
File Manifest:

- ruta/archivo.py → Crear | Modificar
- ruta/archivo.xml → Crear | Modificar
  Odoo Logic Priorities:
- @api.depends('campo1', 'campo2') → \_compute_xyz
- @api.onchange('campo') → \_onchange_xyz
- @api.constrains('campo') → \_check_xyz
  Security:
- ir.model.access.csv → agregar línea modelo X
- groups → group_tms_user / group_tms_manager
  Manifest Update: [sí/no, qué agregar]
  Dependencies: [librerías Python externas si aplica]
```

---

## 12. Dev Workflow Git

```bash
# Solo primer prompt de cada etapa:
git checkout main && git pull origin main
git checkout -b etapa-X.X-nombre

# Validar siempre antes de commit:
python3 -m py_compile models/tms_waybill.py
odoo-19.0/.venv/bin/python odoo-19.0/odoo-bin \
  -c proyectos/tms/odoo.conf -d tms_nuevo -u tms --stop-after-init

# Commit (sin push hasta que Mois indique):
git add -A
git commit -m "etapa-X.X: descripción (I-XX, I-XX)"

# Merge cuando Mois lo indique:
git checkout main
git merge etapa-X.X-nombre
git push origin main
git branch -d etapa-X.X-nombre
```

---

## 13. Roadmap Completo

### ✅ V1.0 — Base Funcional (COMPLETADO)

### ✅ V2.0 — Estabilización (COMPLETADO — 9/9 etapas)

### 📋 V2.1 — Pulido UX

- Wizard cotización multi-paso (usuario no ve cálculos, se sorprende con propuestas)
- Smart buttons, kanban polish, filtros, onboarding wizard

### 📋 V2.2 — Carta Porte 3.1 Completa

### 📋 V2.3 — Facturación Real

### 📋 V2.4 — Inteligencia / KPIs

### 📋 V2.5 — Transporte Especializado

- Caja refrigerada (bitácora temperaturas, alertas, costos refrigeración)
- Materiales peligrosos completo
- Carga sobredimensionada

### 📋 V3.0 — tms_saas (módulo separado)

- Onboarding automático, webhook MercadoPago/Stripe
- Provisioning wizard, panel admin capacidad BD

---

_Este archivo es el cerebro del proyecto. Actualizar después de cada release._
