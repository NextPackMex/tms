/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const commandProviderRegistry = registry.category("command_provider");

commandProviderRegistry.add("tms_tour_command", {
    provide: (env, options) => {
        return [{
            name: _t("TMS: Iniciar Tour Guiado"),
            action: () => {
                odoo.startTour("tms_tour_carta_porte", { mode: 'manual' });
            },
            category: "tms",
            href: "#",
        }];
    },
});
