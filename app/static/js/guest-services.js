const serviceForm = document.querySelector("#service-request-form");
document.querySelectorAll("[data-service-category]").forEach((button) => {
    button.addEventListener("click", () => {
        serviceForm.querySelector('[name="category"]').value = button.dataset.serviceCategory;
        serviceForm.hidden = false;
        serviceForm.querySelector("textarea").focus();
    });
});
document.querySelector("#cancel-service-request")?.addEventListener("click", () => { serviceForm.hidden = true; serviceForm.reset(); });
serviceForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(serviceForm);
    const errorBox = document.querySelector("#service-error");
    errorBox.hidden = true;
    const response = await fetch("/guest/service-requests", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: data.get("category"), description: data.get("description") }),
    });
    if (response.ok) { window.location.reload(); return; }
    const payload = await response.json();
    errorBox.textContent = typeof payload.detail === "string" ? payload.detail : "Não foi possível enviar a solicitação.";
    errorBox.hidden = false;
});

const guestServiceSocket = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/guest/ws`);
guestServiceSocket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "service_request.updated") window.location.reload();
});
