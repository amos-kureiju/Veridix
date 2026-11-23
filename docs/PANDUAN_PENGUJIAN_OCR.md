# Panduan pengujian dan evaluasi OCR

Tanggal bukti awal: **6 November 2026**. Sinkronisasi kontrak dan jalur aplikasi: **23 November 2026**. Status: **pengujian awal terkontrol; evaluasi domain akhir belum selesai**. Angka 6 November di bawah tetap merupakan hasil historis, bukan pengukuran ulang saat sinkronisasi.

Dokumen ini menjadi acuan menjalankan pengujian, memilih masukan, membaca hasil, dan mencatat perubahan. Panduan perlu digunakan bersama tes otomatis; keberadaan dokumen tidak menjamin kode bebas kesalahan. Setelah perubahan kode atau data, perbarui bukti pengujian di dokumen ini.

## 1. Alur dan batas pengujian

Alur bersama: **unggah gambar → OCR → periksa/sunting teks → analisis**. Setelah itu jalur klaim dan naskah berbeda:

| Jalur | Permintaan dengan prefix bawaan `/api/v1` | Hasil dan penyimpanan |
| --- | --- | --- |
| Klaim singkat | `/detect/image` menghasilkan teks editor; analisis memakai `/detect/text` dengan `input_type: IMAGE`. | Hasil klaim mempunyai ID untuk riwayat dan feedback sesuai hak akses. |
| Naskah atau beberapa gambar | OCR setiap gambar memakai `/detect/image`; teks atau daftar `pages` yang dikonfirmasi dikirim ke `/detect/document`. | Keputusan dan cakupan per segmen berada pada sesi halaman. Jalur ini belum menyimpan riwayat/feedback per segmen. |

Pada UI sekarang, teks lebih dari 60 kata atau pilihan analisis naskah memakai jalur dokumen. Periksa route yang benar-benar dikirim, bukan menganggap setiap hasil OCR selalu menjadi riwayat klaim. Lihat [halaman utama](../frontend/src/app/page.tsx), [rute](../src/api/routes/detection_routes.py), dan [Panduan Teks Panjang](PANDUAN_TEKS_PANJANG_DAN_MULTI_GAMBAR.md).

| Bagian | Tanggung jawab |
|---|---|
| `src/utils/ocr_extractor.py` | Menyiapkan gambar, memuat mesin OCR, membaca baris/skor, dan menghitung fitur kualitas. |
| `src/utils/ocr_pipeline.py` | Validasi masukan, pembersihan teks OCR, gerbang kualitas, kategori hasil, dan identitas kebijakan. |
| `src/api/routes/detection_routes.py` | Menghubungkan pipeline dengan unggahan HTTP; memisahkan hasil klaim tersimpan dari analisis naskah selama sesi. |
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
| U02 | `data/sample_panjang.png` | `[KUTIPAN RESMI PRESIDEN RI] Presiden Joko Widodo menegaskan bahwa penyaluran bantuan sosial tahun anggaran baru harus tepat sasaran.` |

U01 memiliki 49 karakter dan 6 kata. Acuan U02 sekarang mencakup judul yang terlihat pada gambar, dengan total 132 karakter dan 18 kata. Gunakan transkripsi seluruh gambar untuk metrik OCR. Jika yang ingin diuji hanya isi kutipan, tetapkan area pembacaan yang sama pada gambar dan transkripsi sebelum pengujian.

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

Runner memerlukan daftar JSON yang tidak kosong, berisi objek dengan `id` unik dan tidak kosong, `gambar` tidak kosong, serta `transkripsi_manual` bertipe string yang wajib disediakan. Acuan string kosong sah untuk kasus tanpa teks; acuan yang hilang berbeda dari acuan kosong. Manifest yang tidak ditemukan atau rusak ditolak sebelum model dimuat. Gambar yang hilang pada manifest yang sah tetap dicatat sebagai kegagalan kasus, bukan dibuang.

Periksa kesesuaian acuan dengan gambar sebelum menjalankan. Simpan identitas kelompok gambar sumber agar versi jelas/buram dari gambar yang sama tidak tersebar antara set kalibrasi dan evaluasi akhir. Label kebenaran klaim, jika digunakan untuk akurasi model, membutuhkan verifikasi terpisah dari transkripsi.

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

Hasil historis pada 6 November 2026 (cakupan ini tidak menyatakan jumlah tes pada revisi sekarang):

