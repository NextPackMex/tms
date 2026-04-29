/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Dashboard operativo TMS.
 * Carga KPIs reales mediante RPC a tms.waybill.get_dashboard_data()
 * y los renderiza con la plantilla tms.Dashboard.
 */
export class TmsDashboard extends Component {
    static template = "tms.Dashboard";

    setup() {
        this.orm    = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            data: null,
        });

        onWillStart(async () => {
            await this._loadData();
        });
    }

    async _loadData() {
        try {
            const data = await this.orm.call(
                "tms.waybill",
                "get_dashboard_data",
                [],
                {}
            );
            this.state.data = data;
        } catch (e) {
            console.error("TMS Dashboard: error al cargar datos", e);
            // Estado vacío para que la vista no quede rota
            this.state.data = {
                viajes_activos:         0,
                facturado_mes:          0,
                facturado_mes_anterior: 0,
                variacion_porcentaje:   0,
                variacion_positiva:     null,
                por_facturar:           0,
                cancelados_mes:         0,
                pendientes_count:       0,
                pendientes_accion:      [],
                por_estado:             [],
                top_rutas:              [],
                alertas_licencia:       [],
                mes_label:              "",
                currency_symbol:        "$",
                vehicle_performance:    [],
                total_cobrado:          0,
                total_por_cobrar:       0,
            };
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Formatea un número como moneda usando el símbolo de la empresa.
     */
    formatMoney(value) {
        const symbol = this.state.data?.currency_symbol || "$";
        const n = new Intl.NumberFormat("es-MX", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value || 0);
        return `${symbol} ${n}`;
    }

    /**
     * Color de badge según el estado del waybill.
     */
    getEstadoColor(estado) {
        const mapa = {
            cotizado:   "#6c757d",
            aprobado:   "#0d6efd",
            waybill:    "#0dcaf0",
            in_transit: "#fd7e14",
            arrived:    "#ffc107",
            closed:     "#198754",
            cancel:     "#dc3545",
            rejected:   "#adb5bd",
        };
        return mapa[estado] || "#6c757d";
    }

    /** Valor absoluto — Math no está en el scope de templates OWL. */
    absValue(v) {
        return Math.abs(v || 0);
    }

    /** Abre el wizard de nueva cotización. */
    openNuevaCotizacion() {
        this.action.doAction("tms.action_tms_cotizacion_wizard");
    }

    /** Abre la vista de viajes filtrada por estado. */
    openViajes(estado) {
        const domain = estado ? [["state", "=", estado]] : [];
        this.action.doAction({
            type:      "ir.actions.act_window",
            res_model: "tms.waybill",
            name:      "Viajes",
            views:     [[false, "list"], [false, "form"]],
            domain,
        });
    }
}

registry.category("actions").add("tms_dashboard", TmsDashboard);
