# CHECKLIST.md — V2.5.1 Tour Guide TMS

Rama: feat/v2.5.1-tour-guide (ya creada)
Modelo Claude Code: claude-sonnet-4-6

---

## [ ] 0. Preparación

- [ ] Confirmar que estás en rama feat/v2.5.1-tour-guide
- [ ] Leer DESIGN.md completo antes de tocar cualquier archivo
- [ ] Verificar API startTour: `odoo.startTour(tourName)` ✅ confirmado
- [ ] Verificar selectores de menús en tms_menus.xml ✅ confirmado
- [ ] Verificar que los archivos nuevos NO existen aún:
  ```bash
  ls static/src/js/tms_help_panel.js 2>&1   # debe decir "No such file"
  ls static/src/xml/tms_help_panel.xml 2>&1
  ls static/src/css/tms_help_panel.css 2>&1
  ```

---

## [ ] 1. Banners informativos en el onboarding wizard

Archivo: `wizard/tms_onboarding_wizard_views.xml`

- [ ] Agregar banner azul (alert-info) en Paso 1 — Empresa
      Texto: RFC, razón social y CP fiscal. Van en todas las facturas.
- [ ] Agregar banner amarillo (alert-warning) en Paso 2 — CSD
      Texto: necesitas .cer + .key + contraseña. Sin ellos no puedes timbrar.
      Incluir: "Los obtienes en sat.gob.mx → CertiSAT Web"
- [ ] Agregar banner azul en Paso 3 — Vehículo
      Texto: placas + Configuración SAT (ej. T3S2) + datos de seguro
- [ ] Agregar banner azul en Paso 4 — Chofer
      Texto: RFC + CURP + número de Licencia Federal vigente
- [ ] Agregar banner azul en Paso 5 — Cliente
      Texto: RFC obligatorio para la factura, régimen fiscal, uso CFDI
- [ ] NO modificar el Paso 6 — ya tiene alert-success correcto
- [ ] Verificar que los banners usan `invisible="step != N"` igual que el resto

---

## [ ] 2. Modificar action_create_first_trip en el wizard

Archivo: `wizard/tms_onboarding_wizard.py`

- [ ] Agregar guard: si el tour ya fue visto (config_parameter), no relanzar
      ```python
      ya_visto = self.env['ir.config_parameter'].sudo().get_param(
          'tms.onboarding_completed_%s' % self.env.company.id
      )
      ```
- [ ] Guardar flag de completado:
      ```python
      self.env['ir.config_parameter'].sudo().set_param(
          'tms.onboarding_completed_%s' % self.env.company.id, '1'
      )
      ```
- [ ] Retornar ir.actions.client con tag 'tms_launch_tour':
      ```python
      return {
          'type': 'ir.actions.client',
          'tag': 'tms_launch_tour',
          'params': {'tour_name': 'tms_tour_carta_porte'},
      }
      ```
- [ ] Docstring en español explicando la lógica

---

## [ ] 3. Reescribir tms_tour.js

Archivo: `static/src/js/tms_tour.js`
Acción: REEMPLAZAR contenido completo (el actual está desactualizado)

### 3.1 Handler de ir.actions.client
- [ ] Registrar en `registry.category("actions")` el tag `tms_launch_tour`
- [ ] Usar setTimeout de 500ms para esperar que el modal se cierre
- [ ] Llamar `odoo.startTour(params.tour_name)`

### 3.2 Tour principal: tms_tour_carta_porte (9 pasos)
- [ ] Paso 1: trigger en botón Nueva Cotización en lista waybill
- [ ] Paso 2: tooltip en campo origin_zip
- [ ] Paso 3: tooltip en campo dest_zip
- [ ] Paso 4: click en button[name="action_compute_route_smart"]
- [ ] Paso 5: tooltip en selected_proposal
- [ ] Paso 6: click en botón Siguiente del wizard
- [ ] Paso 7: click en botón Crear Viaje
- [ ] Paso 8: tooltip en button[name="action_stamp_cfdi"]
- [ ] Paso 9: tooltip en campo cfdi_uuid cuando aparece
- [ ] NINGÚN paso referencia: action_set_en_pedido, draft, en_pedido, assigned

### 3.3 Micro-tour: tms_micro_empresa (3 pasos)
- [ ] Navegación a Configuración → Mi Empresa
- [ ] Tooltip sobre campo vat (RFC)

### 3.4 Micro-tour: tms_micro_csd (4 pasos)
- [ ] Navegación a Configuración → Ajustes
- [ ] Tooltip sobre sección CSD (tms_csd_cer o similar)
- [ ] Tooltip final con instrucción sat.gob.mx

### 3.5 Micro-tour: tms_micro_vehiculos (3 pasos)
- [ ] Navegación a Operaciones → Vehículos
- [ ] Tooltip en lista con botón agregar

### 3.6 Micro-tour: tms_micro_choferes (3 pasos)
- [ ] Navegación a Operaciones → Operadores
- [ ] Tooltip en lista

### 3.7 Micro-tour: tms_micro_cotizacion (4 pasos)
- [ ] Navegación a Viajes → Nueva Cotización
- [ ] Tooltip en wizard paso 1

