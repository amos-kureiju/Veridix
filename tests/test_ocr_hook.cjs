// Hook state/request tests with mocked HTTP; no browser, OCR engine, or database.
// Run with: node --test tests/test_ocr_hook.cjs
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
        module, exports: module.exports, process, console,
        AbortController, AbortSignal, DOMException, FormData, Blob, URL, setTimeout, clearTimeout,
        require: name => Object.hasOwn(mocks, name) ? mocks[name] :
            name.startsWith('@/types/') ? load(name.slice(2) + '.ts', mocks) : frontendRequire(name),
    }, { filename });
    return module.exports;
}

const { getApiConnectionMessage } = load('lib/apiClient.ts');

function hook(post, { deferFunctionalUpdates = false } = {}) {
    const slots = [];
    const stateUpdates = [];
    let cursor = 0;
    let pendingEffects = [];
    const changed = (previous, deps) => !previous || !deps ||
        deps.length !== previous.deps?.length || deps.some((value, i) => !Object.is(value, previous.deps[i]));
    const react = {
        useState(initial) {
            const i = cursor++;
            if (!(i in slots)) slots[i] = { value: typeof initial === 'function' ? initial() : initial };
            return [slots[i].value, next => {
                if (deferFunctionalUpdates && typeof next === 'function') {
                    stateUpdates.push(() => { slots[i].value = next(slots[i].value); });
                    return;
                }
                slots[i].value = typeof next === 'function' ? next(slots[i].value) : next;
            }];
        },
        useRef(initial) {
            const i = cursor++;
            if (!(i in slots)) slots[i] = { current: initial };
            return slots[i];
        },
        useCallback(callback, deps) {
            const i = cursor++;
            if (changed(slots[i], deps)) slots[i] = { value: callback, deps };
            return slots[i].value;
        },
        useEffect(effect, deps) {
            const i = cursor++;
            if (changed(slots[i], deps)) pendingEffects.push(() => {
                slots[i]?.cleanup?.();
                slots[i] = { deps, cleanup: effect() };
            });
        },
    };
    const { useDetection } = load('hooks/useDetection.ts', {
        react, '@/lib/apiClient': { apiClient: { post }, getApiConnectionMessage },
    });
    return {
        render() {
            stateUpdates.splice(0).forEach(update => update());
            cursor = 0;
            pendingEffects = [];
            const state = useDetection();
            pendingEffects.forEach(effect => effect());
            return state;
        },
        unmount() { slots.forEach(slot => slot?.cleanup?.()); },
    };
}

function deferred() {
    let resolve, reject;
    const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
    return { promise, resolve, reject };
}

function file() {
    return Object.assign(new Blob(['synthetic image bytes'], { type: 'image/png' }), { name: 'berita.png' });
}

function ocr(text = 'KPU mengumumkan jadwal pemilu kepada seluruh warga Indonesia melalui pengumuman resmi.') {
    return { status: 'success', message: 'Teks berhasil diekstrak.', data: {
        extracted_text: text, dapat_dinilai: true, confidence: 0.97, character_count: text.length,
        image_url: 'https://images.example.test/berita.png', reason: null,
    } };
}

function verdict() {
    return { status: 'success', data: {
        id: 'existing-verdict', input_text: 'Naskah yang telah dianalisis.',
        process_status: 'dinilai', pattern_label: 'TIDAK BERPOLA HOAKS', is_political: true,
    } };
}

test('OCR uses one multipart request with a cancel signal and keeps verdict/LIME state separate', async () => {
    const requests = [];
    const pending = deferred();
    const result = verdict();
    const runtime = hook(async (url, body, config) => {
        requests.push({ url, body, config });
        if (url === '/api/v1/detect/text') return { data: result };
        return pending.promise;
    });
    await runtime.render().detectText('Naskah analisis sebelumnya yang cukup panjang.');
    const submitted = runtime.render().extractTextFromImage(file());
    let state = runtime.render();
    assert.equal(state.ocrLoading, true);
    assert.equal(state.loading, false);
    assert.equal(state.limeLoading, false);
    assert.equal(state.result, result);
    assert.equal(state.error, null);
    assert.equal(requests.length, 2);
    const request = requests[1];
    assert.equal(request.url, '/api/v1/detect/image');
    assert.ok(request.body instanceof FormData);
    assert.ok(request.body.get('file'));
    assert.ok(request.config.signal instanceof AbortSignal);
    const headers = request.config.headers;
    const contentType = headers?.get?.('Content-Type') ?? headers?.['Content-Type'] ?? headers?.['content-type'];
    assert.notEqual(contentType, 'multipart/form-data', 'Browser must set the multipart boundary');
    assert.equal(request.config.timeout, 180000, 'OCR timeout must be separate from the global timeout');
    const extracted = ocr();
    pending.resolve({ data: extracted });
    assert.equal(await submitted, extracted);
    state = runtime.render();
    assert.equal(state.ocrLoading, false);
    assert.equal(state.ocrError, null);
    assert.equal(state.result, result);
});

