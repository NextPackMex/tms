# DESIGN.md — V2.5.1 Tour Guide TMS

## Auditoría previa (2026-05-04)

### Ya existe: tms_tour.js
- Tour único desactualizado: referencia action_set_en_pedido (eliminado V2.5)
- Acción: reescribir completo

### Ya existe: dependencia web_tour en manifest ✅
### Ya existe: wizard onboarding 6 pasos ✅
### Ya existe: action_create_first_trip() → abre wizard cotización ✅
### No existe: banners en pasos del onboarding
### No existe: panel flotante de ayuda
### No existe: micro-tours por tema

## Restricción crítica
Los tours de Odoo (web_tour) NO funcionan dentro de modals (target: new).
El onboarding wizard corre en un modal → NO se puede usar web_tour ahí.
Solución: usar banners HTML dentro del wizard + lanzar tour DESPUÉS de cerrar.

---

## Componente 1: Banners informativos en onboarding

### Implementación
Agregar un `<div class="alert alert-info">` en cada paso del wizard
con texto explicativo. Ya están usando `invisible="step != N"` para
mostrar/ocultar secciones — los banners siguen el mismo patrón.

### Archivo: wizard/tms_onboarding_wizard_views.xml
Agregar antes de cada `<group invisible="step != N">`:

```xml
<!-- Banner paso 1 -->
<div class="alert alert-info mb-3" invisible="step != 1">
    <strong>📋 ¿Qué necesitas para este paso?</strong><br/>
    Tu <strong>RFC</strong> (12 o 13 caracteres), razón social y
    Código Postal fiscal. Estos datos aparecen en todas tus
    facturas y Cartas Porte ante el SAT.
</div>

<!-- Banner paso 2 -->
<div class="alert alert-warning mb-3" invisible="step != 2">
    <strong>🔐 Certificado de Sello Digital (CSD)</strong><br/>
    Necesitas 2 archivos del SAT: <strong>.cer</strong> (certificado)
    y <strong>.key</strong> (llave privada) + la contraseña.
    Sin estos archivos <strong>no puedes timbrar</strong>.
    Los obtienes en sat.gob.mx → CertiSAT Web.
</div>

<!-- Banner paso 3 -->
<div class="alert alert-info mb-3" invisible="step != 3">
    <strong>🚛 Datos del vehículo para Carta Porte</strong><br/>
    Necesitas: <strong>placas</strong>, <strong>Configuración SAT</strong>
    (ej. T3S2 = Tractocamión 3 ejes + Semirremolque 2 ejes) y
    los datos de tu <strong>póliza de seguro</strong> vigente.
</div>

<!-- Banner paso 4 -->
<div class="alert alert-info mb-3" invisible="step != 4">
    <strong>👤 Datos del chofer para Carta Porte</strong><br/>
    Necesitas su <strong>RFC</strong>, <strong>CURP</strong> y
    número de <strong>Licencia Federal</strong> vigente.
    Sin licencia federal no puedes timbrar Carta Porte.
</div>

<!-- Banner paso 5 -->
<div class="alert alert-info mb-3" invisible="step != 5">
    <strong>👥 Tu primer cliente</strong><br/>
    El <strong>RFC del cliente</strong> es obligatorio para la factura.
    También necesitas su régimen fiscal y uso de CFDI.
    Puedes agregar más clientes después desde Contactos.
</div>

<!-- Banner paso 6 ya existe con alert-success — no modificar -->
```

---

## Componente 2: Tour automático post-onboarding

### Problema técnico
`action_create_first_trip()` retorna `ir.actions.act_window` para abrir
el wizard de cotización. Necesitamos que TAMBIÉN lance el tour, pero:
- No se puede lanzar JS desde Python directamente
- El tour debe correr DESPUÉS de que el popup se cierre

### Solución: ir.actions.client con tag js personalizado

```python
def action_create_first_trip(self):
    """
    Cierra el onboarding, abre wizard de cotización y lanza tour Carta Porte.
    El tour se lanza via ir.actions.client después de que el modal se cierra.
    """
    self.ensure_one()
    # Marcar que el onboarding fue completado (para no relanzar tour en futuros accesos)
    self.env['ir.config_parameter'].sudo().set_param(
        'tms.onboarding_completed_%s' % self.env.company.id, '1'
    )
    return {
        'type': 'ir.actions.client',
        'tag': 'tms_launch_tour',
        'params': {
            'tour_name': 'tms_tour_carta_porte',
        },
    }
```

