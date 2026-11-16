// Isolated admin-users hook checks: mocked HTTP/storage, no app startup or real database.
// Run with: node --test tests/test_admin_users.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');

const frontend = path.resolve(__dirname, '../frontend');
const frontendRequire = createRequire(path.join(frontend, 'package.json'));
const ts = frontendRequire('typescript');
const ADMIN_A = '11111111-1111-4111-8111-111111111111';
const ADMIN_B = '22222222-2222-4222-8222-222222222222';
const USER_A = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const USER_B = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const USER_C = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';

function deferred() {
    let resolve;
    let reject;
    const promise = new Promise((done, fail) => { resolve = done; reject = fail; });
    return { promise, resolve, reject };
}

function user(id = USER_A, overrides = {}) {
    return {
        id,
        name: id === USER_A ? 'Pengguna Uji A' : 'Pengguna Uji B',
        email: id === USER_A ? 'user-a@example.test' : 'user-b@example.test',
        role: 'USER',
        analysis_count: 0,
        has_password: true,
        google_linked: false,
        is_active: true,
        created_at: '2026-11-16T02:00:00Z',
        ...overrides,
    };
}

function list(users = [user()], total = users.length, params = {}) {
    return { data: {
        status: 'success', data: users, total, count: users.length,
        skip: params.skip ?? 0, limit: params.limit ?? 20,
    } };
}

function statusReply(id = USER_A, isActive = false) {
    return { data: { status: 'success', message: 'Status akun berhasil diperbarui.',
        data: { id, is_active: isActive } } };
}

function httpError(status, detail) {
    return { isAxiosError: true, message: 'Request failed',
        response: { status, data: { detail } } };
}

function plain(value) { return JSON.parse(JSON.stringify(value)); }
function ids(view) { return Array.from(view.value.users, row => row.id); }
function saving(view, id) { return new Set(view.value.savingIds).has(id); }

function fixture(options = {}) {
    const slots = [];
    const cache = new Map();
    const storage = new Map();
    const calls = { get: [], patch: [] };
    let enabled = options.enabled ?? true;
    let adminId = options.adminId ?? ADMIN_A;
    let dirty = false;
    let index = 0;
    let pendingEffects = [];
    let value;
    let mounted = true;
    if (options.token !== null) storage.set('token', options.token ?? 'isolated-admin-session-a');

    const sameDeps = (before, after) => before && after && before.length === after.length &&
        before.every((item, position) => Object.is(item, after[position]));
    const hooks = {
        useState(initial) {
            const position = index++;
            if (!slots[position]) slots[position] = { value: typeof initial === 'function' ? initial() : initial };
            return [slots[position].value, next => {
                const result = typeof next === 'function' ? next(slots[position].value) : next;
                if (!Object.is(result, slots[position].value)) {
                    slots[position].value = result;
                    dirty = true;
                }
            }];
        },
        useRef(initial) {
            const position = index++;
            if (!slots[position]) slots[position] = { ref: { current: initial } };
            return slots[position].ref;
        },
        useCallback(callback, deps) {
            const position = index++;
            if (!slots[position] || !sameDeps(slots[position].deps, deps)) slots[position] = { callback, deps };
            return slots[position].callback;
        },
        useMemo(factory, deps) {
            const position = index++;
            if (!slots[position] || !sameDeps(slots[position].deps, deps)) slots[position] = { value: factory(), deps };
            return slots[position].value;
        },
        useEffect(callback, deps) {
            const position = index++;
            if (!slots[position] || !sameDeps(slots[position].deps, deps)) {
                const previous = slots[position];
                slots[position] = { deps, cleanup: previous?.cleanup };
                pendingEffects.push(() => {
                    slots[position].cleanup?.();
                    slots[position].cleanup = callback();
                });
            }
        },
    };
    const localStorage = {
        getItem: key => storage.get(key) ?? null,
        setItem: (key, next) => storage.set(key, String(next)),
        removeItem: key => storage.delete(key),
    };
    const apiClient = {
        async get(url, config = {}) {
            const call = { url, config: { ...config, params: { ...config.params } } };
            calls.get.push(call);
            return options.get ? options.get(call, calls.get.length) : list([user()], 1, config.params);
        },
        async patch(url, payload, config = {}) {
            const call = { url, payload: { ...payload }, config };
            calls.patch.push(call);
            return options.patch ? options.patch(call, calls.patch.length) : statusReply();
        },
    };
    const mocks = {
        react: hooks,
        '@/lib/apiClient': {
            apiClient,
            getApiConnectionMessage: error => error?.code === 'ERR_NETWORK' ? 'Tidak dapat terhubung ke server.' : null,
        },
    };

    function load(relativePath) {
        if (cache.has(relativePath)) return cache.get(relativePath);
        const filename = path.join(frontend, 'src', relativePath);
        const { outputText } = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
            fileName: filename,
            compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
        });
        const module = { exports: {} };
        cache.set(relativePath, module.exports);
        vm.runInNewContext(outputText, {
            module, exports: module.exports, console,
            AbortController, AbortSignal, DOMException, URL, Event,
            localStorage, window: { localStorage },
            require: name => Object.hasOwn(mocks, name) ? mocks[name] :
                name.startsWith('@/') ? load(name.slice(2) + '.ts') : frontendRequire(name),
        }, { filename });
        cache.set(relativePath, module.exports);
        return module.exports;
    }

    const { useAdminUsers } = load('hooks/useAdminUsers.ts');
    function render() {
        assert.ok(mounted, 'Cannot render an unmounted hook');
        index = 0;
        dirty = false;
        pendingEffects = [];
        value = useAdminUsers(enabled, adminId);
        for (const effect of pendingEffects) effect();
        return value;
    }
    async function flush() {
        for (let pass = 0; pass < 40; pass++) {
            await Promise.resolve();
            if (dirty && mounted) render();
        }
    }
    function changeContext(next) {
        if (Object.hasOwn(next, 'enabled')) enabled = next.enabled;
        if (Object.hasOwn(next, 'adminId')) adminId = next.adminId;
        if (Object.hasOwn(next, 'token')) {
            if (next.token === null) storage.delete('token');
            else storage.set('token', next.token);
        }
        render();
    }
    function unmount() {
        for (const slot of slots) slot?.cleanup?.();
        mounted = false;
    }
    render();
    return { get value() { return value; }, calls, render, flush, changeContext, unmount };
}

