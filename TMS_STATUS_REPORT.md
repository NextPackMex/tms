# TMS STATUS REPORT — Análisis Completo de Código Fuente
**Fecha:** 2026-02-18
**Módulo:** TMS & Carta Porte 3.1 (SaaS Multi-Empresa)
**Versión Odoo:** 19 CE | Versión módulo: 19.0.1.0.0
**Archivos analizados:** 52 archivos .py y .xml

---

## 1. MODELOS EXISTENTES

### 1.1 Modelo Maestro — `tms.waybill`
**Archivo:** `models/tms_waybill.py` (líneas 1–1931)
**Herencia:** `mail.thread`, `mail.activity.mixin`, `portal.mixin`
**Orden:** `date_created desc, id desc`

| Campo | Tipo | Notas |
|-------|------|-------|
| `company_id` | Many2one res.company | required=True, index ✅ |
| `name` | Char | Folio VJ/0001, readonly |
| `state` | Selection | 9 estados (ver §3 Workflow) |
| `date_created` | Date | required |
| `cp_type` | Selection ingreso/traslado | **DUPLICA `waybill_type`** ⚠️ |
| `waybill_type` | Selection income/transfer | **DUPLICA `cp_type`** ⚠️ |
| `partner_invoice_id` | Many2one res.partner | Cliente facturación |
| `partner_origin_id` | Many2one res.partner | Remitente |
| `partner_dest_id` | Many2one res.partner | Destinatario |
| `origin_zip`, `dest_zip` | Char | CPs Origen/Destino |
| `origin_address`, `dest_address` | Char | Direcciones manuales |
| `origin_city_id`, `dest_city_id` | Many2one tms.sat.municipio | Municipios SAT |
| `route_id` | Many2one tms.destination | Ruta frecuente |
| `route_name` | Char | compute, store=True |
| `distance_km`, `extra_distance_km` | Float | Distancia base + extras |
| `duration_hours` | Float | Duración estimada |
| `vehicle_id` | Many2one fleet.vehicle | **Domain incorrecto** 🔴 |
| `driver_id` | Many2one hr.employee | Chofer |
| `trailer1_id`, `trailer2_id` | Many2one fleet.vehicle | Remolques |
| `require_trailer` | Boolean | Obliga remolque |
| `total_axles` | Integer | compute, store=True |
| `fuel_price_liter` | Float | Precio diesel |
| `fuel_performance` | Float | Km/L |
| `cost_tolls` | Float | Casetas |
| `cost_driver`, `cost_maneuver`, `cost_other`, `cost_commission` | Float | Costos variables |
| `cost_diesel_total` | Float | compute, store=True |
| `cost_total_estimated` | Monetary | compute, store=True |
| `price_per_km` | Float | Propuesta KM |
| `profit_margin_percent` | Float | Margen % |
| `proposal_km_total` | Monetary | compute, **store=False** |
| `proposal_trip_total` | Monetary | compute, **store=False** |
| `proposal_direct_amount` | Monetary | Precio directo manual |
| `selected_proposal` | Selection km/trip/direct | Default 'direct' |
| `amount_untaxed` | Monetary | store=True **⚠️ escrito desde compute store=False** |
| `amount_tax` | Monetary | compute, store=True |
| `amount_retention` | Monetary | compute, store=True |
| `amount_total` | Monetary | compute, store=True |
| `line_ids` | One2many tms.waybill.line | Mercancías |
| `l10n_mx_edi_customs_regime_ids` | One2many tms.waybill.customs.regime | Regímenes |
| `tms_id_ccp` | Char | UUID Carta Porte 3.1 |
| `tms_gross_vehicle_weight` | Float | compute, store=True |
| `l10n_mx_edi_is_international` | Boolean | Transporte internacional |
| `l10n_mx_edi_logistica_inversa` | Boolean | Logística inversa |
| `signature` | Image | Firma portal |
| `signed_by`, `signed_on`, `signed_ip` | Char/Datetime/Char | Datos de firma |
| `signed_latitude`, `signed_longitude` | Float | Geolocalización firma |
| `rejection_reason` | Text | Rechazo portal |
| `tracking_event_ids` | One2many tms.tracking.event | Bitácora GPS |
| `date_arrived_origin`, `date_started_route`, `date_arrived_dest` | Datetime | Bitácora tiempos |
| `lat_*`, `long_*`, `last_app_lat`, `last_app_long` | Float | GPS |
| `last_report_date` | Datetime | Última pos. app |

**Métodos de negocio en `tms.waybill`:**

