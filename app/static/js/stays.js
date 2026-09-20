document.querySelectorAll(".stay-operation").forEach((button) => {
    button.addEventListener("click", async () => {
        const operation = button.dataset.operation;
        const label = operation === "check-in" ? "check-in" : "check-out";
        if (!window.confirm(`Realizar ${label} para ${button.dataset.guestName}?`)) return;
        button.disabled = true;
        try {
            const response = await fetch(`/reception/reservations/${button.dataset.reservationId}/${operation}`, { method: "POST", credentials: "same-origin", headers: { "Accept": "application/json" } });
            if (!response.ok) {
                const payload = await response.json();
                throw new Error(typeof payload.detail === "string" ? payload.detail : "Não foi possível concluir a operação.");
            }
            window.location.reload();
        } catch (error) {
            button.disabled = false;
            window.alert(error.message);
        }
    });
});
