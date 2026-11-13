# Panduan Kerja dan Integritas Sistem VERIDIX

Tanggal acuan: **13 November 2026**. Berlaku untuk pekerjaan di repositori ini. Catatan kondisi implementasi mengacu pada audit revisi `58e83d2`; perubahan setelah revisi tersebut perlu diverifikasi kembali.

## 1. Tujuan utama

VERIDIX membantu pengguna mengenali **kemiripan pola bahasa dengan klaim politik Indonesia yang dilabeli hoaks pada korpus penelitian**. Sistem bukan pemeriksa kebenaran peristiwa secara otomatis.

Panduan ini menjaga agar implementasi, tampilan, pengujian, dan laporan menyampaikan keadaan sebenarnya: data berasal dari sumber yang jelas, kegagalan terlihat, serta keterbatasan tetap dicatat. Panduan bukan bukti bahwa sistem bebas seluruh kesalahan atau manipulasi.

Ikuti instruksi pengguna sesuai ruang lingkup pekerjaannya. Jika diminta memeriksa saja, lakukan pemeriksaan tanpa mengubah kode. Untuk pekerjaan yang sudah diotorisasi, lanjutkan secara mandiri tanpa menambahkan alur persetujuan yang tidak diperlukan.

## 2. Alur sistem yang harus dipahami

```text
Teks langsung -------------------------------+
                                             |
Gambar -> PaddleOCR -> pengguna memeriksa     |
          dan menyunting teks ---------------+
                                             v
                         Validasi masukan dan gerbang domain
                            | layak                 | ditolak
                            v                       v
                    Praproses dan tokenisasi   Alasan penolakan
                            |
                            v
                 IndoBERT CE: seed 42, 123, 999
                            |
                            v
                    Keputusan per seed -> voting
                            |
                            v
                   Simpan hasil -> tampilkan hasil
                            |
              +-------------+----------------+
              v                              v
       LIME jika diminta              Feedback pengguna
       oleh pemilik hasil             -> tinjauan admin
```

Kegagalan OCR, model, jaringan, atau database harus mempunyai penanganan kegagalan sendiri. Jangan meneruskannya sebagai klasifikasi yang berhasil. Menyimpan feedback atau menandainya untuk penelitian tidak menjalankan pelatihan ulang.

## 3. Peta berkas dan sumber kebenaran

| Bagian | Berkas acuan |
| --- | --- |
| Inisialisasi API, router, dan respons galat database | [main.py](main.py) |
| Validasi dan praproses teks | [input_validation.py](src/utils/input_validation.py), [praproses.py](src/utils/praproses.py), [text_pipeline.py](text_pipeline.py) |
| Gerbang domain | [political_guardrail.py](src/utils/political_guardrail.py) |
| Pemuatan checkpoint, voting, dan LIME aktif | [inference.py](src/ml/inference.py) |
| Endpoint deteksi dan penjelasan | [detection_routes.py](src/api/routes/detection_routes.py), [schemas.py](src/api/schemas.py) |
| OCR aktif | [ocr_pipeline.py](src/utils/ocr_pipeline.py), [ocr_extractor.py](src/utils/ocr_extractor.py) |
| Riwayat, feedback, dan admin | [user_routes.py](src/api/routes/user_routes.py), [feedback_routes.py](src/api/routes/feedback_routes.py), [admin_routes.py](src/api/routes/admin_routes.py) |
| Penyimpanan data | [models.py](src/database/models.py) |
| Permintaan dan tampilan deteksi | [useDetection.ts](frontend/src/hooks/useDetection.ts), [VerdictCard.tsx](frontend/src/components/detector/VerdictCard.tsx), [LimeHighlighter.tsx](frontend/src/components/detector/LimeHighlighter.tsx) |
| Preferensi tampilan lokal | [userSettings.ts](frontend/src/lib/userSettings.ts), [halaman Settings](frontend/src/app/settings/page.tsx) |
| Metodologi penelitian | [PROTOKOL_PRAREGISTRASI.md](PROTOKOL_PRAREGISTRASI.md) dan hasil eksperimen yang menyertakan versi/konfigurasinya |

