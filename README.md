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
- 🎨 **Visualisasi XAI** — highlight kata pemicu hoaks dengan intensitas warna.
- 📊 **Skor kepercayaan** — persentase probabilitas hoaks (0–100%).
- 📄 **Unduh laporan PDF** — bukti verifikasi formal untuk klarifikasi publik.
- 🚩 **Laporkan ketidaksesuaian** — feedback untuk perbaikan model.

### 🛡️ Untuk Verifikator / Admin

- 📈 **Dashboard analitik** — total cek, rasio hoaks, rata-rata latensi.
- 📉 **Tren kata kunci 30 hari** — pantau isu politik terkini (Pilpres, MK, KPU, dll).
- ✅ **Review feedback pengguna** — verifikasi laporan koreksi.
- 🔄 **Retraining pool** — kelola data baru untuk mengatasi *temporal shift*.
- ⚙️ **Kontrol threshold** — atur ambang sensitivitas deteksi (0–100%).

---

## 🧰 Teknologi yang Digunakan

### Backend & ML

| Teknologi | Versi | Fungsi |
|---|---|---|
| **Python** | 3.10+ | Bahasa utama |
| **FastAPI** | 0.115 | REST API framework |
| **Uvicorn** | 0.30 | ASGI server |
| **PyTorch** | 2.4 | Deep learning framework |
| **Transformers** | 4.44 | IndoBERT (HuggingFace) |
| **LIME** | 0.2 | Explainable AI |
| **SQLAlchemy** | 2.0 | ORM database |
| **Pydantic** | 2.9 | Data validation |

### Frontend

| Teknologi | Versi | Fungsi |
|---|---|---|
| **Next.js** | 15 | React framework (App Router) |
| **TypeScript** | 5.x | Type safety |
| **Tailwind CSS** | 3.x | Utility-first styling |
| **shadcn/ui** | latest | UI components |
| **Recharts** | 2.x | Data visualization |

### DevOps & Tools

| Teknologi | Fungsi |
|---|---|
| **Google Colab** | Eksperimen training gratis dengan GPU T4 |
| **NVIDIA Data Center** | Training skala besar (opsional) |
| **Docker** | Containerization |
| **GitHub Actions** | CI/CD pipeline |
| **Pytest** | Unit & integration testing |
| **Ruff + Black** | Linting & formatting |

---

## 📁 Struktur Proyek

```
veridix/
│
├── data/                       # Dataset (raw, processed, uploads)
├── notebooks/                  # Eksperimen riset (Bab 4 skripsi)
│   ├── 01_scraping_eda.ipynb
│   ├── 02_preprocessing.ipynb
│   ├── 03_training_bert.ipynb
│   ├── 04_evaluasi_metrik.ipynb
│   └── 05_xai_lime_shap.ipynb
│
├── saved_models/               # Checkpoint model (production)
│   ├── indobert_focal_loss/
│   └── tokenizer/
│
├── scripts/                    # Deployment & ops scripts
│   ├── run_train_server.sh
│   ├── setup_server.sh
│   └── sync_to_server.bat
│
├── src/                        # SOURCE CODE BACKEND
│   ├── core/                   # Config & logging
│   ├── database/               # ORM models & session
│   ├── ml/                     # IndoBERT, Focal Loss, LIME, Trainer
│   ├── utils/                  # Helper (preprocessor, guardrail, PDF)
│   ├── api/                    # FastAPI routes & schemas
│   └── main.py                 # Entrypoint FastAPI
│
├── frontend/                   # Next.js App Router
│   └── src/
│       ├── app/                # Pages (user + admin)
│       ├── components/         # Atomic design components
│       ├── hooks/              # Custom React hooks
│       ├── lib/                # Utilities & API client
│       └── types/              # TypeScript interfaces
│
├── tests/                      # Unit & integration tests
│
├── .env.example                # Template konfigurasi
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt            # Dependency utama
└── requirements-train.txt      # Dependency khusus training
```

