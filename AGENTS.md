# ══════════════════════════════════════════════════════════════

# INSTRUCCIONES DE OPERACIÓN — TMS "Hombre Camión"

# Para: Claude Code Terminal / Claude Web
# ⚠️ Ya NO se usa Antigravity. Ejecutor: Claude Code terminal.

# 🤖 MODELOS DE IA — CUÁNDO USAR CUÁL

| Situación | Modelo |
|-----------|--------|
| Módulo nuevo, etapa completa, API, orquestador | claude-opus-4-7 |
| Bug difícil, refactor tms_waybill.py | claude-opus-4-7 |
| Fix puntual, un solo archivo | claude-sonnet-4-6 |
| Vista XML, label, color, fix línea | claude-sonnet-4-6 |
| Commits, limpieza, documentación | claude-haiku-4-5 |

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

4. NUNCA crees modelo nuevo si puedes extender uno nativo con _inherit.

5. NUNCA pongas company_id en catálogos SAT (son globales, compartidos entre empresas).

6. SIEMPRE pon company_id obligatorio en modelos operativos (waybill, destination, etc.)

7. SIEMPRE usa check_company=True en Many2one a modelos con company_id.

8. SIEMPRE valida que el módulo actualice sin errores antes de dar por terminado:
   python3 odoo-bin -c odoo.conf -u tms -d tms_v2 --stop-after-init

9. Los estados del workflow son EXACTAMENTE estos (no inventar otros):
   cotizado, aprobado, waybill, in_transit, arrived, closed, cancel, rejected
   ⚠️ NUNCA usar: draft, en_pedido, assigned, transit, destination, carta_porte

10. SIEMPRE busca XML IDs existentes antes de crear vistas nuevas:
    grep -rn "record id=" views/

# ══════════════════════════════════════════════════════════════
# ⚠️ ERRORES COMUNES ODOO 19 — NUNCA REPETIR
# ══════════════════════════════════════════════════════════════

## Vistas Lista y view_mode

❌ MAL en vistas: `<tree>`
✅ BIEN en vistas: `<list>`

❌ MAL en ir.actions.act_window — causa "View types not defined tree":
```xml
<field name="view_mode">kanban,tree,form</field>
```
✅ BIEN en ir.actions.act_window:
```xml
<field name="view_mode">kanban,list,form</field>
```

⚠️ REGLA: Cada vez que escribas un ir.actions.act_window, verifica que
view_mode NO contenga "tree". Siempre usar "list".

## Vistas Kanban — template obligatorio

❌ MAL — Odoo 16 y anteriores:
```xml
<templates>
    <t t-name="kanban-box">...</t>
</templates>
```
✅ BIEN — Odoo 19 obligatorio:
```xml
<templates>
    <t t-name="card">...</t>
</templates>
```

## Imágenes en Kanban

❌ MAL — kanban_image() no existe en Odoo 19:
```xml
<img t-att-src="kanban_image('model', 'field', record.id.value)"/>
```
✅ BIEN — usar widget="image":
```xml
<field name="photo" widget="image" options="{'size': [100, 100]}"/>
```

## Atributos condicionales en vistas

❌ MAL: `attrs="{'invisible': [('state', '=', 'cancel')]}"`
✅ BIEN: `invisible="state == 'cancel'"`

## name_get()

❌ MAL: `def name_get(self): ...`
✅ BIEN: `full_name = fields.Char(compute='_compute_full_name', store=True)` + `_rec_name = 'full_name'`

## Métodos RPC desde OWL

❌ MAL: `def _get_dashboard_data(self):` (métodos privados bloqueados)
✅ BIEN: `def get_dashboard_data(self):` (nombre público)

## Selection → Char mismo nombre

❌ MAL: Renombrar fields.Selection a fields.Char con mismo field name
✅ BIEN: Usar Many2one + actualizar referencias.

## t-esc en QWeb

❌ MAL: `<span t-esc="value"/>`
✅ BIEN: `<span t-out="value"/>`

## _sql_constraints

❌ MAL: `_sql_constraints = [('name_uniq', 'unique(name)', 'Ya existe')]`
✅ BIEN: `models.Constraint('unique(name)', 'Ya existe')`

## name_search

❌ MAL: `def name_search(self, name='', ...)`
✅ BIEN: `_rec_names_search = ['code', 'name', 'full_name']`

# ══════════════════════════════════════════════════════════════

# ARQUITECTURA CLAVE

## Modelo Maestro: tms.waybill

