# Rencana optimasi OCR secara bertahap

Tanggal pemeriksaan awal: 4 November 2026. Status: **arsip rencana awal**.

> Temuan, nomor baris, contoh kode, dan status di bawah menggambarkan pemeriksaan awal, bukan keadaan implementasi sekarang. Gunakan [PANDUAN_PENGUJIAN_OCR.md](PANDUAN_PENGUJIAN_OCR.md) untuk perintah, status verifikasi, dan kekurangan yang masih terbuka pada 6 November 2026. Contoh pemanggilan pembersihan lama di arsip ini tidak menjadi petunjuk implementasi saat ini; gunakan pipeline aktif.

Dokumen ini memetakan berkas, bagian kode, urutan perubahan, dan kriteria selesai pada saat rencana disusun. Saat penyusunan awal hanya dokumen ini yang dibuat; kode aplikasi, skrip evaluasi, dependensi, dan database belum diubah dalam pekerjaan tersebut. OCR, model, dan koneksi database tidak dijalankan ulang saat itu.

Alur sasaran: **unggah gambar → ekstraksi OCR → periksa/sunting teks → analisis model → verdict → riwayat**.

## Kondisi kode yang diperiksa

Nomor baris mengikuti kondisi saat dokumen dibuat. Setelah ada perubahan, gunakan nama fungsi sebagai acuan utama.

| Temuan pada pemeriksaan 4 November 2026 | Lokasi |
|---|---|
| Skrip masih mengimpor `ocr_paddle3` yang tidak ada di root | `uji_ujung_ke_ujung.py:9` |
| Skrip meneruskan OCR mentah ke model, sedangkan endpoint membersihkannya terlebih dahulu | `uji_ujung_ke_ujung.py:30`; `src/api/routes/detection_routes.py:263` |
| Berkas sementara dihapus sebelum seluruh hasil `predict()` dikonsumsi; perlu diperbaiki agar aman untuk iterator | `src/utils/ocr_extractor.py:77`, `ocr_lines()` |
| Unggahan diperiksa berdasarkan MIME saja, dibaca tanpa batas, dan OCR sinkron dipanggil dari endpoint async | `src/api/routes/detection_routes.py:222` |
| Pemeriksaan 50 karakter dilakukan sebelum pembersihan | `src/api/routes/detection_routes.py:249` |
| Pembersihan OCR membuang seluruh karakter non-ASCII | `src/utils/text_preprocessor.py:56`, `clean_ocr_artifacts()` |
| Preview URL dibuat, tetapi gambar belum ditampilkan; alasan gagal OCR diganti pesan umum | `frontend/src/components/detector/NewsInputForm.tsx:45` |
| Analisis gambar akhirnya mengirim `{ text }` tanpa sumber `IMAGE` | `frontend/src/hooks/useDetection.ts:21`; `frontend/src/app/page.tsx:30` |
| Hook `detectImage()` memperlakukan respons ekstraksi sebagai verdict | `frontend/src/hooks/useDetection.ts:93` |
| Dependensi mencantumkan EasyOCR, belum PaddleOCR/PaddlePaddle | `requirements.txt` |

Pada pemeriksaan awal, helper `src/utils/ocr_pipeline.py` dan laporan evaluasi yang disebut pada percakapan sebelumnya belum tersedia pada workspace yang diperiksa. Karena itu, rencana awal ini tidak menganggap perubahan tersebut sudah diterapkan. Pipeline dan skrip evaluasi kini sudah tersedia; status pengujian terbarunya dicatat pada panduan pengujian.

## Aturan pengerjaan