test('disabled or anonymous admin users hook never requests or invents empty totals', async () => {
    for (const options of [{ enabled: false }, { token: null }]) {
        const view = fixture(options);
        await view.flush();
        assert.equal(view.calls.get.length, 0);
        assert.equal(view.value.total, null);
        assert.equal(view.value.count, null);
        assert.equal(view.value.hasLoaded, false);
        assert.equal(view.value.isEmpty, false);
        assert.equal(view.value.loading, false);
        assert.deepEqual(ids(view), []);
        await view.value.reload();
        await view.value.updateStatus(USER_A, false);
        assert.equal(view.calls.get.length, 0);
        assert.equal(view.calls.patch.length, 0);
    }
});

test('a successful list uses real account capabilities and analysis_count including zero', async () => {
    const googleUser = user(USER_A, { has_password: false, google_linked: true });
    const view = fixture({ get: async () => list([googleUser], 7) });
    assert.equal(view.value.total, null);
    assert.equal(view.value.count, null);
    await view.flush();
    assert.equal(view.calls.get[0].url, '/api/v1/admin/users');
    assert.deepEqual(plain(view.calls.get[0].config.params), { skip: 0, limit: 20 });
    assert.equal(view.value.users[0].analysis_count, 0);
    assert.equal(view.value.users[0].has_password, false);
    assert.equal(view.value.users[0].google_linked, true);
    assert.equal(view.value.total, 7);
    assert.equal(view.value.count, 1);
    assert.equal(view.value.hasLoaded, true);
    assert.equal(view.value.isEmpty, false);
    assert.equal(view.value.error, null);
});

test('filters reset pagination and retain an explicit inactive false value', async () => {
    const view = fixture({ get: async call => list([user()], 100, call.config.params) });
    await view.flush();
    view.value.setPage(40, 20);
    await view.flush();
    assert.equal(view.calls.get.at(-1).config.params.skip, 40);
    view.value.setFilters({ search: '  pengguna  ', role: 'USER', is_active: false });
    await view.flush();
    const params = view.calls.get.at(-1).config.params;
    assert.equal(params.skip, 0);
    assert.equal(params.limit, 20);
    assert.equal(params.search, 'pengguna');
    assert.equal(params.role, 'USER');
    assert.equal(params.is_active, false);
});