| Método | Línea | Estado |
|--------|-------|--------|
| `create()` | 1896 | ✅ Genera folio VJ/ |
| `action_confirm()` | 1559 | ✅ draft→en_pedido |
| `action_set_en_pedido()` | 1552 | ✅ alias de action_confirm |
| `action_assign()` | 1055 | ✅ →assigned |
| `action_approve_cp()` | 1574 | 🔴 Escribe estado inválido `'carta_porte'` |
| `action_start_route_manual()` | 1680 | 🔴 Escribe estado inválido `'transit'` |
| `action_arrived_dest_manual()` | 1705 | 🔴 Escribe estado inválido `'destination'` |
| `action_create_invoice()` | 1727 | ✅ →closed |
| `action_cancel()` | 1797 | ✅ →cancel |
| `action_send_email()` | 1271 | 🔴 DUPLICADO (×3) |
| `action_send_email()` | 1907 | 🔴 DUPLICADO (activo, sin validación) |
| `action_driver_report()` | 1807 | 🔴 Escribe estados inválidos `'transit'`/`'destination'` |
| `action_compute_route_smart()` | 734 | ✅ Caché + APIs externas |
| `action_preview_waybill()` | 1043 | ✅ Portal URL |
| `action_generate_id_ccp()` | 178 | ✅ UUID v4 |
| `action_clear_facturacion/origen/destino()` | 202-216 | ✅ Limpieza |
| `_action_sign()` | 1744 | ✅ Firma portal |
| `_check_waybill_constraints()` | 413 | 🔴 DUPLICADO (ignorado) |
| `_check_waybill_constraints()` | 1300 | 🔴 DUPLICADO (activo, incompleto) |
| `_check_waybill_validity()` | 421 | 🔴 DUPLICADO (ignorado) |
| `_check_waybill_validity()` | 1307 | 🔴 DUPLICADO (activo, sin validar traslados) |
| `_check_fiscal_rfc()` | 401 | ✅ Valida RFC partners |
| `_check_financials()` | 473 | ⚠️ Redundante con validity |
| `_check_id_ccp_format()` | 186 | ✅ Valida UUID |
| `_onchange_route_id()` | 483 | 🔴 DUPLICADO (ignorado) |
| `_onchange_route_id()` | 1496 | 🔴 DUPLICADO (activo, **campos fantasma**) |
| `_onchange_vehicle_id()` | 524 | ✅ |
| `_onchange_require_trailer()` | 551 | ✅ |
| `_onchange_partner_origin()` | 1408 | ✅ |
| `_onchange_partner_dest()` | 1452 | ✅ |
| `_compute_gross_weight()` | 160 | ✅ |
| `_compute_total_axles()` | 588 | ✅ |
| `_compute_amount_all()` | 1169 | ✅ IVA 16%, Ret 4% |
| `_compute_cost_diesel_total()` | 1188 | ✅ store=True |
| `_compute_cost_total_estimated()` | 1212 | ✅ store=True |
| `_compute_proposal_values()` | 1230 | ⚠️ store=False escribe en `amount_untaxed` store=True |
| `_compute_route_name()` | 498 | ✅ |
| `_compute_partner_addresses()` | 1369 | ✅ |
| `_compute_is_fuel_price_outdated()` | 1088 | ✅ |
| `_compute_access_url()` | 1351 | ✅ /my/waybills/<id> |
| `_expand_states()` | 1526 | ✅ Kanban group_expand |
| `_get_default_fuel_price()` | 1073 | ✅ Último precio diesel |
| `_get_report_base_filename()` | 1039 | ✅ |
| `_fetch_google_routes_api()` | 788 | ✅ Google Routes API |
| `_fetch_tollguru_api()` | 877 | ✅ TollGuru API |
| `_notify_success()` | 975 | ✅ Rainbow man |

---

### 1.2 Modelo — `tms.waybill.line`
**Archivo:** `models/tms_waybill.py` (líneas 1938–2085)
**Orden:** `sequence, id`

| Campo | Tipo | Notas |
|-------|------|-------|
| `waybill_id` | Many2one tms.waybill | required, ondelete=cascade |
| `sequence` | Integer | Default 10 |
| `product_sat_id` | Many2one tms.sat.clave.prod | Clave SAT |
| `description` | Char | required |
| `quantity` | Float | Default 1.0 |
| `uom_sat_id` | Many2one tms.sat.clave.unidad | |
| `weight_kg` | Float | |
| `dimensions` | Char | |
| `is_dangerous` | Boolean | |
| `l10n_mx_edi_tax_object` | Selection | CFDI 4.0 |
| `l10n_mx_edi_sector_cofepris` | Selection | 9 valores |
| `l10n_mx_edi_active_ingredient` | Char | COFEPRIS |
| `l10n_mx_edi_nominal_purity` | Float | COFEPRIS |
| `l10n_mx_edi_unit_purity` | Char | COFEPRIS |
| ~~`material_peligroso_id`~~ | **NO EXISTE** | 🔴 Referenciado en `action_approve_cp` L1650 |
| ~~`embalaje_id`~~ | **NO EXISTE** | 🔴 Referenciado en `action_approve_cp` L1652 |

**Métodos:** `action_send_email()` (línea 2062) — **SIN SENTIDO en este modelo** 🔴

---

### 1.3 Modelo — `tms.waybill.customs.regime`
**Archivo:** `models/tms_waybill.py` (líneas 2087–2104)

| Campo | Tipo | Notas |
|-------|------|-------|
| `waybill_id` | Many2one tms.waybill | ondelete=cascade |
| `regimen_aduanero` | Selection | 10 regímenes (IMD, EXD, ITR, ITE, ETR, ETE, DFE, TRA, EFE, RFE) |

> 🔴 **Sin ACL en `ir.model.access.csv`** — AccessError en runtime.

---

### 1.4 Modelo — `tms.destination`
**Archivo:** `models/tms_destination.py` (106 líneas)
**Estado:** ✅ Bien implementado

| Campo | Tipo | Notas |
|-------|------|-------|
| `company_id` | Many2one res.company | required, index |
| `currency_id` | Many2one res.currency | related |
| `origin_zip`, `dest_zip` | Char | required, index |
| `vehicle_type_id` | Many2one tms.vehicle.type | |
| `name` | Char | compute (`origin_zip → dest_zip (tipo)`) |
| `active` | Boolean | Default True |
| `distance_km`, `duration_hours` | Float | |
| `cost_tolls` | Float | (**correcto**: `cost_tolls`, no `toll_cost`) |
| `last_update` | Date | |
| `notes` | Text | |

