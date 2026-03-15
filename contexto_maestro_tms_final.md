# 🚛 CONTEXTO MAESTRO — TMS Hombre Camión
# Archivo único para Proyecto TMS en Claude Web
> Versión módulo: 19.0.2.1.4 | Actualizado: 2026-03-14

---

## CÓMO USAR ESTE ARCHIVO

- **Claude Web** → pégalo al inicio de cada sesión o tenlo en el Proyecto
- **Antigravity** → pégalo como contexto en el primer prompt de cada conversación
- **Claude Code CLI** → referenciado desde `CLAUDE.md`
- Para ver el roadmap visual interactivo en Claude Web → escribe: **"Muéstrame el roadmap"**

---

## 1. IDENTIDAD DEL PROYECTO

| Campo | Valor |
|---|---|
| **Módulo** | TMS "Hombre Camión" (`tms/`) |
| **Nombre comercial** | Hombre Camión |
| **Repo** | github.com/NextPackMex/tms |
| **Stack** | Python 3.12+, Odoo 19 CE, MariaDB compatible, JavaScript, OWL, QWeb |
| **Arquitectura** | Single Document Flow — `tms.waybill` fusiona Cotización + Operación + Carta Porte |
| **APIs externas** | TollGuru API v2 (activa), Google Routes API (disponible) |
| **PAC** | Formas Digitales (forsedi.facturacfdi.mx — contrato activo) — para V2.2 |
| **Fiscal** | SAT Carta Porte 3.1, CFDI 4.0 |
| **Autor** | NextPack (nextpack.mx) |
| **Licencia** | LGPL-3 |
| **Progreso actual** | ~40% — V2.1.4f completado, V2.1.5 es la siguiente etapa |

---

## 2. PRINCIPIO RECTOR DE NEGOCIO

> NextPack cobra por **acceso, información y confianza** — nunca por intermediar dinero entre partes.
> Sin factoraje (requiere SOFOM), sin seguros intermediados (requiere CNSF), sin tarjeta combustible.
> Modelo limpio y sin riesgo legal.

---

## 3. ARQUITECTURA SAAS MULTI-EMPRESA

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
tms.route.analytics (global — datos de toda la plataforma)
```

### Modelos CON company_id (privados):
```
tms.waybill, tms.waybill.line, tms.destination,
fleet.vehicle, tms.fuel.log, tms.tracking.event,
tms.driver.settlement, tms.maintenance.order, tms.maintenance.plan,
tms.evidence.photo, tms.digital.signature, tms.subscription
```

### Infraestructura SaaS (V2.8):
```
Load Balancer (nginx) → Odoo Workers → PostgreSQL Cluster (1 DB por tenant)
                                              ↓
                                       Redis Cache (catálogos SAT globales)
```

---

## 4. MODELO MAESTRO: tms.waybill

### Workflow de Estados — ÚNICOS VÁLIDOS
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

⚠️ PROHIBIDO usar: `'transit'`, `'destination'`, `'carta_porte'` → ValueError

### Motor de Cotización — 3 Propuestas
- **A) Por KM:** `(distancia + km_extras) × precio_km`
- **B) Por Viaje:** `(diesel + casetas + chofer + maniobras + otros + comisión) / (1 - margen%)`
- **C) Precio Directo:** monto capturado manualmente

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

### Hook al cerrar viaje (sembrar en V2.3)
```python
def write(self, vals):
    res = super().write(vals)
    if vals.get('state') == 'closed':
        # Alimenta el motor de matching con datos reales de la ruta
        self.env['tms.route.analytics']._update_from_waybill(self)
    return res
```

---

## 5. ESTRUCTURA DE ARCHIVOS — COMPLETA

```
tms/                                # Módulo principal
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
│   ├── tms_fuel_history.py         # Historial diesel (reemplazado por tms_fuel/)
│   ├── tms_tracking_event.py       # Bitácora GPS
│   ├── tms_evidence.py             # Evidencia fotográfica (V2.4b) 🆕
│   ├── hr_employee.py              # _inherit chofer
│   ├── res_partner_tms.py          # _inherit contactos SAT
│   ├── res_company.py              # _inherit empresa
│   ├── res_config_settings.py      # _inherit APIs + seguros
│   └── sat_*.py                    # 11 catálogos SAT
├── views/
│   ├── tms_waybill_views.xml
│   ├── tms_fleet_vehicle_views.xml
│   ├── tms_destination_views.xml
│   └── res_config_settings_views.xml
├── wizard/
│   ├── tms_cotizacion_wizard.py
│   └── tms_cotizacion_wizard_views.xml
├── security/
│   ├── tms_security.xml
│   └── ir.model.access.csv
├── tests/
│   └── test_tms_waybill.py
└── docs/
    └── etapa-X.X.X.md

