@echo off
:: ─────────────────────────────────────────────────────────────
:: start_frontend.bat — Launch Streamlit frontend
:: Dynamic Cloud Service Composition System
:: ─────────────────────────────────────────────────────────────
title MCDM Streamlit Frontend

echo.
echo  ╔═══════════════════════════════════════════════╗
echo  ║  Dynamic Cloud Service Composition System     ║
echo  ║  Streamlit UI  →  http://localhost:8501       ║
echo  ╚═══════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated.
) else (
    echo [WARN] No venv found — using system Python.
)

echo [OK] Starting Streamlit...
echo.
streamlit run frontend\streamlit_app.py --server.port 8501 --server.headless false

pause