### Archivo JS: static/src/js/tms_tour.js
Registrar el action client handler:

```javascript
import { registry } from "@web/core/registry";

// Handler para la acción ir.actions.client
registry.category("actions").add("tms_launch_tour", ({ params }) => {
    // Pequeño delay para asegurar que el modal se cerró
    setTimeout(() => {
        odoo.startTour(params.tour_name);
    }, 500);
});
```

---

## Componente 3: Panel flotante de ayuda

### Arquitectura OWL

```
tms_help_panel.js   → Componente OWL TmsHelpPanel
                      Estado: isOpen (boolean)
                      Método: togglePanel()
                      Método: launchTour(tourName)

tms_help_panel.xml  → Template QWeb
                      Botón ❓ circular flotante
                      Panel con 8 preguntas

tms_help_panel.css  → Estilos
                      Posición fixed bottom-right
                      Animación slide-up del panel
```

### Inyección en la UI
En Odoo 19 se usa el registry `main_components` para inyectar
componentes OWL globales en el root de la aplicación:

```javascript
registry.category("main_components").add("TmsHelpPanel", {
    Component: TmsHelpPanel,
});
```

### Las 8 preguntas — estructura de datos
```javascript
const HELP_TOURS = [
    {
        emoji: "🏢",
        question: "¿Dónde configuro mi empresa y RFC?",
        tour: "tms_micro_empresa",
    },
    {
        emoji: "📜",
        question: "¿Dónde subo mis certificados CSD?",
        tour: "tms_micro_csd",
    },
    {
        emoji: "🚛",
        question: "¿Dónde registro mis tractores?",
        tour: "tms_micro_vehiculos",
    },
    {
        emoji: "👤",
        question: "¿Dónde agrego mis choferes?",
        tour: "tms_micro_choferes",
    },
    {
        emoji: "📦",
        question: "¿Cómo creo una cotización?",
        tour: "tms_micro_cotizacion",
    },
    {
        emoji: "📄",
        question: "¿Cómo timbro mi Carta Porte?",
        tour: "tms_tour_carta_porte",
    },
    {
        emoji: "💰",
        question: "¿Cómo genero la factura del viaje?",
        tour: "tms_micro_factura",
    },
    {
        emoji: "📊",
        question: "¿Qué me dice el dashboard?",
        tour: "tms_micro_dashboard",
    },
];
```

---

## Tours — estructura completa

### tms_tour_carta_porte (9 pasos — el principal)
El más importante. Se lanza automáticamente post-onboarding
y también está disponible desde el panel ❓.

| Paso | Trigger | Acción | Tooltip |
|------|---------|--------|---------|
| 1 | `.o_list_button_add` en vista waybill | click | "Aquí creas una nueva cotización" |
| 2 | `.o_field_widget[name="origin_zip"] input` | — | "CP de origen para calcular la ruta" |
| 3 | `.o_field_widget[name="dest_zip"] input` | — | "CP de destino" |
| 4 | `button[name="action_compute_route_smart"]` | click | "TollGuru calcula distancia, tiempo y casetas" |
| 5 | `.o_field_widget[name="selected_proposal"]` | — | "Elige la propuesta que más te convenga" |
| 6 | `button[name="action_next_step"]` | click | "Siguiente: datos del cliente y mercancía" |
| 7 | `button[name="action_create_waybill"]` | click | "Crear el viaje — queda en estado Cotizado" |
| 8 | `button[name="action_stamp_cfdi"]` | — | "Aquí timbras la Carta Porte con el SAT" |
| 9 | `.o_field_widget[name="cfdi_uuid"]` | — | "¡UUID obtenido! Tu Carta Porte está timbrada" |

### 8 micro-tours (3-5 pasos cada uno)
Estructura simplificada — triggers de menú son los más estables:

**tms_micro_empresa** (3 pasos)
1. `[data-menu-xmlid="tms.menu_tms_config"]` → click
2. `[data-menu-xmlid="tms.menu_tms_my_company"]` → click
3. `.o_field_widget[name="vat"]` → tooltip "Tu RFC del SAT"

