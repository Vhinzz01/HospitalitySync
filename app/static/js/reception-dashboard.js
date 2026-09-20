const receptionDashboardSocket = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/reception/ws`);
receptionDashboardSocket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "service_request.created") window.location.reload();
});
