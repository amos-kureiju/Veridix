"""Evaluasi klaim per teks atau pasangan A/B dengan predictor VERIDIX."""

import argparse
import csv
from datetime import datetime
from hashlib import sha256
from io import BytesIO, TextIOWrapper
import json
import math
import os
from pathlib import Path
import sys
import tempfile

import numpy as np
import pandas as pd

from src.ml.inference import SEEDS, Penilai, get_predictor, validate_claim_result


STATUS_MODEL = ("dinilai", "ambigu")
LABEL_MODEL = {"BERPOLA HOAKS": 1, "TIDAK BERPOLA HOAKS": 0}
KOLOM_PASANGAN = ("pair_id", "group_id", "jenis_uji", "varian", "rujukan", "bukti_label")
KOLOM_HASIL = (
    "eval_mode", "decision_rule", "status", "label_model", "votes_hoax", "pred",
    *(f"pred_{seed}" for seed in SEEDS), *(f"prob_{seed}" for seed in SEEDS),
    "seed_decisions_json", "agreement_ratio", "latency_seconds",
    "teks_dinilai", "terpotong", "reason", "error", "manifest_sha256", "audit_model_json",
)
KOLOM_HASIL_PASANGAN = (
    "pasangan_status", "alasan_pasangan", "transisi_status", "transisi_ambigu",
    "label_berbalik", "suara_berubah", "keduanya_benar",
    *(f"delta_prob_{seed}" for seed in SEEDS),
)


class _Stub:
    """Fixture untuk menguji alur dan format laporan."""

    seeds = SEEDS

    def count_tokens(self, text):
        return len(text.split()) + 2

    def seed_probs_each(self, texts):
        return np.array([
            [0.95, 0.90, 0.99] if "viral" in t.lower() or "hoaks" in t.lower() else [0.05, 0.10, 0.02]
            for t in texts
        ])


def wilson(k, n, z=1.96):
    if n == 0:
        return None, None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(c - h, 0), min(c + h, 1)