test('detectText preserves edited image text/source/server URL and defaults ordinary text to TEXT', async () => {
    const requests = [];
    const runtime = hook(async (url, body) => {
        requests.push({ url, body });
        return { data: verdict() };
    });
    const edited = 'KPU mengoreksi jadwal pemilu dan meminta seluruh warga membaca pengumuman resmi terbaru.';
    const imageUrl = 'https://images.example.test/saved-image.png';
    await runtime.render().detectText(edited, 'IMAGE', imageUrl);
    assert.deepEqual(JSON.parse(JSON.stringify(requests[0].body)), {
        text: edited, input_type: 'IMAGE', image_url: imageUrl,
    });
    await runtime.render().detectText('Naskah teks langsung yang dimasukkan oleh pengguna.');
    assert.equal(requests[1].body.input_type, 'TEXT');
    assert.ok(requests[1].body.image_url == null);
});

test('OCR FormData survives the actual Axios JSON defaults without serializing image bytes as JSON', async () => {
    const { apiClient } = load('lib/apiClient.ts');
    const requests = [];
    apiClient.defaults.adapter = async config => {
        requests.push(config);
        return { status: 200, statusText: 'OK', headers: {}, config, data: ocr() };
    };
    const runtime = hook((...args) => apiClient.post(...args));
    assert.ok(await runtime.render().extractTextFromImage(file()));
    assert.equal(requests.length, 1);
    assert.ok(requests[0].data instanceof FormData, 'Axios transform must preserve the multipart body');
    assert.ok(requests[0].data.get('file'));
    assert.notEqual(requests[0].headers.get('Content-Type'), 'application/json');
    assert.notEqual(requests[0].headers.get('Content-Type'), 'multipart/form-data');
    assert.equal(requests[0].timeout, 180000);
    assert.equal(apiClient.defaults.timeout, 30000);
});

test('transient previews cannot become saved image URLs and TEXT input drops a previous image URL', async () => {
    const bodies = [];
    const runtime = hook(async (_url, body) => { bodies.push(body); return { data: verdict() }; });
    await runtime.render().detectText('Naskah berita yang diperiksa melalui gambar.', 'IMAGE', 'blob:temporary-preview');
    await runtime.render().detectText('Naskah berita yang diperiksa melalui gambar.', 'IMAGE', 'data:image/png;base64,test');
    await runtime.render().detectText('Naskah berita langsung yang diperiksa.', 'TEXT', 'https://images.example.test/old.png');
    assert.ok(bodies.every(body => body.image_url == null));
});

test('OCR accepts nullable confidence and counts Unicode code points consistently with the backend', async () => {
    const text = 'KPU menyampaikan pengumuman pemilu kepada seluruh warga Indonesia melalui kanal resmi. 😀';
    const response = ocr(text);
    response.data.confidence = null;
    response.data.character_count = Array.from(text).length;
    const runtime = hook(async () => ({ data: response }));
    assert.equal(await runtime.render().extractTextFromImage(file()), response);
    assert.equal(runtime.render().ocrError, null);
});

test('replacing an OCR request aborts the old upload and ignores its late success and finalizer', async () => {
    const first = deferred();
    const second = deferred();
    const requests = [];
    const runtime = hook((url, body, config) => {
        requests.push({ url, body, config });
        return requests.length === 1 ? first.promise : second.promise;
    });
    const old = runtime.render().extractTextFromImage(file());
    const current = runtime.render().extractTextFromImage(file());
    assert.equal(requests[0].config.signal.aborted, true);
    assert.equal(requests[1].config.signal.aborted, false);
    first.resolve({ data: ocr('Teks lama yang harus diabaikan oleh antarmuka.') });
    assert.equal(await old, null);
    assert.equal(runtime.render().ocrLoading, true, 'Old completion must not clear the replacement loading state');
    assert.equal(runtime.render().ocrError, null);
    const latest = ocr();
    second.resolve({ data: latest });
    assert.equal(await current, latest);
    assert.equal(runtime.render().ocrLoading, false);
});

