"use strict";
window.Hospitality = (() => {
    let toastTimer;
    function toast(message) {
        let box = document.querySelector('#hs-toast');
        if (!box) {
            box = document.createElement('div');
            box.id = 'hs-toast'; box.className = 'hs-toast'; box.setAttribute('role', 'status');
            document.body.append(box);
        }
        box.textContent = message;
        box.classList.add('is-visible');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => box.classList.remove('is-visible'), 4500);
    }
    async function mutate(url, payload, button) {
        if (button?.disabled) return false;
        if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
        try {
            const response = await fetch(url, {
                method: 'POST', credentials: 'same-origin',
                headers: {'Content-Type': 'application/json'},
                ...(payload === undefined ? {} : {body: JSON.stringify(payload)}),
            });
            if (!response.ok) {
                toast(response.status === 401 || response.status === 403
                    ? 'Acesso encerrado ou não autorizado. Entre novamente no seu ambiente.'
                    : 'Não foi possível concluir. Verifique os dados e tente novamente.');
                return false;
            }
            return true;
        } catch {
            toast('Sem conexão. Verifique a rede antes de tentar novamente.');
            return false;
        } finally {
            if (button) { button.disabled = false; button.removeAttribute('aria-busy'); }
        }
    }
    // Replace only read-only regions. Drafts, focus and the rest of the page survive.
    let refreshRunning = false;
    let refreshQueued = false;
    async function refresh() {
        if (refreshRunning) { refreshQueued = true; return; }
        refreshRunning = true;
        const regions = [...document.querySelectorAll('[data-live-region]')];
        regions.forEach(el => { el.setAttribute('aria-busy', 'true'); el.classList.add('loading-region'); });
        try {
            const response = await fetch(location.href, {credentials: 'same-origin', cache: 'no-store'});
            if (!response.ok) throw new Error('refresh');
            const html = new DOMParser().parseFromString(await response.text(), 'text/html');
            const focusKey = document.activeElement?.dataset.actionKey;
            for (const region of regions) {
                const next = html.querySelector(`[data-live-region="${region.dataset.liveRegion}"]`);
                if (next) {
                    region.replaceChildren(...next.childNodes);
                    region.classList.add('status-flash');
                    region.addEventListener('animationend', () => region.classList.remove('status-flash'), {once: true});
                }
            }
            if (focusKey) {
                const button = [...document.querySelectorAll('[data-action-key]')].find(el => el.dataset.actionKey === focusKey);
                button?.focus();
            }
        } catch {
            toast('Não foi possível atualizar os dados. Use Atualizar para tentar novamente.');
        } finally {
            regions.forEach(el => { el.removeAttribute('aria-busy'); el.classList.remove('loading-region'); });
            refreshRunning = false;
            if (refreshQueued) { refreshQueued = false; await refresh(); }
        }
    }
    function connect(path, events) {
        let socket, retry, stopped = false, attempts = 0, connectedBefore = false;
        const indicator = document.querySelector('[data-connection]');
        const setState = (state, message) => {
            if (indicator) { indicator.dataset.state = state; indicator.textContent = message; }
        };
        function open() {
            if (stopped) return;
            setState('connecting', 'Conectando…');
            socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}${path}`);
            socket.addEventListener('open', () => {
                attempts = 0;
                setState('connected', 'Conectado');
                if (connectedBefore) refresh();
                connectedBefore = true;
            });
            socket.addEventListener('message', (event) => {
                let payload;
                try { payload = JSON.parse(event.data); } catch { return; }
                if (events.includes(payload.type)) {
                    toast(payload.type.startsWith('food_order') ? 'Pedidos atualizados.' : 'Solicitações atualizadas.');
                    refresh();
                }
            });
            socket.addEventListener('close', (event) => {
                if (stopped) return;
                if ([4401, 4403, 1008].includes(event.code) || ++attempts > 6) {
                    setState('closed', 'Desconectado · recarregue para reconectar'); return;
                }
                setState('connecting', 'Reconectando…');
                retry = setTimeout(open, Math.min(1000 * 2 ** attempts, 30000));
            });
        }
        open();
        window.addEventListener('pagehide', () => { stopped = true; clearTimeout(retry); socket?.close(); });
        window.addEventListener('pageshow', event => { if (event.persisted) { stopped = false; open(); } });
    }
    document.addEventListener('click', event => {
        if (event.target.closest('[data-refresh]')) refresh();
        const demoButton = event.target.closest('[data-demo-area]');
        if (demoButton) enterDemo(demoButton);
    });
    async function enterDemo(button) {
        if (button.disabled) return;
        const original = button.textContent;
        button.disabled = true;
        button.textContent = 'Preparando ambiente…';
        try {
            const response = await fetch(`/auth/demo/${button.dataset.demoArea}`, {
                method: 'POST', credentials: 'same-origin',
                headers: {'Accept': 'application/json'},
            });
            if (!response.ok) throw new Error('demo-access');
            const payload = await response.json();
            location.assign(payload.destination);
        } catch {
            button.disabled = false;
            button.textContent = original;
            toast('Não foi possível preparar o acesso de demonstração.');
        }
    }
    return {toast, mutate, refresh, connect, enterDemo};
})();
