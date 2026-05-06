# STATUS.md — TMS Hombre Camión

> Actualizado por Claude Web con cada `/status`, `/archive` y `/ff`.
> Última actualización: **2026-05-06** — V2.4.3 y V2.5.1 mergeados a main

---

## 🏷️ Versión actual

| Campo | Valor |
|-------|-------|
| Versión módulo | `19.0.2.4.3` |
| Rama activa | `main` — limpia |
| Progreso global | ~82% |
| BD local | `tms_v2` · `localhost:8019` |

---

## 🎯 Feature activo

Ninguno — main limpio. Esperando decisión de siguiente etapa.

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
| V2.5 | Ocultar menús irrelevantes `group_tms_user` | ✅ 2026-04-28 |
| V2.5.1 | Tour Guide Interactivo (8 micro-tours + panel ❓) | ✅ 2026-05-06 |

---

## 📋 Pendiente — en orden de prioridad

| Prioridad | Versión | Nombre | Modelo Claude |
|-----------|---------|--------|---------------|
| 🔜 1 | V2.4b | Evidencia fotográfica (`tms.evidence.photo`) | `claude-sonnet-4-6` |
| 📌 2 | V2.4c | Firma digital simple (`tms_signature/`) | `claude-opus-4-7` |
| 📌 3 | V2.4d | Liquidación de choferes (`tms_settlement/`) | `claude-sonnet-4-6` |
| 📋 4 | V2.6 | KPIs/Reportes + Portal Web Cliente | `claude-opus-4-7` |
| 📋 5 | V2.7 | Limpieza final + verificar semillas | `claude-sonnet-4-6` |
| 🎯 6 | **V2.8** | **SaaS multi-tenant + cobro (PRIMER CLIENTE)** | `claude-opus-4-7` |
| 🔮 — | Fase 2 | Marketplace de cargas | Sep-Dic 2026 |

---

## 🌱 Deuda técnica

| Campo | Modelo | Riesgo |
|-------|--------|--------|
| `current_zip` | `fleet.vehicle` | 🟢 Baja — Fase 2 |
| `vehicle_status` | `fleet.vehicle` | 🟡 Media — no activar sin implementar |
| `is_tms_carrier` | `res.partner` | 🟢 Baja — marketplace |

---

## ⚙️ Próxima decisión

Elegir entre:
- **V2.4b** — Evidencia fotográfica (feature operativo)
- **V2.8** — SaaS multi-tenant (primer cliente paga)