tms_fuel/                           # Combustible y rendimiento (V2.4) 🆕
├── models/
│   ├── tms_fuel_log.py             # Registro por carga de diesel
│   └── tms_vehicle_performance.py  # KPIs acumulados por vehículo
└── views/

tms_signature/                      # Firma digital simple (V2.4c) 🆕
├── models/
│   └── tms_digital_signature.py    # SHA-256 + canvas + SMS + QR
├── controllers/
│   └── verify.py                   # GET /verify/{token} público
└── views/

tms_settlement/                     # Liquidación de choferes (V2.4d) 🆕
├── models/
│   ├── tms_driver_settlement.py    # Liquidación por viaje
│   ├── tms_driver_expense.py       # Gastos individuales del chofer
│   └── tms_driver_advance.py       # Anticipos al chofer
└── views/

tms_maintenance/                    # Mantenimiento de unidades (V2.5) 🆕
├── models/
│   ├── tms_maintenance_plan.py     # Servicio preventivo por tipo
│   └── tms_maintenance_order.py    # Falla correctiva
└── views/

tms_saas/                           # Multi-tenant + cobro (V2.8)
├── models/
│   ├── tms_tenant.py
│   ├── tms_subscription.py         # Planes free/pro/flota
│   └── tms_usage_log.py
└── controllers/
    ├── onboarding.py
    └── webhooks_mercadopago.py

tms_marketplace/                    # Marketplace de cargas (Fase 2)
├── models/
│   ├── tms_load.py
│   ├── tms_market_bid.py
│   ├── tms_carrier_profile.py
│   └── tms_route_analytics.py      # Llena modelo sembrado en V2.2
├── services/
│   ├── matching_engine.py
│   └── pricing_engine.py
├── controllers/
│   └── portal_shipper.py
└── views/

tms_api/                            # API REST pública (Fase 2)
└── controllers/
    ├── auth.py
    ├── loads.py
    ├── waybills.py
    └── tracking.py

tms_analytics/                      # Datos de mercado (Fase 3)
└── models/
    └── tms_platform_analytics.py
```

---

## 6. MÓDULOS ODOO — MAPA DE DEPENDENCIAS

| Módulo | Fase | Versión | Depende de | Estado |
|---|---|---|---|---|
| `tms/` | 1 | V2.x | Odoo base | ✅ En curso |
| `tms_fuel/` | 1 🆕 | V2.4 | tms | 📋 Planeado |
| `tms_signature/` | 1 🆕 | V2.4c | tms | 📋 Planeado |
| `tms_settlement/` | 1 🆕 | V2.4d | tms · tms_fuel · tms_signature | 📋 Planeado |
| `tms_maintenance/` | 1 🆕 | V2.5 | tms | 📋 Planeado |
| `tms_saas/` | 1 | V2.8 | tms | 📋 Planeado |
| `tms_marketplace/` | 2 | M2.1 | tms · tms_saas | 📋 Planeado |
| `tms_api/` | 2 | M2.3 | tms · tms_marketplace | 📋 Planeado |
| `tms_analytics/` | 3 | F3.2 | tms · tms_marketplace | 📋 Planeado |

---

## 7. GRUPOS DE SEGURIDAD — TODOS LOS MÓDULOS

| Grupo | Módulo | Permisos |
|---|---|---|
| `group_tms_user` | tms | CRUD operaciones (sin delete waybill) |
| `group_tms_manager` | tms | CRUD completo + configuración |
| `group_tms_driver` | tms | Lectura waybill + escritura tracking |
| `group_tms_fuel_mgr` | tms_fuel | Ver rendimiento todos los vehículos |
| `group_tms_settle_mgr` | tms_settlement | Crear y aprobar liquidaciones |
| `group_tms_maint_mgr` | tms_maintenance | Gestionar órdenes mantenimiento |
| `group_tms_shipper` | tms_marketplace | Publicar cargas, ver ofertas |
| `group_tms_carrier_public` | tms_marketplace | Ver load board, hacer ofertas |
| `group_tms_marketplace_mgr` | tms_marketplace | NextPack modera cargas y perfiles |
| `group_tms_data_viewer` | tms_analytics | Reportes de mercado (plan datos) |
| `group_tms_platform_admin` | tms_analytics | Métricas globales NextPack CEO |

---

## 8. WIZARD DE COTIZACIÓN (V2.1.4)

### Modelo: `tms.cotizacion.wizard` (TransientModel)
- **Paso 1:** CP origen/destino + variables → calcular → 3 propuestas
- **Paso 2:** Datos completos (solo si aprueba) → crear waybill

### Paso 1 — campos:
```python
partner_invoice_id          # Cliente (required)
origin_zip, dest_zip        # CPs para TollGuru
num_axles                   # Ejes del vehículo
diesel_price, fuel_performance
driver_salary, maneuvers, other_costs, commission
price_per_km, margin_percent
direct_price
distance_km, duration_hours, toll_cost
proposal_km_total, proposal_trip_total
selected_proposal
```

### Paso 2 — campos:
```python
partner_origin_id, partner_dest_id
vehicle_id, trailer1_id, dolly_id, trailer2_id
driver_id
line_ids                    # Mercancías con Clave SAT
```

### Conexión con tms_fuel (V2.4):
```python
@api.onchange('vehicle_id')
def _onchange_vehicle_performance(self):
    # Autocompleta costo diesel con dato real histórico del vehículo
    if self.vehicle_id and self.vehicle_id.performance_id:
        perf = self.vehicle_id.performance_id
        self.diesel_estimated = perf.cost_per_km * self.distance_km