1. Kerjakan satu perubahan logis, periksa hasilnya, lalu lanjut ke langkah berikutnya. Bagian berbeda dalam berkas yang sama dapat dikerjakan dalam putaran terpisah.
2. Saat mengubah kontrak antarberkas, tambahkan kemampuan opsional terlebih dahulu, kemudian hubungkan pemanggilnya. Pertahankan pemanggilan teks biasa selama perpindahan.
3. Catat hasil sebelum/sesudah pada masukan yang sama. Perubahan yang mempercepat tetapi merusak bacaan nama, angka, negasi, atau urutan teks tidak otomatis diterima.
4. Pertahankan bobot, `text_pipeline.py`, jalur praproses model, aturan keputusan seed, dan padding token tetap. Padding dinamis tetap eksperimen terpisah selama investigasi paritas belum selesai.
5. Confidence OCR bukan ukuran kebenaran transkripsi. Keputusan menerima perubahan kualitas harus memakai acuan manual dan dampak pada analisis.

## Urutan berkas dan perubahan

### 1. Perbaiki titik masuk pengujian

**Berkas pertama: `uji_ujung_ke_ujung.py`.**

Bagian yang akan diubah:

- Baris 9: ganti impor modul yang hilang dengan modul OCR aktif.
- Baris 18: tunda pemuatan model sampai gambar lolos gerbang OCR. Masukan tertolak tidak perlu memuat IndoBERT.
- Bagian sebelum pemanggilan `pred.nilai()` pada baris 30: gunakan `clean_ocr_artifacts()`; simpan OCR mentah dan teks bersih secara terpisah.
- Bagian argumen/loop: tempatkan eksekusi di dalam `main()` agar modul evaluasi dapat diimpor tanpa menjalankan OCR/model.
- Catat setiap kasus beserta status/alasan, termasuk kasus gagal atau ditolak. Jangan menghilangkan sampel dari ringkasan karena `continue`.

Contoh bagian pengganti yang **direncanakan**, belum diterapkan:

```python
from src.utils import ocr_extractor as op
from src.utils.text_preprocessor import clean_ocr_artifacts

# Setelah hasil OCR tersedia dan pemeriksaan kelayakan selesai:
teks_bersih = clean_ocr_artifacts(r["text"])
# Model nantinya menerima teks_bersih, bukan r["text"] langsung.
```

Kriteria selesai: skrip memakai modul yang tersedia, OCR mentah/bersih dapat dilihat terpisah, dan model tidak dimuat untuk gambar tertolak. Ini baru baseline ekstraksi/model; kesamaan seluruh gerbang HTTP diselesaikan pada langkah 4–5.

### 2. Selaraskan dependensi dengan mesin aktif

**Berkas: `requirements.txt`.**

Periksa versi PaddleOCR, PaddlePaddle, Pillow, dan NumPy yang terpasang serta kompatibilitas runtime. Tambahkan dependensi mesin aktif dengan versi yang sudah dibuktikan bekerja. Cari seluruh penggunaan EasyOCR sebelum memutuskan mempertahankan atau menghapusnya. Catat identitas model OCR dan konfigurasi CPU bersama hasil evaluasi; jangan mengandalkan `lang="id"` saja untuk membandingkan dua lingkungan.

Kriteria selesai: lingkungan uji dapat direproduksi dari dependensi terdokumentasi. Pemasangan lingkungan baru dilakukan pada tahap implementasi, bukan saat menyusun rencana ini.

### 3. Stabilkan pembacaan dan sumber daya OCR

**Berkas: `src/utils/ocr_extractor.py`.** Kerjakan bagian berikut bergiliran:

| Putaran | Bagian | Perubahan yang direncanakan |
|---|---|---|
| 3a | `ocr_lines()` baris 77 | Konsumsi seluruh hasil OCR di dalam `try`; hapus berkas sementara melalui `finally` setelah konsumsi selesai. |
| 3b | `_to_path()` baris 41 | Bersihkan berkas sementara jika `save()` gagal; tutup gambar yang dibuka sendiri; tangani dimensi ekstrem agar tinggi resize tidak menjadi nol. |
| 3c | `_OCR`, `get_ocr()`, `reset_ocr()` | Atur inisialisasi dan pemakaian mesin global agar unggahan bersamaan tidak memakai instance secara tidak terkendali. |
| 3d | `extract_text_from_image()` baris 136 | Pertahankan struktur hasil mentah untuk evaluasi; bedakan galat mesin dari penolakan kualitas pada lapisan pemanggil. |

