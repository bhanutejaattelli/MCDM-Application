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

cd /d "%~dp0"

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated.
)

:: Check .env exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo         Ensure you have a .env file with your Firebase variables.
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

:: Set Flask entry point and run
set FLASK_APP=backend/app.py
set FLASK_ENV=development
set FLASK_DEBUG=1
set FLASK_PORT=5000

flask run --host=0.0.0.0 --port=5000

pause
