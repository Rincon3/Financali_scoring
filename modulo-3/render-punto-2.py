"""Genera el PDF del Punto 2 del Módulo Tres."""

from pathlib import Path

from weasyprint import HTML

ROOT = Path(__file__).resolve().parent
HTML(filename=str(ROOT / "punto-2.html")).write_pdf(
    ROOT / "Punto-2-Analisis-factibilidad-MITRE-ATLAS.pdf"
)
