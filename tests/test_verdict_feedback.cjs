// Run with: node tests/test_verdict_feedback.cjs
// Component event/state tests with mocked HTTP; no browser, model, or database.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');

const frontend = path.resolve(__dirname, '../frontend');
const frontendRequire = createRequire(path.join(frontend, 'package.json'));
const ts = frontendRequire('typescript');
const axios = frontendRequire('axios');

function load(relativePath, mocks = {}) {
    const filename = path.join(frontend, 'src', relativePath);
    const { outputText } = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
        fileName: filename,
        compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
    });
    const module = { exports: {} };
    vm.runInNewContext(outputText, {
        module, exports: module.exports, process, console, URL,
        alert: () => assert.fail('Feedback must not report success or failure through alert'),
        require: name => Object.hasOwn(mocks, name) ? mocks[name] : frontendRequire(name),
    }, { filename });
    return module.exports;
}

const { getApiConnectionMessage } = load('lib/apiClient.ts');

function component(relativePath, props, mocks = {}) {
    const slots = [];
    let cursor = 0;
    let dirty = false;
    let expectedHooks;
    let pendingEffects = [];
    const react = {
        useState(initial) {
            const i = cursor++;
            if (!(i in slots)) slots[i] = { value: initial };
            return [slots[i].value, next => {
                const value = typeof next === 'function' ? next(slots[i].value) : next;
                if (!Object.is(value, slots[i].value)) dirty = true;
                slots[i].value = value;
            }];
        },
        useRef(initial) {
            const i = cursor++;
            if (!(i in slots)) slots[i] = { current: initial };
            return slots[i];
        },
        useEffect(effect, deps) {
            const i = cursor++;
            const previous = slots[i];
            if (!previous || !deps || deps.some((value, j) => !Object.is(value, previous.deps[j]))) {
                pendingEffects.push(() => {
                    previous?.cleanup?.();
                    slots[i] = { deps, cleanup: effect() };
                });
            }
        },
    };
    const Component = load(relativePath, { ...mocks, react }).default;
    return {
        render(nextProps = props) {
            props = nextProps;
            let tree;
            let rounds = 0;
            do {
                assert.ok(rounds++ < 10, 'Effects must settle');
                cursor = 0;
                dirty = false;
                pendingEffects = [];
                tree = Component(props);
                if (expectedHooks === undefined) expectedHooks = cursor;
                else assert.equal(cursor, expectedHooks, 'Hooks must not change across early returns');
                const effects = pendingEffects;
                pendingEffects = [];
                effects.forEach(effect => effect());
            } while (dirty);
            return tree;
        },
        unmount() { slots.forEach(slot => slot?.cleanup?.()); },
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
    if (node === null || node === undefined || typeof node === 'boolean') return '';
    if (Array.isArray(node)) return node.map(text).join('');
    if (typeof node === 'object') return text(node.props?.children);
    return String(node);
}

function button(tree, label) {
    const found = [...elements(tree)].find(node => node.type === 'button' && text(node).trim() === label);
    assert.ok(found, 'Button missing: ' + label);
    return found;
}

function detection(id = '00000000-0000-4000-8000-000000000001', label = 'BERPOLA HOAKS', status = 'dinilai') {
    return { status: 'success', data: { id, input_text: 'KPU mengumumkan tahapan pemilu.',
        is_political: true, process_status: status, pattern_label: label, explanation: null } };
}

function card(props = {}, post = async () => ({ data: { status: 'success' } })) {
    return component('components/detector/VerdictCard.tsx', {
        result: detection(), loading: false, canAct: true, ...props,
    }, {
        '@/lib/apiClient': { apiClient: { post } },
        './LimeHighlighter': { default: 'LimeHighlighter' },
        './DisclaimerBanner': { default: 'DisclaimerBanner' },
        './FeedbackModal': { default: 'FeedbackModal' },
    });
}

function modalNode(tree) { return [...elements(tree)].find(node => node.type === 'FeedbackModal'); }
function statusNode(tree) { return [...elements(tree)].find(node => node.props.role === 'status'); }
function openModal(parent) {
    button(parent.render(), 'Beri masukan').props.onClick();
    const element = modalNode(parent.render());
    assert.ok(element, 'Feedback modal must open');
    const child = component('components/detector/FeedbackModal.tsx', element.props, {
        '@/lib/apiClient': { getApiConnectionMessage },
    });
    child.render();
    return child;
}
function writeNote(modal, value) {
    [...elements(modal.render())].find(node => node.type === 'textarea').props.onChange({ target: { value } });
}
function deferred() {
    let resolve, reject;
    const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
    return { promise, resolve, reject };
}

for (const model of ['BERPOLA HOAKS', 'TIDAK BERPOLA HOAKS']) {
    for (const claim of ['BERPOLA HOAKS', 'TIDAK BERPOLA HOAKS']) {
        test('feedback canonical payload and agreement: ' + model + ' -> ' + claim, async () => {
            const requests = [];
            let refreshed = 0;
            const parent = card({ result: detection(undefined, model), onFeedbackSubmitted: () => { refreshed++; } },
                async (url, body) => { requests.push({ url, body }); return { data: { status: 'success' } }; });
            const modal = openModal(parent);
            button(modal.render(), 'Menurut saya ' + claim).props.onClick();
            writeNote(modal, '  Klarifikasi dari sumber resmi.  ');
            const tree = modal.render();
            assert.equal([...elements(tree)].find(node => node.type === 'textarea').props.maxLength, 1000);
            await button(tree, 'Kirim Masukan').props.onClick();
            assert.equal(requests.length, 1);
            assert.equal(requests[0].url, '/api/v1/feedback');
            assert.deepEqual(JSON.parse(JSON.stringify(requests[0].body)), {
                detection_id: '00000000-0000-4000-8000-000000000001',
                is_agreed: claim === model, claimed_label: claim, user_notes: 'Klarifikasi dari sumber resmi.',
            });
            assert.equal(modalNode(parent.render()), undefined);
            assert.ok(text(statusNode(parent.render())).includes('telah dikirim'));
            assert.equal(refreshed, 1);
        });
    }
}

test('binary correction disagrees with an ambiguous model decision', async () => {
    let payload;
    const parent = card({ result: detection(undefined, 'PERLU VERIFIKASI (SEED TIDAK SEPAKAT)', 'ambigu') },
        async (_url, body) => { payload = body; return { data: { status: 'success' } }; });
    const modal = openModal(parent);
    await button(modal.render(), 'Kirim Masukan').props.onClick();
    assert.equal(payload.claimed_label, 'BERPOLA HOAKS');
    assert.equal(payload.is_agreed, false);
    assert.equal(payload.user_notes, null);
});

test('422 feedback errors remain inline and preserve claim and draft without success', async () => {
    const parent = card({}, async () => {
        throw new axios.AxiosError('Validation error', 'ERR_BAD_REQUEST', {}, {}, {
            status: 422, data: { detail: [{ msg: 'Catatan tidak valid.' }, { msg: 'Label tidak valid.' }] },
        });
    });
    const modal = openModal(parent);
    button(modal.render(), 'Menurut saya TIDAK BERPOLA HOAKS').props.onClick();
    writeNote(modal, 'Draft yang tetap tersimpan di formulir.');
    await button(modal.render(), 'Kirim Masukan').props.onClick();
    const tree = modal.render();
    const error = [...elements(tree)].find(node => node.props.role === 'alert');
    assert.equal(text(error), 'Catatan tidak valid., Label tidak valid.');
    assert.equal([...elements(tree)].find(node => node.type === 'textarea').props.value, 'Draft yang tetap tersimpan di formulir.');
    assert.ok(button(tree, 'Menurut saya TIDAK BERPOLA HOAKS').props.className.includes('ring-2'));
    assert.ok(modalNode(parent.render()));
    assert.equal(statusNode(parent.render()), undefined);
});

test('network feedback errors preserve the draft and use the connection message', async () => {
    const parent = card({}, async () => { throw new axios.AxiosError('Network Error', 'ERR_NETWORK', {}, {}); });
    const modal = openModal(parent);
    writeNote(modal, 'Draft ketika jaringan terputus.');
    await button(modal.render(), 'Kirim Masukan').props.onClick();
    const tree = modal.render();
    assert.equal(text([...elements(tree)].find(node => node.props.role === 'alert')),
        'Tidak dapat terhubung ke server. Periksa koneksi dan pastikan backend aktif.');
    assert.equal([...elements(tree)].find(node => node.type === 'textarea').props.value, 'Draft ketika jaringan terputus.');
    assert.equal(statusNode(parent.render()), undefined);
});

test('duplicate submits are synchronously blocked while loading and controls are disabled', async () => {
    const pending = deferred();
    let requests = 0;
    const parent = card({}, async () => { requests++; return pending.promise; });
    const modal = openModal(parent);
    const submit = button(modal.render(), 'Kirim Masukan').props.onClick;
    const first = submit();
    await submit();
    const busy = modal.render();
    assert.equal(requests, 1);
    assert.equal(button(busy, 'Mengirim...').props.disabled, true);
    assert.equal(button(busy, 'Batal').props.disabled, true);
    assert.equal([...elements(busy)].find(node => node.type === 'textarea').props.disabled, true);
    button(busy, 'Batal').props.onClick();
    assert.ok(modalNode(parent.render()));
    pending.resolve({ data: { status: 'success' } });
    await first;
    assert.equal(requests, 1);
    assert.ok(statusNode(parent.render()));
});

test('notes longer than 1000 characters are rejected before HTTP', async () => {
    let requests = 0;
    const parent = card({}, async () => { requests++; return { data: { status: 'success' } }; });
    const modal = openModal(parent);
    writeNote(modal, 'x'.repeat(1001));
    await button(modal.render(), 'Kirim Masukan').props.onClick();
    assert.equal(requests, 0);
    assert.equal(text([...elements(modal.render())].find(node => node.props.role === 'alert')), 'Catatan maksimal 1000 karakter.');
});

test('feedback requires a session, result ID, and an eligible model decision', () => {
    const cases = [
        { canAct: false },
        { result: detection(null) },
        { result: detection(undefined, 'TIDAK DAPAT DINILAI', 'ditolak') },
        { result: detection(undefined, 'DI LUAR CAKUPAN', 'di_luar_domain') },
        { result: detection(undefined, 'UNKNOWN', 'dinilai') },
    ];
    for (const props of cases) {
        const parent = card(props, async () => assert.fail('Ineligible feedback submitted'));
        const control = button(parent.render(), 'Beri masukan');
        assert.equal(control.props.disabled, true);
        control.props.onClick();
        assert.equal(modalNode(parent.render()), undefined);
    }
});

test('late feedback completion cannot close another result modal or show success there', async () => {
    const pending = deferred();
    let refreshed = 0;
    const parent = card({ onFeedbackSubmitted: () => { refreshed++; } }, async () => pending.promise);
    const firstModal = openModal(parent);
    const sending = button(firstModal.render(), 'Kirim Masukan').props.onClick();
    firstModal.unmount();
    parent.render({ result: detection('00000000-0000-4000-8000-000000000002'), loading: false, canAct: true,
        onFeedbackSubmitted: () => { refreshed++; } });
    openModal(parent);
    pending.resolve({ data: { status: 'success' } });
    await sending;
    assert.equal(modalNode(parent.render()).key, '00000000-0000-4000-8000-000000000002');
    assert.equal(statusNode(parent.render()), undefined);
    assert.equal(refreshed, 0);
});

test('session invalidation hides the modal and discards its late success', async () => {
    const pending = deferred();
    const parent = card({}, async () => pending.promise);
    const modal = openModal(parent);
    const sending = button(modal.render(), 'Kirim Masukan').props.onClick();
    modal.unmount();
    parent.render({ result: detection(), loading: false, canAct: false });
    pending.resolve({ data: { status: 'success' } });
    await sending;
    assert.equal(modalNode(parent.render()), undefined);
    assert.equal(statusNode(parent.render()), undefined);
    assert.equal(button(parent.render(), 'Beri masukan').props.disabled, true);
});

test('refresh callback failure does not turn already saved feedback into a submission failure', async () => {
    let requests = 0;
    const parent = card({ onFeedbackSubmitted: async () => { throw new Error('Refresh unavailable'); } },
        async () => { requests++; return { data: { status: 'success' } }; });
    const modal = openModal(parent);
    await button(modal.render(), 'Kirim Masukan').props.onClick();
    assert.equal(requests, 1);
    assert.equal(modalNode(parent.render()), undefined);
    assert.ok(statusNode(parent.render()));
});

test('saved acknowledgement survives a temporary permission refresh for the same result', async () => {
    const props = { result: detection(), loading: false, canAct: true };
    let parent;
    const refreshedProps = { ...props, onFeedbackSubmitted: async () => {
        parent.render({ ...refreshedProps, canAct: false });
        assert.equal(statusNode(parent.render()), undefined);
        parent.render(refreshedProps);
    } };
    parent = card(refreshedProps);
    const modal = openModal(parent);
    await button(modal.render(), 'Kirim Masukan').props.onClick();
    assert.ok(statusNode(parent.render()));
    assert.equal(modalNode(parent.render()), undefined);
});

test('a response without success acknowledgement does not close the draft or show success', async () => {
    const parent = card({}, async () => ({ data: { status: 'error' } }));
    const modal = openModal(parent);
    writeNote(modal, 'Menunggu konfirmasi penyimpanan.');
    await button(modal.render(), 'Kirim Masukan').props.onClick();
    assert.ok(modalNode(parent.render()));
    assert.equal(statusNode(parent.render()), undefined);
    assert.equal(text([...elements(modal.render())].find(node => node.props.role === 'alert')),
        'Umpan balik gagal dikirim. Coba lagi.');
});

test('card hooks remain stable through empty, loading, and result states; PDF remains disabled', () => {
    const parent = card({ result: null });
    parent.render();
    parent.render({ result: null, loading: true, canAct: true });
    parent.render({ result: detection(), loading: false, canAct: true });
    const tree = parent.render();
    assert.equal(button(tree, 'Unduh PDF').props.disabled, true);
    assert.equal([...elements(tree)].some(node => node.type === 'button' && text(node).trim() === 'Simpan'), false);
});

test('collapsing and expanding an existing LIME explanation preserves its data without refetching', () => {
    let explanationRequests = 0;
    const result = detection();
    result.data.explanation = {
        explanation_available: true,
        num_samples: 200,
        tokens: [
            { word: 'klaim', weight: 0.1234, influence: 'KE_HOAKS' },
            { word: 'resmi', weight: -0.4321, influence: 'KE_TIDAK_HOAKS' },
        ],
        top_hoax_words: [{ word: 'klaim', score: 0.1234 }],
        top_fact_words: [{ word: 'resmi', score: 0.4321 }],
    };
    const original = JSON.stringify(result);
    const parent = card({ result, onRequestExplanation: () => { explanationRequests++; } },
        async () => assert.fail('Toggling an existing explanation must not send an HTTP request'));
    const toggle = tree => [...elements(tree)].find(node => node.type === 'button' && typeof node.props['aria-expanded'] === 'boolean');
    const highlighter = tree => [...elements(tree)].find(node => node.type === 'LimeHighlighter');
    const initial = parent.render();
    assert.equal(toggle(initial).props['aria-expanded'], true);
    const firstProps = highlighter(initial).props;
    toggle(initial).props.onClick();
    const collapsed = parent.render();
    assert.equal(toggle(collapsed).props['aria-expanded'], false);
    assert.equal(highlighter(collapsed), undefined);
    toggle(collapsed).props.onClick();
    const expanded = parent.render();
    assert.equal(toggle(expanded).props['aria-expanded'], true);
    const restored = highlighter(expanded).props;
    assert.equal(restored.numSamples, 200);
    assert.equal(restored.prediction, 'HOAKS');
    assert.equal(restored.confidenceScore, undefined);
    assert.deepEqual(JSON.parse(JSON.stringify(restored.tokens)), result.data.explanation.tokens);
    assert.equal(restored.tokens[0].weight, 0.1234);
    assert.equal(restored.tokens[1].weight, -0.4321);
    assert.equal(restored.topHoax, firstProps.topHoax);
    assert.equal(restored.topFact, firstProps.topFact);
    assert.equal(JSON.stringify(result), original);
    assert.equal(explanationRequests, 0);
});

test('feedback still submits correctly while an existing LIME explanation is collapsed', async () => {
    let explanationRequests = 0;
    const requests = [];
    const result = detection();
    result.data.explanation = { explanation_available: true, num_samples: 200,
        tokens: [{ word: 'klaim', weight: 0.2, influence: 'KE_HOAKS' }] };
    const parent = card({ result, onRequestExplanation: () => { explanationRequests++; } },
        async (url, body) => { requests.push({ url, body }); return { data: { status: 'success' } }; });
    const toggle = tree => [...elements(tree)].find(node => node.type === 'button' && typeof node.props['aria-expanded'] === 'boolean');
    toggle(parent.render()).props.onClick();
    const modal = openModal(parent);
    button(modal.render(), 'Menurut saya TIDAK BERPOLA HOAKS').props.onClick();
    await button(modal.render(), 'Kirim Masukan').props.onClick();
    assert.equal(requests.length, 1);
    assert.equal(requests[0].url, '/api/v1/feedback');
    assert.equal(requests[0].body.claimed_label, 'TIDAK BERPOLA HOAKS');
    assert.equal(requests[0].body.is_agreed, false);
    assert.ok(statusNode(parent.render()));
    assert.equal(toggle(parent.render()).props['aria-expanded'], false);
    assert.equal([...elements(parent.render())].some(node => node.type === 'LimeHighlighter'), false);
    assert.equal(explanationRequests, 0);
});
