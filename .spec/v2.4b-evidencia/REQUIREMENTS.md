# REQUIREMENTS.md — V2.4b Evidencia Fotográfica

## Criterios de Aceptación

**AC-01:** Desde el formulario de un waybill existe una pestaña "Evidencias"
visible en todos los estados.

**AC-02:** El operador puede subir una foto, seleccionar el tipo (6 opciones)
y agregar una nota opcional. El sistema registra fecha y usuario automáticamente.

**AC-03:** Las fotos se muestran en vista kanban dentro de la pestaña,
con miniatura, tipo y fecha.

**AC-04:** El usuario TMS puede crear evidencias pero NO eliminarlas.
Solo el manager puede eliminar.

**AC-05:** Un waybill cancelado no permite agregar nuevas evidencias
(campo waybill_id readonly si state == cancel).

**AC-06:** Las evidencias son privadas por empresa (company_id del waybill).

## Casos límite

- Subir foto sin tipo → error de validación
- Waybill en estado cancel → campo photo readonly
- Foto mayor a 5MB → Odoo maneja por defecto con Binary, aceptable
- Sin foto (campo vacío) → no se guarda el registro

## Reglas de negocio

- `date` se genera automáticamente con `default=fields.Datetime.now`
- `user_id` se genera automáticamente con `default=lambda self: self.env.user`
- `company_id` hereda del waybill relacionado
- El contador de evidencias aparece en el smart button del waybill

## Escenarios de testing

1. Crear evidencia con todos los campos → se guarda correctamente
2. Crear evidencia sin foto → UserError o required validation
3. Crear evidencia sin tipo → ValidationError
4. Usuario TMS intenta eliminar → sin botón delete visible
5. Manager elimina evidencia → se elimina correctamente
6. Waybill cancelado → campo photo no editable
7. Contador smart button → muestra número correcto de evidencias
8. Dos waybills distintos → evidencias no se mezclan