Kriteria selesai: tidak ada berkas sementara tertinggal setelah sukses/gagal; iterator dapat membaca gambar sampai selesai; unggahan bersamaan tidak menukar hasil atau membuat mesin berulang. Gerbang 10 kata/confidence 0,60 serta resize 1400 dan margin 15 piksel belum diubah.

Tes yang akan disiapkan: `tests/test_ocr_pipeline.py` (baru), dimulai dengan pengujian iterator, pembersihan berkas sementara, dan kegagalan simpan/prediksi.

### 4. Buat satu layanan persiapan OCR

**Berkas baru yang direncanakan: `src/utils/ocr_pipeline.py`.**

Pisahkan fungsi berikut agar API dan evaluasi tidak menyalin aturan sendiri:

- `validate_image_upload(contents, content_type)`: MIME, isi/dekode berkas, kosong/rusak, batas byte, dan batas piksel.
- `prepare_ocr_for_analysis(ocr_raw)`: gerbang OCR → pembersihan → pemeriksaan kelayakan teks yang akan masuk editor.
- `prepare_image_text(contents, content_type)`: penggabung kedua fungsi dengan mesin OCR aktif.
- `OCRInputError`: status HTTP, pesan pengguna, dan hasil OCR mentah bila tersedia untuk evaluasi.

Usulan batas awal operasional: **10 MiB dan 20 juta piksel**, dicatat sebagai kebijakan produk yang akan diuji, bukan nilai optimum yang sudah terbukti. Pertahankan ambang confidence awal. Usulan kelayakan setelah pembersihan: minimal 10 kata dan 50 karakter, agar editor tidak menerima teks yang menjadi kosong/pendek setelah URL atau artefak dibuang.

Kriteria selesai: PNG/JPEG/WebP valid diterima; file kosong/rusak/format palsu/terlalu besar ditolak sebelum mesin dipanggil. Nilai tepat pada batas dan satu unit di atasnya diuji. Penolakan tetap membawa hasil OCR mentah jika OCR sudah berjalan.

### 5. Hubungkan API dan skrip ke layanan yang sama

Kerjakan konsumennya satu per satu:

| Berkas | Bagian | Perubahan |
|---|---|---|
| `src/api/routes/detection_routes.py` | `extract_text_from_image_upload()` baris 222 | Pembacaan unggahan terbatas, delegasi ke layanan bersama, OCR melalui threadpool, dan pemetaan galat ke pemberitahuan. |
| `uji_ujung_ke_ujung.py` | Loop pengujian | Gunakan layanan yang sama; hapus validasi/pembersihan OCR yang menjadi duplikasi. |
| `src/api/schemas.py` | `OCRResultData` baris 12 | Pertahankan field lama; tambahkan metadata hanya bila editor/evaluasi memerlukannya. `reason` untuk UI harus memiliki tipe yang konsisten. |

Usulan kontrak: 400 untuk berkas tidak valid, 413 untuk ukuran berlebih, 422 untuk teks/kualitas tidak layak, dan 503 untuk gangguan mesin. Detail exception internal masuk log server. Jangan menganggap keluaran yang kehilangan atribut kelayakan sebagai diterima.

Kriteria selesai: API dan skrip menghasilkan teks editor, status penerimaan, serta alasan yang sama pada fixture identik. Permintaan ringan tetap responsif saat OCR berjalan. Threadpool tidak dianggap membuat OCR lebih cepat; tujuannya menjaga event loop tetap responsif. Batas antrean/penguncian ditetapkan melalui uji beban kecil.

### 6. Tinjau pembersihan teks tanpa merusak isi

**Berkas: `src/utils/text_preprocessor.py`, khusus `clean_ocr_artifacts()` baris 56.**

