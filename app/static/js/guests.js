function guestErrorMessage(payload) {
    if (typeof payload?.detail === "string") return payload.detail;
    if (Array.isArray(payload?.detail) && payload.detail.length) {
        return payload.detail[0].msg ?? "Os dados informados são inválidos.";
    }
    return "Não foi possível concluir a operação.";
}

document.querySelectorAll(".deactivate-guest").forEach((button) => {
    button.addEventListener("click", async () => {
        if (!window.confirm(`Desativar o cadastro de ${button.dataset.guestName}?`)) return;
        button.disabled = true;
        try {
            const response = await fetch(`/reception/guests/${button.dataset.guestId}/deactivate`, { method: "POST", credentials: "same-origin", headers: { "Accept": "application/json" } });
            if (!response.ok) throw new Error(guestErrorMessage(await response.json()));
            window.location.reload();
        } catch (error) {
            button.disabled = false;
            window.alert(error.message);
        }
    });
});

const guestForm = document.querySelector("#guest-form");
guestForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(guestForm);
    const guestId = guestForm.dataset.guestId;
    const errorBox = document.querySelector("#guest-form-error");
    const submitButton = guestForm.querySelector('button[type="submit"]');
    const payload = {
        full_name: data.get("full_name"),
        document: data.get("document"),
        email: data.get("email") || null,
        phone: data.get("phone") || null,
    };
    errorBox.hidden = true;
    submitButton.disabled = true;
    try {
        const response = await fetch(guestId ? `/reception/guests/${guestId}` : "/reception/guests", { method: guestId ? "PUT" : "POST", credentials: "same-origin", headers: { "Accept": "application/json", "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        if (!response.ok) throw new Error(guestErrorMessage(await response.json()));
        window.location.assign("/reception/guests");
    } catch (error) {
        errorBox.textContent = error.message;
        errorBox.hidden = false;
        submitButton.disabled = false;
    }
});
