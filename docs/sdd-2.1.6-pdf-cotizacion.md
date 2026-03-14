# SDD — Etapa 2.1.6: PDF Pre-cotización + Email

| Campo | Valor |
|---|---|
| **Módulo** | TMS "Hombre Camión" (`tms/`) |
| **Fecha** | 2026-03-14 |
| **Prioridad** | Media |
| **Branch GIT** | `feat/etapa-2.1.6-pdf-cotizacion` |
| **Modo Antigravity** | `Planning + Low` |

---

## GIT — Crear rama antes de tocar código

```bash
cd ~/odoo/proyectos/tms
git checkout main && git pull origin main
git checkout -b feat/etapa-2.1.6-pdf-cotizacion
```

⚠️ **NO hacer push — Mois lo hace manualmente después de revisar.**

---

## PROBLEMA

El wizard de cotización calcula 3 propuestas (Por KM, Por Viaje, Precio Directo) pero el usuario no puede enviarle nada al cliente. Tiene que anotar los precios y comunicarlos manualmente por WhatsApp o teléfono. No hay PDF profesional ni forma de enviar por email.

**Objetivo:** Después de calcular las propuestas en el wizard Paso 1, el usuario puede generar un PDF de pre-cotización y enviarlo por email al cliente directamente desde Odoo.

---

## SOLUCIÓN

1. **Template QWeb** para generar un PDF con las 3 propuestas, ruta, distancia, tiempo estimado y logo de la empresa
2. **Botón "Enviar por Email"** en el wizard Paso 1 (después de calcular)
3. **Botón "Descargar PDF"** como alternativa para envío manual (WhatsApp, etc.)

⚠️ **IMPORTANTE:** Este PDF es una cotización COMERCIAL, NO es un CFDI. No lleva UUID, folio fiscal, ni sello del SAT. Es solo un documento de venta.

---

## ARCHIVOS A CREAR/MODIFICAR

| Archivo | Acción |
|---|---|
| `report/tms_cotizacion_report.xml` | **CREAR** — Template QWeb del PDF |
| `report/tms_cotizacion_report_template.xml` | **CREAR** — Diseño del contenido del PDF |
| `wizard/tms_cotizacion_wizard.py` | **MODIFICAR** — Agregar métodos enviar email + descargar PDF |
| `wizard/tms_cotizacion_wizard_views.xml` | **MODIFICAR** — Agregar botones en Paso 1 |
| `data/mail_template_cotizacion.xml` | **CREAR** — Template de email |
| `__manifest__.py` | **MODIFICAR** — Agregar archivos nuevos |

⚠️ **NO tocar:** `tms_waybill.py`, `tms_waybill_views.xml`, `tms_onboarding_wizard.py`
(La etapa 2.1.5 trabaja en el onboarding al mismo tiempo — NO pisar esos archivos)

---

## ANTES DE TOCAR CÓDIGO — Verificar con grep

```bash
# Verificar que NO existen reportes previos de cotización
grep -rn "cotizacion_report\|precotizacion\|quotation_report" report/ views/ wizard/
ls report/ 2>/dev/null || echo "Carpeta report/ no existe — hay que crearla"

# Verificar la estructura actual del wizard
grep -n "def action_\|def button_" wizard/tms_cotizacion_wizard.py

# Verificar campos calculados del wizard que usaremos en el PDF
grep -n "proposal_km_total\|proposal_trip_total\|direct_price\|distance_km\|duration_hours\|toll_cost\|selected_proposal" wizard/tms_cotizacion_wizard.py | head -20

# Verificar si existe carpeta data/
ls data/ 2>/dev/null || echo "Carpeta data/ no existe — hay que crearla"

# Verificar el partner_invoice_id en el wizard
grep -n "partner_invoice_id" wizard/tms_cotizacion_wizard.py | head -10
```

---

## PASO 1 — Crear carpetas necesarias

```bash
mkdir -p report
mkdir -p data
touch report/__init__.py  # vacío, solo para que Python lo reconozca si es necesario
```

---

## PASO 2 — Template QWeb del PDF

### Archivo: `report/tms_cotizacion_report.xml`

Define la acción de reporte que Odoo usa para generar el PDF.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <record id="action_report_tms_cotizacion" model="ir.actions.report">
        <field name="name">Pre-cotización TMS</field>
        <field name="model">tms.cotizacion.wizard</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">tms.report_cotizacion_template</field>
        <field name="report_file">tms.report_cotizacion_template</field>
        <field name="binding_type">report</field>
        <field name="print_report_name">'Pre-Cotizacion_%s' % (object.partner_invoice_id.name or 'SinCliente').replace(' ', '_')</field>
    </record>
