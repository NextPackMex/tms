/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

// ═════════════════════════════════════════════════════════════════════════════════════
// HANDLER ir.actions.client — Lanza tours desde Python después del onboarding
// ═════════════════════════════════════════════════════════════════════════════════════

registry.category("actions").add("tms_launch_tour", async (env, action) => {
    const tourName = action.params?.tour_name || 'tms_tour_carta_porte';
    // Esperar 500ms a que el modal del onboarding se cierre
    setTimeout(() => {
        odoo.startTour(tourName, { mode: 'manual' });
    }, 500);
});

// ═════════════════════════════════════════════════════════════════════════════════════
// TOUR PRINCIPAL — tms_tour_carta_porte (9 pasos)
// Guía al usuario a crear su primer viaje desde cero hasta timbrado
// ═════════════════════════════════════════════════════════════════════════════════════

registry.category("web_tour.tours").add("tms_tour_carta_porte", {
    url: "/odoo/action-452",
    steps: () => [
        {
            trigger: 'button[data-menu-xmlid="tms.menu_tms_nueva_cotizacion"]',
            content: _t("¡Bienvenido! Vamos a crear tu primer viaje. Haz clic en 'Nueva Cotización'."),
            tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: '.o_field_widget[name="origin_zip"] input',
            content: _t("Ingresa el código postal de ORIGEN. Determina dónde parte la carga."),
            tooltipPosition: 'right',
        },
        {
            trigger: '.o_field_widget[name="dest_zip"] input',
            content: _t("Ingresa el código postal de DESTINO."),
            tooltipPosition: 'right',
        },
        {
            trigger: 'button[name="action_calcular_ruta"]',
            content: _t("Haz clic aquí. TollGuru calculará automáticamente distancia, tiempo y casetas."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: '.o_field_widget[name="selected_proposal"]',
            content: _t("El sistema te muestra 3 propuestas: por KM, por viaje (costos+margen) o precio directo. Elige la mejor."),
            tooltipPosition: 'right',
        },
        {
            trigger: 'button:contains("Siguiente")',
            content: _t("Haz clic en 'Siguiente' para agregar cliente y mercancía."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: 'button:contains("Crear Viaje"), button[name="action_create_waybill"]',
            content: _t("Aquí agregas cliente y mercancías. El RFC del cliente es obligatorio. Luego haz clic en 'Crear Viaje'."),
            tooltipPosition: 'right',
        },
        {
            trigger: 'button[name="action_stamp_cfdi"]',
            content: _t("Una vez aprobado por el cliente, usa este botón para timbrar la Carta Porte en el SAT."),
            tooltipPosition: 'right',
        },
        {
            trigger: '.o_field_widget[name="cfdi_uuid"]',
            content: _t("¡Éxito! Este es tu UUID (Folio Fiscal) — comprobante ante el SAT. ¡Felicidades por tu primer viaje!"),
            tooltipPosition: 'right',
        },
    ]
});

// ═════════════════════════════════════════════════════════════════════════════════════
// MICRO-TOUR — tms_micro_empresa (3 pasos)
// Para configurar RFC y datos de empresa en Configuración
// ═════════════════════════════════════════════════════════════════════════════════════

registry.category("web_tour.tours").add("tms_micro_empresa", {
    url: "/odoo/action-452",
    steps: () => [
        {
            trigger: 'button.o-dropdown[data-menu-xmlid="tms.menu_tms_config"]',
            content: _t("Abre el menú de Configuración."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: '.o-dropdown--item[data-menu-xmlid="tms.menu_tms_my_company"]',
            content: _t("Haz clic en 'Mi Empresa' para configurar tu RFC y datos fiscales."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: '.o_field_widget[name="vat"] input',
            content: _t("Aquí va tu RFC. Debe coincidir exactamente con tu Certificado del SAT."),
            tooltipPosition: 'right',
        },
    ]
});

// ═════════════════════════════════════════════════════════════════════════════════════
// MICRO-TOUR — tms_micro_csd (4 pasos)
// Para subir los archivos del Certificado de Sello Digital
// ═════════════════════════════════════════════════════════════════════════════════════

registry.category("web_tour.tours").add("tms_micro_csd", {
    url: "/odoo/action-452",
    steps: () => [
        {
            trigger: 'button.o-dropdown[data-menu-xmlid="tms.menu_tms_config"]',
            content: _t("Abre Configuración."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: '.o-dropdown--item[data-menu-xmlid="tms.menu_tms_config_settings"]',
            content: _t("Haz clic en 'Ajustes TMS'."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: 'button.o-dropdown[data-menu-xmlid="tms.menu_tms_my_company"]',
            content: _t("Aquí está 'Mi Empresa'. Abre el formulario para ver los campos de CSD."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: '.o_field_widget[name="tms_csd_cer"]',
            content: _t("Sube aquí tu archivo .cer (certificado) del SAT. Lo descargas en sat.gob.mx → CertiSAT Web."),
            tooltipPosition: 'right',
        },
    ]
});

// ═════════════════════════════════════════════════════════════════════════════════════
// MICRO-TOUR — tms_micro_vehiculos (3 pasos)
// Para registrar vehículos
// ═════════════════════════════════════════════════════════════════════════════════════

registry.category("web_tour.tours").add("tms_micro_vehiculos", {
    url: "/odoo/action-452",
    steps: () => [
        {
            trigger: 'button.o-dropdown[data-menu-xmlid="tms.menu_tms_operations"]',
            content: _t("Abre el menú de Operaciones."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: '.o-dropdown--item[data-menu-xmlid="tms.menu_tms_vehicles"]',
            content: _t("Haz clic en 'Vehículos' para registrar tus unidades."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: '.o_list_button_add',
            content: _t("Haz clic en 'Nuevo' para agregar un vehículo. Llena: placas, tipo SAT y datos de seguro."),
            tooltipPosition: 'right',
        },
    ]
});

// ═════════════════════════════════════════════════════════════════════════════════════
// MICRO-TOUR — tms_micro_choferes (3 pasos)
// Para registrar operadores
// ═════════════════════════════════════════════════════════════════════════════════════

registry.category("web_tour.tours").add("tms_micro_choferes", {
    url: "/odoo/action-452",
    steps: () => [
        {
            trigger: 'button.o-dropdown[data-menu-xmlid="tms.menu_tms_operations"]',
            content: _t("Abre el menú de Operaciones."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: '.o-dropdown--item[data-menu-xmlid="tms.menu_tms_drivers"]',
            content: _t("Haz clic en 'Operadores' para registrar tus choferes."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: '.o_list_button_add',
            content: _t("Haz clic en 'Nuevo'. Cada chofer necesita RFC, CURP y número de Licencia Federal vigente."),
            tooltipPosition: 'right',
        },
    ]
});

// ═════════════════════════════════════════════════════════════════════════════════════
// MICRO-TOUR — tms_micro_cotizacion (4 pasos)
// Flujo rápido de creación de cotización
// ═════════════════════════════════════════════════════════════════════════════════════

registry.category("web_tour.tours").add("tms_micro_cotizacion", {
    url: "/odoo/action-452",
    steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="tms.menu_tms_root"]',
            content: _t("Estás en el Tablero de Viajes. Este es tu centro de operaciones."),
            tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: 'button[data-menu-xmlid="tms.menu_tms_nueva_cotizacion"]',
            content: _t("Siempre crea cotizaciones desde aquí. Nunca desde el formulario de viaje."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: '.o_field_widget[name="origin_zip"] input',
            content: _t("Ingresa origen, destino, selecciona una propuesta y avanza al siguiente paso."),
            tooltipPosition: 'right',
        },
        {
            trigger: 'button:contains("Siguiente")',
            content: _t("Aquí agregas cliente y mercancía con Clave SAT obligatoria. Luego haz clic en 'Crear Viaje'."),
            tooltipPosition: 'right',
        },
    ]
});

// ═════════════════════════════════════════════════════════════════════════════════════
// MICRO-TOUR — tms_micro_factura (4 pasos)
// Para facturación electrónica (CFDI Ingreso)
// ═════════════════════════════════════════════════════════════════════════════════════

registry.category("web_tour.tours").add("tms_micro_factura", {
    url: "/odoo/action-452",
    steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="tms.menu_tms_root"]',
            content: _t("Estamos en el Tablero."),
            tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: '.o_kanban_record',
            content: _t("Abre un viaje aprobado para facturarlo."),
            tooltipPosition: 'right',
            run: "click",
        },
        {
            trigger: 'button[name="action_create_invoice"]',
            content: _t("Este botón crea la factura CFDI Ingreso consolidando uno o más viajes."),
            tooltipPosition: 'right',
        },
        {
            trigger: '.o_field_widget[name="cfdi_uuid"]',
            content: _t("Aquí aparece el UUID (Folio Fiscal) una vez timbrada la factura en el SAT."),
            tooltipPosition: 'right',
        },
    ]
});

// ═════════════════════════════════════════════════════════════════════════════════════
// MICRO-TOUR — tms_micro_dashboard (4 pasos)
// Para explorar KPIs y analytics
// ═════════════════════════════════════════════════════════════════════════════════════

registry.category("web_tour.tours").add("tms_micro_dashboard", {
    url: "/odoo/action-452",
    steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="tms.menu_tms_root"]',
            content: _t("En la parte superior del Tablero ves los KPIs principales de tu operación."),
            tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: '.o_tms_kpi_card',
            content: _t("'Viajes Activos' = viajes en Tránsito o En Destino ahora mismo."),
            tooltipPosition: 'right',
        },
        {
            trigger: '.o_view_nocontent_smiling_face, table',
            content: _t("Abajo ves rentabilidad por ruta, rendimiento por vehículo y alertas de licencia vencida."),
            tooltipPosition: 'right',
        },
        {
            trigger: '.o_dashboard, .container',
            content: _t("Consulta regularmente estos datos para optimizar tu operación. ¡Éxito!"),
            tooltipPosition: 'bottom',
        },
    ]
});
