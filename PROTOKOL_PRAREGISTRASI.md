## 10. Log Penyimpangan Protokol (Protocol Deviation Log)

### Deviasi 1: Kriteria C4 (Akurasi Pohon Keputusan Fitur Permukaan pada Dataset v2)
* **Tanggal Pencatatan**: 5 Oktober 2026
* **Status Pengujian**: Terdaftar pada evaluasi awal `01b_rebuild_dataset.ipynb` (Dataset v2).
* **Nilai Terukur**: Akurasi gabungan Decision Tree = 0,666 (Ambang batas target: ≤ 0,600).
* **Hasil Audit Forensik Empiris (`diagnostik_v2.ipynb`)**:
  1. Fitur jumlah kata murni (`n_kata`) memiliki akurasi 54,0% (mendekati distribusi acak koin 50:50) dan nilai uji Kolmogorov-Smirnov lulus mutlak di angka $KS = 0,030$ ($\le 0,10$). Hal ini membuktikan secara matematis bahwa bias jalan pintas panjang teks (length shortcut) telah 100% tereliminasi.
  2. Skor pohon gabungan 66,6% didorong secara dominan oleh disparitas gaya penulisan sintaksis antar-domain sumber observasional:
     - `n_kutip`: akurasi 65,1% (rata-rata 0,54 pada fakta vs 1,19 pada hoaks).
     - `pct_kapital`: akurasi 62,3% (rata-rata 9,4% pada fakta vs 14,6% pada hoaks).
     - `n_koma`: akurasi 61,9% (rata-rata 2,35 pada fakta berita formal vs 1,50 pada narasi media sosial).
* **Keputusan Metodologis**:
  - Deviasi diterima dan dipertahankan tanpa melakukan rekayasa/manipulasi tanda baca sintetis pada data.
  - Perbedaan ini dicatat secara transparan sebagai karakteristik intrinsik korpus terbuka (jurnalisme berita taat PUEBI vs narasi media sosial).
  - Ketahanan model terhadap tanda baca akan diuji secara independen pada tahap uji diagnostik kontrafaktual (`dev_test.csv`) dan evaluasi teks gambar PaddleOCR.

  ### Keputusan Strata Penyeimbangan (Pre-registered Decision Rule)
Pemilihan strata penyeimbangan Coarsened Exact Matching (CEM) ditentukan berdasarkan pohon keputusan apriori berikut:
1. **Preset B (sub_topic + len_bin + year_bin):** Dipilih jika menghasilkan ukuran data latih (train) ≥ 1.500 pasang seimbang, untuk mengontrol confound zaman secara simultan.
2. **Preset C (sub_topic + len_bin + year_bin dengan LEN_MATCH_TRUNC = True):** Dipilih jika Preset B menghasilkan < 1.500 pasang, dengan memotong panjang fakta mengikuti sebaran hoaks pada sub-topik yang sama.
3. **Preset A (sub_topic + len_bin):** Dipilih hanya jika Preset C tetap menghasilkan < 1.500 pasang, dan konsekuensi ketimpangan representasi tahun (confound zaman 2022) dicatat secara terbuka sebagai keterbatasan korpus observasional di Bab 5.

### Keputusan Desain Pra-Pembekuan: Normalisasi Deskriptor Judul & Tanda Kutip (UNWRAP)
* **Tanggal Pencatatan**: 10 Oktober 2026
* **Temuan Empiris**:
  - Prefiks deskriptif editorial Mafindo (`video`, `foto`, `gambar`, `tangkapan layar`, dsb.) ditemukan asimetris: 17,4% pada hoaks vs 0,3% pada fakta.
  - Tanda kutip pembungkus judul (`“...”`) ditemukan asimetris ekstrem: 17,8% pada hoaks (47,1% pada hoax_archive) vs 0,5% pada fakta (selisih 17,4 poin persentase).
