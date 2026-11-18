# Panduan Pengembangan AI

Dibagi dan dirapikan: **13 November 2026**.

Mulai dari [AGENTS.md](../AGENTS.md). Gunakan panduan ini untuk cara bekerja dan UX; buka [Referensi Sistem](REFERENSI_SISTEM.md) untuk detail teknis. Riwayat angka/temuan lama dipindahkan ke [Catatan Audit Dokumentasi](../reports/CATATAN_AUDIT_DOKUMENTASI_2026-11-13.md).

Tambahan 16 November 2026: pengembangan daftar akun dan status akses admin mengikuti [Panduan Kelola Pengguna](PANDUAN_KELOLA_PENGGUNA.md). Dokumen tersebut memisahkan kondisi kode yang dibaca dari kontrak yang masih direncanakan, termasuk berkas baru dan bukti penerimaannya.

## 1. Tujuan dan kedudukan panduan

Utamakan fitur yang menyelesaikan kebutuhan pengguna dengan alur singkat, data yang dapat ditelusuri, dan kegagalan yang dijelaskan secara benar.

Jawab tiga pertanyaan sebelum mengubah kode:

1. Apa yang pengguna perlu lakukan atau ketahui?
2. Dari mana informasi yang benar berasal dan siapa yang boleh mengaksesnya?
3. Apa bukti bahwa perubahan bekerja pada alur yang dimaksud?

Panduan ini berisi langkah kerja. Detail implementasi yang dibaca dari kode tersedia di [Referensi Sistem](REFERENSI_SISTEM.md); angka pengujian terdahulu berada pada [catatan historis](../reports/CATATAN_AUDIT_DOKUMENTASI_2026-11-13.md). Pembagian dokumen ini tidak menjalankan ulang aplikasi, database, atau model.

Bedakan keadaan berikut:

| Keadaan | Makna |
| --- | --- |
| Terlihat pada kode | Jalur terkait sudah dibaca, tetapi belum tentu diuji saat dijalankan. |
| Dilaporkan dalam bahan | Pernyataan berasal dari audit atau dokumentasi sebelumnya. |
| Teruji | Ada hasil pemeriksaan dengan lingkungan, cakupan, dan revisi kode yang jelas. |
| Rencana | Perilaku yang diusulkan, tetapi belum dibuktikan tersedia. |

Nama endpoint, tabel, field, dan status dalam panduan harus dicocokkan dengan implementasi sebelum digunakan sebagai kontrak.

Selesaikan keputusan teknis rutin berdasarkan konteks yang tersedia. Minta klarifikasi ketika ada kebutuhan penting atau batas pekerjaan yang memang belum dapat ditentukan.

## 2. Cara menelusuri dan mengerjakan perubahan

Telusuri satu alur lengkap:

```text
Kebutuhan pengguna
-> halaman atau komponen
-> hook atau apiClient
-> metode dan route terdaftar
-> schema
-> query database atau pipeline model
-> respons dan penyimpanan
-> keadaan yang terlihat pengguna
```

Sebelum mengedit, temukan:

- Pelaku dan hak aksesnya.
- Hasil yang diharapkan.
- Sumber data yang benar.
- Kontrak permintaan dan respons.
- Pemicu masalah serta dampaknya.
- Perubahan terkecil yang menyelesaikan masalah.
- Pemeriksaan yang sesuai.

| Kondisi | Tindakan yang diutamakan |
| --- | --- |
| Kontrak sudah mendukung perilaku | Perbaiki pemanggil yang salah. |
| Nama field berbeda | Petakan sekali pada batas API yang jelas. |
| Komponen masih sesuai | Perbaiki komponen tersebut. |
| Logika benar-benar digunakan beberapa pemakai | Ekstrak helper atau hook kecil. |
| Data belum tersedia | Lengkapi query, schema, respons, dan pemakainya bersama. |
| Fitur belum didukung | Sembunyikan kontrol atau jelaskan belum tersedia. |
| Masalah berada pada UI atau koneksi data | Pertahankan algoritma dan artefak model. |
| Kebutuhan masih berupa kemungkinan | Catat sebagai rencana tanpa menambah infrastruktur sekarang. |

