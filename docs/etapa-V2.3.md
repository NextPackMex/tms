# SDD — Etapa V2.3: CFDI Ingreso (Facturación Real)

**Módulo:** tms/ (Odoo 19 CE)  
**Versión base:** 19.0.2.2 (main)  
**Branch:** feat/v2.3-cfdi-ingreso  
**Fecha:** 2026-04-15  
**Prioridad:** ALTA — producto comercializable desde aquí  
**Herramienta:** Claude Code CLI + Orquestador (Planning + High)  

---

## GIT

```bash
git checkout main && git pull origin main
git checkout -b feat/v2.3-cfdi-ingreso
```

---

## 1. Problema

El waybill puede timbrar el CFDI Traslado (Carta Porte) para circular legalmente, pero no tiene facturación real. El método `action_create_invoice()` en `tms_waybill.py` L2344 es un stub que solo hace `write({'state': 'closed'})` sin crear ningún `account.move` ni CFDI. El transportista no puede cobrar legalmente sin un CFDI Ingreso.

---

## 2. Solución

Implementar el flujo completo de CFDI Ingreso extendiendo `account.move`, con un wizard que permita facturar uno o varios viajes en una sola factura (Apéndice 10 SAT), más el ciclo completo de cancelación con liberación automática de viajes.

### Principios de diseño

- Extender `account.move` con campos TMS — el contador trabaja en la interfaz nativa de Odoo Contabilidad
- Wizard con dos modos: **simple** (1 waybill) y **consolidado** (N waybills del mismo cliente)
- El SAT permite N ubicaciones y N mercancías en un solo Carta Porte 3.1 — Apéndice 10 del instructivo oficial
- Cancelación con los 3 motivos SAT aplicables (01, 02, 03) — motivo 01 fuerza timbrar sustituta primero
- Liberación automática de waybills al cancelar con motivo 02/03 — regresan a estado `arrived` para refacturar
- Botón "Volver a facturar" en facturas canceladas — abre wizard pre-llenado con los mismos viajes
- **NO usar l10n_mx_edi** — `xml_builder.py` construye el XML Ingreso íntegramente igual que el Traslado
- `pac_manager.py` ya es agnóstico al tipo — **no requiere cambios**

---

## 3. Wizard de Facturación — Flujo Detallado

### Paso 1 — Modo de facturación

El usuario elige entre dos opciones presentadas como tarjetas visuales:

| Modo simple — 1 viaje | Modo consolidado — N viajes |
|---|---|
| Una factura por cada viaje. Selecciona un solo waybill. Ideal para clientes que piden factura inmediata al concluir el flete. | Una factura para varios viajes del mismo cliente en un período. Selecciona N waybills. Ideal para cortes quincenales o mensuales. |

### Paso 2 — Cliente y selección de viajes

- El usuario selecciona el cliente (`partner_invoice_id`)
- El sistema carga automáticamente los waybills de ese cliente en estado `arrived` con `invoice_status = 'no_invoice'`
- **Modo simple:** solo se puede seleccionar 1 waybill (radio button)
- **Modo consolidado:** se pueden seleccionar N waybills (checkboxes)
- **Validación consolidado:** si los waybills seleccionados tienen distintos `vehicle_id` → advertencia visible (no bloqueo). Se usa el vehículo del primer waybill en el nodo Autotransporte del XML
- El resumen de montos (subtotal, IVA, retención, total) se actualiza en tiempo real al seleccionar/deseleccionar

### Paso 3 — Datos fiscales

- `UsoCFDI` — selector (G03 por default para personas morales)
- Diario contable — pre-llenado con `tms_sales_journal_id` de `res.company`, editable
- Resumen final con desglose completo antes de timbrar

### Paso 4 — Resultado

- UUID visible con opción de copiar
- Botón "Descargar PDF" — PDF de factura timbrada
- Botón "Enviar por email" — usa plantilla mail existente
- Los waybills incluidos pasan automáticamente a estado `closed`

---

## 4. Ciclo de Cancelación

