# CLAUDE.md — TMS "Hombre Camión" & Carta Porte 3.1

# ══════════════════════════════════════════════════════════════

# CONTEXTO PARA CLAUDE CODE / ANTIGRAVITY / CLAUDE WEB

# Última actualización: 2026-03-14 — V2.1.5 COMPLETADO

# ══════════════════════════════════════════════════════════════

## 1. Resumen del Proyecto

**Nombre:** TMS & Carta Porte 3.1 (SaaS Multi-Empresa)
**Nombre comercial:** Hombre Camión
**Versión Odoo:** 19 Community Edition
**Autor:** NextPack (nextpack.mx)
**Licencia:** LGPL-3
**Versión módulo:** 19.0.2.1.6

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
- **PAC:** Formas Digitales (forsedi.facturacfdi.mx — contrato activo) — para V2.2
- **Fiscal:** SAT Carta Porte 3.1, CFDI 4.0

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
`tms.sat.embalaje`, `tms.sat.material.peligroso`, `tms.sat.figura.transporte`

### Modelos PRIVADOS (con company_id + Record Rules):

`tms.waybill`, `tms.waybill.line`, `tms.destination`,
`fleet.vehicle`, `tms.fuel.history`, `tms.tracking.event`

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

⚠️ NUNCA usar: 'transit', 'destination', 'carta_porte' — NO EXISTEN → ValueError

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

### Retención IVA 4%

- Solo aplica cuando `partner_invoice_id.is_company == True`
- Fundamento: Art. 1-A LIVA + Art. 3 RLIVA

### TollGuru API v2

- Endpoint: `https://apis.tollguru.com/toll/v2/origin-destination-waypoints`
- Respuesta: `routes[0].summary.distance.value` metros → /1000 = km
- Duración: `routes[0].summary.duration.value` segundos → /3600 = horas
- Casetas: `routes[0].costs.tag`
- Caché en `tms.destination`

### Tren Vehicular

`vehicle_id (tracto) + trailer1_id + dolly_id + trailer2_id`

- `tms_is_trailer = False` → tractores
- `tms_is_trailer = True` → remolques/dollys
- Domain vehicle_id: `[('tms_is_trailer', '=', False)]`

---

## 5. Estructura de Archivos

```
tms/
├── __init__.py
├── __manifest__.py
├── CLAUDE.md
├── models/
│   ├── tms_waybill.py                  # MODELO MAESTRO
│   ├── tms_destination.py              # Rutas (caché TollGuru)
│   ├── tms_fleet_vehicle.py            # _inherit fleet.vehicle
│   ├── tms_vehicle_type.py             # Catálogo tipos vehículo
│   ├── tms_fuel_history.py             # Historial diesel
│   ├── tms_tracking_event.py           # Bitácora GPS
│   ├── hr_employee.py                  # _inherit chofer
│   ├── res_partner_tms.py              # _inherit contactos SAT
│   ├── res_company.py                  # _inherit empresa
│   ├── res_config_settings.py          # _inherit APIs + seguros
│   └── sat_*.py (11 catálogos SAT)
├── views/
│   ├── tms_waybill_views.xml           # Form + Kanban + List + Search
│   ├── tms_fleet_vehicle_views.xml
│   ├── tms_destination_views.xml
│   └── res_config_settings_views.xml
├── wizard/
│   ├── tms_cotizacion_wizard.py        # Wizard cotización 2 pasos
│   └── tms_cotizacion_wizard_views.xml
├── security/
│   ├── tms_security.xml
│   └── ir.model.access.csv
└── static/description/
```

---

## 6. Grupos de Seguridad

| Grupo       | XML ID              | Permisos                                  |
| ----------- | ------------------- | ----------------------------------------- |
| Usuario TMS | `group_tms_user`    | CRUD operaciones (sin delete waybill)     |
| Manager TMS | `group_tms_manager` | CRUD completo + configuración             |
| Chofer TMS  | `group_tms_driver`  | Solo lectura waybill + escritura tracking |

---

## 7. Estado del Proyecto

### ✅ V1.0 — Base Funcional (COMPLETADO)

### ✅ V2.0 — Estabilización (COMPLETADO — 9/9 etapas)

| Etapa | Nombre                               | Estado |
| ----- | ------------------------------------ | ------ |
| 2.0.1 | Eliminar duplicados Python           | ✅     |
| 2.0.2 | Fix estados + Dolly + TollGuru       | ✅     |
| 2.0.3 | Campos SAT + ACL regímenes           | ✅     |
| 2.0.4 | Fix partner + multi-empresa          | ✅     |
| 2.0.5 | Fix domain vehículo + amount_untaxed | ✅     |
| 2.0.6 | Unificar cp_type/waybill_type        | ✅     |
| 2.0.7 | Limpiar constraints                  | ✅     |
| 2.0.8 | Auditar manifest + fix UI remolques  | ✅     |
| 2.0.9 | QA BD limpia + datos demo + E2E      | ✅     |

