"""Genera el PDF del Punto 4 a partir del HTML fuente."""

from pathlib import Path

from weasyprint import HTML

ROOT = Path(__file__).resolve().parent
HTML(filename=str(ROOT / "punto-4.html")).write_pdf(ROOT / "Punto-4-Aportes-normativos-y-brechas.pdf")