test('a late failure from a replaced OCR request cannot overwrite the current error state', async () => {
    const first = deferred();
    const second = deferred();
    let count = 0;
    const runtime = hook(() => (++count === 1 ? first.promise : second.promise));
    const old = runtime.render().extractTextFromImage(file());
    const current = runtime.render().extractTextFromImage(file());
    first.reject({ response: { status: 503, data: { detail: 'Galat dari unggahan lama.' } } });
    assert.equal(await old, null);
    assert.equal(runtime.render().ocrError, null);
    assert.equal(runtime.render().ocrLoading, true);
    second.resolve({ data: ocr() });
    assert.ok(await current);
    assert.equal(runtime.render().ocrError, null);
});

test('reset cancels OCR and prevents a late success from crossing the account/session boundary', async () => {
    const pending = deferred();
    let signal;
    const runtime = hook((_url, _body, config) => { signal = config.signal; return pending.promise; });
    const submitted = runtime.render().extractTextFromImage(file());
    runtime.render().reset();
    assert.equal(signal.aborted, true);
    assert.equal(runtime.render().ocrLoading, false);
    assert.equal(runtime.render().ocrError, null);
    pending.resolve({ data: ocr() });
    assert.equal(await submitted, null);
    assert.equal(runtime.render().result, null);
    assert.equal(runtime.render().ocrError, null);
});

test('cancelImageExtraction aborts immediately and ignores a late transport error', async () => {
    const pending = deferred();
    let signal;
    const runtime = hook((_url, _body, config) => { signal = config.signal; return pending.promise; });
    const submitted = runtime.render().extractTextFromImage(file());
    runtime.render().cancelImageExtraction();
    assert.equal(signal.aborted, true);
    assert.equal(runtime.render().ocrLoading, false);
    pending.reject(new axios.AxiosError('Network Error', 'ERR_NETWORK', {}, {}));
    assert.equal(await submitted, null);
    assert.equal(runtime.render().ocrError, null);
});

test('external cancellation invalidates OCR even when the transport resolves successfully afterward', async () => {
    const pending = deferred();
    let signal;
    const runtime = hook((_url, _body, config) => { signal = config.signal; return pending.promise; });
    const caller = new AbortController();
    const submitted = runtime.render().extractTextFromImage(file(), caller.signal);
    caller.abort();
    assert.equal(signal.aborted, true);
    assert.equal(runtime.render().ocrLoading, false);
    pending.resolve({ data: ocr() });
    assert.equal(await submitted, null);
    assert.equal(runtime.render().ocrError, null);
});

test('an already cancelled external signal never starts an OCR request', async () => {
    let count = 0;
    const runtime = hook(async () => { count++; return { data: ocr() }; });
    const caller = new AbortController();
    caller.abort();
    assert.equal(await runtime.render().extractTextFromImage(file(), caller.signal), null);
    assert.equal(count, 0);
    assert.equal(runtime.render().ocrLoading, false);
    assert.equal(runtime.render().ocrError, null);
});

test('unmount aborts an active OCR upload', async () => {
    const pending = deferred();
    let signal;
    const runtime = hook((_url, _body, config) => { signal = config.signal; return pending.promise; });
    const submitted = runtime.render().extractTextFromImage(file());
    runtime.unmount();
    assert.equal(signal.aborted, true);
    pending.resolve({ data: ocr() });
    assert.equal(await submitted, null);
});

