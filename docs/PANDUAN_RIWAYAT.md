# Detail dan penghapusan riwayat pengguna

Perubahan fitur: 10 November 2026.

## Alur data

`Unggah gambar → OCR → editor → analisis teks → prediction_logs → riwayat → detail/hapus`.

Unggah/OCR tidak membuat entri riwayat. Setelah pengguna menekan analisis, endpoint deteksi teks menyimpan teks editor terakhir beserta sumber `IMAGE` atau `TEXT`. Membuka detail membaca hasil yang sudah tersimpan; tidak menghitung ulang prediksi atau LIME.

## Berkas yang terkait

| Berkas | Tanggung jawab |
|---|---|
| `frontend/src/app/history/page.tsx` | Daftar, pencarian/filter, ekspor, detail lengkap, konfirmasi dan hasil penghapusan. |
| `frontend/src/hooks/useHistory.ts` | Request daftar/detail/hapus, pembaruan tampilan, pembatalan request dan pemisahan sesi. |
| `frontend/src/types/detector.ts` | Kontrak data riwayat dan metadata detail/feedback. |
| `frontend/src/components/shared/ConfirmDialog.tsx` | Dialog konfirmasi dengan status proses dan pesan kegagalan. |
| `src/api/routes/user_routes.py` | Membatasi pembacaan/penghapusan pada pemilik serta transaksi database. |
| `src/ml/inference.py` | Menyertakan konsensus suara seed pada hasil inferensi baru. |
| `src/api/routes/detection_routes.py` | Jalur penyimpanan teks final, sumber dan hasil analisis yang sudah ada. |
| `src/database/models.py` | Kolom riwayat dan hubungan feedback yang sudah ada. |

## Kontrak API

Seluruh endpoint memakai autentikasi pengguna.

| Metode dan endpoint | Hasil |
|---|---|
| `GET /api/v1/users/history?limit=50&offset=0` | Daftar milik pengguna, terbaru dahulu. Batas `limit` 1–100, `offset` minimal 0. |
| `GET /api/v1/users/history/{id}` | Teks lengkap, sumber, waktu, topik, status, verdict, konsensus, latensi, narasi, entitas, LIME yang sudah tersimpan dan feedback milik pengguna. |
| `DELETE /api/v1/users/history/{id}` | Menghapus riwayat beserta feedback terkait dalam satu transaksi. |

Respons sukses memakai `{ "status": "success", "data": ... }`; hasil hapus memuat `data.id`. ID yang tidak ada dan ID milik akun lain sama-sama menghasilkan 404. Pengunjung tanpa autentikasi menerima 401. Jika transaksi gagal, riwayat dan feedback tidak boleh terhapus sebagian.

Antarmuka menampilkan riwayat terbaru yang dimuat dari endpoint; pencarian, filter dan CSV berlaku pada data yang dimuat. Jangan menafsirkan angka pada layar sebagai jumlah seluruh data database jika melebihi batas daftar.

## Interpretasi data

- `input_text` adalah teks yang benar-benar dikirim untuk analisis setelah penyuntingan. Isi naskah, termasuk kutipan atau judul di dalamnya, dipertahankan.
- Sumber `IMAGE` berarti masukan berasal dari jalur gambar. Ini tidak membuktikan gambar asli disimpan; `image_url` bisa kosong.
- Konsensus dihitung `max(suara_hoaks, jumlah_seed - suara_hoaks) / jumlah_seed`. Untuk tiga seed, 3:0 berarti 100% dan 2:1 berarti sekitar 66,7%. Angka ini menyatakan kesepakatan keputusan model, bukan peluang kebenaran berita.
- Nilai konsensus riwayat lama yang kosong tetap kosong. Nilai ini tidak dapat direkonstruksi dari label saja. Analisis baru dapat menyimpannya melalui kolom yang sudah tersedia.
- Status `ambigu` tetap perlu verifikasi. Status penolakan/di luar domain tidak memiliki verdict biner atau konsensus, meskipun baris lama menyimpan label yang tidak sesuai.
- Narasi, LIME, entitas dan metadata feedback ditampilkan sesuai data tersimpan. Ketidakhadiran informasi ditandai dengan jelas; membuka detail tidak menjalankan ulang mesin.

## Pengujian otomatis

Jalankan dari root proyek di PowerShell:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_history_routes tests.test_history_detection_flow tests.test_reporting_integrity -v
.\.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_consensus_metadata tests.test_ocr_routes tests.test_ocr_cli tests.test_ocr_evaluation -v
node --test tests/test_history_page.cjs tests/test_frontend_guest_access.cjs tests/test_frontend_ocr.cjs tests/test_ocr_hook.cjs tests/test_verdict_feedback.cjs
node frontend/node_modules/typescript/bin/tsc --noEmit --incremental false -p frontend/tsconfig.json
```

Tes database memakai SQLite memori dan akun sementara. OCR/inferensi pada tes alur memakai mesin tiruan. Hasil ini memeriksa kontrak dan integrasi kode; hasilnya tidak menggantikan pengujian browser, kualitas OCR atau akurasi model sebenarnya.

## Pemeriksaan melalui browser

1. Jalankan ulang backend dengan kode terbaru dan buka `/history` setelah login.
2. Klik **Detail** pada riwayat lama. Cocokkan ID, teks lengkap, sumber, waktu dan verdict dengan database. Konsensus lama yang kosong harus ditandai belum tersedia.
3. Unggah gambar jelas, koreksi teks di editor lalu analisis. Cocokkan teks final dan sumber `IMAGE` pada respons, daftar dan detail. Periksa konsensus hasil baru.
4. Jika penjelasan LIME sudah diminta/disimpan, buka detail lagi dan periksa kesesuaiannya. Periksa juga catatan feedback dan tinjauan admin bila tersedia.
5. Uji pencarian, filter, CSV dan refresh. Nilai yang tidak tersedia tidak boleh berubah menjadi nol atau angka contoh.
6. Gunakan satu entri akun uji: pilih **Hapus**, uji **Batal**, lalu konfirmasi. Setelah sukses, entri dan feedback terkait harus hilang setelah refresh dan hitungan profil mengikuti database. Penghapusan ini permanen.
7. Uji kegagalan koneksi serta pergantian akun. Tombol proses tidak boleh mengirim permintaan berulang; kegagalan harus terlihat dan respons sesi sebelumnya tidak boleh mengisi riwayat akun baru. Detail/hapus ID akun lain harus ditolak backend.

Catat hasil browser terpisah dari hasil tes otomatis, beserta tanggal, commit, akun uji dan ID entri uji. Jangan mencantumkan kata sandi atau token dalam laporan.
