"""Genera el PDF del Punto 1 del Módulo Tres."""

from pathlib import Path

from weasyprint import HTML

ROOT = Path(__file__).resolve().parent
HTML(filename=str(ROOT / "punto-1.html")).write_pdf(
    ROOT / "Punto-1-Definicion-del-caso-de-uso.pdf"
)