Evaluasi pengganti penghapusan non-ASCII secara menyeluruh. Kandidat: normalisasi Unicode dan penghapusan artefak yang terbatas, sambil mempertahankan huruf, angka, tanda baca bermakna, dan pemisah kata. Uji pada nama, tanda kutip, persen, nominal, rentang angka, negasi, dan karakter tersembunyi. Ukur perbedaan sebelum/sesudah pembersihan agar skor bersih tidak menyembunyikan teks yang terhapus.

Jangan menambahkan koreksi ejaan otomatis, perubahan angka/nama, atau penyambungan tanda hubung global pada tahap ini. Koreksi semacam itu dapat mengubah klaim. Eksperimen pemenggalan baris harus terpisah dan terukur.

Kriteria selesai: kasus normal tetap terbaca, tidak ada penggabungan/penghapusan informasi penting, dan CER/WER berpasangan tidak memburuk pada set pengembangan yang sudah dipisahkan.

### 7. Perbaiki frontend dalam urutan dependensi

| Urutan | Berkas dan bagian | Perubahan yang direncanakan |
|---|---|---|
| 7a | `frontend/src/types/detector.ts` | Kontrak `OCRResponse` terpisah dari verdict dan metadata sumber `TEXT`/`IMAGE`. |
| 7b | `frontend/src/hooks/useDetection.ts:21` | `detectText(text, source?)` mengirim metadata opsional. Audit lalu hapus/ubah hook `detectImage()` baris 93 yang mencampur hasil OCR dengan verdict. |
| 7c | `frontend/src/app/page.tsx:30` | Teruskan metadata dari formulir ke hook; reset/remount formulir berdasarkan `userId` pada bagian `NewsInputForm`. |
| 7d | `NewsInputForm.tsx:45`, `handleImageSelect()` | Validasi file mengikuti backend, kosongkan hasil lama, cegah unggahan ganda dengan ref, gunakan pembatalan dan nomor generasi permintaan. Biarkan browser menetapkan boundary multipart. |
| 7e | Berkas yang sama, area gambar baris 174 dan tombol ganti baris 206 | Tampilkan gambar sebenarnya, loading dan kontrol batal/ganti; bersihkan object URL dan reset input file. |
| 7f | Berkas yang sama, `catch`, editor baris 222, pesan baris 237 | Tampilkan alasan backend; bedakan format, kualitas, sesi, koneksi, dan timeout. Editor/tombol mengikuti status proses dan penolakan. |
| 7g | Berkas yang sama, props baris 23 dan `handleSubmit()` baris 72 | Kirim teks editor terbaru setelah trim dengan `input_type: IMAGE`; teks biasa tetap `TEXT`. |

Timeout OCR ditetapkan terpisah berdasarkan pengukuran, termasuk cold start; jangan menaikkan timeout global sebagai pengganti perbaikan mesin. Label “Konteks Politik Valid” perlu diperjelas karena saat ini hanya substring kata kunci frontend, bukan keputusan gerbang backend.

Kriteria selesai: unggahan A dibatalkan lalu diganti B tidak dapat ditimpa respons A; pergantian akun membersihkan OCR; teks yang dikirim sama dengan editor; sumber gambar sampai ke API. `blob:` URL tidak disimpan sebagai URL permanen.

Tes yang direncanakan: perluas `tests/test_frontend_guest_access.cjs` dan tambah `tests/test_frontend_ocr.cjs`. Verifikasi TypeScript, perilaku komponen, kemudian browser; ketiganya merupakan tingkat bukti berbeda.

### 8. Lengkapi evaluasi berpasangan sebelum mengubah parameter

**Berkas: `uji_ujung_ke_ujung.py`; berkas baru tes `tests/test_ocr_evaluation.py`.**

Tambahkan manifest CSV dengan ID unik, kelompok gambar sumber, jalur gambar, transkripsi manual, kondisi, serta label klaim opsional. Simpan teks mentah, teks bersih, teks suntingan, prediksi manual/OCR/suntingan, alasan, waktu, versi, dan konfigurasi. Pertahankan satu baris untuk setiap masukan.