```

### Bloqueo por mantenimiento (V2.5):
```python
# Si vehicle_status == 'blocked' → UserError
# Si vehicle_status == 'warning' → advertencia visual, no bloqueo
```

---

## 9. ROADMAP DEFINITIVO COMPLETO

### Progreso actual
- ✅ V1.0 — Base Funcional (COMPLETO)
- ✅ V2.0 — Estabilización (COMPLETO — 9/9 etapas)
- ✅ V2.1.1–2.1.4f — Pulido UX (COMPLETO — último: 2026-03-13)

---

### FASE 1 — TMS Completo + SaaS (Mar–Ago 2026)

| Versión | Nombre | Estado | Herramienta | Módulo |
|---|---|---|---|---|
| **V2.1.5** | Onboarding wizard 6 pasos | 📋 **SIGUIENTE** | Claude Code CLI + Orq. | tms/ |
| V2.1.6 | PDF pre-cotización + email | 📋 | Antigravity `Low` | tms/ |
| **V2.2 ⭐** | Carta Porte 3.1 + Timbrado | 📋 Prioridad máxima | Claude Code CLI + Orq. | tms/ |
| V2.3 | Facturación real | 📋 | Claude Code CLI + Orq. | tms/ |
| V2.4 🆕 | Combustible y rendimiento | 📋 | Antigravity `Low` | tms_fuel/ |
| V2.4b 🆕 | Evidencia fotográfica | 📋 | Antigravity `Low` | tms/ |
| V2.4c 🆕 | Firma digital simple | 📋 | Claude Code CLI + Orq. | tms_signature/ |
| V2.4d 🆕 | Liquidación de choferes | 📋 | Antigravity `Low` | tms_settlement/ |
| V2.5 🆕 | Mantenimiento de unidades | 📋 | Antigravity `Low` | tms_maintenance/ |
| V2.6 | KPIs, reportes y portal web | 📋 | Antigravity `Low` | tms/ |
| V2.7 | Limpieza "Modo Hombre Camión" | 📋 | Antigravity `Flash` | tms/ |
| **V2.8 🎯** | SaaS multi-tenant + cobro | 📋 | Claude Code CLI + Orq. | tms_saas/ |

#### Detalle etapas Fase 1

**V2.1.5 — Onboarding Wizard 6 pasos**
- Paso 1: Empresa + CSD (.cer + .key + contraseña) + Logo
- Paso 2: Vehículo principal + remolque + dolly + config SCT
- Paso 3: Seguros RC + Carga + Ambiental (aseguradora SAT + póliza + vigencia)
- Paso 4: Chofer + licencia federal + tipo + vigencia
- Paso 5: Primer cliente + buscar RFC en SAT (autocompleta nombre)
- Paso 6: Resumen + botón "Crear mi primer viaje"

**V2.2 — Carta Porte 3.1 + Timbrado Formas Digitales**
- Radio button ambiente pruebas `dev33.facturacfdi.mx` / producción `v33.facturacfdi.mx`
- Timbrado CFDI 4.0 + Complemento Carta Porte 3.1
- Cancelación método 1 (con .cer + .key)
- Campos nuevos `res.company`: `fd_usuario`, `fd_password`, `fd_user_id`, `csd_cer`, `csd_key`, `csd_password`, `rfc_emisor`, `regimen_fiscal`
- ⚠️ SEMILLA: crear modelo vacío `tms.route.analytics` aquí

**V2.3 — Facturación Real**
- CFDI de ingreso vinculado al waybill via `account.move`
- ⚠️ SEMILLA: activar hook `waybill.closed → _update_from_waybill()`

**V2.4 🆕 — Combustible y Rendimiento** (`tms_fuel/`)
- `tms.fuel.log`: vehicle_id, driver_id, waybill_id, date, station_name, liters, price_per_liter, total_cost, odometer_start, odometer_after, fuel_type, ticket_image (Binary), is_full_tank, km_since_last_load (computed), performance_km_liter (computed), performance_vs_expected (computed), performance_alert (Boolean — alerta si <-15%)
- `tms.vehicle.performance`: expected_km_liter, actual_avg_km_liter, cost_per_km, last_30_avg_km_liter, trend (improving/stable/declining)
- Alimenta el wizard de cotización con costo real de diesel por km

**V2.4b 🆕 — Evidencia Fotográfica** (`tms/models/tms_evidence.py`)
- `tms.evidence.photo`: waybill_id, photo_type (14 tipos), image (Binary/ir.attachment), captured_at (INMUTABLE), latitude, longitude, gps_accuracy_meters, device_info, extracted_value, fuel_log_id
- 14 tipos: odometer_start, odometer_fuel, odometer_end, fuel_ticket, fuel_pump, cargo_pickup, cargo_delivery, cargo_seal, unit_departure, unit_arrival, incident, maintenance, delivery_receipt, other
- Campos nuevos en `tms.waybill`: odometer_start/end + foto verificada + real_distance_km (alerta si >20% vs TollGuru)
- En V2.4b: carga manual desde navegador. En Fase 2 (Flutter): cámara + GPS automático

**V2.4c 🆕 — Firma Digital Simple** (`tms_signature/`)
- `tms.digital.signature`: waybill_id, document_type (6 tipos), signer_type, signer_name, signer_id_number, signature_image (canvas), signed_at (INMUTABLE), latitude, longitude, device_info, document_hash (SHA-256), signature_hash, sms_code_sent, sms_verified, verification_token, verification_url
- 6 tipos de documento: advance_receipt, departure_checklist, cargo_pickup, cargo_delivery, settlement, incident_report
- PDF con firma incrustada. QR verificable: `nextpack.mx/verify/{token}`
- Flujo: operador genera → SMS al chofer → chofer firma en browser móvil → PDF sellado

**V2.4d 🆕 — Liquidación de Choferes** (`tms_settlement/`)
- `tms.driver.settlement`: waybill_id, driver_id, waybill_amount (related), driver_percent (default 25%), driver_base_pay (computed), expense_ids, advance_ids, total_reimbursable (computed), total_advances (computed), company_expenses, other_deductions, net_amount (computed), previous_balance (saldo arrastrado), final_balance (computed), balance_type (pay/zero/debit), state (draft/review/approved/paid), payment_method, signature_id
- `tms.driver.expense`: settlement_id, expense_type (8 tipos), amount, receipt_image, is_reimbursable, fuel_log_id (vincula con tms_fuel sin duplicar)
- `tms.driver.advance`: settlement_id, driver_id, amount, state (pending/applied)
- Fórmula: `net = (waybill_amount × % chofer + reembolsos) - (anticipos + gastos empresa) - saldo_anterior`
- Comprobante PDF QWeb con firma digital incrustada

**V2.5 🆕 — Mantenimiento de Unidades** (`tms_maintenance/`)
- `tms.maintenance.plan`: vehicle_id, service_type (10 tipos: oil_change, filters, tires, brakes, battery, sct_verify, tenencia, insurance, circulacion, other), trigger_type (km/date/both), interval_km, interval_days, last_service_*, next_service_* (computed), km_remaining (computed), status (ok🟢/warning🟡/overdue🔴)
- `tms.maintenance.order`: vehicle_id, failure_type (9 tipos), description, photos, odometer_at_failure, state (reported/diagnosed/in_repair/done/cancelled), blocks_vehicle (Boolean), repair_cost, parts_cost, downtime_days (computed)
- Campo computed en `fleet.vehicle`: `vehicle_status` (available🟢/warning🟡/maintenance🔴/blocked⛔)
- ⚠️ SEMILLAS Fase 2 aquí: `fleet.vehicle.current_zip` + `res.partner.is_tms_carrier`

**V2.6 — KPIs, Reportes y Portal Web**
- Dashboard ingresos por período, viajes por estado
- Rentabilidad por vehículo (integra tms_fuel + tms_settlement)
- Rendimiento diesel por unidad
- Portal cliente: ver estado de su envío
- Botón aprobación portal → estado waybill

**V2.7 — Limpieza "Modo Hombre Camión"**
- 0 warnings en logs, 0 métodos huérfanos
- Menú simplificado, tooltips en lenguaje transportista
- QA: usuario nuevo < 10 min primera Carta Porte
- Verificar todas las semillas Fase 2 funcionando

**V2.8 🎯 — SaaS Multi-tenant + Cobro**
- `tms.subscription`: planes free ($0) / pro ($990 MXN) / flota ($2,990 MXN)
- Límites: free → 1 camión, 10 viajes/mes, sin marketplace; pro → 5 camiones, ilimitado, marketplace; flota → 20 camiones, API
- MercadoPago webhook: `POST /tms/webhook/mercadopago`
- **HITO: PRIMER CLIENTE PAGA AQUÍ** 🎯

---

### FASE 2 — Marketplace de Cargas (Sep–Dic 2026)

> Principio legal: NextPack es un tablero de avisos inteligente. Contratos directamente entre embarcador y transportista. NextPack jamás toca el dinero del flete.

| Etapa | Nombre | Herramienta | Módulo |
|---|---|---|---|
| M2.1 | Modelos base del marketplace | Claude Code CLI + Orq. | tms_marketplace/ |
| M2.2 | Matching engine + pricing engine | Antigravity `Low` | tms_marketplace/services/ |
| M2.3 | API REST pública | Claude Code CLI + Orq. | tms_api/ |
| M2.4 | App Flutter chofer (MVP) | Flutter developer | Flutter app |
| M2.5 | Portal web del embarcador | Antigravity `Low` | tms_marketplace/ |
| M2.6 | Notificaciones multicanal | Antigravity `Flash` | tms_marketplace/ |

#### Modelos Fase 2

**tms.load** (estados: draft→published→assigned→in_transit→completed→cancelled)
- shipper_id, company_id, origin_zip, dest_zip, pickup_date, vehicle_type_ids, cargo_weight, cargo_volume, price_offer, price_min (privado), bid_ids, assigned_waybill_id, matched_carrier_ids

**tms.market.bid** (estados: pending→accepted/rejected/expired)
- load_id, carrier_id, vehicle_id, driver_id, bid_price, expiry_date (24h auto), waybill_id
- Al aceptar: genera tms.waybill heredando datos load+bid, rechaza demás ofertas

**tms.carrier.profile**
- partner_id, verified_rfc, verified_sct (solo sistema), rating (computed), trips_completed, on_time_percent, current_zip (semilla V2.5), available

**tms.route.analytics** (SIN company_id — datos globales plataforma)
- origin_zip, dest_zip, trip_count, avg_price, avg_distance_km, avg_toll_cost, price_p25, price_p50, price_p75
- Se alimenta con hook waybill.closed desde V2.3

#### Matching Engine (MATCHING_ENGINE_DESIGN.md)
```
Score 0–100:
  35% compatibilidad vehículo
  30% historial en la ruta (tms.route.analytics)
  25% proximidad al origen (carrier_profile.current_zip)
  10% calificación del transportista

