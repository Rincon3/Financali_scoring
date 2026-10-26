"""Genera el PDF del Punto 2 con WeasyPrint o Chrome como respaldo."""

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "punto-2.html"
OUTPUT = ROOT / "Punto-2-Analisis-factibilidad-MITRE-ATLAS.pdf"


def render_with_weasyprint() -> bool:
    try:
        from weasyprint import HTML

        HTML(filename=str(SOURCE)).write_pdf(OUTPUT)
        return True
    except (ImportError, OSError):
        return False


def render_with_chrome() -> None:
    candidates = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    ]
    browser = next((candidate for candidate in candidates if candidate.exists()), None)
    if browser is None:
        raise RuntimeError(
            "No se encontró WeasyPrint funcional ni un navegador Chromium para renderizar."
        )
    subprocess.run(
        [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={OUTPUT}",
            SOURCE.as_uri(),
        ],
        check=True,
    )


if not render_with_weasyprint():
    render_with_chrome()
