@echo off
:: ════════════════════════════════════════════════════════════════════════════
::  HUMS V2 — Build de ejecutable standalone para Windows
::  Genera un único .exe que contiene Python + todas las dependencias.
::  No requiere ninguna instalación previa en el equipo destino.
::
::  Requisito previo: Python 3.x instalado y en el PATH
::    https://www.python.org/downloads/
::    (marcar "Add Python to PATH" durante la instalación)
::
::  Uso:
::    Doble clic en build.bat  -o-  ejecutar desde cmd
::
::  Salida:  dist\HUMS_ModificadorSolicitudes.exe
:: ════════════════════════════════════════════════════════════════════════════
setlocal enabledelayedexpansion

set APP_NAME=HUMS_ModificadorSolicitudes
set VENV_DIR=.venv_build

echo.
echo ══════════════════════════════════════════════
echo   HUMS V2 — Build de ejecutable Windows
echo ══════════════════════════════════════════════

:: ── 1. Comprobar que Python está disponible ──────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python no encontrado en el PATH.
    echo   Instala Python desde https://www.python.org/downloads/
    echo   y marca "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

:: ── 2. Entorno virtual limpio ─────────────────────────────────────────────
echo.
echo ^> Creando entorno virtual de build...
if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"
python -m venv "%VENV_DIR%"
call "%VENV_DIR%\Scripts\activate.bat"

:: ── 3. Dependencias ────────────────────────────────────────────────────────
echo ^> Instalando dependencias...
pip install --quiet --upgrade pip
pip install --quiet PyQt5 paramiko pyinstaller

:: ── 4. PyInstaller ─────────────────────────────────────────────────────────
echo ^> Generando ejecutable con PyInstaller...
echo    (puede tardar 1-2 minutos)

pyinstaller ^
    --onefile ^
    --windowed ^
    --uac-admin ^
    --name "%APP_NAME%" ^
    --add-data "obd_database.py;." ^
    --add-data "pid_selector.py;." ^
    --add-data "network_manager.py;." ^
    --hidden-import "paramiko" ^
    --hidden-import "paramiko.transport" ^
    --hidden-import "paramiko.auth_handler" ^
    --hidden-import "paramiko.channel" ^
    --hidden-import "paramiko.client" ^
    --hidden-import "paramiko.sftp_client" ^
    --hidden-import "paramiko.sftp_file" ^
    --hidden-import "paramiko.hostkeys" ^
    --hidden-import "paramiko.rsakey" ^
    --hidden-import "paramiko.ecdsakey" ^
    --hidden-import "paramiko.ed25519key" ^
    --hidden-import "paramiko.kex_group14" ^
    --hidden-import "paramiko.kex_group16" ^
    --hidden-import "paramiko.kex_ecdh_nist" ^
    --hidden-import "paramiko.kex_curve25519" ^
    --hidden-import "cryptography" ^
    --hidden-import "cryptography.hazmat.primitives.ciphers.algorithms" ^
    --hidden-import "cryptography.hazmat.primitives.ciphers.modes" ^
    --hidden-import "cryptography.hazmat.backends.openssl" ^
    --collect-all "paramiko" ^
    --collect-all "cryptography" ^
    --noconfirm ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller fallo. Revisa los mensajes anteriores.
    call "%VENV_DIR%\Scripts\deactivate.bat"
    pause
    exit /b 1
)

call "%VENV_DIR%\Scripts\deactivate.bat"

:: ── 5. Resultado ───────────────────────────────────────────────────────────
echo.
echo ══════════════════════════════════════════════
echo   BUILD COMPLETADO
echo ══════════════════════════════════════════════
echo.
echo   Ejecutable: %CD%\dist\%APP_NAME%.exe
echo.
echo   El ejecutable incluye Python + PyQt5 + paramiko + todas las
echo   dependencias. No requiere ninguna instalacion en el equipo destino.
echo ══════════════════════════════════════════════
echo.
pause
