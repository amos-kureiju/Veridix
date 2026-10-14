"""
inferensi_lokal.py
==================
Memuat checkpoint ckpt_ce_{seed}.pt di laptop dan memprediksi teks.
Dipakai oleh: verifikasi_ckpt_lokal.py, uji OCR, dan (SATU KALI) evaluasi lockbox.

Arsitektur Clf IDENTIK dengan colab_02_indobert_RUN_PENUH.ipynb.
Praproses teks HARUS sama dengan pelatihan:
  tp.norm_title -> tp.clean -> build_text -> cap_sentences(60)

CATATAN INTEGRITAS CHECKPOINT:
  .pt menyimpan HANYA layer terlatih (layer 8-11, pooler, head).
  Embedding dan layer 0-7 dimuat ulang dari indobenchmark/indobert-base-p1.
  Revisi model dasar WAJIB dicatat -- hasil bisa bergeser bila repo HF berubah.
  Gunakan base_model_revision() dan simpan outputnya di protokol.

Belum diuji dengan bobot asli saat pertama ditulis (hanya dikompilasi).
Kode model sama persis dengan colab_02_indobert_RUN_PENUH.ipynb.
"""

import os, sys
import numpy as np
import torch, torch.nn as nn
from transformers import AutoTokenizer, AutoModel

# -- KONSTANTA (identik dengan CFG Colab 02) ----------------------------------
MODEL_NAME    = "indobenchmark/indobert-base-p1"
MAX_LEN       = 128
DROPOUT       = 0.3
FREEZE_LAYERS = 8
BATCH         = 32
SEEDS         = [42, 123, 999]
DEVICE        = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -- RESOLUSI PATH PROYEK -----------------------------------------------------
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    import text_pipeline as tp
    assert tp.PIPELINE_VERSION == "tp-1.6", (
        f"text_pipeline versi {tp.PIPELINE_VERSION}, diharapkan tp-1.6"
    )
except Exception as e:
    raise ImportError(f"Gagal memuat text_pipeline.py tp-1.6: {e}")


# -- ARSITEKTUR (identik baris-per-baris dengan Colab 02) ---------------------
class Clf(nn.Module):
    """
    Layer terlatih: layer 8-11, pooler, head.
    Layer beku (embedding, 0-7): TIDAK ada di .pt, dimuat ulang dari from_pretrained.
    """
    def __init__(self):
        super().__init__()
        self.bert = AutoModel.from_pretrained(MODEL_NAME)
        for p in self.bert.embeddings.parameters():
            p.requires_grad = False
        for i in range(FREEZE_LAYERS):
            for p in self.bert.encoder.layer[i].parameters():
                p.requires_grad = False
        self.drop = nn.Dropout(DROPOUT)
        self.head = nn.Linear(self.bert.config.hidden_size, 2)

    def forward(self, ids, am):
        return self.head(
            self.drop(
                self.bert(input_ids=ids, attention_mask=am).last_hidden_state[:, 0, :]
            )
        )


# -- TOKENIZER (singleton) ----------------------------------------------------
_TOK = None

def get_tokenizer():
    global _TOK
    if _TOK is None:
        _TOK = AutoTokenizer.from_pretrained(MODEL_NAME)
    return _TOK


# -- MUAT CHECKPOINT ----------------------------------------------------------
def load_ckpt(path):
    """
    Muat checkpoint parsial.
    strict=False wajib -- .pt hanya berisi layer terlatih, bukan layer beku.
    'missing' = layer beku (embedding, 0-7) -- ini NORMAL, bukan error.
    """
    m = Clf().to(DEVICE)
    try:
        sd = torch.load(path, map_location=DEVICE, weights_only=True)
    except TypeError:
        sd = torch.load(path, map_location=DEVICE)   # PyTorch < 2.0
    missing, unexpected = m.load_state_dict(sd, strict=False)
    assert not unexpected, f"kunci tak dikenal: {unexpected[:3]}"
    m.eval()
    return m


def base_model_revision(m):
    """
    Revisi (commit hash) model pralatih yang sedang dimuat.
    Catat di protokol -- dependensi yang tidak tersimpan di .pt.
    Jika None: lakukan snapshot_download dan hash folder cache secara manual.
    """
    return getattr(m.bert.config, "_commit_hash", None)


def resolve_ckpt_paths(seeds=None):
    """Cari ckpt_ce_{seed}.pt di saved_models/indobert_ce_final/, saved_models/, root."""
    if seeds is None:
        seeds = SEEDS
    search = [
        os.path.join(ROOT_DIR, "saved_models", "indobert_ce_final"),
        os.path.join(ROOT_DIR, "saved_models"),
        ROOT_DIR,
    ]
    found = {}
    for s in seeds:
        fn = f"ckpt_ce_{s}.pt"
        for d in search:
            p = os.path.join(d, fn)
            if os.path.exists(p):
                found[s] = p
                break
    return found


# -- PREDIKSI BATCH -----------------------------------------------------------
@torch.no_grad()
def predict_texts(model, texts, batch=BATCH):
    """
    Inferensi satu model pada daftar teks mentah.
    Kembalikan (pred_labels np.int64, prob_hoaks np.float32).
    """
    tok   = get_tokenizer()
    texts = [str(t) for t in texts]
    preds, probs = [], []
    for i in range(0, len(texts), batch):
        e = tok(
            texts[i:i + batch],
            max_length=MAX_LEN,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        lg = model(e["input_ids"].to(DEVICE), e["attention_mask"].to(DEVICE))
        preds.append(lg.argmax(1).cpu().numpy())
        probs.append(torch.softmax(lg, 1)[:, 1].cpu().numpy())
    return np.concatenate(preds), np.concatenate(probs)


# -- PRAPROSES TEKS BARU (OCR / LOCKBOX) -------------------------------------
def preprocess_text(raw):
    """
    Pra-pemrosesan terpadu tp-1.6 untuk teks baru (OCR, lockbox).
    Urutan: clean -> norm_title(unwrap) -> ensure_end -> cap_sentences(60).
    Jangan gunakan ini untuk val/dev -- kolom 'text' di CSV sudah diproses.
    """
    s = tp.clean(str(raw))
    s = tp.norm_title(s, unwrap=True)
    s = tp.ensure_end(s)
    s = tp.cap_sentences(s, max_words=60)
    return s
