# Deteksi Pola Hoaks Politik dan Integritas VERIDIX

**19 November 2026 · Acuan kode d466df0.** Dokumen ini menjelaskan sistem yang berjalan, bukti evaluasi yang tersedia, dan urutan kerja yang diusulkan. Evaluasi final mengikuti [protokol penelitian](../PROTOKOL_PRAREGISTRASI.md).

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

[Audit dataset dan model](../reports/AUDIT_MODEL_2026-10-24.md) · [Laporan paritas](../reports/audit_model_2026-10-24_parity.json) · [Log pelatihan](../log_training.json) · [Protokol](../PROTOKOL_PRAREGISTRASI.md)

Pada data pengembangan yang diaudit, setiap sumber menyumbang satu kelas. Keterkaitan ini memungkinkan model memakai ciri gaya penerbit untuk menebak label. C4 pada dataset beku tercatat **72,46%**, melampaui batas **60%**. Protokol masih mencatat **66,6%** dari tahap sebelumnya. Perbedaan perlu dicatat dengan tanggal sebenarnya sambil mempertahankan riwayat hasil. Tiga seed memberi informasi tentang variasi antar-run pada rancangan ini. Generalisasi tetap perlu diukur. [Hasil kriteria](../data/processed_v2/hasil_kriteria.csv) · [Audit keterbatasan](../reports/AUDIT_MODEL_2026-10-24.md)

## 4. Rancangan uji berita baru dan OCR

1. **Tetapkan unit uji berupa klaim.** Catat ID, kelompok klaim, tanggal, rujukan, gaya bahasa, topik, dan label acuan beserta bukti. Tetapkan label sebelum melihat hasil model. Pisahkan kasus yang bukti faktualnya belum memadai.
2. **Silangkan label acuan dengan gaya bahasa.** Uji klaim benar dan keliru dalam gaya berita formal serta gaya media sosial. Isi setiap kelompok dengan beragam sumber. Angka 40–50 contoh dapat digunakan sebagai pilot. Laporkan jumlah klaim unik dan jumlah variasi teks atau gambar secara terpisah.
3. **Periksa duplikasi dan petunjuk label.** Masukkan klaim yang akan diuji. Simpan judul “HOAKS”, bantahan, serta rujukan verifikasi secara terpisah. Periksa duplikat dekat dan klaim yang sama dalam data pengembangan yang diizinkan. Kelompokkan salinan, parafrasa, dan varian gambar bersama. Berkas **eval_benar.csv** dan **eval_kompas_cekfakta.csv** merupakan set diagnostik historis yang hasilnya tercatat dalam log pelatihan. Pisahkan label asal korpus dari label acuan yang diverifikasi pada tingkat klaim. Judul atau kategori penerbit belum menetapkan kebenaran klaim yang dikutip.
4. **Pisahkan efek OCR dari hasil klasifikasi.** Buat transkripsi manual sebagai acuan. Bandingkan hasil klasifikasi transkripsi dengan hasil dari OCR sebelum koreksi. Jika koreksi pengguna ikut diuji, laporkan sebagai tahap ketiga. Catat CER, WER, penolakan, dan perubahan keputusan. Pisahkan gambar nyata, gambar sintetis, serta simulasi derau teks.
5. **Pertahankan penyebut lengkap.** Laporkan klaim benar, salah, ambigu, ditolak, di luar domain, dan gagal. Tampilkan cakupan kasus dengan keputusan, akurasi pada kasus yang diputuskan, dan jumlah benar terhadap seluruh sampel. Tampilkan kesalahan menandai klaim benar sebagai hoaks dan hoaks yang terlewat. Laporkan per seed dan konsensus pada set aplikasi yang sama.
6. **Simpan keluaran aktual.** Catat versi, hash artefak, konfigurasi, perangkat, status, dan keputusan tiap seed yang tersedia. Simpan suara biner asli secara terpisah dari skor debug yang dibulatkan. Gunakan keluaran baru setiap putaran. Apabila hasil suatu set dipakai untuk mengubah sistem, perlakukan set itu sebagai data diagnostik dan tetapkan set baru untuk evaluasi independen berikutnya.

Gunakan [evaluasi_set_luar.py](../evaluasi_set_luar.py) sebagai dasar untuk klaim singkat. Jalankan dengan CSV uji terpisah dan berkas keluaran baru. Periksa bahwa kegagalan mesin dilaporkan eksplisit sebelum memakai skrip untuk laporan. [Notebook inferensi lokal](../notebooks/03_pengujian_inferensi_lokal.ipynb) bisa menjadi tempat menelaah kasus dengan kontrak respons terkini. [Panduan OCR berpasangan](PANDUAN_PENGUJIAN_OCR.md)

