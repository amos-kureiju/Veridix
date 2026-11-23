# Audit dataset, pelatihan, dan pengujian model — 24 Oktober 2026

Model menunjukkan performa internal yang tinggi, tetapi bukti saat ini belum cukup untuk menyatakan sistem andal pada klaim politik baru atau gambar nyata. Masalah utama adalah perancuan sumber dengan label, kegagalan kriteria fitur permukaan, ketahanan terhadap perubahan distribusi, dan perbedaan antara protokol evaluasi dengan jalur aplikasi.

Audit ini tidak mengubah data beku, bobot, kode aplikasi, atau protokol. Isi lockbox tidak dibaca atau diprediksi. `verifikasi_manifest.py` hanya memeriksa hash berkas lockbox, sesuai fungsi pemeriksaan integritasnya. Perubahan yang sudah ada pada `frontend/src/app/auth/layout.tsx` tidak disentuh.

## Hasil yang diperiksa ulang

| Pemeriksaan | Hasil |
|---|---|
| Data train | 1.660 teks; 830 fakta dan 830 hoaks |
| Data val | 236 teks; 118 fakta dan 118 hoaks |
| Data dev_test | 236 teks; 118 fakta dan 118 hoaks |
| Rentang panjang `text` | 10–60 kata pada keseluruhan data pengembangan |
| Teks kosong, label kosong, ID duplikat | Tidak ditemukan pada tiga split tersebut |
| Grup, teks identik, judul ternormalisasi lintas split | Tidak ditemukan |
| Hash manifest | Pemeriksaan resmi: 0 ketidakcocokan; pemeriksaan tambahan 17 artefak pengembangan/raw juga cocok |
| Hash data dalam log pelatihan | Keenam berkas cocok dengan berkas lokal |
| Prediksi tersimpan vs log | Akurasi dan Macro-F1 semua 6 run × 2 split cocok; label, ID, dan probabilitas juga konsisten |
| Inferensi bobot asli lokal vs prediksi Colab | **1.416/1.416 identik**: 236 val + 236 dev_test × 3 seed CE; hash ketiga checkpoint, pipeline, dan revisi model dasar lolos |
| KS distribusi jumlah kata | 0,04784; memenuhi kriteria ≤0,10, tanpa membuktikan semua bias panjang hilang |
| Pemilihan CE vs focal | CE dipilih sesuai aturan rerata Macro-F1 validasi dan toleransi 1 poin persentase |
| Uji batas saat audit | 17/17 lulus dengan backend tiruan; ini menguji alur, bukan akurasi model |

Ada empat `body` kosong (tiga train, satu dev_test), tetapi `text` tetap terisi. Ini bukan empat input kosong untuk model.

Pelatihan resmi berada di [notebook Colab 02](../notebooks/colab_02_indobert_RUN_PENUH.ipynb), bukan `src/ml/train_model.py` yang masih kosong. Notebook memakai model pralatih, membekukan embedding dan delapan layer awal, lalu melatih empat layer akhir dan kepala klasifikasi. Pemilihan epoch terbaik dilakukan dari validasi; konfigurasi dibandingkan pada tiga seed. Penurunan loss dan hasil prediksi konsisten dengan log, tetapi audit ini tidak mengulang pelatihan GPU dari awal.

| Konfigurasi | Macro-F1 val, mean ± sample SD | Macro-F1 dev_test, mean ± sample SD |
|---|---:|---:|
| Cross-Entropy | 97,03% ± 0,42 poin | 95,20% ± 0,65 poin |
| Focal Loss | 96,89% ± 0,25 poin | 95,06% ± 1,29 poin |

Baseline TF-IDF + Logistic Regression dihitung ulang: akurasi val 94,07%, dev_test 91,53%. Pada dev_test, selisih akurasi CE terhadap baseline adalah 2,97; 4,24; dan 3,81 poin untuk seed 42, 123, 999, dengan p McNemar 0,1435; 0,0129; 0,0352. Hanya seed 123 memenuhi kedua syarat protokol sekaligus (p<0,05 dan selisih>4 poin); ini bukan alasan memilih seed 123 sesudah melihat hasil. Keunggulan belum konsisten pada seluruh seed menurut kriteria yang ditetapkan sendiri.