**Constraint única:** `UNIQUE(company_id, origin_zip, dest_zip, vehicle_type_id)` ✅

---

### 1.5 Extensión — `fleet.vehicle` (TMS)
**Archivo:** `models/tms_fleet_vehicle.py` (415 líneas)

| Campo TMS agregado | Tipo | Notas |
|---------------------|------|-------|
| `company_id` | Many2one res.company | 🔴 **DUPLICADO** (L40 y L56) |
| `tms_vehicle_type_id` | Many2one tms.vehicle.type | required |
| `tms_is_trailer` | Boolean | compute store=True, readonly=False |
| `is_trailer` | Boolean | compute store=True ("Es Tractocamión") |
| `no_economico` | Char | No. económico |
| `sat_config_id` | Many2one tms.sat.config.autotransporte | |
| `num_axles` | Integer | related, store=True |
| `sat_permiso_sct_id` | Many2one tms.sat.tipo.permiso | |
| `permiso_sct_number` | Char | |
| `tms_insurance_civil_liability` | Char | default desde res.company |
| `tms_insurance_civil_liability_mx` | Char | |
| `tms_insurance_environmental` | Char | |
| `tms_insurance_environmental_mx` | Char | |
| `tms_insurance_cargo` | Char | |
| `tms_insurance_cargo_mx` | Char | |
| `tms_gross_vehicle_weight` | Float | Peso bruto en ton |
| `trailer1_id`, `trailer2_id` | Many2one fleet.vehicle | |
| `performance_km_l` | Float | Rendimiento Km/L |
| `display_name` | Char | compute, store=True |

**Métodos:** `validate_carta_porte_compliance()` ✅, `action_view_services()` ✅, `_compute_vehicle_type_props()` ✅, `_compute_display_name()` ✅

---

### 1.6 Extensión — `hr.employee` (Chofer)
**Archivo:** `models/hr_employee.py` (135 líneas)
**Estado:** ✅ Bien implementado

| Campo TMS | Tipo | Notas |
|-----------|------|-------|
| `tms_is_driver` | Boolean | Marca como chofer |
| `tms_driver_license` | Char | No. de licencia federal |
| `tms_driver_license_type` | Selection | A/B/C/D/E/F |
| `tms_driver_license_expiration` | Date | Vigencia |
| `l10n_mx_edi_fiscal_regime` | Selection | 20 regímenes |
| `tms_driver_rfc` | Char | related `work_contact_id.vat` |
| `tms_driver_address` | Char | compute desde work_contact_id |

**Métodos:** `validate_carta_porte_compliance()` ✅

---

### 1.7 Extensión — `res.partner` (SAT)
**Archivo:** `models/res_partner_tms.py` (161 líneas)

| Campo | Tipo | Notas |
|-------|------|-------|
| `company_id` | Many2one res.company | **required=True** 🔴 |
| `tms_cp_id` | Many2one tms.sat.codigo.postal | |
| `tms_sat_state_code` | Char | compute, store=True |
| `l10n_mx_edi_colonia_sat_id` | Many2one tms.sat.colonia | |
| `l10n_mx_edi_municipio_sat_id` | Many2one tms.sat.municipio | |
| `l10n_mx_edi_localidad_sat_id` | Many2one tms.sat.localidad | |
| `l10n_mx_edi_fiscal_regime` | Selection | 20 regímenes |
| `l10n_mx_edi_usage` | Selection | 15 usos CFDI, default 'S01' |

**Métodos:** `action_tms_normalize_name_40()` ✅, `_compute_tms_sat_state_code()` ✅, `_on_cp_change()` ✅, `_on_geo_change()` ✅

---

### 1.8 Extensión — `res.company` (TMS)
**Archivo:** `models/res_company.py` (53 líneas)
**Estado:** ✅ Bien implementado

Agrega campos default para seguros de vehículos (civil, ambiental, carga × 2) y `tms_def_l10n_mx_edi_tax_object`.

---

### 1.9 Extensión — `res.config.settings`
**Archivo:** `models/res_config_settings.py` (29 líneas)
**Estado:** ✅ Bien implementado

Campos: `tms_use_google_maps`, `tms_google_maps_api_key`, `tms_tollguru_api_key`, `tms_route_provider`, seguros default relacionados a `res.company`.

---

### 1.10 Modelo — `tms.vehicle.type`
**Archivo:** `models/tms_vehicle_type.py` (14 líneas)
**Estado:** ✅ Bien implementado

Campos: `name`, `sequence`, `is_trailer`, `is_motorized`.
**Datos iniciales en `data/tms_data.xml`:** Tractocamión, Remolque/Caja, Camioneta, Dolly.

---

### 1.11 Modelo — `tms.fuel.history`
**Archivo:** `models/tms_fuel_history.py` (28 líneas)
**Estado:** ✅ Bien implementado

Campos: `date`, `price`, `notes`, `company_id`. Usa `_check_company_auto = True`.

---

### 1.12 Modelo — `tms.tracking.event`
**Archivo:** `models/tms_tracking_event.py` (31 líneas)
**Estado:** ✅ Bien implementado

Campos: `waybill_id`, `name` (tipo: start/arrival_origin/arrival_dest/loading/unloading/problem/tracking/other), `date`, `latitude`, `longitude`, `location_description`, `notes`, `source` (manual/app).

---

### 1.13 Catálogos SAT (11 modelos globales)

Todos siguen el patrón correcto: sin `company_id`, `_order` definido, constraint `UNIQUE` en claves, `_rec_names_search` para búsqueda multi-campo. ✅

