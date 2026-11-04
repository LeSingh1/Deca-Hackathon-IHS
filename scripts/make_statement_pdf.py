"""Render fixtures/statement_marios_trattoria_oct.json as a realistic-looking
processor statement PDF (the 'photo' the owner texts). Run: python scripts/make_statement_pdf.py"""
from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
st = json.loads((ROOT / "fixtures" / "statement_marios_trattoria_oct.json").read_text())
out = ROOT / "fixtures" / "statement_marios_trattoria_oct.pdf"

c = canvas.Canvas(str(out), pagesize=letter)
W, H = letter
c.setTitle(f"{st['processor']} statement {st['period']['label']}")
c.setFillColor(colors.HexColor("#1f3a5f"))
c.rect(0, H - 80, W, 80, fill=1, stroke=0)
c.setFillColor(colors.white)
c.setFont("Helvetica-Bold", 18)
c.drawString(40, H - 45, st["processor"].upper())
c.setFont("Helvetica", 10)
c.drawString(40, H - 62, "MERCHANT STATEMENT  -  FICTIONAL SAMPLE FOR DEMONSTRATION")
c.setFillColor(colors.black)
y = H - 110
c.setFont("Helvetica-Bold", 11)
c.drawString(40, y, st["merchant"]["name"])
c.setFont("Helvetica", 9)
c.drawString(40, y - 14, st["merchant"]["address"])
c.drawString(40, y - 27, f"Merchant ID {st['merchant']['mid']}")
c.drawRightString(W - 40, y, f"Statement period: {st['period']['label']}")
c.drawRightString(W - 40, y - 14, f"{st['period']['start']} to {st['period']['end']}")

y -= 60
c.setFont("Helvetica-Bold", 10)
c.drawString(40, y, "SUMMARY")
c.setFont("Helvetica", 9)
rows = [("Total card sales", f"${st['monthly_volume']:,.2f}"),
        ("Number of transactions", f"{st['transaction_count']:,}"),
        ("Total fees", f"${st['stated_total_fees']:,.2f}")]
for i, (k, v) in enumerate(rows):
    c.drawString(40, y - 16 - i * 13, k)
    c.drawRightString(300, y - 16 - i * 13, v)

y -= 80
c.setFont("Helvetica-Bold", 10)
c.drawString(40, y, "FEES")
c.setFont("Helvetica-Bold", 8)
c.drawString(40, y - 16, "DESCRIPTION")
c.drawString(330, y - 16, "DETAIL")
c.drawRightString(W - 40, y - 16, "AMOUNT")
c.line(40, y - 20, W - 40, y - 20)
c.setFont("Helvetica", 9)
yy = y - 34
for li in st["line_items"]:
    c.drawString(40, yy, li["description"])
    c.drawString(330, yy, li.get("detail") or "")
    c.drawRightString(W - 40, yy, f"${li['amount']:,.2f}")
    yy -= 15
c.line(40, yy + 6, W - 40, yy + 6)
c.setFont("Helvetica-Bold", 9)
c.drawString(40, yy - 8, "TOTAL FEES")
c.drawRightString(W - 40, yy - 8, f"${st['stated_total_fees']:,.2f}")
c.setFont("Helvetica-Oblique", 7)
c.drawString(40, 40, "Fees may change upon 30 days' notice provided by message on this statement. "
             "Continued processing constitutes acceptance.")
c.showPage()
c.save()
print("wrote", out)
