"use strict";
document.querySelector('#food-order-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const items = [...form.querySelectorAll('[data-menu-item]')].map(input => ({menu_item_id: Number(input.dataset.menuItem), quantity: Number(input.value)})).filter(item => item.quantity > 0);
    const error = document.querySelector('#order-error');
    error.hidden = true;
    if (!items.length) { error.textContent = 'Escolha pelo menos um item para seu pedido.'; error.hidden = false; return; }
    if (!window.confirm('Enviar este pedido para a cozinha?')) return;
    if (await Hospitality.mutate('/guest/orders', {items, notes: new FormData(form).get('notes') || null}, form.querySelector('[type="submit"]'))) {
        form.reset(); Hospitality.toast('Pedido enviado para a cozinha.'); await Hospitality.refresh();
    }
});
Hospitality.connect('/guest/ws', ['food_order.updated']);