| Modelo | Archivo | Campos clave | Constraint |
|--------|---------|-------------|------------|
| `tms.sat.clave.prod` | sat_clave_prod.py | code, name, material_peligroso, palabras_clave | UNIQUE(code) |
| `tms.sat.clave.unidad` | sat_clave_unidad.py | code, name | UNIQUE(code) |
| `tms.sat.embalaje` | sat_embalaje.py | code, name | UNIQUE(code) |
| `tms.sat.material.peligroso` | sat_material_peligroso.py | code, name, clase | UNIQUE(code) |
| `tms.sat.codigo.postal` | sat_codigo_postal.py | code, estado, municipio, localidad | UNIQUE(code, estado, municipio) |
| `tms.sat.colonia` | sat_colonia.py | code, zip_code, name | UNIQUE(code, zip_code) |
| `tms.sat.localidad` | sat_localidad.py | code, estado, name | UNIQUE(code, estado) |
| `tms.sat.municipio` | sat_municipio.py | code, estado, name | UNIQUE(code, estado) |
| `tms.sat.config.autotransporte` | sat_config_autotransporte.py | code, name, total_axles, total_tires, remolque | UNIQUE(code) |
| `tms.sat.tipo.permiso` | sat_tipo_permiso.py | code, name, clave_transporte | UNIQUE(code) |
| `tms.sat.figura.transporte` | sat_figura_transporte.py | code, name | UNIQUE(code) |

---

### 1.14 Wizards

| Clase | Archivo | Descripción | Estado |
|-------|---------|-------------|--------|
| `SatImportWizard` | `wizard/sat_import_wizard.py` (456 líneas) | Importa 11 catálogos SAT desde .xlsx/.xls con upsert por clave | ✅ |
| `PartnerAssignCompanyWizard` | `wizard/partner_assign_company_wizard.py` | Asigna `company_id` masivamente a partners | ✅ |
| `TmsLoadDemoWizard` | `wizard/tms_load_demo_wizard.py` | Carga datos demo programáticamente | ✅ |

---

## 2. VISTAS EXISTENTES

| Archivo | Modelo | Tipos de vista | Observaciones |
|---------|--------|---------------|---------------|
| `views/tms_waybill_views.xml` | `tms.waybill` | Kanban, List, Form, Search | Kanban usa `waybill_type` ⚠️ |
| `views/tms_fleet_vehicle_views.xml` | `fleet.vehicle` | Form (tractor), Form (remolque), List×2 | Acciones con domain `tms_is_trailer` ✅ |
| `views/tms_destination_views.xml` | `tms.destination` | List, Form, Search | ✅ |
| `views/tms_vehicle_type_view.xml` | `tms.vehicle.type` | List, Form | ✅ |
| `views/tms_fuel_history_views.xml` | `tms.fuel.history` | List, Form | ✅ |
| `views/tms_dashboard_views.xml` | `tms.waybill` | Kanban (vía action_tms_home) | ✅ |
| `views/tms_portal_templates.xml` | Portal QWeb | Templates portal web | ✅ |
| `views/res_partner_tms_view.xml` | `res.partner` | Form (extensión) | ✅ |
| `views/res_partner_tms_modals_view.xml` | `res.partner` | Modales | ✅ |
| `views/hr_employee_views.xml` | `hr.employee` | Form (extensión) | ✅ |
| `views/res_config_settings_views.xml` | `res.config.settings` | Form (extensión) | ✅ |
| `views/tms_menus.xml` | Menús operativos | ir.ui.menu | ✅ |
| `views/sat_menus.xml` | Menús catálogos SAT | ir.ui.menu | ✅ |
| `views/sat_*_views.xml` (×11) | Catálogos SAT | List, Form | ✅ |
| `reports/tms_waybill_report.xml` | `tms.waybill` | QWeb PDF | ✅ |

**Estructura del reporte PDF** (`tms_waybill_report.xml`):
- Header: Título dinámico según estado (Cotización / Carta Porte)
- Bloque 1: Cliente Facturación | Origen | Destino
- Bloque 2: Ruta/Distancia | Vehículo/Chofer/Remolque
- Bloque 3: Tabla mercancías (`line_ids`)
- Bloque 4: Subtotal + IVA 16% + Retención 4% + Total
- Firma digital + nombre + fecha

---

## 3. WORKFLOW DE ESTADOS

### Estados definidos en `state` (Selection):

| Clave | Label | Transición correcta |
|-------|-------|---------------------|
| `draft` | Solicitud | Estado inicial |
| `en_pedido` | En Pedido | `action_confirm()` ✅ |
| `assigned` | Por Asignar | `action_assign()` ✅ |
| `waybill` | Carta Porte Lista | `action_approve_cp()` 🔴 escribe `'carta_porte'` |
| `in_transit` | En Trayecto | `action_start_route_manual()` 🔴 escribe `'transit'` |
| `arrived` | En Destino | `action_arrived_dest_manual()` 🔴 escribe `'destination'` |
| `closed` | Facturado / Cerrado | `action_create_invoice()` ✅ |
| `cancel` | Cancelado | `action_cancel()` ✅ |
| `rejected` | Rechazado | portal controller ✅ |

### Diagrama de flujo:
```
draft ──→ en_pedido ──→ assigned ──→ waybill ──→ in_transit ──→ arrived ──→ closed
 │           │                                                              │
 └→ cancel  └→ rejected (portal)                            cancel ←────────┘
```

---

## 4. ISSUES DETECTADOS

### 🔴 CRÍTICOS — Rompen el sistema en runtime

