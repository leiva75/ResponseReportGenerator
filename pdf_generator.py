# pdf_generator.py
from __future__ import annotations
from typing import Any
import os

def create_pdf_report(data: Any, output_path: str) -> str:
    """
    Génère un PDF minimaliste.
    Ne doit PAS faire crasher l'app au moment de l'import.
    """
    # Import tardif pour éviter un crash au démarrage si reportlab n'est pas embarqué
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception as e:
        raise RuntimeError(
            "Le module 'reportlab' est requis pour générer des PDFs. "
            "Ajoute 'reportlab' à requirements.txt puis rebuild."
        ) from e

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 60, "Response Report Generator")

    c.setFont("Helvetica", 10)
    y = height - 90
    text = str(data)

    # découpe simple
    for line in text.splitlines() or [text]:
        if y < 50:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 10)
        c.drawString(50, y, line[:120])
        y -= 14

    c.save()
    return output_path
