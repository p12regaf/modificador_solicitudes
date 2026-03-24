"""
HUMS V2 — Modificador de Solicitudes OBDII
Edita solicitudes.csv en el HUMS via SSH.
"""

from __future__ import annotations

import sys
import csv
import io
import json
import platform
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QCheckBox, QSpinBox, QGroupBox, QMessageBox, QHeaderView,
    QFileDialog, QAbstractItemView, QFrame, QMenu, QAction,
    QDialog, QScrollArea, QTextBrowser,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QColor, QPalette

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

from obd_database import decode_datos, get_pid, OBD_PIDS
from pid_selector import PIDSelectorDialog
from network_manager import (
    is_admin, request_admin_restart,
    needs_config, add_temp_ip, remove_temp_ip,
)


# ── Constants ─────────────────────────────────────────────────────────────────

CONFIG_FILE      = Path.home() / ".config" / "hums_modificador.json"
OVERRIDES_FILE   = Path.home() / ".config" / "hums_pid_overrides.json"
DEFAULT_CSV      = "/home/cosigein/app/solicitudes.csv"
DEFAULT_UNITS    = "/home/cosigein/app/pid_units.csv"
DEFAULT_SERVICE  = "OBD.service"
DEFAULT_PORT     = 22
DEFAULT_USERNAME = "cosigein"

# Column indices
COL_DESC  = 0
COL_UNIT  = 1
COL_ID    = 2
COL_DATOS = 3
COL_FREQ  = 4
COL_DISP  = 5
COL_UNICO = 6
COL_FAB   = 7
N_COLS    = 8

HEADERS = [
    "Descripción",
    "Unidad",
    "ID (hex)",
    "Datos (hex)",
    "Frecuencia (ms)",
    "Disparo (ms)",
    "Disparo Único",
    "Fabricante",
]

# Colors
BG_STANDARD   = QColor("#F5F5F5")   # gris claro — solo lectura
BG_FABRICANTE = QColor("#FFF8E1")   # amarillo suave — editable


# ── SSH Worker ────────────────────────────────────────────────────────────────