---

#### BUG-01 | `_check_waybill_constraints` DUPLICADO
**Archivo:** `models/tms_waybill.py`
**Líneas:** 413 y 1300

```python
# VERSIÓN 1 (L413) — IGNORADA por Python
@api.constrains('amount_total','line_ids','partner_invoice_id',
                'partner_origin_id','partner_dest_id','vehicle_id',
                'distance_km','duration_hours','cost_tolls','state')  # ← más campos
def _check_waybill_constraints(self):
    for record in self:
        if record.state == 'draft':
            continue
        record._check_waybill_validity()   # ← llama v1 (correcta)

# VERSIÓN 2 (L1300) — ACTIVA (Python usa la última)
@api.constrains('amount_total','line_ids','partner_invoice_id',
                'partner_origin_id','partner_dest_id','vehicle_id',
                'distance_km','duration_hours','cost_tolls')  # ← falta 'state'
def _check_waybill_constraints(self):
    for record in self:
        if record.state == 'draft':
            continue
        record._check_waybill_validity()   # ← llama v2 (incompleta)
```

**Impacto:** La v2 activa no tiene `'state'` en `@api.constrains`, por lo que cambios de estado no disparan la validación.

---

#### BUG-02 | `_check_waybill_validity` DUPLICADO
**Archivo:** `models/tms_waybill.py`
**Líneas:** 421 y 1307

```python
# VERSIÓN 1 (L421) — IGNORADA
def _check_waybill_validity(self):
    ...
    if self.waybill_type == 'income' and self.amount_total <= 0:  # ← distingue traslados
        raise ValidationError(...)
    ...
    if self.require_trailer and not self.trailer1_id:             # ← valida remolque
        raise ValidationError(...)

# VERSIÓN 2 (L1307) — ACTIVA
def _check_waybill_validity(self):
    ...
    if self.amount_total <= 0:                  # ← no distingue traslados
        raise ValidationError(...)
    # NO valida require_trailer
```

**Impacto:**
1. Traslados gratuitos (tipo `'traslado'`) son rechazados aunque sea válido
2. La validación de remolque obligatorio (`require_trailer`) no funciona

---

#### BUG-03 | `action_send_email` TRIPLICADO
**Archivo:** `models/tms_waybill.py`
**Líneas:** 1271 (TmsWaybill v1), 1907 (TmsWaybill v2), 2062 (TmsWaybillLine)

```python
# L1271 — IGNORADA (tiene validación previa)
def action_send_email(self):
    self._check_waybill_validity()  # ← valida antes de enviar ✅
    template = self.env.ref('tms.email_template_tms_waybill')
    ...

# L1907 — ACTIVA (sin validación, Python usa esta)
def action_send_email(self):
    # NO hay _check_waybill_validity()  ← envía sin validar 🔴
    template = self.env.ref('tms.email_template_tms_waybill')
    ...

# L2062 — En TmsWaybillLine (no tiene sentido aquí)
def action_send_email(self):
    # referencia waybill template desde una línea de mercancía 🔴
    template = self.env.ref('tms.email_template_tms_waybill')
    ...
```

**Impacto:** Se pueden enviar cotizaciones incompletas sin validación. `TmsWaybillLine` expone un método que no tiene sentido en el contexto de una línea de mercancía.

---

#### BUG-04 | `_onchange_route_id` DUPLICADO con campos fantasma
**Archivo:** `models/tms_waybill.py`
**Líneas:** 483 (v1, simple) y 1496 (v2, con campos inexistentes)

```python
# L483 — IGNORADA (simple, correcta)
@api.onchange('route_id')
def _onchange_route_id(self):
    if self.route_id:
        self.route_name = self.route_id.name         # ✅ existe
        self.distance_km = self.route_id.distance_km  # ✅ existe
        self.duration_hours = self.route_id.duration_hours  # ✅ existe
        self.cost_tolls = self.route_id.cost_tolls    # ✅ existe

# L1496 — ACTIVA (campos inexistentes → AttributeError en runtime)
@api.onchange('route_id')
def _onchange_route_id(self):
    if self.route_id:
        self.origin_state_id = self.route_id.state_origin_id  # 🔴 FANTASMA
        self.dest_state_id = self.route_id.state_dest_id      # 🔴 FANTASMA
        self.distance_km = self.route_id.distance_km or 0.0   # ✅
        self.duration_hours = self.route_id.duration_hours or 0.0  # ✅
        self.cost_tolls = self.route_id.toll_cost or 0.0      # 🔴 tms.destination no tiene toll_cost
        self.toll_cost = self.route_id.toll_cost or 0.0       # 🔴 tms.waybill no tiene toll_cost
```

**Campos inexistentes verificados:**
- `TmsWaybill.origin_state_id` → NO definido en el modelo
- `TmsWaybill.dest_state_id` → NO definido en el modelo
- `TmsWaybill.toll_cost` → NO definido en el modelo (el campo se llama `cost_tolls`)
- `TmsDestination.toll_cost` → NO definido en tms.destination (se llama `cost_tolls`)

**Impacto:** `AttributeError` en runtime al seleccionar cualquier ruta frecuente. La funcionalidad de autocompletado de ruta está completamente rota.

---

#### BUG-05 | 5 estados inválidos escritos en métodos de acción
**Archivo:** `models/tms_waybill.py`

El campo `state` acepta SOLO: `draft, en_pedido, assigned, waybill, in_transit, arrived, closed, cancel, rejected`