Periksa jalur yang benar-benar diimpor dan dipanggil. Nama berkas, komentar, README, atau notebook lama belum membuktikan bahwa suatu implementasi sedang dipakai. Jika dokumentasi bertentangan dengan kode, laporkan perbedaannya; jangan menganggap salah satunya otomatis benar untuk semua konteks.

## 4. Konfigurasi model dan arti angka

Baseline aplikasi pada tanggal acuan:

| Unsur | Nilai/perilaku |
| --- | --- |
| Model dasar | `indobenchmark/indobert-base-p1`, revisi dipatok dan diperiksa |
| Checkpoint terpilih | Cross-Entropy / `ckpt_ce_*`, seed `42`, `123`, `999` |
| Praproses | `tp.clean -> tp.ensure_end -> tp.cap_sentences(60)` |
| Tokenisasi | Maksimum 128 token, padding tetap; batch inferensi 32 |
| Keputusan tiap seed | Hoaks jika probabilitas kelas hoaks `>= 0.5` |
| Aturan aplikasi bawaan | `unanimous`; kode masih menyediakan pengaturan melalui `VERIDIX_DECISION_RULE` |
| LIME | Menjelaskan rerata probabilitas kelas hoaks tiga seed; jumlah sampel dari `VERIDIX_LIME_SAMPLES`, bawaan 200 |

Untuk aturan `unanimous` tiga seed:

| Suara hoaks | Status | Label aplikasi |
| --- | --- | --- |
| `3/3` | `dinilai` | `BERPOLA HOAKS` |
| `0/3` | `dinilai` | `TIDAK BERPOLA HOAKS` |
| `1/3` atau `2/3` | `ambigu` | Perlu verifikasi karena seed tidak sepakat |

`agreement_ratio = max(suara_hoaks, 3 - suara_hoaks) / 3` adalah **kesepakatan suara**, bukan probabilitas hoaks, akurasi, atau persentase kebenaran. Kesepakatan 100% masih dapat salah. Cross-Entropy adalah fungsi loss pelatihan; keputusan aplikasi memakai probabilitas dan aturan voting.

Catat konfigurasi yang benar-benar aktif. Jangan mengasumsikan nilai bawaan tetap berlaku jika lingkungan mengubahnya. Mengganti checkpoint, pipeline, aturan voting, tokenisasi, atau konfigurasi LIME merupakan perubahan perilaku yang perlu penjelasan dan evaluasi yang sesuai.

## 5. Aturan kejujuran data dan tampilan

1. Gunakan data terukur dari sumber yang dapat ditelusuri. Jangan mengisi hasil, jumlah, latensi, progres, grafik, atau status berhasil dengan angka contoh ketika data sebenarnya tidak tersedia.
2. Bedakan `0`, `False`, daftar kosong yang sah, nilai tidak tersedia, dan kegagalan mengambil data. Jangan mengubah `null`, bobot rusak, atau galat menjadi angka nol yang terlihat terukur.
3. Data demo hanya untuk mode demo yang diberi penanda jelas. Akun nyata tidak boleh menerima data contoh sebagai riwayat atau feedback miliknya.
4. Tampilkan keberhasilan penyimpanan atau review setelah respons server mengonfirmasinya. Perubahan state lokal tidak membuktikan database berubah.
5. Petakan label dan status secara eksplisit. Pencarian `includes("HOAKS")` saja salah untuk `TIDAK BERPOLA HOAKS`. Status tidak dikenal tetap netral; `DISMISSED` tidak boleh ditampilkan sebagai `PENDING`.
6. Jangan menyebut label `TIDAK BERPOLA HOAKS` sebagai bukti berita faktual. Jangan menyebut kandidat retraining sebagai model yang sudah dilatih ulang.
7. Kaitkan hasil dengan masukan yang menghasilkan hasil tersebut. Perubahan draf atau pergantian gambar tidak boleh membuat hasil lama terlihat sebagai hasil masukan baru.
8. Preferensi tampilan boleh mengubah jumlah kata atau visibilitas grafik; jangan mengubah bobot, suara seed, keputusan, atau kualitas penjelasan secara diam-diam.

