/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/**
 * Panel flotante de ayuda con 8 preguntas frecuentes.
 * Cada pregunta lanza un tour específico para guiar al usuario.
 *
 * Componente: TmsHelpPanel
 * Registrado en: main_components
 * Visibilidad: global (en toda la interfaz de Odoo)
 */

// Array de preguntas frecuentes y sus tours asociados
const HELP_TOURS = [
    {
        emoji: "🚛",
        question: _t("¿Cómo creo mi primer viaje?"),
        tour: "tms_tour_carta_porte",
    },
    {
        emoji: "📋",
        question: _t("¿Dónde configuro mi RFC y empresa?"),
        tour: "tms_micro_empresa",
    },
    {
        emoji: "🔐",
        question: _t("¿Cómo subo mi Certificado del SAT (CSD)?"),
        tour: "tms_micro_csd",
    },
    {
        emoji: "🛣️",
        question: _t("¿Cómo registro mis vehículos?"),
        tour: "tms_micro_vehiculos",
    },
    {
        emoji: "👷",
        question: _t("¿Cómo agrego mis choferes?"),
        tour: "tms_micro_choferes",
    },
    {
        emoji: "📊",
        question: _t("¿Qué es la cotización y cómo se crea?"),
        tour: "tms_micro_cotizacion",
    },
    {
        emoji: "📑",
        question: _t("¿Cómo facturo electrónicamente (CFDI)?"),
        tour: "tms_micro_factura",
    },
    {
        emoji: "📈",
        question: _t("¿Cómo veo mis KPIs y analytics?"),
        tour: "tms_micro_dashboard",
    },
];

class TmsHelpPanel extends Component {
    /**
     * Panel flotante de ayuda — 8 preguntas con tours interactivos.
     */

    setup() {
        // Estado del panel: abierto/cerrado
        this.state = useState({
            isOpen: false,
        });
        // Guardar referencia a HELP_TOURS para el template
        this.helpTours = HELP_TOURS;
    }

    /**
     * Alterna la visibilidad del panel.
     */
    togglePanel = () => {
        this.state.isOpen = !this.state.isOpen;
    }

    /**
     * Cierra el panel y lanza el tour solicitado.
     *
     * @param {string} tourName - Nombre del tour a lanzar
     */
    launchTour = (tourName) => {
        this.state.isOpen = false;
        // Esperar 200ms a que el panel se cierre antes de lanzar el tour
        setTimeout(() => {
            odoo.startTour(tourName, { mode: 'manual' });
        }, 200);
    }
}

TmsHelpPanel.template = "tms_help_panel";

// Registrar el componente en main_components
registry.category("main_components").add("TmsHelpPanel", {
    Component: TmsHelpPanel,
    props: {},
});
