// Run with: node --test tests/test_frontend_guest_access.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');

const frontend = path.resolve(__dirname, '../frontend');
const frontendRequire = createRequire(path.join(frontend, 'package.json'));
const ts = frontendRequire('typescript');

function load(relativePath, mocks = {}, globals = {}) {
    const filename = path.join(frontend, 'src', relativePath);
    const { outputText } = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
        fileName: filename,
        compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
    });
    const module = { exports: {} };
    vm.runInNewContext(outputText, {
        module, exports: module.exports, process, console, AbortController, Event, FormData, URL,
        require: name => Object.hasOwn(mocks, name) ? mocks[name] : frontendRequire(name),
        ...globals,
    }, { filename });
    return module.exports;
}

function reactHooks(initialValues = []) {
    let index = 0;
    const effects = [];
    const updates = [];
    return {
        effects, updates,
        useState: initial => {
            const slot = index++;
            return [slot in initialValues ? initialValues[slot] : initial,
                value => updates.push({ slot, value })];
        },
        useRef: current => ({ current }),
        useCallback: callback => callback,
        useEffect: callback => effects.push(callback),
    };
}

function detectionHook(post) {
    const slots = [];
    let index = 0;
    const hooks = {
        useState: initial => {
            const slot = index++;
            if (!(slot in slots)) slots[slot] = { value: initial };
            return [slots[slot].value, next => {
                slots[slot].value = typeof next === 'function' ? next(slots[slot].value) : next;
            }];
        },
        useRef: initial => {
            const slot = index++;
            if (!(slot in slots)) slots[slot] = { current: initial };
            return slots[slot];
        },
    };
    const { getApiConnectionMessage } = load('lib/apiClient.ts');
    const { useDetection } = load('hooks/useDetection.ts', {
        react: hooks,
        '@/lib/apiClient': { apiClient: { post }, getApiConnectionMessage },
    });
    return () => { index = 0; return useDetection(); };
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

function home(auth) {
    const hooks = reactHooks();
    const calls = { routes: [], history: [], detections: 0, reloads: 0, explanations: 0, resets: 0, profileRefreshes: 0 };
    const mocks = {
        react: hooks,
        'next/navigation': { useRouter: () => ({ push: route => calls.routes.push(route) }) },
        '@/hooks/useAuth': { useAuth: () => ({
            ...auth,
            refreshUser: async () => { calls.profileRefreshes++; },
        }) },
        '@/hooks/useDetection': { useDetection: () => ({
            loading: false, result: null, error: null,
            detectText: async () => { calls.detections++; return { status: 'success' }; },
            requestExplanation: async () => { calls.explanations++; },
            limeLoading: false, limeError: null,
            reset: () => { calls.resets++; },
        }) },
        '@/hooks/useHistory': { useHistory: enabled => {
            calls.history.push(enabled);
            return { reload: async () => { calls.reloads++; } };
        } },
    };
    for (const name of ['layout/UserShell', 'layout/HeaderStats', 'shared/GuestBanner',
        'detector/NewsInputForm', 'detector/VerdictCard']) {
        mocks['@/components/' + name] = { default: name };
    }
    const tree = load('app/page.tsx', mocks).default();
    const form = [...elements(tree)].find(node => node.type === 'detector/NewsInputForm');
    const card = [...elements(tree)].find(node => node.type === 'detector/VerdictCard');
    for (const effect of hooks.effects) effect();
    return { tree, form: form.props, card: card.props, calls };
}

test('public homepage stays visible and never enables history before verified login', async () => {
    for (const ready of [false, true]) {
        const { tree, form, card, calls } = home({ user: null, ready });
        assert.equal(tree.props.guest, true);
        assert.deepEqual(calls.history, [false]);
        assert.deepEqual(calls.routes, []);
        assert.equal(card.canAct, false);
        assert.equal(calls.resets, 1);
        await form.onAnalyze('Presiden memimpin rapat pemerintah tentang kebijakan publik.');
        assert.equal(calls.detections, 0);
        assert.deepEqual(calls.routes, ready ? ['/auth/login'] : []);
    }
});

test('verified user refreshes history and profile counts after detection and feedback', async () => {
    const { form, card, calls } = home({ user: { id: 'user-test', name: 'Test User', role: 'USER' }, ready: true });
    assert.deepEqual(calls.history, [true]);
    assert.equal(form.loginRequired, false);
    assert.equal(card.canAct, true);
    assert.equal(calls.resets, 1);
    await card.onRequestExplanation();
    assert.equal(calls.explanations, 1);
    await form.onAnalyze('Presiden memimpin rapat pemerintah tentang kebijakan publik.');
    assert.equal(calls.detections, 1);
    assert.equal(calls.reloads, 1);
    assert.equal(calls.profileRefreshes, 1);
    await card.onFeedbackSubmitted();
    assert.equal(calls.reloads, 2);
    assert.equal(calls.profileRefreshes, 2);
    assert.deepEqual(calls.routes, []);
});

test('guest analyze and image upload controls ask for login without API calls', async () => {
    const hooks = reactHooks(['image']);
    let requests = 0;
    let loginPrompts = 0;
    const Form = load('components/detector/NewsInputForm.tsx', {
        react: hooks,
        '@/lib/apiClient': { apiClient: { post: async () => { requests++; } } },
    }).default;
    const tree = Form({ loading: false, blocked: false, loginRequired: true,
        onRequireLogin: () => loginPrompts++, onAnalyze: () => assert.fail('Guest analyzed') });
    const nodes = [...elements(tree)];
    const submit = nodes.filter(node => node.type === 'button').at(-1);
    assert.equal(submit.props.disabled, false);
    submit.props.onClick();
    const input = nodes.find(node => node.type === 'input' && node.props.type === 'file');
    await input.props.onChange({ target: { files: [{}] } });
    assert.equal(loginPrompts, 2);
    assert.equal(requests, 0);
});

test('authenticated image upload uses the backend OCR endpoint and actual extracted text', async () => {
    const hooks = reactHooks(['image']);
    const requests = [];
    const Form = load('components/detector/NewsInputForm.tsx', {
        react: hooks,
        '@/lib/apiClient': { apiClient: { post: async (url, body) => {
            requests.push({ url, body });
            return { data: { data: { extracted_text: 'Teks hasil OCR dari gambar.' } } };
        } } },
    }, { URL: { createObjectURL: () => 'blob:test-preview' } }).default;
    const tree = Form({ loading: false, blocked: false, loginRequired: false,
        onRequireLogin: () => assert.fail('Unexpected login'), onAnalyze: async () => {} });
    const input = [...elements(tree)].find(node => node.type === 'input' && node.props.type === 'file');
    await input.props.onChange({ target: { files: [new Blob(['image'], { type: 'image/png' })] } });
    assert.equal(requests.length, 1);
    assert.equal(requests[0].url, '/api/v1/detect/image');
    assert.ok(requests[0].body.get('file'));
    assert.ok(hooks.updates.some(update => update.value === 'Teks hasil OCR dari gambar.'));
});

test('history hook sends no request when disabled or without a token', async () => {
    for (const [enabled, token, expected] of [[false, null, 0], [true, null, 0], [false, 'valid', 0], [true, 'valid', 1]]) {
        const hooks = reactHooks();
        let requests = 0;
        const { useHistory } = load('hooks/useHistory.ts', {
            react: hooks,
            '@/lib/apiClient': { apiClient: { get: async () => {
                requests++; return { data: { data: [] } };
            } } },
        }, { localStorage: { getItem: () => token } });
        const history = useHistory(enabled);
        await history.reload();
        assert.equal(requests, expected);
    }
});

async function rejectedRequest({ token, replacement, url = '/api/v1/users/history' }) {
    const axios = frontendRequire('axios');
    let storedToken = token;
    const events = [];
    const browser = {
        location: { href: 'http://localhost:3000/', pathname: '/' },
        dispatchEvent: event => events.push(event.type),
    };
    const { apiClient } = load('lib/apiClient.ts', {}, {
        window: browser, document: { cookie: '' },
        localStorage: { getItem: () => storedToken, removeItem: () => { storedToken = null; } },
    });
    apiClient.defaults.adapter = async config => {
        if (replacement) storedToken = replacement;
        throw new axios.AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null,
            { status: 401, data: { detail: 'Not authenticated' }, config });
    };
    await assert.rejects(apiClient.get(url), error => error.response.status === 401);
    return { token: storedToken, events, location: browser.location.href };
}

