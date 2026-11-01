// Run with: node --test tests/test_threshold_page.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');

const frontend = path.resolve(__dirname, '../frontend');
const frontendRequire = createRequire(path.join(frontend, 'package.json'));
const ts = frontendRequire('typescript');
function pageHarness(get, relativePath = 'app/admin/threshold/page.tsx', exportName = 'default') {
    const filename = path.join(frontend, 'src', relativePath);
    const state = [];
    const effects = [];
    const callbacks = [];
    const refs = [];
    let stateIndex = 0;
    let effectIndex = 0;
    let callbackIndex = 0;
    let refIndex = 0;
    let updates = 0;
    const requests = [];
    const writes = [];
    const react = {
        useState(initial) {
            const slot = stateIndex++;
            if (!(slot in state)) state[slot] = initial;
            return [state[slot], value => {
                updates++;
                state[slot] = typeof value === 'function' ? value(state[slot]) : value;
            }];
        },
        useEffect(callback, deps) {
            const slot = effectIndex++;
            const previous = effects[slot];
            if (!previous || deps.some((value, i) => !Object.is(value, previous.deps[i]))) {
                effects[slot] = { deps, callback, cleanup: previous?.cleanup, pending: true };
            }
        },
        useCallback(callback, deps) {
            const slot = callbackIndex++;
            const previous = callbacks[slot];
            if (!previous || deps.some((value, i) => !Object.is(value, previous.deps[i]))) {
                callbacks[slot] = { callback, deps };
            }
            return callbacks[slot].callback;
        },
        useRef(initial) {
            const slot = refIndex++;
            if (!(slot in refs)) refs[slot] = { current: initial };
            return refs[slot];
        },
    };
    const apiClient = {
        get: async (url, config) => {
            requests.push({ url, config });
            return get(url, config);
        },
    };
    for (const method of ['put', 'post', 'patch', 'delete']) {
        apiClient[method] = (...args) => {
            writes.push({ method, args });
            throw new Error('Threshold page must not write settings');
        };
    }
    const { outputText } = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
        fileName: filename,
        compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
    });
    const module = { exports: {} };
    vm.runInNewContext(outputText, {
        module, exports: module.exports, AbortController,
        require(name) {
            if (name === 'react') return react;
            if (name === '@/lib/apiClient') return { apiClient };
            return frontendRequire(name);
        },
    }, { filename });
    return {
        requests, writes,
        get updates() { return updates; },
        render() {
            stateIndex = 0;
            effectIndex = 0;
            callbackIndex = 0;
            refIndex = 0;
            return module.exports[exportName]();
        },
        flushEffects() {
            for (const effect of effects) {
                if (!effect.pending) continue;
                effect.cleanup?.();
                effect.pending = false;
                effect.cleanup = effect.callback();
            }
        },
        unmount() {
            for (const effect of effects) effect.cleanup?.();
        },
    };
}

function* elements(node) {
    if (!node || typeof node !== 'object') return;
    if (Array.isArray(node)) {
        for (const child of node) yield* elements(child);
    } else if (node.props) {
        yield node;
        yield* elements(node.props.children);
    }
}

function text(node) {
    if (Array.isArray(node)) return node.map(text).join(' ');
    if (node && typeof node === 'object') return text(node.props?.children);
    return typeof node === 'string' || typeof node === 'number' ? String(node) : '';
}

const settle = () => new Promise(resolve => setImmediate(resolve));
const result = threshold => ({
    data: { status: 'success', data: {
        threshold, editable: false, note: 'Ambang tetap pada model beku (per seed).',
    } },
});

function assertReadOnly(tree, harness) {
    assert.equal([...elements(tree)].some(node => node.type === 'input'), false);
    const buttons = [...elements(tree)].filter(node => node.type === 'button');
    assert.equal(buttons.length, 1);
    assert.match(text(buttons[0]), /Muat ulang|Coba lagi/);
    assert.doesNotMatch(text(tree), /Terapkan Sekarang|Simulasi Dampak|Belum disimpan/);
    assert.equal(harness.writes.length, 0);
}

test('threshold page reads the actual configuration and has no save controls', async () => {
    const harness = pageHarness(async () => result(0.5));
    const initial = harness.render();
    assert.match(text(initial), /Memuat konfigurasi/);
    assert.doesNotMatch(text(initial), /0\.50|0\.60/);
    harness.flushEffects();
    await settle();
    const tree = harness.render();
    assert.equal(harness.requests.length, 1);
    assert.equal(harness.requests[0].url, '/api/v1/admin/threshold');
    assert.equal(harness.requests[0].config.signal.aborted, false);
    assert.match(text(tree), /0\.50/);
    assert.match(text(tree), /Hanya baca/);
    assert.match(text(tree), /Ambang tetap pada model beku/);
    assertReadOnly(tree, harness);
    harness.unmount();
});

