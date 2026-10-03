// Phone menu (templates/partials/nav.html). Without JavaScript the <details>
// element opens and closes on its own; this makes it dependable on iOS.
//
// - Toggle explicitly on summary clicks instead of trusting the browser's
//   built-in <details> toggle, which WebKit does not always perform.
// - Taps outside the panel land on the summary's full-screen ::before layer
//   (see custom.css), so they come through here as summary clicks and close
//   the menu. A document-level "click outside" check does not work on iOS,
//   which fires no click event for taps on plain page areas.
// - Escape closes it and returns focus to the button.
document.addEventListener("DOMContentLoaded", () => {
    const menu = document.querySelector("details.nav-mobile");
    if (!menu) return;
    const summary = menu.querySelector("summary");

    summary.addEventListener("click", (e) => {
        e.preventDefault();
        menu.open = !menu.open;
        summary.setAttribute("aria-expanded", String(menu.open));
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && menu.open) {
            menu.open = false;
            summary.setAttribute("aria-expanded", "false");
            summary.focus();
        }
    });
});
