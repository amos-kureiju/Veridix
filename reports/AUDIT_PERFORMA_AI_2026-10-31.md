# Audit performa backend dan AI — 31 Oktober 2026

Frontend kembali lulus TypeScript setelah perbaikan penutup JSX. Status ini memastikan kompilasi; kesiapan klasifikasi dan backend dinilai terpisah.

Audit ini tidak mengubah kode aplikasi, bobot, atau dataset beku. Tidak ada akses ke isi lockbox atau database akun nyata. Dua berkas laporan ditambahkan agar hasil pengukuran dapat ditinjau. Detail angka dan hash tersedia di [JSON pengukuran](audit_performa_ai_2026-10-31.json).

## 1. Model dan lingkungan yang diukur

- Jalur aktif: `src/ml/inference.py`, CE tiga seed 42/123/999, keputusan unanimous.
- Pemeriksaan hash ketiga checkpoint, pipeline tp-1.6, dan revisi model dasar lulus; `allow_unverified=False`.
- CPU, PyTorch 2.14.0+cpu, 16 logical CPU, RAM total sekitar 15,39 GiB. RAM tersedia pada probe awal sekitar 2,82 GiB.
- Pengukuran menggunakan dua thread dan batch 1/4 hanya di proses uji. Default kode tetap batch 32. Bobot dibaca dari cache lokal dalam mode offline.
- RSS proses setelah model dimuat sekitar 1.226–1.275 MiB. Ini observasi working set, bukan pengukuran peak RSS.

## 2. Latensi nyata dan kandidat optimasi

| Pengukuran | Hasil | Batas interpretasi |
|---|---:|---|
| Inisialisasi model run pertama | 25,84 detik | get_predictor, cache bobot lokal; tidak termasuk startup interpreter/import |
| Inisialisasi proses kedua | 6,76 detik | Kondisi cache berbeda; bukan distribusi cold start |
| Klasifikasi hangat, padding 128, batch 1 | median 0,5532 detik | Satu teks, tujuh pengulangan |
| Klasifikasi, padding 128, batch 4 | median 0,5334 detik | Enam pengulangan terselang setelah warm-up |
| Klasifikasi, padding dinamis, batch 4 | median 0,2216 detik | Teks sama, enam pengulangan terselang |
| LIME 200, padding 128, batch 1 | 102,79 detik | Satu pengukuran |
| LIME 200, padding 128, batch 4 | 83,70 detik | Satu pengukuran |
| LIME 200, padding dinamis, batch 4 | 23,55 detik | Satu pengukuran |

Padding dinamis mengurangi panjang tensor contoh pendek dari 128 menjadi 21. Pada pengukuran terselang tersebut, klasifikasi sekitar 2,41 kali lebih cepat; pengukuran LIME batch 4 sekitar 3,55 kali lebih cepat. Angka ini adalah kandidat hasil pada perangkat dan teks ini, bukan jaminan performa semua teks. Perbandingan padding mengukur backend tiga seed pada teks yang sudah dipraproses; pengukuran batch 1 tanpa LIME memakai Penilai.nilai, termasuk gerbang dan praproses.

Perbandingan LIME mempertahankan 200 perturbasi, delapan fitur, random seed explainer yang sama, ketiga seed model, label, dan votes 0/3. Delapan bobot keluaran UI identik sampai empat desimal. Weighted R2 lokal sekitar 0,66969 pada kedua konfigurasi; ini diagnostik fit lokal pada perturbasi, bukan bukti kesetiaan global.

Pemeriksaan parity kandidat: 48 keputusan seed pada 16 teks pengembangan tidak berubah; tambahan 24 keputusan seed pada 8 contoh dekat ambang juga tidak berubah. Selisih probabilitas terbesar pada kelompok dekat ambang adalah 4,768e-7. Pemeriksaan ini belum menggantikan regresi lengkap sebelum perubahan kode diterapkan.

Latensi di atas bukan pengukuran HTTP, autentikasi, database, OCR, atau konkurensi. Timer engine juga tidak mencakup pemuatan model oleh adapter lazy. Timeout frontend saat ini 30 detik; biaya LIME pada CPU perlu dipisahkan dari respons klasifikasi utama. Default batch 32 belum diukur ulang karena keterbatasan RAM dan riwayat tekanan memori.

## 3. Kualitas model: hasil tersimpan dan batas kesiapan

Semua 12 kombinasi run×split pada prediksi tersimpan sesuai metrik log pelatihan. Hash train/val/dev_test cocok dengan log. Hasil berikut dihitung ulang dari artefak pengembangan, bukan evaluasi lockbox atau pelatihan baru.

| Konfigurasi | Macro-F1 val, mean±sample SD | Macro-F1 dev_test, mean±sample SD |
|---|---:|---:|
| CE | 97,03% ±0,42 poin | 95,20% ±0,65 poin |
| Focal | 96,89% ±0,25 poin | 95,06% ±1,29 poin |

| Konsensus model mentah | Diputuskan | Ambigu | Benar | Akurasi pada yang diputuskan | Benar/semua input |
|---|---:|---:|---:|---:|---:|
| Val | 232/236 | 4 | 227 | 97,84% | 96,19% |
| Dev_test | 233/236 | 3 | 223 | 95,71% | 94,49% |
| Gabungan eksploratif | 465/472 | 7 | 450 | 96,77% | 95,34% |

Terdapat 15 keputusan kompak salah pada gabungan: 4 fakta menjadi hoaks dan 11 hoaks menjadi fakta. Votes 3/3 tidak menunjukkan probabilitas kebenaran 100%.

