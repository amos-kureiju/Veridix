# 🛡️ TA15_Deteksi Hoaks Politik Indonesia — IndoBERT + XAI

> Sistem verifikasi berita politik berbasis **IndoBERT + Focal Loss** dengan penjelasan transparan (**Explainable AI / LIME**), dilengkapi antarmuka publik (Next.js) dan portal verifikator (Admin Dashboard).

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4-EE4C2C.svg)](https://pytorch.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Daftar Isi

- [Latar Belakang](#-latar-belakang)
- [Fitur Utama](#-fitur-utama)
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Teknologi yang Digunakan](#-teknologi-yang-digunakan)
- [Struktur Proyek](#-struktur-proyek)
- [Instalasi & Setup](#-instalasi--setup)
- [Cara Menjalankan](#-cara-menjalankan)
- [Training Model](#-training-model)
- [API Endpoints](#-api-endpoints)
- [Kontribusi](#-kontribusi)
- [Lisensi](#-lisensi)
- [Kontak](#-kontak)

---

## 🎯 Latar Belakang

Penyebaran **hoaks politik** di Indonesia meningkat signifikan setiap siklus pemilu. Model klasifikasi teks konvensional hanya memberi label *hoaks/fakta* tanpa penjelasan — menyulitkan masyarakat memverifikasi hasilnya.

Proyek ini menghadirkan solusi **end-to-end**:

1. **Deteksi otomatis** berita politik menggunakan **IndoBERT** yang di-*fine-tune* dengan **Focal Loss** untuk menangani *class imbalance*.
2. **Explainable AI (XAI)** dengan **LIME** — menyoroti kata-kata yang paling memengaruhi keputusan model.
3. **Guardrail domain politik** — menolak input non-politik (mis. resep masakan).
4. **Ekstraksi entitas politik** (lightweight NER) — mengenali tokoh & lembaga (KPU, DPR, MK, dll).
5. **Deteksi clickbait** — heuristik untuk judul sensasional (CAPSLOCK, tanda seru ganda).
6. **Human-in-the-loop** — pengguna dapat melaporkan kesalahan prediksi; admin memverifikasi & memasukkan ke *retraining pool*.

---

## ✨ Fitur Utama

### 👥 Untuk Masyarakat / Jurnalis (User)

- 🔍 **Analisis teks & gambar** — input teks berita atau upload screenshot (OCR).
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

## 🏗️ Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│                                                             │
│   Next.js (User Portal)         Streamlit (Admin Fallback)  │
│   - Detector UI                 - Analitik & Feedback       │
│   - LIME Highlighter            - Kontrol Threshold         │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP REST API (JSON)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                APPLICATION LAYER (FastAPI)                  │
│                                                             │
│   /api/v1/detect/text    /api/v1/detect/image               │
│   /api/v1/feedback       /api/v1/admin/*                    │
│                                                             │
│   - Pydantic Validation   - Rate Limiter                    │
│   - Domain Guardrail      - Error Handling                  │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  OCR PIPELINE │ │  AI MODEL     │ │  XAI ENGINE   │
│  EasyOCR      │ │  IndoBERT     │ │  LIME         │
│               │ │  + Focal Loss │ │  Explainer    │
└───────────────┘ └───────────────┘ └───────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   PERSISTENCE LAYER                         │
│                                                             │
│   SQLite/PostgreSQL                File Storage             │
│   - Prediction History             - Screenshots            │
│   - User Feedback                  - PDF Reports            │
│   - Retraining Pool                                         │
└─────────────────────────────────────────────────────────────┘
```

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
| **EasyOCR** | 1.7 | Optical Character Recognition |
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
| **Docker** | Containerization |
| **GitHub Actions** | CI/CD pipeline |
| **Pytest** | Unit & integration testing |
| **Ruff + Black** | Linting & formatting |

---

## 📁 Struktur Proyek

```
hoax-detection-ta/
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
│   ├── ml/                     # IndoBERT, Focal Loss, LIME, OCR, Trainer
│   ├── utils/                  # Helper (text cleaner, PDF gen, guardrail)
│   ├── services/               # Business logic layer
│   ├── api/                    # FastAPI routes & schemas
│   └── main.py                 # Entrypoint FastAPI
│
├── ui/                         # Streamlit (fallback demo sidang)
│   └── app.py
│
├── frontend-hoax-detector/     # Next.js App Router
│   └── src/
│       ├── app/                # Pages (user + admin)
│       ├── components/         # Atomic design components
│       ├── hooks/              # Custom React hooks
│       ├── lib/                # Utilities & API client
│       └── types/              # TypeScript interfaces
│
├── tests/                      # Unit & integration tests
├── docs/                       # Dokumentasi tambahan
├── logs/                       # Runtime logs
│
├── .env.example                # Template konfigurasi
├── .editorconfig               # Standar lintas editor
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── requirements.txt            # Dependency utama
├── requirements-train.txt      # Dependency khusus training
└── README.md
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
git clone https://github.com/username/hoax-detection-ta.git
cd hoax-detection-ta
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
cd frontend-hoax-detector
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
cd frontend-hoax-detector
npm run dev
```
Buka: http://localhost:3000

**Terminal 3 — Streamlit (Fallback Demo):**
```bash
streamlit run ui/app.py
```
Buka: http://localhost:8501

### Mode Production (Docker)

```bash
docker compose up --build
```

---

## 🎓 Training Model

### Di Laptop Lokal

```bash
# Siapkan data di data/processed/ (train.csv, val.csv, test.csv)
python -m src.ml.trainer --config default --epochs 5 --batch-size 8 --device cpu
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
- Metric terbaik disimpan ke `saved_models/indobert_focal_loss/best_model.pt`

---

## 🌐 API Endpoints

### Public

| Method | Endpoint | Deskripsi |
|---|---|---|
| `GET` | `/` | Info API |
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/detect/text` | Deteksi teks berita |
| `POST` | `/api/v1/detect/image` | Deteksi dari gambar (OCR) |
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

### Contoh Response

```json
{
  "status": "success",
  "data": {
    "is_political": true,
    "prediction": "HOAX",
    "confidence_score": 0.934,
    "inference_time_seconds": 1.42,
    "entities_detected": ["KPU"],
    "explanation": {
      "base_score": 0.51,
      "tokens": [
        {"word": "segera sebarkan", "weight": 0.62, "influence": "HOAX"},
        {"word": "KPU", "weight": -0.15, "influence": "FACT"}
      ]
    }
  }
}
```

---

## 🧪 Testing

```bash
# Semua test
pytest tests/ -v

# Test spesifik
pytest tests/test_predictor.py -v

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

## 📚 Referensi Akademik

- Devlin et al. (2019). *BERT: Pre-training of Deep Bidirectional Transformers*
- Wilie et al. (2020). *IndoNLU: Benchmark and Resources for Indonesian NLP*
- Lin et al. (2017). *Focal Loss for Dense Object Detection*
- Ribeiro et al. (2016). *"Why Should I Trust You?": Explaining the Predictions of Any Classifier* (LIME)

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah **MIT License** — lihat file [LICENSE](LICENSE) untuk detail.

---

## 📞 Kontak

**Penulis:** Nama Kamu
**Institusi:** Nama Universitas
**Program Studi:** Teknik Informatika / Ilmu Komputer
**Email:** [email@example.com](mailto:email@example.com)

**Pembimbing:**
- Dosen Pembimbing 1 — [email@example.com](mailto:email@example.com)
- Dosen Pembimbing 2 — [email@example.com](mailto:email@example.com)

---

## 🙏 Ucapan Terima Kasih

- [HuggingFace](https://huggingface.co/) — Model IndoBERT
- [IndoNLU Benchmark](https://github.com/indobenchmark/indonlu) — Dataset & benchmark
- [TurnBackHoax.id](https://turnbackhoax.id/) — Dataset hoaks Indonesia
- [shadcn/ui](https://ui.shadcn.com/) — Komponen UI
- [FastAPI](https://fastapi.tiangolo.com/) — Framework backend

---

<p align="center">
  Dibuat dengan ❤️ untuk memerangi hoaks politik Indonesia
</p>