Ukur:

- CER/WER mentah dan setelah pembersihan, dengan normalisasi tertulis serta jumlah sampel terukur.
- Cakupan keputusan, penolakan, ambiguitas, dan galat terhadap seluruh masukan.
- Kesepakatan serta perubahan verdict pada pasangan yang sama-sama diputuskan; laporkan juga transisi menuju penolakan/ambiguitas.
- Akurasi hanya untuk label klaim yang diverifikasi, baik pada keputusan yang tersedia maupun keputusan benar terhadap seluruh sampel berlabel. Kesepakatan prediksi bukan akurasi.

Jika format ditolak sebelum OCR, CER/WER tidak tersedia; masukan tetap masuk total. Jika OCR menghasilkan kosong pada acuan berisi teks, hitung kesalahan penghapusan. Acuan kosong tidak diberi rasio buatan; simpan jumlah sisipan. Jangan hanya mengukur sampel yang lolos.

Pastikan transkripsi manual dan OCR melewati gerbang teks/model yang sama. Bagian validasi awal HTTP pada `detect_text()` dapat diekstrak ke helper tersendiri jika diperlukan; jangan mengubah urutan sanitasi/domain diam-diam untuk mengejar paritas.

Kriteria selesai: kasus gambar jelas wajib memiliki ekspektasi penerimaan OCR; penolakan semua gambar tidak dapat dianggap lulus. Pisahkan kelompok klaim antara kalibrasi dan evaluasi akhir. Kumpulan sintetis menguji fungsi; tangkapan layar nyata diperlukan untuk menilai kualitas penggunaan.

### 9. Optimalkan kecepatan dan bacaan lewat eksperimen terpisah

**Berkas utama: `src/utils/ocr_extractor.py`, terutama `OCR_KWARGS`, `get_ocr()`, `_to_path()`, dan `join_lines()`.**

Mulai setelah langkah 8 tersedia. Kandidat berikut belum merupakan perubahan default:

| Putaran | Kandidat | Bukti yang diperlukan |
|---|---|---|
| 9a | Konfigurasi eksplisit orientasi dokumen, pelurusan dokumen, dan orientasi baris | Bandingkan screenshot tegak, miring, serta foto dokumen. API instalasi menyediakan `use_doc_orientation_classify`, `use_doc_unwarping`, dan `use_textline_orientation`; manfaat menonaktifkannya belum diasumsikan. |
| 9b | Pengaturan resize dan penanganan orientasi EXIF | Uji teks kecil, gambar panjang/lebar, teks dekat tepi, dan gambar berorientasi berbeda. Margin 15 piksel tetap sebagai baseline. |
| 9c | Model OCR lebih ringan atau konfigurasi CPU | Catat model/versi dan bandingkan pada perangkat sasaran dengan gambar identik. Model ringan tidak otomatis setara kualitasnya. |
| 9d | Penyambungan pemenggalan baris atau pemanfaatan posisi kotak teks | Bandingkan urutan baca dan CER/WER; lindungi nama majemuk dan rentang angka. Jangan mengganti urutan baris hanya berdasarkan asumsi. |

Ukur waktu dekode, praproses gambar, inisialisasi mesin, OCR, dan total. Pisahkan cold start/warm; laporkan p50/p95, RAM, serta waktu antrean ketika ada beberapa unggahan. Target latensi absolut dan toleransi penurunan kualitas ditetapkan setelah baseline, sebelum memilih kandidat. Jika hasil campuran, laporkan tradeoff per kondisi; jangan menyatakan “optimal” dari satu contoh.

### 10. Kalibrasi gerbang kualitas OCR

**Berkas: `src/utils/ocr_extractor.py`, `fitur_kualitas()` baris 101, `ATURAN_AWAL` baris 116, dan `putuskan()` baris 119.**

