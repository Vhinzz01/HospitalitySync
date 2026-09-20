"use strict";
function showMessage(message) { Hospitality.toast(message); }
document.querySelector('#logout-button')?.addEventListener('click', async event => {
    if (await Hospitality.mutate('/auth/logout', undefined, event.currentTarget)) location.replace('/reception/login');
});
const sidebar = document.querySelector('#sidebar');
const menuToggle = document.querySelector('#menu-toggle');
const shell = document.querySelector('.app-shell');
const mobileNavigation = window.matchMedia('(max-width: 820px)');
function syncNavigation() {
    const expanded = mobileNavigation.matches ? sidebar.classList.contains('is-open') : !shell.classList.contains('is-collapsed');
    menuToggle?.setAttribute('aria-expanded', String(expanded));
    sidebar.inert = !expanded;
}
menuToggle?.addEventListener('click', () => {
    if (mobileNavigation.matches) sidebar.classList.toggle('is-open');
    else shell.classList.toggle('is-collapsed');
    syncNavigation();
});
document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && mobileNavigation.matches) {
        sidebar.classList.remove('is-open'); syncNavigation(); menuToggle?.focus();
    }
});
document.addEventListener('click', event => {
    if (mobileNavigation.matches && sidebar.classList.contains('is-open') && !sidebar.contains(event.target) && !menuToggle.contains(event.target)) {
        sidebar.classList.remove('is-open'); syncNavigation();
    }
});
mobileNavigation.addEventListener('change', syncNavigation);
syncNavigation();