### 4.1 Los 3 motivos SAT aplicables

| Motivo | Nombre SAT | Cuándo usar | Efecto en waybills |
|---|---|---|---|
| **01** | Errores con relación | Error en RFC, monto, datos — se corrige con factura nueva (sustituta) | Waybills SIGUEN en `closed` — la sustituta cubre el cobro |
| **02** | Errores sin relación | Error pero no hay sustituta — ej: factura duplicada, cliente equivocado | Waybills REGRESAN a `arrived` — listos para refacturar |
| **03** | Operación no realizada | El cliente rechazó el cobro o el viaje fue cancelado | Waybills REGRESAN a `arrived` — listos para refacturar |

> Motivo 04 (operación nominativa en global) NO aplica para TMS.

### 4.2 Flujo motivo 01 — Corregir factura

1. Usuario hace clic en "Corregir factura" en la factura timbrada
2. Sistema abre el wizard pre-llenado con los mismos viajes y datos — usuario solo corrige el error
3. Sistema timbra la factura corregida (sustituta) con `TipoRelacion='04'` y UUID de la original en `CfdiRelacionados`
4. Sistema envía solicitud de cancelación de la original al SAT con motivo 01 + UUID sustituta
5. SAT notifica al receptor por Buzón Tributario — tiene 3 días hábiles (aceptación ficta si no responde)
6. Waybills: **no cambian de estado** — siguen en `closed`. Factura original pasa a estado `sustituida`

### 4.3 Flujo motivos 02/03 — Cancelar sin reemplazar

1. Usuario hace clic en "Cancelar factura" — sistema pregunta motivo (02 o 03) con descripción en lenguaje simple
2. Sistema envía solicitud al SAT. Si < 1 día hábil: cancelación inmediata. Si no: espera aceptación receptor
3. **Mientras estado sea `en_cancelacion`: waybills siguen en `closed` — NO liberar prematuramente**
4. Cuando SAT confirma la cancelación: waybills regresan automáticamente a `arrived` con `invoice_status='no_invoice'`
5. Aparece botón "Volver a facturar" — abre wizard con los mismos viajes pre-seleccionados

### 4.4 Estados de la factura (account.move extendido)

| Estado TMS (`tms_cfdi_status`) | Estado account.move | Descripción |
|---|---|---|
| `borrador` | `draft` | Factura creada, sin timbrar |
| `timbrada` | `posted` | UUID obtenido, vigente ante el SAT |
| `en_cancelacion` | `posted` (lock) | Solicitud enviada, esperando respuesta receptor |
| `cancelada` | `cancel` | SAT confirmó cancelación. Waybills liberados (motivo 02/03) |
| `sustituida` | `cancel` | Cancelada con motivo 01 — tiene factura sustituta activa |

---

## 5. Arquitectura Técnica

### 5.1 Extensión de account.move — `models/account_move_tms.py`

```python
class AccountMove(models.Model):
    _inherit = 'account.move'

    # Solo visibles cuando tms_is_invoice = True
    tms_waybill_ids         = fields.Many2many('tms.waybill', ...)
    tms_cfdi_uuid           = fields.Char(string='UUID CFDI Ingreso', size=36, copy=False)
    tms_cfdi_xml            = fields.Binary(string='XML Timbrado', copy=False)
    tms_cfdi_status         = fields.Selection([
                                ('borrador','Borrador'),('timbrada','Timbrada'),
                                ('en_cancelacion','En cancelación'),
                                ('cancelada','Cancelada'),('sustituida','Sustituida')
                              ], default='borrador', copy=False)
    tms_cfdi_motivo         = fields.Selection([('01','01 - Errores con relación'),
                                ('02','02 - Errores sin relación'),
                                ('03','03 - Operación no realizada')], copy=False)
    tms_cfdi_uuid_sustituta = fields.Char(string='UUID Factura Sustituta', size=36, copy=False)
    tms_id_ccp_ingreso      = fields.Char(string='IdCCP Ingreso', size=36, copy=False)
    tms_is_invoice          = fields.Boolean(compute='_compute_tms_is_invoice', store=True)

    @api.depends('journal_id', 'journal_id.company_id.tms_sales_journal_id')
    def _compute_tms_is_invoice(self):
        """Determina si esta factura es del diario TMS para mostrar campos fiscales."""
        for rec in self:
            rec.tms_is_invoice = (rec.journal_id == rec.company_id.tms_sales_journal_id)
```