**tms_micro_csd** (4 pasos)
1. `[data-menu-xmlid="tms.menu_tms_config"]` → click
2. `[data-menu-xmlid="tms.menu_tms_config_settings"]` → click
3. `[name="tms_csd_cer"]` o sección CSD → tooltip
4. Tooltip final explicando dónde obtener el CSD en sat.gob.mx

**tms_micro_vehiculos** (3 pasos)
1. `[data-menu-xmlid="tms.menu_tms_operations"]` → click
2. `[data-menu-xmlid="tms.menu_tms_vehicles"]` → click
3. `.o_list_button_add` → tooltip "Aquí agregas tractocamiones"

**tms_micro_choferes** (3 pasos)
1. `[data-menu-xmlid="tms.menu_tms_operations"]` → click
2. `[data-menu-xmlid="tms.menu_tms_drivers"]` → click
3. `.o_list_button_add` → tooltip "Agrega tus choferes aquí"

**tms_micro_cotizacion** (4 pasos)
1. `[data-menu-xmlid="tms.menu_tms_waybill"]` → click
2. `.o_list_button_add` → tooltip "Botón Nueva Cotización"
3. `button[name="action_compute_route_smart"]` → tooltip
4. `button[name="action_create_waybill"]` → tooltip

**tms_micro_factura** (4 pasos)
1. `[data-menu-xmlid="tms.menu_tms_waybill"]` → click
2. Tooltip en waybill en estado arrived → "Abre un viaje en destino"
3. `button[name="action_create_invoice"]` → tooltip
4. Tooltip resultado → "La factura CFDI Ingreso queda timbrada aquí"

**tms_micro_dashboard** (4 pasos)
1. `[data-menu-xmlid="tms.menu_tms_waybill"]` → click
2. Tooltip KPI viajes activos
3. Tooltip sección rendimiento vehículos
4. Tooltip top rutas

---

## Estilos del panel flotante (tms_help_panel.css)

```css
/* Botón flotante ❓ */
.tms-help-btn {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: #0057B8;   /* color NextPack */
    color: white;
    font-size: 20px;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    z-index: 1050;         /* sobre el chatter, bajo los modals */
    transition: transform 0.2s;
}
.tms-help-btn:hover { transform: scale(1.1); }

/* Panel de preguntas */
.tms-help-panel {
    position: fixed;
    bottom: 84px;
    right: 24px;
    width: 320px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    z-index: 1050;
    overflow: hidden;
    animation: slideUp 0.2s ease;
}
@keyframes slideUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
.tms-help-panel-header {
    background: #0057B8;
    color: white;
    padding: 12px 16px;
    font-weight: 600;
}
.tms-help-item {
    display: flex;
    align-items: center;
    padding: 10px 16px;
    border-bottom: 1px solid #f0f0f0;
    cursor: pointer;
    transition: background 0.15s;
}
.tms-help-item:hover { background: #f5f8ff; }
.tms-help-item .emoji { font-size: 18px; margin-right: 10px; }
.tms-help-item .question { flex: 1; font-size: 13px; color: #333; }
.tms-help-item .arrow { color: #0057B8; font-size: 12px; }
```

---

## File Manifest

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `wizard/tms_onboarding_wizard_views.xml` | Modify | Agregar banners informativos pasos 1-5 |
| `models/tms_onboarding_wizard.py` | Modify | action_create_first_trip lanza ir.actions.client |
| `static/src/js/tms_tour.js` | Modify | Reescribir: handler action + 9 tours |
| `static/src/js/tms_help_panel.js` | Create | Componente OWL panel flotante |
| `static/src/xml/tms_help_panel.xml` | Create | Template QWeb del panel |
| `static/src/css/tms_help_panel.css` | Create | Estilos flotante + panel |
| `__manifest__.py` | Modify | Registrar nuevos assets JS/XML/CSS |

## Decisiones de arquitectura

1. **Banners en wizard vs web_tour en wizard:** Banners — los tours no funcionan en modals.
2. **ir.actions.client vs JS inline:** ir.actions.client — es el patrón Odoo para ejecutar JS desde Python.
3. **main_components registry vs manual DOM injection:** main_components — es la API oficial Odoo 19 para componentes globales.
4. **Un archivo tms_tour.js vs múltiples archivos:** Un archivo — todos los tours en un lugar, más fácil de mantener.
5. **z-index 1050:** Sobre el chatter (z-index ~100) pero bajo los modals de Odoo (z-index ~1100).
