# STATUS.md — TMS Hombre Camión

> Actualizado por Claude Web con cada `/status`, `/archive` y `/ff`.
> Última actualización: **2026-05-04**

---

## 🏷️ Versión actual

| Campo | Valor |
|-------|-------|
| Versión módulo | `19.0.2.4.3` |
| Rama activa | `feat/v2.4.3-vehicle-performance` ⚠️ pendiente PR |
| Progreso global | ~80% |
| BD local | `tms_v2` · `localhost:8019` |

---

## 🎯 Feature activo

**Ninguno** — estructura Spec-Driven inicializada 2026-05-04, lista para primer `/ff`.

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
| V2.4.3 | Rendimiento por vehículo (`tms.vehicle.performance`) | ✅ 2026-04-29 |
| V2.5 | Ocultar menús irrelevantes `group_tms_user` | ✅ 2026-04-28 |

---

## 📋 Pendiente — en orden de prioridad

| Prioridad | Versión | Nombre | Modelo Claude |
|-----------|---------|--------|---------------|
| 🔜 1 | V2.5.1 | Tour guide interactivo (4 tours Odoo) | `claude-opus-4-7` |
| 📌 2 | V2.4b | Evidencia fotográfica (`tms.evidence.photo`) | `claude-sonnet-4-6` |
| 📌 3 | V2.4c | Firma digital simple (`tms_signature/`) | `claude-opus-4-7` |
| 📌 4 | V2.4d | Liquidación de choferes (`tms_settlement/`) | `claude-sonnet-4-6` |
| 📋 5 | V2.6 | KPIs/Reportes + Portal Web Cliente | `claude-opus-4-7` |
| 📋 6 | V2.7 | Limpieza final + verificar semillas | `claude-sonnet-4-6` |
| 🎯 7 | **V2.8** | **SaaS multi-tenant + cobro (PRIMER CLIENTE)** | `claude-opus-4-7` |
| 🔮 — | Fase 2 | Marketplace de cargas | Sep-Dic 2026 |

---

## 🌱 Deuda técnica

| Campo | Modelo | Riesgo |
|-------|--------|--------|
| `current_zip` | `fleet.vehicle` | 🟢 Baja — Fase 2 |
| `vehicle_status` | `fleet.vehicle` | 🟡 Media — comentario en waybill.py, no activar sin implementar |
| `is_tms_carrier` | `res.partner` | 🟢 Baja — marketplace |

---

## 📦 Features archivados (Spec-Driven)

_(ninguno aún — flujo iniciado 2026-05-04)_

---

## ⚙️ Próximos pasos

1. Mergear `feat/v2.4.3-vehicle-performance` → PR a main (si QA ok)
2. Ejecutar `/ff v2.5.1-tour-guide` para arrancar el tour guide interactivo