Gunakan jalur HTTP dan autentikasi yang sudah ada. Hindari alamat dasar, token, dan penanganan galat kedua yang membuat perilaku berbeda.

Untuk `/admin/users`, telusuri tabel ke hook, endpoint admin, schema, `users`, dan agregasi `prediction_logs`. Daftar contoh, perubahan status yang hanya mengubah state browser, dan alert pengiriman tanpa proses server belum memenuhi alur lengkap. Kontrak target dan urutan penggantiannya dikelola pada [Panduan Kelola Pengguna](PANDUAN_KELOLA_PENGGUNA.md); jangan menganggap endpoint rencana sudah tersedia.

Perbaikan UI tidak menjadi alasan untuk mengubah checkpoint, voting, parameter eksperimen, atau dataset. Perubahan metodologi dikerjakan dalam ruang lingkup dan protokol tersendiri.

## 3. Keadaan UI dan dashboard

| Keadaan | Perilaku |
| --- | --- |
| Memuat | Indikator singkat dan pencegahan tindakan konflik. |
| Sukses berisi data | Data nyata dalam cakupan yang benar. |
| Sukses kosong | Keterangan belum ada data. |
| Pencarian kosong | Keterangan filter tidak menemukan hasil. |
| Koneksi/layanan gagal | Kegagalan dan tindakan mencoba lagi. |
| Nilai tidak tersedia | Keterangan yang jelas, tanpa angka pengganti. |
| Fitur belum tersedia | Kontrol disembunyikan atau diberi keterangan. |

“Feedback Saya” menunggu sesi terverifikasi dan mengambil data pemilik. Data contoh tidak digunakan sebagai isi akun nyata.

Admin menyimpan review berdasarkan konteks hasil, memeriksa konfirmasi server, dan melihat nilai yang sama setelah reload. Kegagalan menyimpan mempertahankan draf yang relevan.

Dashboard membedakan kegagalan log dari statistik yang berhasil. Grafik kosong/gagal tidak diisi angka tetap. Metrik menjelaskan sumber, satuan, periode, dan cakupan.

Nilai nol ditampilkan ketika benar-benar diketahui nol. Data yang belum diketahui ditampilkan sebagai tidak tersedia.

Gunakan istilah konsisten, dukungan keyboard, label kontrol, dan penanda selain warna. Peringatan penting tidak disembunyikan dalam bagian teknis tambahan.

## 4. Tipe dan validasi respons

Gunakan satu batas validasi yang jelas pada jalur API.

- Cocokkan field wajib/opsional, enum, nullability, satuan, serta bentuk daftar/detail.
- Pemetaan nama dilakukan sekali, bukan fallback berbeda di tiap komponen.
- Jangan memakai `as any` atau default kosong untuk menyamarkan payload rusak.
- TypeScript tidak memvalidasi JSON saat runtime.
- Tipe dapat dibangkitkan dari OpenAPI jika schema aktual akurat.
- `openapi-typescript` merupakan pilihan alat yang perlu dievaluasi, bukan dependensi wajib.
- Gunakan parser/type guard yang memadai tanpa menambah lapisan berlebihan.
- Perubahan kontrak memperbarui schema, parser, tipe, UI, dan fixture terkait.

Perbedaan `status`/`review_status`, `review_notes`/`admin_notes`, dan enum tidak dikenal harus terdeteksi melalui pemeriksaan kontrak.

## 5. Bukti penerimaan dan pengujian

Gunakan akun/fixture terisolasi dan data yang diizinkan protokol. Pemeriksaan khusus riwayat ada di [Panduan Riwayat](PANDUAN_RIWAYAT.md), sedangkan OCR ada di [Panduan Pengujian OCR](PANDUAN_PENGUJIAN_OCR.md). Pilih skenario yang terkait perubahan; tabel berikut bukan kewajiban menjalankan semua pengujian pada setiap tugas.

### 5.1 Aplikasi dan kontrak

