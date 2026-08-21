@echo off
title Akilli Depo Yonetim Sistemi
color 0A

set "PROJECT_DIR=%~dp0"
set "VENV_PYTHON=%PROJECT_DIR%.venv\Scripts\python.exe"

REM --- Bootstrap: create venv and install deps if missing ---
if not exist "%VENV_PYTHON%" (
    echo.
    echo [SETUP] .venv bulunamadi, olusturuluyor...
    python -m venv "%PROJECT_DIR%.venv"
    "%VENV_PYTHON%" -m pip install -r "%PROJECT_DIR%requirements.txt"
    echo.
)

echo ==================================================
echo AKILLI DEPO YONETIM SISTEMI BASLATILIYOR...
echo ==================================================
echo.
echo [1/2] Sunucu ve Veritabani (Backend) calistiriliyor...
start "Sunucu (Backend)" cmd /k "cd /d %PROJECT_DIR% && "%VENV_PYTHON%" -m uvicorn backend.main:app --port 8000"
timeout /t 3 >nul

echo [2/2] Yapay Zeka Kamerasi (CV) calistiriliyor...
start "Kamera (Yapay Zeka)" cmd /k "cd /d %PROJECT_DIR% && "%VENV_PYTHON%" cv/camera_feed.py"

echo.
echo Baslatici gorevini tamamladi. 
echo - Sitenize tarayicidan erisebilirsiniz (index.html)
echo - Sistemi kapatmak icin acilan siyah pencereleri (X) isaretinden kapatmaniz yeterlidir.
echo.
pause
