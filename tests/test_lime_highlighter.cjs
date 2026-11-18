// Isolated rendering checks; no browser, HTTP, OCR, model, or database.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');

const frontend = path.resolve(__dirname, '../frontend');
const frontendRequire = createRequire(path.join(frontend, 'package.json'));
const ts = frontendRequire('typescript');
const filename = path.join(frontend, 'src/components/detector/LimeHighlighter.tsx');
const { outputText } = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    fileName: filename,
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
});
const loaded = { exports: {} };
vm.runInNewContext(outputText, {
    module: loaded,
    exports: loaded.exports,
    require: name => name === 'react' ? { useMemo: compute => compute() } : frontendRequire(name),
}, { filename });
const Highlighter = loaded.exports.default;

function* elements(node) {
    if (Array.isArray(node)) {
        for (const child of node) yield* elements(child);
    } else if (node && typeof node === 'object' && node.props) {
        yield node;
        yield* elements(node.props.children);
    }
}

function text(node) {
    if (node === null || node === undefined || typeof node === 'boolean') return '';
    if (Array.isArray(node)) return node.map(text).join('');
    return typeof node === 'object' ? text(node.props?.children) : String(node);
}

function inline(tree) {
    return [...elements(tree)].find(node => node.type === 'div' &&
        node.props.className?.includes('max-h-48'));
}

function attributed(tree, word) {
    return [...elements(inline(tree))].find(node => node.type === 'span' &&
        typeof node.props.title === 'string' && text(node) === word);
}

test('inline attribution preserves case, Unicode words, spacing, and the supplied text', () => {
    const original = 'Presiden  presiden\nJosé.';
    const tokens = [
        { word: 'Presiden', weight: 0.2, influence: 'KE_HOAKS' },
        { word: 'presiden', weight: -0.1, influence: 'KE_TIDAK_HOAKS' },
        { word: 'José', weight: 0.3, influence: 'KE_HOAKS' },
    ];
    const before = JSON.stringify(tokens);
    const tree = Highlighter({ text: original, tokens, showChart: false });
    assert.equal(text(inline(tree)), original);
    assert.equal(attributed(tree, 'Presiden').props.title, 'Bobot Pengaruh: +0.2000');
    assert.match(attributed(tree, 'Presiden').props.className, /bg-rose/);
    assert.equal(attributed(tree, 'presiden').props.title, 'Bobot Pengaruh: -0.1000');
    assert.match(attributed(tree, 'presiden').props.className, /bg-emerald/);
    assert.equal(attributed(tree, 'José').props.title, 'Bobot Pengaruh: +0.3000');
    assert.equal(JSON.stringify(tokens), before);
});

test('numeric sign controls attribution even when influence metadata disagrees; zero stays neutral', () => {
    const tree = Highlighter({ text: 'naik turun netral', showChart: false, tokens: [
        { word: 'naik', weight: 0.2, influence: 'KE_TIDAK_HOAKS' },
        { word: 'turun', weight: -0.1, influence: 'KE_HOAKS' },
        { word: 'netral', weight: 0, influence: 'KE_HOAKS' },
    ] });
    assert.match(attributed(tree, 'naik').props.className, /bg-rose/);
    assert.match(attributed(tree, 'turun').props.className, /bg-emerald/);
    assert.equal(attributed(tree, 'netral').props.className, '');
    assert.equal(attributed(tree, 'netral').props.title, 'Bobot Pengaruh: 0.0000');
});

test('missing and non-finite weights remain unavailable and never become zero', () => {
    const tree = Highlighter({ text: 'hilang rusak nol', showChart: false, tokens: [
        null,
        { word: 'hilang', weight: null, influence: 'KE_HOAKS' },
        { word: 'rusak', weight: NaN, influence: 'KE_TIDAK_HOAKS' },
        { word: 'nol', weight: 0, influence: 'KE_TIDAK_HOAKS' },
    ] });
    assert.equal(attributed(tree, 'hilang').props.title, 'Bobot Pengaruh: Tidak tersedia');
    assert.equal(attributed(tree, 'rusak').props.title, 'Bobot Pengaruh: Tidak tersedia');
    assert.equal(attributed(tree, 'nol').props.title, 'Bobot Pengaruh: 0.0000');
    assert.match(text(tree), /Beberapa kata tidak memiliki atribusi bobot valid/);
});

test('legacy explanation without supplied text only lists the available attributed words', () => {
    const tree = Highlighter({ showChart: false, tokens: [
        { word: 'tersedia', weight: -0.25, influence: 'KE_TIDAK_HOAKS' },
    ] });
    assert.equal(text(inline(tree)), 'tersedia ');
    assert.equal(attributed(tree, 'tersedia ').props.title, 'Bobot Pengaruh: -0.2500');
});