Métodos:
  get_carriers_for_load(load, limit=10)
  get_loads_for_carrier(carrier, limit=20)  → empty trip optimization

Ejecución: ir.cron — NUNCA en request directo
```

#### API REST Endpoints (tms_api/)
```
POST /tms/api/v1/auth/login
POST /tms/api/v1/waybills/quote          ← /cotizar
POST /tms/api/v1/waybills                ← /crear_viaje
GET  /tms/api/v1/waybills/{id}           ← /estatus_viaje
GET  /tms/api/v1/loads                   ← load board
POST /tms/api/v1/loads                   ← /publicar_carga
POST /tms/api/v1/loads/{id}/bid          ← /ofertar_carga
POST /tms/api/v1/driver/trips/{id}/location   ← GPS c/5min
POST /tms/api/v1/driver/trips/{id}/photos     ← fotos odómetro
POST /tms/api/v1/driver/trips/{id}/sign       ← firma digital
GET  /tms/api/v1/track/{token}                ← tracking público
GET  /tms/api/v1/verify/{token}               ← verificar firma QR
```

#### App Flutter MVP
- Stack: Flutter 3.x + Riverpod + Dio + Drift (SQLite offline) + Firebase FCM + Google Maps
- Pantallas: Mis Viajes → Detalle → GPS tracking → 📷 fotos odómetro/tickets → ✍️ firma receptor → gastos → load board → hacer oferta
- Offline: cola SQLite → sincroniza al recuperar señal (last-write-wins)

---

### FASE 3 — Datos, Confianza y Escala (2027)

| Etapa | Nombre | Herramienta |
|---|---|---|
| F3.1 | Verificaciones y badges RFC/SCT | Antigravity `Low` |
| F3.2 | Analytics de mercado (producto de datos) | Antigravity `Low` |
| F3.3 | Matching engine V2 con ML básico | Claude Code CLI (solo con 1,000+ viajes) |
| F3.4 | API para brokers y 3PLs | Extensión tms_api/ |

**Verificaciones (F3.1):** RFC $150 MXN · SCT $250 MXN · IMSS $150 MXN · Bundle $499/año
**Analytics (F3.2):** índice precios por corredor · demanda insatisfecha · tiempo asignación · exportación CSV/API
**ML V2 (F3.3):** scikit-learn + joblib · predice aceptación · optimiza rutas vacías · ajusta precios

---

## 10. SEMILLAS ENTRE FASES — CRÍTICO

| Cuándo | Qué sembrar | Para qué |
|---|---|---|
| **V2.2** | Modelo `tms.route.analytics` vacío (_name, _description) | Los primeros viajes acumulan datos desde el día 1 |
| **V2.3** | Hook `waybill.closed → _update_from_waybill()` | Alimenta matching engine con datos reales |
| **V2.5** | `fleet.vehicle.current_zip` (Many2one tms.sat.codigo.postal) | Matching engine: score de proximidad |
| **V2.5** | `res.partner.is_tms_carrier` (Boolean) | Marketplace: filtrar transportistas |
| **V2.5** | `fleet.vehicle.vehicle_status` bloquea wizard y marketplace | Sin asignar vehículos con falla |
| **V2.7** | Verificar TODAS las semillas funcionan | Base lista para Fase 2 sin migraciones |

---

## 11. MODELO DE INGRESOS

| Fuente | Cuándo | Precio |
|---|---|---|
| Plan Gratis | V2.8 | $0/mes — anzuelo |
| Plan Pro | V2.8 | $990 MXN/mes |
| Plan Flota | V2.8 | $2,990 MXN/mes |
| Publicar cargas (embarcador) | M2.1 | $X por carga |
| Badge RFC verificado | F3.1 | $150 MXN |
| Badge SCT verificado | F3.1 | $250 MXN |
| Bundle verificación anual | F3.1 | $499 MXN/año |
| Plan datos embarcador | F3.2 | $X/mes extra |
| API brokers/3PLs | F3.4 | Plan Flota+ |
| ❌ Factoraje | DESCARTADO | Requiere SOFOM |
| ❌ Seguros intermediados | DESCARTADO | Requiere CNSF |
| ❌ Tarjeta combustible | DESCARTADO | Complejidad alta |

---

## 12. TIMELINE

```
2026
Mar   V2.1.5 Onboarding wizard
      ↳ Paralelo: Claude Web genera SDD V2.2