| Método | Línea | Valor escrito | Valor correcto |
|--------|-------|--------------|----------------|
| `action_approve_cp` | 1678 | `'carta_porte'` | `'waybill'` |
| `action_start_route_manual` | 1702 | `'transit'` | `'in_transit'` |
| `action_arrived_dest_manual` | 1724 | `'destination'` | `'arrived'` |
| `action_driver_report` | 1852 | `'transit'` | `'in_transit'` |
| `action_driver_report` | 1865 | `'destination'` | `'arrived'` |

**Impacto:** `ValueError: 'carta_porte' is not a valid value for field 'state'` (o similar) en runtime. Las acciones de aprobación de carta porte, inicio de ruta, llegada a destino y la API de app móvil están completamente rotas.

---

#### BUG-06 | `company_id` DUPLICADO en `tms_fleet_vehicle.py`
**Archivo:** `models/tms_fleet_vehicle.py`
**Líneas:** 40 y 56

```python
# L40 — IGNORADA
company_id = fields.Many2one(
    'res.company', string='Compañía', required=True,
    default=lambda self: self.env.company,
    help='Compañía propietaria del vehículo (CRÍTICO para multi-empresa)'
)

# L56 — ACTIVA (idéntica, redefinición innecesaria)
company_id = fields.Many2one(
    'res.company', string='Compañía', required=True,
    default=lambda self: self.env.company,
    help='Compañía propietaria del vehículo (aislamiento multi-empresa)'
)
```

**Impacto:** Warning de Odoo al cargar el módulo (`Field company_id already defined`). Funcionalidad idéntica en este caso, pero viola el principio DRY y puede generar comportamiento inesperado.

---

#### BUG-07 | Campos faltantes en `TmsWaybillLine` referenciados en `action_approve_cp`
**Archivo:** `models/tms_waybill.py`
**Líneas de referencia:** 1650 y 1652 (dentro de `action_approve_cp`)

```python
# L1649-1653 en action_approve_cp:
if line.is_dangerous:
    if not line.material_peligroso_id:  # 🔴 No existe en TmsWaybillLine
        errors.append(...)
    if not line.embalaje_id:            # 🔴 No existe en TmsWaybillLine
        errors.append(...)
```

Los campos que faltan definir en `TmsWaybillLine`:
- `material_peligroso_id` → Many2one `tms.sat.material.peligroso`
- `embalaje_id` → Many2one `tms.sat.embalaje`

**Impacto:** `AttributeError` en runtime al intentar generar una Carta Porte que contenga materiales peligrosos.

---

#### BUG-08 | Domain incorrecto en `vehicle_id`
**Archivo:** `models/tms_waybill.py`
**Línea:** 517

```python
vehicle_id = fields.Many2one(
    'fleet.vehicle',
    string='Vehículo (Tractor)',
    domain="[('is_trailer', '=', True), ('company_id', '=', company_id)]",  # 🔴
    ...
)
```

**Problema:** El dominio usa `is_trailer = True` para filtrar tractores. En la extensión TMS de `fleet.vehicle`, el campo `is_trailer` significa "Es Tractocamión" (motorizado que puede llevar remolque), pero el campo para identificar si un vehículo **es** remolque es `tms_is_trailer`.

Comparación con campos de remolque (correcto):
```python
trailer1_id = fields.Many2one(
    domain="[('tms_is_trailer', '=', True), ...]",  # ✅ usa tms_is_trailer
)
```

**Impacto:** El domain funciona accidentalmente gracias a que `_compute_vehicle_type_props` también llena `is_trailer=True` para tractocamiones. Sin embargo es semánticamente incorrecto, inconsistente con los campos de remolque, y podría fallar si la lógica de `is_trailer` cambia.

**Corrección:** Cambiar a `[('tms_is_trailer', '=', False), ('company_id', '=', company_id)]`

---

#### BUG-09 | `res.partner.company_id` required=True + Record Rule sin fallback
**Archivos:**
- `models/res_partner_tms.py` línea 14
- `security/tms_security.xml` línea 196

```python
# res_partner_tms.py:14
company_id = fields.Many2one(
    'res.company', required=True,  # 🔴 CRÍTICO
    ...
)
```

```xml
<!-- tms_security.xml:196 — Record Rule SIN fallback -->
<field name="domain_force">[('company_id', 'in', company_ids)]</field>
<!-- CORRECTO sería: ['|', ('company_id', '=', False), ('company_id', 'in', company_ids)] -->
```

**Impacto:**
1. Hace obligatorio `company_id` en TODOS los contactos de Odoo
2. Los contactos nativos sin empresa (admin, portal, seguidor de email, contactos de sistema) quedan invisibles o producen errores de validación
3. El módulo `mail` y `portal` pueden fallar porque usan partners sin company_id
4. Record Rules agravan el problema: sin el fallback `company_id = False`, ningún usuario puede ver contactos globales

---

#### BUG-10 | `tms.waybill.customs.regime` sin ACL
**Archivo:** `security/ir.model.access.csv`

El modelo `tms.waybill.customs.regime` está definido en Python (líneas 2087-2104) pero **no tiene ninguna entrada** en el CSV de permisos.

**Impacto:** `AccessError: You are not allowed to access 'tms.waybill.customs.regime'` al intentar leer o escribir regímenes aduaneros desde cualquier grupo (usuario, manager, driver, portal).

---

### 🟡 MEDIANOS — Degradan funcionalidad o generan warnings

---

#### WARN-01 | `cp_type` y `waybill_type` DUPLICADOS
**Archivo:** `models/tms_waybill.py` (líneas 225 y 231)

