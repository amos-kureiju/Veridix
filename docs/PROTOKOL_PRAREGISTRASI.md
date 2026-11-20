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
## 11. Adendum 19 November 2026: Koreksi Bukti dan Rencana Pilot Eksternal

**Kedudukan:** bagian ini ditulis setelah pelatihan dan audit terdahulu. Catatan historis di atas dipertahankan; koreksi berikut tidak diklaim sebagai keputusan yang dibuat sebelum eksperimen. Rencana pilot di bagian 11.4 belum merupakan hasil pengujian. Penambahan adendum ini tidak menjalankan pelatihan, evaluasi model, atau evaluasi LOCKBOX.

### 11.1 Build dataset yang diperiksa

Acuan adalah `data/processed_v2`, bukan folder trial/salinan/arsip. Pada pemeriksaan 19 November 2026, jumlah baris dan label tiga split berikut dihitung ulang tanpa menampilkan naskah. SHA-256 masing-masing berkas cocok dengan `MANIFEST_sha256.csv` dan `data_hash` pada `log_training.json`.

| Split | Baris | Label 0 | Label 1 | Peran |
| --- | ---: | ---: | ---: | --- |
| Train | 1.660 | 830 | 830 | Pelatihan bobot. |
| Validation | 236 | 118 | 118 | Seleksi epoch dan CE/focal sesuai aturan terdahulu. |
| Dev-test | 236 | 118 | 118 | Diagnostik; tidak dipakai memilih konfigurasi model. |
| Total yang dibaca | 2.132 | 1.066 | 1.066 | Tidak mencakup isi LOCKBOX. |

[Konfigurasi build](data/processed_v2/config.json) mencatat `B_tahun`, strata `sub_topic + len_bin + year_bin`, `len_match_trunc=false`, pipeline `tp-1.6`, waktu pembentukan `2026-10-11T13:58:14`, dan `all_criteria_passed=false`. [Agregat tahap CEM](data/processed_v2/audit_log_per_langkah.csv) berjumlah 2.368 baris sebelum pembagian split. Selisih 236 terhadap total pengembangan merupakan inferensi aritmetika dari metadata pembentukan, bukan penghitungan atau verifikasi berkas LOCKBOX. Angka 2.456/1.722/245/245/244 yang pernah disebut dalam bahan lain tidak digunakan sebagai ukuran build ini.

Satuan aturan strata terdahulu perlu dikoreksi: [`match_n`](01b_rebuild_dataset_final.py) menghitung baris kedua label, dan pemilihan preset membandingkan perkiraan 70% jumlah baris dengan `MIN_TRAIN_OK=1500`. Itu bukan ambang 1.500 pasangan label. Train final berisi 1.660 baris, setara 830 pasangan seimbang. Catatan ini menjelaskan perbedaan kode dengan istilah lama, bukan mengubah aturan lama secara retroaktif atau membuktikan ukuran sampel optimal.

### 11.2 Koreksi C4 dan batas klaim kualitas

| Bukti build beku | Nilai | Interpretasi |
| --- | ---: | --- |
| C2, KS jumlah kata | 0,0478424 | Memenuhi batas 0,10 untuk pemeriksaan ini. |
| C4, akurasi pohon fitur permukaan pada dev-test | 0,7245763 | **Gagal** terhadap batas 0,60; bukan akurasi IndoBERT. |
| Status keseluruhan kriteria pada konfigurasi | `false` | Tidak seluruh kriteria lulus. |

Sumber nilai adalah [hasil_kriteria.csv](data/processed_v2/hasil_kriteria.csv). [Audit 24 Oktober](reports/AUDIT_MODEL_2026-10-24.md) juga mereproduksi C4 sebesar 72,46%. Nilai historis 66,6% di bagian 10 tetap menjadi catatan tahap sebelumnya. Klaim lama bahwa bias panjang telah “100% tereliminasi” tidak digunakan sebagai kesimpulan build final: kelulusan satu pemeriksaan tidak membuktikan ketiadaan seluruh jalan pintas.

Penghitungan ulang train+validation+dev-test menemukan sumber-label terpisah: CNN 339, Kompas 557, dan Tempo 170 baris seluruhnya berlabel 0; Hoax Archive 250 dan TurnBackHoax 816 baris seluruhnya berlabel 1. Label sumber dan ciri bahasa penerbit dapat merancukan hasil walaupun kolom `source` tidak dimasukkan sebagai fitur model. Label 0 juga tidak menggantikan verifikasi fakta independen setiap klaim. Karena itu, istilah “steril”, “bebas seluruh shortcut”, atau “ukuran train terbukti optimal” tidak didukung oleh bukti ini.

### 11.3 Model, paritas historis, dan status LOCKBOX

