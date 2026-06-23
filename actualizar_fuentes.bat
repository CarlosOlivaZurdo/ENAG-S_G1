@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Actualizar PDFs oficiales - Comparador de Calidad de Gas

echo ===============================================
echo   Actualizar PDFs oficiales (BOE, EUR-Lex...)
echo ===============================================
echo.
echo Descarga la ultima version de las normativas con URL configurada
echo en data\raw\. Conserva el PDF anterior como .bak si algo falla.
echo Requiere conexion a internet.
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se encuentra Python. Instala Python 3.11+ y marca "Add to PATH".
    echo.
    pause
    exit /b
)

python -m pip install --quiet --disable-pip-version-check pyyaml >nul 2>&1
python actualizar_fuentes.py

echo.
echo Hecho. Revisa los avisos de arriba. Pulsa una tecla para cerrar.
pause >nul
