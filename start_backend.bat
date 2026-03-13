@echo off
:: ─────────────────────────────────────────────────────────────
:: start_backend.bat  — Launch Flask API server
:: Dynamic Cloud Service Composition System
:: ─────────────────────────────────────────────────────────────
title MCDM Flask Backend

echo.
echo  ╔═══════════════════════════════════════════════╗
echo  ║  Dynamic Cloud Service Composition System     ║
echo  ║  Flask Backend  →  http://localhost:5000      ║
echo  ╚═══════════════════════════════════════════════╝
echo.

:: Change to project root (wherever this .bat lives)
cd /d "%~dp0"

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated.
) else (
    echo [WARN] No venv found — using system Python.
)

:: Check .env exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo         Copy .env.example to .env and fill in your Firebase credentials.
    pause
    exit /b 1
)

:: Check firebase_credentials.json exists
if not exist "firebase_credentials.json" (
    echo [ERROR] firebase_credentials.json not found!
    echo         Download your service account key from Firebase Console.
    pause
    exit /b 1
)

echo [OK] Starting Flask on port 5000...
echo.
python backend\app.py

pause
