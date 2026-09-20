function deviceError(payload) {
    if (typeof payload?.detail === "string") return payload.detail;
    return "Não foi possível concluir a operação.";
}

document.querySelector("#device-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const errorBox = document.querySelector("#device-form-error");
    const submit = form.querySelector('button[type="submit"]');
    errorBox.hidden = true;
    submit.disabled = true;
    try {
        const response = await fetch("/reception/room-devices", {
            method: "POST", credentials: "same-origin",
            headers: { "Content-Type": "application/json", "Accept": "application/json" },
            body: JSON.stringify({ code: data.get("code"), room_id: Number(data.get("room_id")) }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(deviceError(payload));
        document.querySelector("#pairing-code").textContent = payload.pairing_code;
        document.querySelector("#pairing-result").hidden = false;
        form.reset();
    } catch (error) {
        errorBox.textContent = error.message;
        errorBox.hidden = false;
    } finally { submit.disabled = false; }
});

document.querySelectorAll(".revoke-device").forEach((button) => {
    button.addEventListener("click", async () => {
        if (!window.confirm("Revogar o acesso deste dispositivo?")) return;
        const response = await fetch(`/reception/room-devices/${button.dataset.deviceId}/revoke`, { method: "POST", credentials: "same-origin" });
        if (response.ok) window.location.reload();
        else window.alert(deviceError(await response.json()));
    });
});