## Temuan prioritas tinggi

### 1. Kriteria bias permukaan gagal pada dataset final

[hasil_kriteria.csv](../data/processed_v2/hasil_kriteria.csv:7) mencatat akurasi pohon keputusan **72,46%**, melebihi batas 60%. Nilai ini berhasil direproduksi hanya menggunakan jumlah kata, karakter, tanda akhir kalimat, dan koma. Tanda baca kalimat saja mencapai 67,80% pada diagnostik satu fitur.

[config.json](../data/processed_v2/config.json:44) memang menyatakan `all_criteria_passed=false`. Akan tetapi [protokol](../docs/PROTOKOL_PRAREGISTRASI.md:6) masih menjelaskan deviasi **66,6%** dari versi sebelumnya. Nilai dan penjelasan deviasi belum diselaraskan dengan build beku yang sebenarnya. Kelulusan KS atau skor jumlah kata mendekati acak tidak membuktikan seluruh jalan pintas berbasis panjang dan format telah hilang.

### 2. Sumber dan label masih terpisah sempurna

[Pembentukan label](../01b_rebuild_dataset_final.py:49) menghasilkan pola berikut pada train+val+dev_test:

| Sumber | Fakta | Hoaks |
|---|---:|---:|
| CNN Indonesia | 339 | 0 |
| Kompas | 557 | 0 |
| Tempo | 170 | 0 |
| Hoax Archive | 0 | 250 |
| TurnBackHoax | 0 | 816 |

Kolom `source` tidak dimasukkan langsung sebagai fitur IndoBERT. Namun, gaya penulisan dan karakteristik sumber dapat berkorelasi dengan label. Pembagian berdasarkan grup mengurangi kebocoran artikel serupa, tetapi tidak menghilangkan perancuan tersebut.

Diagnostik tambahan **baseline**, dilatih ulang tanpa satu sumber dan diuji hanya pada baris dev_test sumber itu, memperlihatkan sensitivitas besar:

| Sumber dev_test | n | Baseline biasa | Baseline tanpa sumber itu di train |
|---|---:|---:|---:|
| CNN Indonesia | 33 | 96,97% | 66,67% |
| Kompas | 64 | 98,44% | 32,81% |
| Tempo | 21 | 90,48% | 76,19% |
| Hoax Archive | 23 | 86,96% | 78,26% |
| TurnBackHoax | 95 | 86,32% | 4,21% |

Ini diagnostik eksploratif dengan ukuran dan distribusi train yang berubah, bukan skor generalisasi final IndoBERT. Hasilnya memperkuat kebutuhan evaluasi dengan sumber dan gaya yang tidak menentukan label.

### 3. Hasil luar distribusi dan simulasi OCR menunjukkan keterbatasan nyata

[Log pelatihan](../log_training.json) mencatat **89,04% rata-rata** judul bertag BENAR diprediksi hoaks oleh CE (per seed: 90,05%; 89,81%; 87,27%). Ini tanda masalah transfer ke bentuk teks lain. Pengujian tersebut memakai judul saja, berbeda dari judul+isi saat training, dan tidak menjalankan gerbang aplikasi. Dari 432 judul itu, hanya 102 yang lolos validasi input dan domain aplikasi pada audit ini. Jadi 89,04% bukan estimasi false-positive sistem produksi; penyebabnya juga belum bisa diatribusikan hanya kepada sumber.

Set Kompas berukuran 20 memberi proporsi prediksi hoaks 85%, 95%, 85%. Hanya dua judul lolos kedua gerbang aplikasi. Set itu terlalu kecil dan berbeda jalur untuk menjadi bukti umum kesiapan aplikasi. Tidak ditemukan judul kanonis yang identik dengan data pengembangan pada kedua set diagnostik tersebut.

