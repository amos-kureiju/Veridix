const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { createRequire } = require("node:module");

const frontend = path.join(__dirname, "../frontend");
const frontendRequire = createRequire(path.join(frontend, "package.json"));
const ts = frontendRequire("typescript");

function load(relative, mocks = {}, globals = {}) {
    const filename = path.join(frontend, "src", relative);
    const { outputText } = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
        fileName: filename,
        compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
    });
    const module = { exports: {} };
    vm.runInNewContext(outputText, {
        module,
        exports: module.exports,
        require: name => mocks[name] ?? frontendRequire(name),
        AbortController,
        ...globals,
    });
    return module.exports;
}

function* elements(node) {
    if (Array.isArray(node)) {
        for (const child of node) yield* elements(child);
    } else if (node && typeof node === "object" && node.props) {
        yield node;
        yield* elements(node.props.children);
    }
}

function response(text) {
    return { status: "success", message: "Teks berhasil dibaca.", data: {
        extracted_text: text, dapat_dinilai: true, character_count: Array.from(text).length, confidence: 0.95,
    } };
}

const photo = (name, type = "image/png") => new File(["data"], name, { type });
const tick = () => new Promise(resolve => setImmediate(resolve));

function harness() {
    const slots = [];
    const effects = [];
    const uploads = [];
    const analyses = [];
    const revoked = [];
    let cursor = 0;
    let urls = 0;
    const hooks = {
        useState(initial) {
            const slot = cursor++;
            if (!(slot in slots)) slots[slot] = { value: initial };
            return [slots[slot].value, next => {
                slots[slot].value = typeof next === "function" ? next(slots[slot].value) : next;
            }];
        },
        useRef(initial) {
            const slot = cursor++;
            slots[slot] ??= { current: initial };
            return slots[slot];
        },
        useEffect(effect, dependencies) {
            const slot = cursor++;
            if (!slots[slot] || dependencies.some((value, index) => value !== slots[slot].dependencies[index])) {
                const previous = slots[slot];
                slots[slot] = { dependencies };
                effects.push(() => {
                    previous?.cleanup?.();
                    slots[slot].cleanup = effect();
                });
            }
        },
    };
    const Form = load("components/detector/MultiImageOcrForm.tsx", {
        react: hooks,
        "@/lib/apiClient": { getApiConnectionMessage: () => null },
        "@/types/detector": load("types/detector.ts"),
    }, { URL: {
        createObjectURL: () => `blob:page-${++urls}`,
        revokeObjectURL: url => revoked.push(url),
    } }).default;
    const props = {
        active: true, disabled: false, ocrLoading: false, loginRequired: false,
        onRequireLogin: () => assert.fail("The signed-in fixture must remain signed in"),
        onExtractImage: (file, signal, onFailure) => new Promise(resolve => uploads.push({ file, signal, onFailure, resolve })),
        onAnalyzePages: async pages => analyses.push(JSON.parse(JSON.stringify(pages))),
    };
    const view = () => {
        cursor = 0;
        const nodes = [...elements(Form(props))];
        for (const effect of effects.splice(0)) effect();
        return nodes;
    };
    const button = label => view().find(node => node.type === "button" &&
        (node.props["aria-label"] ?? [node.props.children].flat().join("")) === label);
    return {
        props, uploads, analyses, revoked, view, button,
        select(files) {
            const input = view().find(node => node.type === "input" && node.props.multiple);
            input.props.onChange({ currentTarget: { files, value: "files" } });
        },
        edit(page, text) {
            const editor = view().find(node => node.props["aria-label"] === `Teks halaman ${page}`);
            editor.props.onChange({ currentTarget: { value: text } });
        },
        unmount() {
            for (const slot of slots) slot?.cleanup?.();
        },
    };
}

