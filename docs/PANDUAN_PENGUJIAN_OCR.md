# Panduan pengujian dan evaluasi OCR

Tanggal verifikasi: **6 November 2026**. Status: **siap untuk pengujian awal terkontrol; evaluasi akhir belum selesai**.

Dokumen ini menjadi acuan menjalankan pengujian, memilih masukan, membaca hasil, dan mencatat perubahan. Panduan perlu digunakan bersama tes otomatis; keberadaan dokumen tidak menjamin kode bebas kesalahan. Setelah perubahan kode atau data, perbarui bukti pengujian di dokumen ini.

## 1. Alur dan batas pengujian

Alur aplikasi: **unggah gambar → OCR → periksa/sunting teks → analisis model → verdict → riwayat**.

| Bagian | Tanggung jawab |
|---|---|
| `src/utils/ocr_extractor.py` | Menyiapkan gambar, memuat mesin OCR, membaca baris/skor, dan menghitung fitur kualitas. |
| `src/utils/ocr_pipeline.py` | Validasi masukan, pembersihan teks OCR, gerbang kualitas, kategori hasil, dan identitas kebijakan. |
| `src/api/routes/detection_routes.py` | Menghubungkan pipeline dengan unggahan HTTP; endpoint teks menganalisis dan menyimpan hasil. |
| `frontend/src/components/detector/NewsInputForm.tsx` | Unggah, preview, loading, penolakan, editor, dan pengiriman teks terakhir. |
| `uji_ujung_ke_ujung.py` | Pemeriksaan fungsi OCR → model dan laporan setiap masukan. |
| `uji_ocr_berpasangan.py` | Perbandingan transkripsi manual/OCR dan keluaran model pada pasangan tersebut. |

Skrip evaluasi memanggil inti inferensi, tetapi belum menguji seluruh gerbang HTTP, editor, autentikasi, atau database. Keberhasilan skrip tidak menggantikan pengujian melalui aplikasi.

## 2. Aturan yang dipertahankan selama baseline

- Gunakan pipeline aktif yang sama untuk aplikasi dan skrip; jangan menyalin logika pembersihan ke notebook.
- Pertahankan bobot, praproses model, aturan konsensus, dan ambang domain selama perbandingan OCR.
- Kebijakan awal saat diverifikasi: berkas maksimal 10 MiB, maksimal 20 juta piksel, format PNG/JPEG/WebP (MPO sebagai varian JPEG), minimal 10 kata dan 50 karakter setelah pembersihan, serta rerata confidence minimal 0,60.
- Resize lebar maksimal 1400 dan margin gambar 15 piksel adalah baseline, bukan jaminan semua huruf terbaca.
- Confidence OCR bukan akurasi transkripsi atau kebenaran klaim. Jangan memperbaiki nama, angka, atau negasi secara otomatis untuk mengecilkan CER/WER.
- Padding token dinamis tetap eksperimen terpisah selama investigasi paritas. Perubahan margin gambar juga harus menjadi kandidat eksperimen yang dicatat tersendiri.

Nilai aktual tetap diperiksa dari kode dan kebijakan yang dicatat pada setiap putaran; jangan mengandalkan angka dalam panduan jika kode telah berubah.

## 3. Menyiapkan pasangan gambar dan acuan

Transkripsi manual dibuat dengan membaca gambar secara langsung, lalu diperiksa kembali sebelum menjalankan evaluasi. Hasil OCR tidak digunakan untuk menentukan acuan. Pertahankan kapitalisasi, angka, tanda baca, dan spasi sesuai kebijakan penilaian.

Pasangan contoh yang telah diperiksa secara visual:

| ID | Gambar | Transkripsi manual |
|---|---|---|
| U01 | `data/sample_probe.png` | `KEMENTERIAN KEUANGAN MEMASTIKAN BANSOS TAHUN 2026` |
| U02 | `data/sample_panjang.png` | `Presiden Joko Widodo menegaskan bahwa penyaluran bantuan sosial tahun anggaran baru harus tepat sasaran.` |

