function getErrorMessage(payload) {
    if (typeof payload?.detail === "string") {
        return payload.detail;
    }
    if (Array.isArray(payload?.detail) && payload.detail.length > 0) {
        return payload.detail[0].msg ?? "Os dados informados são inválidos.";
    }
    return "Não foi possível concluir a operação.";
}

document.querySelectorAll(".cancel-reservation").forEach((button) => {
    button.addEventListener("click", async () => {
        const reservationId = button.dataset.reservationId;
        const guestName = button.dataset.guestName;
        const confirmed = window.confirm(`Cancelar a reserva de ${guestName}?`);
        if (!confirmed) {
            return;
        }

        button.disabled = true;
        try {
            const response = await fetch(`/reception/reservations/${reservationId}/cancel`, {
                method: "POST",
                credentials: "same-origin",
                headers: { "Accept": "application/json" },
            });
            if (!response.ok) {
                throw new Error(getErrorMessage(await response.json()));
            }
            window.location.reload();
        } catch (error) {
            button.disabled = false;
            window.alert(error.message);
        }
    });
});

const reservationForm = document.querySelector("#reservation-form");
reservationForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorBox = document.querySelector("#reservation-form-error");
    const submitButton = reservationForm.querySelector('button[type="submit"]');
    const formData = new FormData(reservationForm);
    const reservationId = reservationForm.dataset.reservationId;
    const payload = {
        guest_id: Number(formData.get("guest_id")),
        room_id: Number(formData.get("room_id")),
        guest_count: Number(formData.get("guest_count")),
        check_in_date: formData.get("check_in_date"),
        check_out_date: formData.get("check_out_date"),
    };

    errorBox.hidden = true;
    submitButton.disabled = true;
    try {
        const response = await fetch(
            reservationId ? `/reception/reservations/${reservationId}` : "/reception/reservations",
            {
                method: reservationId ? "PUT" : "POST",
                credentials: "same-origin",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            },
        );
        if (!response.ok) {
            throw new Error(getErrorMessage(await response.json()));
        }
        window.location.assign("/reception/reservations");
    } catch (error) {
        errorBox.textContent = error.message;
        errorBox.hidden = false;
        submitButton.disabled = false;
        errorBox.scrollIntoView({ behavior: "smooth", block: "center" });
    }
});