### 🚧 V2.1 — Pulido UX (EN CURSO)

| Etapa  | Nombre                                       | Estado            |
| ------ | -------------------------------------------- | ----------------- |
| 2.1.1  | Formulario por estado                        | ✅                |
| 2.1.2  | Smart buttons                                | ✅                |
| 2.1.3  | Kanban polish                                | ✅                |
| 2.1.4a | Wizard cotización base 2 pasos               | ✅                |
| 2.1.4b | Rediseño UX 3 columnas propuestas            | ✅                |
| 2.1.4c | Estados cotizado+aprobado                    | ✅                |
| 2.1.4d | Mercancías simplificadas Paso 1              | ✅                |
| 2.1.4e | Wizard desde lista, no desde form            | ✅                |
| 2.1.4f | Cierre V2.1.4 (fix direcciones + botón form) | 🚧 En Claude Code |
| 2.1.5  | Onboarding wizard 6 pasos                    | ✅                |
| 2.1.6  | PDF pre-cotización + email                   | ✅                |

### 📋 V2.2 — Carta Porte 3.1 + Timbrado Formas Digitales

**PAC:** Formas Digitales (forsedi.facturacfdi.mx)
**Incluye:**

- Radio button ambiente pruebas/producción en config empresa
- URLs automáticas según selección:
  - Pruebas: `dev33.facturacfdi.mx` / usuario: pruebasWS
  - Producción: `v33.facturacfdi.mx`
- Timbrado CFDI 4.0 con Complemento Carta Porte 3.1
- Cancelación método 1 (con .cer + .key)
- Consulta estatus CFDI

**Campos nuevos res.company:**

```python
fd_usuario, fd_password, fd_user_id   # Credenciales FD
csd_cer, csd_key, csd_password        # Certificados SAT
rfc_emisor, regimen_fiscal            # Datos fiscales
```

### 📋 V2.3 — Facturación Real

### 📋 V2.4 — KPIs y Reportes / Portal aprobación web

### 📋 V2.5 — Limpieza Final "Modo Hombre Camión"

- 0 warnings en logs
- 0 métodos huérfanos
- Menú simplificado
- Tooltips en lenguaje transportista
- Validaciones amigables
- Flujo 3 clics verificado
- QA con usuario nuevo < 10 min primera Carta Porte

### 📋 V3.0 — App Flutter chofer + SaaS

- Estados tránsito para app: En Origen → Cargando → En Tránsito → En Destino → Descargando → Liberado
- Onboarding automático SaaS
- Webhook MercadoPago/Stripe
- Multi-tenant Formas Digitales

---

## 8. Wizard Cotización (V2.1.4) — Arquitectura

### Modelo: tms.cotizacion.wizard (TransientModel)

- Paso 1: Cliente + CP origen/destino + variables → calcular → 3 propuestas
- Paso 2: Datos completos (solo si aprueba) → crear waybill

### Paso 1 campos:

```python
partner_invoice_id  # Cliente (required)
origin_zip, dest_zip
num_axles
# COSTOS OPERATIVOS (Propuesta B)
diesel_price, fuel_performance
driver_salary, maneuvers, other_costs, commission
# PRECIO POR KM (Propuesta A)
price_per_km, margin_percent
# PRECIO DIRECTO (Propuesta C)
direct_price
# RESULTADO (después de calcular)
distance_km, duration_hours, toll_cost
proposal_km_total, proposal_trip_total
selected_proposal
```

### Paso 2 campos:

```python
partner_origin_id, partner_dest_id  # Remitente/Destinatario
vehicle_id, trailer1_id, dolly_id, trailer2_id
driver_id
# Mercancías completas con Clave SAT
line_ids → tms.cotizacion.wizard.line
```

### Mercancías Paso 1 (simplificadas):

Solo: description + quantity + weight_kg
Sin: Clave SAT, Unidad SAT, Material Peligroso

### Mercancías Paso 2 (completas):

Clave SAT, Unidad SAT (default KGM), Material Peligroso, etc.

### Flujo UI:

1. Botón "Nueva Cotización" en vista LISTA (no en formulario)
2. Wizard crea waybill en estado `cotizado`
3. Waybill cotizado muestra solo: cliente + precio
4. Botón "Aprobar Cotización" → estado `aprobado`
5. Estado aprobado → formulario completo visible
6. "Confirmar Pedido" → estado `draft`/`en_pedido`

---

## 9. Onboarding Wizard V2.1.5 (Planeado)