Campos en `account.move` — resumen:

| Campo | Tipo | Req. | Descripción |
|---|---|---|---|
| `tms_waybill_ids` | Many2many tms.waybill | ✅ | Viajes incluidos en esta factura |
| `tms_cfdi_uuid` | Char(36) | | UUID del CFDI Ingreso timbrado |
| `tms_cfdi_xml` | Binary | | XML timbrado almacenado |
| `tms_cfdi_status` | Selection | ✅ | borrador/timbrada/en_cancelacion/cancelada/sustituida |
| `tms_cfdi_motivo` | Selection | | 01/02/03 — se llena al cancelar |
| `tms_cfdi_uuid_sustituta` | Char(36) | | UUID de la factura sustituta (motivo 01) |
| `tms_id_ccp_ingreso` | Char(36) | | IdCCP generado al timbrar |
| `tms_is_invoice` | Boolean compute store=True | | True si es del diario TMS |

### 5.2 Cambios en tms_waybill.py

| Qué | Cómo |
|---|---|
| `invoice_ids` | Many2many → account.move filtrado a `tms_is_invoice=True`. Smart button "Ver Factura" con count. |
| `invoice_status` | Selection compute store=True: `no_invoice` / `invoiced`. Depende de `invoice_ids.tms_cfdi_status`. |
| `action_create_invoice()` | Reemplazar stub: abre wizard `tms.invoice.wizard`. NO cambia estado waybill todavía. |
| Estado `closed` | Solo se activa cuando existe `invoice_ids` con `tms_cfdi_status='timbrada'`. Triggered por compute. |
| Botón "Facturar" | `invisible="state not in ['aprobado','waybill','in_transit','arrived']"` |
| `action_release_from_invoice()` | Nuevo método: libera waybill a `arrived` cuando factura cancelada con motivo 02/03. |

### 5.3 Cambios en xml_builder.py

```python
def build(self, waybill_or_move, tipo='T'):
    """
    Construye el XML CFDI. tipo='T' para Traslado (existente), tipo='I' para Ingreso (nuevo).
    Mantiene compatibilidad hacia atrás — tipo='T' funciona exactamente igual que antes.
    """
    if tipo == 'T':
        return self._build_traslado(waybill_or_move, datos)
    elif tipo == 'I':
        return self._build_ingreso(waybill_or_move, datos)
```

Diferencias CFDI Ingreso vs Traslado:

| Atributo CFDI | Traslado (T) — actual | Ingreso (I) — nuevo |
|---|---|---|
| TipoDeComprobante | `T` | `I` |
| SubTotal | `0` | `sum(waybill.amount_untaxed)` |
| Total | `0` | `sum(waybill.amount_total)` |
| Conceptos | 1 concepto vacío | 1 concepto por waybill con monto real |
| ObjetoImp | `01` (no objeto) | `02` (sí objeto de impuesto) |
| Nodo Impuestos | PROHIBIDO (CFDI40201) | REQUERIDO: IVA 16% + Retención 4% condicional |
| Ubicaciones | 1 par OR/DE del waybill | N pares OR/DE — uno por waybill incluido |
| Mercancías | Todas del waybill | Todas de todos los waybills incluidos |
| Complemento CP 3.1 | ✅ Siempre | ✅ Siempre — SAT obliga a transportistas |
| CfdiRelacionados | No aplica | Solo motivo 01: `TipoRelacion='04'` + UUID original |

Nuevos métodos en xml_builder.py:

```python
def _build_ingreso(self, move, datos):
    """Construye CFDI tipo Ingreso con Carta Porte 3.1. Itera move.tms_waybill_ids."""

def _build_impuestos_ingreso(self, move):
    """IVA 16% siempre. Retención 4% solo si receptor is_company=True y no ZEDE."""

def _get_tasa_iva(self, partner):
    """Retorna 0.16 o 0.00 según partner.zip contra catálogo tms.sat.zona.especial."""

def _build_cfdi_relacionados(self, uuid_original):
    """Nodo CfdiRelacionados con TipoRelacion='04' para sustitución motivo 01."""
```

### 5.4 IVA — lógica completa

| Escenario | Lógica |
|---|---|
| Receptor persona moral (`is_company=True`) | IVA 16% + Retención 4%. Validar: RFC 12 chars = PM. Si RFC tiene 13 chars → `UserError` antes de timbrar. |
| Receptor persona física (`is_company=False`) | IVA 16%, sin retención. Validar: RFC 13 chars = PF. |
| Receptor en zona ZEDE (Istmo Tehuantepec) | IVA 0%. Verificar `receptor.zip` contra catálogo `tms.sat.zona.especial`. Si zip ∈ ZEDE → `TasaOCuota=0.000000`. |
| CFDI Traslado (tipo T) | NUNCA lleva impuestos — nodo Impuestos prohibido (regla CFDI40201). Sin cambio. |

### 5.5 Nuevo modelo — tms.sat.zona.especial

```python
class TmsSatZonaEspecial(models.Model):
    _name = 'tms.sat.zona.especial'
    # SIN company_id — catálogo global SAT
    name    = fields.Char(string='Nombre zona', required=True)
    cp_from = fields.Char(string='CP inicio', size=5, required=True)
    cp_to   = fields.Char(string='CP fin',    size=5, required=True)
```

---

## 6. File Manifest

| Archivo | Acción | Qué cambia |
|---|---|---|
| `models/res_company.py` | MODIFICAR | `tms_sales_journal_id` Many2one account.journal |
| `models/res_config_settings.py` | MODIFICAR | `tms_sales_journal_id` related + sección Facturación TMS en vistas |
| `models/account_move_tms.py` | **CREAR** | `_inherit account.move`: 8 campos tms_*, métodos timbrado/cancelación |
| `models/tms_waybill.py` | MODIFICAR | `invoice_ids`, `invoice_status`, `action_create_invoice`, `action_release_from_invoice`, estado `closed` |
| `models/tms_sat_zona_especial.py` | **CREAR** | Catálogo zonas ZEDE — global sin company_id |
| `services/xml_builder.py` | MODIFICAR | `build(tipo)`, `_build_ingreso()`, `_build_impuestos_ingreso()`, `_get_tasa_iva()`, `_build_cfdi_relacionados()` |
| `wizard/tms_invoice_wizard.py` | **CREAR** | Wizard 4 pasos: modo, cliente+viajes, datos fiscales, resultado |
| `wizard/tms_invoice_wizard_views.xml` | **CREAR** | Vistas del wizard con lógica modo simple/consolidado |
| `wizard/tms_cancel_invoice_wizard.py` | **CREAR** | Wizard cancelación: motivo 01/02/03, validación orden sustitución |
| `wizard/tms_cancel_invoice_wizard_views.xml` | **CREAR** | Vistas del wizard de cancelación |
| `views/tms_waybill_views.xml` | MODIFICAR | Smart button factura, botón Facturar desde `aprobado`, pestaña Facturación |
| `views/account_move_tms_views.xml` | **CREAR** | Pestaña TMS en form de account.move, botones Corregir/Cancelar/Volver a facturar |
| `views/res_config_settings_views.xml` | MODIFICAR | Sección Facturación TMS con selector de diario |
| `reports/tms_invoice_report.xml` | **CREAR** | PDF factura timbrada (UUID, datos fiscales, conceptos por viaje, impuestos, QR SAT, cadena TFD) |
| `data/tms_sat_zona_especial.csv` | **CREAR** | CPs del Istmo de Tehuantepec — zonas ZEDE |
| `security/ir.model.access.csv` | MODIFICAR | Acceso a `tms.sat.zona.especial` |
| `__manifest__.py` | MODIFICAR | Nuevos archivos en `data[]` y `views[]` |