Abr   V2.2 Carta Porte + Timbrado ⭐ HITO CRÍTICO
      ↳ Paralelo: SDD V2.3

May   V2.3 Facturación real
      V2.4 Combustible + Rendimiento

Jun   V2.4b Evidencia fotográfica
      V2.4c Firma digital
      V2.4d Liquidación choferes

Jul   V2.5 Mantenimiento unidades
      V2.6 KPIs y reportes

Ago   V2.7 Limpieza
      V2.8 SaaS + MercadoPago
      🎯 PRIMER CLIENTE PAGA

Sep   M2.1 Modelos marketplace
      M2.2 Matching + Pricing engine
      ↳ Paralelo: inicia Flutter

Oct   M2.3 API REST
      M2.5 Portal embarcador

Nov   M2.4 Flutter MVP lanzamiento
      M2.6 Notificaciones + WhatsApp
      🎯 PRIMER EMBARCADOR PUBLICA CARGA

Dic   Estabilización Fase 2

2027
Ene   F3.1 Verificaciones
      F3.2 Analytics de mercado
Feb+  F3.3 ML · F3.4 API brokers
      🎯 500+ TRANSPORTISTAS ACTIVOS
```

---

## 13. REGLAS DE VELOCIDAD — DESARROLLO PARALELO

```
CARRIL 1 — Código (tú + Antigravity/Claude Code)
  Siempre hay una etapa activa en desarrollo

