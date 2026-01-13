/** @odoo-module **/

// TMS Portal Link Handler: Intercepta clics en enlaces del chatter
document.addEventListener('click', function(ev) {
    // 1. Find the closest anchor tag (in case click is on an icon/span inside a)
    const link = ev.target.closest('a');

    if (!link || !link.href) {
        return;
    }

    // 2. Define criteria for the target link
    // We check for the specific custom portal route AND the access_token param
    // This ensures we only capture our specific quotation links, not generic Odoo links.
    const href = link.href;
    const isWaybillUrl = href.includes('/my/waybills/');
    const hasAccessToken = href.includes('access_token=');

    // 3. Intercept if it matches our target
    if (isWaybillUrl && hasAccessToken) {
        // Prevent Odoo/OWL from handling this click
        ev.preventDefault();
        ev.stopPropagation();
        ev.stopImmediatePropagation();

        // Open securely in new tab
        window.open(href, '_blank', 'noopener,noreferrer');
    }
}, true); // TRUE = Capture Phase (Executes before bubbling/Odoo handlers)
