@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Chatbot Calidad de Gas Natural - Servidor

echo ===============================================
echo    Chatbot de Calidad de Gas Natural - ENAGAS
echo ===============================================
echo.
echo Arrancando el servidor... NO cierres esta ventana.
echo.

REM --- Muestra las URLs de acceso (local y para companeros en la misma red) ---
powershell -NoProfile -Command "$ip=(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'} | Select-Object -First 1).IPAddress; Write-Host '  Acceso en ESTE equipo:        http://localhost:8000/' -ForegroundColor Green; if($ip){ Write-Host ('  Acceso para COMPANEROS:        http://{0}:8000/' -f $ip) -ForegroundColor Cyan }; Write-Host '  (Los companeros deben estar en la MISMA red Wi-Fi / LAN)' -ForegroundColor DarkGray"

echo.
echo Para detener el servidor: pulsa Ctrl+C o cierra esta ventana.
echo.

REM Abre el navegador en este equipo (~3 s despues)
start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & explorer http://localhost:8000/"

REM Arranca el backend ACCESIBLE DESDE LA RED (--host 0.0.0.0)
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

echo.
echo El servidor se ha detenido. Pulsa una tecla para cerrar.
pause >nul
