"""
Gestión automática de configuración de red para el HUMS.

Si el PC no tiene ninguna IP en la misma subred /24 que el HUMS, añade
una IP temporal al adaptador adecuado. Al cerrar la app, la elimina.

Solo aplica en Windows (usa netsh). En Linux no hace nada.
Requiere privilegios de administrador.
"""

from __future__ import annotations

import platform
import re
import socket
import subprocess
import ctypes
import sys
from typing import Optional

# ── IPs conocidas del HUMS ────────────────────────────────────────────────────
# Subred (/24) → IP temporal que se asignará al PC
HUMS_TEMP_IPS: dict[str, str] = {
    "192.168.5": "192.168.5.200",   # Ethernet
    "192.168.4": "192.168.4.200",   # WiFi
}
SUBNET_MASK = "255.255.255.0"

# En Windows, CREATE_NO_WINDOW evita que aparezca una ventana de consola
# al ejecutar netsh desde un proceso windowed.
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ── Privilegios de administrador ──────────────────────────────────────────────

def is_admin() -> bool:
    """True si el proceso actual tiene privilegios de administrador."""
    if platform.system() != "Windows":
        try:
            import os
            return os.geteuid() == 0
        except AttributeError:
            return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def request_admin_restart() -> None:
    """
    Relanza la aplicación con privilegios de administrador vía UAC.
    El proceso actual termina inmediatamente después.
    """
    if platform.system() == "Windows":
        args = " ".join(f'"{a}"' for a in sys.argv)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, None, 1)
    sys.exit(0)


# ── Utilidades de red ─────────────────────────────────────────────────────────

def _subnet_prefix(ip: str) -> Optional[str]:
    """'192.168.5.100' → '192.168.5'"""
    parts = ip.split(".")
    return ".".join(parts[:3]) if len(parts) == 4 else None


def _local_ips() -> list[str]:
    """Devuelve todas las IPs IPv4 locales del PC (sin loopback)."""
    ips: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                ips.add(ip)
    except Exception:
        pass
    return list(ips)


def needs_config(hums_ip: str) -> bool:
    """
    True si el PC no tiene ninguna IP en la subred /24 del HUMS
    y la subred del HUMS es una de las conocidas (192.168.5.x o 192.168.4.x).
    """
    prefix = _subnet_prefix(hums_ip)
    if not prefix or prefix not in HUMS_TEMP_IPS:
        return False
    return not any(lip.startswith(prefix + ".") for lip in _local_ips())


# ── Detección de adaptadores (Windows) ───────────────────────────────────────

def _get_interfaces_windows() -> list[tuple[str, list[str]]]:
    """
    Devuelve [(nombre_interfaz, [ips_asignadas]), ...] para todos
    los adaptadores configurados en Windows.
    """
    try:
        result = subprocess.run(
            ["netsh", "interface", "ipv4", "show", "addresses"],
            capture_output=True, text=True, timeout=10,
            creationflags=_NO_WIN,
        )
        interfaces: list[tuple[str, list[str]]] = []
        current_name: Optional[str] = None
        current_ips: list[str] = []

        for line in result.stdout.splitlines():
            # Cabecera de sección: Configuración para la interfaz "Ethernet"
            # (funciona tanto en inglés como en español de Windows)
            m = re.search(r'["\u201c\u201d]([^"\u201c\u201d]+)["\u201c\u201d]', line)
            if m and re.search(r'(interfaz|interface|configuraci)', line, re.IGNORECASE):
                if current_name is not None:
                    interfaces.append((current_name, current_ips))
                current_name = m.group(1)
                current_ips = []
            elif current_name:
                ip_m = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', line)
                if ip_m and re.search(r'(IP\s+(Address|Direcci))', line, re.IGNORECASE):
                    ip = ip_m.group(1)
                    if not ip.startswith("127."):
                        current_ips.append(ip)

        if current_name is not None:
            interfaces.append((current_name, current_ips))
        return interfaces
    except Exception:
        return []


def _choose_interface(subnet_prefix: str) -> Optional[str]:
    """
    Elige el adaptador de red más adecuado para añadir la IP temporal.
    - Subred 192.168.5.x (Ethernet) → preferir adaptador cableado.
    - Subred 192.168.4.x (WiFi)     → preferir adaptador inalámbrico.
    """
    interfaces = _get_interfaces_windows()

    # Excluir loopback
    active = [
        (name, ips) for name, ips in interfaces
        if "loopback" not in name.lower() and "pseudo" not in name.lower()
    ]
    if not active:
        return None

    wifi_keywords = {"wi-fi", "wifi", "wireless", "wlan", "inalámbri"}
    want_wifi = (subnet_prefix == "192.168.4")

    wifi_ifaces  = [n for n, _ in active if any(k in n.lower() for k in wifi_keywords)]
    wired_ifaces = [n for n, _ in active if not any(k in n.lower() for k in wifi_keywords)]

    if want_wifi:
        candidates = wifi_ifaces or wired_ifaces
    else:
        candidates = wired_ifaces or wifi_ifaces

    return candidates[0] if candidates else active[0][0]


# ── API pública ───────────────────────────────────────────────────────────────

def add_temp_ip(hums_ip: str) -> Optional[tuple[str, str]]:
    """
    Añade una IP temporal al adaptador adecuado para alcanzar el HUMS.

    Devuelve (nombre_interfaz, ip_temporal) si el cambio se realizó,
    o None si no fue necesario, la subred no es conocida, o falló.
    """
    if platform.system() != "Windows":
        return None

    prefix = _subnet_prefix(hums_ip)
    if not prefix or prefix not in HUMS_TEMP_IPS:
        return None

    temp_ip = HUMS_TEMP_IPS[prefix]
    interface = _choose_interface(prefix)
    if not interface:
        return None

    result = subprocess.run(
        ["netsh", "interface", "ipv4", "add", "address",
         f"name={interface}", f"address={temp_ip}", f"mask={SUBNET_MASK}"],
        capture_output=True, text=True, timeout=15,
        creationflags=_NO_WIN,
    )
    return (interface, temp_ip) if result.returncode == 0 else None


def remove_temp_ip(interface: str, temp_ip: str) -> None:
    """Elimina la IP temporal añadida previamente por add_temp_ip."""
    if platform.system() != "Windows":
        return
    subprocess.run(
        ["netsh", "interface", "ipv4", "delete", "address",
         f"name={interface}", f"address={temp_ip}"],
        capture_output=True, text=True, timeout=15,
        creationflags=_NO_WIN,
    )
