@echo off
title Akilli Depo Yonetim Sistemi
color 0A
echo ==================================================
echo AKILLI DEPO YONETIM SISTEMI BASLATILIYOR...
echo ==================================================
echo.
echo [1/2] Sunucu ve Veritabani (Backend) calistiriliyor...
start "Sunucu (Backend)" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --port 8000"
timeout /t 3 >nul

echo [2/2] Yapay Zeka Kamerasi (CV) calistiriliyor...
start "Kamera (Yapay Zeka)" cmd /k "cd /d %~dp0 && python cv/camera_feed.py"

echo.
echo Baslatici gorevini tamamladi. 
echo - Sitenize tarayicidan erisebilirsiniz (index.html)
echo - Sistemi kapatmak icin acilan siyah pencereleri (X) isaretinden kapatmaniz yeterlidir.
echo.
pause
