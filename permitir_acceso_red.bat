@echo off
chcp 65001 >nul
title Permitir acceso de red al Chatbot (puerto 8000)

REM --- Se auto-eleva a Administrador (necesario para tocar el firewall) ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permisos de administrador...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo ===============================================
echo   Abriendo el puerto 8000 en el firewall...
echo ===============================================
echo.

REM Elimina una regla previa con el mismo nombre (si existe) y crea la nueva.
netsh advfirewall firewall delete rule name="Chatbot Gas Natural 8000" >nul 2>&1
netsh advfirewall firewall add rule name="Chatbot Gas Natural 8000" dir=in action=allow protocol=TCP localport=8000 profile=private,domain

echo.
echo Listo. Tus companeros (en la misma red) ya pueden conectar al puerto 8000.
echo Solo necesitas ejecutar esto UNA VEZ.
echo.
pause