| Skenario | Bukti yang diperlukan |
| --- | --- |
| Akun A/B berbeda | Data dan respons terlambat tidak tertukar antar akun. |
| Operasi admin | Role diperiksa backend. |
| Daftar akun admin | Akun lokal/Google berasal dari database terisolasi; nol, total hasil filter, dan panjang halaman dibedakan. |
| Status akses akun | Perubahan persisten setelah konfirmasi; target ADMIN dilindungi dan JWT lama tetap ditolak setelah aktivasi kembali. |
| Feedback ulang/bersamaan | Tidak ada duplikasi pasangan logis; status konsisten. |
| Review tersimpan | Konfirmasi server dan reload menghasilkan nilai sama. |
| Penyimpanan gagal | Tidak muncul keberhasilan lokal; draf relevan tetap tersedia. |
| Edit feedback | Status/metadata mengikuti kontrak; riwayat mengikuti fitur yang tersedia. |
| Penghapusan | Kepemilikan, transaksi, dan kebijakan data konsisten. |
| Payload rusak | Validasi gagal secara jelas, tanpa sukses/daftar kosong palsu. |
| Dashboard sebagian gagal | Kegagalan dipisahkan tanpa angka pengganti. |
| OCR disunting | Teks terakhir dikirim dengan sumber yang benar. |
| Preferensi disimpan | Event membaca nilai baru; reload mempertahankannya. |
| Reset | Draf kembali ke bawaan; penyimpanan melalui Simpan. |
| Fitur/data tidak tersedia | Tidak muncul contoh atau metrik buatan sebagai data nyata. |

### 5.2 Model, integritas, dan LIME

| Skenario | Bukti yang diperlukan |
| --- | --- |
| Baseline dibekukan | Bandingkan dengan artefak seperti `prediksi_val_dev.csv` jika tersedia; cocokkan identitas sampel, input, pipeline, dan konfigurasi. |
| NaN/tak hingga/seed wajib tidak lengkap | Tidak ada keputusan atau skor pengganti. |
| Batas bahasa/domain/kelayakan | Sesuai aturan aktif pada fixture yang diizinkan. |
| Hash tidak cocok | Layanan prediksi tidak dinyatakan siap. |
| Pencatatan hasil | Artefak/config yang digunakan dapat ditelusuri. |
| LIME lintas versi | Versi sesuai atau keterbatasan dinyatakan. |
| Reproduksibilitas LIME | Input, seed, model, config, dan lingkungan dikendalikan dengan toleransi protokol. |
| Stabilitas LIME | Diukur terpisah dari keberhasilan eksekusi. |
| Nol dan bobot rusak | Nol sah dipertahankan; data rusak tidak menjadi `0.0000`. |
| Pilihan 3/5/7 | Jumlah dibatasi ketersediaan; bobot/label tetap. |
| Grafik dimatikan | Penjelasan dan peringatan tetap sesuai. |
| Pemotongan | Penanda dan bagian input model sesuai tahap sebenarnya. |
| OCR gagal | Alasan benar; tidak ada klasifikasi otomatis atau data lama tertukar. |

Pengujian baseline tidak memberi izin membuka atau mengeksplorasi ulang lockbox.

### 5.3 Lingkungan tes

Komponen yang memakai `window`, storage, atau DOM memerlukan lingkungan tes sesuai. Gunakan mock browser/runner yang sudah ada; jsdom hanya pilihan jika diperlukan, bukan dependensi wajib.

Periksa stack trace sebelum menyimpulkan penyebab kegagalan. Jangan menghapus efek preferensi hanya agar tes lulus.

Periksa pembacaan storage, urutan event, dan pelepasan listener. SSR normal tidak menjalankan `useEffect`; bedakan dari test renderer tanpa DOM.

Laporkan terpisah:

- Pemeriksaan TypeScript/statis.
- Tes unit/kontrak dengan mock.
- Integrasi database.
- Model/checkpoint nyata.
- Browser.
- Beban.

Jangan menyebut browser, database, atau model asli telah diuji ketika hanya mock yang dijalankan. Jika konfigurasi pemeriksaan belum tersedia, laporkan batasnya.

### 5.4 Contoh pemeriksaan terisolasi

