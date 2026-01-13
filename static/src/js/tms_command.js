/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const commandProviderRegistry = registry.category("command_provider");

commandProviderRegistry.add("tms_tour_command", {
    provide: (env, options) => {
        return [{
            name: _t("TMS: Iniciar Tour Guiado"),
            action: () => {
                const tour = env.services.tour_manager; // Odoo 19 uses tour_manager or tour service
                // Attempt to use the tour service
                if (env.services.tour_service) {
                     env.services.tour_service.startTour("tms_onboarding_tour_detailed", { keepWatch: true });
                } else if (env.services.tour) {
                     // Fallback/standard for some versions
                     env.services.tour.start("tms_onboarding_tour_detailed", true);
                } else {
                    console.error("TMS Tour: No tour service found.");
                }
            },
            category: "tms",
            href: "#",
        }];
    },
});