</odoo>
```

### Archivo: `report/tms_cotizacion_report_template.xml`

Diseño visual del PDF. Incluye logo, datos del cliente, ruta, y las 3 propuestas.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <template id="report_cotizacion_template">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="doc">
                <t t-call="web.external_layout">
                    <div class="page">

                        <!-- Encabezado -->
                        <div class="row mb-4">
                            <div class="col-8">
                                <h2 style="color: #035d96;">
                                    <strong>PRE-COTIZACIÓN DE FLETE</strong>
                                </h2>
                                <p style="color: #888; font-size: 12px;">
                                    Documento comercial — No es un CFDI
                                </p>
                            </div>
                            <div class="col-4 text-end">
                                <p><strong>Fecha:</strong>
                                    <span t-esc="context_timestamp(datetime.datetime.now()).strftime('%d/%m/%Y')"/>
                                </p>
                            </div>
                        </div>

                        <!-- Datos del cliente -->
                        <div class="row mb-4">
                            <div class="col-12">
                                <h4 style="border-bottom: 2px solid #e1a13e; padding-bottom: 4px;">
                                    Datos del Cliente
                                </h4>
                            </div>
                            <div class="col-6">
                                <p>
                                    <strong>Cliente:</strong>
                                    <span t-field="doc.partner_invoice_id.name"/>
                                </p>
                                <p t-if="doc.partner_invoice_id.vat">
                                    <strong>RFC:</strong>
                                    <span t-field="doc.partner_invoice_id.vat"/>
                                </p>
                            </div>
                            <div class="col-6">
                                <p t-if="doc.partner_invoice_id.email">
                                    <strong>Email:</strong>
                                    <span t-field="doc.partner_invoice_id.email"/>
                                </p>
                                <p t-if="doc.partner_invoice_id.phone">
                                    <strong>Teléfono:</strong>
                                    <span t-field="doc.partner_invoice_id.phone"/>
                                </p>
                            </div>
                        </div>

                        <!-- Datos de la ruta -->
                        <div class="row mb-4">
                            <div class="col-12">
                                <h4 style="border-bottom: 2px solid #e1a13e; padding-bottom: 4px;">
                                    Datos de la Ruta
                                </h4>
                            </div>
                            <div class="col-4">
                                <p><strong>Origen (CP):</strong>
                                    <span t-field="doc.origin_zip"/></p>
                            </div>
                            <div class="col-4">
                                <p><strong>Destino (CP):</strong>
                                    <span t-field="doc.dest_zip"/></p>
                            </div>
                            <div class="col-4">
                                <p><strong>Ejes:</strong>
                                    <span t-field="doc.num_axles"/></p>
                            </div>
                        </div>

                        <!-- Resultados de ruta -->
                        <div class="row mb-4">
                            <div class="col-4 text-center"
                                 style="background: #f0f5fa; padding: 12px; border-radius: 8px;">
                                <h5 style="color: #035d96;">Distancia</h5>
                                <p style="font-size: 20px; font-weight: bold;">
                                    <span t-esc="'%.1f' % doc.distance_km"/> km
                                </p>
                            </div>
                            <div class="col-4 text-center"
                                 style="background: #f0f5fa; padding: 12px; border-radius: 8px;">
                                <h5 style="color: #035d96;">Tiempo Estimado</h5>
                                <p style="font-size: 20px; font-weight: bold;">
                                    <span t-esc="'%.1f' % doc.duration_hours"/> hrs
                                </p>
                            </div>
                            <div class="col-4 text-center"
                                 style="background: #f0f5fa; padding: 12px; border-radius: 8px;">
                                <h5 style="color: #035d96;">Casetas</h5>
                                <p style="font-size: 20px; font-weight: bold;">
                                    $ <span t-esc="'%.2f' % doc.toll_cost"/>
                                </p>
                            </div>
                        </div>

                        <!-- Las 3 propuestas -->
                        <div class="row mb-4">
                            <div class="col-12">
                                <h4 style="border-bottom: 2px solid #e1a13e; padding-bottom: 4px;">
                                    Propuestas de Precio
                                </h4>
                            </div>
                        </div>

                        <table class="table table-bordered" style="font-size: 13px;">
                            <thead style="background: #035d96; color: white;">
                                <tr>
                                    <th>Propuesta</th>
                                    <th>Método</th>
                                    <th class="text-end">Subtotal</th>
                                    <th class="text-end">IVA 16%</th>
                                    <th class="text-end" t-if="doc.partner_invoice_id.is_company">
                                        Ret. IVA 4%
                                    </th>
                                    <th class="text-end" style="background: #e1a13e; color: #333;">
                                        Total
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Propuesta A — Por KM -->
                                <tr t-att-style="'background: #e8f4e8; font-weight: bold;' if doc.selected_proposal == 'km' else ''">
                                    <td>
                                        A
                                        <span t-if="doc.selected_proposal == 'km'"
                                              style="color: green;"> ★ Seleccionada</span>
                                    </td>
                                    <td>Por Kilómetro</td>
                                    <td class="text-end">
                                        $ <span t-esc="'%.2f' % doc.proposal_km_total"/>
                                    </td>
                                    <td class="text-end">
                                        $ <span t-esc="'%.2f' % (doc.proposal_km_total * 0.16)"/>
                                    </td>
                                    <td class="text-end" t-if="doc.partner_invoice_id.is_company">
                                        $ <span t-esc="'%.2f' % (doc.proposal_km_total * 0.04)"/>
                                    </td>
                                    <td class="text-end">
                                        <strong>
                                            $ <span t-esc="'%.2f' % (doc.proposal_km_total * (1.16 - (0.04 if doc.partner_invoice_id.is_company else 0)))"/>
                                        </strong>
                                    </td>
                                </tr>
                                <!-- Propuesta B — Por Viaje -->
                                <tr t-att-style="'background: #e8f4e8; font-weight: bold;' if doc.selected_proposal == 'trip' else ''">
                                    <td>
                                        B
                                        <span t-if="doc.selected_proposal == 'trip'"
                                              style="color: green;"> ★ Seleccionada</span>
                                    </td>
                                    <td>Por Viaje (costos)</td>
                                    <td class="text-end">
                                        $ <span t-esc="'%.2f' % doc.proposal_trip_total"/>
                                    </td>
                                    <td class="text-end">
                                        $ <span t-esc="'%.2f' % (doc.proposal_trip_total * 0.16)"/>
                                    </td>
                                    <td class="text-end" t-if="doc.partner_invoice_id.is_company">
                                        $ <span t-esc="'%.2f' % (doc.proposal_trip_total * 0.04)"/>
                                    </td>
                                    <td class="text-end">
                                        <strong>
                                            $ <span t-esc="'%.2f' % (doc.proposal_trip_total * (1.16 - (0.04 if doc.partner_invoice_id.is_company else 0)))"/>
                                        </strong>
                                    </td>
                                </tr>
                                <!-- Propuesta C — Precio Directo -->
                                <tr t-if="doc.direct_price > 0"
                                    t-att-style="'background: #e8f4e8; font-weight: bold;' if doc.selected_proposal == 'direct' else ''">
                                    <td>
                                        C
                                        <span t-if="doc.selected_proposal == 'direct'"
                                              style="color: green;"> ★ Seleccionada</span>
                                    </td>
                                    <td>Precio Directo</td>
                                    <td class="text-end">
                                        $ <span t-esc="'%.2f' % doc.direct_price"/>
                                    </td>
                                    <td class="text-end">
                                        $ <span t-esc="'%.2f' % (doc.direct_price * 0.16)"/>
                                    </td>
                                    <td class="text-end" t-if="doc.partner_invoice_id.is_company">
                                        $ <span t-esc="'%.2f' % (doc.direct_price * 0.04)"/>
                                    </td>
                                    <td class="text-end">
                                        <strong>
                                            $ <span t-esc="'%.2f' % (doc.direct_price * (1.16 - (0.04 if doc.partner_invoice_id.is_company else 0)))"/>
                                        </strong>
                                    </td>
                                </tr>
                            </tbody>
                        </table>

                        <!-- Mercancía simplificada (si hay) -->
                        <div t-if="doc.line_ids" class="row mb-4">
                            <div class="col-12">
                                <h4 style="border-bottom: 2px solid #e1a13e; padding-bottom: 4px;">
                                    Carga a Transportar
                                </h4>
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>Descripción</th>
                                            <th class="text-end">Cantidad</th>
                                            <th class="text-end">Peso (kg)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <t t-foreach="doc.line_ids" t-as="line">
                                            <tr>
                                                <td><span t-field="line.description"/></td>
                                                <td class="text-end">
                                                    <span t-field="line.quantity"/>
                                                </td>
                                                <td class="text-end">
                                                    <span t-field="line.weight_kg"/>
                                                </td>
                                            </tr>
                                        </t>
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- Notas legales -->
                        <div class="row mt-4"
                             style="border-top: 1px solid #ccc; padding-top: 12px;">
                            <div class="col-12" style="font-size: 10px; color: #888;">
                                <p>
                                    <strong>Nota:</strong> Esta pre-cotización es un documento
                                    comercial informativo. No constituye un CFDI ni tiene
                                    validez fiscal. Los precios pueden variar según condiciones
                                    de mercado. Vigencia: 15 días a partir de la fecha de emisión.
                                </p>
                                <p>
                                    <strong>Condiciones:</strong> Precios en MXN.
                                    IVA 16% incluido. Retención IVA 4% aplica solo a personas morales.
                                    Casetas calculadas con sistema de telepeaje (TAG).
                                </p>
                            </div>
                        </div>

                    </div>
                </t>
            </t>
        </t>
    </template>
</odoo>
```