[Log pelatihan](log_training.json) memilih Cross-Entropy untuk seed 42/123/999. Tiga seed mengukur variasi run pada rancangan ini; jumlah tersebut bukan jaminan generalisasi. Baseline dan artefaknya dipertahankan untuk evaluasi. Pelatihan baru, jika diperlukan oleh temuan yang sah, memerlukan versi data/model, alasan, dan rancangan evaluasi terpisah; perbaikan UI/API/OCR bukan alasan otomatis melatih ulang.

[Laporan paritas 24 Oktober](reports/audit_model_2026-10-24_parity.json) mencatat 236 validation + 236 dev-test, masing-masing dinilai tiga seed: **472 teks unik dan 0 perbedaan dari 1.416 keputusan kelas** terhadap prediksi Colab. Pemeriksaan memakai CPU, batch 4 dan dua thread setelah percobaan batch 32 terhenti pada tekanan memori. Ini bukti historis pada kolom teks beku, bukan probabilitas bit-identik, evaluasi API/OCR/LIME, atau paritas mode naskah yang ditambahkan kemudian. Tidak ada pengulangan inferensi pada saat menulis adendum ini.

Untuk klaim singkat, kebijakan aplikasi bawaan adalah ambang kelas hoaks `>=0.5` per seed dan voting `unanimous`; nilai lingkungan yang aktif tetap dicatat. Abstain akibat ketidaksepakatan seed berbeda dari zona probabilitas yang dikalibrasi di validation. Evaluasi voting aplikasi dipisahkan dari aturan final terdahulu yang melaporkan per seed dan melarang ensemble.

Isi maupun arsip LOCKBOX tidak dibaca, dihitung, dihash, atau dijalankan untuk adendum ini. Audit 24 Oktober mencatat akses byte untuk pemeriksaan hash; itu berbeda dari membaca klaim untuk tuning atau evaluasi. Bukti yang diperiksa belum memuat laporan evaluasi final LOCKBOX, tetapi tidak menyediakan riwayat lengkap seluruh akses. Karena itu, statusnya **belum terkonfirmasi**, bukan sertifikasi “belum pernah dibuka”. Tidak ada izin membuka atau mengulang evaluasi final yang timbul dari adendum ini. Jika catatan evaluasi final sebelumnya ditemukan, dokumentasikan waktu, konfigurasi, dan pemakaiannya; jangan memperlakukan hasil yang sudah dilihat sebagai holdout baru.

### 11.4 Rencana prospektif pilot klaim dan OCR

Rencana ini berlaku untuk sampel eksternal yang belum dinilai pada putaran pilot ini. Tujuannya menemukan keterbatasan transfer dan memisahkan kesalahan klasifikasi dari OCR atau integrasi. Ini bukan evaluasi final LOCKBOX dan bukan jaminan kesiapan produksi.

**Prasyarat sebelum inferensi:**

1. Tetapkan manifest dengan ID unik, `group_id` klaim, tanggal, rujukan, topik, gaya, teks yang diuji, label acuan, dan bukti label. Label ditentukan sebelum melihat keluaran model. Pisahkan label asal sumber dari label acuan; kasus tanpa bukti memadai dicatat terpisah, bukan dipaksa menjadi kelas 0/1.
2. Periksa duplikat, salinan dekat, serta klaim sama terhadap data pengembangan yang diizinkan. Semua parafrasa, gambar, dan variasi klaim yang sama tetap satu kelompok. Jangan membuka LOCKBOX untuk pemeriksaan ini; independensi terhadap isi LOCKBOX tidak diklaim telah diperiksa.
3. Pisahkan bahan penyusunan/koreksi evaluator atau kalibrasi dari sampel pilot. Jika hasil pilot kemudian dipakai mengubah sistem, set itu menjadi diagnostik; evaluasi independen berikutnya menggunakan sampel baru yang ditetapkan sebelum hasilnya dilihat.
4. Catat revisi kode, identitas checkpoint dan pipeline, tokenizer, voting, konfigurasi OCR/LIME, perangkat, serta versi dependensi. Pemeriksaan integritas tidak boleh dilewati dengan mengganti hash atau mengaktifkan `VERIDIX_ALLOW_UNVERIFIED`.
5. Verifikasi evaluator dengan fixture terisolasi: status gagal/ditolak/di luar domain/ambigu harus berbeda, keluaran rusak tidak menjadi label 0, dan semua kasus tetap tercatat jika satu kasus gagal. Gunakan keluaran baru yang berbeda dari masukan dan laporan terdahulu. Notebook hanya menelaah keluaran atau memanggil kontrak aktif; jangan menjalankan ulang notebook training/build sebagai persiapan.

**Target pilot yang direncanakan:** 40 klaim unik, dengan matriks berikut. Angka ini adalah target eksploratif, bukan ukuran yang terbukti cukup untuk kesimpulan umum. Jika belum terkumpul, laporkan jumlah aktual dan sel kosong; jangan mengisi kekurangan dengan data contoh yang dianggap nyata.

| Label acuan klaim | Gaya formal | Gaya informal/media sosial | Total klaim unik |
| --- | ---: | ---: | ---: |
| Benar menurut bukti acuan | 10 | 10 | 20 |
| Keliru menurut bukti acuan | 10 | 10 | 20 |
| Total target | 20 | 20 | 40 |

