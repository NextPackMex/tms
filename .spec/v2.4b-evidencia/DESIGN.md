# DESIGN.md — V2.4b Evidencia Fotográfica

## Modelos afectados

| Modelo | Acción | Archivo |
|--------|--------|---------|
| tms.evidence.photo | Crear | models/tms_evidence.py |
| tms.waybill | _inherit — smart button + pestaña | models/tms_waybill.py |

## Campos nuevos — tms.evidence.photo

| Campo | Tipo | Descripción | Requerido |
|-------|------|-------------|-----------|
| waybill_id | Many2one(tms.waybill) | Viaje relacionado | Sí |
| photo | Binary | Imagen en base64 | Sí |
| photo_filename | Char | Nombre del archivo | No |
| photo_type | Selection | Tipo de evidencia | Sí |
| date | Datetime | Fecha/hora automática | Sí |
| user_id | Many2one(res.users) | Usuario que subió | Sí |
| notes | Text | Observaciones opcionales | No |
| company_id | Many2one(res.company) | Empresa (related waybill) | Sí |

### Selection photo_type:
```python
[
    ('salida_origen', 'Salida de Origen'),
    ('carga_origen', 'Carga en Origen'),
    ('entrega_destino', 'Entrega en Destino'),
    ('odometro', 'Odómetro'),
    ('incidente', 'Incidente'),
    ('otro', 'Otro'),
]
```

## Campos nuevos en tms.waybill

| Campo | Tipo | Descripción |
|-------|------|-------------|
| evidence_ids | One2many(tms.evidence.photo) | Evidencias del viaje |
| evidence_count | Integer (compute) | Contador para smart button |

## Vistas

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| views/tms_evidence_views.xml | Crear | Vista list + form de evidencias |
| views/tms_waybill_views.xml | Modificar | Pestaña Evidencias + smart button |

### Smart button en waybill:
```xml
<button name="action_view_evidences"
        type="object"
        class="oe_stat_button"
        icon="fa-camera"
        invisible="evidence_count == 0">
    <field name="evidence_count" widget="statinfo" string="Evidencias"/>
</button>
```

### Pestaña en waybill (al final, antes de Tracking):
```xml
<page string="Evidencias 📷" name="evidencias">
    <field name="evidence_ids" mode="kanban">
        <!-- kanban con miniatura + tipo + fecha -->
    </field>
</page>
```

## Métodos Python

| Método | Modelo | Descripción |
|--------|--------|-------------|
| _compute_evidence_count | tms.waybill | Cuenta evidencias del viaje |
| action_view_evidences | tms.waybill | Abre vista lista de evidencias |

## Seguridad

```csv
access_tms_evidence_photo_user,tms.evidence.photo.user,model_tms_evidence_photo,tms.group_tms_user,1,1,1,0
access_tms_evidence_photo_manager,tms.evidence.photo.manager,model_tms_evidence_photo,tms.group_tms_manager,1,1,1,1
access_tms_evidence_photo_driver,tms.evidence.photo.driver,model_tms_evidence_photo,tms.group_tms_driver,1,1,1,0
```

## Grep de verificación previa

```bash
grep -rn "tms_evidence\|evidence_ids\|evidence_count" models/
grep -rn "tms.evidence" security/ir.model.access.csv
grep -rn "tms_evidence" __manifest__.py
```

## Decisiones de arquitectura

- `company_id` en `tms.evidence.photo` como `related='waybill_id.company_id', store=True`
  para herencia automática sin campo adicional.
- `photo_filename` para que el widget `binary` muestre nombre del archivo correctamente.
- Vista kanban dentro del waybill (no lista) para mostrar miniaturas de fotos.
- NO usar `required=True` en campos heredados.