| Pemeriksaan | Hasil | Batas bukti |
|---|---|---|
| CLI dan evaluasi berpasangan | 19/19 lulus: 12 CLI + 7 evaluasi | OCR dan evaluator diganti tiruan pada pengujian kasus. |
| Endpoint gambar | 13/13 lulus | Permintaan HTTP ke aplikasi uji dengan pipeline tiruan. |
| Frontend | 84/84 lulus | Harness komponen/hook dan permintaan tiruan; belum browser nyata. |
| TypeScript | Lulus | Pemeriksaan tipe; bukan pengujian perilaku browser. |

Tidak ada mesin OCR, bobot model, atau akun/database sebenarnya yang digunakan pada verifikasi otomatis ini. Impor modul tetap dapat memuat pustaka seperti Torch; itu berbeda dari inisialisasi mesin dan pemuatan bobot.

Pemeriksaan runner pada **23 November 2026**, dijalankan sebagai dua proses terpisah:

| Perintah modul unittest | Hasil | Cakupan |
| --- | ---: | --- |
| `tests.test_ocr_evaluation -v` | 17/17 lulus | Fixture manifest, hasil model, ringkasan `main()`, kelanjutan batch, pasangan ambigu, dan perlindungan laporan. |
| `tests.test_ocr_cli -q` | 12/12 lulus | Fixture CLI OCR ke model. |

Keduanya menggunakan OCR/evaluator tiruan. Hasil ini tidak mengukur ulang CER/WER atau prediksi checkpoint pada gambar nyata. Perintah Python pada bagian ini dapat dipakai untuk menjalankan ulang modul tersebut di lingkungan proyek.

### B. Ulangi dua pasangan dengan acuan yang benar

