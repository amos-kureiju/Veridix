# Panduan pengembangan kelola pengguna admin

Disusun: **16 November 2026**.

**Status: rencana implementasi berdasarkan pemeriksaan kode lokal.** Dokumen ini belum menambahkan endpoint, menghubungkan tabel, mengubah database, atau menjalankan pengujian. Kontrak rencana harus diimplementasikan dan dibuktikan sebelum disebut fitur tersedia.

Acuan: [AGENTS.md](../AGENTS.md), [Panduan Pengembangan AI](PANDUAN_PENGEMBANGAN_AI.md), dan [Referensi Sistem](REFERENSI_SISTEM.md). Panduan ini memusatkan daftar akun dan perubahan status akses pada `/admin/users`.

## 1. Kondisi kode dan cakupan

Pemeriksaan sumber pada 16 November 2026 menemukan:

| Bagian | Kondisi yang dibaca |
| --- | --- |
| [Halaman pengguna admin](../frontend/src/app/admin/users/page.tsx) | Memasang `UserManageTable`; deskripsi masih menjanjikan pengelolaan izin akses. |
| [UserManageTable](../frontend/src/components/admin/UserManageTable.tsx) | Memakai array tiga akun contoh, angka analisis tetap, dan pencarian lokal. Total berasal dari panjang array. |
| Tindakan status di tabel | `toggleStatus` hanya memperbarui state React; tidak menyimpan ke server. |
| Tindakan reset di tabel | `handleResetPassword` hanya menampilkan alert bahwa tautan telah dikirim. |
| [Router admin](../src/api/routes/admin_routes.py) | Memiliki statistik, threshold, feedback, dan log terkini; belum memiliki endpoint daftar/status pengguna yang direncanakan di sini. |
| [ManagedUser](../frontend/src/types/admin.ts) | Memiliki tipe dasar baris; belum ada kontrak daftar/pagination khusus. |
| Hook kelola pengguna | `useAdminUsers.ts` belum tersedia. |
| [Model akun](../src/database/models.py) | Memiliki UUID, nama, email, role, status aktif, versi sesi, tanggal, dan identitas Google. |
| [Autorisasi](../src/core/auth_deps.py) | Memeriksa akun aktif, versi JWT, dan role admin dari database. |

Temuan ini bukan introspeksi Supabase atau hasil pengujian browser. Angka contoh pada tabel tidak membuktikan jumlah akun atau aktivitas database nyata.

Target tahap ini: daftar akun tersimpan termasuk Google, pencarian/filter/pagination/refresh melalui API, pengaktifan/penonaktifan akun `USER`, serta keadaan memuat/kosong/gagal dan pergantian sesi yang benar.

Perubahan role, penghapusan akun, reset sandi oleh admin, notifikasi, dan perubahan model AI berada di luar tahap ini. Akun `ADMIN` dapat dibaca dalam daftar tetapi statusnya tidak dapat diubah melalui fitur ini. Badge sidebar dan notifikasi bukan sumber jumlah akun; datanya tidak otomatis menjadi dinamis karena tabel pengguna diperbaiki.

## 2. Sumber data dan arti nilai

Sumber akun adalah tabel aplikasi `public.users` melalui backend. Login Google kustom tetap menggunakan UUID akun aplikasi; daftar tidak membaca `auth.users` milik Supabase Auth.

| Field respons rencana | Sumber dan arti |
| --- | --- |
| `id` | `users.id`; UUID asli untuk identitas baris dan tindakan. |
| `name` | Pemetaan tunggal dari `users.full_name`. |
| `email` | `users.email`; tidak diganti email contoh. |
| `role` | `users.role`; enum `USER` atau `ADMIN`. |
| `is_active` | `users.is_active`; tidak diturunkan dari aktivitas terakhir. |
| `created_at` | Waktu pendaftaran tersimpan, ISO 8601 dengan offset. |
| `total_detections` | Jumlah record `prediction_logs` yang `user_id`-nya sama dengan akun tersebut. |
| `has_password` | Boolean keberadaan sandi lokal; nilai hash tidak dikirim. |
| `google_linked` | Boolean keberadaan identitas Google; nilai `google_sub` tidak dikirim. |

Label UI untuk `total_detections` disarankan **Analisis tersimpan**. Angka ini menghitung record yang masih ada, bukan jumlah klik, seluruh percobaan sepanjang umur akun, jumlah berita benar, atau hanya hasil yang berhasil dinilai. Penghapusan riwayat dapat mengubah jumlah pada pembacaan berikutnya.

Aturan query:

