// Run with node --test tests/frontend.test.cjs; no packages or browser required.
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../app/static/js/base.js'), 'utf8');

function clientHarness(fetchImpl) {
    const indicator = {dataset: {}, textContent: ''};
    const toast = {classList: {add() {}, remove() {}}, textContent: ''};
    const sockets = [];
    const timers = [];
    class Socket {
        constructor(url) { this.url = url; this.events = {}; sockets.push(this); }
        addEventListener(type, handler) { this.events[type] = handler; }
        close() {}
    }
    const context = {
        document: {
            querySelector: selector => selector === '[data-connection]' ? indicator : toast,
            querySelectorAll: () => [], addEventListener() {},
        },
        window: {addEventListener() {}},
        location: {protocol: 'https:', host: 'hotel.example.test', href: 'https://hotel.example.test/guest'},
        fetch: fetchImpl,
        WebSocket: Socket,
        setTimeout: (callback, delay) => { timers.push({callback, delay}); return timers.length; },
        clearTimeout() {},
        DOMParser: class { parseFromString() { return {querySelector() { return null; }}; } },
    };
    vm.runInNewContext(source, context);
    return {api: context.window.Hospitality, indicator, toast, sockets, timers};
}

test('network failure releases the button and provides safe feedback', async () => {
    const {api, toast} = clientHarness(async () => { throw new Error('internal-network-detail'); });
    const button = {disabled: false, setAttribute() {}, removeAttribute() {}};
    assert.equal(await api.mutate('/guest/orders', {items: []}, button), false);
    assert.equal(button.disabled, false);
    assert.match(toast.textContent, /Sem conexão/);
    assert.doesNotMatch(toast.textContent, /internal-network-detail/);
});

test('an in-flight button cannot submit a duplicate request', async () => {
    let calls = 0;
    const {api} = clientHarness(async () => { calls++; return {ok: true}; });
    assert.equal(await api.mutate('/guest/orders', {}, {disabled: true}), false);
    assert.equal(calls, 0);
});

test('API errors never render raw backend details', async () => {
    const {api, toast} = clientHarness(async () => ({ok: false, status: 500, text: async () => 'secret'}));
    assert.equal(await api.mutate('/guest/orders', {}), false);
    assert.match(toast.textContent, /Não foi possível/);
    assert.doesNotMatch(toast.textContent, /secret/);
});

test('connection state follows the real socket and authorization denial stops reconnecting', () => {
    const {api, indicator, sockets, timers} = clientHarness(async () => ({ok: true, text: async () => ''}));
    api.connect('/guest/ws', ['food_order.updated']);
    assert.equal(sockets[0].url, 'wss://hotel.example.test/guest/ws');
    assert.equal(indicator.dataset.state, 'connecting');
    sockets[0].events.open();
    assert.equal(indicator.dataset.state, 'connected');
    sockets[0].events.close({code: 4401});
    assert.equal(indicator.dataset.state, 'closed');
    assert.equal(timers.length, 0);
});

test('socket events trigger refresh, unknown events do not, disconnect uses backoff', async () => {
    let calls = 0;
    const {api, sockets, timers, indicator} = clientHarness(async () => { calls++; return {ok: true, text: async () => ''}; });
    api.connect('/guest/ws', ['food_order.updated']);
    sockets[0].events.open();
    sockets[0].events.message({data: JSON.stringify({type: 'unknown'})});
    assert.equal(calls, 0);
    sockets[0].events.message({data: JSON.stringify({type: 'food_order.updated'})});
    await Promise.resolve();
    assert.equal(calls, 1);
    sockets[0].events.close({code: 1006});
    assert.equal(indicator.textContent, 'Reconectando…');
    assert.ok(timers.some(timer => timer.delay === 2000));
});