Jalankan dari akar proyek dan pilih modul yang sesuai setelah memeriksa fixture:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_consensus_metadata tests.test_model_loading -v
.\.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_reporting_integrity tests.test_history_routes tests.test_history_detection_flow -v
.\.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_database_errors -v
node --test tests/test_verdict_feedback.cjs tests/test_frontend_guest_access.cjs
node frontend/node_modules/typescript/bin/tsc -p frontend/tsconfig.json --noEmit --incremental false
```

Tes Python di atas memakai fixture terisolasi/pemuatan model tiruan; tes komponen tidak menjalankan browser nyata. Jangan memakai seluruh discovery yang dapat memasukkan `tests/test_api.py`. Build frontend, bila relevan, dijalankan dari folder `frontend` melalui `npm.cmd run build` setelah pemeriksaan tipe lulus.

Perintah dan hasilnya adalah hal berbeda. Catat perintah yang benar-benar dijalankan, revisi, cakupan, dan hasil; dokumen ini tidak menyatakan tes tersebut telah dijalankan saat pembagian.

## 6. Prioritas dan batas selesai

Tentukan prioritas dari masalah pada kode saat ini: penghambat build, pemisahan data akun, risiko perubahan perilaku model, dan alur pengguna yang gagal. Jangan mengikuti urutan audit lama tanpa memeriksa perubahan yang sudah terjadi.

Perbaikan kecil yang independen boleh dikerjakan lebih awal. Hindari perombakan seluruh sistem untuk perubahan lokal. Optimasi performa dimulai dari pengukuran request/query, waktu, ukuran input, atau tindakan pengguna yang terhambat; batas teknis tersedia di [Referensi Sistem](REFERENSI_SISTEM.md).

Pekerjaan selesai pada cakupannya ketika kebutuhan pengguna, sumber data, kontrak, hak akses, keadaan gagal/kosong, dan pemeriksaan terkait telah terhubung. Selesai satu fitur tidak berarti seluruh sistem atau penelitian sudah final.

## 7. Pemeliharaan dokumentasi

| Dokumen | Tanggung jawab |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | Aturan wajib dan navigasi ke acuan yang relevan. |
| Panduan ini | Cara menelusuri masalah, memilih solusi sederhana, menjaga UX, dan menentukan bukti selesai. |
| [Referensi Sistem](REFERENSI_SISTEM.md) | Sumber kode, arsitektur, API, relasi, status, model, dan batas implementasi. |
| [Panduan Riwayat](PANDUAN_RIWAYAT.md) / [Pengujian OCR](PANDUAN_PENGUJIAN_OCR.md) | Detail alur dan pemeriksaan khusus yang sudah tersedia. |
| [Integrasi LIME](PANDUAN_INTEGRASI_LIME.md) | Arsitektur penjelasan teks/OCR, kontrak metadata, konteks permintaan, penyimpanan, dan batas bukti pengujian. |
| [Panduan Kelola Pengguna](PANDUAN_KELOLA_PENGGUNA.md) | Rencana daftar akun admin dari database, kontrak status akses, berkas implementasi baru, dan bukti penerimaan; status implementasi diperbarui setelah kode berubah. |
| [README](../README.md) | Pintu masuk proyek dan petunjuk menjalankan; cocokkan keterangan lama dengan kode. |
| [Protokol](../PROTOKOL_PRAREGISTRASI.md) dan reports/ | Metodologi serta laporan eksperimen/audit bertanggal. |

Ubah sumber utama ketika kontrak atau kebijakan berubah, lalu perbarui tautan pemakainya. Hindari menyalin daftar endpoint, enum, angka konfigurasi, dan hasil tes ke beberapa panduan. Tulis kebutuhan yang belum diimplementasikan sebagai rencana.

Laporan pengerjaan memuat masalah, perubahan, alasan, pemeriksaan, dan pekerjaan tersisa. Jika pengguna meminta perubahan sebagian, tunjukkan lokasi serta potongan yang relevan.

> Pahami kebutuhan pengguna dan telusuri jalur aktif. Gunakan data dan kontrak yang tersedia, pilih perubahan paling sederhana yang menyelesaikan alur lengkap, lalu buktikan hasilnya. Jangan mengarang endpoint, status, angka, atau keberhasilan.
