#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
#  HUMS V2 — Build de ejecutable standalone
#  Genera un único binario que contiene Python + todas las dependencias.
#  No requiere ninguna instalación previa en el equipo destino.
#
#  Uso:
#    chmod +x build.sh
#    ./build.sh
#
#  Salida:  dist/HUMS_ModificadorSolicitudes
# ════════════════════════════════════════════════════════════════════════════
set -e

APP_NAME="HUMS_ModificadorSolicitudes"
VENV_DIR=".venv_build"

echo ""
echo "══════════════════════════════════════════════"
echo "  HUMS V2 — Build de ejecutable"
echo "══════════════════════════════════════════════"

# ── 1. Entorno virtual limpio ─────────────────────────────────────────────
echo ""
echo "► Creando entorno virtual de build…"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# ── 2. Dependencias ────────────────────────────────────────────────────────
echo "► Instalando dependencias…"
pip install --quiet --upgrade pip
pip install --quiet PyQt5 paramiko pyinstaller

# ── 3. PyInstaller ─────────────────────────────────────────────────────────
echo "► Generando ejecutable con PyInstaller…"
echo "   (puede tardar 1-2 minutos)"

pyinstaller \
    --onefile \
    --windowed \
    --name "$APP_NAME" \
    --add-data "obd_database.py:." \
    --add-data "pid_selector.py:." \
    --add-data "network_manager.py:." \
    --hidden-import "paramiko" \
    --hidden-import "paramiko.transport" \
    --hidden-import "paramiko.auth_handler" \
    --hidden-import "paramiko.channel" \
    --hidden-import "paramiko.client" \
    --hidden-import "paramiko.sftp_client" \
    --hidden-import "paramiko.sftp_file" \
    --hidden-import "paramiko.hostkeys" \
    --hidden-import "paramiko.rsakey" \
    --hidden-import "paramiko.ecdsakey" \
    --hidden-import "paramiko.ed25519key" \
    --hidden-import "paramiko.kex_group14" \
    --hidden-import "paramiko.kex_group16" \
    --hidden-import "paramiko.kex_ecdh_nist" \
    --hidden-import "paramiko.kex_curve25519" \
    --hidden-import "cryptography" \
    --hidden-import "cryptography.hazmat.primitives.ciphers.algorithms" \
    --hidden-import "cryptography.hazmat.primitives.ciphers.modes" \
    --hidden-import "cryptography.hazmat.backends.openssl" \
    --collect-all "paramiko" \
    --collect-all "cryptography" \
    --noconfirm \
    main.py

deactivate

# ── 4. Resultado ───────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo "  ✓ BUILD COMPLETADO"
echo "══════════════════════════════════════════════"
echo ""
echo "  Ejecutable: $(pwd)/dist/$APP_NAME"
echo "  Tamaño:     $(du -sh dist/$APP_NAME 2>/dev/null | cut -f1)"
echo ""
echo "  Para ejecutar:"
echo "    ./dist/$APP_NAME"
echo ""
echo "  El ejecutable incluye Python + PyQt5 + paramiko + todas las"
echo "  dependencias. No requiere ninguna instalación en el equipo destino."
echo ""
echo "  NOTA: El binario generado es para Linux (x86-64)."
echo "  Para otros sistemas, ejecutar este script en ese sistema."
echo "══════════════════════════════════════════════"
