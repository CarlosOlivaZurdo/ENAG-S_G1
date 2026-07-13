@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Chatbot de Calidad de Gas Natural - ENAGAS

REM ============================================================================
REM  Al abrir:
REM   1) Se ACTUALIZA solo a la ultima version (git, de forma SEGURA: nunca
REM      borra cambios locales).
REM   2) Se relanza ya actualizado (lee el .bat nuevo) y arranca el servidor.
REM   3) Libera el puerto 8000 si quedo un servidor anterior abierto.
REM  Asi todos los companeros ven SIEMPRE la misma version, sin pasos manuales.
REM ============================================================================

if /i "%~1"=="run" goto run

call :actualizar
REM Relanza leyendo el .bat YA ACTUALIZADO (no vuelve aqui).
"%~f0" run
goto :eof

:actualizar
where git >nul 2>&1 || goto :eof
if not exist ".git" goto :eof
echo Buscando actualizaciones...
set GIT_TERMINAL_PROMPT=0
git pull --ff-only
if errorlevel 1 (
    echo   [aviso] No se pudo actualizar automaticamente.
    echo           Causa habitual: tienes cambios locales sin guardar o no hay conexion.
    echo           Se usara la version que ya tienes. Para forzar la ultima: git pull
) else (
    echo   Tienes la ultima version.
)
echo.
goto :eof

:run
echo ===============================================
echo    Chatbot de Calidad de Gas Natural - ENAGAS
echo ===============================================
echo.

REM --- 1) Comprobar que Python esta instalado ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se encuentra Python en este equipo.
    echo.
    echo   Instala Python 3.11 o superior desde:
    echo       https://www.python.org/downloads/
    echo   IMPORTANTE: durante la instalacion marca la casilla
    echo   "Add Python to PATH".
    echo.
    echo   Despues, vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b
)

REM --- 2) Instalar dependencias (solo la PRIMERA vez tarda; luego es instantaneo) ---
echo Preparando el entorno...
echo  (La PRIMERA vez instala las librerias y puede tardar 1-2 minutos. Espera, por favor.)
echo.
python -m pip install --quiet --disable-pip-version-check fastapi uvicorn pydantic python-dotenv pandas openpyxl xhtml2pdf pdfplumber openai pyyaml cryptography
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudieron instalar las dependencias.
    echo   Comprueba que tienes conexion a internet y vuelve a intentarlo.
    echo.
    pause
    exit /b
)

REM --- 2b) [HTTPS OPCIONAL - PARA PRODUCCION] ---------------------------------
REM   Por defecto el servidor arranca por HTTP (uso interno/local). Si se quiere
REM   servir por HTTPS (recomendado en un despliegue de produccion), basta con:
REM     1) descomentar la linea siguiente (genera un certificado autofirmado), y
REM     2) anadir  --ssl-keyfile key.pem --ssl-certfile cert.pem  al comando
REM        "uvicorn" del final de este archivo (y cambiar http:// por https://).
REM   Alternativa mas robusta: servir detras de un proxy inverso (nginx / IIS)
REM   que gestione el TLS con un certificado de confianza.
REM python generar_certificado.py

REM --- 3) Liberar el puerto 8000 si quedo un servidor anterior abierto ---
REM   (cerrar el navegador NO detiene el servidor; esto evita el error 10048
REM    "solo se permite un uso de cada direccion de socket")
powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; if ($c) { $c.OwningProcess | Select-Object -Unique | ForEach-Object { try { Stop-Process -Id $_ -Force -ErrorAction Stop; Write-Host ('  Se cerro una instancia anterior del servidor (PID {0}) que ocupaba el puerto 8000.' -f $_) -ForegroundColor Yellow } catch {} }; Start-Sleep -Milliseconds 700 }"

echo Servidor listo. NO cierres esta ventana mientras uses la herramienta.
echo.
powershell -NoProfile -Command "$ip=(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'} | Select-Object -First 1).IPAddress; Write-Host '  Abrir en ESTE equipo:          http://localhost:8000/' -ForegroundColor Green; if($ip){ Write-Host ('  Compartir (misma red):         http://{0}:8000/' -f $ip) -ForegroundColor Cyan }; Write-Host '  (Se sirve por HTTP para uso interno/local. Para HTTPS ver la nota [HTTPS OPCIONAL] en este .bat.)' -ForegroundColor DarkGray"
echo.
echo Para detener el servidor: pulsa Ctrl+C o cierra esta ventana.
echo.

REM Abre el navegador en este equipo (~4 s, cuando el servidor ya responde)
start "" /b cmd /c "ping -n 5 127.0.0.1 >nul & explorer http://localhost:8000/"

REM Arranca el servidor por HTTP (uso interno/local).
REM   Para HTTPS: ver la nota [HTTPS OPCIONAL] de arriba y anadir a esta linea:
REM     --ssl-keyfile key.pem --ssl-certfile cert.pem
python -m uvicorn api:app --host 0.0.0.0 --port 8000

echo.
echo El servidor se ha detenido. Pulsa una tecla para cerrar.
pause >nul
