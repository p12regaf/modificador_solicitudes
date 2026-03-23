"""
Diálogo de selección de variable OBD-II desde la base de datos estándar.
Se abre desde el botón "Añadir desde OBD-II..." de la ventana principal.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QSpinBox, QCheckBox, QAbstractItemView,
    QFrame, QSplitter,
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel
from PyQt5.QtGui import QFont, QColor

from obd_database import OBD_PIDS, CATEGORIAS, OBDPid


class PIDSelectorDialog(QDialog):
    """
    Permite buscar en la base de datos OBD-II y añadir una variable
    con frecuencia y disparo configurables antes de confirmar.

    Uso:
        dlg = PIDSelectorDialog(parent, existing_rows=[...])
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.result_data()  # dict con todos los campos
    """

    def __init__(self, parent=None, existing_rows: list[dict] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar variable OBD-II estándar")
        self.setMinimumSize(1000, 620)
        self.resize(1100, 680)
        self.setModal(True)

        self._existing_rows: list[dict] = existing_rows or []
        self._result: dict | None = None
        self._filtered_pids: list[OBDPid] = list(OBD_PIDS)

        self._setup_ui()
        self._populate_table(self._filtered_pids)

    # ── UI construction ────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        root.addWidget(self._build_filter_row())
        root.addWidget(self._build_table(), stretch=1)
        root.addWidget(self._build_preview_panel())
        root.addLayout(self._build_button_row())

    def _build_filter_row(self) -> QWidget:
        from PyQt5.QtWidgets import QWidget
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Buscar por nombre, PID (hex), unidad o descripción…"
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filter)

        self.cat_combo = QComboBox()
        self.cat_combo.addItems(CATEGORIAS)
        self.cat_combo.setFixedWidth(200)
        self.cat_combo.currentTextChanged.connect(self._apply_filter)

        layout.addWidget(QLabel("Buscar:"))
        layout.addWidget(self.search_input, stretch=1)
        layout.addWidget(QLabel("Categoría:"))
        layout.addWidget(self.cat_combo)

        lbl_count = QLabel()
        lbl_count.setStyleSheet("color: gray; font-size: 11px;")
        self._lbl_count = lbl_count
        layout.addWidget(lbl_count)

        return widget

    def _build_table(self) -> QTableWidget:
        cols = ["PID (hex)", "Modo", "Nombre (ES)", "Nombre (EN)", "Unidad", "Categoría", "Freq. sugerida", "Fórmula"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.setSortingEnabled(True)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)   # Nombre ES: stretch
        self.table.setColumnWidth(0, 80)   # PID
        self.table.setColumnWidth(1, 60)   # Modo
        self.table.setColumnWidth(3, 200)  # Nombre EN
        self.table.setColumnWidth(4, 65)   # Unidad
        self.table.setColumnWidth(5, 160)  # Categoría
        self.table.setColumnWidth(6, 110)  # Freq
        self.table.setColumnWidth(7, 200)  # Fórmula

        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(self._on_accept)

        return self.table

    def _build_preview_panel(self) -> QGroupBox:
        group = QGroupBox("Configuración de la solicitud")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        mono = QFont("Courier New", 11)

        # Row 0: CAN frame preview
        grid.addWidget(QLabel("ID CAN:"), 0, 0, Qt.AlignRight)
        self._prev_id = QLabel("—")
        self._prev_id.setFont(mono)
        grid.addWidget(self._prev_id, 0, 1)

        grid.addWidget(QLabel("Trama (Datos):"), 0, 2, Qt.AlignRight)
        self._prev_datos = QLabel("—")
        self._prev_datos.setFont(mono)
        grid.addWidget(self._prev_datos, 0, 3)

        grid.addWidget(QLabel("Variable:"), 0, 4, Qt.AlignRight)
        self._prev_nombre = QLabel("—")
        self._prev_nombre.setStyleSheet("font-weight: bold;")
        grid.addWidget(self._prev_nombre, 0, 5, 1, 3)

        # Row 1: description
        grid.addWidget(QLabel("Descripción:"), 1, 0, Qt.AlignRight)
        self._prev_desc = QLabel("—")
        self._prev_desc.setStyleSheet("color: #555;")
        self._prev_desc.setWordWrap(True)
        grid.addWidget(self._prev_desc, 1, 1, 1, 7)

        # Row 2: editable params
        grid.addWidget(self._separator(), 2, 0, 1, 8)

        grid.addWidget(QLabel("Frecuencia:"), 3, 0, Qt.AlignRight)
        self.freq_spin = QSpinBox()
        self.freq_spin.setRange(0, 600_000)
        self.freq_spin.setSingleStep(500)
        self.freq_spin.setSuffix(" ms")
        self.freq_spin.setToolTip("0 = no repetir periódicamente")
        grid.addWidget(self.freq_spin, 3, 1)

        lbl_f = QLabel("(0 = no periódico)")
        lbl_f.setStyleSheet("color: gray; font-size: 11px;")
        grid.addWidget(lbl_f, 3, 2)

        grid.addWidget(QLabel("Disparo inicial:"), 3, 3, Qt.AlignRight)
        self.disparo_spin = QSpinBox()
        self.disparo_spin.setRange(0, 600_000)
        self.disparo_spin.setSingleStep(100)
        self.disparo_spin.setSuffix(" ms")
        self.disparo_spin.setToolTip("Retardo antes del primer envío")
        grid.addWidget(self.disparo_spin, 3, 4)

        grid.addWidget(QLabel("Disparo único:"), 3, 5, Qt.AlignRight)
        self.unico_check = QCheckBox()
        self.unico_check.setToolTip("Marcar si la solicitud debe enviarse solo una vez al arrancar")
        grid.addWidget(self.unico_check, 3, 6)

        grid.setColumnStretch(7, 1)
        return group

    def _separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def _build_button_row(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel)

        self.btn_add = QPushButton("  ＋  Añadir esta variable  ")
        self.btn_add.setEnabled(False)
        self.btn_add.setDefault(True)
        self.btn_add.setStyleSheet(
            "font-weight: bold; padding: 6px 18px;"
            "background-color: #1976D2; color: white;"
        )
        self.btn_add.clicked.connect(self._on_accept)
        layout.addWidget(self.btn_add)

        return layout

    # ── Table population ───────────────────────────────────────────────────

    def _populate_table(self, pids: list[OBDPid]):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        self._row_to_pid: list[OBDPid] = []

        for pid in pids:
            row = self.table.rowCount()
            self.table.insertRow(row)

            freq_str = f"{pid.freq_ms} ms" if pid.freq_ms > 0 else "Una vez (disparo único)"

            cells = [
                (pid.pid.upper(), QFont("Courier New", 10), None),
                (pid.mode, QFont("Courier New", 10), None),
                (pid.nombre, None, None),
                (pid.nombre_en, None, QColor("#888888")),
                (pid.unidad, None, None),
                (pid.categoria, None, None),
                (freq_str, None, None),
                (pid.formula, QFont("Courier New", 9), QColor("#666666")),
            ]

            for col, (text, font, color) in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if font:
                    item.setFont(font)
                if color:
                    item.setForeground(color)
                if pid.descripcion:
                    item.setToolTip(pid.descripcion)
                self.table.setItem(row, col, item)

            self._row_to_pid.append(pid)

        self.table.setSortingEnabled(True)
        n = len(pids)
        self._lbl_count.setText(f"{n} variable{'s' if n != 1 else ''}")

    # ── Filtering ──────────────────────────────────────────────────────────

    def _apply_filter(self):
        query = self.search_input.text().strip().lower()
        category = self.cat_combo.currentText()

        result = []
        for pid in OBD_PIDS:
            if category != "Todas" and pid.categoria != category:
                continue
            if query and not any(
                query in field.lower()
                for field in (pid.pid, pid.nombre, pid.nombre_en, pid.unidad,
                              pid.categoria, pid.descripcion, pid.formula)
            ):
                continue
            result.append(pid)

        self._populate_table(result)
        self.btn_add.setEnabled(False)
        self._clear_preview()

    # ── Selection handling ─────────────────────────────────────────────────

    def _on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.btn_add.setEnabled(False)
            self._clear_preview()
            return

        logical_row = rows[0].row()
        # Table may be sorted; map visual row → logical row via the item
        item = self.table.item(rows[0].row(), 0)
        if item is None or logical_row >= len(self._row_to_pid):
            return

        # Find the pid by matching PID hex + mode from the first two columns
        pid_hex = self.table.item(rows[0].row(), 0).text().strip()
        mode = self.table.item(rows[0].row(), 1).text().strip()
        pid = next(
            (p for p in self._row_to_pid if p.pid.upper() == pid_hex and p.mode == mode),
            None,
        )
        if pid is None:
            return

        self._selected_pid = pid
        self.btn_add.setEnabled(True)
        self._update_preview(pid)

    def _update_preview(self, pid: OBDPid):
        self._prev_id.setText(pid.can_id)
        self._prev_datos.setText(pid.datos)
        self._prev_nombre.setText(
            f"{pid.nombre}  [{pid.unidad}]" if pid.unidad else pid.nombre
        )
        desc_parts = []
        if pid.descripcion:
            desc_parts.append(pid.descripcion)
        if pid.formula:
            desc_parts.append(f"Fórmula: {pid.formula}")
        self._prev_desc.setText("  |  ".join(desc_parts) if desc_parts else "—")

        self.freq_spin.setValue(pid.freq_ms)
        self.unico_check.setChecked(pid.disparo_unico)
        self.disparo_spin.setValue(self._suggest_disparo(pid))

    def _clear_preview(self):
        for lbl in (self._prev_id, self._prev_datos, self._prev_nombre, self._prev_desc):
            lbl.setText("—")
        self._selected_pid = None

    # ── Auto-disparo calculation ───────────────────────────────────────────

    def _suggest_disparo(self, pid: OBDPid) -> int:
        """
        Calcula un valor de Disparo que no colisione con los existentes:
        - Para disparos únicos: max(disparos únicos existentes) + 100ms
        - Para periódicos: busca si hay otros con la misma frecuencia
          y sugiere max(sus disparos) + 100ms
        """
        if pid.disparo_unico or pid.freq_ms == 0:
            existing = [
                r.get("disparo", 0)
                for r in self._existing_rows
                if r.get("disparo_unico")
            ]
            return (max(existing) + 100) if existing else 100

        freq = pid.freq_ms
        same_freq = [
            r.get("disparo", 0)
            for r in self._existing_rows
            if r.get("frecuencia") == freq and not r.get("disparo_unico")
        ]
        if not same_freq:
            return 0
        return max(same_freq) + 100

    # ── Confirm ────────────────────────────────────────────────────────────

    def _on_accept(self):
        if not hasattr(self, "_selected_pid") or self._selected_pid is None:
            return
        pid = self._selected_pid
        self._result = {
            "can_id": pid.can_id,
            "datos": pid.datos,
            "frecuencia": self.freq_spin.value(),
            "disparo": self.disparo_spin.value(),
            "disparo_unico": self.unico_check.isChecked(),
            "nombre": pid.nombre,
            "unidad": pid.unidad,
            "pid_hex": pid.pid.upper(),
            "mode": pid.mode,
        }
        self.accept()

    def result_data(self) -> dict | None:
        """Devuelve el dict con los datos del PID seleccionado, o None si se canceló."""
        return self._result