const invalidResponses = [
    ['missing response', null],
    ['error envelope', { ...ocr(), status: 'error', message: 'Pembacaan belum berhasil.' }],
    ['missing data', { status: 'success', message: 'OK' }],
    ['missing eligibility', { ...ocr(), data: { ...ocr().data, dapat_dinilai: undefined } }],
    ['quality rejection', { ...ocr(), data: { ...ocr().data, dapat_dinilai: false, reason: 'Kepercayaan OCR rendah.' } }],
    ['missing text', { ...ocr(), data: { ...ocr().data, extracted_text: undefined } }],
    ['empty text', { ...ocr(), data: { ...ocr().data, extracted_text: '   ' } }],
    ['nonfinite confidence', { ...ocr(), data: { ...ocr().data, confidence: NaN } }],
    ['confidence outside bounds', { ...ocr(), data: { ...ocr().data, confidence: 2 } }],
    ['invalid character count', { ...ocr(), data: { ...ocr().data, character_count: 'not-a-number' } }],
    ['mismatching character count', { ...ocr(), data: { ...ocr().data, character_count: 1 } }],
];
for (const [name, invalid] of invalidResponses) {
    test('OCR rejects invalid runtime success contracts: ' + name, async () => {
        const runtime = hook(async () => ({ data: invalid }));
        const result = await runtime.render().extractTextFromImage(file());
        assert.equal(result, null);
        assert.equal(runtime.render().ocrLoading, false);
        assert.equal(typeof runtime.render().ocrError, 'string');
        assert.ok(runtime.render().ocrError.length > 0);
        assert.equal(runtime.render().result, null);
        assert.equal(runtime.render().error, null, 'OCR failure must not become a model error');
    });
}

const httpErrors = [
    [400, 'Format gambar tidak didukung.'],
    [413, 'Ukuran berkas melebihi 10 MB.'],
    [422, 'Teks yang terbaca terlalu pendek untuk diverifikasi.'],
    [503, 'Mesin OCR mengalami kegagalan. Coba lagi nanti.'],
    [401, 'Sesi login kedaluwarsa atau tidak valid. Silakan login kembali.',
        'Sesi login berakhir. Silakan masuk kembali sebelum mengunggah gambar.'],
];
for (const [status, detail, expected = detail] of httpErrors) {
    test('OCR presents backend HTTP ' + status + ' rejection as its own readable error', async () => {
        const runtime = hook(async () => { throw { response: { status, data: { detail } } }; });
        assert.equal(await runtime.render().extractTextFromImage(file()), null);
        assert.equal(runtime.render().ocrError, expected);
        assert.equal(runtime.render().ocrLoading, false);
        assert.equal(runtime.render().error, null);
    });
}

test('OCR array validation details render as a readable message rather than an object', async () => {
    const runtime = hook(async () => { throw { response: { status: 422, data: {
        detail: [{ msg: 'Berkas harus berupa gambar.' }, { msg: 'Ukuran berkas tidak valid.' }],
    } } }; });
    assert.equal(await runtime.render().extractTextFromImage(file()), null);
    const message = runtime.render().ocrError;
    assert.equal(typeof message, 'string');
    assert.ok(message.includes('Berkas harus berupa gambar.'));
    assert.ok(message.includes('Ukuran berkas tidak valid.'));
    assert.equal(message.includes('[object Object]'), false);
});

for (const [code, expected] of [
    ['ERR_NETWORK', 'Tidak dapat terhubung ke server. Periksa koneksi dan pastikan backend aktif.'],
    ['ECONNABORTED', 'Waktu tunggu server habis. Silakan coba lagi.'],
    ['ETIMEDOUT', 'Waktu tunggu server habis. Silakan coba lagi.'],
]) {
    test('OCR identifies connection/timeout failure: ' + code, async () => {
        const runtime = hook(async () => { throw new axios.AxiosError('private diagnostic', code, {}, {}); });
        assert.equal(await runtime.render().extractTextFromImage(file()), null);
        assert.equal(runtime.render().ocrError, expected);
        assert.equal(runtime.render().ocrLoading, false);
        assert.equal(runtime.render().error, null);
    });
}

test('a new OCR request clears an earlier OCR error without resetting the model verdict', async () => {
    let attempts = 0;
    const second = deferred();
    const runtime = hook((url) => {
        if (url === '/api/v1/detect/text') return Promise.resolve({ data: verdict() });
        if (++attempts === 1) return Promise.reject({ response: { status: 422, data: { detail: 'Gambar pertama buram.' } } });
        return second.promise;
    });
    await runtime.render().detectText('Naskah yang sebelumnya sudah dianalisis.');
    const saved = runtime.render().result;
    await runtime.render().extractTextFromImage(file());
    assert.equal(runtime.render().ocrError, 'Gambar pertama buram.');
    const next = runtime.render().extractTextFromImage(file());
    assert.equal(runtime.render().ocrError, null);
    assert.equal(runtime.render().result, saved);
    second.resolve({ data: ocr() });
    assert.ok(await next);
    assert.equal(runtime.render().ocrError, null);
});

function limeResponse(word = 'klaim') {
    return { status: 'success', message: 'Penjelasan tersedia.', explanation: {
        explanation_available: true,
        tokens: [{ word, weight: 0.2, influence: 'KE_HOAKS' }],
        teks_dijelaskan: 'Naskah yang telah dianalisis.',
    } };
}