test('401 clears the expired session while preserving the public page', async () => {
    const result = await rejectedRequest({ token: 'expired-test-token' });
    assert.equal(result.token, null);
    assert.deepEqual(result.events, ['auth:session-expired']);
    assert.equal(result.location, 'http://localhost:3000/');
});

test('late 401 response cannot erase a newer login session', async () => {
    const result = await rejectedRequest({ token: 'old-test-token', replacement: 'new-test-token' });
    assert.equal(result.token, 'new-test-token');
    assert.deepEqual(result.events, []);
});

test('anonymous 401 and wrong login preserve the public page and other session state', async () => {
    for (const options of [{ token: null }, { token: 'existing-test-token', url: '/api/v1/auth/login' }]) {
        const result = await rejectedRequest(options);
        assert.equal(result.token, options.token);
        assert.deepEqual(result.events, []);
        assert.equal(result.location, 'http://localhost:3000/');
    }
});

test('API diagnostics identify the request without logging credentials, query, body, or response payload', async () => {
    const axios = frontendRequire('axios');
    const logs = [];
    const { apiClient } = load('lib/apiClient.ts', {}, {
        console: { ...console, error: (...args) => logs.push(args) },
    });
    apiClient.defaults.adapter = async config => {
        throw new axios.AxiosError('private-error-message', 'ERR_BAD_RESPONSE', config, {}, {
            status: 500, data: { detail: 'private-response-payload' }, config,
        });
    };
    await assert.rejects(apiClient.post(
        'https://private-url-user:private-url-password@backend.invalid/api/v1/auth/reset-password?token=private-query-token#private-fragment',
        { password: 'private-request-password' },
        { headers: { Authorization: 'Bearer private-header-token' } }
    ));
    assert.equal(logs.length, 1);
    assert.equal(logs[0][0], '[API Error]:');
    const diagnostic = JSON.parse(JSON.stringify(logs[0][1]));
    assert.deepEqual(diagnostic, {
        method: 'POST', endpoint: '/api/v1/auth/reset-password',
        status: 500, code: 'ERR_BAD_RESPONSE', timeout: 30000,
    });
    const serialized = JSON.stringify(logs);
    for (const secret of ['private-error-message', 'private-response-payload', 'private-url-user',
        'private-url-password', 'private-query-token', 'private-fragment', 'private-request-password',
        'private-header-token', 'backend.invalid']) {
        assert.equal(serialized.includes(secret), false, 'Diagnostic leaked ' + secret);
    }
});