---

## PASO 3 — Template de Email

### Archivo: `data/mail_template_cotizacion.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <record id="mail_template_tms_cotizacion" model="mail.template">
        <field name="name">TMS - Pre-cotización de Flete</field>
        <field name="model_id" ref="model_tms_cotizacion_wizard"/>
        <field name="subject">Pre-cotización de Flete — {{ object.partner_invoice_id.name or 'Cliente' }}</field>
        <field name="email_from">{{ (object.env.company.email or user.email) }}</field>
        <field name="email_to">{{ object.partner_invoice_id.email or '' }}</field>
        <field name="body_html"><![CDATA[
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: #035d96; color: white; padding: 20px; text-align: center;">
        <h2 style="margin: 0;">Pre-cotización de Flete</h2>
    </div>
    <div style="padding: 20px;">
        <p>Estimado/a <strong>{{ object.partner_invoice_id.name or 'Cliente' }}</strong>,</p>
        <p>Le compartimos la cotización del servicio de transporte solicitado:</p>

        <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
            <tr style="background: #f0f5fa;">
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Origen (CP):</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{{ object.origin_zip or '-' }}</td>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Destino (CP):</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{{ object.dest_zip or '-' }}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Distancia:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{{ '%.1f' % object.distance_km }} km</td>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Tiempo est.:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{{ '%.1f' % object.duration_hours }} hrs</td>
            </tr>
        </table>

        <p>Adjuntamos el detalle completo de las propuestas en PDF.</p>
        <p>Quedamos a sus órdenes para cualquier duda.</p>

        <p style="margin-top: 24px;">
            <strong>{{ object.env.company.name or 'Empresa' }}</strong><br/>
            {{ object.env.company.phone or '' }}<br/>
            {{ object.env.company.email or '' }}
        </p>
    </div>
    <div style="background: #e1a13e; padding: 8px; text-align: center; font-size: 12px;">
        <span style="color: #333;">Cotización comercial — No es un CFDI</span>
    </div>
</div>
        ]]></field>
        <field name="report_template_ids"
               eval="[(4, ref('action_report_tms_cotizacion'))]"/>
        <field name="auto_delete" eval="False"/>
    </record>
