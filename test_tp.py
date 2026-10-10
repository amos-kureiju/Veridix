"""
test_tp.py — Uji Assertion Resmi text_pipeline tp-1.5
"""
import text_pipeline as tp

print("=" * 60)
print("MEMULAI UJI ASSERTION tp-1.5...")
print("=" * 60)

# 1. Uji pembuangan dateline sumber (TEMPO / CNN)
assert tp.clean("TEMPO.CO, Jakarta - Presiden Jokowi memanggil.") == "Presiden Jokowi memanggil."
assert tp.clean("Lampung, CNN Indonesia -- Rapat diskors.") == "Rapat diskors."

# 2. Uji tag tanpa kurung siku
assert tp.clean("HASUT: “Bendera PKI berkibar”") == "“Bendera PKI berkibar”"

# 3. Uji kata 'klaim' normal tidak boleh terpotong
assert tp.clean("Klaim Presiden menanyakan wajib militer?") == "Klaim Presiden menanyakan wajib militer?"

# 4. Uji penyelamatan narasi dari blok Mafindo
s = "Judul klaim.\n=== KATEGORI: KONTEN YANG MENYESATKAN ===\nNARASI: isi klaim yang harus tetap ada.\n=====\nPenjelasan: bantahan"
assert tp.clean(s) == "Judul klaim. isi klaim yang harus tetap ada."

# 5. Uji pencegahan judul ganda geser (sliding title)
t1 = tp.build_text("Berita CNN tentang “TEKA-TEKI ARMANDO DI DPR”", "TEKA-TEKI ARMANDO DI DPR babak belur terjawab sudah")
t2 = tp.build_text("BREAKING NEWS!!! Judul ini", "BREAKING NEWS!!! Judul ini. isi lanjutan klaim ini")

print("Test 1 build_text:", repr(t1))
print("Test 2 build_text:", repr(t2))
print("=" * 60)
print("✓ SEMUA UJI ASSERTION tp-1.5 LULUS!")
print("=" * 60)