## 6. Kegagalan, pemotongan, dan penggunaan bersamaan

- Penolakan masukan dan penolakan domain harus menjelaskan alasannya. Label dan konsensus tidak tersedia jika model tidak menilai teks; jangan mengisinya dengan `0/3`.
- Kegagalan komputasi bukan kesalahan pengguna. NaN/Inf, probabilitas di luar rentang, keluaran model kosong, dan jumlah seed yang salah tidak boleh menjadi hasil sukses.
- Validasi kontrak respons. Payload internal rusak tidak boleh otomatis dianggap `dinilai` hanya karena statusnya hilang.
- Jaga respons galat database tetap aman dan terbaca frontend. Jangan mengganti kegagalan query dengan respons sukses berisi daftar kosong.
- Laporkan batas praproses kata dan batas token secara terpisah. Jika pengukuran pemotongan gagal, statusnya tidak diketahui; jangan menyimpulkan seluruh teks sudah dibaca.
- Tokenizer bersama dapat mengubah konfigurasi padding/truncation. Semua akses yang bersaing harus memakai sinkronisasi yang konsisten atau instance terpisah, termasuk pemeriksaan panjang dan callback LIME.
- Tampilkan peringatan pemotongan dan jelaskan bagian teks yang benar-benar masuk model. Teks hasil praproses sebelum pemotongan token belum tentu sama dengan segmen token yang diproses.
- Tampilkan fitur yang belum tersedia sebagai belum tersedia. Jangan memakai pesan “online”, “optimal”, atau “tersinkron” tanpa pemeriksaan yang mendasarinya.

## 7. Ketentuan penjelasan LIME

- Merah berarti bobot lokal menaikkan skor kelas hoaks; hijau berarti menurunkannya. Warna bukan kamus kata benar/salah dan bukan bukti kebenaran berita.
- LIME menjelaskan fungsi rerata probabilitas seed. Jangan menyatakan bahwa bobot LIME secara langsung menghasilkan aturan voting atau status ambigu.
- Gunakan bobot yang diterima, skala maksimum absolut bersama, dan jumlah fitur yang tersedia. Jangan menambahkan panjang batang minimum yang mengubah kesan besarnya pengaruh.
- Jumlah sampel yang ditampilkan harus berasal dari metadata penjelasan. Jangan menulis angka tetap yang dapat berbeda dari konfigurasi sebenarnya.
- R² lokal, galat pendekatan lokal, stabilitas top-k, waktu, dan akurasi klasifikasi adalah ukuran berbeda. R² 0,67 bukan akurasi 67%.
- `status=ok` pada skrip eksperimen berarti syarat pengukuran terpenuhi sesuai skrip, bukan sertifikat kesetiaan LIME.
- Jangan menghapus hasil buruk, mengubah koefisien, atau memotong prediksi surrogate saat melaporkan eksperimen. Prediksi surrogate linear dapat berada di luar `[0,1]`; bedakan dari probabilitas model.
- Cache lama harus tetap dikenali sebagai cache lama. Jangan mengklaim kecocokan dengan checkpoint/pipeline saat ini tanpa metadata identitas yang mendukungnya.

## 8. Akun, riwayat, dan jejak audit

