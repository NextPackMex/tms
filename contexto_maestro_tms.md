# 🚛 CONTEXTO MAESTRO — TMS Hombre Camión (NextPackMex)
> **Spec-Driven Development (SDD)** — Documento vivo. Actualizar tras cada etapa completada.
> Última actualización: 2026-03-13 | Versión actual: 2.0.9

---

## 1. IDENTIDAD DEL PROYECTO

| Campo | Valor |
|---|---|
| **Nombre** | TMS Hombre Camión |
| **Repositorio** | github.com/NextPackMex/tms |
| **Tipo** | Módulo Odoo 17/18 CE |
| **Descripción** | Sistema de gestión de transporte para operadores individuales (hombre-camión) en México |
| **Stack** | Python 3.10+, Odoo 17/18 CE, MariaDB, JavaScript, CSS |
| **Rama principal** | `main` (protegida — solo merge vía PR) |
| **Convención de ramas** | `feature/X.X.X-descripcion`, `fix/descripcion` |
| **Convención de commits** | `feat(2.x.x): descripción`, `fix(2.x.x): descripción`, `chore: descripción` |

---

## 2. ROL DEL AGENTE IA

Actúa como un **Desarrollador Backend Senior especializado en Odoo y fiscalidad mexicana (SAT/CFDI)**.

### Reglas obligatorias para todo el código generado:
- ✅ Todo el código en **español** (comentarios, variables, nombres de campos)
- ✅ Comentar **cada función** explicando qué hace y por qué
- ✅ Comentar **líneas no obvias** dentro de los métodos
- ✅ Seguir la estructura de carpetas existente del módulo
- ✅ Usar **MariaDB** como motor de base de datos (no PostgreSQL-specific syntax)
- ✅ Validar siempre con `@api.constrains` los campos críticos de negocio
- ✅ Respetar el sistema de **grupos de seguridad** ya definido en `security/`
- ❌ NO crear archivos de fix/verify en la raíz del repo (limpiar los existentes)
- ❌ NO hacer push directo a `main` — siempre crear rama feature y PR

---

## 3. ARQUITECTURA DEL MÓDULO

### Estructura de carpetas:
```
tms/
├── .agent/rules/          # Reglas del agente IA (AGENTS.md)
├── controllers/           # Controladores HTTP/JSON (API endpoints)
├── data/                  # Datos iniciales (secuencias, configuración)
├── demo/                  # Datos de demostración para desarrollo
├── docs/                  # Documentación técnica del módulo
├── models/                # Modelos ORM (tablas de BD)
├── reports/               # Reportes QWeb (PDF)
├── security/              # Grupos, reglas de acceso, multi-empresa
├── static/                # Assets estáticos (JS, CSS, imágenes)
├── tests/                 # Suite de pruebas unitarias e integración
├── views/                 # Vistas XML (formularios, listas, menús)
├── wizard/                # Asistentes (wizards) para acciones complejas
├── __manifest__.py        # Metadatos del módulo Odoo
└── AGENTS.md              # Contexto persistente para agentes IA
```

### Modelos principales:
| Modelo | Archivo | Descripción |
|---|---|---|
| `tms.waybill` | `models/tms_waybill.py` | Viajes/guías de transporte |
| `tms.expense` | `models/tms_expense.py` | Gastos por viaje |
| `fleet.vehicle` (ext) | (pendiente) | Extensión de vehículos de flota |
| `res.partner` (ext) | (pendiente) | Extensión para choferes |

---

## 4. REGLAS DE NEGOCIO CRÍTICAS

### Workflow de Viajes (`tms.waybill`):
```
Borrador → Confirmado → En Ruta → Entregado
```
- Solo se puede confirmar si tiene: cliente, chofer, vehículo, y al menos un tramo
- La utilidad se calcula automáticamente: `Flete - Total Gastos`
- Los folios son autogenerados via secuencia `ir.sequence`
- Multi-empresa: cada registro pertenece a una sola compañía

### Cálculos financieros:
- `utilidad_neta = flete_total - sum(gastos_ids.monto)`
- `costo_por_km = total_gastos / distancia_km` (si distancia > 0)
- Todos los montos en **MXN (pesos mexicanos)**

### Validaciones obligatorias:
- RFC del cliente: formato válido SAT (personas físicas y morales)
- Placas del vehículo: formato mexicano
- Fechas: fecha_salida debe ser <= fecha_llegada

---

## 5. CONTEXTO FISCAL MEXICANO (SAT)

### Integraciones pendientes / en desarrollo:
- **Carta Porte 3.1** — CFDI de Traslado (Tipo T) con complemento Carta Porte
- **Catálogos SAT** — Ver `CATALOGS_SAT_README.md` para referencia completa
- **Cotizador** — Ver `COTIZADOR_IMPLEMENTADO.md` para lógica implementada

