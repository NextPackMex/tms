/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { onMounted, onPatched } from "@odoo/owl";

const SAT_PATTERN = /^([0-9]{1,3}\/){2}[0-9]{1,3}(cm|plg)?$/;
const MASK = "000/000/000cm";

class TmsDimensionsField extends CharField {
    setup() {
        super.setup();
        this._ghostEl = null;
        onMounted(() => this._initGhost());
        onPatched(() => this._initGhost());
    }

    _findInput() {
        return this.inputRef?.el || null;
    }

    _initGhost() {
        const input = this._findInput();
        if (!input || input.dataset.tmsDimGhost) return;
        input.dataset.tmsDimGhost = "1";
        input.style.background = "transparent";
        input.style.fontFamily = "monospace";
        input.style.position = "relative";
        input.style.zIndex = "1";
        input.setAttribute("maxlength", "15");
        input.setAttribute("placeholder", MASK);

        const wrapper = input.parentElement;
        wrapper.style.position = "relative";

        const ghost = document.createElement("div");
        const cs = window.getComputedStyle(input);
        Object.assign(ghost.style, {
            position: "absolute",
            top: "0",
            left: "0",
            right: "0",
            bottom: "0",
            display: "flex",
            alignItems: "center",
            pointerEvents: "none",
            zIndex: "0",
            color: "#bbb",
            fontFamily: "monospace",
            paddingLeft: cs.paddingLeft,
            paddingRight: cs.paddingRight,
            fontSize: cs.fontSize,
            lineHeight: cs.lineHeight,
        });
        wrapper.appendChild(ghost);
        this._ghostEl = ghost;

        input.addEventListener("input", () => this._refreshGhost());
        this._refreshGhost();
    }

    _refreshGhost() {
        const input = this._findInput();
        if (!this._ghostEl || !input) return;
        const val = input.value || "";

        // Ghost mask
        if (!val) {
            this._ghostEl.textContent = MASK;
        } else if (val.length >= MASK.length) {
            this._ghostEl.textContent = "";
        } else {
            this._ghostEl.innerHTML =
                `<span style="visibility:hidden">${val}</span>${MASK.substring(val.length)}`;
        }

        // Validation border
        if (val && !SAT_PATTERN.test(val)) {
            input.style.borderColor = "#dc3545";
        } else {
            input.style.borderColor = "";
        }
    }
}

const tmsDimensionsField = {
    ...charField,
    component: TmsDimensionsField,
};

registry.category("fields").add("tms_dimensions", tmsDimensionsField);
