document.querySelectorAll(".request-actions button").forEach((button) => {
    button.addEventListener("click", async () => {
        button.disabled = true;
        const requestId = button.closest(".request-actions").dataset.requestId;
        const response = await fetch(`/reception/service-requests/${requestId}/status`, {
            method: "POST", credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: button.dataset.status }),
        });
        if (response.ok) window.location.reload();
        else {
            const payload = await response.json();
            window.alert(typeof payload.detail === "string" ? payload.detail : "Não foi possível atualizar a solicitação.");
            button.disabled = false;
        }
    });
});
const receptionServiceSocket = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/reception/ws`);
receptionServiceSocket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "service_request.created") window.location.reload();
});
