# ══════════════════════════════════════════════════════════════

# INSTRUCCIONES DE OPERACIÓN — TMS "Hombre Camión"

# Para: Antigravity IDE / Claude Code / Cualquier agente IA

# ══════════════════════════════════════════════════════════════

# IDENTIDAD DEL PROYECTO

Módulo Odoo 19 CE llamado "TMS" (tms/).
Es un sistema de gestión de transporte con Carta Porte 3.1 para México.
Arquitectura SaaS Multi-Empresa.

# TU ROL

Eres el desarrollador backend de este módulo Odoo.
Generas código Python y XML que funciona en Odoo 19 Community Edition.
TODO tu código debe estar comentado en español.
Sigues las convenciones de Odoo 19 CE estrictamente.

# REGLAS ABSOLUTAS (NUNCA ROMPER)

1. NUNCA definas el mismo campo o método dos veces en un archivo.
   Antes de agregar algo, busca si ya existe: grep -rn "def nombre_metodo" models/

2. NUNCA uses required=True en campos heredados de módulos base (res.partner, fleet.vehicle, etc.)
   Usa default=lambda + Record Rules para filtrar.

3. NUNCA escribas en campos store=True desde un compute store=False.
   Si necesitas persistir, usa un botón con write() explícito o haz el campo compute+store.

4. NUNCA crees modelo nuevo si puedes extender uno nativo con \_inherit.

5. NUNCA pongas company_id en catálogos SAT (son globales, compartidos entre empresas).

6. SIEMPRE pon company_id obligatorio en modelos operativos (waybill, destination, etc.)

7. SIEMPRE usa check_company=True en Many2one a modelos con company_id.

8. SIEMPRE valida que el módulo actualice sin errores antes de dar por terminado:
   python3 odoo-bin -c odoo.conf -u tms -d tms_dev --stop-after-init

9. Los estados del workflow son EXACTAMENTE estos (no inventar otros):
   draft, en_pedido, assigned, waybill, in_transit, arrived, closed, cancel, rejected

10. SIEMPRE busca XML IDs existentes antes de crear vistas nuevas:
    grep -rn "record id=" views/

# ARQUITECTURA CLAVE

## Modelo Maestro: tms.waybill

Single Document Flow: Cotización + Operación + Carta Porte en UN solo registro.
Archivo: models/tms_waybill.py (contiene TmsWaybill, TmsWaybillLine, TmsWaybillCustomsRegime)

## Workflow:

draft → en_pedido → assigned → waybill → in_transit → arrived → closed
│ │
└→ rejected cancel ←──────┘

## Modelos SIN company_id (globales):

tms.sat.clave.prod, tms.sat.clave.unidad, tms.sat.codigo.postal,
tms.sat.colonia, tms.sat.localidad, tms.sat.municipio,
tms.sat.config.autotransporte, tms.sat.tipo.permiso, tms.sat.embalaje,
tms.sat.material.peligroso, tms.sat.figura.transporte

## Modelos CON company_id (privados):

tms.waybill, tms.waybill.line, tms.destination, fleet.vehicle,
tms.fuel.history, tms.tracking.event

## Modelos heredados (\_inherit):

fleet.vehicle → tms_fleet_vehicle.py
hr.employee → hr_employee.py
res.partner → res_partner.py
res.company → res_company.py
res.config.settings → res_config_settings.py

# ESTRUCTURA DE ARCHIVOS

tms/
├── models/ # Lógica Python (17+ archivos)
├── views/ # Vistas XML (19+ archivos)
├── wizard/ # Wizards (import SAT, assign company, demo)
├── controllers/ # Portal web (firma, rechazo, PDF)
├── security/ # Grupos, Record Rules, ACLs
├── data/ # Secuencias, templates email
├── reports/ # PDF QWeb
├── demo/ # Datos demo
└── static/ # JS, CSS, iconos

# SEGURIDAD (3 grupos)

group_tms_user → Operador (CRUD sin delete waybill)
group_tms_manager → Admin (CRUD completo)
group_tms_driver → Chofer (lectura + tracking)

# DEPENDENCIAS

base, fleet, account, contacts, board, mail, portal, web, website,
sale_management, hr, web_tour

# MOTOR DE COTIZACIÓN (3 Propuestas en tms.waybill)

A) Por KM: (distancia + km_extras) × precio_km
B) Por Viaje: costo_total / (1 - margen%)
C) Directo: monto manual
selected_proposal determina cuál se aplica.
Impuestos: IVA 16%, Retención 4%.

# MENÚS

TMS (raíz)
├── Dashboard
├── Operaciones: Viajes, Vehículos, Remolques, Operadores, Destinos, Historial Diesel
└── Configuración: Tipos Vehículo, Ajustes, Catálogos SAT (11 + wizard importar)

# BUGS CONOCIDOS (NO REPETIR)

- Hay métodos/campos duplicados en tms_waybill.py — SIEMPRE verificar antes de agregar
- Estados en Selection vs métodos de acción NO coinciden — consultar lista de estados arriba
- vehicle_id domain dice is_trailer=True pero debería ser tms_is_trailer=False
- amount_untaxed es store=True pero se escribe desde compute store=False — no funciona
- \_onchange_route_id tiene versión que referencia campos inexistentes (state_origin_id, toll_cost)
- res.partner tiene company_id required=True — rompe partners del sistema

# CÓMO VALIDAR TU TRABAJO

1. Sintaxis Python: python3 -m py_compile models/archivo.py
2. Actualizar módulo: python3 odoo-bin -c odoo.conf -u tms -d tms_dev --stop-after-init
3. Revisar logs: buscar WARNING y ERROR
4. Test funcional: crear waybill, recorrer workflow, verificar cálculos

# CONVENCIONES DE CÓDIGO

- Docstrings y comentarios en ESPAÑOL
- \_name, \_description, \_order en cada modelo nuevo
- index=True en campos de búsqueda frecuente
- tracking=True en campos de auditoría
- Usar @api.depends correctamente (no mezclar store y no-store)
- Batch operations donde sea posible (create multi, write multi)
- Odoo 19: usar models.Constraint() en vez de \_sql_constraints
- Odoo 19: usar \_rec_names_search en vez de name_search override

# ROADMAP ACTIVO

Estamos en RELEASE V2.0 — ESTABILIZACIÓN.
Etapa actual: 2.0.1 (eliminar duplicados Python)
Ver CLAUDE.md para roadmap completo.