test('network and timeout diagnostics preserve the configured timeout and omit raw error messages', async () => {
    const axios = frontendRequire('axios');
    for (const code of ['ERR_NETWORK', 'ECONNABORTED']) {
        const logs = [];
        const { apiClient } = load('lib/apiClient.ts', {}, {
            console: { ...console, error: (...args) => logs.push(args) },
        });
        apiClient.defaults.adapter = async config => {
            throw new axios.AxiosError('private-network-message', code, config, {});
        };
        await assert.rejects(apiClient.post('/api/v1/detect/text?token=private-query', { text: 'private-input' }));
        assert.equal(apiClient.defaults.timeout, 30000);
        assert.equal(logs.length, 1);
        assert.deepEqual(JSON.parse(JSON.stringify(logs[0][1])), {
            method: 'POST', endpoint: '/api/v1/detect/text', status: null, code, timeout: 30000,
        });
        assert.equal(JSON.stringify(logs).includes('private-'), false);
    }
});

test('cancelled API requests do not produce error diagnostics', async () => {
    const axios = frontendRequire('axios');
    const logs = [];
    const { apiClient } = load('lib/apiClient.ts', {}, {
        console: { ...console, error: (...args) => logs.push(args) },
    });
    apiClient.defaults.adapter = async config => { throw new axios.CanceledError('Cancelled', config); };
    await assert.rejects(apiClient.get('/api/v1/users/history'), error => axios.isCancel(error));
    assert.equal(logs.length, 0);
});