### 3.8 Micro-tour: tms_micro_factura (4 pasos)
- [ ] Navegación a Viajes
- [ ] Tooltip en button[name="action_create_invoice"]

### 3.9 Micro-tour: tms_micro_dashboard (4 pasos)
- [ ] Navegación a Viajes (donde está el dashboard)
- [ ] Tooltip en KPIs principales

---

## [ ] 4. Crear componente OWL: tms_help_panel.js

Archivo: `static/src/js/tms_help_panel.js` (NUEVO)

- [ ] Importar Component, useState de OWL
- [ ] Importar registry de @web/core/registry
- [ ] Definir array HELP_TOURS con las 8 preguntas (ver DESIGN.md)
- [ ] Clase TmsHelpPanel extends Component:
  - [ ] Estado: `isOpen = useState({ value: false })`
  - [ ] Método togglePanel(): alterna isOpen
  - [ ] Método launchTour(tourName): cierra panel + llama odoo.startTour()
- [ ] Template: `tms_help_panel` (referencia al XML)
- [ ] Registrar en `registry.category("main_components")`
- [ ] Docstrings en español

---

## [ ] 5. Crear template QWeb: tms_help_panel.xml

Archivo: `static/src/xml/tms_help_panel.xml` (NUEVO)

- [ ] Declarar namespace OWL correcto para Odoo 19
- [ ] Template `tms_help_panel`:
  - [ ] Botón flotante ❓ con clase `tms-help-btn`
  - [ ] Panel condicional `t-if="state.isOpen.value"`
  - [ ] Header con título "❓ ¿En qué necesitas ayuda?"
  - [ ] Loop `t-foreach` sobre HELP_TOURS
  - [ ] Cada item: emoji + pregunta + "Ver cómo →"
  - [ ] Click en item: `t-on-click` → launchTour(tour.tour)

---

## [ ] 6. Crear estilos: tms_help_panel.css

Archivo: `static/src/css/tms_help_panel.css` (NUEVO)

- [ ] Estilos del botón flotante (ver DESIGN.md — color #0057B8)
- [ ] Estilos del panel (320px, border-radius 12px, shadow)
- [ ] Animación slideUp
- [ ] Hover en items
- [ ] z-index 1050 (sobre chatter, bajo modals)
- [ ] bottom: 24px, right: 24px para no tapar el botón de mensajes de Odoo

---

## [ ] 7. Actualizar __manifest__.py

- [ ] Agregar en `web.assets_backend`:
  ```python
  'tms/static/src/js/tms_help_panel.js',
  'tms/static/src/xml/tms_help_panel.xml',
  'tms/static/src/css/tms_help_panel.css',
  ```
- [ ] Verificar que tms_tour.js ya está registrado (no duplicar)

---

## [ ] 8. Validación

### Python
- [ ] `python3 -m py_compile wizard/tms_onboarding_wizard.py`

### Odoo (solo reiniciar — no hay campos nuevos)
```bash
cd /Users/macbookpro/odoo/odoo19ce
odoo-19.0/.venv/bin/python odoo-19.0/odoo-bin \
  -c proyectos/tms/odoo.conf -d tms_v2 --dev reload,qweb,xml,assets
```

### Verificación en navegador (localhost:8019?debug=assets)
- [ ] Botón ❓ visible en esquina inferior derecha
- [ ] Click en ❓ abre panel con 8 preguntas
- [ ] Click en cualquier pregunta cierra panel y lanza tour
- [ ] En consola: `odoo.startTour('tms_tour_carta_porte')` → tour corre
- [ ] En consola: `odoo.startTour('tms_micro_csd')` → navega a Ajustes CSD
- [ ] Abrir wizard onboarding → ver banners informativos en cada paso
- [ ] Paso 6 → "Crear mi primer viaje" → popup se cierra → tour inicia
- [ ] Log limpio: sin errores JS en consola

---

## [ ] 9. Revisión final

- [ ] AC-01 al AC-08 cubiertos ✅
- [ ] Sin estados eliminados en tours (no draft, en_pedido, assigned) ✅
- [ ] Todos los textos en español ✅
- [ ] Botón ❓ no tapa el chatter de Odoo ✅
- [ ] CLAUDE.md actualizado marcando V2.5.1 ✅
- [ ] NO push sin orden de Mois ✅

---

## Notas para Claude Code

**Por qué ir.actions.client y no JS directo:**
Python no puede ejecutar JS directamente. ir.actions.client es el
patrón oficial de Odoo para retornar acciones que ejecutan código JS.

**Por qué setTimeout 500ms:**
El modal necesita tiempo para cerrarse antes de que el tour empiece.
Sin el delay, el tour intenta hacer click en elementos que están
cubiertos por el overlay del modal.

**Si un trigger falla:**
Inspeccionar el HTML real con DevTools. Reportar el selector correcto
antes de seguir. No avanzar con triggers rotos.

**Modelo recomendado:** claude-sonnet-4-6
Si el componente OWL resulta complejo: claude-opus-4-7