- Gunakan autentikasi dan pemeriksaan kepemilikan di backend. Perlindungan frontend tidak menggantikannya.
- Kaitkan permintaan dengan akun/sesi dan generasi permintaan. Abaikan respons setelah logout, pergantian akun, permintaan pengganti, atau komponen dibongkar.
- Pertahankan masukan dan keluaran aktual jika menambah metadata audit: alasan, keputusan per seed, aturan, konfigurasi, identitas artefak, dan waktu. Bedakan metadata respons langsung dengan metadata yang benar-benar tersimpan.
- Jangan merekonstruksi suara seed dari label atau rasio kesepakatan lalu mengklaimnya sebagai hasil asli.
- Jangan mencetak token, kata sandi, string koneksi, header otorisasi, badan permintaan, atau naskah privat ke log diagnostik. Gunakan jenis galat dan penanda permintaan yang aman.
- Jangan mengubah hash pembanding atau mengaktifkan `VERIDIX_ALLOW_UNVERIFIED` hanya untuk melewati pemeriksaan integritas yang gagal. Perubahan artefak yang sah memerlukan identitas, alasan, dan bukti evaluasi baru.

## 9. Dataset dan batas klaim penelitian

- Acuan pengembangan beku adalah `data/processed_v2`; periksa manifest dan konfigurasi sebelum memilih berkas. Folder trial, salinan, dan arsip bukan otomatis dataset final.
- Pertahankan pemisahan tujuan train, validation, development, dan lockbox sesuai protokol. Hindari pemilihan model berdasarkan hasil set yang tidak diizinkan untuk seleksi.
- Dalam pekerjaan rutin, jangan membaca, menyampel, mengunggah, atau menjalankan isi `LOCKBOX`. Evaluasi final hanya dalam ruang lingkup yang secara eksplisit mencakupnya dan mengikuti protokol/adendum yang berlaku.
- Jangan mengulang evaluasi final atau mengubah ambang setelah melihat hasilnya untuk memperoleh angka lebih bagus. Simpan kegagalan, hasil parsial, penyimpangan, dan seluruh denominator evaluasi.
- Label sumber, sumber rujukan, dan label independen adalah hal berbeda. Catat asal label dan keterbatasan hubungan sumber dengan kelas.
- Empat teks contoh tidak membuktikan akurasi umum, kestabilan LIME, atau ketahanan terhadap OCR. Tes perangkat lunak dengan backend tiruan tidak mengukur akurasi checkpoint.
- Pisahkan simulasi derau OCR dari OCR citra nyata. Pada uji berpasangan, simpan transkripsi acuan, hasil OCR, CER/WER, keluaran klasifikasi, dan penolakan.
- Dokumen ini bukan adendum praregistrasi. Perubahan metodologi harus dicatat bertanggal dengan urutan kejadian yang sebenarnya; jangan mengubah catatan lama seolah ditetapkan sebelum eksperimen.

## 10. Cara bekerja dan memverifikasi perubahan

1. Periksa status Git dan berkas aktif. Pertahankan perubahan pengguna yang sudah ada.
2. Telusuri alur pemanggilan, schema, penyimpanan, dan tampilan sebelum mengubah kontrak. Jelaskan pemicu masalah dan dampaknya.
3. Buat perubahan secukupnya pada jalur yang terkait. Jangan mengganti algoritma atau melatih ulang untuk menyelesaikan masalah tampilan.
4. Jalankan pemeriksaan yang relevan. Gunakan fixture terisolasi; jangan menyentuh database pengguna lewat pengujian otomatis.
5. Laporkan perubahan, alasan, pemeriksaan yang benar-benar dilakukan, kegagalan, serta bagian yang belum diverifikasi.

Contoh pemeriksaan terisolasi dari akar proyek, pilih sesuai perubahan:

```powershell
# Kontrak voting dan pemuatan model; pemuatan bobot ditirukan dalam tes.
.\.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_consensus_metadata tests.test_model_loading -v

# Riwayat dan pelaporan; fixture SQLite memori / galat tiruan.
.\.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_reporting_integrity tests.test_history_routes tests.test_history_detection_flow -v

# Handler database/CORS; tidak menjalankan lifespan aplikasi.
.\.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_database_errors -v

# Komponen/hook; tanpa browser, database, atau model asli.
node --test tests/test_verdict_feedback.cjs tests/test_frontend_guest_access.cjs

# Pemeriksaan TypeScript tanpa menghasilkan cache incremental.
node frontend/node_modules/typescript/bin/tsc -p frontend/tsconfig.json --noEmit --incremental false
```

