#!/usr/bin/env python3
"""
HUMS V2 — Generador del manual de usuario en PDF.

Toma el HTML exacto del botón '? Ayuda' de la app y adapta solo el CSS
para que QTextDocument lo renderice bien en PDF.
El texto es idéntico al de la aplicación, sin añadir ni quitar nada.

Uso:
    python3 generar_manual.py
    python3 generar_manual.py mi_salida.pdf

Salida por defecto: HUMS_V2_Manual_Usuario.pdf
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrinter

from main import HelpDialog


_CSS_PDF = """
  body  { font-family: Arial, sans-serif; font-size: 11pt; color: #111; }
  h1    { font-size: 17pt; color: #0D47A1; margin-bottom: 4px; }
  h2    { font-size: 13pt; color: #1565C0; margin-top: 18px; margin-bottom: 3px; }
  h3    { font-size: 11pt; color: #333; margin-top: 10px; margin-bottom: 2px; font-style: italic; }
  p     { margin: 4px 0; }
  ul    { margin: 4px 0 4px 20px; }
  li    { margin-bottom: 3px; }
  code  { font-family: Courier New, monospace; font-size: 10pt; }
  table { border-collapse: collapse; width: 100%; margin: 6px 0; }
  th    { background-color: #1565C0; color: white; padding: 4px 8px; text-align: left; font-size: 10pt; }
  td    { border: 1px solid #BDBDBD; padding: 4px 7px; font-size: 10pt; }
  blockquote { margin: 6px 0 6px 10px; padding: 4px 8px;
               border-left: 3px solid #999; color: #333; }
"""


def _adapt_for_pdf(html: str) -> str:
    """
    Reemplaza el bloque <style> con CSS compatible con QTextDocument
    y convierte las clases div que QTextDocument no renderiza
    (col, warn, tip) a <blockquote>, manteniendo el texto intacto.
    """
    # 1. Sustituir bloque <style>…</style>
    html = re.sub(r'<style>.*?</style>', f'<style>{_CSS_PDF}</style>',
                  html, flags=re.DOTALL)

    # 2. <div class="col">, <div class="warn">, <div class="tip"> → <blockquote>
    html = re.sub(r'<div class="(?:col|warn|tip)">', '<blockquote>', html)
    html = html.replace('</div>', '</blockquote>')

    # 3. <span class="btn"> → <b>
    html = re.sub(r'<span class="btn">', '<b>', html)
    html = re.sub(r'</span>', '</b>', html)

    return html


def generar_pdf(output_path: str = "HUMS_V2_Manual_Usuario.pdf"):
    app = QApplication.instance() or QApplication(sys.argv)

    html = _adapt_for_pdf(HelpDialog._html())

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(output_path)
    printer.setPageSize(QPrinter.A4)
    printer.setPageMargins(18, 18, 18, 18, QPrinter.Millimeter)

    doc = QTextDocument()
    doc.setHtml(html)
    doc.print_(printer)

    size_kb = Path(output_path).stat().st_size // 1024
    print(f"PDF generado correctamente:")
    print(f"  Archivo : {Path(output_path).resolve()}")
    print(f"  Tamaño  : {size_kb} KB")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "HUMS_V2_Manual_Usuario.pdf"
    generar_pdf(out)