U01 memiliki 49 karakter dan 6 kata; penolakan panjang teks sesuai kebijakan. U02 memiliki 104 karakter dan 14 kata pada acuan.

Jika memakai `--dataset`, format saat ini adalah JSON berupa daftar objek:

```json
[
  {
    "id": "U01",
    "kategori": "teks_pendek",
    "gambar": "data/sample_probe.png",
    "deskripsi": "Teks pendek untuk memeriksa gerbang kualitas",
    "transkripsi_manual": "KEMENTERIAN KEUANGAN MEMASTIKAN BANSOS TAHUN 2026"
  }
]
```

Periksa ID unik, keberadaan setiap gambar, dan kesesuaian acuannya. Simpan identitas kelompok gambar sumber agar versi jelas/buram dari gambar yang sama tidak tersebar antara set kalibrasi dan evaluasi akhir. Label kebenaran klaim, jika digunakan untuk akurasi model, membutuhkan verifikasi terpisah dari transkripsi.

Saat ini jalur gambar relatif mengikuti direktori kerja. Jalankan perintah dari root proyek `E:\SEMESTER 5\TA\PROJECT`.

## 4. Urutan menjalankan tes

### A. Tes otomatis sebelum OCR nyata

Jalankan dari PowerShell di root proyek:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_ocr_cli tests.test_ocr_evaluation -v
.\.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_ocr_routes -q
node --test tests/test_frontend_guest_access.cjs tests/test_frontend_ocr.cjs tests/test_ocr_hook.cjs tests/test_verdict_feedback.cjs
.\frontend\node_modules\.bin\tsc.cmd --noEmit --incremental false -p frontend/tsconfig.json
```

Jalankan dua perintah Python sebagai proses terpisah seperti contoh; pengujian route menggunakan modul tiruan untuk mengisolasi dependensi.

Hasil verifikasi pada 6 November 2026:

| Pemeriksaan | Hasil | Batas bukti |
|---|---|---|
| CLI dan evaluasi berpasangan | 19/19 lulus: 12 CLI + 7 evaluasi | OCR dan evaluator diganti tiruan pada pengujian kasus. |
| Endpoint gambar | 13/13 lulus | Permintaan HTTP ke aplikasi uji dengan pipeline tiruan. |
| Frontend | 84/84 lulus | Harness komponen/hook dan permintaan tiruan; belum browser nyata. |
| TypeScript | Lulus | Pemeriksaan tipe; bukan pengujian perilaku browser. |

Tidak ada mesin OCR, bobot model, atau akun/database sebenarnya yang digunakan pada verifikasi otomatis ini. Impor modul tetap dapat memuat pustaka seperti Torch; itu berbeda dari inisialisasi mesin dan pemuatan bobot.

### B. Ulangi dua pasangan dengan acuan yang benar

Gunakan nama keluaran baru untuk setiap putaran:

```powershell
.\.venv\Scripts\python.exe uji_ocr_berpasangan.py --output reports/ocr/evaluasi_berpasangan_verifikasi_01.json
```

Perintah ini menjalankan OCR dan model sebenarnya. Acuan default sudah diperbaiki pada kode yang diperiksa. Pastikan nama keluaran belum dipakai; jangan memilih gambar atau manifest sebagai tujuan laporan.

Laporan `reports/ocr/evaluasi_berpasangan.json` yang dibaca saat verifikasi sudah diperbarui oleh pengguna pada **6 November 2026, 11:09:40 UTC+07:00**, dengan acuan yang sesuai kedua gambar. Hasil yang tersimpan:

| Kasus | CER / WER | Hasil pada teks manual | Hasil pada teks OCR |
|---|---|---|---|
| U01 | 0% / 0% | Ditolak karena pendek | Ditolak kualitas; inferensi jalur OCR dilewati |
| U02 | 1,9231% / 21,4286% | `dinilai`, `TIDAK BERPOLA HOAKS`, suara 0/3 | `ambigu`, suara 2/3 |

Untuk U02, `label_sama` bernilai **false**. Acuan dan bacaan OCR berbeda pada `Presiden → residen` serta `tepat → te pat`; hasil ini menunjukkan perubahan keluaran pada pasangan tersebut. Simpan sebagai kasus investigasi sensitivitas, bukan bukti ketahanan semantik. Kebenaran klaim juga belum ditentukan oleh kesamaan atau perbedaan keluaran ini. Pembacaan laporan ini tidak mencakup eksekusi ulang mesin OCR/model oleh pemeriksa.

Percobaan sebelumnya dengan acuan berbeda menghasilkan CER/WER 104,4%/100% dan 43,4%/61,9%. Angka tersebut tidak digunakan untuk baseline ketepatan OCR. Mengubah acuan di kode tidak memperbarui laporan lama; simpan keluaran baru setiap putaran. Hasil metrik di atas bukan target yang harus dicapai dengan mengubah acuan; hasil eksekusi berikutnya tetap dicatat apa adanya.

### C. Lengkapi lima kondisi fungsional

| Kondisi | Ekspektasi yang diperiksa |
|---|---|
| Teks jelas, cukup panjang, dan dalam domain | Ada contoh yang benar-benar lolos OCR dan diteruskan ke model. |
| Buram | Catat bacaan, confidence, dan hasil gerbang; ukur bacaan buruk yang lolos maupun bacaan layak yang tertolak. |
| Tanpa teks | Jika OCR selesai dengan teks kosong, hasil masuk penolakan kualitas. Acuan kosong memiliki CER/WER tidak tersedia dan jumlah sisipan dicatat. |
| Teks pendek | Ditolak kualitas sebelum inferensi pada jalur hasil OCR. |
| Format tidak didukung, misalnya BMP | Ditolak input sebelum pengenalan teks; CER/WER tidak tersedia. |

Gambar buram tidak otomatis ditolak. Penolakan harus dijelaskan oleh gerbang yang benar-benar berjalan. Seluruh masukan tetap masuk total, termasuk berkas hilang, penolakan, dan galat.

### D. Periksa aplikasi melalui browser

1. Masuk dengan akun uji yang ditetapkan dan unggah gambar jelas.
2. Periksa preview, loading, hasil OCR, serta pesan ketika unggahan ditolak.
3. Koreksi `residen` menjadi `Presiden` dan `te pat` menjadi `tepat` pada editor jika kesalahan itu muncul.
4. Analisis; periksa payload menggunakan teks editor terakhir dan `input_type: IMAGE`.
5. Cocokkan teks dan verdict pada respons dengan riwayat, lalu ulangi setelah refresh dan masuk ulang.
6. Uji ganti/batalkan gambar saat loading: respons gambar sebelumnya tidak boleh menimpa gambar terbaru.
7. Periksa feedback pada ID hasil yang sama sesuai status yang diizinkan, serta pemisahan data antara dua akun uji.

Riwayat saat ini dibuat melalui analisis teks. Unggahan yang ditolak OCR tetap dicatat pada laporan evaluasi; tidak otomatis menjadi entri riwayat aplikasi. Penyimpanan gambar asli juga belum dibuktikan oleh sumber `IMAGE`.

## 5. Aturan membaca metrik dan latensi

- CER = jarak edit karakter / jumlah karakter acuan; WER = jarak edit token / jumlah token acuan. Skrip mempertahankan kapitalisasi dan tanda baca; WER memakai pemisahan `split()`.
- Rasio dapat melebihi 100% karena penyisipan. Acuan kosong tidak memiliki rasio yang sah; catat `null` beserta jumlah sisipan.
- Jika OCR selesai tetapi bacaannya kosong sementara acuan berisi teks, hitung penghapusan. Jika input ditolak sebelum OCR atau mesin gagal, gunakan metrik tidak tersedia; jangan menyamakan keduanya.
- Laporkan jumlah seluruh masukan, jumlah yang terukur, penolakan, galat, ambiguitas, serta jumlah pasangan yang dibandingkan. Nilai yang tidak tersedia tidak diganti nol.
- Rerata hanya untuk hasil diterima adalah metrik bersyarat. Evaluasi akhir juga membutuhkan hasil seluruh sampel yang terukur, termasuk penolakan kualitas.
- Pisahkan kesamaan status/label, kesepakatan keputusan biner, dan akurasi terhadap label klaim terverifikasi. Dua hasil `ambigu` yang sama tidak membuktikan ketepatan klasifikasi atau ketahanan semantik.
- Pengukuran pertama/warm memakai gambar sama. Jalankan beberapa proses baru dan beberapa pengulangan warm; laporkan jumlah pengulangan, median, variasi, perangkat, dan versi runtime. Laporan terbaru mencatat 7,477 detik dan 2,740 detik (sekitar 2,7×); satu perbandingan hanya pengamatan awal.
- Skrip sekarang memuat IndoBERT sebelum pengukuran OCR. Angka tersebut bukan waktu awal seluruh aplikasi, serta belum memisahkan inisialisasi OCR, praproses, dan pengenalan.

## 6. Kekurangan yang masih terbuka

Hal berikut belum dianggap selesai meskipun tes yang tersedia lulus:

- `--dataset` yang tidak ditemukan masih dapat beralih ke dataset default. Verifikasi jalur sebelum menjalankan; kode berikutnya perlu menolak kesalahan ini secara eksplisit.
- Struktur manifest, ID unik, dan kelengkapan referensi belum divalidasi ketat oleh runner.
- Penulisan laporan evaluasi berpasangan belum atomik. Gunakan keluaran baru dan pertahankan hasil sebelumnya.
- Tes agregasi saat ini mengulang rumus lokal, belum memeriksa ringkasan yang dibuat `main()`. Jalur pasangan model yang diterima, galat per kasus, serta lanjutan batch juga perlu diuji langsung.
- Ringkasan belum menghitung metrik seluruh sampel terukur dan belum lengkap memisahkan galat eksekusi/model dari kategori OCR.
- Runner berpasangan belum menyimpan `teks_dinilai`, keputusan dan probabilitas setiap seed, maupun status perbandingan secara lengkap. Simpan keluaran aktual tersebut untuk menyelidiki perubahan U02, tanpa mengubah praproses atau aturan model.
- Hash kebijakan sudah mencakup `OCR_KWARGS`. Konfigurasi lengkap belum dicantumkan langsung dalam laporan berpasangan; konfigurasi tersebut, identitas model OCR yang terpilih, versi dependensi, dan perangkat masih perlu dicatat untuk evaluasi yang dapat diulang di lingkungan lain.
- Pengujian browser, akun sebenarnya, penyimpanan riwayat/feedback, dan evaluasi domain akhir belum selesai.

Status saat ini mengizinkan pengujian awal dua gambar default yang acuannya telah diperiksa. Sebelum menjalankan dataset besar atau membuat klaim Bab 4, selesaikan validasi manifest dan pemeriksaan ringkasan, lengkapi kondisi gambar, lalu bekukan konfigurasi.

## 7. Catatan setiap putaran

Gunakan catatan berikut bersama keluaran JSON baru:

```text
Tanggal / ID putaran:
Commit atau perubahan kode:
Manifest dan hash gambar:
Pemeriksa transkripsi manual:
Versi pipeline / hash kebijakan / konfigurasi OCR:
Model OCR / versi runtime / perangkat:
Aturan keputusan model:
Perintah dan jalur laporan:
Jumlah seluruh masukan / terukur / diterima / ditolak / galat / ambigu:
Jumlah pasangan pembanding:
CER/WER mentah dan bersih, berikut pembaginya:
Jumlah pengulangan dan hasil latensi:
Hasil uji editor / riwayat / feedback jika dilakukan:
Keterbatasan dan keputusan menerima atau menolak kandidat:
```

Notebook Jupyter membaca keluaran yang sudah diverifikasi untuk tabel dan grafik; notebook tidak menetapkan ulang acuan atau mengubah praproses aplikasi. Rencana perubahan awal disimpan sebagai arsip di [RENCANA_OPTIMASI_OCR.md](RENCANA_OPTIMASI_OCR.md).

Kontrak API, berkas terkait, dan langkah pengujian detail/penghapusan riwayat pengguna dicatat di [PANDUAN_RIWAYAT.md](PANDUAN_RIWAYAT.md).
