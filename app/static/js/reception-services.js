"use strict";
document.addEventListener('click', async event => {
    const button = event.target.closest('.request-actions button');
    if (!button) return;
    if (button.dataset.status === 'CANCELLED' && !window.confirm('Cancelar esta solicitação?')) return;
    const id = button.closest('.request-actions').dataset.requestId;
    if (await Hospitality.mutate(`/reception/service-requests/${id}/status`, {status: button.dataset.status}, button)) {
        Hospitality.toast('Solicitação atualizada.'); await Hospitality.refresh();
    }
});
Hospitality.connect('/reception/ws', ['service_request.created']);