class SSHWorker(QThread):
    """Operaciones SSH en hilo separado para no bloquear la UI."""

    finished = pyqtSignal(bool, str, object)

    def __init__(self, operation: str, **kwargs):
        super().__init__()
        self.operation = operation
        self.kwargs = kwargs

    def run(self):
        if not PARAMIKO_AVAILABLE:
            self.finished.emit(False, "Paramiko no instalado — ejecuta: pip install paramiko", None)
            return
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=self.kwargs["host"],
                port=self.kwargs["port"],
                username=self.kwargs["username"],
                password=self.kwargs["password"],
                timeout=12,
            )

            if self.operation == "test":
                _, stdout, _ = client.exec_command("uname -srm && hostname -I")
                info = stdout.read().decode().strip()
                client.close()
                self.finished.emit(True, f"Conexión OK\n{info}", None)

            elif self.operation == "load":
                sftp = client.open_sftp()
                with sftp.open(self.kwargs["remote_path"], "r") as f:
                    content = f.read().decode("utf-8")
                sftp.close()
                client.close()
                self.finished.emit(True, "CSV cargado", content)

            elif self.operation == "save":
                sftp = client.open_sftp()
                # Backup del archivo original
                remote = self.kwargs["remote_path"]
                try:
                    sftp.rename(remote, remote + ".bak")
                except Exception:
                    pass
                data = self.kwargs["content"].encode("utf-8")
                with sftp.open(remote, "w") as f:
                    f.write(data)
                # Save pid_units if provided
                units_content = self.kwargs.get("units_content")
                units_path = self.kwargs.get("units_path")
                if units_content and units_path:
                    try:
                        sftp.rename(units_path, units_path + ".bak")
                    except Exception:
                        pass
                    with sftp.open(units_path, "w") as f:
                        f.write(units_content.encode("utf-8"))
                sftp.close()
                client.close()
                self.finished.emit(True, "Archivos guardados en el HUMS", None)

            elif self.operation == "restart":
                service = self.kwargs.get("service", DEFAULT_SERVICE)
                _, stdout, stderr = client.exec_command(f"sudo systemctl restart {service}")
                code = stdout.channel.recv_exit_status()
                err = stderr.read().decode().strip()
                client.close()
                if code == 0:
                    self.finished.emit(True, f"Servicio {service} reiniciado", None)
                else:
                    self.finished.emit(False, f"Error al reiniciar {service}: {err}", None)

        except Exception as exc:
            self.finished.emit(False, f"Error SSH: {exc}", None)


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HUMS V2 — Modificador de Solicitudes OBDII")
        self.setMinimumSize(1150, 700)
        self.resize(1350, 800)

        self._worker: SSHWorker | None = None
        self._temp_network: tuple | None = None   # (interfaz, ip_temporal) añadida por network_manager
        self._load_config()
        self._overrides: dict = self._load_overrides()
        self._setup_ui()
        self.statusBar().showMessage(
            f"Listo — base de datos OBD-II: {len(OBD_PIDS)} variables estándar disponibles"
        )

    # ── Config ─────────────────────────────────────────────────────────────

    def _load_config(self):
        self.config = {"host": ""}
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    self.config.update(json.load(f))
            except Exception:
                pass

    def _save_config(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"host": self.host_input.text().strip()}, f)
        except Exception:
            pass

    # ── Overrides (PIDs de fabricante) ─────────────────────────────────────

    def _load_overrides(self) -> dict:
        """
        Carga el mapa de PIDs personalizados (fabricante).
        Formato: { "0201460000000000": {"nombre": "...", "unidad": "..."}, ... }
        """
        if OVERRIDES_FILE.exists():
            try:
                with open(OVERRIDES_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _persist_overrides(self):
        OVERRIDES_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(OVERRIDES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._overrides, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _set_override(self, datos_hex: str, nombre: str, unidad: str):
        key = datos_hex.strip().upper()
        if not key:
            return
        self._overrides[key] = {"nombre": nombre, "unidad": unidad}
        self._persist_overrides()

    def _remove_override(self, datos_hex: str):
        key = datos_hex.strip().upper()
        if key in self._overrides:
            del self._overrides[key]
            self._persist_overrides()

    # ── UI construction ────────────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(6)
        root.setContentsMargins(10, 8, 10, 8)

        root.addWidget(self._build_conn_panel())
        root.addWidget(self._hline())
        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_table(), stretch=1)

    def _hline(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setFrameShadow(QFrame.Sunken)
        return f

    def _vline(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.VLine)
        f.setFrameShadow(QFrame.Sunken)
        return f

    def _build_conn_panel(self) -> QGroupBox:
        group = QGroupBox("Conexión SSH a HUMS")
        col = QVBoxLayout(group)
        col.setSpacing(5)
        col.setContentsMargins(8, 6, 8, 6)

        # ── Fila 1: IP + botones de acción ────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        row1.addWidget(QLabel("Dirección IP:"))
        self.host_input = QLineEdit(self.config.get("host", ""))
        self.host_input.setPlaceholderText("192.168.1.100")
        self.host_input.setFixedWidth(160)
        self.host_input.returnPressed.connect(self._do_load)
        row1.addWidget(self.host_input)
        row1.addStretch()

        self.btn_test = QPushButton("Probar conexión")
        self.btn_test.setToolTip("Prueba la conexión SSH")
        self.btn_test.clicked.connect(self._do_test)
        row1.addWidget(self.btn_test)

        self.btn_load = QPushButton("⬇  Cargar CSV")
        self.btn_load.setStyleSheet("font-weight: bold;")
        self.btn_load.setToolTip("Descarga solicitudes.csv desde el HUMS")
        self.btn_load.clicked.connect(self._do_load)
        row1.addWidget(self.btn_load)

        self.btn_save = QPushButton("⬆  Guardar en el HUMS")
        self.btn_save.setStyleSheet(
            "font-weight: bold; background-color: #1565C0; color: white; padding: 4px 10px;"
        )
        self.btn_save.setToolTip(
            "Guarda solicitudes.csv (y pid_units.csv) en el HUMS"
        )
        self.btn_save.clicked.connect(self._do_save)
        row1.addWidget(self.btn_save)

        self.btn_restart = QPushButton("↺  Reiniciar servicio")
        self.btn_restart.setStyleSheet(
            "background-color: #BF360C; color: white; padding: 4px 10px;"
        )
        self.btn_restart.setToolTip(f"Reinicia {DEFAULT_SERVICE} en el HUMS")
        self.btn_restart.clicked.connect(self._do_restart)
        row1.addWidget(self.btn_restart)

        col.addLayout(row1)

        # ── Fila 2: rutas remotas (informativas, no editables) ─────────────
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        lbl_paths = QLabel(
            f"<span style='color:#888;'>Rutas fijas en HUMS: &nbsp;"
            f"<b>solicitudes.csv</b> → {DEFAULT_CSV} &nbsp;|&nbsp; "
            f"<b>pid_units.csv</b> → {DEFAULT_UNITS}</span>"
        )
        lbl_paths.setTextFormat(Qt.RichText)
        row2.addWidget(lbl_paths)
        row2.addStretch()

        col.addLayout(row2)

        return group

    def _build_toolbar(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.btn_obd = QPushButton("  ＋  Añadir desde OBD-II…")
        self.btn_obd.setStyleSheet(
            "font-weight: bold; padding: 5px 12px; "
            "background-color: #2E7D32; color: white;"
        )
        self.btn_obd.setToolTip(
            "Abre el selector de variables OBD-II estándar.\n"
            "Busca por nombre, categoría o PID y añade la solicitud con los valores recomendados."
        )
        self.btn_obd.clicked.connect(self._open_pid_selector)
        layout.addWidget(self.btn_obd)

        layout.addWidget(self._vline())

        btn_add = QPushButton("＋  Fila vacía")
        btn_add.setToolTip("Añade una fila en blanco para configurar manualmente")
        btn_add.clicked.connect(self._add_empty_row)
        layout.addWidget(btn_add)

        btn_del = QPushButton("✕  Eliminar fila")
        btn_del.clicked.connect(self._delete_selected)
        layout.addWidget(btn_del)

        btn_dup = QPushButton("⧉  Duplicar fila")
        btn_dup.setToolTip("Duplica la fila seleccionada")
        btn_dup.clicked.connect(self._duplicate_selected)
        layout.addWidget(btn_dup)

        layout.addWidget(self._vline())

        btn_open = QPushButton("📂  Abrir CSV local")
        btn_open.clicked.connect(self._open_local)
        layout.addWidget(btn_open)

        btn_save_local = QPushButton("💾  Guardar CSV local")
        btn_save_local.clicked.connect(self._save_local)
        layout.addWidget(btn_save_local)

        layout.addWidget(self._vline())

        btn_check = QPushButton("⚠  Verificar colisiones")
        btn_check.setToolTip(
            "Analiza si alguna solicitud se envía en el mismo instante que otra\n"
            "y permite corregirlo ajustando el Disparo."
        )
        btn_check.setStyleSheet("color: #E65100;")
        btn_check.clicked.connect(lambda: self._check_collisions(interactive=True))
        layout.addWidget(btn_check)

        layout.addStretch()

        btn_help = QPushButton("?  Ayuda")
        btn_help.setToolTip("Manual de usuario completo")
        btn_help.setStyleSheet("padding: 4px 10px; font-weight: bold;")
        btn_help.clicked.connect(self._open_help)
        layout.addWidget(btn_help)

        lbl = QLabel(
            "Doble clic / Clic derecho → editar  |  "
            "Frecuencia=0 → no repetir  |  Disparo Único → envía una sola vez"
        )
        lbl.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(lbl)

        return w

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget(0, N_COLS)
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.AnyKeyPressed
        )
        self.table.setWordWrap(False)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(COL_DESC, QHeaderView.Stretch)
        self.table.setColumnWidth(COL_UNIT,  70)
        self.table.setColumnWidth(COL_ID,    80)
        self.table.setColumnWidth(COL_DATOS, 185)
        self.table.setColumnWidth(COL_FREQ,  125)
        self.table.setColumnWidth(COL_DISP,  115)
        self.table.setColumnWidth(COL_UNICO, 95)
        self.table.setColumnWidth(COL_FAB,   85)

        # Tooltips on headers
        tips = {
            COL_DESC:  "Nombre de la variable (se actualiza al cambiar Datos)",
            COL_UNIT:  "Unidad de medida",
            COL_ID:    "Identificador del mensaje CAN (hex). 7DF = broadcast OBD-II",
            COL_DATOS: "8 bytes del payload CAN en hexadecimal. Ej: 02010C0000000000",
            COL_FREQ:  "Intervalo de repetición en ms. 0 = no repetir.",
            COL_DISP:  "Retardo antes del primer envío en ms.",
            COL_UNICO: "Si está marcado, solo se envía una vez al arrancar.",
            COL_FAB:   (
                "Fabricante: marcar si este PID no es estándar OBD-II.\n"
                "Al marcarlo, Descripción y Unidad se vuelven editables.\n"
                "El cambio persiste entre sesiones (se guarda localmente).\n"
                "Clic derecho → 'Restablecer a estándar' para deshacer."
            ),
        }
        for col, tip in tips.items():
            item = self.table.horizontalHeaderItem(col)
            if item:
                item.setToolTip(tip)

        # Ocultar columnas de datos en bruto (accesibles sólo mediante el diálogo de edición)
        self.table.setColumnHidden(COL_ID,    True)
        self.table.setColumnHidden(COL_DATOS, True)

        self.table.cellChanged.connect(self._on_cell_changed)
        return self.table

    # ── Table row helpers ──────────────────────────────────────────────────

    def _make_ro(self, text: str, tooltip: str = "") -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setBackground(QColor("#F5F5F5"))
        item.setForeground(QColor("#444"))
        if tooltip:
            item.setToolTip(tooltip)
        return item

    def _make_hex(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text.strip().upper())
        item.setFont(QFont("Courier New", 10))
        return item

    def _spin(self, value: int, step: int = 500) -> QSpinBox:
        s = QSpinBox()
        s.setRange(0, 600_000)
        s.setSingleStep(step)
        s.setSuffix(" ms")
        s.setValue(value)
        s.setButtonSymbols(QSpinBox.PlusMinus)
        return s

    def _checkbox_widget(self, checked: bool, freq_spin: QSpinBox) -> QWidget:
        """
        CheckBox de Disparo Único vinculado al SpinBox de Frecuencia:
        - Al marcar: pone Frecuencia a 0 y la deshabilita.
        - Al desmarcar: la vuelve a habilitar.
        """
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        cb = QCheckBox()

        def on_toggle(state):
            if state == Qt.Checked:
                freq_spin.setValue(0)
                freq_spin.setEnabled(False)
            else:
                freq_spin.setEnabled(True)

        cb.stateChanged.connect(on_toggle)
        cb.setChecked(checked)   # dispara on_toggle si checked=True
        layout.addWidget(cb)
        return w

    def _get_checkbox(self, row: int) -> int:
        w = self.table.cellWidget(row, COL_UNICO)
        if w:
            for cb in w.findChildren(QCheckBox):
                return 1 if cb.isChecked() else 0
        return 0

    def _is_row_fabricante(self, row: int) -> bool:
        w = self.table.cellWidget(row, COL_FAB)
        if w:
            for cb in w.findChildren(QCheckBox):
                return cb.isChecked()
        return False

    def _fab_checkbox_widget(self, is_fab: bool) -> QWidget:
        """
        CheckBox de Fabricante. Al cambiar estado, llama a _apply_fab_state
        para la fila que contiene este widget.
        """
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        cb = QCheckBox()

        def find_row() -> int:
            for r in range(self.table.rowCount()):
                if self.table.cellWidget(r, COL_FAB) is w:
                    return r
            return -1

        def on_toggle(state):
            r = find_row()
            if r >= 0:
                self._apply_fab_state(r, state == Qt.Checked)

        cb.stateChanged.connect(on_toggle)
        # No llamamos setChecked aquí; lo haremos desde _insert_row
        # una vez que el widget esté en la tabla.
        cb._pending_state = is_fab
        layout.addWidget(cb)
        return w

    def _apply_fab_state(self, row: int, is_fab: bool):
        """
        Aplica el estado Fabricante/Estándar a una fila:
        - Fabricante: Descripción y Unidad se vuelven editables (fondo amarillo).
          Guarda el override en disco.
        - Estándar: restaura Descripción y Unidad desde la base OBD-II.
          Borra el override de disco.
        """
        desc_item  = self.table.item(row, COL_DESC)
        unit_item  = self.table.item(row, COL_UNIT)
        datos_item = self.table.item(row, COL_DATOS)
        datos_key  = datos_item.text().strip().upper() if datos_item else ""

        if is_fab:
            for item in (desc_item, unit_item):
                if item:
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    item.setBackground(BG_FABRICANTE)
                    item.setForeground(QColor("#333333"))
            # Guardar en overrides con los valores actuales
            if datos_key:
                self._set_override(
                    datos_key,
                    desc_item.text() if desc_item else "",
                    unit_item.text() if unit_item else "",
                )
        else:
            # Restaurar desde base de datos OBD-II
            nombre, unidad = decode_datos(datos_key) if datos_key else ("", "")
            if datos_key:
                self._remove_override(datos_key)
            for item, text in ((desc_item, nombre), (unit_item, unidad)):
                if item:
                    self.table.blockSignals(True)
                    item.setText(text)
                    self.table.blockSignals(False)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    item.setBackground(BG_STANDARD)
                    item.setForeground(QColor("#444444"))

    def _insert_row(
        self,
        id_val: str = "",
        datos: str = "",
        freq: int = 0,
        disparo: int = 0,
        unico: bool = False,
        nombre: str = "",
        unidad: str = "",
        fabricante: bool | None = None,   # None = auto-detectar
    ) -> int:
        self.table.blockSignals(True)
        r = self.table.rowCount()
        self.table.insertRow(r)

        datos_key = datos.strip().upper()

        # Determinar si es fabricante
        if fabricante is None:
            fabricante = datos_key in self._overrides

        # Resolver nombre y unidad
        if fabricante and datos_key in self._overrides:
            ov = self._overrides[datos_key]
            if not nombre:
                nombre = ov.get("nombre", "")
            if not unidad:
                unidad = ov.get("unidad", "")
        elif not fabricante and datos_key:
            if not nombre or not unidad:
                dec_nombre, dec_unidad = decode_datos(datos_key, id_val)
                if not nombre:
                    nombre = dec_nombre
                if not unidad:
                    unidad = dec_unidad

        # Crear items de desc y unidad (siempre read-only aquí; FAB los hará editables después)
        self.table.setItem(r, COL_DESC,  self._make_ro(nombre))
        self.table.setItem(r, COL_UNIT,  self._make_ro(unidad))
        self.table.setItem(r, COL_ID,    self._make_hex(id_val))
        self.table.setItem(r, COL_DATOS, self._make_hex(datos))

        freq_spin = self._spin(freq, step=500)
        self.table.setCellWidget(r, COL_FREQ,  freq_spin)
        self.table.setCellWidget(r, COL_DISP,  self._spin(disparo, step=100))
        self.table.setCellWidget(r, COL_UNICO, self._checkbox_widget(unico, freq_spin))

        # Columna Fabricante — aplicar estado DESPUÉS de que el widget esté en la tabla
        fab_w = self._fab_checkbox_widget(fabricante)
        self.table.setCellWidget(r, COL_FAB, fab_w)

        self.table.blockSignals(False)

        # Fijar el estado visual del checkbox FAB sin re-disparar on_toggle
        for _cb in fab_w.findChildren(QCheckBox):
            _cb.blockSignals(True)
            _cb.setChecked(fabricante)
            _cb.blockSignals(False)

        # Activar estado FAB ahora que todo está en la tabla
        if fabricante:
            self._apply_fab_state(r, True)

        return r

    def _on_cell_changed(self, row: int, col: int):
        """Actualiza Descripción/Unidad cuando cambian ID, Datos, o el propio DESC/UNIT en FAB."""
        if col in (COL_DESC, COL_UNIT):
            # Si la fila es fabricante, persistir el override inmediatamente
            if self._is_row_fabricante(row):
                datos_item = self.table.item(row, COL_DATOS)
                desc_item  = self.table.item(row, COL_DESC)
                unit_item  = self.table.item(row, COL_UNIT)
                if datos_item:
                    self._set_override(
                        datos_item.text(),
                        desc_item.text() if desc_item else "",
                        unit_item.text() if unit_item else "",
                    )
            return

        if col not in (COL_ID, COL_DATOS):
            return

        id_item    = self.table.item(row, COL_ID)
        datos_item = self.table.item(row, COL_DATOS)
        if not id_item or not datos_item:
            return

        self.table.blockSignals(True)
        id_item.setText(id_item.text().upper())
        datos_item.setText(datos_item.text().upper())
        self.table.blockSignals(False)

        datos_key = datos_item.text().strip().upper()

        if self._is_row_fabricante(row):
            # Para filas FAB: si el nuevo datos tiene override, aplicarlo
            if datos_key in self._overrides:
                ov = self._overrides[datos_key]
                self.table.blockSignals(True)
                if self.table.item(row, COL_DESC):
                    self.table.item(row, COL_DESC).setText(ov.get("nombre", ""))
                if self.table.item(row, COL_UNIT):
                    self.table.item(row, COL_UNIT).setText(ov.get("unidad", ""))
                self.table.blockSignals(False)
            # Si no hay override para el nuevo datos, mantener los valores actuales
        else:
            nombre, unidad = decode_datos(datos_key, id_item.text())
            if self.table.item(row, COL_DESC):
                self.table.item(row, COL_DESC).setText(nombre)
            if self.table.item(row, COL_UNIT):
                self.table.item(row, COL_UNIT).setText(unidad)

    # ── Context menu ────────────────────────────────────────────────────────

    def _show_context_menu(self, pos: QPoint):
        row = self.table.rowAt(pos.y())
        menu = QMenu(self)

        act_obd = QAction("＋  Añadir desde OBD-II…", self)
        act_obd.triggered.connect(self._open_pid_selector)
        menu.addAction(act_obd)

        menu.addSeparator()

        act_edit_frame = QAction("✎  Editar trama CAN…", self)
        act_edit_frame.setEnabled(row >= 0)
        act_edit_frame.setToolTip("Edita el ID CAN, los bytes de datos y el resto de parámetros de esta solicitud")
        act_edit_frame.triggered.connect(lambda: self._edit_row_frame(row))
        menu.addAction(act_edit_frame)

        act_change = QAction("⇄  Cambiar PID desde OBD-II…", self)
        act_change.setEnabled(row >= 0)
        act_change.triggered.connect(lambda: self._change_pid_at_row(row))
        menu.addAction(act_change)

        act_dup = QAction("⧉  Duplicar fila", self)
        act_dup.setEnabled(row >= 0)
        act_dup.triggered.connect(self._duplicate_selected)
        menu.addAction(act_dup)

        act_del = QAction("✕  Eliminar fila", self)
        act_del.setEnabled(row >= 0)
        act_del.triggered.connect(self._delete_selected)
        menu.addAction(act_del)

        menu.addSeparator()

        act_restore = QAction("↺  Restablecer a estándar OBD-II", self)
        act_restore.setEnabled(row >= 0 and self._is_row_fabricante(row))
        act_restore.setToolTip("Desmarca Fabricante y restaura Descripción y Unidad desde la base OBD-II")
        act_restore.triggered.connect(lambda: self._restore_to_standard(row))
        menu.addAction(act_restore)

        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _restore_to_standard(self, row: int):
        """Desmarca el checkbox Fabricante, restaurando la interpretación estándar OBD-II."""
        w = self.table.cellWidget(row, COL_FAB)
        if w:
            for cb in w.findChildren(QCheckBox):
                cb.setChecked(False)   # dispara on_toggle → _apply_fab_state(row, False)
                break

    # ── CSV serialize / parse ──────────────────────────────────────────────

    def _parse_csv(self, content: str) -> int:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.blockSignals(False)

        reader = csv.DictReader(io.StringIO(content))
        count = 0
        for row in reader:
            id_val = row.get("ID", "").strip()
            datos  = row.get("Datos", "").strip()
            if not id_val and not datos:
                continue
            try:
                freq = int(row.get("Frecuencia", "0").strip() or "0")
            except ValueError:
                freq = 0
            try:
                disp = int(row.get("Disparo", "0").strip() or "0")
            except ValueError:
                disp = 0
            try:
                unico = bool(int(row.get("Disparo Único", "0").strip() or "0"))
            except ValueError:
                unico = False

            self._insert_row(id_val, datos, freq, disp, unico)
            count += 1
        return count

    def _serialize_csv(self) -> str:
        out = io.StringIO()
        writer = csv.DictWriter(
            out,
            fieldnames=["ID", "Datos", "Frecuencia", "Disparo", "Disparo Único"],
            lineterminator="\n",
        )
        writer.writeheader()
        for r in range(self.table.rowCount()):
            id_item    = self.table.item(r, COL_ID)
            datos_item = self.table.item(r, COL_DATOS)
            if not id_item or not datos_item:
                continue
            fw = self.table.cellWidget(r, COL_FREQ)
            dw = self.table.cellWidget(r, COL_DISP)
            writer.writerow({
                "ID":            id_item.text().strip(),
                "Datos":         datos_item.text().strip(),
                "Frecuencia":    fw.value() if fw else 0,
                "Disparo":       dw.value() if dw else 0,
                "Disparo Único": self._get_checkbox(r),
            })
        return out.getvalue()

    def _build_pid_units_csv(self) -> str:
        """
        Construye el contenido de pid_units.csv a partir de las filas
        actuales de la tabla (solo PIDs Mode 01 con nombre y unidad conocidos).
        """
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["pid", "nombre_es", "unidad"])
        seen: set[str] = set()
        for r in range(self.table.rowCount()):
            datos_item = self.table.item(r, COL_DATOS)
            if not datos_item:
                continue
            datos = datos_item.text().strip().upper()
            if len(datos) < 6 or datos[2:4] != "01":
                continue
            pid = datos[4:6]
            if pid in seen:
                continue
            seen.add(pid)
            desc_item = self.table.item(r, COL_DESC)
            unit_item = self.table.item(r, COL_UNIT)
            nombre = desc_item.text() if desc_item else ""
            unidad = unit_item.text() if unit_item else ""
            writer.writerow([pid, nombre, unidad])
        return out.getvalue()

    # ── Collision detection ────────────────────────────────────────────────

    _COLLISION_WINDOW = 120_000   # ms — ventana de simulación (2 min)
    _MAX_FIRES        = 600       # límite de eventos por fila para freq muy bajas

    def _row_fire_times(self, row: int) -> frozenset[int]:
        """Devuelve el conjunto de instantes (ms) en que dispara esta fila."""
        fw = self.table.cellWidget(row, COL_FREQ)
        dw = self.table.cellWidget(row, COL_DISP)
        freq = fw.value() if fw else 0
        disp = dw.value() if dw else 0

        if freq <= 0:
            return frozenset({disp})

        times: set[int] = set()
        t, count = disp, 0
        while t <= self._COLLISION_WINDOW and count < self._MAX_FIRES:
            times.add(t)
            t += freq
            count += 1
        return frozenset(times)

    def _find_collisions(self) -> list[dict]:
        """
        Devuelve lista de dicts con las colisiones encontradas:
          row_a, row_b, name_a, name_b, times (primeras 4), total
        """
        n = self.table.rowCount()
        fire_times = [self._row_fire_times(r) for r in range(n)]

        def row_name(r):
            item = self.table.item(r, COL_DESC)
            return item.text() if item else f"Fila {r+1}"

        collisions = []
        for i in range(n):
            for j in range(i + 1, n):
                shared = sorted(fire_times[i] & fire_times[j])
                if shared:
                    collisions.append({
                        "row_a":  i,
                        "row_b":  j,
                        "name_a": row_name(i),
                        "name_b": row_name(j),
                        "times":  shared[:4],
                        "total":  len(shared),
                    })
        return collisions

    def _auto_fix_collisions(self, collisions: list[dict]):
        """
        Añade +50 ms al Disparo de row_b en cada colisión detectada.
        Itera hasta que no queden colisiones (máx. 20 pasadas).
        """
        for _ in range(20):
            if not collisions:
                break
            # Para cada par colisionante, incrementa el disparo de la fila con índice mayor
            for col in collisions:
                dw = self.table.cellWidget(col["row_b"], COL_DISP)
                if dw:
                    dw.setValue(dw.value() + 50)
            collisions = self._find_collisions()

    def _check_collisions(self, interactive: bool = True) -> bool:
        """
        Comprueba colisiones en la tabla actual.
        - interactive=True: muestra el diálogo de aviso.
        - Devuelve True si no hay colisiones (o el usuario elige ignorar).
        """
        collisions = self._find_collisions()
        if not collisions:
            if interactive:
                QMessageBox.information(
                    self, "Sin colisiones",
                    "No se detectaron colisiones en la ventana de 2 minutos. ✓"
                )
            return True

        dlg = CollisionDialog(collisions, self)
        result = dlg.exec_()

        if result == CollisionDialog.RESULT_FIX:
            self._auto_fix_collisions(collisions)
            remaining = self._find_collisions()
            if remaining:
                QMessageBox.warning(
                    self, "Colisiones residuales",
                    f"Quedan {len(remaining)} colisión(es) que no se pudieron resolver "
                    f"automáticamente.\nRevisa los valores manualmente."
                )
            else:
                self.statusBar().showMessage("Colisiones corregidas automáticamente.")
            return True   # continuar con el guardado tras corregir

        elif result == CollisionDialog.RESULT_IGNORE:
            return True   # el usuario elige ignorar y continuar

        else:             # cancelar
            return False

    def _get_table_rows_as_dicts(self) -> list[dict]:
        """Devuelve las filas de la tabla como lista de dicts (para auto-disparo)."""
        rows = []
        for r in range(self.table.rowCount()):
            fw = self.table.cellWidget(r, COL_FREQ)
            dw = self.table.cellWidget(r, COL_DISP)
            rows.append({
                "frecuencia":    fw.value() if fw else 0,
                "disparo":       dw.value() if dw else 0,
                "disparo_unico": bool(self._get_checkbox(r)),
            })
        return rows

    # ── SSH helpers ────────────────────────────────────────────────────────

    def _ssh_params(self) -> dict | None:
        host = self.host_input.text().strip()
        if not host:
            QMessageBox.warning(self, "Sin host",
                "Introduce la dirección IP del HUMS.")
            return None
        return {
            "host":        host,
            "port":        DEFAULT_PORT,
            "username":    DEFAULT_USERNAME,
            "password":    DEFAULT_USERNAME,   # misma cadena: cosigein
            "remote_path": DEFAULT_CSV,
        }

    def _ssh_buttons(self, enabled: bool):
        for b in (self.btn_test, self.btn_load, self.btn_save, self.btn_restart):
            b.setEnabled(enabled)

    def _run_ssh(self, operation: str, on_done, **extra):
        params = self._ssh_params()
        if params is None:
            return
        self._save_config()
        self._ensure_network(params["host"])
        self._ssh_buttons(False)
        self._worker = SSHWorker(operation, **params, **extra)
        self._worker.finished.connect(on_done)
        self._worker.start()

    def _ensure_network(self, hums_ip: str) -> None:
        """
        Si el PC no está en la subred del HUMS, añade una IP temporal
        al adaptador adecuado. Solo actúa en Windows y una sola vez por sesión.
        """
        if platform.system() != "Windows":
            return
        if self._temp_network:
            return  # ya configurado en esta sesión
        if not needs_config(hums_ip):
            return  # ya está en el rango correcto
        self.statusBar().showMessage("Configurando red para alcanzar el HUMS…")
        result = add_temp_ip(hums_ip)
        if result:
            self._temp_network = result
            iface, ip = result
            self.statusBar().showMessage(
                f"Red configurada — IP temporal {ip} añadida en '{iface}'"
            )
        else:
            self.statusBar().showMessage(
                "Aviso: no se pudo configurar la red automáticamente"
            )

    def closeEvent(self, event) -> None:
        """Al cerrar, elimina la IP temporal si se añadió durante la sesión."""
        if platform.system() == "Windows" and self._temp_network:
            iface, ip = self._temp_network
            remove_temp_ip(iface, ip)
            self._temp_network = None
        super().closeEvent(event)

    # ── SSH button actions ─────────────────────────────────────────────────

    def _do_test(self):
        self.statusBar().showMessage("Probando conexión SSH…")
        self._run_ssh("test", self._on_test_done)

    def _on_test_done(self, ok, msg, _):
        self._ssh_buttons(True)
        if ok:
            QMessageBox.information(self, "Conexión SSH", msg)
            self.statusBar().showMessage(f"Conexión OK — {self.host_input.text()}")
        else:
            QMessageBox.critical(self, "Error de conexión", msg)
            self.statusBar().showMessage(f"Error: {msg}")

    def _do_load(self):
        self.statusBar().showMessage("Descargando CSV desde el HUMS…")
        self._run_ssh("load", self._on_load_done)

    def _on_load_done(self, ok, msg, data):
        self._ssh_buttons(True)
        if ok and data:
            count = self._parse_csv(data)
            self.statusBar().showMessage(f"{msg} — {count} solicitudes cargadas.")
        else:
            QMessageBox.critical(self, "Error al cargar CSV", msg)
            self.statusBar().showMessage(f"Error: {msg}")

    def _do_save(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Tabla vacía", "No hay solicitudes para guardar.")
            return

        if not self._check_collisions(interactive=True):
            return   # usuario canceló

        reply = QMessageBox.question(
            self, "Confirmar guardado",
            f"¿Guardar {self.table.rowCount()} solicitudes en el HUMS?\n\n"
            f"• {DEFAULT_CSV}\n"
            f"• {DEFAULT_UNITS}  (pid_units.csv — actualizado)\n\n"
            f"Se creará una copia de seguridad (.bak) de los archivos actuales.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        csv_content   = self._serialize_csv()
        units_content = self._build_pid_units_csv()
        self.statusBar().showMessage("Guardando archivos en el HUMS…")
        self._run_ssh(
            "save", self._on_save_done,
            content=csv_content,
            units_content=units_content,
            units_path=DEFAULT_UNITS,
        )

    def _on_save_done(self, ok, msg, _):
        self._ssh_buttons(True)
        if ok:
            QMessageBox.information(self, "Guardado", msg)
            self.statusBar().showMessage(msg)
        else:
            QMessageBox.critical(self, "Error al guardar", msg)
            self.statusBar().showMessage(f"Error: {msg}")

    def _do_restart(self):
        reply = QMessageBox.question(
            self, "Reiniciar servicio",
            f"¿Reiniciar {DEFAULT_SERVICE} en el HUMS?\n"
            "Esto aplicará los cambios en solicitudes.csv.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.statusBar().showMessage(f"Reiniciando {DEFAULT_SERVICE}…")
        self._run_ssh("restart", self._on_restart_done, service=DEFAULT_SERVICE)

    def _on_restart_done(self, ok, msg, _):
        self._ssh_buttons(True)
        if ok:
            QMessageBox.information(self, "Servicio reiniciado", msg)
        else:
            QMessageBox.critical(self, "Error", msg)
        self.statusBar().showMessage(msg)

    # ── PID selector ────────────────────────────────────────────────────────

    def _open_pid_selector(self):
        dlg = PIDSelectorDialog(self, existing_rows=self._get_table_rows_as_dicts())
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.result_data()
            if data:
                self._insert_row(
                    id_val=data["can_id"],
                    datos=data["datos"],
                    freq=data["frecuencia"],
                    disparo=data["disparo"],
                    unico=data["disparo_unico"],
                    nombre=data["nombre"],
                    unidad=data["unidad"],
                )
                self.table.scrollToBottom()
                self.statusBar().showMessage(
                    f"Variable añadida: {data['nombre']} — {data['unidad']}"
                )

    def _change_pid_at_row(self, row: int):
        """Reemplaza ID y Datos de una fila existente con un PID del selector."""
        if row < 0:
            return
        dlg = PIDSelectorDialog(self, existing_rows=self._get_table_rows_as_dicts())
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.result_data()
            if data:
                self.table.blockSignals(True)
                id_item    = self.table.item(row, COL_ID)
                datos_item = self.table.item(row, COL_DATOS)
                desc_item  = self.table.item(row, COL_DESC)
                unit_item  = self.table.item(row, COL_UNIT)
                if id_item:    id_item.setText(data["can_id"])
                if datos_item: datos_item.setText(data["datos"])
                if desc_item:  desc_item.setText(data["nombre"])
                if unit_item:  unit_item.setText(data["unidad"])
                self.table.blockSignals(False)
                self.statusBar().showMessage(f"Fila {row+1} actualizada: {data['nombre']}")

    # ── Table toolbar actions ───────────────────────────────────────────────

    def _add_empty_row(self):
        dlg = RowDialog(self, title="Nueva solicitud CAN")
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.result_data()
            if d:
                self._insert_row(**d)
                self.table.scrollToBottom()
                self.statusBar().showMessage(
                    f"Fila añadida: {d['nombre'] or d['datos'] or 'vacía'}"
                )

    def _edit_row_frame(self, row: int):
        """Abre el diálogo de edición pre-cargado con los datos de la fila."""
        if row < 0:
            return
        id_item    = self.table.item(row, COL_ID)
        datos_item = self.table.item(row, COL_DATOS)
        desc_item  = self.table.item(row, COL_DESC)
        unit_item  = self.table.item(row, COL_UNIT)
        fw = self.table.cellWidget(row, COL_FREQ)
        dw = self.table.cellWidget(row, COL_DISP)

        dlg = RowDialog(
            self,
            title="Editar solicitud CAN",
            id_val    = id_item.text()    if id_item    else "7DF",
            datos     = datos_item.text() if datos_item else "",
            freq      = fw.value()        if fw         else 0,
            disparo   = dw.value()        if dw         else 0,
            unico     = bool(self._get_checkbox(row)),
            nombre    = desc_item.text()  if desc_item  else "",
            unidad    = unit_item.text()  if unit_item  else "",
            fabricante= self._is_row_fabricante(row),
        )
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.result_data()
            if d:
                self.table.blockSignals(True)
                if id_item:    id_item.setText(d["id_val"].upper())
                if datos_item: datos_item.setText(d["datos"].upper())
                if desc_item:  desc_item.setText(d["nombre"])
                if unit_item:  unit_item.setText(d["unidad"])
                self.table.blockSignals(False)
                if fw: fw.setValue(d["freq"])
                if dw: dw.setValue(d["disparo"])
                # Disparo único
                uw = self.table.cellWidget(row, COL_UNICO)
                if uw:
                    for cb in uw.findChildren(QCheckBox):
                        cb.setChecked(d["unico"])
                        break
                # Estado FAB
                fab_w = self.table.cellWidget(row, COL_FAB)
                if fab_w:
                    for cb in fab_w.findChildren(QCheckBox):
                        if cb.isChecked() != d["fabricante"]:
                            cb.setChecked(d["fabricante"])
                        break
                # Si cambió datos y es row estándar, actualizar override/desc
                if not d["fabricante"]:
                    datos_key = d["datos"].upper()
                    nombre, unidad = decode_datos(datos_key, d["id_val"])
                    self.table.blockSignals(True)
                    if desc_item: desc_item.setText(nombre)
                    if unit_item: unit_item.setText(unidad)
                    self.table.blockSignals(False)
                else:
                    self._set_override(d["datos"], d["nombre"], d["unidad"])
                self.statusBar().showMessage(
                    f"Fila {row + 1} actualizada: {d['nombre'] or d['datos']}"
                )

    def _open_help(self):
        HelpDialog(self).exec_()

    def _delete_selected(self):
        rows = sorted(
            set(i.row() for i in self.table.selectedItems()), reverse=True
        )
        if not rows:
            QMessageBox.information(self, "Sin selección",
                "Selecciona al menos una fila para eliminar.")
            return
        for r in rows:
            self.table.removeRow(r)
        self.statusBar().showMessage(f"{len(rows)} fila(s) eliminada(s).")

    def _duplicate_selected(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows:
            return
        for row in reversed(rows):
            id_item    = self.table.item(row, COL_ID)
            datos_item = self.table.item(row, COL_DATOS)
            desc_item  = self.table.item(row, COL_DESC)
            unit_item  = self.table.item(row, COL_UNIT)
            fw = self.table.cellWidget(row, COL_FREQ)
            dw = self.table.cellWidget(row, COL_DISP)
            self._insert_row(
                id_val     = id_item.text()    if id_item    else "",
                datos      = datos_item.text() if datos_item else "",
                freq       = fw.value()        if fw         else 0,
                disparo    = dw.value()        if dw         else 0,
                unico      = bool(self._get_checkbox(row)),
                nombre     = desc_item.text()  if desc_item  else "",
                unidad     = unit_item.text()  if unit_item  else "",
                fabricante = self._is_row_fabricante(row),
            )
        self.statusBar().showMessage("Fila(s) duplicada(s).")

    # ── Local file ──────────────────────────────────────────────────────────

    def _open_local(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir solicitudes.csv", "",
            "Archivos CSV (*.csv);;Todos (*)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(path, encoding="latin-1") as f:
                content = f.read()
        count = self._parse_csv(content)
        self.statusBar().showMessage(f"Cargado: {count} solicitudes desde {path}")

    def _save_local(self):
        if not self._check_collisions(interactive=True):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar solicitudes.csv", "solicitudes.csv",
            "Archivos CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._serialize_csv())
        self.statusBar().showMessage(f"Guardado localmente: {path}")


# ── Collision Dialog ──────────────────────────────────────────────────────────

class CollisionDialog(QDialog):
    """
    Muestra las colisiones detectadas y ofrece tres opciones:
      - Corregir automáticamente (ajusta Disparo +50 ms)
      - Ignorar y continuar
      - Cancelar
    """

    RESULT_FIX    = 10
    RESULT_IGNORE = 20
    # QDialog.Rejected == cancelar

    def __init__(self, collisions: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚠  Colisiones detectadas")
        self.setMinimumSize(780, 420)
        self.resize(880, 480)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Cabecera ─────────────────────────────────────────────────────
        lbl_head = QLabel(
            f"<b>Se detectaron {len(collisions)} par(es) de solicitudes que se envían "
            f"en el mismo instante</b> (ventana de análisis: 2 minutos).<br>"
            f"Las colisiones pueden causar errores en el bus CAN.<br>"
            f"Puedes corregirlas automáticamente (se añaden 50 ms al <i>Disparo</i> "
            f"de la fila con número mayor) o ignorarlas y guardar de todas formas."
        )
        lbl_head.setWordWrap(True)
        lbl_head.setTextFormat(Qt.RichText)
        layout.addWidget(lbl_head)

        # ── Tabla de colisiones ───────────────────────────────────────────
        tbl = QTableWidget(len(collisions), 5)
        tbl.setHorizontalHeaderLabels([
            "Fila A", "Variable A",
            "Fila B", "Variable B",
            "Instantes de colisión (ms) …",
        ])
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setDefaultSectionSize(24)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        tbl.setColumnWidth(0, 55)
        tbl.setColumnWidth(2, 55)
        tbl.setColumnWidth(4, 230)

        orange = QColor("#E65100")
        for r, col in enumerate(collisions):
            times_str = ", ".join(str(t) for t in col["times"])
            if col["total"] > len(col["times"]):
                times_str += f"  … ({col['total']} en total)"

            items = [
                f"  {col['row_a'] + 1}",
                col["name_a"],
                f"  {col['row_b'] + 1}",
                col["name_b"],
                times_str,
            ]
            for c, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c in (0, 2):
                    item.setForeground(orange)
                    item.setFont(QFont("Courier New", 10))
                tbl.setItem(r, c, item)

        layout.addWidget(tbl, stretch=1)

        # ── Botones ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()

        btn_fix = QPushButton("✔  Corregir automáticamente")
        btn_fix.setStyleSheet(
            "font-weight: bold; background-color: #2E7D32; color: white; padding: 5px 14px;"
        )
        btn_fix.setToolTip("Añade +50 ms al Disparo de la fila con índice mayor en cada par colisionante")
        btn_fix.clicked.connect(lambda: self.done(self.RESULT_FIX))

        btn_ignore = QPushButton("Ignorar y continuar")
        btn_ignore.setToolTip("Guarda el archivo aunque haya colisiones")
        btn_ignore.clicked.connect(lambda: self.done(self.RESULT_IGNORE))

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_fix)
        btn_row.addStretch()
        btn_row.addWidget(btn_ignore)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)


# ── Row Edit Dialog ───────────────────────────────────────────────────────────

class RowDialog(QDialog):
    """
    Diálogo para introducir o editar los datos completos de una solicitud CAN.
    Se usa al pulsar '+ Fila vacía' y desde 'Clic derecho → Editar trama CAN…'.
    """

    def __init__(self, parent=None, *, title="Solicitud CAN",
                 id_val="7DF", datos="", freq=0, disparo=0,
                 unico=False, nombre="", unidad="", fabricante=True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.setModal(True)
        self._result: dict | None = None
        self._setup_ui(id_val, datos, freq, disparo, unico, nombre, unidad, fabricante)

    def _setup_ui(self, id_val, datos, freq, disparo, unico, nombre, unidad, fabricante):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 12, 14, 12)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        r = 0

        # ── Fabricante ────────────────────────────────────────────────
        grid.addWidget(QLabel("PID de fabricante:"), r, 0, Qt.AlignRight)
        self._fab = QCheckBox("Marcar si este PID no es estándar OBD-II")
        self._fab.setChecked(fabricante)
        self._fab.stateChanged.connect(self._on_datos_changed)
        grid.addWidget(self._fab, r, 1)
        r += 1

        # ── ID CAN ────────────────────────────────────────────────────
        grid.addWidget(QLabel("ID CAN (hex):"), r, 0, Qt.AlignRight)
        self._id = QLineEdit(id_val)
        self._id.setPlaceholderText("7DF")
        self._id.setMaxLength(8)
        self._id.setFont(QFont("Courier New", 10))
        self._id.setToolTip("Identificador del frame CAN. 7DF = broadcast OBD-II estándar")
        grid.addWidget(self._id, r, 1)
        r += 1

        # ── Datos (8 bytes hex) ───────────────────────────────────────
        grid.addWidget(QLabel("Datos CAN (hex, 8 bytes):"), r, 0, Qt.AlignRight)
        self._datos = QLineEdit(datos)
        self._datos.setPlaceholderText("02 01 0C 00 00 00 00 00")
        self._datos.setFont(QFont("Courier New", 10))
        self._datos.setToolTip(
            "8 bytes del payload CAN en hexadecimal (sin espacios o con espacios).\n"
            "Ejemplo OBD-II Modo 01 PID 0C (RPM): 02010C0000000000\n"
            "  Byte 0: longitud (02 = 2 bytes de datos)\n"
            "  Byte 1: modo (01 = datos en tiempo real)\n"
            "  Byte 2: PID (0C = RPM)\n"
            "  Bytes 3-7: padding (00)"
        )
        self._datos.textChanged.connect(self._on_datos_changed)
        grid.addWidget(self._datos, r, 1)
        r += 1

        # ── Descripción ───────────────────────────────────────────────
        grid.addWidget(QLabel("Descripción:"), r, 0, Qt.AlignRight)
        self._desc = QLineEdit(nombre)
        self._desc.setPlaceholderText("Se rellena automáticamente desde la BD OBD-II")
        grid.addWidget(self._desc, r, 1)
        r += 1

        # ── Unidad ────────────────────────────────────────────────────
        grid.addWidget(QLabel("Unidad:"), r, 0, Qt.AlignRight)
        self._unit = QLineEdit(unidad)
        self._unit.setPlaceholderText("rpm, °C, km/h, %…")
        grid.addWidget(self._unit, r, 1)
        r += 1

        # ── Frecuencia ────────────────────────────────────────────────
        grid.addWidget(QLabel("Frecuencia (ms):"), r, 0, Qt.AlignRight)
        self._freq = QSpinBox()
        self._freq.setRange(0, 600_000)
        self._freq.setSingleStep(500)
        self._freq.setSuffix(" ms")
        self._freq.setValue(freq)
        self._freq.setToolTip("Intervalo de repetición. 0 = no repetir periódicamente.")
        grid.addWidget(self._freq, r, 1)
        r += 1

        # ── Disparo ───────────────────────────────────────────────────
        grid.addWidget(QLabel("Disparo inicial (ms):"), r, 0, Qt.AlignRight)
        self._disp = QSpinBox()
        self._disp.setRange(0, 600_000)
        self._disp.setSingleStep(100)
        self._disp.setSuffix(" ms")
        self._disp.setValue(disparo)
        self._disp.setToolTip("Retardo antes del primer envío en ms.")
        grid.addWidget(self._disp, r, 1)
        r += 1

        # ── Disparo único ─────────────────────────────────────────────
        grid.addWidget(QLabel("Disparo único:"), r, 0, Qt.AlignRight)
        self._unico = QCheckBox("Enviar solo una vez al arrancar (ignora Frecuencia)")
        self._unico.setChecked(unico)
        self._unico.stateChanged.connect(self._on_unico_changed)
        grid.addWidget(self._unico, r, 1)
        r += 1

        layout.addLayout(grid)

        if unico:
            self._freq.setValue(0)
            self._freq.setEnabled(False)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_ok = QPushButton("  ✔  Aceptar  ")
        btn_ok.setDefault(True)
        btn_ok.setStyleSheet(
            "font-weight: bold; padding: 5px 18px; "
            "background-color: #1565C0; color: white;"
        )
        btn_ok.clicked.connect(self._on_accept)
        btns.addWidget(btn_ok)
        layout.addLayout(btns)

    def _on_unico_changed(self, state):
        if state == Qt.Checked:
            self._freq.setValue(0)
            self._freq.setEnabled(False)
        else:
            self._freq.setEnabled(True)

    def _on_datos_changed(self):
        if self._fab.isChecked():
            return
        raw = self._datos.text().strip().upper().replace(" ", "")
        if len(raw) >= 6:
            nombre, unidad = decode_datos(raw, self._id.text().strip())
            self._desc.setText(nombre)
            self._unit.setText(unidad)

    def _on_accept(self):
        datos_raw = self._datos.text().strip().upper().replace(" ", "")
        id_raw    = self._id.text().strip().upper() or "7DF"
        self._result = {
            "id_val":    id_raw,
            "datos":     datos_raw,
            "freq":      self._freq.value(),
            "disparo":   self._disp.value(),
            "unico":     self._unico.isChecked(),
            "nombre":    self._desc.text().strip(),
            "unidad":    self._unit.text().strip(),
            "fabricante": self._fab.isChecked(),
        }
        self.accept()

    def result_data(self) -> dict | None:
        return self._result


# ── Help Dialog ───────────────────────────────────────────────────────────────

class HelpDialog(QDialog):
    """Manual de usuario completo de la herramienta."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual de usuario — HUMS V2 Modificador de Solicitudes")
        self.setMinimumSize(820, 700)
        self.resize(900, 780)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tb = QTextBrowser()
        tb.setOpenExternalLinks(False)
        tb.setHtml(self._html())
        layout.addWidget(tb, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(10, 6, 10, 10)
        btn_row.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.setDefault(True)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    @staticmethod
    def _html() -> str:
        return """
<html><head><style>
  body  { font-family: Segoe UI, Arial, sans-serif; font-size: 13px;
          margin: 18px 24px; color: #1a1a1a; }
  h1    { font-size: 20px; color: #0D47A1; border-bottom: 2px solid #0D47A1;
          padding-bottom: 6px; margin-top: 0; }
  h2    { font-size: 15px; color: #1565C0; margin-top: 22px;
          border-bottom: 1px solid #90CAF9; padding-bottom: 3px; }
  h3    { font-size: 13px; color: #37474F; margin-top: 14px; margin-bottom: 4px; }
  p     { margin: 6px 0; line-height: 1.55; }
  ul    { margin: 6px 0 6px 20px; }
  li    { margin-bottom: 4px; line-height: 1.5; }
  code  { background: #ECEFF1; border-radius: 3px; padding: 1px 5px;
          font-family: Courier New, monospace; font-size: 12px; }
  .btn  { background: #E3F2FD; border: 1px solid #90CAF9; border-radius: 4px;
          padding: 1px 7px; font-weight: bold; font-size: 12px; }
  .warn { background: #FFF8E1; border-left: 4px solid #F9A825;
          padding: 6px 10px; margin: 8px 0; border-radius: 2px; }
  .tip  { background: #E8F5E9; border-left: 4px solid #43A047;
          padding: 6px 10px; margin: 8px 0; border-radius: 2px; }
  .col  { background: #F3F4F6; border-left: 4px solid #1976D2;
          padding: 6px 10px; margin: 6px 0; border-radius: 2px; }
  table { border-collapse: collapse; width: 100%; margin: 8px 0; }
  th    { background: #1565C0; color: white; padding: 5px 8px; text-align: left; }
  td    { border: 1px solid #CFD8DC; padding: 4px 8px; }
  tr:nth-child(even) td { background: #F5F9FF; }
</style></head><body>

<h1>HUMS V2 — Manual de Usuario<br>
<span style="font-size:13px;font-weight:normal;color:#555;">
Modificador de Solicitudes OBD-II</span></h1>

<p>Esta herramienta permite <b>visualizar, editar y enviar</b> el archivo
<code>solicitudes.csv</code> del sistema HUMS.
Desde aquí controlas qué variables OBD-II se solicitan al vehículo, con qué
frecuencia y en qué orden, sin necesidad de acceder físicamente al HUMS.</p>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<h2>1. Panel de conexión SSH</h2>

<p>En la parte superior de la ventana encontrarás el panel de conexión:</p>
<ul>
  <li><b>Dirección IP</b> — IP del HUMS en la red local (p. ej.
      <code>192.168.1.100</code>). La app recuerda la última IP usada.</li>
  <li><span class="btn">Probar conexión</span> — verifica que el HUMS es
      accesible y muestra su hostname y versión de kernel. Úsalo siempre antes
      de cargar o guardar para asegurarte de que la red funciona.</li>
  <li><span class="btn">⬇ Cargar CSV</span> — descarga el archivo
      <code>solicitudes.csv</code> actual desde el HUMS y lo muestra en
      la tabla. <b>Los cambios no guardados se pierden.</b></li>
  <li><span class="btn">⬆ Guardar en el HUMS</span> — sube el contenido
      actual de la tabla al HUMS. Antes de escribir, hace una copia de
      seguridad automática (<code>solicitudes.csv.bak</code> y
      <code>pid_units.csv.bak</code>). También actualiza
      <code>pid_units.csv</code> con los nombres y unidades actuales.</li>
  <li><span class="btn">↺ Reiniciar servicio</span> — reinicia el servicio
      <code>OBD.service</code> en el HUMS para que aplique los nuevos
      valores. <b>Solo hace falta después de guardar.</b></li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<h2>2. Barra de herramientas</h2>

<table>
<tr><th>Botón</th><th>Qué hace</th></tr>
<tr><td><b>＋ Añadir desde OBD-II…</b></td>
    <td>Abre el selector de la base de datos OBD-II estándar.
    Busca por nombre, categoría o código PID, y añade la solicitud con
    frecuencia y disparo recomendados.</td></tr>
<tr><td><b>＋ Fila vacía</b></td>
    <td>Abre el diálogo de nueva solicitud para introducir manualmente una
    trama CAN personalizada (PIDs de fabricante o tramas no estándar).</td></tr>
<tr><td><b>✕ Eliminar fila</b></td>
    <td>Elimina la fila actualmente seleccionada (o varias si se seleccionan
    con Ctrl+clic).</td></tr>
<tr><td><b>⧉ Duplicar fila</b></td>
    <td>Crea una copia exacta de la fila seleccionada al final de la tabla,
    preservando todos los parámetros incluido el estado de fabricante.</td></tr>
<tr><td><b>📂 Abrir CSV local</b></td>
    <td>Carga un archivo <code>solicitudes.csv</code> desde tu ordenador,
    sin necesidad de conexión SSH.</td></tr>
<tr><td><b>💾 Guardar CSV local</b></td>
    <td>Guarda el contenido actual de la tabla en un archivo CSV en tu
    ordenador.</td></tr>
<tr><td><b>⚠ Verificar colisiones</b></td>
    <td>Analiza si dos o más solicitudes se enviarían exactamente en el mismo
    milisegundo dentro de una ventana de 2 minutos, lo que podría causar
    errores en el bus CAN.</td></tr>
<tr><td><b>? Ayuda</b></td>
    <td>Muestra este manual.</td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<h2>3. La tabla de solicitudes</h2>

<p>Cada fila de la tabla representa una solicitud CAN que el sistema HUMS
enviará periódicamente al vehículo. Las columnas visibles son:</p>

<div class="col"><b>Descripción</b> — Nombre de la variable en español.
En filas estándar OBD-II se rellena automáticamente desde la base de datos.
En filas de fabricante es editable directamente (fondo amarillo).</div>

<div class="col"><b>Unidad</b> — Unidad de medida del valor (rpm, °C, km/h…).
Igual que Descripción: automática en estándar, editable en fabricante.</div>

<div class="col"><b>Frecuencia (ms)</b> — Cada cuántos milisegundos se repite
el envío. <code>0</code> = no se repite periódicamente (se combina con
Disparo para enviarse solo una vez o al arrancar).</div>

<div class="col"><b>Disparo (ms)</b> — Retardo en ms antes del <i>primer</i>
envío desde que arranca el servicio. Permite escalonar las solicitudes para
evitar saturar el bus CAN en el arranque.</div>

<div class="col"><b>Disparo Único</b> — Si está marcado, la solicitud se
envía <b>una sola vez</b> al arrancar (independientemente de la frecuencia,
que se fija a 0 automáticamente). Útil para solicitar el VIN, los DTC, etc.</div>

<div class="col"><b>Fabricante</b> — Indica que este PID no pertenece al
estándar OBD-II. Al marcarlo, los campos Descripción y Unidad se vuelven
editables (fondo amarillo) y el cambio se guarda permanentemente en tu
ordenador para futuras sesiones.</div>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<h2>4. Añadir solicitudes</h2>

<h3>4.1 Desde la base de datos OBD-II estándar</h3>
<p>Pulsa <b>＋ Añadir desde OBD-II…</b>. Se abre un selector con más de
160 variables estándar organizadas por categoría. Puedes:</p>
<ul>
  <li>Buscar por texto libre (nombre, PID hex, unidad, descripción).</li>
  <li>Filtrar por categoría (Motor, Temperatura, Presión, Sensores O2…).</li>
  <li>Ver la trama CAN, la fórmula de conversión y la descripción en el
      panel inferior antes de confirmar.</li>
  <li>Ajustar Frecuencia, Disparo y Disparo Único antes de añadir.</li>
</ul>
<div class="tip">La app sugiere automáticamente un valor de Disparo que no
colisione con las solicitudes ya existentes de la misma frecuencia.</div>

<h3>4.2 Fila vacía (trama personalizada)</h3>
<p>Pulsa <b>＋ Fila vacía</b>. Se abre el diálogo <i>Nueva solicitud CAN</i>
con los siguientes campos:</p>
<ul>
  <li><b>PID de fabricante</b> — marcar para PIDs no estándar.</li>
  <li><b>ID CAN (hex)</b> — identificador del frame. <code>7DF</code> es el
      broadcast OBD-II estándar para consultar a cualquier ECU.</li>
  <li><b>Datos CAN (hex, 8 bytes)</b> — payload del frame. Puedes escribirlo
      con o sin espacios: <code>02010C0000000000</code> o
      <code>02 01 0C 00 00 00 00 00</code>. Si no marcas Fabricante, la
      Descripción y la Unidad se rellenan automáticamente.</li>
  <li><b>Descripción / Unidad</b> — se rellenan solos para PIDs estándar.
      Para fabricante, escríbelos manualmente.</li>
  <li><b>Frecuencia, Disparo, Disparo único</b> — ver columnas de la tabla.</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<h2>5. Editar solicitudes</h2>

<h3>5.1 Editar trama CAN (ID y datos)</h3>
<p>Haz <b>clic derecho</b> sobre la fila → <b>✎ Editar trama CAN…</b>.
Se abre el mismo diálogo pre-cargado con los valores actuales de la fila.
Esta es la <b>única forma</b> de modificar los bytes del frame CAN.</p>

<h3>5.2 Editar Frecuencia y Disparo</h3>
<p>Haz doble clic sobre el SpinBox de Frecuencia o Disparo directamente en
la tabla y escribe el nuevo valor. También puedes usar las flechas del
SpinBox.</p>

<h3>5.3 Editar Descripción y Unidad (solo filas Fabricante)</h3>
<p>Si la fila tiene el checkbox <b>Fabricante</b> marcado (fondo amarillo),
haz doble clic sobre la celda de Descripción o Unidad para editarla. El
cambio se guarda automáticamente en tu ordenador para futuras sesiones.</p>

<h3>5.4 Cambiar el PID por otro de la base OBD-II</h3>
<p>Clic derecho → <b>⇄ Cambiar PID desde OBD-II…</b>. Permite sustituir
la trama de una fila existente eligiendo un PID diferente del selector.</p>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<h2>6. PIDs de fabricante</h2>

<p>Algunos vehículos usan PIDs propietarios que no están en el estándar
OBD-II. Para manejarlos:</p>
<ol>
  <li>Añade la solicitud con <b>＋ Fila vacía</b> y marca
      <i>PID de fabricante</i>. Introduce la trama CAN del fabricante,
      la descripción que quieras y la unidad.</li>
  <li>El fondo de la fila se vuelve <b style="background:#FFF8E1;padding:1px 4px">
      amarillo claro</b> para distinguirla visualmente.</li>
  <li>El nombre y la unidad que asignes quedan guardados en
      <code>~/.config/hums_pid_overrides.json</code>. La próxima vez que
      abras la app y cargues el CSV, la fila se reconocerá automáticamente.</li>
  <li>Para volver a la interpretación estándar OBD-II: clic derecho →
      <b>↺ Restablecer a estándar OBD-II</b>. Esto borra el override y
      restaura el nombre y la unidad de la base de datos.</li>
</ol>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<h2>7. Detección de colisiones</h2>

<p>Una <b>colisión</b> ocurre cuando dos solicitudes se programan para
enviarse exactamente en el mismo milisegundo. En un bus CAN esto puede causar
errores de arbitraje y pérdidas de datos.</p>

<p>La detección se activa automáticamente al guardar. También puedes
ejecutarla manualmente con <b>⚠ Verificar colisiones</b>.</p>

<p>Cuando se detecta una colisión aparece un diálogo que muestra los pares
afectados y los instantes exactos. Tienes tres opciones:</p>
<ul>
  <li><b>✔ Corregir automáticamente</b> — la app añade <b>+50 ms</b> al
      Disparo de la fila con índice mayor en cada par colisionante y repite
      el proceso hasta que no queden colisiones.</li>
  <li><b>Ignorar y continuar</b> — guarda el archivo aunque existan
      colisiones (útil si sabes que el bus CAN del vehículo lo tolera).</li>
  <li><b>Cancelar</b> — vuelve a la tabla sin guardar para que puedas
      ajustar los valores manualmente.</li>
</ul>
<div class="tip"><b>Consejo para evitar colisiones:</b> usa el campo
<i>Disparo</i> para escalonar las solicitudes. Por ejemplo, si tienes cuatro
solicitudes a 1000 ms, ponles disparos de 0, 100, 200 y 300 ms
respectivamente.</div>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<h2>8. Guardar y aplicar cambios</h2>

<h3>8.1 Guardar en el HUMS</h3>
<ol>
  <li>Asegúrate de que la IP es correcta y la conexión funciona
      (botón <i>Probar conexión</i>).</li>
  <li>Pulsa <b>⬆ Guardar en el HUMS</b>. La app ejecuta la verificación
      de colisiones. Si no hay colisiones (o las corriges/ignoras), pide
      confirmación y sube los archivos.</li>
  <li>Se generan copias de seguridad automáticas
      (<code>.bak</code>) de los archivos anteriores.</li>
  <li>Pulsa <b>↺ Reiniciar servicio</b> para que el sistema aplique los
      cambios. <b>El vehículo debe estar encendido y conectado al lector.</b>
      </li>
</ol>

<h3>8.2 Guardar en local</h3>
<p>Usa <b>💾 Guardar CSV local</b> para exportar el archivo a tu ordenador.
Puedes copiarlo manualmente al HUMS más tarde o usarlo como copia de
seguridad.</p>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<h2>9. Estructura del archivo CSV</h2>

<p>El archivo <code>solicitudes.csv</code> tiene las siguientes columnas:</p>
<table>
<tr><th>Columna</th><th>Descripción</th><th>Ejemplo</th></tr>
<tr><td><code>ID</code></td><td>Identificador CAN (hex)</td><td><code>7DF</code></td></tr>
<tr><td><code>Datos</code></td><td>8 bytes del payload (hex, 16 chars)</td><td><code>02010C0000000000</code></td></tr>
<tr><td><code>Frecuencia</code></td><td>Intervalo de repetición en ms</td><td><code>200</code></td></tr>
<tr><td><code>Disparo</code></td><td>Retardo inicial en ms</td><td><code>0</code></td></tr>
<tr><td><code>Disparo Único</code></td><td>1 = enviar solo una vez, 0 = periódico</td><td><code>0</code></td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<h2>10. Estructura del frame CAN OBD-II</h2>

<p>Para introducir tramas manualmente es útil conocer el formato:</p>
<table>
<tr><th>Byte</th><th>Nombre</th><th>Valor típico</th><th>Descripción</th></tr>
<tr><td>0</td><td>Longitud</td><td><code>02</code></td><td>Nº de bytes de datos que siguen</td></tr>
<tr><td>1</td><td>Modo</td><td><code>01</code></td><td>Servicio OBD (01=datos en tiempo real, 03=DTC, 09=info vehículo, 22=UDS)</td></tr>
<tr><td>2</td><td>PID</td><td><code>0C</code></td><td>Identificador del parámetro (p. ej. 0C=RPM)</td></tr>
<tr><td>3–7</td><td>Padding</td><td><code>00</code></td><td>Bytes de relleno hasta completar 8 bytes</td></tr>
</table>
<p><b>Ejemplos frecuentes:</b></p>
<ul>
  <li>RPM: <code>02010C0000000000</code> (Modo 01, PID 0C)</li>
  <li>Velocidad: <code>02010D0000000000</code> (Modo 01, PID 0D)</li>
  <li>Temperatura refrigerante: <code>0201050000000000</code> (Modo 01, PID 05)</li>
  <li>DTC almacenados: <code>0103000000000000</code> (Modo 03)</li>
  <li>VIN: <code>0209020000000000</code> (Modo 09, tipo 02)</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<h2>11. Preguntas frecuentes (FAQ)</h2>

<h3>¿Por qué no puedo editar la Descripción o la Unidad de una fila?</h3>
<p>Las filas de PIDs estándar OBD-II tienen Descripción y Unidad protegidas
para evitar modificaciones accidentales. Para editarlas, marca el checkbox
<b>Fabricante</b> de esa fila o usa clic derecho → <i>Editar trama CAN…</i>
y activa la casilla de fabricante.</p>

<h3>¿Cómo veo el ID CAN y los bytes de datos?</h3>
<p>Haz clic derecho sobre la fila → <b>✎ Editar trama CAN…</b>. El diálogo
muestra y permite editar tanto el ID CAN como los 8 bytes del payload.</p>

<h3>¿Qué pasa si pongo Frecuencia = 0 sin marcar Disparo Único?</h3>
<p>La solicitud se enviará exactamente una vez, en el instante indicado
por el campo Disparo. Si Disparo también es 0, se enviará nada más arrancar
el servicio.</p>

<h3>¿Puedo añadir varias veces el mismo PID?</h3>
<p>Sí, aunque raramente tiene sentido. El sistema HUMS procesará ambas
respuestas. Lo más útil es tener el mismo PID a diferentes frecuencias,
aunque esto genera tráfico extra.</p>

<h3>Error SSH: Unable to connect to port 22</h3>
<p>Posibles causas:</p>
<ul>
  <li>El servicio todavía no se ha activado.</li>
  <li>La IP es incorrecta.</li>
  <li>El HUMS no está encendido o no está en la misma red.</li>
</ul>

<h3>¿Dónde se guardan los PIDs de fabricante personalizados?</h3>
<p>En <code>~/.config/hums_pid_overrides.json</code> en tu ordenador.
Este archivo es independiente del CSV y persiste entre sesiones. Si lo
borras, perderás los nombres personalizados (pero no los datos del CSV).</p>

<h3>¿Qué hace exactamente el botón "Reiniciar servicio"?</h3>
<p>Ejecuta <code>sudo systemctl restart OBD.service</code> en el HUMS
vía SSH. El servicio OBD lee el <code>solicitudes.csv</code> al arrancar,
por lo que hay que reiniciarlo para que los nuevos valores tengan efecto.
<b>No reinicies el servicio mientras el vehículo esté en marcha salvo que
sepas lo que haces.</b></p>

<h3>¿Cuál es la frecuencia mínima recomendada?</h3>
<p>Depende del bus CAN del vehículo, pero como guía general:</p>
<ul>
  <li>Variables críticas (RPM, velocidad): 200–500 ms.</li>
  <li>Variables de confort (temperatura, presión): 1000–5000 ms.</li>
  <li>Variables de diagnóstico (DTC, VIN): solo al arrancar (Disparo único).</li>
</ul>
<p>Con demasiadas solicitudes a frecuencias muy bajas el bus CAN puede
saturarse y el vehículo podría no responder a todas.</p>

<h3>¿La herramienta modifica el comportamiento del vehículo?</h3>
<p>No. Solo envía solicitudes de lectura (modo pasivo). No escribe ningún
parámetro en las ECUs del vehículo.</p>

</body></html>
"""


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    import os

    # En Windows, la configuración de red requiere privilegios de administrador.
    # Si no los tenemos (p. ej. al ejecutar el script directamente en desarrollo),
    # relanzamos con UAC. El .exe ya lo pide automáticamente vía su manifiesto.
    if platform.system() == "Windows" and not is_admin():
        request_admin_restart()
        return

    # Necesario para algunas distribuciones Linux con Wayland
    if "WAYLAND_DISPLAY" in os.environ and "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("HUMS Modificador Solicitudes")
    app.setApplicationVersion("1.0")

    palette = app.palette()
    palette.setColor(QPalette.Highlight, QColor("#1565C0"))
    palette.setColor(QPalette.HighlightedText, QColor("white"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