test('successful empty response and list failure remain distinct', async () => {
    const empty = fixture({ get: async () => list([], 0) });
    await empty.flush();
    assert.equal(empty.value.total, 0);
    assert.equal(empty.value.count, 0);
    assert.equal(empty.value.hasLoaded, true);
    assert.equal(empty.value.isEmpty, true);
    assert.equal(empty.value.error, null);
    const failed = fixture({ get: async () => { throw httpError(503, 'Database sementara tidak tersedia.'); } });
    await failed.flush();
    assert.equal(failed.value.total, null);
    assert.equal(failed.value.count, null);
    assert.equal(failed.value.isEmpty, false);
    assert.ok(failed.value.error);
    assert.deepEqual(ids(failed), []);
});

test('a denied list refresh clears previously loaded accounts for 401 and 403', async () => {
    for (const status of [401, 403]) {
        const view = fixture({ get: async (_call, attempt) => {
            if (attempt === 1) return list();
            throw httpError(status, 'Akses daftar akun tidak lagi diizinkan.');
        } });
        await view.flush();
        assert.deepEqual(ids(view), [USER_A]);
        assert.equal(view.value.hasLoaded, true);
        assert.equal(await view.value.reload(), false);
        await view.flush();
        assert.deepEqual(ids(view), []);
        assert.equal(view.value.total, null);
        assert.equal(view.value.count, null);
        assert.equal(view.value.hasLoaded, false);
        assert.equal(view.value.loading, false);
        assert.equal(view.value.isEmpty, false);
        assert.ok(view.value.error);
    }
});

test('an empty page beyond available rows is not reported as an empty account dataset', async () => {
    const view = fixture({ get: async call => call.config.params.skip
        ? list([], 5, call.config.params) : list([user()], 5, call.config.params) });
    await view.flush();
    view.value.setPage(20);
    await view.flush();
    assert.equal(view.value.total, 5);
    assert.equal(view.value.count, 0);
    assert.equal(view.value.hasLoaded, true);
    assert.equal(view.value.error, null);
    assert.equal(view.value.isEmpty, false);
    assert.equal(view.value.isPageEmpty, true);
});

const malformedLists = [
    ['count disagrees with data', response => { response.data.count = 2; }],
    ['total is smaller than count', response => { response.data.total = 0; }],
    ['negative analysis count', response => { response.data.data[0].analysis_count = -1; }],
    ['missing analysis count', response => { delete response.data.data[0].analysis_count; }],
    ['password capability is a string', response => { response.data.data[0].has_password = 'false'; }],
    ['missing Google capability', response => { delete response.data.data[0].google_linked; }],
    ['invalid UUID', response => { response.data.data[0].id = 'not-a-uuid'; }],
    ['invalid timestamp', response => { response.data.data[0].created_at = 'not-a-date'; }],
    ['unknown role', response => { response.data.data[0].role = 'OWNER'; }],
    ['unsuccessful envelope', response => { response.data.status = 'failed'; }],
];
for (const [description, breakResponse] of malformedLists) {
    test(`malformed list is a contract error: ${description}`, async () => {
        const response = list();
        breakResponse(response);
        const view = fixture({ get: async () => response });
        await view.flush();
        assert.ok(view.value.error);
        assert.equal(view.value.total, null);
        assert.equal(view.value.count, null);
        assert.equal(view.value.isEmpty, false);
        assert.deepEqual(ids(view), []);
    });
}

test('old filter success cannot supply rows or finish the current request loading state', async () => {
    const old = deferred();
    const current = deferred();
    const view = fixture({ get: (_call, attempt) => attempt === 1 ? old.promise : current.promise });
    await view.flush();
    view.value.setFilters({ search: 'new-filter' });
    await view.flush();
    assert.equal(view.calls.get.length, 2);
    old.resolve(list([user(USER_A)]));
    await view.flush();
    assert.deepEqual(ids(view), []);
    assert.equal(view.value.loading, true);
    assert.equal(view.value.error, null);
    current.resolve(list([user(USER_B)]));
    await view.flush();
    assert.deepEqual(ids(view), [USER_B]);
    assert.equal(view.value.loading, false);
});

test('old filter failure cannot overwrite a newer successful list', async () => {
    const old = deferred();
    const current = deferred();
    const view = fixture({ get: (_call, attempt) => attempt === 1 ? old.promise : current.promise });
    await view.flush();
    view.value.setFilters({ role: 'USER' });
    await view.flush();
    current.resolve(list([user(USER_B)]));
    await view.flush();
    old.reject(httpError(500, 'Old request failed.'));
    await view.flush();
    assert.deepEqual(ids(view), [USER_B]);
    assert.equal(view.value.error, null);
    assert.equal(view.value.loading, false);
});