**9 archivos nuevos · 8 archivos modificados · 0 archivos eliminados**

---

## 7. Acceptance Criteria

| ID | Criterio | Archivo | Cómo verificar |
|---|---|---|---|
| AC-01 | Wizard muestra opción "Un viaje" y "Varios viajes" en Paso 1 | `tms_invoice_wizard` | Abrir wizard → 2 tarjetas visibles |
| AC-02 | Botón "Facturar" visible desde estado `aprobado` en adelante | `tms_waybill_views.xml` | Waybill en aprobado → botón presente |
| AC-03 | Modo simple: solo permite seleccionar 1 waybill | `tms_invoice_wizard` | Seleccionar 2 → el segundo reemplaza al primero |
| AC-04 | Modo consolidado: permite seleccionar N waybills del mismo cliente | `tms_invoice_wizard` | Seleccionar 3 → resumen muestra suma correcta |
| AC-05 | Advertencia visible si waybills consolidados tienen distintos vehículos | `tms_invoice_wizard.py` | Seleccionar viajes con 2 camiones → aviso amarillo |
| AC-06 | Resumen calcula subtotal, IVA 16% y retención 4% en tiempo real | `tms_invoice_wizard.py` | Verificar cálculos contra fórmula manual |
| AC-07 | CFDI Ingreso timbra exitosamente — UUID obtenido | `xml_builder.py` | Completar wizard → UUID visible en account.move |
| AC-08 | XML Ingreso tiene `TipoDeComprobante='I'` | `xml_builder.py` | Descargar XML → atributo correcto |
| AC-09 | XML Ingreso incluye Complemento Carta Porte 3.1 | `xml_builder.py` | XML → nodo `cartaporte30:CartaPorte` presente |
| AC-10 | N waybills consolidados generan N pares Ubicacion OR/DE en el XML | `xml_builder.py` | Factura con 3 viajes → 6 nodos Ubicacion |
| AC-11 | N waybills generan N conceptos con montos reales | `xml_builder.py` | 3 viajes → 3 Concepto con ValorUnitario correcto |
| AC-12 | Retención 4% solo si receptor `is_company=True` | `xml_builder.py` | PF → sin Retenciones. PM → Retenciones IVA 4% |
| AC-13 | UserError si longitud RFC no coincide con `is_company` | `account_move_tms.py` | RFC con longitud incorrecta → error antes de timbrar |
| AC-14 | IVA 0% para receptor con CP en zona ZEDE | `xml_builder.py` | CP del Istmo → `TasaOCuota=0.000000` en XML |
| AC-15 | Waybill pasa a `closed` solo cuando `tms_cfdi_status='timbrada'` | `tms_waybill.py` | Timbrar factura → waybill cambia a closed |
| AC-16 | Cancelación motivo 01: sistema obliga timbrar sustituta primero | `tms_cancel_invoice_wizard` | Intentar cancelar con 01 sin sustituta → error bloqueante |
| AC-17 | Cancelación motivo 01: waybills siguen en `closed` | `tms_waybill.py` | Cancelar con motivo 01 → waybills no cambian de estado |
| AC-18 | Cancelación motivo 02/03: waybills regresan a `arrived` al confirmar SAT | `account_move_tms.py` | Confirmar cancelación → waybills en arrived |
| AC-19 | Botón "Volver a facturar" en factura cancelada (motivo 02/03) | `account_move_tms_views.xml` | Factura cancelada → botón visible, abre wizard pre-llenado |
| AC-20 | PDF factura descargable con UUID, QR SAT, conceptos e impuestos | `tms_invoice_report.xml` | Botón PDF → documento con mínimo 6 secciones |
| AC-21 | Diario ventas configurable en Ajustes → TMS → Facturación | `res_config_settings` | Cambiar diario → nueva factura usa ese diario |
| AC-22 | 0 warnings ni errores en odoo.log tras actualización | `__manifest__.py` | `grep 'ERROR\|WARNING' odoo.log` = 0 líneas relevantes |

