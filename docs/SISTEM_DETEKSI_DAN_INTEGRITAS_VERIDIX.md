# Deteksi Pola Hoaks Politik dan Integritas VERIDIX

**19 November 2026.** Gunakan nama **VERIDIX** dalam dokumentasi, laporan, dan naskah penelitian. Dokumen ini menjelaskan sistem yang berjalan, bukti evaluasi yang tersedia, dan urutan kerja yang diusulkan. Evaluasi final mengikuti [protokol penelitian](PROTOKOL_PRAREGISTRASI.md).

## 1. Tujuan dan makna hasil

VERIDIX membantu pengguna menilai kemiripan pola bahasa pada klaim politik Indonesia dengan contoh yang dilabeli hoaks di korpus penelitian. Pengguna dapat memasukkan klaim atau menyunting teks hasil PaddleOCR sebelum mengirimnya. Verifikasi kebenaran sebuah peristiwa memerlukan sumber asli, konteks, dan pemeriksaan bukti secara terpisah.

Sistem menjalankan klasifikasi dengan IndoBERT dan checkpoint Cross-Entropy untuk seed 42, 123, dan 999. Penjelasan dibuat dengan LIME. Kartu hasil memakai templat untuk menjelaskan keputusan dan batas hasil. [Kode inferensi](../src/ml/inference.py) · [Referensi Sistem](REFERENSI_SISTEM.md)

| Kondisi pada aturan bawaan *unanimous* | Makna yang ditampilkan |
| --- | --- |
| 3 dari 3 seed memberi suara hoaks | **Berpola hoaks** pada teks yang dinilai. |
| 0 dari 3 seed memberi suara hoaks | **Tidak berpola hoaks** pada teks yang dinilai. |
| 1 atau 2 seed memberi suara hoaks | **Ambigu, perlu verifikasi** karena seed berbeda keputusan. |
| Masukan ditolak atau di luar domain | Tampilkan alasannya. Skor dan kesepakatan tidak tersedia. |
| Model, OCR, API, atau database gagal | Tampilkan kegagalan pada tahap terkait. Konfirmasi penyimpanan mengikuti respons server. |

Setiap seed memberi suara hoaks jika skor kelas hoaks **≥ 0,5**. Laporan eksperimen mencatat aturan voting yang benar-benar dipakai karena lingkungan dapat mengubah aturan bawaan. Dalam mode *unanimous*, ambiguitas berasal dari perbedaan suara antar-seed. Rasio kesepakatan 100% berarti ketiganya mengambil kelas yang sama. Ketiganya masih dapat salah pada klaim yang sama. [Aturan voting](../src/ml/inference.py) · [Ambang yang ditampilkan admin](../src/api/routes/admin_routes.py)

## 2. Alur aplikasi

~~~mermaid
flowchart LR
    A["Masukan teks"] --> E["Validasi teks dan gerbang politik"]
    B["Gambar"] --> C["PaddleOCR dan pemeriksaan mutu"]
    C --> D["Pengguna memeriksa atau menyunting teks"]
    D --> E
    E --> F["Praproses klaim atau segmentasi naskah"]
    F --> G["IndoBERT dan voting"]
    G --> H["Hasil klaim atau hasil per segmen"]
    H --> I["LIME saat diminta"]
    H --> J["Riwayat dan feedback untuk hasil klaim yang tersimpan"]
~~~

| Jalur | Perilaku dan batas |
| --- | --- |
| Klaim singkat | Praproses dengan batas 60 kata, kemudian tokenizer dengan batas 128 token termasuk token khusus. Status pemotongan bisa benar, salah, atau belum diketahui. Teks praproses belum tentu sama dengan bagian yang masuk setelah batas tokenizer. |
| Naskah panjang | Mode eksperimental menampilkan keputusan per segmen, cakupan, dan bagian yang belum dinilai. Jalur ini memakai rentang sumber dan perlu dievaluasi tersendiri karena masukan model dapat berbeda dari jalur klaim singkat. Hasilnya tersedia selama sesi halaman. |
| Gambar | Pemeriksaan format, ukuran, dan mutu baca mendahului penilaian teks. Pengguna bisa memeriksa angka, nama, dan negasi seperti “tidak” sebelum analisis. |
| LIME | Dihitung saat diminta. Bobot positif menaikkan rerata skor kelas hoaks dan bobot negatif menurunkannya pada penjelasan lokal. Keputusan label mengikuti voting. Stabilitas kata yang muncul perlu diukur secara terpisah. |
| Riwayat dan tinjauan | Hasil awal, feedback pengguna, dan tinjauan admin mempunyai peran berbeda. Tinjauan memperbarui status dan catatan feedback. Pelatihan serta penerbitan checkpoint berjalan melalui proses penelitian terpisah. |

