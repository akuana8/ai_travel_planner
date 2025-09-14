# src/pdf_generator.py
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_itinerary_pdf(title: str, body_text: str):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(tmp.name, pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, h - 50, title)
    c.setFont("Helvetica", 10)
    y = h - 80
    for line in body_text.split("\n"):
        if y < 60:
            c.showPage()
            y = h - 60
            c.setFont("Helvetica", 10)
        c.drawString(50, y, line)
        y -= 14
    c.save()
    return tmp.name
