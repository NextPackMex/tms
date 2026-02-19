# ✅ COTIZADOR DE FLETES IMPLEMENTADO

## 🎉 Estado Actual

El Cotizador de Fletes está **INTEGRADO DIRECTAMENTE** en el modelo `tms.waybill` (Viaje / Carta Porte).

> **NOTA IMPORTANTE**: Los archivos `tms_quotation.py` y `tms_quotation_line.py` mencionados en documentación anterior **NO EXISTEN**. La funcionalidad de cotización está fusionada en el documento único `tms.waybill`.

---

## 📦 ARQUITECTURA ACTUAL

### Modelo Principal: `tms.waybill`

**Archivo:** `models/tms_waybill.py`

El modelo implementa un **SINGLE DOCUMENT FLOW** que fusiona:

- ✅ Cotización (propuestas de precio)
- ✅ Operación (asignación de vehículos/choferes)
- ✅ Carta Porte (cumplimiento fiscal)

---

## 🔄 WORKFLOW (Estados Reales)

| Estado            | Clave        | Descripción                         |
| ----------------- | ------------ | ----------------------------------- |
| Solicitud         | `draft`      | Cotización inicial / borrador       |
| En Pedido         | `en_pedido`  | Pedido confirmado por cliente       |
| Por Asignar       | `assigned`   | Confirmada, asignar vehículo/chofer |
| Carta Porte Lista | `waybill`    | CP lista para timbrar               |
| En Trayecto       | `in_transit` | Chofer en camino                    |
| En Destino        | `arrived`    | Entregado                           |
| Facturado/Cerrado | `closed`     | Cerrado y facturado                 |
| Cancelado         | `cancel`     | Anulado                             |
| Rechazado         | `rejected`   | Rechazado desde portal              |

---

## 💰 SISTEMA DE 3 PROPUESTAS

Integrado en `tms.waybill`:

### Propuesta 1: Por Kilómetro

```
Total = (Distancia + Km Extras) × Precio/KM
```

Campos: `price_per_km`, `distance_km`, `extra_distance_km`, `proposal_km_total`

### Propuesta 2: Por Viaje (Costo + Margen)

```
Costo Diesel = (Distancia / Rendimiento) × Precio Diesel
Total = (Costo Total) × (1 + Margen%)
```

Campos: `profit_margin_percent`, `cost_diesel_total`, `proposal_trip_total`

### Propuesta 3: Precio Directo

```
Total = Monto ingresado manualmente
```

Campo: `proposal_direct_amount`

Selector: `selected_proposal` → determina cuál propuesta se aplica a `amount_untaxed`

---

## 📋 ARCHIVOS RELEVANTES

| Archivo                       | Propósito                                |
| ----------------------------- | ---------------------------------------- |
| `models/tms_waybill.py`       | Modelo principal con cotizador integrado |
| `models/tms_waybill_line.py`  | Líneas de mercancías                     |
| `views/tms_waybill_views.xml` | Formulario con pestañas de cotización    |
| `tests/test_tms_waybill.py`   | Pruebas automatizadas del workflow       |

---

**Última actualización:** 2026-01-26 - Normalización workflow (Etapa 6.A)
