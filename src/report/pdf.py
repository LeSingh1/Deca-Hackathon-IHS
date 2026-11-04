"""
Lender/accountant-ready PDF, generated server-side with reportlab.

Contents: headline, fee table, options considered, MCA APR disclosure with the
balance-paydown chart, contract redlines, actions taken (with sandbox labels
and the approval record), and sources/methodology. Every figure comes from
the run state, which comes from src/finance.
"""
from __future__ import annotations

import io
from datetime import date
from typing import Any

from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..agents import fixtures

INK = colors.HexColor("#1f1a14")
MUTED = colors.HexColor("#6b6257")
RULE = colors.HexColor("#d9cfbf")
PAPER = colors.HexColor("#f6f1e7")
MONEY = colors.HexColor("#1f6b45")
TRAP = colors.HexColor("#b0391f")

CATEGORY_LABEL = {
    "interchange": "Interchange (pass-through)", "assessment": "Network assessments (pass-through)",
    "processor_markup": "Processor markup", "junk_fee": "Junk fee", "equipment_lease": "Equipment lease",
}

_ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=_ss["Title"], fontName="Times-Bold", fontSize=22, leading=26, textColor=INK, alignment=TA_LEFT, spaceAfter=4)
H2 = ParagraphStyle("h2", parent=_ss["Heading2"], fontName="Times-Bold", fontSize=14, leading=18, textColor=INK, spaceBefore=14, spaceAfter=6)
BODY = ParagraphStyle("body", parent=_ss["BodyText"], fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7.5, leading=10, textColor=MUTED)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8, leading=10)


def m(x: float | None, cents: bool = True) -> str:
    if x is None:
        return "-"
    sign = "-" if x < 0 else ""
    return f"{sign}${abs(x):,.2f}" if cents else f"{sign}${abs(x):,.0f}"


def pct(x: float, dp: int = 2) -> str:
    return f"{x * 100:.{dp}f}%"