test('unavailable configuration shows a readable error and can be retried', async () => {
    let fail = true;
    const harness = pageHarness(async () => {
        if (fail) throw { isAxiosError: true, response: { data: { detail: 'Layanan belum tersedia.' } } };
        return result(0.5);
    });
    harness.render();
    harness.flushEffects();
    await settle();
    const failed = harness.render();
    assert.match(text(failed), /Layanan belum tersedia/);
    assert.doesNotMatch(text(failed), /0\.50|0\.60/);
    assert.ok([...elements(failed)].some(node => node.props.role === 'alert'));
    const retry = [...elements(failed)].find(node => node.type === 'button');
    assert.match(text(retry), /Coba lagi/);
    assert.equal(retry.props.disabled, false);
    fail = false;
    retry.props.onClick();
    harness.render();
    harness.flushEffects();
    await settle();
    const recovered = harness.render();
    assert.equal(harness.requests.length, 2);
    assert.equal(harness.requests[0].config.signal.aborted, true);
    assert.match(text(recovered), /0\.50/);
    assert.doesNotMatch(text(recovered), /Layanan belum tersedia/);
    assertReadOnly(recovered, harness);
    harness.unmount();
});

test('malformed values and unexpected editable settings are not displayed as active', async () => {
    const payloads = [
        ...[NaN, Infinity, -0.1, 1.1, '0.5', null].map(threshold => result(threshold)),
        { data: { status: 'success', data: { threshold: 0.5, editable: true } } },
        { data: { status: 'success', data: { threshold: 0.5 } } },
        { data: { status: 'success' } },
    ];
    for (const payload of payloads) {
        const harness = pageHarness(async () => payload);
        harness.render();
        harness.flushEffects();
        await settle();
        const tree = harness.render();
        assert.match(text(tree), /Konfigurasi ambang belum dapat dimuat/);
        assert.doesNotMatch(text(tree), /Hanya baca|0\.50|0\.60/);
        assertReadOnly(tree, harness);
        harness.unmount();
    }
});

test('displayed value comes from the response rather than a hardcoded fallback', async () => {
    const harness = pageHarness(async () => result(0.75));
    harness.render();
    harness.flushEffects();
    await settle();
    const tree = harness.render();
    assert.match(text(tree), /0\.75/);
    assert.doesNotMatch(text(tree), /0\.50|0\.60/);
    assertReadOnly(tree, harness);
    harness.unmount();
});

test('unmount aborts the read and ignores a late response', async () => {
    let resolve;
    const harness = pageHarness(() => new Promise(done => { resolve = done; }));
    const tree = harness.render();
    assert.equal([...elements(tree)].find(node => node.type === 'button').props.disabled, true);
    harness.flushEffects();
    const beforeUnmount = harness.updates;
    harness.unmount();
    assert.equal(harness.requests[0].config.signal.aborted, true);
    resolve(result(0.5));
    await settle();
    assert.equal(harness.updates, beforeUnmount);
    assert.equal(harness.writes.length, 0);
});

test('admin hook starts with an unknown threshold and loads the actual value', async () => {
    const harness = pageHarness(async url => {
        if (url === '/api/v1/admin/stats') {
            return { data: { status: 'success', data: { active_threshold: 0.5, threshold_editable: false } } };
        }
        assert.equal(url, '/api/v1/admin/logs/recent');
        return { data: { data: [] } };
    }, 'hooks/useAdminDashboard.ts', 'useAdminDashboard');
    assert.equal(harness.render().threshold, null);
    harness.flushEffects();
    await settle();
    const state = harness.render();
    assert.equal(state.threshold, 0.5);
    assert.equal(state.loading, false);
    assert.equal(state.error, null);
    assert.deepEqual(harness.requests.map(request => request.url), [
        '/api/v1/admin/stats', '/api/v1/admin/logs/recent',
    ]);
    harness.flushEffects();
    await settle();
    assert.equal(harness.requests.length, 2);
    assert.equal(harness.writes.length, 0);
    harness.unmount();
});

test('admin hook keeps missing or malformed thresholds unknown instead of inventing 0.60', async () => {
    for (const active of [undefined, null, NaN, Infinity, -0.1, 1.1, '0.5']) {
        const harness = pageHarness(async url => ({ data: { data:
            url === '/api/v1/admin/stats'
                ? { active_threshold: active }
                : [],
        } }), 'hooks/useAdminDashboard.ts', 'useAdminDashboard');
        assert.equal(harness.render().threshold, null);
        harness.flushEffects();
        await settle();
        assert.equal(harness.render().threshold, null);
        assert.equal(harness.writes.length, 0);
        harness.unmount();
    }
});