**Perhatian label:** `eval_benar.csv` masih menyimpan label sumber `1`, sedangkan `eval_kompas_cekfakta.csv` menyimpan label sumber `0`. Keduanya bukan label kebenaran siap pakai untuk evaluasi umum. Notebook sengaja melaporkan proporsi prediksi, bukan akurasi terhadap kolom label mentah tersebut. Pemakaian ulang wajib melakukan pemetaan label dan pemeriksaan klaim yang tepat.

[hasil_derau_ocr.csv](../hasil_derau_ocr.csv) yang sudah ada mencatat:

| Kondisi | Akurasi rata-rata 3 seed | Spesifisitas fakta |
|---|---:|---:|
| Bersih | 96,12% | 97,60% |
| Tanpa tanda baca | 89,48% | 81,36% |
| Salah karakter 5% | 90,04% | 83,33% |
| Gabungan sedang | **74,65%** | **50,56%** |

Angka derau ini diperiksa dari artefak tersimpan, tidak dihitung ulang dari seluruh inferensi derau saat audit. Ini simulasi teks pada val+dev_test, bukan hasil membaca gambar nyata. Penurunan spesifisitas menunjukkan fakta lebih sering bergeser menjadi prediksi hoaks pada kondisi tersebut. CI dalam skrip derau merupakan pendekatan dari akurasi rata-rata seed, bukan interval yang secara penuh memodelkan korelasi antar-seed dan kelompok artikel.

### 4. Aturan aplikasi berbeda dari protokol final

[Protokol](../docs/PROTOKOL_PRAREGISTRASI.md:49) menetapkan pelaporan per seed, mean±SD, dan melarang ensemble. [Inferensi aplikasi](../src/ml/inference.py:51) memakai `unanimous`: keputusan dari tiga seed, lalu abstain jika suara berbeda. Docstring kode sendiri masih menyebut aturan tersebut kandidat yang belum dikunci.

Keduanya dapat dipisahkan sebagai eksperimen per-seed dan kebijakan aplikasi, tetapi status, dasar pemilihan, dan evaluasinya harus ditulis sebelum lockbox dibuka. Angka per-seed tidak boleh langsung disebut sebagai akurasi sistem konsensus aplikasi.

Sebagai ilustrasi, penggabungan gerbang pada teks beku dengan prediksi tersimpan menghasilkan 196 dari 236 dev_test yang diputuskan, 186 benar: akurasi pada yang diputuskan 94,90%, cakupan 83,05%, dan proporsi benar sekaligus diputuskan 78,81%. Ini estimasi dari teks pendek beku, bukan uji API independen atau skor pada teks penuh. Ketiga metrik memiliki penyebut berbeda.

## Koreksi terhadap catatan lampiran dan gerbang input

- Benar: 27 dari 2.132 teks ditolak oleh validasi input karena kata fungsi sedikit; terdiri atas 3 fakta dan 24 hoaks.
- **Perlu koreksi: hanya 20 dari 27 memiliki rasio tepat 0.** Tujuh lainnya memiliki rasio positif 0,01667–0,01923. Tidak semua teks tertolak sama sekali tidak memuat kata fungsi.
- Benar: guardrail domain pada judul+isi penuh meloloskan 100% pada kedua label. Itu konsisten dengan cara korpus diseleksi menggunakan aturan yang sama; bukan uji independen bahwa guardrail selalu benar pada input baru.
- Pada teks beku terpotong, gabungan validasi dan domain meloloskan 893/1.066 fakta (83,77%) dan 960/1.066 hoaks (90,06%). Penyebab banyak penolakan adalah kata kunci domain hilang setelah pemotongan; dampaknya tetap perlu dilaporkan untuk input OCR yang memang pendek.
- Lolosnya 98,7% korpus dari validasi saja belum membuktikan ambang aman untuk bahasa, berita pendek, atau pengguna baru. Kalimat Indonesia bergaya judul dapat tidak memiliki anggota daftar kata fungsi yang terbatas tersebut.
- Ditemukan celah validasi setelah pembersihan: input 10 kata berupa `KPU dan` + delapan URL lolos, tetapi menjadi **`KPU dan.` (2 kata)** setelah praproses dan tetap diteruskan ke backend. Probe menggunakan backend tiruan untuk membuktikan alur; ini bukan prediksi model asli. [Lokasi](../src/ml/inference.py:130) hanya memeriksa kosong/tidak kosong sesudah praproses.