- Agregasikan `PredictionLog.user_id` dan pertahankan pengguna tanpa analisis melalui outer join/subquery agregat.
- Hitung ID analisis, bukan `COUNT(*)` pada outer join yang dapat memberi angka satu untuk akun tanpa analisis.
- Jangan memperbanyak hitungan dengan join feedback atau menjalankan query hitungan terpisah per pengguna.
- Nol sah untuk akun tanpa record setelah query berhasil. Kegagalan query tidak boleh menjadi nol.
- Pilih kolom yang diperlukan; jangan memuat naskah/LIME hanya untuk menghitung record.
- Akun seed/demo yang memang tersimpan tidak dihapus/disembunyikan otomatis. Jika perlu membedakannya, gunakan penanda nyata, bukan tebakan berdasarkan nama/email.

Berdasarkan model yang dibaca, daftar/status tidak membutuhkan kolom total atau tabel baru. Kesesuaian skema database nyata tetap perlu diperiksa saat implementasi. Jejak pelaku perubahan status belum tersedia; perubahan `updated_at` tidak membuktikan audit perubahan akun sudah lengkap.

## 3. Rencana kontrak daftar

**Endpoint berikut belum tersedia pada pemeriksaan ini:**

```text
GET /api/v1/admin/users
```

Wajib memakai autentikasi aplikasi dan `require_admin` sebelum membaca akun.

| Parameter rencana | Aturan |
| --- | --- |
| `search` | Opsional; trim, pencarian nama/email tanpa membedakan kapitalisasi; batas panjang ditetapkan pada schema. Karakter pencarian mengikuti semantik literal yang didokumentasikan. |
| `role` | Opsional; hanya `USER` atau `ADMIN`. |
| `is_active` | Opsional; boolean filter aktif/nonaktif. |
| `skip` | Integer minimal 0; nilai awal 0. |
| `limit` | Integer 1–100; nilai awal 20. |

Gunakan parameter query database, filter yang sama untuk data/total, dan urutan stabil `created_at DESC, id DESC`. Filter diterapkan sebelum pagination. Perubahan pencarian/filter mengembalikan halaman ke awal.

Respons rencana:

```text
status: "success"
data: ManagedUser[]
count: jumlah baris di halaman ini
total: jumlah akun sesuai filter sebelum pagination
skip: posisi halaman
limit: ukuran halaman
```

`count` sama dengan panjang `data`; `total` bukan panjang halaman. Tanpa filter, `total` menghitung semua akun; dengan filter, gunakan label **Akun ditemukan**. Jangan menambahkan total global kedua kecuali UI membutuhkannya.

Validasi UUID, role, boolean, timestamp, jumlah nonnegatif, metadata pagination, dan konsistensi daftar. Payload rusak menjadi error kontrak, bukan `{data: [], total: 0}`. Timestamp hilang/rusak tidak diganti waktu sekarang. Jangan serialisasi ORM secara umum atau mengirim hash sandi, token, nonce, string koneksi, maupun identitas Google mentah.

## 4. Rencana perubahan status akses

**Endpoint berikut juga masih rencana:**

```text
PATCH /api/v1/admin/users/{user_id}/status
```

Validasi UUID target pada parameter path `user_id`. Body hanya memuat boolean tujuan eksplisit:

```json
{"is_active": false}
```

Kebijakan tahap awal:

1. Hanya sesi admin yang masih valid boleh mengirim perubahan.
2. Target harus akun `USER`. Perubahan akun `ADMIN`, termasuk akun pelaku sendiri, ditolak backend; tombol UI bukan batas keamanan.
3. Kunci/periksa baris target dalam transaksi sebelum menilai keadaan terakhir.
4. Jika status berubah, perbarui `is_active`, `updated_at` UTC, dan naikkan `token_version` tepat sekali.
5. Jika nilai tujuan sudah sama, kembalikan keadaan yang benar tanpa menaikkan versi lagi. Permintaan ulang tidak membalik status.
6. Commit sekali; kegagalan tidak boleh menyimpan sebagian perubahan.

Respons sukses rencana memuat `status: "success"` dan `data` berisi `id`, `is_active`, serta `updated_at`. Frontend memvalidasi ID/status sesuai target. Versi sesi digunakan backend dan tidak perlu ditampilkan di tabel.

Penonaktifan membuat JWT ditolak oleh pemeriksaan akun aktif. Perubahan versi memastikan JWT lama tidak hidup lagi setelah akun diaktifkan. Ini bukan logout dari akun Google pada penyedia; login Google ke VERIDIX tetap memeriksa `is_active`.