test('login distinguishes connection failure, timeout, invalid credentials, and backend failure', async () => {
    const axios = frontendRequire('axios');
    const { getApiConnectionMessage } = load('lib/apiClient.ts');
    const cases = [
        {
            error: new axios.AxiosError('Network Error', 'ERR_NETWORK', {}, {}),
            expected: 'Tidak dapat terhubung ke server. Periksa koneksi dan pastikan backend aktif.',
        },
        {
            error: new axios.AxiosError('timeout of 30000ms exceeded', 'ECONNABORTED', {}, {}),
            expected: 'Waktu tunggu server habis. Silakan coba lagi.',
        },
        {
            error: new axios.AxiosError('timeout', 'ETIMEDOUT', {}, {}),
            expected: 'Waktu tunggu server habis. Silakan coba lagi.',
        },
        {
            error: new axios.AxiosError('Unauthorized', 'ERR_BAD_REQUEST', {}, {}, {
                status: 401, data: { detail: 'Email atau kata sandi salah.' },
            }),
            expected: 'Email atau kata sandi salah.',
        },
        {
            error: new axios.AxiosError('Unauthorized', 'ERR_BAD_REQUEST', {}, {}, { status: 401, data: {} }),
            expected: 'Email atau kata sandi salah.',
        },
        {
            error: new axios.AxiosError('Validation failed', 'ERR_BAD_REQUEST', {}, {}, {
                status: 422, data: { detail: [{ msg: 'Email tidak valid.' }] },
            }),
            expected: 'Email tidak valid.',
        },
        {
            error: new axios.AxiosError('Server failed', 'ERR_BAD_RESPONSE', {}, {}, { status: 500, data: {} }),
            expected: 'Gagal masuk. Silakan coba lagi.',
        },
    ];
    for (const { error, expected } of cases) {
        const hooks = reactHooks();
        const requests = [];
        const { useAuth } = load('hooks/useAuth.ts', {
            react: hooks,
            '@/lib/apiClient': {
                getApiConnectionMessage,
                apiClient: { post: async (url, body) => { requests.push({ url, body }); throw error; } },
            },
        });
        const outcome = await useAuth().login('user@example.test', 'test-password');
        assert.equal(outcome.success, false);
        assert.equal(outcome.message, expected);
        assert.equal(requests.length, 1);
        assert.equal(requests[0].url, '/api/v1/auth/login');
        assert.equal(hooks.updates.at(-1).value, false);
    }
});

test('detection connection failure clears the previous verdict and explains the network failure', async () => {
    const axios = frontendRequire('axios');
    let requests = 0;
    const render = detectionHook(async url => {
        assert.equal(url, '/api/v1/detect/text');
        requests++;
        if (requests === 1) return { data: {
            status: 'success', data: { id: 'previous-result', is_political: true, pattern_label: 'BERPOLA HOAKS' },
        } };
        throw new axios.AxiosError('Network Error', 'ERR_NETWORK', {}, {});
    });
    await render().detectText('Naskah analisis pertama yang berhasil.');
    assert.equal(render().result.data.id, 'previous-result');
    const outcome = await render().detectText('Naskah berikutnya ketika jaringan terputus.');
    assert.equal(outcome, null);
    assert.equal(render().result, null);
    assert.equal(render().error, 'Tidak dapat terhubung ke server. Periksa koneksi dan pastikan backend aktif.');
    assert.equal(render().loading, false);
    assert.equal(requests, 2);
});