## 5. Prioritas integritas dan optimasi

| Urutan | Sasaran | Bukti penerimaan |
| --- | --- | --- |
| 1. Ketatkan kontrak hasil | Validasi status, label, keputusan seed, dan angka sebelum menyimpan atau menampilkan hasil model. Hilangkan nilai bawaan yang menyamarkan payload rusak. | Status hilang atau tak dikenal, keluaran kosong, NaN/Inf, atau seed tidak lengkap menghasilkan kegagalan yang jelas. Nilai tidak tersedia tetap terlihat. |
| 2. Jaga asal data dan hak akses | Pisahkan keputusan awal, koreksi, dan tinjauan. Periksa pemilik dan role di backend. Abaikan respons yang kembali ke sesi atau masukan berbeda. | Uji akun silang, pergantian sesi, pengiriman ulang feedback, dan kegagalan simpan. Tinjauan tersimpan dapat dimuat ulang tanpa mengubah keputusan awal. |
| 3. Kaitkan penjelasan dengan hasil asal | Identifikasi model, pipeline, konfigurasi, serta teks yang dijelaskan. Simpan metadata minimum sesuai kebutuhan. Tandai riwayat yang kekurangan metadata. | Pergantian versi menghasilkan penanda pada penjelasan lama atau permintaan analisis ulang. Kegagalan LIME tetap terpisah dari hasil klasifikasi. |
| 4. Ukur beban sebelum optimasi | Pertahankan klasifikasi tanpa LIME sebagai jalur awal. Ukur waktu tunggu saat OCR, analisis, dan LIME berlangsung bersamaan. | Catat waktu pemuatan model, waktu respons per jalur, kebutuhan memori, tingkat gagal, dan konfigurasi. Bandingkan kandidat pada masukan yang sama, termasuk contoh dekat ambang. |
| 5. Pisahkan perbaikan sistem dan pelatihan | Perbaiki UI, API, atau OCR jika kesalahan berasal dari tahap itu. Pertimbangkan kandidat data dan pelatihan baru jika teks sudah tepat tetapi kesalahan model terus muncul pada kelompok tertentu. | Alasan, data, konfigurasi, dan kriteria perubahan ditetapkan sebelum evaluasi kandidat. Hasil baseline, penyimpangan, dan kegagalan tersimpan untuk perbandingan. |

Pada kode yang diperiksa, pemeriksaan pemilik, verifikasi hash, pemisahan LIME dari klasifikasi, dan penyimpanan feedback sudah tersedia. Identitas cache LIME klaim historis dan penyimpanan metadata reproduksi belum lengkap. Catat jenis galat, status, dan ID aman. Teks privat, token, kata sandi, serta string koneksi tetap dikecualikan dari log. [AGENTS.md](../AGENTS.md) · [Panduan Pengembangan AI](PANDUAN_PENGEMBANGAN_AI.md) · [Integritas cache](PANDUAN_INTEGRASI_LIME.md#6-cache-konkurensi-dan-penyimpanan-backend)

### Temuan pemeriksaan terhadap kode acuan

| Pemeriksaan terisolasi | Perilaku yang ditemukan |
| --- | --- |
| Keluaran inferensi kosong pada rute klaim | Fixture menerima hasil sukses dengan status **dinilai**, label kosong, latensi 0,0, dan satu pemanggilan commit tiruan. Status yang hilang dipetakan menjadi nilai bawaan. |
| Keputusan seed dengan nilai di luar 0 atau 1 | Validasi respons menolak hasil setelah rute memanggil commit tiruan. Validasi kontrak model perlu dilakukan sebelum persistensi. |
| Kesesuaian label dengan suara pada parser naskah | Parser menerima label **tidak berpola hoaks** pada 3/3 suara hoaks. Pemeriksaan konsistensi perlu mengikuti aturan voting yang tercatat pada hasil. |
| Kesesuaian setuju dengan label koreksi | Fixture feedback menerima setuju bernilai benar bersama label koreksi yang berlawanan. Keputusan model tetap terpisah. Definisi setuju dan klaim koreksi perlu disejajarkan di backend dan UI, termasuk saat hasil ambigu. |

Pemeriksaan menggunakan keluaran tiruan dan validasi kode, tanpa model atau database produksi. Temuan menunjukkan kondisi ketika integritas hasil atau feedback dapat terganggu. [Rute klaim](../src/api/routes/detection_routes.py#L336) · [Parser naskah](../frontend/src/types/document-analysis.ts#L116) · [Rute feedback](../src/api/routes/feedback_routes.py#L47)