| Campo | Tipo Ingreso | Tipo Traslado | Usado en |
|-------|-------------|--------------|----------|
| `cp_type` | `'ingreso'` | `'traslado'` | Vista form |
| `waybill_type` | `'income'` | `'transfer'` | Kanban, `_check_waybill_validity` v1 |

Ambos son `required=True` con defaults. El Kanban consulta `waybill_type`. La validación activa (v2) no usa ninguno de los dos.

**Impacto:** Duplicación de datos en BD. El tipo de carta porte se guarda en dos campos distintos con claves distintas. Inconsistencia en la lógica de validación.

---

#### WARN-02 | `amount_untaxed` (store=True) escrito desde compute (store=False)
**Archivo:** `models/tms_waybill.py`

```python
# Campo con store=True:
amount_untaxed = fields.Monetary(store=True, ...)  # L707

# Método con store=False escribe en amount_untaxed:
@api.depends(...)
def _compute_proposal_values(self):  # store=False implícito
    ...
    record.amount_untaxed = record.proposal_km_total    # L1265 — NO se persiste
    record.amount_untaxed = record.proposal_trip_total  # L1267 — NO se persiste
    record.amount_untaxed = record.proposal_direct_amount  # L1269
```

**Problema técnico:** Odoo no permite que un método compute sin `store=True` escriba en un campo con `store=True`. Los valores se calculan en sesión pero al recargar el registro pueden perderse o mostrar valores desactualizados.

**Impacto:** El subtotal calculado por el motor de propuestas puede no guardarse correctamente en BD.

---

#### WARN-03 | `_check_financials` redundante
**Archivo:** `models/tms_waybill.py` (línea 473)

```python
@api.constrains('amount_total', 'state')
def _check_financials(self):
    for record in self:
        if record.state in ['draft', 'cancel', 'rejected']:
            continue
        if record.amount_total <= 0:
            raise ValidationError(...)
```

Esta validación ya está cubierta por `_check_waybill_validity()` (v2 activa, línea 1311). Doble validación innecesaria.

---

### 🟢 MENORES — Cosmético o deuda técnica

---

#### NOTE-01 | Archivos en disco no referenciados en manifest
**Archivos:**
- `static/src/js/portal_waybill_sign.js` — No en `web.assets_backend` ni `web.assets_frontend`
- `static/src/css/portal_waybill.css` — No en assets

**Observación:** Puede ser código legado o en desarrollo. Si se necesita la firma en portal, este JS puede ser el correcto y estar reemplazado por `tms_portal_signature_modal.js`.

---

#### NOTE-02 | Docstring incorrecto en `_action_sign`
**Archivo:** `models/tms_waybill.py` (línea 1752)

```python
# Docstring dice:
# "4. Cambia el estado a 'confirmed' (cotización aceptada)"
# Pero el código hace:
self.write({'state': 'en_pedido'})  # 'confirmed' no existe
```

Solo afecta documentación. El código funciona correctamente.

---

#### NOTE-03 | Dependencias potencialmente excesivas en manifest
**Archivo:** `__manifest__.py` (línea 67)

```python
'depends': ['base', 'fleet', 'account', 'contacts', 'board', 'mail',
            'portal', 'web', 'website', 'sale_management', 'hr', 'web_tour']
```

Dependencias cuestionables:
- `website`: módulo pesado (~100MB), ¿realmente necesario?
- `web_tour`: solo para tour de onboarding
- `sale_management`: según comentario del código, solo para "estética de portal"
- `board`: para el dashboard (podría reemplazarse con vista kanban nativa)

---

#### NOTE-04 | Comentario duplicado en tms_security.xml
**Archivo:** `security/tms_security.xml` (líneas 11-12)

```xml
<!-- Categoría del módulo TMS -->
<!-- Categoría del módulo TMS -->
```

Solo cosmético.

---

## 5. TABLA CONSOLIDADA DE ISSUES

| ID | Severidad | Descripción | Archivo | Línea(s) |
|----|-----------|-------------|---------|----------|
| BUG-01 | 🔴 Crítico | `_check_waybill_constraints` duplicado | tms_waybill.py | 413, 1300 |
| BUG-02 | 🔴 Crítico | `_check_waybill_validity` duplicado | tms_waybill.py | 421, 1307 |
| BUG-03 | 🔴 Crítico | `action_send_email` triplicado | tms_waybill.py | 1271, 1907, 2062 |
| BUG-04 | 🔴 Crítico | `_onchange_route_id` duplicado + campos fantasma | tms_waybill.py | 483, 1496-1518 |
| BUG-05 | 🔴 Crítico | 5 estados inválidos en acciones | tms_waybill.py | 1678, 1702, 1724, 1852, 1865 |
| BUG-06 | 🔴 Crítico | `company_id` duplicado en fleet_vehicle | tms_fleet_vehicle.py | 40, 56 |
| BUG-07 | 🔴 Crítico | `material_peligroso_id` y `embalaje_id` inexistentes | tms_waybill.py | 1650, 1652 |
| BUG-08 | 🔴 Crítico | `vehicle_id` domain incorrecto (`is_trailer` vs `tms_is_trailer`) | tms_waybill.py | 517 |
| BUG-09 | 🔴 Crítico | `res.partner company_id required=True` + Record Rule sin fallback | res_partner_tms.py + tms_security.xml | 14, 196 |
| BUG-10 | 🔴 Crítico | `tms.waybill.customs.regime` sin ACL | ir.model.access.csv | — |
| WARN-01 | 🟡 Medio | `cp_type` y `waybill_type` duplicados | tms_waybill.py | 225, 231 |
| WARN-02 | 🟡 Medio | `amount_untaxed` store=True escrito desde compute store=False | tms_waybill.py | 707, 1265-1269 |
| WARN-03 | 🟡 Medio | `_check_financials` redundante | tms_waybill.py | 473 |
| NOTE-01 | 🟢 Menor | JS/CSS en disco sin referenciar en manifest | __manifest__.py | — |
| NOTE-02 | 🟢 Menor | Docstring incorrecto en `_action_sign` | tms_waybill.py | 1752 |
| NOTE-03 | 🟢 Menor | Dependencias excesivas en manifest | __manifest__.py | 67 |
| NOTE-04 | 🟢 Menor | Comentario duplicado en security | tms_security.xml | 11-12 |