Perintah berikut memakai dua gambar default dan membuat nama laporan bertimestamp di `reports/ocr`:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 uji_ocr_berpasangan.py
```

Perintah ini menjalankan OCR dan model sebenarnya; jangan menjalankannya sebagai tes mock. `--dataset` memilih manifest yang sudah disiapkan, sedangkan `--output` hanya menerima nama keluaran baru. Runner menolak tujuan yang sudah ada sebelum memuat model dan juga menolak benturan saat publikasi laporan. Laporan ditulis atomik; gambar, manifest, dan laporan lama tidak ditimpa.

Kesalahan argumen, manifest, atau tujuan yang ditolak sebelum eksekusi menghasilkan exit code 2. Kegagalan per kasus tetap menghasilkan laporan dan exit code 1; kegagalan publikasi laporan juga menghasilkan exit code 1 tanpa menimpa keluaran yang sudah ada. Penolakan input/mutu yang sah bukan otomatis galat eksekusi. Exit code 0 menyatakan runner selesai tanpa galat yang dicatat, bukan bahwa OCR atau klasifikasi seluruh kasus benar.

Laporan historis berikut memakai gambar yang tersedia pada **6 November 2026, 11:09:40 UTC+07:00**. Hash kedua gambar berbeda dari berkas dengan nama yang sama saat ini. [Laporan 6 November](../reports/ocr/evaluasi_berpasangan.json)

| Kasus | CER / WER | Hasil pada teks manual | Hasil pada teks OCR |
|---|---|---|---|
| U01 | 0% / 0% | Ditolak karena pendek | Ditolak kualitas; inferensi jalur OCR dilewati |
| U02 | 1,9231% / 21,4286% | `dinilai`, `TIDAK BERPOLA HOAKS`, suara 0/3 | `ambigu`, suara 2/3 |

Pada gambar U02 saat itu, laporan mencatat `label_sama=false` dan perbedaan bacaan pada `Presiden → residen` serta `tepat → te pat`. Kasus historis ini menunjukkan sensitivitas keluaran terhadap variasi transkripsi tersebut. [Laporan 6 November](../reports/ocr/evaluasi_berpasangan.json)

Percobaan sebelumnya dengan acuan berbeda menghasilkan CER/WER 104,4%/100% dan 43,4%/61,9%. Angka tersebut tidak digunakan untuk baseline ketepatan OCR. Mengubah acuan di kode tidak memperbarui laporan lama; simpan keluaran baru setiap putaran. Hasil metrik di atas bukan target yang harus dicapai dengan mengubah acuan; hasil eksekusi berikutnya tetap dicatat apa adanya.

**Pengujian ulang 23 November 2026.** Percobaan pertama mencatat dua galat mesin karena proses tidak dapat membaca cache lokal UVDoc. CER/WER tidak tersedia dan runner keluar dengan kode 1. Percobaan berikutnya membaca gambar U02, tetapi acuan awalnya belum mencakup judul pada gambar. CER 26,9231% dan WER 28,5714% pada percobaan itu mencakup selisih cakupan transkripsi. Pemeriksaan visual mengonfirmasi judul sebelum acuan dibetulkan. [Percobaan dengan galat akses cache](../reports/ocr/evaluasi_berpasangan_20261123_verifikasi_runner.json) · [Percobaan dengan acuan belum lengkap](../reports/ocr/evaluasi_berpasangan_20261123_verifikasi_ulang.json)

Putaran dengan acuan terverifikasi selesai dengan kode 0. PaddleOCR 3.7.0, PaddlePaddle 3.3.1, PaddleX 3.7.2, PyTorch 2.14.0, dan Transformers 5.17.0 dijalankan di CPU Windows dari cache lokal. IndoBERT memakai aturan `unanimous` dan verifikasi artefak aktif.

| Kasus | CER / WER | Hasil jalur manual dan OCR |
|---|---|---|
| U01 | 0% / 0% | OCR membaca seluruh teks dan gerbang mutu menolaknya karena pendek. Tidak ada pasangan keputusan model. |
| U02 | 0% / 0% | OCR membaca judul dan isi. Transkripsi manual dan OCR sama-sama `dinilai`, **TIDAK BERPOLA HOAKS**, dengan suara 0/3. |

Penyebutnya dua gambar terukur, satu gambar lolos gerbang OCR, dan satu pasangan keputusan model. Kedua berkas gambar berbeda hash dari laporan 6 November, sehingga angka ini tidak digunakan untuk mengukur peningkatan terhadap laporan historis. [Laporan dengan acuan terverifikasi](../reports/ocr/evaluasi_berpasangan_20261123_acuan_terverifikasi.json)

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
4. Untuk jalur klaim, periksa `/detect/text`, teks editor terakhir, dan `input_type: IMAGE`. Untuk naskah atau teks lebih dari 60 kata, periksa `/detect/document` dan teks/urutan `pages` yang dikonfirmasi; payload ini tidak memakai kontrak klaim.
5. Pada jalur klaim, cocokkan teks dan hasil dengan riwayat setelah refresh dan masuk ulang. Pada jalur naskah, cocokkan hasil per segmen serta cakupan selama sesi; jangan menganggapnya sudah tersimpan di riwayat.
6. Uji ganti/batalkan gambar saat loading: respons gambar sebelumnya tidak boleh menimpa gambar terbaru. Untuk beberapa gambar, uji urutan dan satu gambar gagal tanpa menyamarkan hasil halaman lain.
7. Periksa feedback hanya pada ID hasil klaim tersimpan yang memenuhi syarat, serta pemisahan data dua akun uji. LIME klaim memakai `/{detection_id}/explain`; LIME naskah memakai `/document/explain` untuk segmen asal yang sah.

Unggahan yang ditolak OCR tetap dicatat pada laporan evaluasi; tidak otomatis menjadi entri riwayat aplikasi. Sumber `IMAGE` tidak membuktikan gambar asli disimpan. Uji skrip OCR berpasangan juga tidak menguji route dokumen, editor, riwayat, atau feedback melalui browser.

## 5. Aturan membaca metrik dan latensi

- CER = jarak edit karakter / jumlah karakter acuan; WER = jarak edit token / jumlah token acuan. Skrip mempertahankan kapitalisasi dan tanda baca; WER memakai pemisahan `split()`.
- Rasio dapat melebihi 100% karena penyisipan. Acuan kosong tidak memiliki rasio yang sah; catat `null` beserta jumlah sisipan.
- Jika OCR selesai tetapi bacaannya kosong sementara acuan berisi teks, hitung penghapusan. Jika input ditolak sebelum OCR atau mesin gagal, gunakan metrik tidak tersedia; jangan menyamakan keduanya.
- Laporkan jumlah seluruh masukan, jumlah yang terukur, penolakan, galat, ambiguitas, serta jumlah pasangan yang dibandingkan. Nilai yang tidak tersedia tidak diganti nol.
- Ringkasan memisahkan rerata CER/WER per gambar pada OCR diterima dari rerata seluruh pasangan transkripsi yang terukur, termasuk penolakan mutu. Keduanya adalah rerata makro, bukan jumlah galat dibagi jumlah seluruh karakter/kata. Jumlah pasangan dan pembagi setiap gambar tetap dicatat; acuan kosong, penolakan sebelum OCR, serta galat mesin tidak diberi rasio buatan.
- Hanya dua hasil model yang sama-sama valid dan berstatus `dinilai` atau `ambigu`, lengkap dengan tiga keputusan seed serta aturan voting yang dapat dibandingkan, menjadi pasangan model pembanding. `label_sama` dan `votes_sama` dilaporkan terpisah. Penolakan input/domain yang sah tetap dicatat; kegagalan atau kontrak model rusak bukan pasangan valid. Dua hasil ambigu yang sama tidak membuktikan ketepatan atau ketahanan semantik.
- Pengukuran pertama/warm memakai gambar sama. Jalankan beberapa proses baru dan beberapa pengulangan warm; laporkan jumlah pengulangan, median, variasi, perangkat, dan versi runtime. Laporan historis 6 November mencatat 7,477 detik dan 2,740 detik (sekitar 2,7×); satu perbandingan hanya pengamatan awal.
- Skrip sekarang memuat IndoBERT sebelum pengukuran OCR. Angka tersebut bukan waktu awal seluruh aplikasi, serta belum memisahkan inisialisasi OCR, praproses, dan pengenalan.

## 6. Kontrak sinkronisasi 23 November dan batas yang tersisa

Kontrak runner yang diselaraskan pada revisi ini:

- `--dataset` yang tidak ditemukan tidak beralih ke default. Manifest daftar/objek, ID unik, jalur gambar, dan keberadaan string acuan diperiksa sebelum inferensi; acuan kosong tetap sah untuk kasus tanpa teks.
- Keluaran model diperiksa dengan kontrak yang dipakai API. Penolakan input/domain dibedakan dari kegagalan; hanya pasangan model valid masuk perbandingan konsistensi.
- Ringkasan memisahkan OCR diterima, penolakan, galat, seluruh metrik transkripsi terukur, dan pasangan model valid. Kasus gagal tidak menghilang dari total.
- Laporan atomik dan penolakan overwrite menjaga laporan lama. Gunakan nama baru walaupun putaran sebelumnya gagal.
- Laporan menyertakan kebijakan/konfigurasi OCR dan hash yang tersedia, metadata audit model yang tersedia, teks praproses, suara/keputusan seed, serta skor debug yang dibulatkan. Skor debug bukan representasi probabilitas dengan presisi penuh; keputusan biner asli tetap acuan voting.

Hasil tes revisi ini harus dilaporkan terpisah dari tabel historis 6 November, dengan command, cakupan fixture, dan revisi kode. Perubahan runner tidak memperbarui otomatis laporan `evaluasi_berpasangan.json` yang lama.

Hal yang tetap memerlukan bukti:

- Identitas model OCR yang benar-benar dipilih, versi runtime lengkap, dan perangkat harus diverifikasi pada lingkungan pengujian. `lang="id"` dan hash kebijakan saja tidak membuktikan lingkungan identik.
- Metrik runner memakai `teks_bersih` sebelum edit pengguna. Evaluasi OCR mentah dan edit pengguna merupakan perbandingan terpisah; jangan menyebut ketiganya sudah diukur hanya karena tersedia satu CER/WER.
- Transkripsi dan label klaim independen, gambar nyata, kondisi kamera/buram/miring, serta jumlah sampel pilot masih perlu disiapkan dan diperiksa sebelum inferensi. Dua gambar default dan fixture tidak membuktikan generalisasi.
- Browser, akun sebenarnya, penyimpanan riwayat/feedback klaim, dan perilaku naskah selama sesi memerlukan pengujian integrasi tersendiri. Tes mock tidak membuktikan PostgreSQL atau perangkat kamera nyata.
- Fixture terbaru mencakup ringkasan `main()`, kegagalan model per kasus, pasangan ambigu yang valid, kelanjutan batch, perlindungan keluaran, dan penyebut. Kelulusan fixture membuktikan perilaku yang dicakupnya; sebelum memperbesar dataset, bekukan konfigurasi dan manifest serta periksa kembali hasil pada gambar acuan yang benar.

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
Jumlah pasangan transkripsi terukur / pasangan model valid:
CER/WER mentah dan bersih, berikut pembaginya:
Jumlah pengulangan dan hasil latensi:
Hasil uji editor / riwayat / feedback jika dilakukan:
Keterbatasan dan keputusan menerima atau menolak kandidat:
```

Notebook Jupyter membaca keluaran yang sudah diverifikasi untuk tabel dan grafik; notebook tidak menetapkan ulang acuan atau mengubah praproses aplikasi. Rencana perubahan awal disimpan sebagai arsip di [RENCANA_OPTIMASI_OCR.md](RENCANA_OPTIMASI_OCR.md).

Kontrak API, berkas terkait, dan langkah pengujian detail/penghapusan riwayat pengguna dicatat di [PANDUAN_RIWAYAT.md](PANDUAN_RIWAYAT.md).
