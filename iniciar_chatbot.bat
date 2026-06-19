@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Chatbot Calidad de Gas Natural - Servidor

echo ===============================================
echo    Chatbot de Calidad de Gas Natural - ENAGAS
echo ===============================================
echo.
echo Arrancando el servidor... NO cierres esta ventana.
echo El navegador se abrira solo en unos segundos.
echo.
echo Para detener el servidor: pulsa Ctrl+C o cierra esta ventana.
echo.

REM Abre el navegador tras ~3 segundos (cuando el servidor ya esta listo)
start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & explorer http://localhost:8000/"

REM Arranca el backend (esta ventana queda ocupada con el servidor)
python -m uvicorn api:app --port 8000

echo.
echo El servidor se ha detenido. Pulsa una tecla para cerrar.
pause >nul
