from io import BytesIO
from datetime import datetime
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_CENTER


def _fmt_dt(value: Optional[Any]) -> str:
    if not value:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _currency(value: Optional[Any]) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def build_payment_receipt_pdf(invoice: dict[str, Any]) -> bytes:
    """Build a payment receipt/invoice PDF (ReportLab)."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleX",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4f46e5"),
        fontSize=20,
    )
    subtitle = ParagraphStyle(
        "SubtitleX",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        textColor=colors.grey,
        fontSize=10,
        spaceAfter=12,
    )
    h2 = ParagraphStyle("H2X", parent=styles["Heading2"], fontSize=13, spaceBefore=10)

    story: list = []
    story.append(Paragraph("Legal Connect", title))
    story.append(Paragraph("Payment Receipt", subtitle))
    story.append(Spacer(1, 6))

    header = [
        ["Receipt", "Invoice to"],
        [f"#{invoice.get('reference', '—')}", invoice.get("payee_name", "")],
    ]
    header_table = Table(header, colWidths=[3 * inch, 3 * inch])
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#4f46e5")),
                ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("FONTSIZE", (0, 0), (0, 0), 12),
                ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c7c7cc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Appointment Details", h2))
    rows = [
        ["Description", f"Legal consultation ({invoice.get('category', 'other')})"],
        ["Lawyer", invoice.get("lawyer_name", "")],
        ["Start time", _fmt_dt(invoice.get("start_time"))],
        ["End time", _fmt_dt(invoice.get("end_time"))],
        ["Payment date", _fmt_dt(invoice.get("created_at"))],
        ["Status", invoice.get("status", "").title()],
    ]
    detail = Table(rows, colWidths=[1.7 * inch, 4.3 * inch])
    detail.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e5ea")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f5f5f7")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(detail)
    story.append(Spacer(1, 12))

    total_row = [
        ["Total Paid", _currency(invoice.get("amount"))],
    ]
    total = Table(total_row, colWidths=[4.3 * inch, 1.7 * inch])
    total.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef2ff")),
                ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
                ("FONTSIZE", (1, 0), (1, 0), 13),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#4f46e5")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c7c7cc")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(total)
    story.append(Spacer(1, 18))
    story.append(
        Paragraph(
            "Thank you for using Legal Connect. This is a system-generated receipt.",
            subtitle,
        )
    )

    doc.build(story)
    return buf.getvalue()


def build_admin_report_pdf(report: dict[str, Any]) -> bytes:
    """Build a simple admin report PDF from a summary dict."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleX",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4f46e5"),
        fontSize=18,
    )
    subtitle = ParagraphStyle(
        "SubtitleX",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        textColor=colors.grey,
        fontSize=10,
    )
    h2 = ParagraphStyle("H2X", parent=styles["Heading2"], fontSize=13)

    story: list = []
    story.append(Paragraph("Legal Connect", title))
    story.append(Paragraph(f"Report: {report.get('report_type', '').title()}", subtitle))
    story.append(Spacer(1, 12))

    summary = report.get("summary", {})
    rows = []
    for key, value in summary.items():
        label = key.replace("_", " ").title()
        if isinstance(value, dict) and value:
            for k2, v2 in value.items():
                rows.append([f"{label} — {k2.replace('_', ' ').title()}", str(v2)])
        else:
            rows.append([label, str(value)])
    if not rows:
        rows.append(["No data", "—"])

    table = Table(rows, colWidths=[3.4 * inch, 3.4 * inch])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e5ea")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f5f5f7")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buf.getvalue()