---

## 6. ARCHIVOS EN `__manifest__.py` vs DISCO

### ✅ Todos los archivos del manifest existen en disco

Verificado: data/, views/, wizard/, security/, reports/, static/src/js/, static/src/css/ — sin archivos faltantes.

### ⚠️ Archivos en disco NO referenciados en el manifest

| Archivo | Tipo | Estado |
|---------|------|--------|
| `static/src/js/portal_waybill_sign.js` | JavaScript | No cargado en el frontend |
| `static/src/css/portal_waybill.css` | CSS | No cargado en el frontend |

---

## 7. RESUMEN EJECUTIVO

### ✅ QUÉ FUNCIONA CORRECTAMENTE

1. **11 Catálogos SAT** — Arquitectura global correcta, wizard de importación robusto
2. **Motor de Cotización (3 propuestas)** — Fórmulas correctas (pendiente BUG fix de persistencia)
3. **Portal Web** — Controlador con validación multiempresa, firma y rechazo
4. **APIs de Rutas** — Google Routes API y TollGuru con caché en `tms.destination`
5. **Bitácora GPS** — `tms.tracking.event` correctamente implementado
6. **Estructura Multi-empresa** — Record Rules para waybill, destinos y vehículos
7. **Historial Diesel** — Limpio, usa `_check_company_auto`
8. **Wizard de importación SAT** — Upsert, soporte xlsx/xls, normalización de datos
9. **PDF de cotización** — Reporte QWeb completo con firma digital
10. **Secuencia de folios** — VJ/0001 correctamente configurada

### 🔴 QUÉ ESTÁ ROTO (Impide uso en producción)

| Funcionalidad | Bug | Síntoma |
|---------------|-----|---------|
| Generar Carta Porte | BUG-05 | `ValueError: 'carta_porte' is not a valid value` |
| Iniciar Ruta | BUG-05 | `ValueError: 'transit' is not a valid value` |
| Llegada a Destino | BUG-05 | `ValueError: 'destination' is not a valid value` |
| API App Móvil | BUG-05 | `ValueError` en estados transit/destination |
| Seleccionar Ruta Frecuente | BUG-04 | `AttributeError: origin_state_id` |
| CP con Mat. Peligrosos | BUG-07 | `AttributeError: material_peligroso_id` |
| Regímenes Aduaneros | BUG-10 | `AccessError` al acceder al modelo |
| Enviar Cotización por email | BUG-03 | Se envía sin validar el waybill |
| Contactos nativos Odoo | BUG-09 | Posible `ValidationError` o invisibilidad |

### 🗺️ MAPA DE PRIORIDADES DE CORRECCIÓN

```
Etapa 2.0.1 — Eliminar duplicados Python (30 min)
  ├── Eliminar _check_waybill_constraints L1300 (conservar L413)
  ├── Eliminar _check_waybill_validity L1307 (conservar L421)
  ├── Eliminar action_send_email L1907 y L2062 (conservar L1271)
  ├── Eliminar _onchange_route_id L1496-1518 (conservar L483)
  └── Eliminar company_id duplicado en tms_fleet_vehicle.py L56

Etapa 2.0.2 — Fix estados workflow (15 min)
  ├── action_approve_cp L1678: 'carta_porte' → 'waybill'
  ├── action_start_route_manual L1702: 'transit' → 'in_transit'
  ├── action_arrived_dest_manual L1724: 'destination' → 'arrived'
  ├── action_driver_report L1852: 'transit' → 'in_transit'
  └── action_driver_report L1865: 'destination' → 'arrived'

Etapa 2.0.3 — Agregar campos faltantes en TmsWaybillLine (10 min)
  ├── Agregar material_peligroso_id (Many2one tms.sat.material.peligroso)
  └── Agregar embalaje_id (Many2one tms.sat.embalaje)

Etapa 2.0.4 — Fix ACL y res.partner (10 min)
  ├── Agregar ACL para tms.waybill.customs.regime en ir.model.access.csv
  ├── Quitar required=True de res.partner.company_id
  └── Agregar fallback ('company_id','=',False) en Record Rule de res.partner

Etapa 2.0.5 — Fix vehicle_id domain y amount_untaxed (20 min)
  ├── vehicle_id domain: ('is_trailer','=',True) → ('tms_is_trailer','=',False)
  └── Resolver persistencia de amount_untaxed

Etapa 2.0.6 — Unificar cp_type/waybill_type (30 min)
  ├── Elegir cp_type como campo principal
  ├── Migrar referencias de waybill_type → cp_type en vistas y código
  └── Eliminar waybill_type
```

---

*Reporte generado por análisis estático de 52 archivos .py y .xml del módulo TMS.*
*Total de líneas analizadas: ~5,200 líneas Python + ~2,800 líneas XML*
