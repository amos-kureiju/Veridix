import hashlib, os
import pandas as pd

F = "data/processed_v2"
m = pd.read_csv(f"{F}/MANIFEST_sha256.csv")


def sha(p):
  h = hashlib.sha256()
  with open(p, "rb") as f:
    for ch in iter(lambda: f.read(1 << 20), b""):
      h.update(ch)
  return h.hexdigest()


bad = 0
for _, r in m.iterrows():
  b = str(r.berkas).replace("\\", "/")
  if b.startswith("RAW/"):
    continue

  # Pemetaan path: arahkan file skrip ke root, dan lockbox ke subfolder
  p = {
      "LOCKBOX/lockbox.csv": f"{F}/LOCKBOX/lockbox.csv",
      "text_pipeline.py": "text_pipeline.py",
      "01b_rebuild_dataset_final.py": "01b_rebuild_dataset_final.py",  # <── TAMBAHKAN INI
  }.get(b, f"{F}/{b}")

  ok = os.path.exists(p) and sha(p) == r.sha256.lower()
  bad += not ok
  print("OK  " if ok else "BEDA", b)

print("-" * 40)
print("Total tidak cocok:", bad)
assert bad == 0, (
    "Integritas build gagal: ada berkas yang berubah setelah build!"
)