</odoo>
```

---

## PASO 4 — Métodos en wizard/tms_cotizacion_wizard.py

⚠️ **ANTES de agregar métodos, verificar que no existen:**
```bash
grep -n "def action_send_email\|def action_download_pdf\|def action_enviar\|def action_descargar" wizard/tms_cotizacion_wizard.py
```

Agregar estos dos métodos al modelo `tms.cotizacion.wizard`:

```python
def action_download_pdf(self):
    """
    Genera y descarga el PDF de pre-cotización.
    No es un CFDI — es un documento comercial.
    """
    self.ensure_one()
    return self.env.ref('tms.action_report_tms_cotizacion').report_action(self)

def action_send_email(self):
    """
    Envía la pre-cotización por email al cliente.
    Adjunta el PDF automáticamente via el mail.template.
    Abre el composer para que el usuario pueda editar antes de enviar.
    """
    self.ensure_one()
    # Verificar que el cliente tiene email
    if not self.partner_invoice_id.email:
        raise UserError(
            'El cliente no tiene email configurado. '
            'Agrega un email al contacto antes de enviar la cotización.'
        )
    template = self.env.ref('tms.mail_template_tms_cotizacion', raise_if_not_found=False)
    if not template:
        raise UserError('No se encontró la plantilla de email para cotización.')
    # Abrir el mail composer con la plantilla pre-llenada
    return {
        'type': 'ir.actions.act_window',
        'res_model': 'mail.compose.message',
        'view_mode': 'form',
        'target': 'new',
        'context': {
            'default_model': 'tms.cotizacion.wizard',
            'default_res_ids': self.ids,
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'force_email': True,
        },
    }
