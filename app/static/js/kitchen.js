"use strict";
document.querySelector('#kitchen-logout').addEventListener('click', async event => {
    if (await Hospitality.mutate('/auth/logout', undefined, event.currentTarget)) location.assign('/kitchen/login');
});
document.addEventListener('click', async event => {
    const statusButton = event.target.closest('[data-next-status]');
    const menuButton = event.target.closest('.toggle-menu-item');
    if (statusButton && await Hospitality.mutate(`/kitchen/orders/${statusButton.dataset.orderId}/status`, {status: statusButton.dataset.nextStatus}, statusButton)) {
        Hospitality.toast('Pedido atualizado.'); await Hospitality.refresh();
    }
    if (menuButton && await Hospitality.mutate(`/kitchen/menu-items/${menuButton.dataset.itemId}/availability`, {available: menuButton.dataset.available === 'true'}, menuButton)) {
        Hospitality.toast('Cardápio atualizado.'); await Hospitality.refresh();
    }
});
document.querySelector('#menu-item-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    if (await Hospitality.mutate('/kitchen/menu-items', {name: data.get('name'), description: data.get('description') || null, price: data.get('price'), available: true}, form.querySelector('[type="submit"]'))) {
        form.reset(); Hospitality.toast('Item adicionado ao cardápio.'); await Hospitality.refresh();
    }
});
Hospitality.connect('/kitchen/ws', ['food_order.created']);
