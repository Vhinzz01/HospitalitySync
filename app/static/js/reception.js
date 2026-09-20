const logoutButton = document.querySelector("#logout-button");
const sidebar = document.querySelector("#sidebar");
const menuToggle = document.querySelector("#menu-toggle");
const toast = document.querySelector("#toast");

function showMessage(message) {
    toast.textContent = message;
    toast.classList.add("is-visible");
    window.setTimeout(() => toast.classList.remove("is-visible"), 2600);
}

logoutButton?.addEventListener("click", async () => {
    logoutButton.disabled = true;
    logoutButton.textContent = "Saindo…";

    try {
        const response = await fetch("/auth/logout", {
            method: "POST",
            credentials: "same-origin",
        });

        if (!response.ok) {
            throw new Error("Logout request failed");
        }
        window.location.replace("/reception");
    } catch {
        logoutButton.disabled = false;
        logoutButton.textContent = "Sair";
        showMessage("Não foi possível encerrar a sessão.");
    }
});

menuToggle?.addEventListener("click", () => {
    const isOpen = sidebar.classList.toggle("is-open");
    menuToggle.setAttribute("aria-expanded", String(isOpen));
});

document.querySelectorAll(".upcoming-module").forEach((button) => {
    button.addEventListener("click", () => {
        showMessage("Este módulo será disponibilizado em uma próxima etapa.");
    });
});