CARRIL 2 — Documentación (Claude Web)
  Mientras desarrollas V2.X, Claude Web ya tiene listo el SDD de V2.X+1
  NUNCA esperas el SDD — siempre está listo antes de necesitarlo

CARRIL 3 — QA (Claude Code en modo Ask)
  Mientras Antigravity termina, Claude Code revisa la etapa anterior

REGLAS DIARIAS:
  ✅ Nunca arranca etapa sin SDD completo en docs/etapa-X.X.X.md
  ✅ Termina el día con python3 -m py_compile models/*.py → 0 errores
  ✅ Siempre commit antes de cerrar (aunque sea WIP)
  ✅ El SDD de la siguiente etapa ya pedido antes de terminar la actual
  ✅ Claude Code en modo Ask para QA mientras Antigravity implementa
```

---

## 14. HERRAMIENTAS POR TIPO DE TAREA

| Tarea | Herramienta | Modo | Tiempo típico |
|---|---|---|---|
| Generar SDD nuevo | Claude Web | — | 30 min |
| Fix quirúrgico 1–2 archivos | Antigravity | `Fast + Flash` | 1–2 hrs |
| Bug complejo, lógica Python | Antigravity | `Planning + Low` | 2–4 hrs |
| Etapa nueva completa | Claude Code CLI + Orq. | `Planning + High` | 1–2 días |
| Módulo nuevo completo | Claude Code CLI + Orq. | `Planning + High` | 3–5 días |
| QA, inspección, tests | Claude Code | `Ask` | 1–2 hrs |
| Revisión arquitectura | Claude Web | — | 1 hr |
| Ver roadmap visual | Claude Web | — | escribir "Muéstrame el roadmap" |

### Tabla de ejecución por versión

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

## 15. FLUJO DE EJECUCIÓN DE ETAPAS

### Con Orquestador (etapas complejas: 2.1.5, 2.2, 2.3, 2.4c, 2.8)
```
PASO 1 — Claude Web: "Genera el SDD de la etapa X.X.X"
         → guardar en docs/etapa-X.X.X.md

PASO 2 — Terminal:
         cd ~/odoo/proyectos/tms
         claude "Lee ORCHESTRATOR.md y docs/etapa-X.X.X.md
                 y ejecuta el flujo multi-agente completo"

PASO 3 — 4 agentes en paralelo (Git Worktrees):
         Agente A: models/ → rama feat/etapa-X.X.X-models
         Agente B: views/  → rama feat/etapa-X.X.X-views
         Agente C: tests/  → rama feat/etapa-X.X.X-tests
         Agente D: auditoría seguridad (sin rama)

PASO 4 — Revisar reporte Agente D → aprobar o corregir

PASO 5 — python3 odoo-bin -c odoo.conf -u tms -d tms_v2 --stop-after-init
          python3 odoo-bin -c odoo.conf

PASO 6 — PR a main (nunca push directo)
```

### Con Antigravity (etapas simples)
```
PASO 1 — Claude Web: "Genera el SDD de la etapa X.X.X"
         → copiar SDD al prompt de Antigravity

PASO 2 — Antigravity implementa → NO commit hasta aprobación

PASO 3 — python3 odoo-bin -c odoo.conf -u tms -d tms_v2 --stop-after-init

PASO 4 — Verificar en navegador → flujo completo de la etapa

PASO 5 — git checkout -b feat/etapa-X.X.X-nombre
          git add . && git commit -m "feat(X.X.X): descripción"
          git push origin feat/etapa-X.X.X-nombre → PR en GitHub
```

---

## 16. REGLAS ABSOLUTAS — NUNCA ROMPER

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
13. NO hacer push a `main` — siempre rama + PR
14. Vistas: `<list>` (NO `<tree>`), `invisible=` (NO `attrs=`)
15. NUNCA tocar dinero entre partes — NextPack cobra por acceso, no por transacción

---

## 17. BUGS CONOCIDOS — NO REPETIR

| ID | Descripción | Estado |
|---|---|---|
| FIX-01 | widget monetary sin currency_field en wizard | ✅ Resuelto |
| FIX-02 | is_dangerous no definido en wizard.line | ✅ Resuelto |
| FIX-03 | Direcciones origen/destino no llegaban al waybill | ✅ Resuelto 2026-03-13 |
| FIX-04 | Retención 4% no considera is_company | ✅ Resuelto |

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

---

## 18. COMANDOS CLAVE

```bash
# Update módulo + reinicio
python3 odoo-bin -c odoo.conf -u tms -d tms_v2 --stop-after-init
python3 odoo-bin -c odoo.conf

# Update módulo específico nuevo
python3 odoo-bin -c odoo.conf -u tms_fuel -d tms_v2 --stop-after-init

# Validar Python antes de commit
python3 -m py_compile models/archivo.py

# Buscar duplicados
grep -rn "def nombre_metodo" models/
grep -rn "record id=" views/

# Activar orquestador
claude "Lee ORCHESTRATOR.md y docs/etapa-X.X.X.md y ejecuta el flujo multi-agente"

# Ver logs de errores
grep -n "WARNING\|ERROR" odoo.log | tail -20

# Git — flujo correcto
git checkout main && git pull origin main
git checkout -b feat/etapa-X.X.X-nombre
git add .
git commit -m "feat(X.X.X): descripción en español"
git push origin feat/etapa-X.X.X-nombre
# → PR en GitHub → merge vía PR — NUNCA push directo a main
```

---

## 19. CONVENCIÓN DE COMMITS

```
feat(X.X.X): descripción    ← nueva funcionalidad
fix(X.X.X): descripción     ← corrección de bug
chore: descripción           ← mantenimiento
```

---

## 20. FORMATO SDD OBLIGATORIO

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

## 21. RIESGOS Y MITIGACIONES

| Riesgo | Nivel | Mitigación |
|---|---|---|
| SAT actualiza Carta Porte | Alto | Suscribirse a avisos SAT; timbrado modular |
| Adopción lenta | Medio | Plan gratis + onboarding <14 min + WhatsApp |
| Flutter sin señal en carretera | Alto | SQLite offline + cola sincronización |
| Escalabilidad miles de tenants | Alto | Arquitectura híbrida desde V2.8 |
| Fraude marketplace | Medio | Verificación RFC + revisión manual primeros 100 |
| Competidor copia modelo | Medio | Datos históricos de ruta = moat no copiable |

---

## 22. CONFIGURACIÓN DEL ENTORNO

```
Base de datos activa:  tms_v2
Puerto Odoo:           localhost:8019
Python:                odoo-19.0/.venv/bin/python odoo-19.0/odoo-bin
Config:                proyectos/tms/odoo.conf
Addons path:           /proyectos/theme (MUK) + /proyectos/tms
PostgreSQL:            usuario odoo, sin contraseña
PAC pruebas:           dev33.facturacfdi.mx
PAC producción:        v33.facturacfdi.mx
```

---

*Archivo único — fuente de verdad del proyecto*
*Actualizado: 2026-03-14 — Incorpora roadmap definitivo Fase 1/2/3*
*Para roadmap visual interactivo: escribir "Muéstrame el roadmap" en Claude Web*
*Próxima acción: generar SDD etapa 2.1.5 y lanzar orquestador*
