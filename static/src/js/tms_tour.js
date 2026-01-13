/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

registry.category("web_tour.tours").add("tms_onboarding_tour_detailed", {
    url: "/odoo",
    steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="tms.menu_tms_root"]',
            content: _t("¡Bienvenido al TMS! Vamos a realizar un flujo completo desde la configuración hasta la Carta Porte."),
            tooltipPosition: 'bottom',
            run: "click",
        },
        // --- SECCIÓN 1: CHOFERES ---
        {
            trigger: 'button.dropdown-toggle[data-menu-xmlid="tms.menu_tms_operations"]',
            content: _t("El primer paso es tener operadores. Vamos a la sección de Operadores."),
            run: "click",
        },
        {
            trigger: '.dropdown-item[data-menu-xmlid="tms.menu_tms_drivers"]',
            content: _t("Aquí puedes ver a tus operadores. Asegúrate de que tengan RFC y Licencia Federal para poder timbrar."),
            run: "click",
        },
        // --- SECCIÓN 2: VEHÍCULOS ---
        {
            trigger: 'button.dropdown-toggle[data-menu-xmlid="tms.menu_tms_operations"]',
            content: _t("Ahora revisemos los vehículos."),
            run: "click",
        },
        {
            trigger: '.dropdown-item[data-menu-xmlid="tms.menu_tms_vehicles"]',
            content: _t("Los Tractocamiones deben tener Configuración SAT (ej. T3S2) y su Póliza de Seguro vigente."),
            run: "click",
        },
        {
            trigger: 'button.dropdown-toggle[data-menu-xmlid="tms.menu_tms_operations"]',
            content: _t("No olvides los Remolques."),
            run: "click",
        },
        {
            trigger: '.dropdown-item[data-menu-xmlid="tms.menu_tms_trailers"]',
            content: _t("Aquí registras cajas secas, refrigeradas, etc. También requieren placas de remolque."),
            run: "click",
        },
        // --- SECCIÓN 3: EL VIAJE ---
        {
            trigger: '.dropdown-item[data-menu-xmlid="tms.menu_tms_waybill"]',
            content: _t("¡Vamos al tablero de control! Aquí sucede la magia."),
            run: "click",
        },
        {
            trigger: '.o_list_button_add', 
            content: _t("Crea un nuevo viaje. Notarás que el formulario está dividido en secciones lógicas."),
            run: "click",
        },
        {
            trigger: '.o_field_widget[name="partner_invoice_id"]',
            content: _t("Primero selecciona quién paga (Cliente). Esto auto-llenará sus datos fiscales."),
            run: "click",
        },
        {
            trigger: '.o_field_widget[name="partner_origin_id"]',
            content: _t("Define de dónde sale la carga (Remitente) y a dónde llega (Destinatario)."),
        },
        {
            trigger: 'a[role="tab"]:contains("Información de Ruta")',
            content: _t("En esta pestaña asignarás la unidad física: Vehículo, Chofer y, si es necesario, el Remolque."),
            run: "click",
        },
        {
            trigger: 'a[role="tab"]:contains("Mercancías")',
            content: _t("Es obligatorio detallar qué llevas (Clave SAT, Peso en KG y Descripción) para la Carta Porte."),
            run: "click",
        },
        {
            trigger: 'button[name="action_set_en_pedido"]',
            content: _t("Cuando estés listo, confirma el pedido. Esto validará que no falten datos fiscales."),
            run: "click",
        },
        {
            trigger: 'button[name="action_approve_cp"]',
            content: _t("Finalmente, genera la Carta Porte. El sistema generará el PDF y el XML listo para el SAT."),
            run: "click",
        }
    ]
});
