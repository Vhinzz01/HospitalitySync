document.querySelector("#pair-device-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const errorBox = document.querySelector("#pair-error");
    const submit = form.querySelector('button[type="submit"]');
    errorBox.hidden = true;
    submit.disabled = true;
    try {
        const response = await fetch("/guest/pair", {
            method: "POST", credentials: "same-origin",
            headers: { "Content-Type": "application/json", "Accept": "application/json" },
            body: JSON.stringify({ code: data.get("code"), pairing_code: data.get("pairing_code") }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Não foi possível vincular o dispositivo.");
        window.location.assign("/guest");
    } catch (error) {
        errorBox.textContent = error.message;
        errorBox.hidden = false;
        submit.disabled = false;
    }
});
