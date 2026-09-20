"use strict";
const loginForm = document.querySelector('#employee-login');
document.querySelector('#toggle-password').addEventListener('click', (event) => {
    const input = document.querySelector('#password');
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';
    event.currentTarget.textContent = visible ? 'Ocultar' : 'Mostrar';
    event.currentTarget.setAttribute('aria-pressed', String(visible));
});
loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = loginForm.querySelector('[type="submit"]');
    const error = document.querySelector('#login-error');
    error.hidden = true;
    button.disabled = true;
    button.textContent = 'Entrando…';
    loginForm.setAttribute('aria-busy', 'true');
    try {
        const fields = new FormData(loginForm);
        const response = await fetch(loginForm.dataset.endpoint, {
            method: 'POST', credentials: 'same-origin',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email: fields.get('email'), password: fields.get('password')}),
        });
        if (!response.ok) {
            error.textContent = response.status === 401 ? 'Email ou senha inválidos para este ambiente.' : 'Não foi possível entrar. Tente novamente em instantes.';
            error.hidden = false;
            return;
        }
        loginForm.reset();
        window.location.assign(loginForm.dataset.destination);
    } catch {
        error.textContent = 'Não foi possível conectar. Verifique sua conexão e tente novamente.';
        error.hidden = false;
    } finally {
        button.disabled = false;
        button.textContent = 'Entrar';
        loginForm.setAttribute('aria-busy', 'false');
    }
});
