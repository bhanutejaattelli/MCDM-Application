@echo off
:: ─────────────────────────────────────────────────────────────
:: start_frontend.bat — Launch React frontend
:: Dynamic Cloud Service Composition System
:: ─────────────────────────────────────────────────────────────
title MCDM React Frontend

echo.
echo  ╔═══════════════════════════════════════════════╗
echo  ║  Dynamic Cloud Service Composition System     ║
echo  ║  React Frontend →  http://localhost:5173       ║
echo  ╚═══════════════════════════════════════════════╝
echo.

cd /d "%~dp0frontend_react"

if not exist "node_modules" (
    echo [INFO] node_modules not found. Installing dependencies...
    npm install
)

echo [OK] Starting Vite Dev Server...
echo.
npm run dev

pause