Bedakan 401 untuk sesi tidak valid, 403 untuk hak akses/kebijakan target, 404 untuk target tidak ditemukan, validasi input, serta kegagalan database. Jangan mengubah kegagalan penyimpanan menjadi sukses atau daftar kosong.

## 5. Berkas implementasi dan berkas baru

Semua perubahan berikut **belum diterapkan oleh panduan ini**.

| Berkas | Pekerjaan yang direncanakan |
| --- | --- |
| [src/api/schemas.py](../src/api/schemas.py) | Schema item pengguna, daftar/pagination, permintaan dan respons status; batas nilai/enum. |
| [src/api/routes/admin_routes.py](../src/api/routes/admin_routes.py) | Endpoint daftar, query/agregasi/filter/total, dan transaksi status dengan `require_admin`. |
| [frontend/src/types/admin.ts](../frontend/src/types/admin.ts) | Sesuaikan `ManagedUser`; tipe respons daftar, filter, dan status sesuai schema backend. |
| `frontend/src/hooks/useAdminUsers.ts` — **baru, belum ada** | Request daftar/status, validasi respons, refresh, pagination, error, pembatalan dan pemisahan sesi melalui `apiClient` yang sudah ada. |
| [frontend/src/components/admin/UserManageTable.tsx](../frontend/src/components/admin/UserManageTable.tsx) | Hapus array/tindakan contoh; gunakan hook, konfirmasi, proses per baris, keadaan kosong/gagal, pagination dan refresh. |
| [frontend/src/app/admin/users/page.tsx](../frontend/src/app/admin/users/page.tsx) | Hubungkan konteks admin terverifikasi dan sesuaikan deskripsi dengan kemampuan nyata. |
| [frontend/src/components/shared/ConfirmDialog.tsx](../frontend/src/components/shared/ConfirmDialog.tsx) | Gunakan dialog yang ada; modifikasi hanya jika kontraknya belum cukup. |
| `tests/test_admin_users_routes.py` — **baru, belum ada** | Fixture akun/database terisolasi untuk daftar, hitungan, filter, hak akses, status dan pembatalan sesi. |
| `tests/test_admin_users.cjs` — **baru, belum ada** | Tes hook/tabel dengan mock untuk kontrak, kegagalan, pagination, penyimpanan, dan respons terlambat. |

[models.py](../src/database/models.py), [auth_deps.py](../src/core/auth_deps.py), dan [apiClient.ts](../frontend/src/lib/apiClient.ts) menjadi acuan yang dipakai ulang. Jangan menambah model, jalur token, atau klien HTTP kedua bila yang ada sudah cukup. Jika implementasi perlu mengubah kontraknya, catat alasan dan perbarui panduan.

## 6. Perilaku hook dan UI

Hook berjalan setelah sesi/role admin terverifikasi. Identitas sesi/permintaan harus melindungi data, error, loading, dan hasil mutasi. Respons admin lama atau filter lama tidak boleh mengisi konteks baru. Gunakan pembatalan dan pemeriksaan identitas sebagaimana pola [useHistory](../frontend/src/hooks/useHistory.ts); pembatalan belum tentu menghentikan respons server.

Daftar diperbarui saat dibuka, filter/pagination berubah, refresh diminta, dan setelah status disimpan. **Dinamis berarti membaca API terbaru pada pemicu tersebut, bukan pembaruan realtime otomatis.**

| Keadaan | Hasil yang harus terlihat |
| --- | --- |
| Memuat pertama kali | Indikator memuat; tanpa akun contoh atau total sementara nol. |
| Daftar berhasil kosong | Keterangan belum ada akun. |
| Pencarian berhasil kosong | Keterangan tidak ada akun sesuai pencarian/filter. |
| Gagal memuat | Pesan kegagalan dan tindakan mencoba lagi. |
| Refresh gagal setelah berhasil | Data sebelumnya hanya boleh dipertahankan dalam konteks sama, dengan penanda belum berhasil diperbarui. |
| Respons rusak | Error kontrak; tidak disamarkan sebagai kosong/default. |
| Menyimpan status | Konfirmasi dan proses per baris; cegah pengiriman berulang. |
| Penyimpanan gagal | Pertahankan status sebelumnya; jangan tampilkan sukses. |
| Simpan berhasil, refresh gagal | Nyatakan perubahan sudah dikonfirmasi tetapi daftar belum berhasil dimuat ulang. |
| Sesi berubah atau role hilang | Bersihkan data lama dan hentikan interaksi admin. |

Tampilkan role/status/tanggal dari server. Format waktu eksplisit ke `Asia/Jakarta` (WIB), konsisten dengan riwayat. Sesuaikan posisi halaman yang tidak lagi valid setelah filter/mutasi, tanpa mengganti total dengan panjang array.