test('admin session changes hide old accounts and old reload callbacks cannot cancel the new list', async () => {
    const old = deferred();
    const current = deferred();
    const view = fixture({ get: (_call, attempt) => attempt === 1 ? old.promise : current.promise });
    await view.flush();
    const oldReload = view.value.reload;
    view.changeContext({ adminId: ADMIN_B, token: 'isolated-admin-session-b' });
    await view.flush();
    assert.equal(view.calls.get.length, 2);
    assert.equal(view.value.total, null);
    await oldReload();
    await view.flush();
    assert.equal(view.calls.get.length, 2);
    assert.equal(view.calls.get[1].config.signal.aborted, false);
    old.resolve(list([user(USER_A)]));
    await view.flush();
    assert.deepEqual(ids(view), []);
    assert.equal(view.value.loading, true);
    current.resolve(list([user(USER_B)]));
    await view.flush();
    assert.deepEqual(ids(view), [USER_B]);
});

test('disabling the hook after load clears the visible account context', async () => {
    const view = fixture();
    await view.flush();
    view.changeContext({ enabled: false });
    await view.flush();
    assert.deepEqual(ids(view), []);
    assert.equal(view.value.total, null);
    assert.equal(view.value.count, null);
    assert.equal(view.value.error, null);
    assert.equal(view.value.isEmpty, false);
    assert.equal(view.calls.get.length, 1);
});

test('a pre-aborted reload is a no-op', async () => {
    const view = fixture();
    await view.flush();
    const controller = new AbortController();
    controller.abort();
    await view.value.reload(controller.signal);
    await view.flush();
    assert.equal(view.calls.get.length, 1);
    assert.deepEqual(ids(view), [USER_A]);
    assert.equal(view.value.error, null);
    assert.equal(view.value.loading, false);
});

test('cancelling the latest reload preserves rows without leaving loading or an error behind', async () => {
    const pending = deferred();
    const view = fixture({ get: (_call, attempt) => attempt === 1 ? list() : pending.promise });
    await view.flush();
    const controller = new AbortController();
    const reload = view.value.reload(controller.signal);
    await view.flush();
    assert.equal(view.value.loading, true);
    controller.abort();
    pending.reject(new DOMException('Aborted', 'AbortError'));
    assert.equal(await reload, false);
    await view.flush();
    assert.deepEqual(ids(view), [USER_A]);
    assert.equal(view.value.total, 1);
    assert.equal(view.value.count, 1);
    assert.equal(view.value.loading, false);
    assert.equal(view.value.error, null);
});

test('status mutation waits for server confirmation and blocks duplicate same-ID PATCH', async () => {
    const patch = deferred();
    const view = fixture({
        get: async (_call, attempt) => list([user(USER_A, { is_active: attempt === 1 })]),
        patch: () => patch.promise,
    });
    await view.flush();
    const update = view.value.updateStatus(USER_A, false);
    const duplicate = view.value.updateStatus(USER_A, false);
    await view.flush();
    assert.equal(view.calls.patch.length, 1);
    assert.equal(view.calls.patch[0].url, `/api/v1/admin/users/${USER_A}/status`);
    assert.deepEqual(view.calls.patch[0].payload, { is_active: false });
    assert.equal(view.value.users[0].is_active, true, 'The row must not change before a confirmed reply');
    assert.equal(saving(view, USER_A), true);
    patch.resolve(statusReply(USER_A, false));
    const result = await update;
    await duplicate;
    await view.flush();
    assert.equal(result.success, true);
    assert.equal(result.refreshed, true);
    assert.equal(view.calls.get.length, 2);
    assert.equal(view.value.users[0].is_active, false);
    assert.equal(saving(view, USER_A), false);
});

test('failed status mutation preserves account state and reports the server failure', async () => {
    const view = fixture({ patch: async () => { throw httpError(403, 'Target tidak dapat diubah.'); } });
    await view.flush();
    const result = await view.value.updateStatus(USER_A, false);
    await view.flush();
    assert.equal(result.success, false);
    assert.ok(result.message.includes('Target tidak dapat diubah'));
    assert.equal(view.value.users[0].is_active, true);
    assert.equal(view.calls.get.length, 1);
    assert.ok(view.value.mutationError);
    assert.equal(saving(view, USER_A), false);
});