6 pasos para primera configuración:

1. Empresa + CSD (.cer + .key + contraseña) + Logo
2. Vehículo principal + remolque + dolly + config SCT visual (imágenes)
3. Seguros: RC + Carga + Ambiental (aseguradora SAT + póliza + vigencia)
4. Chofer + licencia federal + tipo + vigencia (¿eres tú el chofer?)
5. Primer cliente + buscar RFC en SAT (autocompleta nombre)
6. Resumen + botón "Crear mi primer viaje"

Meta: usuario nuevo saca primera Carta Porte en < 14 minutos.

---

## 10. Issues Conocidos Activos

| ID     | Severidad | Descripción                                             | Estado                                       |
| ------ | --------- | ------------------------------------------------------- | -------------------------------------------- |
| FIX-01 | ✅        | widget monetary sin currency_field en wizard            | Resuelto — currency_id invisible ya existe   |
| FIX-02 | ✅        | is_dangerous no definido en wizard.line                 | Resuelto — campo y vista ya existen          |
| FIX-03 | 🚧        | Direcciones origen/destino no se pasan al crear waybill | En Claude Code (etapa 2.1.4f)                |
| FIX-04 | ✅        | Retención 4% no considera is_company                    | Resuelto — lógica correcta en tms_waybill.py |

---

## 11. Problemas Históricos (NUNCA Repetir)

1. **Código duplicado** — Python usa la última definición silenciosamente
2. **Estados desalineados** — Selection vs métodos → ValueError
3. **Campos fantasma** — onchange referencia campos inexistentes → AttributeError
4. **required=True en modelos heredados** — Rompe registros del sistema
5. **compute store=False escribiendo store=True** — No persiste en BD
6. **\_fetch_tollguru_api duplicada** — Verificar con grep antes de agregar
7. **Leer mal JSON TollGuru** — Usar routes[0], no route ni metric
8. **widget monetary sin currency_field** — OWL error en Odoo 19
9. **column_invisible con campo inexistente** — EvalError en OWL
10. **on_create en kanban agrupado** — No funciona en Odoo 19 con group_by activo

---

## 12. Dev Workflow Git

```bash
# Primer prompt de cada etapa:
git checkout main && git pull origin main
git checkout -b etapa-X.X-nombre

# Validar antes de commit:
python3 -m py_compile models/tms_waybill.py
odoo-19.0/.venv/bin/python odoo-19.0/odoo-bin \
  -c proyectos/tms/odoo.conf -d tms_nuevo -u tms --stop-after-init

# Commit (sin push hasta que Mois indique):
git add -A
git commit -m "etapa-X.X: descripción"

# Merge cuando Mois lo indique:
git checkout main
git merge etapa-X.X-nombre
git push origin main
git branch -d etapa-X.X-nombre
```

---

## 13. Reglas de Trabajo

### Claude Code (consola IDE)

- Lee CLAUDE.md automáticamente al iniciar — NO incluir en cada prompt
- Usar modo **Ask before edit** para cambios quirúrgicos
- Usar modo **Edit automatic** para refactors grandes
- NO hacer commit hasta que Mois lo apruebe explícitamente

### Antigravity

- Primer prompt de cada etapa: incluir contexto completo (SDD)
- Prompts siguientes dentro de la misma etapa: NO repetir contexto

### Prioridad de pensamiento Antigravity:

- `Planning + High` → SDDs, modelos nuevos, integraciones API
- `Planning + Low` → lógica Python, bugs complejos, cálculos
- `Fast + Flash` → XML, labels, colores, fix una línea, verificaciones

### Idioma

- TODO en ESPAÑOL: walkthrough, comentarios, tasks

### Formato SDD obligatorio (Antigravity):

1. GIT (solo primer prompt de etapa)
2. Walkthrough en español
3. grep/verificar antes de implementar
4. Tasks checkboxes
5. QA comandos exactos
6. Rollback
7. Actualizar CLAUDE.md (OBLIGATORIO antes del commit)
8. Commit (sin push)
9. Context Blueprint para Gemini

### Qué actualizar en CLAUDE.md (paso 7):

- Fecha en el encabezado → fecha actual
- Tabla de etapas → marcar esta etapa como ✅
- Issues Conocidos → marcar resueltos los que se hayan fixeado
- Problemas Históricos → agregar si se descubrió algo nuevo durante la etapa

Verificar con:

```bash
grep -n "✅\|🚧\|📋\|Última actualización" CLAUDE.md | head -20
```

### Al finalizar cada etapa:

Explicar brevemente los conceptos clave del código generado para que Mois aprenda.

---

_Este archivo es el cerebro del proyecto. Actualizar después de cada release._
