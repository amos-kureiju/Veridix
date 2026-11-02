"""
uji_kesetiaan_lime.py - uji awal kesetiaan LIME (penghapusan fitur) dengan kontrol acak.
- Penghapusan kata utuh pada TEKS HASIL PRAPROSES (masukan model yang sama dengan LIME).
- Kata merah (bobot > 0) dan hijau (bobot < 0), masing-masing top-2.
- Kontrol: penghapusan kata acak berjumlah sama, diulang N kali, di luar kata LIME teratas.
- Skor dihitung langsung dari backend (rerata probabilitas hoaks tiga seed), tanpa gerbang ulang.
Keluaran: hasil_kesetiaan_lime.csv dan hasil_kesetiaan_lime.json
"""
import os, sys, re, json, random
import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
from src.ml.inference import get_predictor, LIME_NUM_SAMPLES

pen = get_predictor()
N_ACAK = 10
TOP_K = 2

KORPUS_UJI = [
    {"id": "T01", "teks": "Beredar kabar viral jutaan surat suara pemilu di gudang logistik Tanjung Priok sudah dicoblos nomor dua secara curang sebelum hari pencoblosan nasional dimulai."},
    {"id": "T02", "teks": "Terbongkar dokumen rahasia menteri keuangan diam-diam menyetujui pemotongan anggaran bantuan sosial rakyat demi mendanai proyek oligarki dan dinasti politik."},
    {"id": "T03", "teks": "Kementerian Keuangan memastikan alokasi anggaran perlindungan sosial dan bantuan pangan tahun 2026 disalurkan secara transparan kepada pemerintah daerah penerima manfaat."},
    {"id": "T04", "teks": "Presiden Joko Widodo didampingi jajaran menteri meresmikan pembukaan jalan tol Trans Jawa guna memangkas durasi distribusi logistik dan mempercepat pertumbuhan ekonomi daerah."},
]

def hapus_kata_utuh(teks, kata):
    """Hapus kata utuh (bukan substring), tidak sensitif huruf."""
    s = teks
    for w in kata:
        s = re.sub(r"\b" + re.escape(w.strip()) + r"\b", " ", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip()

def skor(teks):
    """Rerata probabilitas hoaks tiga seed pada teks yang sudah dipraproses; None bila tidak valid."""
    if not teks or len(teks.split()) < 3:
        return None
    p = np.asarray(pen.backend.seed_probs_each([teks])[0], dtype=float)
    return float(p.mean()) if np.all(np.isfinite(p)) else None

def delta_pt(p, p0):
    return None if p is None else round((p - p0) * 100, 2)

baris = []
for item in KORPUS_UJI:
    print(f"\n--- {item['id']} ---")
    res = pen.nilai(item["teks"], explain=True, debug=True)
    if res.get("status") not in ("dinilai", "ambigu") or "debug" not in res:
        print("Ditolak gerbang/engine, dilewati:", res.get("reason"))
        baris.append({"id": item["id"], "status": res.get("status"), "catatan": "dilewati"})
        continue

    t = res["teks_dinilai"]
    p0 = float(res["debug"]["mean_prob_hoax"])
    ex = res.get("explanation", {}) or {}
    tokens = [x for x in ex.get("tokens", []) if isinstance(x.get("weight"), (int, float))]
    merah = [x["word"] for x in sorted((x for x in tokens if x["weight"] > 0), key=lambda x: -x["weight"])][:TOP_K]
    hijau = [x["word"] for x in sorted((x for x in tokens if x["weight"] < 0), key=lambda x: x["weight"])][:TOP_K]
    print(f"Awal: {p0*100:.2f}% | voting {res['votes_hoax']} | {res['label']}")
    print(f"Merah: {merah} | Hijau: {hijau}")

    d_merah = delta_pt(skor(hapus_kata_utuh(t, merah)), p0) if merah else None
    d_hijau = delta_pt(skor(hapus_kata_utuh(t, hijau)), p0) if hijau else None

    # Kontrol acak: kata unik di luar kata LIME teratas
    dikecualikan = {w.lower() for w in merah + hijau}
    kandidat = sorted({w.lower() for w in re.split(r"\W+", t) if len(w) >= 3} - dikecualikan)

    def acak(k):
        if k == 0 or len(kandidat) < k:
            return []
        rng = random.Random(42)
        out = []
        for _ in range(N_ACAK):
            d = delta_pt(skor(hapus_kata_utuh(t, rng.sample(kandidat, k))), p0)
            if d is not None:
                out.append(d)
        return out

    a_merah, a_hijau = acak(len(merah)), acak(len(hijau))
    print(f"Hapus merah : {d_merah} pt | acak (n={len(a_merah)}): rerata {np.mean(a_merah) if a_merah else None}")
    print(f"Hapus hijau : {d_hijau} pt | acak (n={len(a_hijau)}): rerata {np.mean(a_hijau) if a_hijau else None}")

    baris.append({
        "id": item["id"], "status": res["status"], "label": res["label"], "votes": res["votes_hoax"],
        "p_awal": round(p0, 4), "kata_merah": "|".join(merah), "kata_hijau": "|".join(hijau),
        "delta_hapus_merah_pt": d_merah, "delta_acak_merah_rerata_pt": round(float(np.mean(a_merah)), 2) if a_merah else None,
        "delta_hapus_hijau_pt": d_hijau, "delta_acak_hijau_rerata_pt": round(float(np.mean(a_hijau)), 2) if a_hijau else None,
        "local_r2": (ex.get("diagnostik") or {}).get("local_r2"),
        "lime_num_samples": ex.get("num_samples", LIME_NUM_SAMPLES), "n_acak": N_ACAK,
    })

df = pd.DataFrame(baris)
df.to_csv("hasil_kesetiaan_lime.csv", index=False)
with open("hasil_kesetiaan_lime.json", "w", encoding="utf-8") as f:
    json.dump(baris, f, ensure_ascii=False, indent=2)
print("\n" + df.to_string(index=False))
print("\nTersimpan: hasil_kesetiaan_lime.csv, hasil_kesetiaan_lime.json")