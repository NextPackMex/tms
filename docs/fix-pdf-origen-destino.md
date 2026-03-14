# FIX — PDF Pre-cotización + Origen/Destino vacío en waybill

⚠️ **NO crear rama nueva — estamos en `feat/etapa-2.1.6-pdf-cotizacion`**
⚠️ **NO hacer git push — Mois lo hace manualmente**

---

## PROBLEMA 1 — PDF Pre-cotización se ve feo

El PDF actual tiene los headers de la tabla cortados, los datos del cliente no se leen bien, y el diseño general es pobre. Necesita un rediseño completo.

### Archivo a modificar: `report/tms_cotizacion_report_template.xml`

Reemplaza TODO el contenido del archivo con este template rediseñado:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <template id="report_cotizacion_template">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="doc">
                <t t-call="web.external_layout">
                    <div class="page" style="font-family: Arial, sans-serif;">

                        <!-- ===== ENCABEZADO ===== -->
                        <div class="row mb-3">
                            <div class="col-8">
                                <h2 style="color: #035d96; margin-bottom: 2px;">
                                    <strong>PRE-COTIZACIÓN DE FLETE</strong>
                                </h2>
                                <p style="color: #999; font-size: 11px; margin: 0;">
                                    Documento comercial informativo — No es un CFDI
                                </p>
                            </div>
                            <div class="col-4 text-end">
                                <p style="margin: 0;">
                                    <strong>Fecha:</strong>
                                    <span t-esc="context_timestamp(datetime.datetime.now()).strftime('%d/%m/%Y')"/>
                                </p>
                            </div>
                        </div>

                        <hr style="border-top: 3px solid #e1a13e; margin: 8px 0 16px 0;"/>

                        <!-- ===== DATOS DEL CLIENTE ===== -->
                        <div class="row mb-3">
                            <div class="col-12">
                                <h5 style="color: #035d96; margin-bottom: 8px;">
                                    <i class="fa fa-building"/> Datos del Cliente
                                </h5>
                            </div>
                            <div class="col-6">
                                <table style="font-size: 12px; line-height: 1.8;">
                                    <tr>
                                        <td style="width: 80px;"><strong>Cliente:</strong></td>
                                        <td><span t-field="doc.partner_invoice_id.name"/></td>
                                    </tr>
                                    <tr t-if="doc.partner_invoice_id.vat">
                                        <td><strong>RFC:</strong></td>
                                        <td><span t-field="doc.partner_invoice_id.vat"/></td>
                                    </tr>
                                </table>
                            </div>
                            <div class="col-6">
                                <table style="font-size: 12px; line-height: 1.8;">
                                    <tr t-if="doc.partner_invoice_id.email">
                                        <td style="width: 80px;"><strong>Email:</strong></td>
                                        <td><span t-field="doc.partner_invoice_id.email"/></td>
                                    </tr>
                                    <tr t-if="doc.partner_invoice_id.phone">
                                        <td><strong>Tel:</strong></td>
                                        <td><span t-field="doc.partner_invoice_id.phone"/></td>
                                    </tr>
                                </table>
                            </div>
                        </div>

                        <!-- ===== RUTA: ORIGEN → DESTINO ===== -->
                        <div class="row mb-3">
                            <div class="col-12">
                                <h5 style="color: #035d96; margin-bottom: 8px;">
                                    <i class="fa fa-map-marker"/> Ruta
                                </h5>
                            </div>
                            <div class="col-5">
                                <div style="background: #e8f4e8; padding: 10px 14px; border-radius: 6px; border-left: 4px solid #28a745;">
                                    <strong style="font-size: 11px; color: #666;">ORIGEN</strong><br/>
                                    <span style="font-size: 16px; font-weight: bold;">
                                        CP <span t-field="doc.origin_zip"/>
                                    </span>
                                </div>
                            </div>
                            <div class="col-2 text-center" style="padding-top: 14px;">
                                <span style="font-size: 24px; color: #035d96;">→</span>
                            </div>
                            <div class="col-5">
                                <div style="background: #fde8e8; padding: 10px 14px; border-radius: 6px; border-left: 4px solid #dc3545;">
                                    <strong style="font-size: 11px; color: #666;">DESTINO</strong><br/>
                                    <span style="font-size: 16px; font-weight: bold;">
                                        CP <span t-field="doc.dest_zip"/>
                                    </span>
                                </div>
                            </div>
                        </div>

                        <!-- ===== MÉTRICAS DE RUTA ===== -->
                        <div class="row mb-4">
                            <div class="col-4 text-center">
                                <div style="background: #f0f5fa; padding: 10px; border-radius: 6px;">
                                    <span style="font-size: 11px; color: #666; display: block;">DISTANCIA</span>
                                    <strong style="font-size: 22px; color: #035d96;">
                                        <span t-esc="'%.0f' % doc.distance_km"/> km
                                    </strong>
                                </div>
                            </div>
                            <div class="col-4 text-center">
                                <div style="background: #f0f5fa; padding: 10px; border-radius: 6px;">
                                    <span style="font-size: 11px; color: #666; display: block;">TIEMPO ESTIMADO</span>
                                    <strong style="font-size: 22px; color: #035d96;">
                                        <span t-esc="'%.1f' % doc.duration_hours"/> hrs
                                    </strong>
                                </div>
                            </div>
                            <div class="col-4 text-center">
                                <div style="background: #f0f5fa; padding: 10px; border-radius: 6px;">
                                    <span style="font-size: 11px; color: #666; display: block;">CASETAS (TAG)</span>
                                    <strong style="font-size: 22px; color: #035d96;">
                                        $ <span t-esc="'%,.2f' % doc.toll_cost"/>
                                    </strong>
                                </div>
                            </div>
                        </div>

                        <!-- ===== PROPUESTA DE PRECIO ===== -->
                        <div class="row mb-3">
                            <div class="col-12">
                                <h5 style="color: #035d96; margin-bottom: 8px;">
                                    <i class="fa fa-money"/> Cotización de Flete
                                </h5>
                            </div>
                        </div>

                        <!-- Calcular variables para evitar repetir lógica -->
                        <t t-set="subtotal"
                           t-value="doc.proposal_km_total if doc.selected_proposal == 'km'
                                    else (doc.proposal_trip_total if doc.selected_proposal == 'trip'
                                    else doc.direct_price)"/>
                        <t t-set="iva" t-value="subtotal * 0.16"/>
                        <t t-set="retencion" t-value="subtotal * 0.04 if doc.partner_invoice_id.is_company else 0"/>
                        <t t-set="total" t-value="subtotal + iva - retencion"/>
                        <t t-set="metodo_nombre"
                           t-value="'Por Kilómetro' if doc.selected_proposal == 'km'
                                    else ('Por Viaje (costos operativos)' if doc.selected_proposal == 'trip'
                                    else 'Precio Directo')"/>

                        <table class="table" style="font-size: 13px; border: 1px solid #ddd;">
                            <thead>
                                <tr style="background: #035d96; color: white;">
                                    <th style="padding: 10px;">Concepto</th>
                                    <th class="text-end" style="padding: 10px; width: 180px;">Importe</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td style="padding: 8px 10px;">
                                        <strong>Servicio de Flete</strong>
                                        <br/>
                                        <small style="color: #888;">
                                            Método: <span t-esc="metodo_nombre"/>
                                        </small>
                                    </td>
                                    <td class="text-end" style="padding: 8px 10px;">
                                        $ <span t-esc="'%,.2f' % subtotal"/>
                                    </td>
                                </tr>
                                <tr style="background: #f9f9f9;">
                                    <td style="padding: 8px 10px;">IVA (16%)</td>
                                    <td class="text-end" style="padding: 8px 10px;">
                                        $ <span t-esc="'%,.2f' % iva"/>
                                    </td>
                                </tr>
                                <tr t-if="doc.partner_invoice_id.is_company" style="color: #dc3545;">
                                    <td style="padding: 8px 10px;">Retención IVA (4%)</td>
                                    <td class="text-end" style="padding: 8px 10px;">
                                        - $ <span t-esc="'%,.2f' % retencion"/>
                                    </td>
                                </tr>
                            </tbody>
                            <tfoot>
                                <tr style="background: #e1a13e;">
                                    <td style="padding: 12px 10px;">
                                        <strong style="font-size: 16px; color: #333;">TOTAL</strong>
                                    </td>
                                    <td class="text-end" style="padding: 12px 10px;">
                                        <strong style="font-size: 20px; color: #333;">
                                            $ <span t-esc="'%,.2f' % total"/>
                                        </strong>
                                    </td>
                                </tr>
                            </tfoot>
                        </table>

                        <!-- ===== CARGA (si hay mercancías) ===== -->
                        <div t-if="doc.line_ids" class="mb-3">
                            <h5 style="color: #035d96; margin-bottom: 8px;">
                                <i class="fa fa-cubes"/> Carga a Transportar
                            </h5>
                            <table class="table table-sm" style="font-size: 12px;">
                                <thead>
                                    <tr style="background: #f0f0f0;">
                                        <th>Descripción</th>
                                        <th class="text-end">Cantidad</th>
                                        <th class="text-end">Peso (kg)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <t t-foreach="doc.line_ids" t-as="line">
                                        <tr>
                                            <td><span t-field="line.description"/></td>
                                            <td class="text-end"><span t-field="line.quantity"/></td>
                                            <td class="text-end"><span t-field="line.weight_kg"/></td>
                                        </tr>
                                    </t>
                                </tbody>
                            </table>
                        </div>

                        <!-- ===== NOTAS LEGALES ===== -->
                        <div style="border-top: 1px solid #ddd; padding-top: 10px; margin-top: 20px;">
                            <p style="font-size: 9px; color: #999; margin: 0;">
                                <strong>Nota:</strong> Esta pre-cotización es un documento comercial informativo.
                                No constituye un CFDI ni tiene validez fiscal. Los precios pueden variar según
                                condiciones de mercado. Vigencia: 15 días a partir de la fecha de emisión.
                                Precios en MXN. IVA 16% incluido. Retención IVA 4% aplica solo a personas morales.
                                Casetas calculadas con sistema de telepeaje (TAG).
                            </p>
                        </div>

                    </div>
                </t>
            </t>
        </t>
    </template>
