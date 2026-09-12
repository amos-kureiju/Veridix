@echo off
setlocal enabledelayedexpansion
title Scaffolding Hoax Detection TA

echo ============================================
echo   MEMBUAT STRUKTUR DI:
echo   %CD%
echo ============================================
echo.

REM ============================================
REM 1. ROOT FILES
REM ============================================
type nul > .env.example
type nul > .gitignore
type nul > README.md
type nul > requirements.txt

REM ============================================
REM 2. DATA LAYER
REM ============================================
mkdir data\raw 2>nul
mkdir data\processed 2>nul
mkdir data\uploads 2>nul
type nul > data\raw\.gitkeep
type nul > data\processed\.gitkeep
type nul > data\uploads\.gitkeep

REM ============================================
REM 3. NOTEBOOKS (Eksperimen Bab 4)
REM ============================================
mkdir notebooks 2>nul
type nul > notebooks\01_scraping_eda.ipynb
type nul > notebooks\02_preprocessing.ipynb
type nul > notebooks\03_training_bert.ipynb
type nul > notebooks\04_evaluasi_metrik.ipynb
type nul > notebooks\05_xai_lime_shap.ipynb

REM ============================================
REM 4. SAVED MODELS
REM ============================================
mkdir saved_models\indobert_focal_loss 2>nul
mkdir saved_models\tokenizer 2>nul
type nul > saved_models\indobert_focal_loss\.gitkeep
type nul > saved_models\tokenizer\.gitkeep

REM ============================================
REM 5. SRC (FastAPI + ML)
REM ============================================
mkdir src 2>nul
mkdir src\core 2>nul
mkdir src\database 2>nul
mkdir src\ml 2>nul
mkdir src\utils 2>nul
mkdir src\api 2>nul
mkdir src\api\routes 2>nul

type nul > src\__init__.py
type nul > src\main.py

type nul > src\core\__init__.py
type nul > src\core\config.py
type nul > src\core\logger.py

type nul > src\database\__init__.py
type nul > src\database\models.py
type nul > src\database\session.py

type nul > src\ml\__init__.py
type nul > src\ml\model.py
type nul > src\ml\focal_loss.py
type nul > src\ml\predictor.py
type nul > src\ml\ocr_engine.py
type nul > src\ml\explainer.py

type nul > src\utils\__init__.py
type nul > src\utils\text_cleaner.py
type nul > src\utils\political_filter.py
type nul > src\utils\pdf_generator.py

type nul > src\api\__init__.py
type nul > src\api\dependencies.py
type nul > src\api\schemas.py
type nul > src\api\routes\__init__.py
type nul > src\api\routes\predict.py
type nul > src\api\routes\feedback.py
type nul > src\api\routes\admin.py

REM ============================================
REM 6. UI STREAMLIT (fallback demo sidang)
REM ============================================
mkdir ui 2>nul
mkdir ui\components 2>nul
mkdir ui\static 2>nul
type nul > ui\app.py
type nul > ui\components\header.py
type nul > ui\components\input_section.py
type nul > ui\components\result_card.py
type nul > ui\components\lime_view.py
type nul > ui\static\.gitkeep

REM ============================================
REM 7. FRONTEND NEXT.JS
REM ============================================
set FE=frontend-hoax-detector
mkdir %FE% 2>nul
mkdir %FE%\public 2>nul
mkdir %FE%\public\logos 2>nul
mkdir %FE%\public\icons 2>nul
mkdir %FE%\src 2>nul
mkdir %FE%\src\app 2>nul
mkdir %FE%\src\app\admin 2>nul
mkdir %FE%\src\app\admin\feedback 2>nul
mkdir "%FE%\src\app\report" 2>nul
mkdir "%FE%\src\app\report\[id]" 2>nul
mkdir %FE%\src\components 2>nul
mkdir %FE%\src\components\ui 2>nul
mkdir %FE%\src\components\shared 2>nul
mkdir %FE%\src\components\detector 2>nul
mkdir %FE%\src\components\admin 2>nul
mkdir %FE%\src\hooks 2>nul
mkdir %FE%\src\lib 2>nul
mkdir %FE%\src\types 2>nul

type nul > %FE%\.env.example
type nul > %FE%\package.json
type nul > %FE%\tailwind.config.ts
type nul > %FE%\tsconfig.json
type nul > %FE%\next.config.ts

type nul > %FE%\src\app\layout.tsx
type nul > %FE%\src\app\page.tsx
type nul > "%FE%\src\app\report\[id]\page.tsx"
type nul > %FE%\src\app\admin\layout.tsx
type nul > %FE%\src\app\admin\page.tsx
type nul > %FE%\src\app\admin\feedback\page.tsx

type nul > %FE%\src\components\shared\navbar.tsx
type nul > %FE%\src\components\shared\footer.tsx
type nul > %FE%\src\components\shared\badge-status.tsx

type nul > %FE%\src\components\detector\input-mode-tabs.tsx
type nul > %FE%\src\components\detector\text-input-box.tsx
type nul > %FE%\src\components\detector\image-uploader.tsx
type nul > %FE%\src\components\detector\result-banner.tsx
type nul > %FE%\src\components\detector\lime-highlighter.tsx
type nul > %FE%\src\components\detector\feature-chart.tsx
type nul > %FE%\src\components\detector\feedback-modal.tsx

type nul > %FE%\src\components\admin\stats-cards.tsx
type nul > %FE%\src\components\admin\trend-chart.tsx
type nul > %FE%\src\components\admin\retrain-table.tsx

type nul > %FE%\src\hooks\useHoaxDetector.ts
type nul > %FE%\src\hooks\useAdminStats.ts
type nul > %FE%\src\lib\api-client.ts
type nul > %FE%\src\lib\utils.ts
type nul > %FE%\src\lib\pdf-exporter.ts
type nul > %FE%\src\types\api.ts
type nul > %FE%\src\types\detector.ts

REM ============================================
REM 8. TESTS
REM ============================================
mkdir tests 2>nul
type nul > tests\__init__.py
type nul > tests\test_predictor.py
type nul > tests\test_api.py
type nul > tests\test_political_filter.py

echo.
echo ============================================
echo   SELESAI!
echo   Semua struktur dibuat di folder ini.
echo ============================================
echo.
echo Folder : %CD%
echo.
echo Verifikasi dengan:
echo   tree /F /A
echo.
pause
endlocal