test('LIME timeout keeps the classification and reports the specific timeout without retrying automatically', async () => {
    const axios = frontendRequire('axios');
    const requests = [];
    const render = detectionHook(async (url, body, config) => {
        requests.push({ url, body, config });
        if (url === '/api/v1/detect/text') return { data: {
            status: 'success', data: {
                id: 'detection-A', is_political: true, pattern_label: 'TIDAK BERPOLA HOAKS',
                votes_hoax: '0/3', explanation: null,
            },
        } };
        throw new axios.AxiosError('timeout of 180000ms exceeded', 'ECONNABORTED', {}, {});
    });
    await render().detectText('Naskah politik yang sudah selesai diklasifikasikan.');
    const verdict = render().result;
    await render().requestExplanation();
    assert.equal(render().result, verdict);
    assert.equal(render().result.data.votes_hoax, '0/3');
    assert.equal(render().limeError, 'Waktu tunggu server habis. Silakan coba lagi. Hasil klasifikasi tetap tersedia.');
    assert.equal(render().limeLoading, false);
    assert.equal(requests.length, 2);
    assert.equal(requests[1].url, '/api/v1/detect/detection-A/explain');
    assert.equal(requests[1].config.timeout, 180000);
});

test('registration hook sends the backend payload without creating a login session', async () => {
    const hooks = reactHooks();
    const requests = [];
    const { useAuth } = load('hooks/useAuth.ts', {
        react: hooks,
        '@/lib/apiClient': { apiClient: { post: async (url, body) => {
            requests.push({ url, body });
            return { data: { status: 'success', message: 'Akun berhasil dibuat. Silakan login.' } };
        } } },
    });
    const result = await useAuth().register('  Pengguna Baru  ', '  NEW@example.com  ', 'RegisterTest123!');
    assert.equal(result.success, true);
    assert.equal(requests.length, 1);
    assert.equal(requests[0].url, '/api/v1/auth/register');
    assert.equal(requests[0].body.name, 'Pengguna Baru');
    assert.equal(requests[0].body.email, 'new@example.com');
    assert.equal(requests[0].body.password, 'RegisterTest123!');
    assert.deepEqual(Object.keys(requests[0].body).sort(), ['email', 'name', 'password']);
});

test('registration reports duplicate email, validation errors, and connection failures as text', async () => {
    const cases = [
        ['Alamat email sudah terdaftar.', 'Alamat email sudah terdaftar.'],
        [[{ msg: 'Email tidak valid.' }], 'Email tidak valid.'],
        [undefined, 'Pendaftaran gagal. Silakan coba lagi.'],
    ];
    for (const [detail, expected] of cases) {
        const hooks = reactHooks();
        const { useAuth } = load('hooks/useAuth.ts', {
            react: hooks,
            '@/lib/apiClient': { apiClient: { post: async () => {
                throw { isAxiosError: true, response: detail ? { data: { detail } } : undefined };
            } } },
        });
        const result = await useAuth().register('Pengguna', 'new@example.com', 'RegisterTest123!');
        assert.equal(result.success, false);
        assert.equal(result.message, expected);
    }
});

test('registration page goes to login only after successful account creation', async () => {
    for (const success of [true, false]) {
        const hooks = reactHooks(['Pengguna Baru', 'new@example.com', 'RegisterTest123!', 'RegisterTest123!']);
        const routes = [];
        const { default: RegisterPage } = load('app/auth/register/page.tsx', {
            react: hooks,
            'next/navigation': { useRouter: () => ({ push: route => routes.push(route) }) },
            '@/hooks/useAuth': { useAuth: () => ({ register: async () => ({
                success, message: success ? 'Akun berhasil dibuat.' : 'Email sudah terdaftar.',
            }) }) },
            '@/components/auth/AuthHeading': { default: 'AuthHeading' },
        });
        const form = [...elements(RegisterPage())].find(node => node.type === 'form');
        await form.props.onSubmit({ preventDefault() {} });
        assert.deepEqual(routes, success ? ['/auth/login'] : []);
        if (!success) {
            assert.ok(hooks.updates.some(update => update.value === 'Email sudah terdaftar.'));
            assert.equal(hooks.updates.at(-1).value, false);
        }
    }
});
