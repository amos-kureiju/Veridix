# Catatan Historis Audit dan Dokumentasi

Tanggal pemindahan: **13 November 2026**. Ini arsip konteks, bukan status operasional terkini.

## 1. Sumber dan batas

Catatan ini memindahkan lampiran angka audit, daftar masalah pada AGENTS lama, dan urutan pekerjaan yang sebelumnya berada di panduan panjang. Sumbernya adalah dokumen kerja dan laporan percakapan pada sesi tersebut. Pemindahan ini tidak menjalankan ulang tes, mengaudit database, memuat checkpoint, atau membuka lockbox.

Daftar AGENTS lama mengacu pada revisi 58e83d2. Sesudahnya terdapat perubahan lokal yang belum dicakup snapshot itu. Jangan menggunakan temuan lama untuk menyatakan bahwa revisi baru masih gagal atau sudah lulus.

## 2. Klaim audit yang perlu ditelusuri

Tabel berikut dipertahankan dari lampiran panduan sebelum pembagian. Ini klaim laporan terdahulu yang perlu ditelusuri, bukan status terbaru atau pengujian yang dijalankan saat pemisahan.

| Klaim laporan | Tindak lanjut |
| --- | --- |
| Hash 3/3 checkpoint cocok | Periksa manifest, hash, dan artefak yang dimuat. |
| 12/12 pasangan metrik konsisten | Periksa prediksi/label, identitas sampel, definisi, dan script. |
| C4 72,46%; target 60%; protokol 66,6% | Telusuri perhitungan dan buat adendum jika perbedaannya terbukti. |
| LIME 24/24 pengukuran selesai; 1/8 kelompok memenuhi Jaccard ≥ 0,6 | Pisahkan keberhasilan eksekusi dari stabilitas eksploratif. |
| TypeScript, 23 tes Python, dan 21 tes frontend lulus | Telusuri commit, lingkungan, cakupan, dan laporan mentah. |
| 18 tes Verdict gagal dan dilaporkan terkait `window` | Periksa log/config, sesuaikan lingkungan bila diperlukan, lalu jalankan ulang. |

Angka lama tidak membuktikan revisi sekarang lulus.



## 3. Pemeriksaan lanjutan yang pernah dilaporkan

Sesudah laporan kegagalan 18 tes Verdict, pemeriksaan dalam sesi 13 November mencatat:

| Pemeriksaan saat itu | Hasil yang dilaporkan | Batas |
| --- | --- | --- |
| test_verdict_feedback.cjs + test_frontend_guest_access.cjs | 39 lulus, 0 gagal. | Komponen/hook dengan mock; mencakup perbaikan lingkungan window. |
| Modul Python consensus/model-loading, reporting/history, database-errors | 51 lulus. | Fixture terisolasi dan pemuatan model tiruan; bukan evaluasi akurasi checkpoint. |
| Pemeriksaan TypeScript pada saat itu | Satu TS2339: halaman feedback mengambil token yang tidak dikembalikan useAuth. | Pengguna kemudian mengubah berkas; ini bukan penilaian revisi berikutnya. |

Tabel ini adalah ringkasan hasil yang pernah dilaporkan di percakapan, bukan salinan log mentah baru. Angka 23/21 dan 18 gagal pada tabel lama mempunyai cakupan/urutan berbeda dari 51/39 berikutnya; jangan menggabungkannya sebagai satu suite atau satu revisi.

Untuk bukti yang dapat diaudit ulang, simpan command, stdout/stderr yang sudah disanitasi, commit/hash berkas, waktu, lingkungan, cakupan data, dan jenis fixture pada laporan pengujian tersendiri. Jangan membuat metadata yang tidak diketahui.

## 4. Snapshot masalah pada revisi 58e83d2

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



## 5. Urutan usulan pada panduan sebelumnya

Urutan awal berdasarkan temuan:

1. Data feedback akun yang nyata.
2. Status kegagalan backend dan pesan hasil.
3. Keselarasan status legacy, review, dan kepemilikan.
4. Bantuan, dashboard, serta ketersediaan ekspor.
5. Pemotongan teks dan provenance hasil.
6. Integritas LIME dan penyimpanan preferensi.
7. Beban, privasi, bukti penelitian, dan konsistensi diagram.



Urutan tersebut disimpan sebagai konteks. Prioritas pekerjaan baru mengikuti kode, kebutuhan pengguna, dan risiko saat ini; bukan urutan historis secara otomatis.

## 6. Rujukan aktif

- [Instruksi wajib](../AGENTS.md).
- [Panduan Pengembangan AI](../docs/PANDUAN_PENGEMBANGAN_AI.md).
- [Referensi Sistem](../docs/REFERENSI_SISTEM.md).
- [Audit model 24 Oktober](AUDIT_MODEL_2026-10-24.md).
- [Audit performa 31 Oktober](AUDIT_PERFORMA_AI_2026-10-31.md).

Perubahan metodologi tetap memerlukan catatan/adendum yang sesuai pada [protokol penelitian](../PROTOKOL_PRAREGISTRASI.md). Pemisahan dokumentasi ini bukan adendum dan tidak menetapkan ulang keputusan penelitian.
