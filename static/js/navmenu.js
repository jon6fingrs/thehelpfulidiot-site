// Phone menu (templates/partials/nav.html): close the <details> dropdown on
// a tap outside it or on Escape. The menu opens and closes without this;
// it only adds the dismiss behaviour people expect from a dropdown.
document.addEventListener("click", (e) => {
    const menu = document.querySelector("details.nav-mobile[open]");
    if (menu && !menu.contains(e.target)) menu.removeAttribute("open");
});
document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const menu = document.querySelector("details.nav-mobile[open]");
    if (!menu) return;
    menu.removeAttribute("open");
    menu.querySelector("summary").focus();
});