Single Document Flow: Cotización + Operación + Carta Porte en UN solo registro.
Archivo: models/tms_waybill.py

## Workflow:

cotizado → aprobado → waybill → in_transit → arrived → closed
                                                           ↓
                                                         cancel
rejected (portal)

## Modelos SIN company_id (globales):

tms.sat.clave.prod, tms.sat.clave.unidad, tms.sat.codigo.postal,
tms.sat.colonia, tms.sat.localidad, tms.sat.municipio,
tms.sat.config.autotransporte, tms.sat.tipo.permiso, tms.sat.embalaje,
tms.sat.material.peligroso, tms.sat.figura.transporte, tms.sat.regimen.fiscal

## Modelos CON company_id (privados):

tms.waybill, tms.waybill.line, tms.destination, fleet.vehicle,
tms.fuel.history, tms.tracking.event, tms.evidence.photo,
tms.route.stats, tms.vehicle.performance

## Modelos heredados (_inherit):

fleet.vehicle → tms_fleet_vehicle.py
hr.employee → hr_employee.py
res.partner → res_partner_tms.py
res.company → res_company.py
res.config.settings → res_config_settings.py
account.move → account_move_tms.py

# ESTRUCTURA DE ARCHIVOS

tms/
├── models/          # Lógica Python
├── views/           # Vistas XML
├── wizard/          # Wizards
├── controllers/     # Portal web
├── security/        # Grupos, Record Rules, ACLs
├── data/            # Secuencias, templates email, catálogos CSV
├── reports/         # PDF QWeb
├── demo/            # Datos demo
└── static/          # JS, CSS, XML OWL

# SEGURIDAD (3 grupos principales)

group_tms_user   → Operador (CRUD sin delete waybill)
group_tms_manager → Admin (CRUD completo)
group_tms_driver  → Chofer (lectura + tracking)

# DEPENDENCIAS

base, fleet, account, contacts, board, mail, portal, web, website,
sale_management, hr, web_tour

# MOTOR DE COTIZACIÓN (3 Propuestas en tms.waybill)

A) Por KM: (distancia + km_extras) × precio_km
B) Por Viaje: costo_total / (1 - margen%)
C) Directo: monto manual
selected_proposal determina cuál se aplica.
Impuestos: IVA 16%, Retención 4% solo si receptor is_company=True.

# CÓMO VALIDAR TU TRABAJO

1. Sintaxis Python: python3 -m py_compile models/archivo.py
2. Actualizar módulo:
   cd /Users/macbookpro/odoo/odoo19ce
   odoo-19.0/.venv/bin/python odoo-19.0/odoo-bin -c proyectos/tms/odoo.conf -u tms -d tms_v2 --stop-after-init
3. Revisar logs: grep -n "WARNING\|ERROR" proyectos/tms/odoo.log | tail -20
4. Cambios solo JS/XML: usar --dev reload,qweb,xml,assets

# ══════════════════════════════════════════════════════════════
# REGLA PORTAL / FRONTEND — LEER ODOO CORE PRIMERO
# ══════════════════════════════════════════════════════════════

Si un tile, template o componente del portal/website no cuadra visualmente
o no funciona correctamente, IR DIRECTO a leer el patrón en Odoo core
antes de intentar cualquier fix. NO inventar HTML o Bootstrap custom.

Rutas de referencia:
  odoo-19.0/addons/{módulo}/views/*portal*.xml
  odoo-19.0/addons/{módulo}/controllers/portal.py

Ejemplos de patrones nativos que Odoo ya tiene resueltos:
  - portal_docs_entry     → tiles del home /my
  - placeholder_count     → lazy load de contadores (evita spinner infinito)
  - portal_client_category_enable → activa la sección de tiles del cliente
  - portal.portal_layout  → layout base del portal
  - portal.portal_table   → tabla paginada estándar

Esta regla aplica a cualquier componente frontend, no solo al portal.

# CONVENCIONES DE CÓDIGO

- Docstrings y comentarios en ESPAÑOL
- _name, _description, _order en cada modelo nuevo
- index=True en campos de búsqueda frecuente
- tracking=True en campos de auditoría
- Odoo 19: models.Constraint() en vez de _sql_constraints
- Odoo 19: _rec_names_search en vez de name_search override
- Odoo 19: t-out en vez de t-esc en QWeb
- Odoo 19: <list> en vez de <tree>
- Odoo 19: invisible= en vez de attrs=
- Odoo 19: view_mode usa "list" nunca "tree"
