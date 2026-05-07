# STATUS.md — TMS Hombre Camión

> Actualizado por Claude Web con cada `/status`, `/archive` y `/ff`.
> Última actualización: **2026-05-07** — V2.6 Portal Web Cliente completado

---

## 🏷️ Versión actual

| Campo | Valor |
|-------|-------|
| Versión módulo | `19.0.2.6.0` |
| Rama activa | `main` — limpia |
| Progreso global | ~90% |
| BD local | `tms_v2` · `localhost:8019` |

---

## 🎯 Feature activo

Ninguno — main limpio. Completado: V2.6 Portal Web Cliente.

---

## ✅ Completado

| Versión | Nombre | Fecha |
|---------|--------|-------|
| V1.0 | Base funcional | ✅ |
| V2.0 (9/9) | Estabilización | ✅ |
| V2.1 (11/11) | Pulido UX + onboarding + PDF cotización | ✅ |
| V2.2 | Carta Porte 3.1 + Timbrado (UUID obtenido) | ✅ |
| V2.2.1 | PDF Carta Porte timbrada (7 secciones + QR) | ✅ |
| V2.2.2 | Wizard validación pre-timbrado (20 checks) | ✅ 2026-03-23 |
| V2.3 | CFDI Ingreso — facturación real | ✅ 2026-04-15 |
| V2.3.2 | Cancelación CFDI Traslado (motivos 01/02/03) | ✅ 2026-04-22 |
| V2.4.1 | Rentabilidad por ruta (`tms.route.stats`) | ✅ 2026-04-22 |
| V2.4.2 | Dashboard operativo + KPIs tiempo real | ✅ 2026-04-23 |
| V2.4.3 | Rendimiento por vehículo (`tms.vehicle.performance`) | ✅ 2026-05-06 |
| V2.4b | Evidencia fotográfica (`tms.evidence.photo`) | ✅ 2026-05-06 |
| V2.4c | Firma digital portal | ✅ 2026-05-06 (ya existía) |
| V2.4d | Liquidación de choferes (`tms.liquidacion`) | ✅ 2026-05-06 (ya existía) |
| V2.5 | Menús limpios + data integrity | ✅ 2026-04-28 |
| V2.5.1 | Tour Guide Interactivo (8 micro-tours + panel ❓) | ✅ 2026-05-06 |
| V2.6 | Portal Web Cliente (tracking, XML, historial) | ✅ 2026-05-07 |

---

## 📋 Pendiente — en orden de prioridad

| Prioridad | Versión | Nombre | Qué es | Modelo |
|-----------|---------|--------|--------|--------|
| 🔜 1 | V2.7 | Limpieza Final + QA | 0 warnings, semillas Fase 2, QA < 10 min primer CP | `claude-sonnet-4-6` |
| 🎯 2 | **V2.8** | **SaaS — PRIMER CLIENTE** | Multi-tenant, MercadoPago, self-service onboarding | `claude-opus-4-7` |
| 🚀 3 | **V3.0** | **App Flutter Chofer** | Ver viaje asignado, iniciar ruta, foto entrega, liquidación | Flutter/Dart |
| 🔮 4 | Fase 2 | Marketplace de Cargas | Matching engine, API REST, portal embarcador | Sep-Dic 2026 |
| 🔮 5 | Fase 3 | Datos y Escala | Analytics mercado, ML matching, API brokers | 2027 |

---

## 📱 V3.0 — App Flutter Chofer (detalle)

**Stack:** Flutter, Dart, Riverpod, API REST Odoo
**Propósito:** App móvil para el chofer — independiente de Odoo Web

**Funcionalidades:**
- Ver viaje asignado (ruta, cliente, mercancía)
- Botones: Iniciar Ruta → Llegada a Destino
- Subir foto de entrega (evidencia)
- Ver su liquidación (anticipos, gastos, saldo)
- Notificaciones push de nuevos viajes

**Prerequisito:** V2.8 en producción — la app consume la API REST de Odoo

---

## 🌱 Deuda técnica

| Campo | Modelo | Riesgo |
|-------|--------|--------|
| `current_zip` | `fleet.vehicle` | 🟢 Baja — Fase 2 |
| `vehicle_status` | `fleet.vehicle` | 🟡 Media — no activar sin implementar |
| `is_tms_carrier` | `res.partner` | 🟢 Baja — marketplace |

---

## ⚙️ Próxima decisión

**V2.7** (limpieza Final + QA, 1 sesión) → **V2.8** (SaaS — PRIMER CLIENTE PAGA) → **V3.0** (App Flutter Chofer)
