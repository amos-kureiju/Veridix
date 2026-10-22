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
        module, exports: module.exports, process, console, AbortController, Event, FormData,
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
    const calls = { routes: [], history: [], detections: 0, reloads: 0 };
    const mocks = {
        'next/navigation': { useRouter: () => ({ push: route => calls.routes.push(route) }) },
        '@/hooks/useAuth': { useAuth: () => auth },
        '@/hooks/useDetection': { useDetection: () => ({
            loading: false, result: null, error: null,
            detectText: async () => { calls.detections++; return { status: 'success' }; },
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
    return { tree, form: form.props, calls };
}

test('public homepage stays visible and never enables history before verified login', async () => {
    for (const ready of [false, true]) {
        const { tree, form, calls } = home({ user: null, ready });
        assert.equal(tree.props.guest, true);
        assert.deepEqual(calls.history, [false]);
        assert.deepEqual(calls.routes, []);
        await form.onAnalyze('Presiden memimpin rapat pemerintah tentang kebijakan publik.');
        assert.equal(calls.detections, 0);
        assert.deepEqual(calls.routes, ready ? ['/auth/login'] : []);
    }
});

test('verified user can analyze and refresh private history', async () => {
    const { form, calls } = home({ user: { name: 'Test User', role: 'USER' }, ready: true });
    assert.deepEqual(calls.history, [true]);
    assert.equal(form.loginRequired, false);
    await form.onAnalyze('Presiden memimpin rapat pemerintah tentang kebijakan publik.');
    assert.equal(calls.detections, 1);
    assert.equal(calls.reloads, 1);
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