test('LIME attaches a confirmed explanation to its result without changing the classification', async () => {
    const requests = [];
    const classified = verdict();
    const explained = limeResponse();
    const runtime = hook(async (url, body, config) => {
        requests.push({ url, body, config });
        return { data: url === '/api/v1/detect/text' ? classified : explained };
    });
    await runtime.render().detectText(classified.data.input_text);
    await runtime.render().requestExplanation();
    const state = runtime.render();
    assert.equal(requests.length, 2);
    assert.equal(requests[1].url, '/api/v1/detect/existing-verdict/explain');
    assert.equal(requests[1].body, null);
    assert.equal(requests[1].config.timeout, 180000);
    assert.ok(requests[1].config.signal instanceof AbortSignal);
    assert.equal(state.result.data.explanation, explained.explanation);
    assert.equal(state.result.data.input_text, classified.data.input_text);
    assert.equal(state.result.data.pattern_label, classified.data.pattern_label);
    assert.equal(state.limeLoading, false);
    assert.equal(state.limeError, null);
    assert.equal(classified.data.explanation, undefined, 'The previous result object must not be mutated');
});

test('LIME applies a queued React result update after request cleanup without losing the explanation', async () => {
    const explained = limeResponse();
    const runtime = hook(async (url) => ({
        data: url === '/api/v1/detect/text' ? verdict() : explained,
    }), { deferFunctionalUpdates: true });
    await runtime.render().detectText('Naskah yang sudah dianalisis oleh model.');
    await runtime.render().requestExplanation();
    const state = runtime.render();
    assert.equal(state.result.data.explanation, explained.explanation);
    assert.equal(state.limeLoading, false);
    assert.equal(state.limeError, null);
});

test('a retained result callback cannot revive its explanation request after reset', async () => {
    const requests = [];
    const runtime = hook(async (url) => {
        requests.push(url);
        return { data: verdict() };
    });
    await runtime.render().detectText('Naskah yang sebelumnya sudah dinilai oleh model.');
    const oldRequest = runtime.render().requestExplanation;
    runtime.render().reset();
    await oldRequest();
    assert.deepEqual(requests, ['/api/v1/detect/text']);
    assert.equal(runtime.render().result, null);
    assert.equal(runtime.render().limeLoading, false);
    assert.equal(runtime.render().limeError, null);
});

test('LIME prevents duplicate requests while the current explanation is pending', async () => {
    const pending = deferred();
    let count = 0;
    const runtime = hook((url) => {
        if (url === '/api/v1/detect/text') return Promise.resolve({ data: verdict() });
        count++;
        return pending.promise;
    });
    await runtime.render().detectText('Naskah yang sudah dinilai oleh model.');
    const first = runtime.render().requestExplanation();
    await runtime.render().requestExplanation();
    assert.equal(count, 1);
    assert.equal(runtime.render().limeLoading, true);
    pending.resolve({ data: limeResponse() });
    await first;
    assert.equal(runtime.render().limeLoading, false);
});

for (const outcome of ['success', 'failure']) {
    test('LIME ignores an old ' + outcome + ' and finalizer after reset even when the record ID repeats', async () => {
        const old = deferred(), current = deferred();
        const signals = [];
        const runtime = hook((url, _body, config) => {
            if (url === '/api/v1/detect/text') return Promise.resolve({ data: verdict() });
            signals.push(config.signal);
            return signals.length === 1 ? old.promise : current.promise;
        });
        await runtime.render().detectText('Naskah akun pertama yang sebelumnya dinilai.');
        const first = runtime.render().requestExplanation();
        runtime.render().reset();
        assert.equal(signals[0].aborted, true);
        await runtime.render().detectText('Naskah konteks baru yang akan dinilai.');
        const second = runtime.render().requestExplanation();
        if (outcome === 'success') old.resolve({ data: limeResponse('lama') });
        else old.reject({ response: { status: 503, data: { detail: 'Galat penjelasan lama.' } } });
        await first;
        assert.equal(runtime.render().limeLoading, true);
        assert.equal(runtime.render().limeError, null);
        assert.equal(runtime.render().result.data.explanation, undefined);
        assert.equal(signals[1].aborted, false);
        await runtime.render().requestExplanation();
        assert.equal(signals.length, 2, 'The old finalizer must not release the new request guard');
        const latest = limeResponse('terbaru');
        current.resolve({ data: latest });
        await second;
        assert.equal(runtime.render().result.data.explanation, latest.explanation);
        assert.equal(runtime.render().limeLoading, false);
    });
}