[Rute deteksi](../src/api/routes/detection_routes.py) · [Naskah dan banyak gambar](PANDUAN_TEKS_PANJANG_DAN_MULTI_GAMBAR.md) · [Integrasi LIME](PANDUAN_INTEGRASI_LIME.md) · [Rute feedback](../src/api/routes/feedback_routes.py)

## 3. Bukti penelitian dan peran setiap set

| Set atau bukti | Fungsi dan batas kesimpulan |
| --- | --- |
| Train, **1.660** baris | Pelatihan bobot. Audit mencatat 830 baris untuk masing-masing kelas. |
| Validation, **236** baris | Pemilihan epoch dan konfigurasi CE/Focal Loss sesuai protokol. Ada 118 baris per kelas. Aturan ambiguitas aplikasi berasal dari voting tiga seed. |
| Dev-test, **236** baris | Diagnostik ketahanan sesuai protokol. Ada 118 baris per kelas. Pemeriksaan C1–C6 menilai karakteristik korpus dan dilaporkan terpisah dari akurasi checkpoint. |
| Paritas CPU–Colab | Audit mencatat 472 teks validation dan dev-test × 3 seed, dengan **0 perbedaan dari 1.416 keputusan kelas**. Perbandingan memakai kolom teks beku. Probabilitas bit-identik, API, OCR, dan LIME berada di luar cakupannya. |
| Berita baru | Mengukur transfer ke waktu, sumber, topik, dan gaya di luar korpus latih. Dua contoh November 2026 mendukung uji fungsional pada pasangan itu. Kemampuan umum dan penyebab perbedaan skor memerlukan rancangan pembanding. |
| Lockbox | Protokol menetapkan evaluasi final sekali per seed serta pelaporan per seed dan rerata ± simpangan baku. Ukuran performa voting aplikasi dilaporkan terpisah. Audit terdahulu mencatat pemeriksaan hash. Bukti yang diperiksa belum memuat laporan evaluasi final. Jumlah baris lockbox tidak diverifikasi pada pemeriksaan dokumentasi ini. |

[Audit dataset dan model](../reports/AUDIT_MODEL_2026-10-24.md) · [Laporan paritas](../reports/audit_model_2026-10-24_parity.json) · [Log pelatihan](../log_training.json) · [Protokol](PROTOKOL_PRAREGISTRASI.md)

Pada data pengembangan yang diaudit, setiap sumber menyumbang satu kelas. Keterkaitan ini memungkinkan model memakai ciri gaya penerbit untuk menebak label. C4 pada dataset beku tercatat **72,46%**, melampaui batas **60%**. Adendum protokol mencatat angka itu dan mempertahankan **66,6%** sebagai catatan tahap sebelumnya. Tiga seed memberi informasi tentang variasi antar-run pada rancangan ini. Generalisasi tetap perlu diukur. [Hasil kriteria](../data/processed_v2/hasil_kriteria.csv) · [Audit keterbatasan](../reports/AUDIT_MODEL_2026-10-24.md) · [Adendum protokol](PROTOKOL_PRAREGISTRASI.md)

## 4. Rancangan uji berita baru dan OCR