Hapus atau nonaktifkan tindakan reset contoh dengan penjelasan belum tersedia. Jangan mempertahankan alert pengiriman palsu. Pengembangan reset berikutnya memerlukan pengiriman nyata, penanganan akun tanpa sandi, dan pemisahan permintaan diterima dari email terkirim. Respons umum endpoint pemulihan publik tidak membuktikan pengiriman email tertentu kepada admin.

## 7. Urutan pengembangan

1. Tetapkan sumber/arti field dan kontrak daftar/status.
2. Buat schema dan endpoint daftar dengan fixture terisolasi; periksa nol dan total.
3. Tambahkan tipe/hook frontend dengan validasi serta pemisahan sesi/permintaan.
4. Hubungkan halaman/tabel dan hilangkan data/keberhasilan contoh. Daftar dapat diselesaikan sebelum mutasi status.
5. Implementasikan endpoint status, konfirmasi, dan pembaruan setelah server mengonfirmasi.
6. Jalankan pemeriksaan relevan, uji browser memakai akun uji, lalu perbarui status implementasi dan kontrak dokumentasi.

Jangan menyentuh database pengguna melalui tes otomatis, menjalankan startup/seeding sebagai efek samping, atau memakai seluruh unittest discovery. Fitur ini tidak memerlukan eksekusi model/OCR/LOCKBOX.

## 8. Bukti penerimaan

| Skenario | Bukti yang diperlukan |
| --- | --- |
| Tanpa sesi / role USER | Daftar dan mutasi ditolak backend sesuai semantik autentikasi/otorisasi. |
| Akun lokal dan Google | Berasal dari fixture; UUID dan field sesuai database. |
| Akun tanpa analisis | Tetap terdaftar dengan nol setelah query berhasil. |
| Beberapa analisis/feedback | Hitungan per pengguna tidak terduplikasi oleh relasi feedback. |
| Filter/pagination | Data dan total memakai filter sama; urutan stabil; jumlah halaman benar. |
| Input/payload rusak | Ditolak/ditandai sebagai error kontrak; tidak menjadi sukses palsu. |
| Database/backend gagal | Tidak diganti akun contoh atau nol palsu. |
| Penonaktifan berhasil | Persisten setelah reload; versi naik sekali; JWT lama ditolak. |
| Aktivasi kembali | Dapat login ulang; JWT sebelum penonaktifan tetap ditolak. |
| Permintaan berulang | Nilai tujuan tetap sama; tidak toggle atau menaikkan versi tanpa perubahan. |
| Target ADMIN atau ID salah | Kebijakan target/ketidakhadiran diperiksa backend. |
| Mutasi gagal | Tidak ada perubahan sebagian pada status/versi; hash, identitas, role dan riwayat tetap sesuai cakupan. |
| Respons terlambat | Data/error/loading sesi atau filter lama tidak mengubah konteks baru. |
| Respons dan log | Tanpa hash sandi, credential Google, JWT, nonce, atau naskah privat. |

Ikuti pola aplikasi FastAPI kecil dan dependency override pada [test_auth_roles.py](../tests/test_auth_roles.py), bukan impor startup aplikasi utama. SQLite/mocks memeriksa kontrak dasar; klaim penguncian/transaksi bersamaan PostgreSQL memerlukan integrasi terisolasi yang sesuai. Tes frontend dengan mock DOM/HTTP tidak membuktikan browser nyata.

Berkas tes baru di bagian 5 belum ada. Jangan menganggap perintah yang merujuknya dapat dijalankan sebelum fixture/implementasi selesai. Sesudahnya, pilih tes baru, tes role relevan, dan pemeriksaan TypeScript sesuai [panduan pengembangan](PANDUAN_PENGEMBANGAN_AI.md). Catat hasil aktual, kegagalan, dan batas lingkungan secara terpisah.

## 9. Pemeliharaan dan batas selesai

[Referensi Sistem](REFERENSI_SISTEM.md) mencatat keberadaan route dan keadaan implementasi; dokumen ini memusatkan rancangan/penerimaan kelola pengguna. Setelah kode berubah, sesuaikan keduanya agar endpoint rencana tidak dianggap tersedia atau sebaliknya. Laporan audit lama tetap bertanggal.

Fitur selesai ketika daftar membaca database melalui API admin, mutasi terkonfirmasi/persisten, hak akses/sesi ditegakkan, kegagalan/kosong dibedakan, dan pemeriksaan terkait mempunyai hasil yang dicatat. Menambahkan panduan ini sendiri belum memenuhi kondisi tersebut.
