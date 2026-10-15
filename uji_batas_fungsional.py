"""uji_batas_fungsional.py - uji masukan batas. Ekspektasi ditulis SEBELUM dijalankan.

Setiap kasus punya himpunan status yang diterima. Jangan ubah ekspektasi atau
aturan setelah melihat hasil tanpa mencatat alasannya di protokol.
Keluaran lengkap disimpan ke hasil_uji_batas.csv (simpan sebagai log di repo).
"""
import csv
import os
import sys
import time

sys.path.insert(0, os.getcwd())
from src.ml.inference import predictor  # noqa: E402

ZW = "\u200b"
BASE = ("Presiden menegaskan bahwa pemerintah tetap memprioritaskan penyaluran "
        "bantuan sosial tepat sasaran menjelang akhir tahun anggaran.")

KASUS = [
    ("kosong", "", {"ditolak"}),
    ("spasi saja", "     ", {"ditolak"}),
    ("simbol saja", "   ... ??? !!!   ", {"ditolak"}),
    ("angka saja", "12345 67890 11223 44556 77889 00112", {"ditolak"}),
    ("satu kata", "Presiden", {"ditolak"}),
    ("terlalu pendek", "Jokowi resmikan jalan tol.", {"ditolak", "dinilai", "ambigu", "di_luar_domain"}),
    ("sangat panjang", (BASE + " ") * 100, {"ditolak"}),
    ("acak/sampah", "asdkjh qwpoei zxmncb lkjhgf poiuyt mnbvcx", {"ditolak", "di_luar_domain"}),
    ("non-politik", "Cara memasak rendang daging sapi empuk khas Padang dengan santan kelapa kental dan rempah pilihan.", {"di_luar_domain"}),
    ("bahasa Inggris", "Breaking news: The election commission announced the official results of the presidential race today.", {"ditolak", "di_luar_domain"}),
    ("emoji & tautan", "VIRAL!! 🔥🔥 Klik link ini https://bit.ly/bansos2026 untuk dapat uang gratis dari pemerintah!! 💰💰", {"dinilai", "ambigu", "di_luar_domain", "ditolak"}),
    ("politik normal", BASE, {"dinilai", "ambigu"}),
]

rows, gagal = [], 0
print("=" * 80)
for nama, teks, diterima in KASUS:
  t0 = time.time()
  try:
    r = predictor.predict_and_explain(teks)
    status, pred = r["status"], r["prediction"]
    pesan = r.get("domain_warning")
  except Exception as e:  # crash = kegagalan uji
    status, pred, pesan = "CRASH", "-", repr(e)
  ok = status in diterima
  gagal += (not ok)
  print(f"[{'OK ' if ok else 'GAGAL'}] {nama:<18} status={status:<15} pred={pred} | {pesan}")
  rows.append([nama, repr(teks[:80]), sorted(diterima), status, pred, pesan,
               round(time.time() - t0, 2)])

# Uji kekokohan: karakter tak terlihat & homoglif TIDAK boleh mengubah teks yang diproses.
ref = predictor.predict_and_explain(BASE, explain=False)
for nama, teks in [
    ("zero-width disisipkan", BASE.replace("pemerintah", "pemer" + ZW + "intah")),
    ("homoglif Sirilik", BASE.replace("pemerintah", "pemerint\u0430h")),
]:
  r = predictor.predict_and_explain(teks, explain=False)
  sama = r["processed_text"] == ref["processed_text"]
  gagal += (not sama)
  print(f"[{'OK ' if sama else 'GAGAL'}] {nama:<22} teks proses identik dengan acuan: {sama}")
  rows.append([nama, repr(teks[:80]), ["teks identik"], sama, r["prediction"], "", ""])

with open("hasil_uji_batas.csv", "w", newline="", encoding="utf-8") as f:
  w = csv.writer(f)
  w.writerow(["kasus", "masukan", "diterima", "status", "prediksi", "pesan", "detik"])
  w.writerows(rows)
print("=" * 80)
print(f"Gagal: {gagal} dari {len(KASUS) + 2}. Log: hasil_uji_batas.csv")
sys.exit(1 if gagal else 0)