Pertahankan ambang awal selama evaluasi kandidat. Nilai tambahan yang dapat dianalisis: proporsi baris confidence rendah, panjang baris, token rusak, dan kesalahan unsur penting. Periksa validitas skor serta kecocokan jumlah teks/skor. Rerata confidence saja dapat menutupi satu baris penting yang salah.

Baru setelah anotasi tersedia, tentukan kebijakan menerima, meminta koreksi, atau menolak. Jangan menaikkan confidence ke angka lain atau menolak berdasarkan blur semata tanpa mengukur kesalahan terima/tolak dan dampak pada coverage.

Kriteria selesai: aturan dipilih dari set kalibrasi, dibekukan, lalu dinilai pada set terpisah. Laporan mencakup OCR buruk yang lolos, OCR layak yang tertolak, dan kualitas transkripsi pada hasil diterima.

### 11. Verifikasi riwayat/feedback, lalu lanjutkan domain

| Berkas | Bagian yang ditinjau | Target |
|---|---|---|
| `src/api/routes/user_routes.py:109` | `get_user_history()`, khusus fallback baris 181 | Bedakan hasil ditolak, di luar domain, dan ambigu. |
| `src/api/routes/feedback_routes.py:19` | `submit_feedback()`, sebelum upsert | Feedback hanya untuk status yang memiliki hasil model; kepemilikan tetap diperiksa. |
| `src/api/routes/detection_routes.py:49` | Penyimpanan `input_text`/`input_type` | Teks final editor dan sumber IMAGE cocok dengan verdict serta riwayat. |
| `src/utils/political_guardrail.py` | `sub_topik()`, prioritas NOISE, aturan kata kunci | Evaluasi terpisah dengan label domain manusia, termasuk topik campuran dan Unicode. |
| `frontend/src/components/detector/NewsInputForm.tsx` dan `frontend/src/app/page.tsx` | Indikator domain dan fokus isu | Hindari indikator yang mengesankan validasi backend; pilihan fokus isu belum digunakan inferensi. |

Perbaikan penyimpanan sumber IMAGE **tidak memerlukan migrasi**: `TextDetectionRequest` dan `PredictionLog` sudah mendukung `input_type`, dan riwayat mengembalikannya. Penyimpanan OCR asli, confidence, alasan, serta detail seed secara permanen merupakan pekerjaan skema/migrasi terpisah bila dibutuhkan. Penyimpanan gambar asli juga keputusan fitur tersendiri.

Tes terisolasi yang direncanakan: `tests/test_detection_history_pipeline.py`, menggunakan akun/database memori dan kontrak routing asli. Sesudah itu gunakan akun uji sebenarnya pada layanan yang ditetapkan: unggah → koreksi nama/angka → analisis → baca kembali riwayat → refresh/logout-login → feedback pada ID yang sama → periksa isolasi akun kedua. Jangan menganggap keberhasilan database memori sebagai keberhasilan PostgreSQL.

Penolakan OCR masuk ledger evaluasi. Riwayat aplikasi saat ini baru dibuat ketika `/detect/text` berjalan; menampilkan semua unggahan tertolak di riwayat akan menjadi perubahan fitur tambahan.

## Paket pertama pada rencana awal

Rencana awal dimulai dari **langkah 1, `uji_ujung_ke_ujung.py` saja**: perbaiki impor, pisahkan OCR mentah/bersih, tunda pemuatan model, dan buat titik masuk yang dapat diuji. Hasil langkah itu diperiksa sebelum beralih ke dependensi atau mesin OCR. Tidak ada parameter pengenalan atau ambang yang direncanakan berubah pada paket pertama.

Status seluruh langkah pada saat dokumen awal disusun adalah **belum dikerjakan**. Status tersebut tidak berlaku sebagai checklist implementasi sekarang. Untuk pekerjaan berikutnya, gunakan panduan pengujian dan catat hasil setiap putaran beserta berkas yang berubah, pengujian yang dijalankan, serta keputusan menerima atau membatalkan perubahan.