Usahakan sumber tidak menentukan label. Nilai kebenaran melekat pada klaim yang diuji, bukan pada nama penerbit atau seluruh artikel yang mengutipnya. Simpan judul vonis “HOAKS”, bantahan, dan rujukan verifikasi terpisah dari teks klaim. Parafrasa atau rendering buatan diberi penanda sintetis; tidak dihitung sebagai berita nyata baru atau klaim unik tambahan. Rancangan seimbang ini tidak memperkirakan prevalensi hoaks di penggunaan sebenarnya.

`eval_benar.csv` dan `eval_kompas_cekfakta.csv` tetap set diagnostik historis: kolom labelnya mempertahankan label sumber 1 dan 0, dan hasilnya sudah diamati dalam log training. Keduanya bukan pengganti otomatis untuk sel matriks atau evaluasi eksternal yang belum pernah diamati. Rujuk [audit label diagnostik](reports/AUDIT_MODEL_2026-10-24.md).

**Pilot OCR yang direncanakan:** pilih delapan klaim dari matriks, dua per sel, sebelum melihat hasil. Gunakan gambar/screenshot nyata yang diizinkan bila tersedia; pisahkan gambar sintetis dan varian degradasi. Tetapkan transkripsi manual dengan membaca gambar sebelum OCR, lalu periksa ulang acuannya. Bandingkan tiga masukan: transkripsi manual, bacaan OCR sebelum koreksi, dan edit pengguna jika diuji. Gambar tersebut merupakan representasi klaim yang sama, sehingga tidak menambah 40 klaim unik menjadi 48. Jumlah gambar aktual, sumber, kualitas, pasangan terukur, dan penolakannya dilaporkan apa adanya.

**Luaran dan penyebut:**

- Simpan status, alasan, label, suara dan keputusan biner asli per seed, skor yang tersedia beserta presisinya, teks/rentang yang benar-benar masuk model, pemotongan atau ketidakpastiannya, konfigurasi, dan waktu tiap tahap. Jangan merekonstruksi keputusan seed dari label akhir atau skor yang sudah dibulatkan.
- Laporkan seluruh masukan, yang diputuskan, ambigu, ditolak, di luar domain, dan gagal. Pisahkan cakupan, akurasi pada yang diputuskan, benar/seluruh masukan, recall hoaks, dan spesifisitas klaim benar. Laporkan per seed serta voting aplikasi; jangan menggabungkan ketiganya sebagai observasi independen.
- Gunakan interval Wilson 95% (`z=1.96`) untuk proporsi binomial yang sesuai beserta `k/n`; tidak untuk Macro-F1 atau menganggap varian klaim berkorelasi sebagai sampel independen. Sebagai **ilustrasi perencanaan, bukan hasil pilot**, 10/10 benar memberi interval 72,25–100%, dan 40/40 memberi 91,24–100%. Pilot sempurna sekalipun tidak membuktikan akurasi populasi 100%.
- OCR melaporkan CER/WER beserta pembagi karakter/kata, hasil pasangan yang terukur, penolakan mutu, galat mesin, dan perubahan keputusan terhadap transkripsi. Dua hasil ambigu yang sama bukan bukti ketepatan atau ketahanan semantik. Ikuti [Panduan OCR](docs/PANDUAN_PENGUJIAN_OCR.md).
- Mode naskah panjang diuji terpisah: posisi klaim, batas segmen, kutipan, negasi, dan bantahan memerlukan acuan per klaim/rentang. Jangan menyalin label satu artikel ke seluruh segmen. Ikuti [Panduan Teks Panjang](docs/PANDUAN_TEKS_PANJANG_DAN_MULTI_GAMBAR.md).

Pilot selesai secara pencatatan apabila asal data dan label dapat ditelusuri, semua masukan memiliki hasil atau alasan kegagalan, penyebut lengkap, serta keluaran dan keterbatasan tersimpan. Penyelesaian ini tidak mensyaratkan semua prediksi benar dan tidak menjadi klaim lolos produksi. Kriteria mutu untuk keputusan pemakaian berikutnya ditetapkan sebelum evaluasi kandidat, bukan dipilih setelah melihat angka yang menguntungkan.

Optimasi dibandingkan satu kandidat pada satu waktu dengan masukan berpasangan, pengulangan, perangkat, serta konfigurasi yang dicatat. Pisahkan waktu pemuatan, antrean, inferensi, OCR, LIME, memori, dan kegagalan. Tetapkan cakupan/toleransi paritas sebelum perbandingan dan pertahankan hasil buruk atau parsial. Pemilihan kandidat memakai bahan pengembangan/kalibrasi yang sesuai, tidak memakai LOCKBOX. Perubahan jumlah seed, praproses, tokenisasi, voting, atau sampel LIME bukan optimasi UI yang boleh dilakukan diam-diam.
