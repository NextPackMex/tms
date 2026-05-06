# PROPOSAL.md — V2.4b Evidencia Fotográfica

Fecha: 2026-05-06
Proyecto: TMS Hombre Camión
Estimación: M
Branch: feat/v2.4b-evidencia

## Problema que resuelve

El operador no tiene forma de registrar evidencia fotográfica de un viaje
(salida, carga, entrega, incidente). Si hay disputa con el cliente o
el chofer sobre el estado de la mercancía, no existe prueba documental
dentro del sistema.

## Solución propuesta

Modelo `tms.evidence.photo` vinculado a `tms.waybill`.
El chofer o el operador sube fotos con un tipo (salida, carga, entrega, etc.)
y el sistema registra timestamp + usuario automáticamente.
Las fotos se muestran en una pestaña dentro del formulario del waybill.

## Alcance IN scope

- Modelo `tms.evidence.photo` con campos: waybill_id, photo, photo_type, date, user_id, notes
- 6 tipos de foto: salida_origen, carga_origen, entrega_destino, odometro, incidente, otro
- Pestaña "Evidencias" en el formulario del waybill
- Vista lista de evidencias por viaje
- Permisos: user puede crear, manager puede eliminar

## Alcance OUT scope

- GPS / coordenadas (requiere app móvil — Fase 2)
- Timestamp inmutable / firma digital (eso es V2.4c)
- Comparativa automática odómetro vs TollGuru (requiere tms.fuel.log — posterior)
- Compresión automática de imágenes

## Impacto técnico

- Nuevo archivo: `models/tms_evidence.py`
- Modificar: `views/tms_waybill_views.xml` — agregar pestaña Evidencias
- Nuevo archivo: `views/tms_evidence_views.xml`
- Modificar: `security/ir.model.access.csv`
- Modificar: `models/__init__.py`
- Modificar: `__manifest__.py`

## Criterio de éxito

Desde el formulario de un waybill, el operador puede subir una foto,
asignarle un tipo y verla en la pestaña Evidencias.