---

## 8. Upgrade Command

```bash
# Nuevos modelos → actualizar
python3 odoo-bin -c odoo.conf -u tms -d tms_dev --stop-after-init
python3 odoo-bin -c odoo.conf

# Verificar
grep -n 'WARNING\|ERROR' odoo.log | tail -30
```

> Si `account_move_tms.py` genera error de migración, usar `-i tms` para reinstalar. Respaldar `tms_dev` antes.

---

## 9. Reglas absolutas para esta etapa

- SIEMPRE comentar cada función con docstring en **español**
- NUNCA hardcodear `tipo='T'` en `build()` — respetar el parámetro
- NUNCA modificar la lógica existente de `_build_traslado()` — solo agregar ramas nuevas
- NUNCA liberar waybills mientras `tms_cfdi_status='en_cancelacion'`
- NUNCA poner `company_id` en `tms.sat.zona.especial` — es catálogo global
- SIEMPRE generar `tms_id_ccp_ingreso` al momento de timbrar, no en `create()`
- SIEMPRE validar RFC length vs `is_company` antes de llamar al PAC
- NO tocar `pac_manager.py` — ya es agnóstico al tipo de CFDI

---

## 10. Context Blueprint

### Modelos _name

- `tms.waybill` (existente — modificar)
- `tms.sat.zona.especial` (NUEVO — global sin company_id)
- `account.move` (existente — _inherit con campos tms_*)
- `res.company` (existente — agregar tms_sales_journal_id)
- `res.config.settings` (existente — agregar campo related)

### Decoradores y campos nuevos clave

```python
# En account.move (_inherit)
tms_waybill_ids     = fields.Many2many('tms.waybill', string='Viajes')
tms_cfdi_status     = fields.Selection([...], default='borrador', copy=False, tracking=True)
tms_is_invoice      = fields.Boolean(compute='_compute_tms_is_invoice', store=True)

# En tms.waybill (_inherit existente)
invoice_ids         = fields.Many2many('account.move', domain=[('tms_is_invoice','=',True)])
invoice_status      = fields.Selection([('no_invoice','Sin facturar'),('invoiced','Facturado')],
                        compute='_compute_invoice_status', store=True)

# En xml_builder.py
def build(self, waybill_or_move, tipo='T'): ...
def _build_ingreso(self, move, datos): ...
def _build_impuestos_ingreso(self, move): ...
def _get_tasa_iva(self, partner): ...
def _build_cfdi_relacionados(self, uuid_original): ...
```

### Seguridad — ir.model.access.csv

```csv
access_tms_sat_zona_especial_user,tms.sat.zona.especial user,model_tms_sat_zona_especial,base.group_user,1,0,0,0
access_tms_sat_zona_especial_manager,tms.sat.zona.especial manager,model_tms_sat_zona_especial,tms.group_tms_manager,1,1,1,1
```

---

## 11. Lo que viene después de V2.3

| Versión | Nombre | Descripción |
|---|---|---|
| V2.3.1 | Notas de crédito/cargo | CFDI Egreso tipo E sin Carta Porte — ajustes al CFDI Ingreso ya timbrado |
| V2.3.2 | Cancelación CFDI Traslado | Mismo esquema motivos 01/02/03. Motivo 01 requiere Traslado sustituto. Motivo 02/03 libera waybill a estado previo al timbrado. |
| V2.4 | KPIs y portal | Dashboard rentabilidad. Beneficio Neto = Ingreso − Casetas − Diesel − Comisiones. |
| V2.5 | Limpieza final | Estados simplificados a 6. Menús irrelevantes ocultos. QA < 10 min primera Carta Porte. |

---

*TMS Hombre Camión · NextPack · SDD V2.3 · 2026-04-15*