* **Aturan Apriori**: Karena selisih proporsi tanda kutip > 10 poin, parameter `UNWRAP = True` dan pembersihan bertingkat `DESC` diaktifkan secara simetris untuk seluruh kelas.
* **Dasar Justifikasi**: Teks masukan nyata dari PaddleOCR (poster/meme/tangkapan layar) di dunia nyata memuat isi klaim murni, bukan deskripsi metadata editor pemeriksa fakta.
* **Prosedur**: Dijalankan tepat satu kali di folder trial, lalu hasilnya langsung dibekukan.

### Keputusan Apriori Pelatihan, Seleksi Model, dan Evaluasi Lockbox (Colab 02)
* **Tanggal Pencatatan**: 13 Oktober 2026 (Ditetapkan sebelum run training penuh dilakukan)
* **Lingkungan Komputasi Terverifikasi**:
  - Akselerator: NVIDIA Tesla T4 GPU (Device: `cuda`)
  - Framework: PyTorch `2.11.0+cu130`, Transformers `5.18.0`, CUDA Build `13.0`
  - Pipeline Teks: `text_pipeline.py` versi `tp-1.6` (terverifikasi hash sha256)
* **Aturan Pemilihan Konfigurasi (Model Selection Rule)**:
  1. Pemilihan konfigurasi (`ce` vs `focal`) dilakukan murni berdasarkan rerata Macro-F1 pada set validasi (`val.csv`) lintas 3 seed (`42`, `123`, `999`).
  2. **Aturan Parsimoni (Prinsip Sederhana)**: Jika selisih rerata Macro-F1 val antara `ce` dan `focal` $< 0,01$ ($< 1$ poin persentase), maka Cross-Entropy (`ce`) secara apriori ditetapkan sebagai konfigurasi terpilih.
  3. Subset `dev_test.csv` (uji kontrafaktual) hanya dilaporkan untuk diagnosis ketahanan, dan **dilarang digunakan** dalam pemilihan konfigurasi model.
* **Kriteria Signifikansi Statistik (McNemar Test)**:
  - Perbandingan performa berpasangan antara IndoBERT dan baseline TF-IDF + Logistic Regression dievaluasi menggunakan Exact Binomial McNemar Test.
  - Perbedaan performa hanya dianggap bermakna secara praktis dan statistik jika:
    1. Nilai signifikansi $p < 0,05$, **DAN**
    2. Selisih performa $> 4$ poin persentase pada set uji ($n \approx 236$). Selisih di bawah ambang ini dicatat sebagai variasi kebetulan acak pada sampel terbatas.
* **Protokol Evaluasi Kumpulan Terkunci (Lockbox Evaluation Rule)**:
  1. **Evaluasi Tunggal per Seed**: Evaluasi lockbox hanya dijalankan tepat **satu kali per seed** terhadap 3 model checkpoint dari konfigurasi terpilih (`ckpt_{terpilih}_{seed}.pt`).
  2. **Pelaporan Metrik**: Hasil lockbox dilaporkan sebagai **rerata $\pm$ standar deviasi (mean $\pm$ std)** lintas 3 seed.
  3. **Larangan Cherry-Picking & Ensemble**: Dilarang keras memilih satu seed terbaik setelah melihat hasil (*no post-hoc cherry-picking*) dan dilarang menggabungkan model (*no ensembling*).
  4. **Eksekusi Lokal Terisolasi**: Evaluasi dijalankan di lingkungan laptop lokal menggunakan fungsi pembantu `load_ckpt()`, tanpa pernah mengunggah data lockbox ke lingkungan cloud (Google Colab).
  5. **Verifikasi Integritas Bobot**: Seluruh checkpoint wajib diverifikasi menggunakan pencocokan nilai SHA-256 hash (hasil output sel Colab dicocokkan dengan `Get-FileHash` di laptop) sebelum evaluasi lockbox dimulai guna menjamin keaslian bobot model.