### Reglas SAT críticas:
- Todo viaje con mercancía requiere Carta Porte desde Junio 2022
- El RFC del emisor debe estar en el SAT como transportista
- Los catálogos SAT se actualizan periódicamente — no hardcodear valores

---

## 6. ESTADO ACTUAL DEL PROYECTO

### ✅ Completado (Etapa 2.0.9):
- Módulo base instalable en Odoo 18 CE
- Workflow de viajes (Borrador → Entregado)
- Gestión de gastos por viaje
- Sistema de cotización implementado
- Seguridad multi-empresa y grupos de acceso
- QA final BD limpia + workflow end-to-end verificado
- Catálogos SAT integrados

### 🔄 En progreso / Próximas etapas:
- Integración con `fleet.vehicle` (vehículos de flota)
- Extensión `res.partner` para choferes (licencias, certificados)
- Generación de Carta Porte 3.1 (CFDI tipo T)
- Suite de tests automatizados en `tests/`
- GitHub Actions CI/CD

### 📋 Backlog (no iniciado):
- App móvil para choferes
- Integración con TollGuru (cálculo de casetas) — ver `add_tollguru_methods.py`
- Portal web para clientes
- Reportes avanzados (KPIs de flota)

---

## 7. CONVENCIONES DE CÓDIGO

### Python / Odoo:
```python
# ✅ CORRECTO — nombre de campo en español, comentado
flete_total = fields.Monetary(
    string='Flete Total',
    currency_field='currency_id',
    help='Monto total acordado con el cliente por el servicio de transporte'
)

# ✅ CORRECTO — método comentado
def _calcular_utilidad(self):
    """
    Calcula la utilidad neta del viaje restando los gastos al flete.
    Se ejecuta automáticamente cuando cambian los gastos o el flete.
    """
    for record in self:
        # Sumar todos los gastos asociados al viaje
        total_gastos = sum(record.gasto_ids.mapped('monto'))
        # La utilidad es la diferencia entre lo cobrado y lo gastado
        record.utilidad_neta = record.flete_total - total_gastos
```

### XML (Views):
```xml
<!-- Siempre incluir string descriptivo en español -->
<field name="flete_total" widget="monetary" string="Flete Total"/>
```

### Commits:
```
feat(2.1.0): Agregar integración con fleet.vehicle para gestión de vehículos
fix(2.0.9): Corregir cálculo de utilidad cuando gasto tiene impuesto incluido
chore: Limpiar archivos verify_*.py de la raíz del proyecto
```

---

## 8. CONFIGURACIÓN DE ENTORNO

### Odoo (odoo.conf):
```ini
# Ver odoo.conf en la raíz del repo para configuración completa
# Base de datos: MariaDB/MySQL (no PostgreSQL)
# Ruta del módulo: incluir carpeta padre de tms/ en addons_path
```

### Instalación del módulo:
```bash
# Modo desarrollador: Aplicaciones → Actualizar Lista → buscar "TMS"
# CLI:
python3 odoo-bin -c proyectos/tms/odoo.conf -u tms -d tms_db --stop-after-init
```

---

## 9. ARCHIVOS DE REFERENCIA CLAVE

| Archivo | Propósito |
|---|---|
| `AGENTS.md` | Reglas del agente IA (system prompt del proyecto) |
| `CLAUDE.md` | Contexto adicional para Claude |
| `CATALOGS_SAT_README.md` | Catálogos del SAT integrados |
| `COTIZADOR_IMPLEMENTADO.md` | Documentación del cotizador |
| `FASE_2_COMPLETADA.md` | Resumen de la fase 2 completada |
| `QA_GUIDE.md` | Guía de pruebas de calidad |
| `TMS_STATUS_REPORT.md` | Estado actual detallado del módulo |
| `docs/` | Documentación técnica adicional |
| `tests/` | Suite de pruebas (expandir) |

---

## 10. CÓMO USAR ESTE DOCUMENTO CON CLAUDE

### Al iniciar una nueva sesión de desarrollo, pega esto:
```
Lee el archivo contexto_maestro_tms.md en la raíz del repo.
Ese es tu contexto completo del proyecto.
Tarea: [describe lo que necesitas]
```

### Para nueva funcionalidad, sigue este flujo SDD:
1. **Actualiza la sección 6** (Estado actual) con lo que vas a construir
2. **Pide a Claude** que genere el código siguiendo las reglas de la sección 2
3. **Revisa** que el código siga las convenciones de la sección 7
4. **Crea rama** `feature/X.X.X-descripcion` y abre PR a `main`
5. **Actualiza este archivo** marcando la etapa como completada

---

*Documento generado con asistencia de Claude (Anthropic) — Curso Desarrollo con IA 2026*