def _table(rows: list[list[Any]], widths: list[float], money_cols: tuple[int, ...] = (), bold_last: bool = False) -> Table:
    t = Table(rows, colWidths=widths, repeatRows=1)
    style = [
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for c in money_cols:
        style.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
        style.append(("FONT", (c, 1), (c, -1), "Courier", 8))
    if bold_last:
        style += [("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 8), ("LINEABOVE", (0, -1), (-1, -1), 0.8, INK)]
    t.setStyle(TableStyle(style))
    return t


def _mca_chart(schedule: list[dict], payback: float) -> Drawing:
    d = Drawing(6.6 * inch, 2.0 * inch)
    lp = LinePlot()
    lp.x, lp.y, lp.width, lp.height = 40, 22, 6.6 * inch - 60, 2.0 * inch - 40
    lp.data = [[(p["day"], p["balance"]) for p in schedule], [(p["day"], p["paid"]) for p in schedule]]
    lp.lines[0].strokeColor, lp.lines[0].strokeWidth = TRAP, 1.6
    lp.lines[1].strokeColor, lp.lines[1].strokeWidth = MUTED, 1.0
    lp.xValueAxis.valueMin, lp.xValueAxis.valueMax = 0, max(p["day"] for p in schedule)
    lp.yValueAxis.valueMin, lp.yValueAxis.valueMax = 0, payback
    lp.yValueAxis.labelTextFormat = lambda v: f"${v / 1000:.0f}k"
    lp.xValueAxis.labelTextFormat = lambda v: f"day {v:.0f}"
    for ax in (lp.xValueAxis, lp.yValueAxis):
        ax.labels.fontName, ax.labels.fontSize, ax.labels.fillColor = "Helvetica", 7, MUTED
        ax.strokeColor = RULE
    d.add(lp)
    d.add(String(lp.x + lp.width * 0.62, lp.y + lp.height * 0.18, "Balance owed", fontName="Helvetica-Bold", fontSize=7, fillColor=TRAP))
    d.add(String(lp.x + lp.width * 0.62, lp.y + lp.height * 0.78, "Total paid to funder", fontName="Helvetica-Bold", fontSize=7, fillColor=MUTED))
    return d


def build_report(state: dict[str, Any], run_id: str) -> bytes:
    st = state["statement"]
    b = state["baseline"]
    v = state["verdict"]
    win = v["winner_option"]
    mca = state["mca"]
    offer = fixtures.load("mca_offer_fastfund")
    approval = state.get("approval")
    executed = state.get("executed", [])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            title=f"ShadowBuyer review - {st['merchant']['name']}", author="ShadowBuyer")
    W = letter[0] - 1.5 * inch
    s: list[Any] = []

    s.append(Paragraph(f"Card-processing &amp; financing review<br/>{st['merchant']['name']}", H1))
    s.append(Paragraph(
        f"{st['merchant']['address']} &middot; MID {st['merchant']['mid']} &middot; Statement period "
        f"{st['period']['label']} &middot; Processor {st['processor']} &middot; Prepared {date.today():%B %d, %Y} "
        f"by ShadowBuyer (run {run_id})", SMALL))
    s.append(Spacer(1, 10))

    head = Table([
        ["Effective rate today", "Negotiated rate", "Back in your pocket", f"{offer['lender']} offer"],
        [pct(b.current_rate), pct(win["effective_rate"]), f"{m(win['annual_savings'], False)}/yr",
         f"~{mca.apr * 100:.0f}% APR"],
        [f"{m(b.current_cost)} on {m(st['monthly_volume'], False)} volume", win["label"].split(":")[0] + " deal",
         f"{m(win['annual_savings'] / 12)}/mo", f"advertised as {offer['factor_rate']:.2f} factor"],
    ], colWidths=[W / 4] * 4)
    head.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER), ("BOX", (0, 0), (-1, -1), 0.8, INK),
        ("FONT", (0, 0), (-1, 0), "Helvetica", 7.5), ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("FONT", (0, 1), (-1, 1), "Times-Bold", 18), ("TEXTCOLOR", (2, 1), (2, 1), MONEY), ("TEXTCOLOR", (3, 1), (3, 1), TRAP),
        ("FONT", (0, 2), (-1, 2), "Helvetica", 7), ("TEXTCOLOR", (0, 2), (-1, 2), MUTED),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    s.append(head)

    # 1. Fee table
    s.append(Paragraph("1. What the statement actually charges", H2))
    rows = [["Line", "Description", "Detail", "Category", "Amount"]]
    for li in state["classified"]:
        rows.append([li["id"], Paragraph(li["description"], CELL), Paragraph(li.get("detail") or "", CELL),
                     Paragraph(CATEGORY_LABEL.get(li["category"], li["category"]), CELL), m(li["amount"])])
    rows.append(["", "Total fees", "", f"effective rate {pct(b.current_rate)}", m(b.current_cost)])
    s.append(_table(rows, [0.45 * inch, 2.1 * inch, 1.35 * inch, 1.6 * inch, 0.9 * inch], money_cols=(4,), bold_last=True))
    bd = state["breakdown"]
    s.append(Spacer(1, 4))
    s.append(Paragraph(
        f"Pass-through cost (interchange + network assessments): <b>{m(bd['pass_through'])}</b>. "
        f"Processor-controlled (markup + junk fees), the negotiable part: <b>{m(bd['processor_controlled'])}</b>/month. "
        f"Equipment lease: {m(bd['equipment_lease'])}/month.", BODY))

    # 2. Options
    s.append(Paragraph("2. Options considered (first-year net, after exit costs)", H2))
    rows = [["Option", "Rate", "Annual savings", "One-time costs", "First-year net"]]
    for o in v["options"]:
        rows.append([Paragraph(("<b>Chosen:</b> " if o["key"] == v["winner"] else "") + o["label"], CELL),
                     pct(o["effective_rate"]), m(o["annual_savings"]), m(o["one_time_costs"]), m(o["net_first_year"])])
    s.append(_table(rows, [2.9 * inch, 0.7 * inch, 1.0 * inch, 0.95 * inch, 0.95 * inch], money_cols=(2, 3, 4)))
    s.append(Spacer(1, 4))
    s.append(Paragraph(v["rationale"], BODY))
    ec = b.exit_cost
    s.append(Paragraph(
        f"Cost to exit the current agreement today ({ec.months_remaining} months left): ETF {m(ec.flat_fee)} + "
        f"liquidated damages {m(ec.liquidated_damages)} + accelerated lease {m(ec.lease_buyout)} = <b>{m(ec.total)}</b>.", SMALL))

    # 3. MCA disclosure
    s.append(KeepTogether([
        Paragraph(f"3. {offer['lender']} merchant cash advance: true cost", H2),
        _table([
            ["Advertised", "Advance", "Cash received", "Total repaid", "Cost of money", "Daily debit", "Days to repay", "Est. APR"],
            [f"{offer['factor_rate']:.2f} factor", m(mca.advance, False), m(mca.net_funded, False), m(mca.payback, False),
             m(mca.finance_charge, False), m(mca.daily_remittance), str(mca.term_days), pct(mca.apr, 1)],
        ], [0.85 * inch, 0.75 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch],
            money_cols=(1, 2, 3, 4, 5)),
        Spacer(1, 6),
        _mca_chart(state["mca_schedule"], mca.payback),
        Paragraph(
            f"Estimated APR = daily internal rate of return on the remittance schedule x 365, assuming "
            f"{offer['holdback_pct'] * 100:.0f}% of estimated daily card sales ({m(b.annual_volume / 365)}/day). "
            f"Effective annual rate (compounded): {pct(mca.effective_annual_rate, 0)}. Recommendation: do not sign.", SMALL),
    ]))

    # 4. Redlines
    s.append(Paragraph("4. Contract traps and requested changes", H2))
    rows = [["Document", "Clause", "Severity", "At risk", "Why it matters / what to ask for"]]
    for r in state["redlines"]:
        rows.append([Paragraph("MCA offer" if r["doc"] == "mca_offer" else "Processing agreement", CELL),
                     Paragraph(r["title"], CELL),
                     r["severity"], m(r["dollars_at_risk"]) if r["dollars_at_risk"] else "-",
                     Paragraph(f"{r['why']}<br/><i>Ask for:</i> {r['revised']}", CELL)])
    s.append(_table(rows, [0.95 * inch, 1.0 * inch, 0.55 * inch, 0.75 * inch, 3.75 * inch], money_cols=(3,)))

    # 5. Actions
    s.append(Paragraph("5. Actions taken", H2))
    if approval and approval.approved:
        s.append(Paragraph(f"Owner approval received by SMS (\"{approval.body}\", approval id {approval.approval_id}). "
                           "Nothing was sent or moved before this approval.", BODY))
        rows = [["Action", "Provider", "Reference", "Amount", "Status"]]
        for a in executed:
            status = a["detail"].get("status", "")
            if a["action"] == "fee_receipt":
                status = f"$48.20 ticket: {m(a['detail']['old_fee'])} -> {m(a['detail']['new_fee'])}"
            rows.append([a["action"].replace("_", " "), a["provider"] + (" (sandbox)" if a["sandbox"] else ""),
                         a["ref"], m(a["amount"]), Paragraph(status, CELL)])
        s.append(_table(rows, [1.1 * inch, 1.3 * inch, 1.9 * inch, 0.8 * inch, 1.9 * inch], money_cols=(3,)))
        s.append(Paragraph("Sandbox: rep email is a dry run; the savings sweep is a Stripe test-mode payment "
                           "(production rail: FedNow instant payment to the owner's reserve account).", SMALL))
    else:
        s.append(Paragraph("No actions taken: the owner did not approve.", BODY))

    # 6. Sources
    s.append(Paragraph("6. Sources and methodology", H2))
    src_rows = [["Figure", "Source", "As of", "Illustrative"]]
    for q in state["quotes"]:
        src_rows.append([Paragraph(q["label"], CELL), Paragraph(q["source"], CELL), q["as_of"], "yes" if q["illustrative"] else "no"])
    src_rows.append([Paragraph("MCA offer, merchant agreement", CELL),
                     Paragraph("Fictional documents created for this demo", CELL), "2026-10", "yes"])
    s.append(_table(src_rows, [1.8 * inch, 3.4 * inch, 0.8 * inch, 0.8 * inch]))
    s.append(Spacer(1, 4))
    s.append(Paragraph(
        "All dollar amounts, rates and APRs in this report are computed by deterministic, unit-tested calculators "
        "(ShadowBuyer src/finance). AI agents read documents, classify fees, negotiate and draft language; they do "
        "not produce figures. Merchant, processor, lender and documents in this demo are fictional. This report is "
        "informational and is not legal or financial advice.", SMALL))

    doc.build(s)
    return buf.getvalue()
