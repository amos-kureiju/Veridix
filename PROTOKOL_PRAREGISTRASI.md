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