</odoo>
```

---

## PROBLEMA 2 — Origen y Destino vacíos en vista waybill (estado cotizado)

Cuando un waybill está en estado `cotizado` o `aprobado`, no hay `partner_origin_id` ni `partner_dest_id` todavía. Las cards de Origen y Destino se ven vacías. Deben mostrar al menos la información que sí tenemos: el CP y el nombre de ciudad/estado que se resuelve del código postal.

### Archivo a modificar: `views/tms_waybill_views.xml`

Busca las dos cards de Origen y Destino (la sección `<div class="row mb-3">` que contiene las dos cards con `string="Origen"` y `string="Destino"`).

Reemplaza **toda esa sección** (el `<div class="row mb-3">` que contiene ambas cards) con esto:

```xml
                    <div class="row mb-3">
                        <div class="col-lg-6">
                            <!-- ORIGEN CARD -->
                            <div class="card shadow-sm p-3 bg-white h-100" style="border: 1px solid #e0e0e0;">
                                <div class="d-flex align-items-center mb-2" style="border-left: 4px solid #28a745; padding-left: 8px;">
                                    <strong style="font-size: 1.1em;">Origen</strong>
                                </div>
                                <!-- Info mínima: CP + ciudad/estado (siempre visible si hay CP) -->
                                <div invisible="not origin_zip" class="mb-2">
                                    <div class="d-flex align-items-center">
                                        <span class="badge text-bg-success me-2">
                                            CP <field name="origin_zip" readonly="1" nolabel="1"/>
                                        </span>
                                        <span class="text-muted">
                                            <field name="origin_city_name" readonly="1" nolabel="1"/>
                                        </span>
                                    </div>
                                </div>
                                <!-- Datos completos: solo visibles cuando hay partner_origin_id -->
                                <group class="mb-0" readonly="state in ['in_transit','arrived','closed','cancel']" invisible="state in ['cotizado']">
                                    <field name="partner_origin_id" required="state not in ['draft', 'cotizado', 'aprobado']"/>
                                    <field name="origin_address" required="state not in ['draft', 'cotizado', 'aprobado']"/>
                                    <label for="origin_zip" invisible="state in ['cotizado', 'aprobado']"/>
                                    <div class="d-flex align-items-center" invisible="state in ['cotizado', 'aprobado']">
                                        <field name="origin_zip" required="state not in ['draft', 'cotizado', 'aprobado']" class="me-2" style="max-width: 100px;"/>
                                        <field name="origin_city_name" readonly="1" nolabel="1" class="text-muted fst-italic"/>
                                    </div>
                                    <field name="origin_rfc"/>
                                </group>
                                <div class="text-end mt-2" invisible="state in ['cotizado', 'in_transit','arrived','closed','cancel']">
                                    <button name="action_clear_origen" type="object" icon="fa-trash" title="Limpiar" class="btn btn-link text-danger"/>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-6">
                            <!-- DESTINO CARD -->
                            <div class="card shadow-sm p-3 bg-white h-100" style="border: 1px solid #e0e0e0;">
                                <div class="d-flex align-items-center mb-2" style="border-left: 4px solid #dc3545; padding-left: 8px;">
                                    <strong style="font-size: 1.1em;">Destino</strong>
                                </div>
                                <!-- Info mínima: CP + ciudad/estado (siempre visible si hay CP) -->
                                <div invisible="not dest_zip" class="mb-2">
                                    <div class="d-flex align-items-center">
                                        <span class="badge text-bg-danger me-2">
                                            CP <field name="dest_zip" readonly="1" nolabel="1"/>
                                        </span>
                                        <span class="text-muted">
                                            <field name="dest_city_name" readonly="1" nolabel="1"/>
                                        </span>
                                    </div>
                                </div>
                                <!-- Datos completos: solo visibles cuando no es cotizado -->
                                <group class="mb-0" readonly="state in ['in_transit','arrived','closed','cancel']" invisible="state in ['cotizado']">
                                    <field name="partner_dest_id" required="state not in ['draft', 'cotizado', 'aprobado']"/>
                                    <field name="dest_address" required="state not in ['draft', 'cotizado', 'aprobado']"/>
                                    <label for="dest_zip" invisible="state in ['cotizado', 'aprobado']"/>
                                    <div class="d-flex align-items-center" invisible="state in ['cotizado', 'aprobado']">
                                        <field name="dest_zip" required="state not in ['draft', 'cotizado', 'aprobado']" class="me-2" style="max-width: 100px;"/>
                                        <field name="dest_city_name" readonly="1" nolabel="1" class="text-muted fst-italic"/>
                                    </div>
                                    <field name="dest_rfc"/>
                                </group>
                                <div class="text-end mt-2" invisible="state in ['cotizado', 'in_transit','arrived','closed','cancel']">
                                    <button name="action_clear_destino" type="object" icon="fa-trash" title="Limpiar" class="btn btn-link text-danger"/>
                                </div>
                            </div>
                        </div>
                    </div>
