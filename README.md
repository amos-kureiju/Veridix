<div align="center">

<img src="frontend/public/logo.png" alt="Veridix Logo" width="160" />

# 🛡️ Veridix — Deteksi Hoaks Politik Indonesia

### IndoBERT + XAI + LIME

> Sistem verifikasi berita politik berbasis **Fine-Tuning IndoBERT + Focal Loss** dengan penjelasan transparan (**Explainable AI / LIME**), dilengkapi antarmuka publik (Next.js) dan portal verifikator (Admin Dashboard).

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4-EE4C2C.svg)](https://pytorch.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📖 Daftar Isi

- [Latar Belakang](#-latar-belakang)
- [Fitur Utama](#-fitur-utama)
- [Teknologi yang Digunakan](#-teknologi-yang-digunakan)
- [Struktur Proyek](#-struktur-proyek)
- [Instalasi & Setup](#-instalasi--setup)
- [Cara Menjalankan](#-cara-menjalankan)
- [Training Model](#-training-model)
- [API Endpoints](#-api-endpoints)
- [Testing](#-testing)
- [Kontribusi](#-kontribusi)
- [Lisensi](#-lisensi)

---

## 🎯 Latar Belakang

Penyebaran **hoaks politik** di Indonesia meningkat signifikan setiap siklus pemilu. Model klasifikasi teks konvensional hanya memberi label *hoaks/fakta* tanpa penjelasan — menyulitkan masyarakat memverifikasi hasilnya.

**Veridix** hadir sebagai solusi **end-to-end**:

1. **Deteksi otomatis** berita politik menggunakan **IndoBERT** yang di-*fine-tune* dengan **Focal Loss** untuk menangani *class imbalance*.
2. **Explainable AI (XAI)** dengan **LIME** — menyoroti kata-kata yang paling memengaruhi keputusan model.
3. **Guardrail domain politik** — menolak input non-politik menggunakan kamus leksikal entitas politik (KPU, DPR, MK, dll).
4. **Deteksi clickbait** — heuristik untuk judul sensasional (CAPSLOCK, tanda seru ganda).
5. **Human-in-the-loop** — pengguna dapat melaporkan kesalahan prediksi; admin memverifikasi & memasukkan ke *retraining pool*.

---

## ✨ Fitur Utama

### 👥 Untuk Masyarakat / Jurnalis (User)

- 🔍 **Analisis teks berita** — input teks langsung, minimal 30 karakter.
- 🖼️ **Analisis tangkapan layar** — ekstraksi teks gambar otomatis berbasis PaddleOCR.
- 🎨 **Visualisasi XAI** — highlight kata pemicu hoaks dengan intensitas warna LIME.
- 📊 **Skor keyakinan** — persentase probabilitas hoaks (0–100%).
- 🚩 **Laporkan ketidaksesuaian** — feedback koreksi untuk perbaikan model.

### 🛡️ Untuk Verifikator / Admin

- 📈 **Dashboard analitik riil** — total cek, rasio hoaks harian, dan metrik sistem.
- 📋 **Riwayat log inferensi** — audit trail seluruh aktivitas deteksi di database.
- ⚙️ **Kontrol threshold AI** — atur ambang batas sensitivitas klasifikasi hoaks secara dinamis.
- ✅ **Review feedback pengguna** — verifikasi sanggahan dan laporan masyarakat.

---

## 🧰 Teknologi yang Digunakan

### Backend & ML

| Teknologi | Versi | Fungsi |
|---|---|---|
| **Python** | 3.10+ | Bahasa utama backend |
| **FastAPI** | 0.115 | REST API framework |
| **Uvicorn** | 0.30+ | ASGI production server |
| **PyTorch** | 2.4+ | Deep learning framework |
| **Transformers** | 4.44+ | Model IndoBERT (HuggingFace) |
| **LIME** | 0.2+ | Explainable AI (Local Interpretable Model-agnostic Explanations) |
| **SQLAlchemy** | 2.0+ | ORM database (SQLite lokal / PostgreSQL Supabase) |
| **Pydantic** | 2.9+ | Skema validasi data request/response |
| **Bcrypt / Jose** | Latest | Enkripsi kata sandi & JWT Bearer token |

### Frontend

| Teknologi | Versi | Fungsi |
|---|---|---|
| **Next.js** | 15 | React framework (App Router) |
| **TypeScript** | 5.x | Type safety |
| **Tailwind CSS** | 3.x | Utility-first styling |
| **Lucide Icons** | Latest | Iconography modern |

---

## 📁 Struktur Proyek

```
veridix/
│
├── data/                       # Dataset (raw, processed, uploads)
├── notebooks/                  # Eksperimen riset (Bab 4 skripsi)
├── saved_models/               # Checkpoint model (production)
├── scripts/                    # Deployment, seeder, & ops scripts
│   ├── init_admin.py           # Inisialisasi akun Super Admin
│   └── seed_demo_users.py      # Seeder akun demo
│
├── src/                        # SOURCE CODE BACKEND
│   ├── core/                   # Config, security (bcrypt/JWT), & auth deps
│   ├── database/               # ORM models & session database
│   ├── ml/                     # IndoBERT, Focal Loss, LIME, Inference pipeline
│   ├── utils/                  # Helper (preprocessor, guardrail, OCR)
│   └── api/                    # FastAPI routes & schemas
│       ├── routes/             # detection, auth, user, feedback, admin
│       ├── dependencies.py     # Dependency injection (get_current_user, get_current_admin)
│       └── schemas.py          # Skema Pydantic request & response
│
├── main.py                     # Entrypoint aplikasi FastAPI
├── frontend/                   # Next.js App Router (User & Admin UI)
├── tests/                      # Unit & integration tests
│   └── test_api.py             # Test suite alur API, deteksi, DB, & auth
│
├── .env.example                # Template konfigurasi environment
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt            # Dependency backend
```

---

## ⚙️ Instalasi & Setup

### Prasyarat

- **Python** ≥ 3.10
- **Node.js** ≥ 20 (untuk frontend)
- **Git**

### 1. Clone Repositori

```bash
git clone https://github.com/Septianhutasoit/HoaxLeenss_15.git
cd HoaxLeenss_15
```

### 2. Setup Backend (Python)

```bash
# Buat virtual environment
python -m venv .venv

# Aktifkan virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies backend
pip install -r requirements.txt
```

### 3. Konfigurasi Environment (.env)

Salin file template `.env.example` menjadi `.env`:

```bash
copy .env.example .env     # Windows
cp .env.example .env       # Linux/macOS
```

Daftar variabel penting pada `.env`:

| Variabel | Deskripsi | Nilai Default |
|---|---|---|
| `DATABASE_URL` | String koneksi SQLite lokal atau PostgreSQL Supabase | `sqlite:///./hoax_inspect.db` |
| `JWT_SECRET_KEY` | Kunci rahasia penandatanganan token JWT | `VERIDIX_POLITICAL_AI_SECRET_KEY_2026` |
| `DEFAULT_HOAX_THRESHOLD` | Ambang batas sensitivitas klasifikasi hoaks (0.0 - 1.0) | `0.60` |
| `CORS_ORIGINS` | Daftar domain frontend yang diizinkan mengakses API | `["http://localhost:3000","http://127.0.0.1:3000"]` |

### 4. Setup Frontend (Next.js)

```bash
cd frontend
npm install
cd ..
```

---

## 🚀 Cara Menjalankan

### Mode Development

**Terminal 1 — Backend API (FastAPI):**
```bash
uvicorn main:app --reload --port 8000
```
> **Akun Demo Bawaan:** Saat backend pertama kali dijalankan, sistem secara otomatis melakukan inisialisasi tabel dan seeding akun demo:
> - **Administrator:** `admin@veridix.id` | Kata Sandi: `admin123`
> - **Pengguna Publik:** `amos@veridix.id` | Kata Sandi: `password123`

Swagger UI interaktif: [http://localhost:8000/docs](http://localhost:8000/docs)

**Terminal 2 — Frontend (Next.js):**
```bash
cd frontend
npm run dev
```
Buka antarmuka aplikasi di browser: [http://localhost:3000](http://localhost:3000)

---

## 🌐 API Endpoints

Aplikasi backend berjalan pada port `8000`. Dokumentasi interaktif Swagger UI tersedia di [http://localhost:8000/docs](http://localhost:8000/docs).

### 1. Jalur Deteksi Berita Politik (`/api/v1/detect`)

| Method | Endpoint | Deskripsi | Akses |
|---|---|---|---|
| `POST` | `/api/v1/detect/text` | Deteksi teks naskah politik (IndoBERT + XAI LIME) | Publik / Tamu |
| `POST` | `/api/v1/detect/image` | Ekstraksi & pembersihan teks tangkapan layar (PaddleOCR) | Publik / Tamu |

### 2. Autentikasi Pengguna (`/api/v1/auth`)

| Method | Endpoint | Deskripsi | Akses |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Pendaftaran akun masyarakat/jurnalis baru | Publik |
| `POST` | `/api/v1/auth/login` | Masuk akun & penerbitan Bearer JWT Token | Publik |
| `GET` | `/api/v1/auth/me` | Mengambil data sesi dan profil pengguna aktif | Bearer Token |
| `POST` | `/api/v1/auth/direct-reset-password` | Atur ulang kata sandi akun | Publik |

### 3. Profil Pengguna (`/api/v1/user`)

| Method | Endpoint | Deskripsi | Akses |
|---|---|---|---|
| `PATCH` | `/api/v1/user/profile` | Perbarui nama dan avatar profil | Bearer Token |
| `POST` | `/api/v1/user/change-password` | Ganti kata sandi akun | Bearer Token |
| `DELETE` | `/api/v1/user/delete-account` | Hapus akun secara permanen | Bearer Token |

### 4. Umpan Balik Pengguna (`/api/v1/feedback`)

| Method | Endpoint | Deskripsi | Akses |
|---|---|---|---|
| `POST` | `/api/v1/feedback/submit` | Kirim sanggahan/koreksi terhadap hasil deteksi | Publik / User |

### 5. Portal Verifikator / Admin (`/api/v1/admin`)

| Method | Endpoint | Deskripsi | Akses |
|---|---|---|---|
| `GET` | `/api/v1/admin/stats` | Statistik monitoring riil (total deteksi, rasio hoaks, user aktif) | Admin |
| `GET` | `/api/v1/admin/logs/recent` | Riwayat log inferensi riil yang tersimpan di database | Admin |
| `POST` | `/api/v1/admin/threshold` | Kontrol dinamis ambang batas sensitivitas AI | Admin |

### Contoh Request Deteksi Teks

```bash
curl -X POST http://localhost:8000/api/v1/detect/text \
  -H "Content-Type: application/json" \
  -d '{"text": "KPU RI secara resmi mengumumkan jadwal pelaksanaan tahapan pemilu serentak dan pilpres tahun depan."}'
```

---

## 🧪 Testing

Jalankan test suite backend untuk memvalidasi alur deteksi, validasi guardrail politik, persistensi database, dan autentikasi:

```bash
# Jalankan test suite bawaan Python
python -m unittest tests/test_api.py -v

# Atau menggunakan pytest (bila terinstal)
pytest tests/ -v
```

---

## 🤝 Kontribusi

Kontribusi sangat diterima! Ikuti langkah berikut:

1. **Fork** repositori ini
2. Buat **branch fitur**: `git checkout -b feat/nama-fitur`
3. **Commit** perubahan: `git commit -m "feat: tambah fitur X"`
4. **Push** ke branch: `git push origin feat/nama-fitur`
5. Buat **Pull Request**

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah **MIT License** — lihat file [LICENSE](LICENSE) untuk detail.

---

<div align="center">

**Veridix © 2026**

Dibuat dengan ❤️ untuk memerangi hoaks politik Indonesia

_God's Plan_ ✨

</div>