---

## ⚙️ Instalasi & Setup

### Prasyarat

- **Python** ≥ 3.10
- **Node.js** ≥ 20 (untuk frontend)
- **Git**
- (Opsional) **CUDA GPU** untuk training

### 1. Clone Repositori

```bash
git clone https://github.com/username/veridix.git
cd veridix
```

### 2. Setup Backend (Python)

```bash
# Buat virtual environment
python -m venv .venv

# Aktifkan
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Konfigurasi Environment

```bash
copy .env.example .env     # Windows
cp .env.example .env       # Linux/macOS
```

Edit `.env` sesuai kebutuhan (path model, threshold, DB URL).

### 4. Setup Frontend (Next.js)

```bash
cd frontend
npm install
cd ..
```

---

## 🚀 Cara Menjalankan

### Mode Development

**Terminal 1 — Backend API:**
```bash
uvicorn src.main:app --reload --port 8000
```
Buka: http://localhost:8000/docs

**Terminal 2 — Frontend Next.js:**
```bash
cd frontend
npm run dev
```
Buka: http://localhost:3000

---

## 🎓 Training Model

### Di Laptop Lokal / Google Colab

```bash
# Siapkan data di data/processed/ (train.csv, val.csv, test.csv)
python -m src.ml.train_model --config default --epochs 5 --batch-size 8 --device cpu
```

### Di Server GPU (SSH)

```bash
# 1. Setup server sekali saja
bash scripts/setup_server.sh

# 2. Sync dari Windows
scripts\sync_to_server.bat

# 3. Jalankan training di background (anti broken pipe)
bash scripts/run_train_server.sh

# 4. Pantau progress
tail -f saved_models/indobert_focal_loss/logs/train_*.log
```

### Metrik Evaluasi

- **Macro F1-Score** — metrik utama (mengatasi imbalance)
- **Precision, Recall** per kelas
- **Confusion Matrix**
- **ROC-AUC**

### Early Stopping

- Patience: **3 epoch**
- Model terbaik disimpan ke `saved_models/indobert_focal_loss/best_model.pt`

---

## 🌐 API Endpoints

### Public

| Method | Endpoint | Deskripsi |
|---|---|---|
| `GET` | `/` | Info API |
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/detect/text` | Deteksi teks berita |
| `POST` | `/api/v1/feedback` | Kirim feedback koreksi |

### Admin

| Method | Endpoint | Deskripsi |
|---|---|---|
| `GET` | `/api/v1/admin/stats` | Statistik dashboard |
| `GET` | `/api/v1/admin/retrain-pool` | Data antrean retraining |

### Contoh Request

```bash
curl -X POST http://localhost:8000/api/v1/detect/text \
  -H "Content-Type: application/json" \
  -d '{"text": "GEMPAR!! KPU resmi membatalkan hasil pemilu, segera sebarkan!"}'
```

---

## 🧪 Testing

```bash
# Semua test
pytest tests/ -v

# Test spesifik
pytest tests/test_inference.py -v

# Coverage
pytest --cov=src tests/
```

---

## 🤝 Kontribusi

Kontribusi sangat diterima! Ikuti langkah berikut:

1. **Fork** repositori ini
2. Buat **branch fitur**: `git checkout -b feat/nama-fitur`
3. **Commit** perubahan: `git commit -m "feat: tambah fitur X"`
4. **Push** ke branch: `git push origin feat/nama-fitur`
5. Buat **Pull Request**

### Konvensi Commit

Kami mengikuti [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` fitur baru
- `fix:` perbaikan bug
- `docs:` perubahan dokumentasi
- `refactor:` refactor kode
- `test:` tambah/ubah test
- `chore:` tooling & setup

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah **MIT License** — lihat file [LICENSE](LICENSE) untuk detail.

---

<div align="center">

**Veridix © 2026**

Dibuat dengan ❤️ untuk memerangi hoaks politik Indonesia

_God's Plan_ ✨

</div>