Urutan kerja **23 November 2026**. Mulai dari uji pasangan klaim singkat pada checkpoint aktif. Pilot eksternal dan OCR mengikuti adendum penelitian. Tetapkan kriteria sebelum melihat keluaran untuk setiap putaran. [Adendum protokol](PROTOKOL_PRAREGISTRASI.md#114-rencana-prospektif-pilot-klaim-dan-ocr)

### 4.1 Periksa kontrak dan siapkan evaluator

Jalankan tes berikut dari root proyek. Tes memakai backend dan pemuat model tiruan untuk memeriksa keputusan seed, metadata pemotongan, serta penanganan pemuatan artefak.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_inference_text_contract tests.test_consensus_metadata tests.test_model_loading -q
```

Pada pemeriksaan awal 23 November 2026, **31 tes lulus**. Setelah runner pasangan diperbarui, **9/9 tes `tests.test_evaluasi_set_luar` lulus** dan CLI `--pairs --stub` pada fixture empat baris menghasilkan dua pasangan yang dapat dibandingkan, dengan laporan sementara terpisah. Pemeriksaan ini membuktikan perilaku pada fixture yang diuji, bukan kualitas checkpoint pada klaim baru. Hasil model nyata pada pasangan belum diklaim dari pengujian itu.

Gunakan [runner eksternal](../evaluasi_set_luar.py) melalui CLI dengan `--pairs` untuk evaluator pasangan. Runner memvalidasi CSV sebelum memuat model dan memakai `validate_claim_result` yang sama dengan API. Status dan label rusak dicatat sebagai kegagalan per baris, bukan dipetakan menjadi kelas 0; baris lain tetap diproses. Entry point aman diimpor untuk tes terisolasi. Keluaran berupa satu CSV atomik pada jalur baru; input dan laporan yang sudah ada tidak ditimpa. [Kontrak model](../src/ml/inference.py)

### 4.2 Susun dan kunci pasangan klaim

Gunakan satu baris per versi teks. Kontrak CSV kanonik untuk `--pairs` adalah:

| Kolom wajib | Isi |
| --- | --- |
| `id`, `text`, `label` | ID baris unik, teks masukan, serta label acuan biner 0 atau 1. Alias `teks` dan `label_acuan` diterima untuk `text` dan `label`; utamakan nama kanonik saat membuat berkas baru. |
| `pair_id`, `group_id` | ID pasangan dan kelompok klaim asal. Setiap pasangan berisi tepat dua versi dari kelompok yang sama. |
| `jenis_uji`, `varian` | `jenis_uji` adalah `gaya` atau `isi`; kedua versi diberi `v1` dan `v2`. |
| `rujukan`, `bukti_label` | Rujukan dan alasan label yang telah diperiksa, terpisah dari teks yang masuk model. |

Kolom protokol lain seperti `tanggal_klaim`, `topik`, `gaya`, `bagian_diubah`, dan jenis sumber direkomendasikan untuk penelusuran. `group_id` menyatukan salinan, parafrasa, dan varian dari peristiwa atau kelompok klaim yang sama. Verifikasi kedua teks dan label sebelum melihat skor. Simpan bantahan dan bukti terpisah dari teks masukan. Klaim yang belum dapat dipastikan dicatat terpisah dari pasangan berlabel biner.

| Kelompok | Desain | Pertanyaan yang dinilai |
| --- | --- | --- |
| **A · perubahan gaya** | Dua versi menyatakan klaim yang sama. Ubah gaya atau penanda awalan yang tidak menambah klaim baru. Kedua versi memakai label acuan yang sama. | Seberapa sering keputusan, suara seed, atau status berubah ketika isi klaim tetap? Berapa pasangan yang konsisten tetapi kedua hasilnya salah? |
| **B · perubahan isi** | Pertahankan gaya dan struktur sejauh mungkin. Ubah satu unsur seperti pelaku, angka, atau negasi, lalu verifikasi label benar/keliru untuk kedua sisi. | Seberapa sering skor kelas hoaks meningkat pada versi keliru dan model memberi keputusan yang sesuai pada kedua sisi? |

Tempatkan perubahan cukup awal pada teks singkat. Jika `bagian_diubah` diisi, gunakan penanda literal yang benar-benar terdapat pada versi itu; penanda kosong boleh dipakai jika tidak ada rentang tambahan pada sisi tersebut. Runner memeriksa keberadaan penanda setelah praproses dengan penyamaan kapitalisasi dan spasi. Pemeriksaan ini tidak menggantikan penilaian manusia bahwa isi pasangan gaya tetap sama atau bahwa perubahan isi memiliki label acuan yang sah.

Catat versi manifest, SHA-256, tanggal penguncian, arah yang diharapkan, aturan inklusi, dan seluruh pengecualian sebelum inferensi. Pasangan yang sudah dipakai untuk diagnosis dan semua varian satu `group_id` dikeluarkan dari pilot eksternal. [Protokol penelitian](PROTOKOL_PRAREGISTRASI.md#114-rencana-prospektif-pilot-klaim-dan-ocr)

[sample_pasangan_teks.csv](../data/sample_pasangan_teks.csv) berisi **empat baris fixture sintetis**, bukan sampel penelitian atau berita berlabel faktual. Pasangan `FIX_GAYA` memakai klaim cerita yang sama dan label 0 pada kedua versi; versi kedua menambahkan penanda `Viral!`. Pasangan `FIX_ISI` mengganti nama program rekaan `Tertib` menjadi `Viral`; ketetapan cerita buatan menyatakan hanya `Tertib` disetujui, sehingga label cerita kedua versi adalah 0 dan 1. `rujukan` dan `bukti_label` menjelaskan ketetapan internal fixture, bukan mengaku sebagai bukti dunia nyata. Kata `viral` sengaja memicu aturan stub. Hasil fixture hanya membuktikan jalur perbandingan berjalan, bukan bahwa IndoBERT peka terhadap gaya atau memahami isi.

### 4.3 Jalankan dan baca hasil pasangan

Jalankan dari root proyek dengan nama keluaran yang belum ada:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 evaluasi_set_luar.py data/sample_pasangan_teks.csv --pairs --stub --out reports/pasangan_teks_stub_01.csv
```

Ini bentuk konkret `python evaluasi_set_luar.py <csv> --pairs --stub --out <jalur baru>`. `--stub` memakai prediksi tiruan; jangan melaporkan hasilnya sebagai evaluasi checkpoint. Pilih nama baru pada setiap putaran. Kesalahan manifest ditolak sebelum inferensi dengan exit code 2. Galat eksekusi atau penulisan menghasilkan exit code 1; laporan lama tidak ditimpa. Inferensi nyata tanpa `--stub` merupakan putaran terpisah setelah fixture dan manifest penelitian diperiksa; belum dijalankan sebagai bagian uji fixture ini.

Runner memakai `explain=False` dan `debug=True`. Catat revisi kode, identitas checkpoint, pipeline, tokenizer, aturan voting aktif, perangkat, dan versi runtime yang tersedia. **Satu CSV** menyimpan hasil per versi teks dan metadata perbandingan pasangan yang diulang pada kedua baris pasangan; konsol menampilkan agregat kelompok uji secara terpisah. Kolom laporan mencakup `status`, `reason`, `label_model`, `seed_decisions_json`, `votes_hoax`, `teks_dinilai`, `terpotong`, `manifest_sha256`, serta `audit_model_json` jika metadata audit tersedia. `debug.prob_hoax_per_seed` dipetakan menjadi `prob_42`, `prob_123`, dan `prob_999` yang dibulatkan ke enam desimal; selisih yang dihitung darinya juga memakai skor debug yang dibulatkan. Selisih nol pada presisi ini bukan bukti tidak ada perubahan probabilitas. Ambil keputusan biner dari `seed_decisions` yang disimpan sebagai `seed_decisions_json` dan `pred_42/123/999` agar pembulatan dekat 0,5 tidak mengubah suara. [Keluaran predictor](../src/ml/inference.py)

- **Periksa perubahan yang diterima model.** Batas 60 kata dan 128 token bekerja pada tahap berbeda. `teks_dinilai` adalah hasil praproses sebelum batas tokenizer. Pasangan yang dapat dibandingkan memerlukan dua hasil valid `dinilai` atau `ambigu`, dua teks praproses tidak kosong dan berbeda, pemotongan keduanya `false`, serta penanda literal yang diisi tetap ditemukan. Jika syarat gagal, simpan alasan pasangan belum dapat dibandingkan. Pemeriksaan teks ini belum membuktikan token ID kedua versi berbeda; jika perlu memeriksa token lebih jauh, gunakan diagnostik dengan konfigurasi dan sinkronisasi tokenizer yang sama dengan inferensi.
- **Kelompok A.** `label_berbalik` berlaku ketika kedua sisi memberi keputusan biner. Laporkan jumlah keputusan yang berbalik dibagi jumlah pasangan dengan dua keputusan biner. Laporkan juga perubahan suara per seed, `transisi_ambigu`, dan pasangan konsisten yang salah. Tampilkan jumlah seluruh pasangan dan jumlah yang dapat dibandingkan.
- **Kelompok B.** `delta_prob_42`, `delta_prob_123`, dan `delta_prob_999` adalah skor debug `keliru − benar` ketika tersedia pada kedua sisi. `keduanya_benar` menunjukkan apakah kedua keputusan biner sesuai label acuan. Tampilkan cakupan perbandingan dan jumlah pasangan benar terhadap seluruh pasangan. Pergeseran skor dan keberhasilan keputusan mempunyai penyebut masing-masing.
- **Setiap putaran.** Pertahankan hasil ambigu, ditolak, di luar domain, gagal, dan masalah pemotongan. `transisi_status` tetap dicatat saat pasangan tidak dapat dibandingkan; `transisi_ambigu` hanya terisi untuk pasangan yang dapat dibandingkan. Nilai yang tidak tersedia dicatat sebagai kosong. Varian satu kelompok klaim tetap dihitung sebagai pasangan atau kelompok, sesuai metrik yang ditetapkan.

Gunakan Jupyter untuk menelaah hasil per pasangan dan menyiapkan tabel Bab 4. Notebook inferensi lokal masih membaca field lama `prediction`, `confidence_score`, dan `inference_time_seconds`. Selaraskan pembacaan field sebelum menjalankan seluruh notebook. [Notebook inferensi lokal](../notebooks/03_pengujian_inferensi_lokal.ipynb)

### 4.4 Lanjut ke pilot eksternal dan OCR

Setelah alur pasangan menghasilkan laporan lengkap, siapkan **40 klaim unik**. Gunakan 10 klaim per sel pada matriks benar/keliru × formal/media sosial. Catat label terverifikasi, sumber, tanggal, topik, dan bukti sebelum inferensi. Periksa salinan dekat terhadap data pengembangan yang diizinkan. Keluarkan dua klaim November yang sudah dilihat, kelompok diagnostik pasangan, serta varian masing-masing. Berkas `eval_benar.csv` dan `eval_kompas_cekfakta.csv` tetap menjadi set diagnostik historis dengan label asal sumber. Sajikan pilot secara deskriptif dengan cakupan, akurasi pada kasus yang diputuskan, benar terhadap seluruh masukan, salah tuduh hoaks, dan hoaks yang terlewat.

Pilih **delapan klaim dari 40 itu**, dua per sel, sebelum melihat keluaran model. Bandingkan transkripsi manual, bacaan OCR sebelum koreksi, dan teks hasil koreksi jika diuji. Laporkan CER/WER dengan jumlah sampel terukur, efek penolakan mutu, serta perubahan keputusan. Gambar dan parafrasa dari klaim yang sama tetap satu kelompok. [Adendum protokol](PROTOKOL_PRAREGISTRASI.md#114-rencana-prospektif-pilot-klaim-dan-ocr) · [Panduan OCR berpasangan](PANDUAN_PENGUJIAN_OCR.md)

### 4.5 Tentukan perbaikan dari pola kesalahan

Utamakan perbaikan yang sesuai dengan bukti. Perubahan hilang saat praproses atau pemotongan memerlukan pemeriksaan jalur input. Kesalahan yang muncul sesudah OCR memerlukan pemeriksaan pembacaan gambar. Kesalahan berulang pada klaim bersih mengarahkan pengumpulan data berlabel dari sumber, gaya, atau topik yang kurang tercakup. Bila perlu mengukur manfaat jumlah data, rancang learning curve dari subset train dengan validation tetap. Catat perubahan dan buat set evaluasi baru jika hasil pilot dipakai untuk menyesuaikan sistem.

**LOCKBOX mengikuti evaluasi final tersendiri.** Angka 236 adalah selisih dari agregat pembagian. Ikuti aturan evaluasi satu kali per seed setelah konfigurasi dan kriteria final dikunci. [Protokol evaluasi final](PROTOKOL_PRAREGISTRASI.md#keputusan-apriori-pelatihan-seleksi-model-dan-evaluasi-lockbox-colab-02)

## 5. Prioritas integritas dan optimasi

| Urutan | Sasaran | Bukti penerimaan |
| --- | --- | --- |
| 1. Ketatkan kontrak hasil | Validasi status, label, keputusan seed, dan angka sebelum menyimpan atau menampilkan hasil model. Hilangkan nilai bawaan yang menyamarkan payload rusak. | Status hilang atau tak dikenal, keluaran kosong, NaN/Inf, atau seed tidak lengkap menghasilkan kegagalan yang jelas. Nilai tidak tersedia tetap terlihat. |
| 2. Jaga asal data dan hak akses | Pisahkan keputusan awal, koreksi, dan tinjauan. Periksa pemilik dan role di backend. Abaikan respons yang kembali ke sesi atau masukan berbeda. | Uji akun silang, pergantian sesi, pengiriman ulang feedback, dan kegagalan simpan. Tinjauan tersimpan dapat dimuat ulang tanpa mengubah keputusan awal. |
| 3. Kaitkan penjelasan dengan hasil asal | Identifikasi model, pipeline, konfigurasi, serta teks yang dijelaskan. Simpan metadata minimum sesuai kebutuhan. Tandai riwayat yang kekurangan metadata. | Pergantian versi menghasilkan penanda pada penjelasan lama atau permintaan analisis ulang. Kegagalan LIME tetap terpisah dari hasil klasifikasi. |
| 4. Ukur beban sebelum optimasi | Pertahankan klasifikasi tanpa LIME sebagai jalur awal. Ukur waktu tunggu saat OCR, analisis, dan LIME berlangsung bersamaan. | Catat waktu pemuatan model, waktu respons per jalur, kebutuhan memori, tingkat gagal, dan konfigurasi. Bandingkan kandidat pada masukan yang sama, termasuk contoh dekat ambang. |
| 5. Pisahkan perbaikan sistem dan pelatihan | Perbaiki UI, API, atau OCR jika kesalahan berasal dari tahap itu. Pertimbangkan kandidat data dan pelatihan baru jika teks sudah tepat tetapi kesalahan model terus muncul pada kelompok tertentu. | Alasan, data, konfigurasi, dan kriteria perubahan ditetapkan sebelum evaluasi kandidat. Hasil baseline, penyimpangan, dan kegagalan tersimpan untuk perbandingan. |

Pada kode yang diperiksa, pemeriksaan pemilik, verifikasi hash, pemisahan LIME dari klasifikasi, dan penyimpanan feedback sudah tersedia. Identitas cache LIME klaim historis dan penyimpanan metadata reproduksi belum lengkap. Catat jenis galat, status, dan ID aman. Teks privat, token, kata sandi, serta string koneksi tetap dikecualikan dari log. [AGENTS.md](../AGENTS.md) · [Panduan Pengembangan AI](PANDUAN_PENGEMBANGAN_AI.md) · [Integritas cache](PANDUAN_INTEGRASI_LIME.md#6-cache-konkurensi-dan-penyimpanan-backend)

### Temuan pemeriksaan dan status tindak lanjut

| Pemeriksaan terisolasi | Perilaku yang ditemukan |
| --- | --- |
| Keluaran inferensi kosong pada rute klaim | Pada `d466df0`, fixture menerima status **dinilai**, label kosong, latensi 0,0, dan satu pemanggilan commit tiruan. Rute sekarang menolak keluaran kosong sebagai HTTP 500, lalu melakukan rollback tanpa membuat log. |
| Keputusan seed dan respons rusak | Sebelumnya validasi respons berjalan setelah commit. Rute sekarang memeriksa ketiga suara dan konsistensi keputusan sebelum menambah baris, serta memvalidasi respons sebelum commit. Kegagalan database membatalkan permintaan dan tidak mengonfirmasi penyimpanan. |
| Kesesuaian label dengan suara pada parser naskah | Parser menerima label **tidak berpola hoaks** pada 3/3 suara hoaks. Pemeriksaan konsistensi perlu mengikuti aturan voting yang tercatat pada hasil. |
| Kesesuaian setuju dengan label koreksi | Fixture feedback menerima setuju bernilai benar bersama label koreksi yang berlawanan. Keputusan model tetap terpisah. Definisi setuju dan klaim koreksi perlu disejajarkan di backend dan UI, termasuk saat hasil ambigu. |

Pemeriksaan ini menggunakan keluaran tiruan dan validasi kode, tanpa model atau database produksi. [Rute klaim](../src/api/routes/detection_routes.py) · [Parser naskah](../frontend/src/types/document-analysis.ts#L116) · [Rute feedback](../src/api/routes/feedback_routes.py#L47)