## Kesiapan pengujian dan integrasi aplikasi

1. **Uji gambar belum dapat dijalankan melalui skrip yang dirujuk lampiran.** Eksekusi `uji_ujung_ke_ujung.py data/sample_panjang.png` berhenti dengan `ModuleNotFoundError: No module named 'ocr_paddle3'` pada [baris 9](../uji_ujung_ke_ujung.py:9). Pembungkus OCR sekarang berada di `src/utils/ocr_extractor.py`. Folder `data/` hanya memiliki dua gambar sampel; tiga gambar nyata bersih/poster/buram yang diminta lampiran belum tersedia dengan nama tersebut. Uji gambar akhir juga perlu mencakup jalur upload API yang menambahkan `clean_ocr_artifacts`.
2. **LIME masih otomatis pada route teks.** [Route](../src/api/routes/detection_routes.py:50) memanggil predictor tanpa opsi `explain`; default pembungkus adalah `True` di [inference.py](../src/ml/inference.py:260), dengan 200 sampel. Saran menjadikannya fitur saat diminta belum diterapkan. Pengukuran 17 kasus yang memakai `nilai(..., explain=False)` tidak mengukur biaya route teks tersebut.
3. **Pemetaan hasil route tidak sepenuhnya selaras.** Predictor mengembalikan status huruf kecil dan `votes_hoax`, sedangkan route memeriksa penolakan huruf besar dan membaca `agreement_ratio` yang tidak dikirim predictor. Probe fungsi route dengan model/DB tiruan mengonfirmasi `agreement_ratio=null` meski suara `3/3`; penolakan juga menghasilkan pesan tingkat atas “Verifikasi berhasil diselesaikan” dan kehilangan alasan aslinya. Ini pengujian fungsi route dan skema, bukan pengujian HTTP penuh.
4. **Komponen tampilan masih memakai kontrak lama.** `useDetection.ts` dan `VerdictCard.tsx` membaca `prediction`, `confidence_score`, dan `inference_time_seconds`, sedangkan route mengirim `pattern_label`, `agreement_ratio`, dan `latency_seconds`. Integrasi tampilan perlu pengujian tersendiri; rasio kesepakatan seed juga bukan probabilitas kebenaran.
5. **Tes dan reproduksibilitas belum lengkap.** `tests/test_predictor.py` dan `tests/test_political_filter.py` kosong. `requirements-train.txt` dan `scripts/run_train_server.sh` juga kosong. Notebook memasang dependensi tanpa versi terkunci. Lingkungan lokal berbeda dari log training, sehingga hash model/data dan uji paritas sangat penting. `src/ml/inference_service.py` memiliki utilitas kalibrasi, tetapi tidak dipanggil jalur inferensi aktif; keberadaan berkas itu bukan bukti probabilitas aplikasi telah dikalibrasi.
6. **Dokumentasi model tertinggal.** README menonjolkan Focal Loss dan ketidakseimbangan kelas, padahal data final seimbang 50:50 dan checkpoint aktif adalah CE. Protokol juga menulis ambang strata “1.500 pasang”, sementara kode menghitung jumlah baris; train final 1.660 baris = 830 pasang label seimbang. Satuan tersebut perlu diperjelas.