test('starting a new classification aborts LIME and ignores its late response', async () => {
    const pending = deferred();
    let signal;
    const runtime = hook((url, _body, config) => {
        if (url === '/api/v1/detect/text') return Promise.resolve({ data: verdict() });
        signal = config.signal;
        return pending.promise;
    });
    await runtime.render().detectText('Naskah pertama yang sudah dianalisis.');
    const first = runtime.render().requestExplanation();
    await runtime.render().detectText('Naskah kedua yang baru dianalisis.');
    assert.equal(signal.aborted, true);
    pending.resolve({ data: limeResponse('lama') });
    await first;
    assert.equal(runtime.render().result.data.explanation, undefined);
    assert.equal(runtime.render().limeLoading, false);
    assert.equal(runtime.render().limeError, null);
});

test('unmount aborts LIME and ignores a late response', async () => {
    const pending = deferred();
    let signal;
    const runtime = hook((url, _body, config) => {
        if (url === '/api/v1/detect/text') return Promise.resolve({ data: verdict() });
        signal = config.signal;
        return pending.promise;
    });
    await runtime.render().detectText('Naskah yang sudah dianalisis oleh model.');
    const submitted = runtime.render().requestExplanation();
    const saved = runtime.render().result;
    runtime.unmount();
    assert.equal(signal.aborted, true);
    pending.resolve({ data: limeResponse() });
    await submitted;
    assert.equal(runtime.render().result, saved);
    assert.equal(runtime.render().limeError, null);
});

const invalidExplanations = [
    ['missing body', null],
    ['error envelope', { ...limeResponse(), status: 'error' }],
    ['missing acknowledgement', { explanation: limeResponse().explanation }],
    ['unavailable explanation', { ...limeResponse(), explanation: { explanation_available: false, tokens: [] } }],
    ['missing token array', { ...limeResponse(), explanation: { explanation_available: true } }],
    ['empty token array', { ...limeResponse(), explanation: { explanation_available: true, tokens: [] } }],
    ['no named tokens', { ...limeResponse(), explanation: { explanation_available: true, tokens: [null, {}, { word: ' ' }] } }],
    ['invalid explained text', { ...limeResponse(), explanation: { ...limeResponse().explanation, teks_dijelaskan: null } }],
];
for (const [name, invalid] of invalidExplanations) {
    test('LIME preserves the classification and reports an invalid response: ' + name, async () => {
        const classified = verdict();
        const runtime = hook(async (url) => ({ data: url === '/api/v1/detect/text' ? classified : invalid }));
        await runtime.render().detectText('Naskah yang sudah dianalisis oleh model.');
        await runtime.render().requestExplanation();
        assert.equal(runtime.render().result, classified);
        assert.equal(runtime.render().limeLoading, false);
        assert.equal(typeof runtime.render().limeError, 'string');
        assert.equal(runtime.render().error, null);
    });
}

test('a failed LIME request exposes its reason while preserving the model verdict', async () => {
    const classified = verdict();
    const runtime = hook(async (url) => {
        if (url === '/api/v1/detect/text') return { data: classified };
        throw { response: { status: 503, data: { detail: 'Penjelasan lain sedang diproses.' } } };
    });
    await runtime.render().detectText('Naskah yang sudah dianalisis oleh model.');
    await runtime.render().requestExplanation();
    assert.equal(runtime.render().result, classified);
    assert.equal(runtime.render().limeError, 'Penjelasan lain sedang diproses.');
    assert.equal(runtime.render().limeLoading, false);
});

test('LIME retains a named token with unavailable weight for explicit rendering of partial data', async () => {
    const explained = limeResponse();
    explained.explanation.tokens = [null, { word: 'tersedia', weight: null, influence: 'KE_HOAKS' }];
    const runtime = hook(async (url) => ({ data: url === '/api/v1/detect/text' ? verdict() : explained }));
    await runtime.render().detectText('Naskah yang sudah dianalisis oleh model.');
    await runtime.render().requestExplanation();
    assert.equal(runtime.render().result.data.explanation, explained.explanation);
    assert.equal(runtime.render().result.data.explanation.tokens[1].weight, null);
    assert.equal(runtime.render().limeError, null);
});