```

⚠️ Asegurarse de importar `UserError` al inicio del archivo si no está:
```bash
grep -n "from odoo.exceptions import" wizard/tms_cotizacion_wizard.py
```
Si no incluye `UserError`, agregar:
```python
from odoo.exceptions import UserError, ValidationError
```

---

## PASO 5 — Agregar botones en la vista del wizard

### Archivo: `wizard/tms_cotizacion_wizard_views.xml`

Buscar la sección del Paso 1 donde aparecen los resultados de las propuestas (después de calcular). Agregar botones **después** de la tabla de propuestas, **antes** del botón "Siguiente":

```xml
<!-- Botones de envío — solo visibles cuando ya se calculó -->
<div class="text-center mt-3" invisible="distance_km == 0">
    <button string="📄 Descargar PDF"
            type="object"
            name="action_download_pdf"
            class="btn-secondary me-2"
            icon="fa-file-pdf-o"/>
    <button string="📧 Enviar por Email"
            type="object"
            name="action_send_email"
            class="btn-primary"
            icon="fa-envelope"/>
</div>
```

⚠️ **Verificar el campo correcto para el invisible:**
```bash
grep -n "distance_km\|proposal_km_total\|toll_cost" wizard/tms_cotizacion_wizard_views.xml | head -10
```
Si el campo que indica "ya se calculó" es diferente a `distance_km`, ajustar el `invisible` correspondientemente.

---

## PASO 6 — Actualizar __manifest__.py

Agregar los archivos nuevos en la lista `data` (respetar orden — reports antes de data):

```python
# En la lista 'data' del __manifest__.py agregar:
'report/tms_cotizacion_report.xml',
'report/tms_cotizacion_report_template.xml',
'data/mail_template_cotizacion.xml',
```

⚠️ El template de email referencia al reporte (`ref('action_report_tms_cotizacion')`), así que los archivos de `report/` DEBEN ir ANTES que `data/` en la lista del manifest.

---

## ACCEPTANCE CRITERIA

| ID | Criterio | Verificación |
|---|---|---|
| AC-01 | Botón "Descargar PDF" genera PDF correcto | Crear cotización → calcular → click PDF → se descarga |
| AC-02 | PDF muestra logo de empresa | Verificar que el header del PDF tiene logo |
| AC-03 | PDF muestra las 3 propuestas con precios | Verificar tabla con propuestas A, B, C |
| AC-04 | PDF marca propuesta seleccionada con ★ | Seleccionar propuesta → descargar → verificar marca |
| AC-05 | Retención 4% solo aparece si cliente es persona moral | Probar con is_company=True y False |
| AC-06 | Botón "Enviar por Email" abre composer | Click → se abre ventana de email con template |
| AC-07 | Email incluye PDF adjunto | Verificar que el composer tiene el PDF adjunto |
| AC-08 | Email tiene datos del cliente pre-llenados | Verificar destinatario y asunto |
| AC-09 | Error si cliente no tiene email | Probar con cliente sin email → debe mostrar UserError |
| AC-10 | Botones no aparecen si no se ha calculado | Abrir wizard → botones invisibles → calcular → botones visibles |
| AC-11 | No hay errores en log al actualizar módulo | `grep -n "WARNING\|ERROR" odoo.log \| tail -20` |

---

## QA — Validación

```bash
# Compilar Python (solo el archivo modificado)
python3 -m py_compile wizard/tms_cotizacion_wizard.py

# Verificar que no hay XML mal formado
python3 -c "
import xml.etree.ElementTree as ET
for f in ['report/tms_cotizacion_report.xml',
          'report/tms_cotizacion_report_template.xml',
          'data/mail_template_cotizacion.xml']:
    ET.parse(f)
    print(f'{f} — XML válido')
"

# Update módulo
python3 odoo-bin -c odoo.conf -u tms -d tms_dev --stop-after-init

# Verificar logs
grep -n "WARNING\|ERROR" odoo.log | tail -20
```

---

## COMMIT — Solo commit, NO push

```bash
git add -A
git commit -m "feat(2.1.6): PDF pre-cotización + envío email con las 3 propuestas"
```

⚠️ **NO ejecutar git push — Mois lo hace manualmente.**

## Actualizar CLAUDE.md

Marcar etapa 2.1.6 como ✅ en la sección de roadmap.

---

*FIN DEL SDD — Etapa 2.1.6*