def baca_manifest(data, *, pairs, by):
    with TextIOWrapper(BytesIO(data), encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        header = next((record for record in reader if record), [])
        if len(header) != len(set(header)):
            raise ValueError("Nama kolom manifest harus unik.")
        records = []
        for record in reader:
            if not record:
                continue
            if len(record) != len(header):
                raise ValueError(f"Jumlah kolom CSV tidak sesuai pada baris {reader.line_num}.")
            records.append(record)
    df = pd.DataFrame(records, columns=header)
    if df.empty:
        raise ValueError("Manifest harus berisi minimal satu baris.")
    for alias, kolom in (("teks", "text"), ("label_acuan", "label")):
        if alias in df:
            if kolom in df and not df[kolom].equals(df[alias]):
                raise ValueError(f"Kolom {kolom} dan {alias} berbeda.")
            if kolom not in df:
                df = df.rename(columns={alias: kolom})

    konflik = sorted(set(df.columns) & {*KOLOM_HASIL, *KOLOM_HASIL_PASANGAN})
    if konflik:
        raise ValueError(f"Nama kolom dipakai untuk keluaran: {', '.join(konflik)}.")
    wajib = ("id", "text", "label", *KOLOM_PASANGAN) if pairs else ("id", "text", "label")
    kurang = sorted(set((*wajib, *by)) - set(df.columns))
    if kurang:
        raise ValueError(f"Kolom wajib tidak ada: {', '.join(kurang)}.")
    for kolom in wajib:
        if df[kolom].str.strip().eq("").any():
            raise ValueError(f"Kolom {kolom} berisi nilai kosong.")
        if kolom != "text":
            df[kolom] = df[kolom].str.strip()
    if df["id"].duplicated().any():
        raise ValueError("ID setiap baris harus unik.")
    if not df["label"].isin(("0", "1")).all():
        raise ValueError("Label acuan wajib 0 atau 1.")
    df["label"] = df["label"].astype(int)

    if pairs:
        validasi_pasangan(df)
    return df


def validasi_pasangan(df):
    for nomor, (_, grup) in enumerate(df.groupby("pair_id", sort=False), 1):
        if len(grup) != 2 or set(grup["varian"]) != {"v1", "v2"}:
            raise ValueError(f"Pasangan ke-{nomor} harus memiliki satu v1 dan satu v2.")
        if grup["group_id"].nunique() != 1 or grup["jenis_uji"].nunique() != 1:
            raise ValueError(f"Pasangan ke-{nomor} harus memakai satu group_id dan satu jenis_uji.")
        jenis = grup["jenis_uji"].iloc[0]
        jumlah_label = grup["label"].nunique()
        if jenis not in ("gaya", "isi"):
            raise ValueError(f"Jenis uji pasangan ke-{nomor} harus gaya atau isi.")
        if jumlah_label != (1 if jenis == "gaya" else 2):
            raise ValueError(f"Label pasangan ke-{nomor} tidak sesuai jenis uji {jenis}.")
        if grup["text"].nunique() != 2:
            raise ValueError(f"Kedua teks pasangan ke-{nomor} harus berbeda.")


def normalisasi_teks(value):
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def metadata_model(hasil, aturan):
    validate_claim_result(hasil)
    if hasil["status"] in STATUS_MODEL and hasil.get("decision_rule") != aturan:
        raise ValueError("Aturan voting hasil berbeda dari konfigurasi evaluator.")

    data = {
        "status": hasil["status"],
        "reason": hasil.get("reason"),
        "latency_seconds": hasil["latency_seconds"],
    }
    if hasil["status"] not in STATUS_MODEL:
        return data

    keputusan = hasil["seed_decisions"]
    teks = hasil.get("teks_dinilai")
    terpotong = hasil.get("terpotong")
    if (teks is not None and not isinstance(teks, str)) or (terpotong is not None and type(terpotong) is not bool):
        raise ValueError("Metadata pemotongan atau teks praproses tidak sah.")

    debug = hasil.get("debug")
    skor = debug.get("prob_hoax_per_seed") if isinstance(debug, dict) else None
    if skor is not None and (
        not isinstance(skor, dict)
        or set(skor) != set(SEEDS)
        or any(type(v) not in (int, float) or not (0 <= v <= 1) or not math.isfinite(v) for v in skor.values())
    ):
        raise ValueError("Skor debug per seed tidak sah.")

    data.update(
        label_model=hasil["label"],
        votes_hoax=hasil["votes_hoax"],
        pred=LABEL_MODEL.get(hasil["label"]),
        seed_decisions_json=json.dumps(keputusan, sort_keys=True),
        agreement_ratio=hasil["agreement_ratio"],
        teks_dinilai=teks,
        terpotong=terpotong,
    )
    data.update({f"pred_{seed}": keputusan[seed] for seed in SEEDS})
    if skor is not None:
        data.update({f"prob_{seed}": skor[seed] for seed in SEEDS})
    return data


def evaluate_dataframe(df, pen, is_stub=False, *, load_error=None, manifest_sha256=None):
    rows = []
    aturan = getattr(pen, "rule", None)
    audit = getattr(getattr(pen, "backend", None), "audit", None)
    auditable = ("base_revision", "text_pipeline_sha256", *(f"sha256_seed_{seed}" for seed in SEEDS))
    identitas = {key: audit[key] for key in auditable if isinstance(audit, dict) and key in audit}
    common = dict.fromkeys(KOLOM_HASIL)
    common.update(
        eval_mode="stub" if is_stub else "real_model",
        decision_rule=aturan,
        manifest_sha256=manifest_sha256,
        audit_model_json=json.dumps(identitas, sort_keys=True) if identitas else None,
    )
    for teks in df["text"]:
        row = dict(common)
        if load_error is not None:
            row.update(status="gagal", error=load_error, reason="Model tidak dapat dimuat.")
        else:
            try:
                hasil = pen.nilai(teks, explain=False, debug=True)
                row.update(metadata_model(hasil, aturan))
            except Exception as exc:
                row.update(status="gagal", error=type(exc).__name__, reason="Inferensi gagal atau keluarannya tidak sah.")
        rows.append(row)
    return pd.concat([df.reset_index(drop=True), pd.DataFrame(rows, columns=KOLOM_HASIL)], axis=1)


def alasan_tidak_dibandingkan(a, b):
    if a["status"] not in STATUS_MODEL or b["status"] not in STATUS_MODEL:
        return "status_model"
    if any(not isinstance(side["terpotong"], (bool, np.bool_)) or bool(side["terpotong"]) for side in (a, b)):
        return "terpotong_atau_tidak_diketahui"
    prep_a, prep_b = (normalisasi_teks(side["teks_dinilai"]) for side in (a, b))
    if not prep_a or not prep_b:
        return "teks_dinilai_tidak_tersedia"
    if a["teks_dinilai"] == b["teks_dinilai"]:
        return "teks_dinilai_sama"
    for side, prep in ((a, prep_a), (b, prep_b)):
        bagian = normalisasi_teks(side.get("bagian_diubah"))
        if bagian and bagian not in prep:
            return "bagian_diubah_hilang"
    return None


def ringkas_pasangan(hasil):
    pairs = []
    for pair_id, grup in hasil.groupby("pair_id", sort=False):
        a, b = grup.sort_values("varian").to_dict(orient="records")
        alasan = alasan_tidak_dibandingkan(a, b)
        row = dict.fromkeys(KOLOM_HASIL_PASANGAN)
        row.update(
            pair_id=pair_id,
            jenis_uji=a["jenis_uji"],
            pasangan_status="tidak_dibandingkan" if alasan else "dibandingkan",
            alasan_pasangan=alasan,
            transisi_status=f"{a['status']}->{b['status']}",
        )
        if alasan is None:
            row["transisi_ambigu"] = (a["status"] == "ambigu") != (b["status"] == "ambigu")
            row["suara_berubah"] = a["seed_decisions_json"] != b["seed_decisions_json"]
            if a["status"] == b["status"] == "dinilai":
                row["keduanya_benar"] = a["pred"] == a["label"] and b["pred"] == b["label"]
                if a["jenis_uji"] == "gaya":
                    row["label_berbalik"] = a["pred"] != b["pred"]
            if a["jenis_uji"] == "isi":
                benar, keliru = (a, b) if a["label"] == 0 else (b, a)
                for seed in SEEDS:
                    kolom = f"prob_{seed}"
                    if pd.notna(benar[kolom]) and pd.notna(keliru[kolom]):
                        row[f"delta_prob_{seed}"] = round(keliru[kolom] - benar[kolom], 6)
        pairs.append(row)
    return pd.DataFrame(pairs)


def simpan_csv(hasil, tujuan):
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    fd, sementara = tempfile.mkstemp(dir=tujuan.parent, prefix=f".{tujuan.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            hasil.to_csv(f, index=False)
        os.link(sementara, tujuan)
    finally:
        Path(sementara).unlink(missing_ok=True)


def format_akurasi(k, n):
    if not n:
        return "N/A"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f}% [{100 * lo:.0f}-{100 * hi:.0f}%]"


def cetak_ringkasan(hasil, by, pasangan=None):
    grup = [*by, "label"]
    for key, data in hasil.groupby(grup, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        dinilai = data.loc[data["status"].eq("dinilai")]
        benar = int(dinilai["pred"].eq(dinilai["label"]).sum())
        status = data["status"].value_counts()
        print(
            f"{dict(zip(grup, key))} | n={len(data)} | dinilai={len(dinilai)} "
            f"ambigu={status.get('ambigu', 0)} ditolak={status.get('ditolak', 0)} "
            f"di_luar_domain={status.get('di_luar_domain', 0)} gagal={status.get('gagal', 0)} "
            f"| akurasi pada yang dinilai {format_akurasi(benar, len(dinilai))} "
            f"| benar/seluruh {benar}/{len(data)}"
        )
    dinilai = hasil.loc[hasil["status"].eq("dinilai")]
    for label, nama in ((1, "Recall hoaks"), (0, "Spesifisitas fakta")):
        total = int(hasil["label"].eq(label).sum())
        if total:
            kelas = dinilai.loc[dinilai["label"].eq(label)]
            benar = int(kelas["pred"].eq(label).sum())
            print(f"{nama} pada yang dinilai {format_akurasi(benar, len(kelas))} | ketat {benar}/{total}")
    print(f"Cakupan keputusan {len(dinilai)}/{len(hasil)} | gagal={hasil['status'].eq('gagal').sum()}")

    if pasangan is not None:
        for jenis, data in pasangan.groupby("jenis_uji", sort=False):
            n = len(data)
            banding = int(data["pasangan_status"].eq("dibandingkan").sum())
            benar = int(data["keduanya_benar"].eq(True).sum())
            print(f"Pasangan {jenis} | dibandingkan {banding}/{n} | kedua keputusan benar {benar}/{n}")
            if jenis == "gaya":
                flips = int(data["label_berbalik"].eq(True).sum())
                biner = int(data["label_berbalik"].notna().sum())
                print(f"  Label berbalik {flips}/{biner} pasangan dengan dua keputusan biner")
            else:
                for seed in SEEDS:
                    delta = data[f"delta_prob_{seed}"].dropna()
                    print(f"  Seed {seed} | skor keliru > benar {int(delta.gt(0).sum())}/{len(delta)} pasangan terukur")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="CSV dengan id,text,label")
    parser.add_argument("--stub", action="store_true", help="Jalankan fixture tiruan")
    parser.add_argument("--pairs", action="store_true", help="Validasi dan ringkas pasangan gaya/isi")
    parser.add_argument("--by", default="", help="Kolom kelompok tambahan, dipisahkan koma")
    parser.add_argument("--out", type=Path, help="Jalur laporan baru")
    args = parser.parse_args(argv)
    by = list(dict.fromkeys(c.strip() for c in args.by.split(",") if c.strip() and c.strip() != "label"))
    tujuan = args.out or Path(f"hasil_set_luar_{datetime.now():%Y%m%d_%H%M%S_%f}.csv")

    if os.path.lexists(tujuan):
        parser.error("Jalur laporan sudah ada. Gunakan nama berkas baru.")
    if tujuan.resolve() == args.csv.resolve():
        parser.error("Jalur laporan harus berbeda dari manifest masukan.")
    try:
        data = args.csv.read_bytes()
        df = baca_manifest(data, pairs=args.pairs, by=by)
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(f"Manifest tidak dapat dipakai ({exc}).")

    load_error = None
    try:
        pen = Penilai(_Stub()) if args.stub else get_predictor()
    except Exception as exc:
        pen = None
        load_error = type(exc).__name__
    hasil = evaluate_dataframe(df, pen, args.stub, load_error=load_error, manifest_sha256=sha256(data).hexdigest())
    pasangan = ringkas_pasangan(hasil) if args.pairs else None
    if pasangan is not None:
        hasil = hasil.merge(pasangan.drop(columns="jenis_uji"), on="pair_id", sort=False, validate="many_to_one")
    try:
        simpan_csv(hasil, tujuan)
    except (OSError, TypeError, ValueError) as exc:
        print(f"Laporan gagal diterbitkan ({type(exc).__name__}): {tujuan}", file=sys.stderr)
        return 1

    print(f"Mode {'stub' if args.stub else 'real_model'} | n={len(hasil)}")
    cetak_ringkasan(hasil, by, pasangan)
    print(f"Laporan tersimpan: {tujuan}")
    return int(hasil["status"].eq("gagal").any())


if __name__ == "__main__":
    raise SystemExit(main())