```

---

## TAMBIÉN: Fix el PDF del waybill (report_tms_waybill_document)

En `report/tms_waybill_report.xml` (o como se llame el archivo que tiene `report_tms_waybill_document`), las secciones de Origen y Destino usan `origin_city_id.name` que probablemente no existe. Busca:

```bash
grep -rn "origin_city_id\|dest_city_id" report/
```

Si encuentra referencias, reemplazar:
- `o.origin_city_id.name` → `o.origin_city_name`
- `o.dest_city_id.name` → `o.dest_city_name`

Y envolver las referencias a `partner_origin_id` y `partner_dest_id` en `t-if` para que no truene cuando están vacíos:

```xml
<!-- Origen -->
<div class="col-4">
    <strong style="color: #212529; font-size: 1.1em;">Origen</strong><br/>
    <t t-if="o.partner_origin_id">
        <span t-field="o.partner_origin_id.name"/><br/>
    </t>
    <t t-if="o.origin_city_name">
        <span t-esc="o.origin_city_name"/><br/>
    </t>
    <t t-elif="o.origin_zip">
        CP <span t-field="o.origin_zip"/><br/>
    </t>
    <small t-if="o.origin_address" t-field="o.origin_address"/>
</div>
<!-- Destino -->
<div class="col-4">
    <strong style="color: #212529; font-size: 1.1em;">Destino</strong><br/>
    <t t-if="o.partner_dest_id">
        <span t-field="o.partner_dest_id.name"/><br/>
    </t>
    <t t-if="o.dest_city_name">
        <span t-esc="o.dest_city_name"/><br/>
    </t>
    <t t-elif="o.dest_zip">
        CP <span t-field="o.dest_zip"/><br/>
    </t>
    <small t-if="o.dest_address" t-field="o.dest_address"/>
</div>
```

---

## QA

```bash
# Verificar XMLs válidos
python3 -c "
import xml.etree.ElementTree as ET
import glob
for f in glob.glob('report/*.xml') + glob.glob('views/tms_waybill_views.xml'):
    ET.parse(f)
    print(f'{f} — OK')
"

# Update módulo
python3 odoo-bin -c odoo.conf -u tms -d tms_dev --stop-after-init

# Verificar logs
grep -n "WARNING\|ERROR" odoo.log | tail -20
```

## COMMIT — Solo commit, NO push

```bash
git add -A
git commit -m "fix(2.1.6): rediseño PDF pre-cotización + origen/destino visible en estado cotizado"
```

⚠️ **NO ejecutar git push — Mois lo hace manualmente.**

---

*FIN DEL FIX*
