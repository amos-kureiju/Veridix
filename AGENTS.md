# Instruksi Kerja dan Integritas VERIDIX

Diperbarui: **13 November 2026**. Berlaku untuk repositori ini.

VERIDIX mendeteksi kemiripan pola bahasa dengan klaim politik Indonesia yang dilabeli hoaks pada korpus penelitian. Hasilnya bukan pembuktian kebenaran berita. Dokumen membantu menjaga konsistensi kerja; kode dan pengujian tetap harus menegakkan aturannya.

## 1. Mulai dari dokumen yang relevan

| Kebutuhan | Acuan |
| --- | --- |
| Memilih solusi, memperbaiki fitur, dan menentukan pemeriksaan | [Panduan Pengembangan AI](docs/PANDUAN_PENGEMBANGAN_AI.md) |
| Memeriksa arsitektur, relasi, API, status, dan model | [Referensi Sistem](docs/REFERENSI_SISTEM.md) |
| Detail/hapus riwayat dan pengujiannya | [Panduan Riwayat](docs/PANDUAN_RIWAYAT.md) |
| Alur dan evaluasi OCR | [Panduan Pengujian OCR](docs/PANDUAN_PENGUJIAN_OCR.md) |
| Metodologi, pembagian data, dan evaluasi final | [Protokol penelitian](PROTOKOL_PRAREGISTRASI.md) |
| Menelusuri temuan/angka audit lama | [Catatan Audit Dokumentasi](reports/CATATAN_AUDIT_DOKUMENTASI_2026-11-13.md) |

Baca acuan sesuai tugas, lalu periksa jalur kode aktif. Referensi implementasi, laporan bertanggal, dan rencana mempunyai kedudukan berbeda. Jika bertentangan, jelaskan perbedaannya; jangan menjadikan snapshot lama sebagai keadaan terbaru.

## 2. Ruang lingkup dan keputusan

- Ikuti instruksi pengguna. Jika diminta memeriksa saja, jangan mengubah kode.
- Untuk pekerjaan yang sudah diotorisasi, lanjutkan secara mandiri tanpa menambahkan persetujuan yang tidak diperlukan.
- Periksa status Git dan pertahankan perubahan pengguna. Jangan menimpa pekerjaan lain.
- Telusuri kebutuhan -> komponen -> API/schema -> sumber data -> hasil pengguna sebelum memutuskan.
- Pilih perubahan terkecil yang menyelesaikan alur lengkap. Gunakan pola yang ada; tambah berkas, dependensi, atau abstraksi hanya untuk kebutuhan konkret.
- Perubahan UI/API tidak menjadi alasan mengganti algoritma, checkpoint, aturan voting, atau dataset.

## 3. Aturan yang wajib dipertahankan

1. **Sumber nyata.** Jangan mengarang data akun, angka, progres, latensi, grafik, atau keberhasilan. Mode demo harus jelas dan terpisah.
2. **Nilai yang tepat.** Bedakan nol/False yang terukur, nilai tidak tersedia, hasil kosong yang sah, dan kegagalan. Payload rusak tidak boleh menjadi sukses atau angka nol.
3. **Kontrak yang terbukti.** Periksa endpoint, metode, field, enum, nullability, dan hak akses. Jangan menganggap kontrak tersedia karena frontend memanggilnya.
4. **Makna hasil.** Kesepakatan seed bukan probabilitas atau akurasi. Label tidak berpola hoaks bukan bukti fakta. LIME menunjukkan pengaruh lokal pada fungsi skor yang dijelaskan.
5. **Kegagalan terlihat.** Bedakan input ditolak, di luar domain, kegagalan komputasi, dan kegagalan layanan/database. Jangan membuat label/konsensus saat model tidak menilai.
6. **Masukan yang jelas.** Kaitkan hasil dengan input asal dan jelaskan pemotongan. Pengukuran pemotongan yang gagal berarti belum diketahui, bukan pasti utuh.
7. **Konteks akun.** Backend memeriksa identitas, pemilik, dan role. Respons akun/permintaan lama tidak boleh mengisi konteks yang baru.
8. **Penyimpanan yang nyata.** Tampilkan sukses setelah server mengonfirmasi. Koreksi pengguna/review admin tidak menimpa keputusan asli model atau otomatis melatih ulang.
9. **Integritas artefak.** Jangan mengganti hash pembanding atau memakai VERIDIX_ALLOW_UNVERIFIED hanya untuk meloloskan pemeriksaan. Perubahan artefak/config perlu alasan, identitas, dan evaluasi yang sesuai.
10. **Akses bersama aman.** Pemakaian tokenizer atau keadaan model bersama harus disinkronkan secara konsisten, termasuk diagnostik dan LIME.
11. **Privasi.** Jangan log token, kata sandi, string koneksi, badan permintaan, atau naskah privat. Simpan data minimum; jangan membuat arsip tersembunyi untuk menghindari penghapusan.
12. **Bukti jujur.** Simpan hasil buruk/parsial. Jangan memotong koefisien atau memilih denominator/hasil hanya agar metrik terlihat lebih baik.

## 4. Batas penelitian

- Gunakan dataset dan manifest yang ditetapkan protokol; trial/salinan/arsip bukan otomatis dataset final.
- Pertahankan peran train, validation, development, dan lockbox. Feedback tidak otomatis menjadi data latih atau masuk ke dev-test/lockbox beku.
- Dalam pekerjaan rutin, jangan membaca, menyampel, mengunggah, atau menjalankan isi LOCKBOX. Evaluasi final hanya dalam ruang lingkup yang secara eksplisit mencakupnya dan mengikuti protokol/adendum.
- Jangan mengulang evaluasi final atau mengubah kriteria setelah melihat hasil lalu menyebutnya keputusan awal. Catat penyimpangan dan adendum dengan tanggal sebenarnya.
- Bedakan tes perangkat lunak, hash artefak, akurasi model, reproduksibilitas, stabilitas LIME, dan kualitas OCR. Satu contoh atau tes mock tidak membuktikan generalisasi.

## 5. Verifikasi dan penutupan pekerjaan

- Pilih pemeriksaan yang relevan sesuai [panduan pengembangan](docs/PANDUAN_PENGEMBANGAN_AI.md). Periksa fixture sebelum menjalankan tes.
- Gunakan data/akun uji terisolasi. Jangan menyentuh database pengguna melalui pengujian otomatis.
- Jangan memakai seluruh unittest discover untuk pemeriksaan rutin: tests/test_api.py dapat memakai koneksi aplikasi nyata. Jangan menjalankan startup/seeding/LOCKBOX sebagai efek samping tes.
- Laporkan perubahan, alasan, tes yang benar-benar dijalankan, kegagalan, dan batas verifikasi. Bedakan mock/SQLite, tokenizer, checkpoint, browser, serta database nyata.
- Perbarui dokumen yang menjadi sumber utama ketika kontrak berubah. Hasil audit lama tetap bertanggal; jangan menyalinnya sebagai status aktif.

Fitur selesai pada cakupannya ketika sumber data, kontrak, hak akses, perilaku UI, dan pemeriksaan terkait selaras. Menambahkan dokumen tidak otomatis memperbaiki implementasi.
