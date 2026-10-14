# SIMULASI ala OCR + kerangka evaluasi. Ini BUKAN uji OCR nyata.
import re, random
import numpy as np, pandas as pd

PUNCT = re.compile(r"[.,!?;:]")
CONF = {"i": "1", "l": "1", "o": "0", "s": "5", "e": "c", "a": "o"}


def hyphen_break(t, p, rng):
    """Pemenggalan baris ala OCR: 'menetapkan' -> 'me- netapkan'."""
    out = []
    for w in t.split():
        if len(w) >= 7 and w.isalpha() and rng.random() < p:
            k = rng.randint(3, len(w) - 3)
            out += [w[:k] + "-", w[k:]]
        else:
            out.append(w)
    return " ".join(out)


def split_words(t, p, rng):
    """Spasi nyasar di tengah kata: 'menetapkan' -> 'mene tapkan'."""
    out = []
    for w in t.split():
        if len(w) >= 6 and w.isalpha() and rng.random() < p:
            k = rng.randint(2, len(w) - 2)
            out += [w[:k], w[k:]]
        else:
            out.append(w)
    return " ".join(out)


def char_confusion(t, p, rng):
    """Salah baca karakter: i/l->1, o->0, s->5, e->c, a->o."""
    return "".join(CONF[c.lower()] if (c.lower() in CONF and rng.random() < p) else c for c in t)


def drop_punct(t, rng=None):
    return PUNCT.sub("", t)


def dehyphenate(t):
    """Sambung kembali pemenggalan baris ('me- netapkan' -> 'menetapkan'). Tanda hubung sah ('Prabowo-Gibran') tidak tersentuh."""
    return re.sub(r"(\w)-\s+(\w)", r"\1\2", t)


CONDITIONS = {
    "bersih (acuan)":                lambda t, r: t,
    "tanpa tanda baca":              lambda t, r: drop_punct(t),
    "tanda hubung baris 5%":         lambda t, r: hyphen_break(t, .05, r),
    "tanda hubung baris 15%":        lambda t, r: hyphen_break(t, .15, r),
    "tanda hubung baris 30%":        lambda t, r: hyphen_break(t, .30, r),
    "  ... disambung kembali (15%)": lambda t, r: dehyphenate(hyphen_break(t, .15, r)),
    "pisah kata 5%":                 lambda t, r: split_words(t, .05, r),
    "pisah kata 15%":                lambda t, r: split_words(t, .15, r),
    "salah karakter 2%":             lambda t, r: char_confusion(t, .02, r),
    "salah karakter 5%":             lambda t, r: char_confusion(t, .05, r),
    "gabungan sedang":               lambda t, r: drop_punct(char_confusion(hyphen_break(t, .10, r), .03, r)),
    "  ... hubung disambung kembali": lambda t, r: dehyphenate(drop_punct(char_confusion(hyphen_break(t, .10, r), .03, r))),
}


def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(c - h, 0.0), min(c + h, 1.0)


def make_variants(texts, tp):
    """Kembalikan {kondisi: [teks setelah derau + praproses inferensi]}."""
    out = {}
    for name, f in CONDITIONS.items():
        vs = []
        for i, t in enumerate(texts):
            x = f(str(t), random.Random(f"{name.strip()}|{i}"))
            x = tp.clean(x)
            vs.append(tp.cap_sentences(tp.ensure_end(x), 60) if x else x)
        out[name] = vs
    return out


def evaluate(predict_fn, df, tp, variants=None):
    """predict_fn(list_of_texts) -> array prediksi (0/1). df: kolom text, label."""
    variants = variants or make_variants(df.text.tolist(), tp)
    y = df.label.to_numpy(); rows = []
    for name, texts in variants.items():
        p = np.asarray(predict_fn(texts))
        rows.append(dict(kondisi=name, n=len(y), akurasi=float((p == y).mean()),
                         recall_hoaks=float((p[y == 1] == 1).mean()), spesifisitas_fakta=float((p[y == 0] == 0).mean()),
                         share_diprediksi_hoaks=float(p.mean())))
    return pd.DataFrame(rows)