Ada tiga pasangan dev_test→train dengan cosine sekitar 0,707–0,719 setelah TF-IDF dihitung ulang pada korpus pengembangan. Tidak ada judul identik atau grup lintas split. Karena IDF berubah dari graf pembentuk dataset yang lebih besar, tiga pasangan ini adalah kandidat inspeksi, bukan bukti pasti pelanggaran grouping asli atau dasar mengklaim “bebas seluruh kebocoran”. ID pasangan tersimpan dalam ringkasan JSON.

## Urutan tindak lanjut yang disarankan

1. Selaraskan laporan dengan build final: CE, nilai C4 72,46%, batas klaim, satuan strata, dan kebijakan per-seed/konsensus. Jangan menuliskan keputusan baru seolah-olah sudah dipraregistrasikan sebelum training; catat deviasi dan tanggal sebenarnya.
2. Rapikan jalur validasi sesudah pembersihan, kontrak hasil API, biaya LIME, dan impor pengujian OCR. Uji dengan model tiruan untuk alur, lalu model asli untuk konsistensi, secara terpisah.
3. Siapkan set eksternal berlabel yang diverifikasi: fakta dan hoaks pada sumber/gaya yang saling silang, klaim sama dalam gaya formal/medsos, serta gambar nyata dan transkripsi acuannya. Hindari kata “hoaks/palsu” hanya muncul pada contoh berlabel hoaks seperti empat contoh `hasil_set_luar.csv`.
4. Laporkan Macro-F1, recall hoaks, spesifisitas fakta, cakupan, abstain, dan kesalahan per sumber/gaya/kualitas gambar. Untuk OCR, ukur juga kesalahan transkripsi terhadap acuan. Jangan menganggap 17 uji fungsional atau empat contoh buatan sebagai evaluasi generalisasi.
5. Jika perlu memperbaiki data atau melatih ulang, buat versi eksperimen baru; jangan mengubah dataset beku diam-diam. Augmentasi gaya/derau diterapkan hanya pada data latih dan dinilai pada data yang tidak digunakan menyusun perbaikan. Focal Loss sendiri bukan solusi untuk perancuan sumber dan format.
6. Setelah konfigurasi, aturan aplikasi, dan rencana analisis dikunci, baru jalankan evaluasi lockbox sesuai protokol yang disepakati. Jangan gunakan lockbox untuk memilih perbaikan.

## Artefak audit

- [Ringkasan mesin dan perhitungan ulang](audit_model_2026-10-24_summary.json).
- [Probe fungsi route dengan model/OCR/DB tiruan](audit_model_2026-10-24_api_probes.json). Percobaan TestClient menemui loop redirect pada lingkungan ini; karena itu audit tidak mengklaim status HTTP dari probe tersebut. Pembungkus OCR yang berhasil dengan `alasan=[]` dipetakan normal, bukan temuan galat.
- [17 kasus batas dengan backend tiruan](audit_model_2026-10-24_batas_stub.csv).
- [Skrip audit yang dapat diulang](../scripts/audit_model_readonly.py): jalankan `.\.venv\Scripts\python.exe scripts\audit_model_readonly.py` dari root. Skrip hanya menulis ringkasan audit; tidak memuat bobot atau mengevaluasi lockbox.

Uji paritas bobot asli selesai dengan exit code 0: **0 perbedaan dari 1.416 prediksi**. Pada val, akurasi seed 42/123/999 adalah 97,46%/96,61%/97,03%; pada dev_test 94,49%/95,76%/95,34%. Percobaan batch bawaan 32 terhenti ketika sumber daya memori tidak mencukupi; pengulangan menggunakan batch 4 dan dua thread CPU, tanpa mengubah bobot, tokenizer, atau data. Waktu setelah model dimuat sekitar 115 detik untuk val dan 113 detik untuk dev_test. Uji ini membandingkan backend pada kolom `text` beku; tidak menguji keseluruhan route, gerbang, atau LIME. [Catatan terstruktur](audit_model_2026-10-24_parity.json).