for (const [description, reply] of [
    ['wrong target ID', statusReply(USER_B, false)],
    ['wrong resulting status', statusReply(USER_A, true)],
]) {
    test(`unconfirmed status response is rejected: ${description}`, async () => {
        const view = fixture({ patch: async () => reply });
        await view.flush();
        const result = await view.value.updateStatus(USER_A, false);
        await view.flush();
        assert.equal(result.success, false);
        assert.ok(view.value.mutationError);
        assert.equal(view.value.users[0].is_active, true);
        assert.equal(view.calls.get.length, 1);
        assert.equal(saving(view, USER_A), false);
    });
}

test('confirmed save remains successful when the subsequent list refresh fails', async () => {
    const view = fixture({ get: async (_call, attempt) => {
        if (attempt === 1) return list();
        throw httpError(503, 'Daftar belum dapat dimuat ulang.');
    } });
    await view.flush();
    const result = await view.value.updateStatus(USER_A, false);
    await view.flush();
    assert.equal(result.success, true);
    assert.equal(result.refreshed, false);
    assert.ok(result.message);
    assert.ok(view.value.error);
    assert.equal(view.value.isEmpty, false);
    assert.equal(view.value.total, null);
    assert.equal(view.value.count, null);
    assert.equal(saving(view, USER_A), false);
});

test('abort after a valid PATCH acknowledgement does not turn a confirmed save into failure', async () => {
    const refreshed = deferred();
    const view = fixture({ get: (_call, attempt) => attempt === 1 ? list() : refreshed.promise });
    await view.flush();
    const controller = new AbortController();
    const update = view.value.updateStatus(USER_A, false, controller.signal);
    await view.flush();
    assert.equal(view.calls.patch.length, 1);
    assert.equal(view.calls.get.length, 2, 'The PATCH was acknowledged and started refresh');
    controller.abort();
    refreshed.resolve(list([user(USER_A, { is_active: false })]));
    const result = await update;
    await view.flush();
    assert.equal(result.success, true);
    assert.equal(result.refreshed, true);
    assert.equal(view.value.users[0].is_active, false);
    assert.equal(view.value.mutationError, null);
    assert.equal(saving(view, USER_A), false);
});

test('a status reply from a prior admin session cannot refresh or alter the new session', async () => {
    const patch = deferred();
    const view = fixture({
        get: async (_call, attempt) => list([user(attempt === 1 ? USER_A : USER_B)]),
        patch: () => patch.promise,
    });
    await view.flush();
    const update = view.value.updateStatus(USER_A, false);
    await view.flush();
    view.changeContext({ adminId: ADMIN_B, token: 'isolated-admin-session-b' });
    await view.flush();
    patch.resolve(statusReply(USER_A, false));
    const result = await update;
    await view.flush();
    assert.equal(result.success, false);
    assert.equal(result.cancelled, true);
    assert.deepEqual(ids(view), [USER_B]);
    assert.equal(view.calls.get.length, 2);
    assert.equal(view.value.mutationError, null);
    assert.equal(view.value.error, null);
    assert.equal(new Set(view.value.savingIds).size, 0);
});

test('late status confirmation never reloads an obsolete filter', async () => {
    const patch = deferred();
    const view = fixture({
        get: async call => list([user(call.config.params.search ? USER_B : USER_A)], 1, call.config.params),
        patch: () => patch.promise,
    });
    await view.flush();
    const update = view.value.updateStatus(USER_A, false);
    await view.flush();
    view.value.setFilters({ search: 'current-filter' });
    await view.flush();
    patch.resolve(statusReply(USER_A, false));
    const result = await update;
    await view.flush();
    assert.equal(result.success, true);
    assert.equal(result.refreshed, true);
    assert.equal(view.calls.get.length, 3);
    assert.deepEqual(ids(view), [USER_B]);
    assert.equal(view.value.params.search, 'current-filter');
    for (const call of view.calls.get.slice(2)) assert.equal(call.config.params.search, 'current-filter');
});

test('a status failure from a prior admin session does not contaminate current errors', async () => {
    const patch = deferred();
    const view = fixture({
        get: async (_call, attempt) => list([user(attempt === 1 ? USER_A : USER_C)]),
        patch: () => patch.promise,
    });
    await view.flush();
    const update = view.value.updateStatus(USER_A, false);
    await view.flush();
    view.changeContext({ adminId: ADMIN_B, token: 'isolated-admin-session-b' });
    await view.flush();
    patch.reject(httpError(500, 'Old mutation failed.'));
    const result = await update;
    await view.flush();
    assert.equal(result.cancelled, true);
    assert.deepEqual(ids(view), [USER_C]);
    assert.equal(view.value.mutationError, null);
    assert.equal(view.value.error, null);
    assert.equal(new Set(view.value.savingIds).size, 0);
});