Periksa fixture sebelum menjalankan tes lain. Jangan memakai seluruh `unittest discover` untuk pemeriksaan rutin: `tests/test_api.py` memakai koneksi aplikasi dan dapat menyentuh database nyata. Build frontend dijalankan dari `frontend` melalui `npm.cmd run build` setelah pemeriksaan tipe lulus. Keberhasilan build belum menggantikan uji browser, API, database, atau model nyata.

## 11. Masalah terbuka pada tanggal acuan

Daftar ini adalah catatan audit revisi `58e83d2`, **bukan daftar perbaikan yang telah diterapkan oleh dokumen ini**. Daftar ini tidak menilai perubahan lokal atau revisi berikutnya. Perbarui statusnya hanya setelah ada perubahan dan bukti verifikasi.

| Bagian | Temuan yang masih perlu ditangani |
| --- | --- |
| Tokenizer inferensi | Pemeriksaan panjang tanpa truncation dan tokenisasi inferensi berbagi tokenizer tanpa sinkronisasi menyeluruh; pengecualian penghitungan masih ditelan. |
| Feedback pengguna | Halaman mengambil `useAuth().token` yang tidak tersedia dan memanggil `/api/feedback/my` yang belum diimplementasikan. Isolasi respons antar-akun dan pemetaan status/label juga belum lengkap. |
| Feedback admin | `RetrainTable` masih memakai data simulasi; tindakan review hanya mengubah state lokal dan menampilkan pesan berhasil. |
| Dashboard admin | Endpoint log terkini belum tersedia. Sebagian keterangan performa/online masih statis; grafik contoh pendaftaran diberi penanda “Contoh”. |
| Teks yang dianalisis | Peringatan pemotongan sudah ada, tetapi `teks_dinilai` belum diteruskan melalui schema/route untuk dibaca kartu hasil. Metadata audit historis dan identitas cache juga belum lengkap. |
| Halaman Bantuan | Masih menyebut mayoritas pada bagian yang seharusnya menjelaskan kesepakatan bulat tiga seed. |
| Protokol penelitian | C4 aktual 72,46% melampaui target 60%, sedangkan protokol masih mencatat 66,6%. Klaim “100% tereliminasi” dan larangan ensemble belum diselaraskan dengan bukti/aplikasi. |
| Bukti LIME | Baseline stabilitas selesai 24/24 fit, hanya 1/8 kelompok memenuhi kriteria eksploratif Jaccard >= 0,6. Kandidat padding dinamis masih menyimpan kegagalan paritas dan belum disetujui untuk aplikasi. |

## 12. Pemeriksaan sebelum menyebut fitur selesai

- [ ] Data dan sumbernya jelas; data demo tidak disajikan sebagai data akun nyata.
- [ ] Kontrak frontend, API, dan database sesuai; tidak ada keberhasilan tanpa konfirmasi.
- [ ] Nilai tidak tersedia dibedakan dari nol dan dari hasil kosong yang sah.
- [ ] Penolakan, kegagalan, pemotongan, dan keterbatasan terlihat oleh pengguna.
- [ ] Permintaan lama tidak dapat mengubah tampilan akun atau masukan yang berbeda.
- [ ] Perubahan model/pipeline/config tercatat dan mempunyai evaluasi yang sesuai.
- [ ] Tes relevan telah dijalankan; kegagalan dan bagian yang belum diuji dilaporkan.
- [ ] Klaim laporan mengikuti bukti, konfigurasi, tanggal, serta denominator yang benar.

Panduan ini bermanfaat jika dipakai bersama pemeriksaan kode, jejak data, dan pengujian. Menambahkan dokumen saja tidak memperbaiki fitur yang masih bermasalah.