Gerbang saat ini meloloskan 205/236 teks val dan 198/236 dev jika kolom text beku dijadikan masukan aplikasi. Overlay label tersimpan memperkirakan dev 196 diputuskan dan 186 benar: cakupan 83,05%, selective accuracy 94,90%, benar/semua 78,81%. Ini hanya estimasi overlay, bukan pengujian ulang model/API. Praproses mengubah 10 teks val dan 5 dev yang lolos, sehingga estimasi tersebut harus diverifikasi lewat jalur model aktual sebelum dipakai sebagai metrik aplikasi.

Empat contoh sample_set_luar berhasil diproses dan sesuai labelnya. Keempatnya tetap hanya smoke test: formal seluruhnya label 0, medsos seluruhnya label 1, dan teks label 1 mengandung petunjuk eksplisit “hoaks”/“palsu”.

## 4. Uji tantangan model riil

| Probe | Hasil |
|---|---|
| Sampel 1 asli, label 0 yang diberikan dataset | Tidak berpola hoaks, 0/3 |
| Sampel 1 diubah menjadi huruf besar | Tetap 0/3 |
| Sampel 1 + “VIRAL!!!” dan “SEBARKAN!!!” | Berpola hoaks, 3/3 |
| Sampel 2 + “VIRAL!!!” dan “SEBARKAN!!!” | Berubah dari 0/3 menjadi 3/3 |
| Sampel 1 “Presiden” menjadi “Pre- siden” | Tetap 0/3 pada kasus ini |
| Teks Inggris 13 kata dengan KPU | Gerbang menerima; dinilai berpola hoaks 3/3 |
| Teks Megawati Hangestri tentang voli | Gerbang menerima sebagai tokoh; hasil ambigu 2/3 |

Transformasi ini merupakan diagnostik sintetis, bukan kumpulan kebenaran baru yang diverifikasi independen. Dua pembalikan akibat framing menunjukkan sensitivitas gaya; tidak dapat ditafsirkan sebagai tingkat kesalahan populasi. Sistem tetap mendeteksi pola, bukan memverifikasi peristiwa.

Probe backend tiruan tambahan mengungkap bahasa Inggris dengan nama “Dan” dapat lolos rasio stopword; konteks politik kesehatan dapat ditolak oleh keyword NOISE; dan pemicu politik di akhir teks dapat terpotong sebelum masuk model. Celah padding URL lama sudah ditutup dengan pemeriksaan jumlah kata setelah pembersihan.

## 5. Bagian backend yang perlu diperbaiki

1. **LIME selalu aktif pada API.** detection_routes memanggil predict_and_explain tanpa opsi, sedangkan default adapter explain=True. Sediakan respons klasifikasi cepat dan penjelasan yang diminta secara eksplisit, dengan pembatasan antrean/konkurensi.
2. **Kontrak respons belum lengkap.** Status engine huruf kecil, beberapa pemeriksaan route/admin huruf besar. Votes, seed_decisions, alasan penolakan, dan aturan keputusan belum diteruskan. agreement_ratio dibaca dari field yang tidak dibuat engine.
3. **Metadata LIME belum lengkap.** Engine tidak mengembalikan num_samples aktual, target kelas, agregasi yang dijelaskan, atau diagnostik fidelity. LIME menjelaskan rerata P(hoaks), bukan voting unanimous.
4. **OCR sinkron dipanggil langsung dari endpoint async.** Gunakan worker dengan konkurensi terbatas setelah memeriksa thread safety singleton. Tetapkan batas ukuran upload/dimensi sesuai kapasitas.
5. **Threshold admin belum mengubah engine.** Engine memakai 0,5, adapter tidak menyediakan setter. Config 0,60 dan path focal-loss adalah sisa konfigurasi; jangan mengaktifkannya sebagai optimasi kecepatan.
6. **Tes model/guard belum lengkap.** test_predictor.py dan test_political_filter.py kosong. test_api.py masih memakai kontrak lama dan SessionLocal aplikasi; perlu isolasi sebelum dijadikan pemeriksaan rutin.

Lock backend pergantian bobot harus dipertahankan. Menghapusnya untuk mengejar konkurensi berisiko mencampur seed antarpermintaan.

## 6. Generalisasi dan urutan pekerjaan

Label dan sumber masih terpisah sempurna dalam data pengembangan. C4 masih 72,46%, melampaui ambang 60%. Protokol masih mencatat 66,6%, klaim bias panjang hilang 100%, serta larangan ensemble yang belum dibedakan dari konsensus aplikasi. Ini perlu koreksi bertanggal dan pembatasan klaim; bukan pengubahan angka atau dataset beku secara diam-diam.

Urutan yang didukung audit:

1. Satukan status/metadata API dan ukur waktu HTTP lengkap.
2. Pisahkan permintaan klasifikasi dan penjelasan LIME.
3. Validasi kandidat padding dinamis lebih luas; ukur batch/thread dan memori serta kasus dekat ambang sebelum adopsi.
4. Tambahkan challenge set label×gaya×sumber, parafrasa tanpa petunjuk label, bahasa/domain ambigu, serta OCR nyata dengan transkripsi acuan.
5. Ukur fidelity/stabilitas LIME dan perubahan skor terhadap penghapusan fitur dengan pembanding acak yang sepadan.
6. Kunci desain, checkpoint, praproses, gerbang, dan pelaporan sebelum evaluasi lockbox sesuai protokol.

Frontend sudah lulus kompilasi. Model layak untuk demonstrasi penelitian dengan batasan yang dijelaskan; bukti sekarang belum cukup untuk klaim generalisasi atau kesiapan sebagai pemeriksa kebenaran umum.

