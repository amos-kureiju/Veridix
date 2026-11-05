// Run with: node --test tests/test_frontend_ocr.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');

const frontend = path.resolve(__dirname, '../frontend');
const frontendRequire = createRequire(path.join(frontend, 'package.json'));
const ts = frontendRequire('typescript');

function load(relative, mocks = {}, globals = {}) {
    const filename = path.join(frontend, 'src', relative);
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

function* elements(node) {
    if (Array.isArray(node)) for (const child of node) yield* elements(child);
    else if (node && typeof node === 'object' && node.props) {
        yield node;
        yield* elements(node.props.children);
    }
}

function deferred() {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
}

const original = 'Presiden memimpin rapat pemerintah tentang anggaran pembangunan nasional tahun depan.';
const response = (text = original, imageUrl = null) => ({ status: 'success', message: 'Teks berhasil dibaca.', data: {
    extracted_text: text, dapat_dinilai: true, character_count: text.length, confidence: 0.95, image_url: imageUrl,
} });
const file = (type = 'image/png', contents = 'png-image') => Object.assign(new Blob([contents], { type }), { name: 'berita.png' });

function formHarness(extract = async () => response(), analyze = async () => {}) {
    const slots = [];
    const pendingEffects = [];
    const revoked = [], extractions = [], analyses = [];
    let index = 0, nextUrl = 0, loginPrompts = 0;
    const hooks = {
        useState: initial => {
            const slot = index++;
            if (!(slot in slots)) slots[slot] = { value: slot === 0 ? 'image' : initial };
            return [slots[slot].value, next => {
                slots[slot].value = typeof next === 'function' ? next(slots[slot].value) : next;
            }];
        },
        useRef: initial => {
            const slot = index++;
            if (!(slot in slots)) slots[slot] = { current: initial };
            return slots[slot];
        },
        useEffect: (effect, deps) => {
            const slot = index++;
            if (!(slot in slots) || deps.some((dep, i) => dep !== slots[slot].deps[i])) {
                const previous = slots[slot];
                slots[slot] = { deps };
                pendingEffects.push(() => { previous?.cleanup?.(); slots[slot].cleanup = effect(); });
            }
        },
    };
    const { getApiConnectionMessage } = load('lib/apiClient.ts');
    const Form = load('components/detector/NewsInputForm.tsx', {
        react: hooks,
        '@/lib/apiClient': { getApiConnectionMessage }, // No API fallback is available to this component.
    }, { URL: {
        createObjectURL: () => `blob:ocr-${++nextUrl}`,
        revokeObjectURL: url => revoked.push(url),
    } }).default;
    const props = {
        loading: false, ocrLoading: false, ocrError: null, blocked: false, loginRequired: false,
        onRequireLogin: () => { loginPrompts++; },
        onExtractImage: async (...args) => { extractions.push(args); return extract(...args); },
        onAnalyze: async (...args) => { analyses.push(args); return analyze(...args); },
    };
    const render = () => {
        index = 0;
        const nodes = [...elements(Form(props))];
        for (const effect of pendingEffects.splice(0)) effect();
        return {
            nodes,
            input: nodes.find(node => node.type === 'input' && node.props.type === 'file'),
            editor: nodes.find(node => node.type === 'textarea'),
            submit: nodes.filter(node => node.type === 'button').at(-1),
            remove: nodes.find(node => node.props.title === 'Ganti gambar'),
            alert: nodes.find(node => node.props.role === 'alert'),
        };
    };
    return {
        render, revoked, props, extractions, analyses, get loginPrompts() { return loginPrompts; },
        select: image => render().input.props.onChange({ target: { files: [image], value: 'file' } }),
        unmount: () => { for (const slot of slots) slot?.cleanup?.(); },
    };
}

test('one parent OCR callback drives preview/loading and edited IMAGE submission with the server URL', async () => {
    const pending = deferred();
    const h = formHarness(async () => pending.promise);
    const image = file();
    const upload = h.select(image);
    let view = h.render();
    assert.equal(h.extractions.length, 1);
    assert.equal(h.extractions[0][0], image);
    assert.ok(h.extractions[0][1] instanceof AbortSignal);
    assert.equal(view.submit.props.disabled, true);
    assert.equal(view.editor.props.disabled, true);
    assert.ok(view.nodes.some(node => node.props.role === 'status'));
    assert.equal(view.nodes.find(node => node.type === 'img').props.src, 'blob:ocr-1');
    assert.equal(h.analyses.length, 0);
    pending.resolve(response(original, '/uploads/berita.png'));
    await upload;
    view = h.render();
    assert.equal(view.editor.props.value, original);
    assert.equal(view.submit.props.disabled, false);
    const edited = original.replace('tahun depan', 'tahun 2027');
    view.editor.props.onChange({ target: { value: `  ${edited}  ` } });
    await h.render().submit.props.onClick();
    assert.deepEqual(h.analyses[0], [edited, 'IMAGE', '/uploads/berita.png']);
    assert.equal(h.extractions.length, 1);
    h.unmount();
    assert.deepEqual(h.revoked, ['blob:ocr-1']);
});

test('parent OCR loading keeps analysis disabled until the hook finishes', async () => {
    const h = formHarness();
    await h.select(file());
    h.props.ocrLoading = true;
    assert.equal(h.render().submit.props.disabled, true);
    assert.equal(h.render().editor.props.disabled, true);
    h.props.ocrLoading = false;
    assert.equal(h.render().submit.props.disabled, false);
});

test('hook failure shows the parent quality reason and clearing the image hides that old error', async () => {
    const h = formHarness(async () => null);
    await h.select(file());
    h.props.ocrError = 'Teks terlalu pendek. Unggah gambar dengan teks yang lebih lengkap.';
    const view = h.render();
    assert.equal(view.alert.props.children, h.props.ocrError);
    assert.equal(view.editor.props.value, '');
    assert.equal(view.editor.props.disabled, true);
    assert.equal(view.submit.props.disabled, true);
    await view.submit.props.onClick();
    assert.equal(h.analyses.length, 0);
    view.remove.props.onClick();
    assert.equal(h.render().alert, undefined);
    assert.deepEqual(h.revoked, ['blob:ocr-1']);
});

test('empty, malformed, unsuccessful, and quality-rejected OCR responses cannot reach analysis', async () => {
    const bad = [null, {}, { status: 'success' }, { ...response(), status: 'error', message: 'OCR gagal.' },
        { ...response(), data: { ...response().data, dapat_dinilai: false, reason: 'Gambar terlalu buram.' } },
        { ...response(), data: { ...response().data, extracted_text: '  ' } },
        { ...response(), data: { ...response().data, extracted_text: { value: original } } }];
    for (const result of bad) {
        const h = formHarness(async () => result);
        await h.select(file());
        const view = h.render();
        assert.ok(view.alert);
        assert.equal(view.editor.props.value, '');
        assert.equal(view.editor.props.disabled, true);
        assert.equal(view.submit.props.disabled, true);
        await view.submit.props.onClick();
        assert.equal(h.analyses.length, 0);
    }
});

test('unsupported, empty, and oversized images fail without calling the hook', async () => {
    const tooLarge = file();
    Object.defineProperty(tooLarge, 'size', { value: 10 * 1024 * 1024 + 1 });
    for (const [image, message] of [[file('image/gif'), /Format gambar tidak didukung/],
        [file('image/png', ''), /Berkas gambar kosong/], [tooLarge, /Batas unggahan adalah 10 MB/]]) {
        const h = formHarness();
        await h.select(image);
        assert.match(h.render().alert.props.children, message);
        assert.equal(h.render().submit.props.disabled, true);
        assert.equal(h.extractions.length, 0);
    }
});

test('removing pending OCR aborts it and late success cannot overwrite a replacement', async () => {
    const first = deferred(), second = deferred();
    let requests = 0;
    const h = formHarness(async () => ++requests === 1 ? first.promise : second.promise);
    const firstUpload = h.select(file());
    h.render().remove.props.onClick();
    assert.equal(h.extractions[0][1].aborted, true);
    h.props.ocrLoading = true; // The aborted hook may still be finishing when the next image is selected.
    const secondUpload = h.select(file());
    assert.equal(h.extractions.length, 2);
    first.resolve(response('STALE text from the removed image must never reappear.'));
    await firstUpload;
    assert.equal(h.render().editor.props.value, '');
    assert.equal(h.render().submit.props.disabled, true);
    h.props.ocrLoading = false;
    second.resolve(response(original));
    await secondUpload;
    assert.equal(h.render().editor.props.value, original);
    assert.equal(h.render().submit.props.disabled, false);
    h.unmount();
    assert.deepEqual(h.revoked, ['blob:ocr-1', 'blob:ocr-2']);
});

test('late errors after replacement are ignored and do not clear the accepted OCR text', async () => {
    const first = deferred();
    let requests = 0;
    const h = formHarness(async () => ++requests === 1 ? first.promise : response());
    const oldUpload = h.select(file());
    h.render().remove.props.onClick();
    await h.select(file());
    first.reject(new Error('Old request failed'));
    await oldUpload;
    assert.equal(h.render().editor.props.value, original);
    assert.equal(h.render().alert, undefined);
});

test('rapid duplicate selection calls OCR once and unmount cancels the pending callback', async () => {
    const pending = deferred();
    const h = formHarness(async () => pending.promise);
    const input = h.render().input;
    const first = input.props.onChange({ target: { files: [file()] } });
    await input.props.onChange({ target: { files: [file()] } });
    assert.equal(h.extractions.length, 1);
    h.unmount();
    assert.equal(h.extractions[0][1].aborted, true);
    pending.resolve(response());
    await first;
    assert.deepEqual(h.revoked, ['blob:ocr-1']);
});

test('double analyze clicks before the loading rerender submit only one detection', async () => {
    const pending = deferred();
    const h = formHarness(async () => response(), async () => pending.promise);
    await h.select(file());
    const submit = h.render().submit;
    const first = submit.props.onClick();
    await submit.props.onClick();
    assert.equal(h.analyses.length, 1);
    pending.resolve();
    await first;
    await submit.props.onClick();
    assert.equal(h.analyses.length, 2);
});

test('blob/data image URLs are never forwarded as persistent image metadata', async () => {
    for (const imageUrl of ['blob:untrusted-preview', 'data:image/png;base64,abc', null]) {
        const h = formHarness(async () => response(original, imageUrl));
        await h.select(file());
        await h.render().submit.props.onClick();
        assert.equal(h.analyses[0][2], null);
    }
});

test('direct text uses TEXT and no image URL even after an OCR upload', async () => {
    const h = formHarness(async () => response(original, '/uploads/berita.png'));
    await h.select(file());
    h.render().nodes.filter(node => node.type === 'button')[0].props.onClick();
    h.render().editor.props.onChange({ target: { value: `  ${original}  ` } });
    await h.render().submit.props.onClick();
    assert.deepEqual(h.analyses[0], [original, 'TEXT', null]);
});

test('guest upload and analysis ask for login without calling OCR or detection', async () => {
    const h = formHarness();
    h.props.loginRequired = true;
    await h.select(file());
    await h.render().submit.props.onClick();
    assert.equal(h.loginPrompts, 2);
    assert.equal(h.extractions.length, 0);
    assert.equal(h.analyses.length, 0);
});
