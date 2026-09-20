"use strict";
const serviceForm = document.querySelector('#service-request-form');
let categoryButton;
document.querySelectorAll('[data-service-category]').forEach(button => {
    button.addEventListener('click', () => {
        categoryButton = button;
        serviceForm.querySelector('[name="category"]').value = button.dataset.serviceCategory;
        document.querySelector('#service-form-label').textContent = button.textContent.trim() + ' — descreva como podemos ajudar';
        serviceForm.hidden = false;
        serviceForm.querySelector('textarea').focus();
    });
});
document.querySelector('#cancel-service-request')?.addEventListener('click', () => {
    serviceForm.hidden = true; serviceForm.reset(); categoryButton?.focus();
});
serviceForm?.addEventListener('submit', async event => {
    event.preventDefault();
    const data = new FormData(serviceForm);
    if (await Hospitality.mutate('/guest/service-requests', {category: data.get('category'), description: data.get('description')}, serviceForm.querySelector('[type="submit"]'))) {
        serviceForm.reset(); serviceForm.hidden = true; categoryButton?.focus();
        Hospitality.toast('Solicitação enviada. Nossa equipe foi avisada.'); await Hospitality.refresh();
    }
});
Hospitality.connect('/guest/ws', ['service_request.updated', 'food_order.updated']);