test("OCR berjalan berurutan dan analisis parsial mempertahankan halaman hilang", async () => {
    const h = harness();
    const files = [1, 2, 3, 4].map(i => photo(`halaman-${i}.png`));
    h.select(files);
    assert.deepEqual(h.uploads.map(item => item.file), files.slice(0, 1));
    assert.equal(h.button("Analisis halaman tersedia (parsial)").props.disabled, true);

    h.uploads[0].resolve(response("Halaman pertama"));
    await tick();
    assert.deepEqual(h.uploads.map(item => item.file), files.slice(0, 2));
    h.uploads[1].resolve(response("Halaman kedua"));
    await tick();
    assert.deepEqual(h.uploads.map(item => item.file), files.slice(0, 3));
    h.uploads[2].onFailure("Foto kurang jelas.");
    h.uploads[2].resolve(null);
    await tick();
    assert.deepEqual(h.uploads.map(item => item.file), files);
    h.uploads[3].resolve(response("Halaman keempat"));
    await tick();
    assert.ok(h.view().some(node => node.props.children === "Foto kurang jelas."));
    assert.equal(h.analyses.length, 0);

    const edited = "Halaman pertama\n\nParagraf kedua setelah koreksi.";
    h.edit(1, edited);
    await h.button("Analisis halaman tersedia (parsial)").props.onClick();
    assert.deepEqual(h.analyses[0], [
        { page_number: 1, text: edited }, { page_number: 2, text: "Halaman kedua" },
        { page_number: 3, text: null }, { page_number: 4, text: "Halaman keempat" },
    ]);

    h.button("Coba lagi halaman 3").props.onClick();
    assert.equal(h.uploads.length, 5);
    assert.equal(h.uploads[4].file, files[2]);
    h.uploads[4].resolve(response("Halaman ketiga"));
    await tick();
    h.button("Naikkan halaman 2").props.onClick();
    await h.button("Analisis semua halaman").props.onClick();
    assert.deepEqual(h.analyses[1], [
        { page_number: 1, text: "Halaman kedua" }, { page_number: 2, text: edited },
        { page_number: 3, text: "Halaman ketiga" }, { page_number: 4, text: "Halaman keempat" },
    ]);
});

test("pilihan melebihi batas terlihat dan gambar invalid menempati slotnya", async () => {
    const h = harness();
    const valid = photo("ok.png");
    h.select(Array(5).fill(valid));
    assert.equal(h.uploads.length, 0);
    assert.match(h.view().find(node => node.props.role === "alert").props.children, /4 foto/);

    h.select([photo("invalid.gif", "image/gif"), valid]);
    assert.equal(h.uploads.length, 1);
    assert.equal(h.uploads[0].file, valid);
    assert.equal(h.button("Isi transkripsi sendiri untuk halaman 1"), undefined);
    h.uploads[0].resolve(response("Teks yang terbaca dari halaman kedua"));
    await tick();
    await h.button("Analisis halaman tersedia (parsial)").props.onClick();
    assert.equal(h.analyses[0][0].text, null);
    assert.equal(h.analyses[0][1].page_number, 2);
});

test("transkripsi manual untuk OCR gagal dikirim utuh setelah disunting", async () => {
    const h = harness();
    h.select([photo("1.png"), photo("2.png")]);
    h.uploads[0].onFailure("Teks terlalu pendek untuk OCR otomatis.");
    h.uploads[0].resolve(null);
    await tick();
    h.uploads[1].resolve(response("Teks yang terbaca dari halaman kedua"));
    await tick();
    h.button("Isi transkripsi sendiri untuk halaman 1").props.onClick();
    assert.ok(h.view().some(node => [node.props.children].flat().join("").includes("OCR gagal: Teks terlalu pendek")));
    assert.equal(h.button("Analisis semua halaman"), undefined);
    const transcription = `  Awal dokumentasi\n\n${"tulisan ".repeat(180)}akhir.  `;
    h.edit(1, transcription);
    await h.button("Analisis semua halaman").props.onClick();
    assert.equal(h.analyses[0][0].text, transcription);
    assert.equal(h.uploads.length, 2);
});

test("OCR yang selesai setelah form ditutup tidak mengirim foto berikutnya", async () => {
    const h = harness();
    h.select([photo("1.png"), photo("2.png")]);
    h.unmount();
    assert.equal(h.uploads[0].signal.aborted, true);
    h.uploads[0].resolve(response("Respons OCR lama"));
    await tick();
    assert.equal(h.uploads.length, 1);
    assert.deepEqual(h.revoked, ["blob:page-1", "blob:page-2"]);
});
