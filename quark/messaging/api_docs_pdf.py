# Copyright (c) 2026
"""Build a PDF guide for Joyce's external messaging API."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_FONTS_DIR = Path(__file__).resolve().parent / "fonts"
_FONTS_REGISTERED = False

# Liberation Sans / Mono — metric-compatible with Arial / Courier New; common in guides.
FONT_SANS = "JoyceSans"
FONT_SANS_BOLD = "JoyceSans-Bold"
FONT_SANS_ITALIC = "JoyceSans-Italic"
FONT_MONO = "JoyceMono"
FONT_MONO_BOLD = "JoyceMono-Bold"


def _register_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    pairs = (
        (FONT_SANS, "LiberationSans-Regular.ttf"),
        (FONT_SANS_BOLD, "LiberationSans-Bold.ttf"),
        (FONT_SANS_ITALIC, "LiberationSans-Italic.ttf"),
        (FONT_MONO, "LiberationMono-Regular.ttf"),
        (FONT_MONO_BOLD, "LiberationMono-Bold.ttf"),
    )
    for name, filename in pairs:
        path = _FONTS_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing guide font {path}. Expected Liberation fonts under {_FONTS_DIR}."
            )
        pdfmetrics.registerFont(TTFont(name, str(path)))

    pdfmetrics.registerFontFamily(
        FONT_SANS,
        normal=FONT_SANS,
        bold=FONT_SANS_BOLD,
        italic=FONT_SANS_ITALIC,
        boldItalic=FONT_SANS_BOLD,
    )
    _FONTS_REGISTERED = True


def build_messaging_api_pdf(*, send_url: str, workspace_name: str = "") -> bytes:
    """Return PDF bytes documenting POST /api/v1/messaging/send/ for integrators."""
    _register_fonts()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Joyce Messaging API",
        author="Joyce",
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "JoyceTitle",
        parent=styles["Heading1"],
        fontName=FONT_SANS_BOLD,
        fontSize=20,
        leading=26,
        spaceAfter=8,
        textColor=colors.HexColor("#171717"),
    )
    h2 = ParagraphStyle(
        "JoyceH2",
        parent=styles["Heading2"],
        fontName=FONT_SANS_BOLD,
        fontSize=13,
        leading=18,
        spaceBefore=16,
        spaceAfter=6,
        textColor=colors.HexColor("#171717"),
    )
    h3 = ParagraphStyle(
        "JoyceH3",
        parent=styles["Heading3"],
        fontName=FONT_SANS_BOLD,
        fontSize=11,
        leading=15,
        spaceBefore=12,
        spaceAfter=4,
        textColor=colors.HexColor("#262626"),
    )
    body = ParagraphStyle(
        "JoyceBody",
        parent=styles["Normal"],
        fontName=FONT_SANS,
        fontSize=10.5,
        leading=15,
        spaceAfter=7,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#404040"),
    )
    code = ParagraphStyle(
        "JoyceCode",
        parent=styles["Code"],
        fontName=FONT_MONO,
        fontSize=8.5,
        leading=12,
        leftIndent=4,
        rightIndent=4,
        spaceBefore=4,
        spaceAfter=8,
        backColor=colors.HexColor("#f5f5f5"),
        textColor=colors.HexColor("#171717"),
    )
    meta = ParagraphStyle(
        "JoyceMeta",
        parent=styles["Normal"],
        fontName=FONT_SANS,
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#737373"),
        spaceAfter=14,
    )

    story = []
    story.append(Paragraph("Joyce Messaging API", title))
    subtitle = "External-facing SMS send API and delivery-report forwarding."
    if workspace_name:
        subtitle += f" Workspace: <b>{_esc(workspace_name)}</b>."
    story.append(Paragraph(subtitle, meta))

    story.append(Paragraph("Overview", h2))
    story.append(
        Paragraph(
            "External applications submit SMS through Joyce. Joyce talks to Jasmin "
            f"(HTTP <font face='{FONT_MONO}'>/send</font> or REST "
            f"<font face='{FONT_MONO}'>/secure/sendbatch</font>) and always receives DLRs "
            f"on its own <font face='{FONT_MONO}'>/dlr</font> endpoint. Optionally, Joyce "
            "forwards DLRs to your external channel URL.",
            body,
        )
    )

    story.append(Paragraph("Enable the API", h2))
    story.append(
        Paragraph(
            "1. Open <b>Workspace settings</b>.<br/>"
            "2. Under <b>External channel</b>, enable <b>Joyce messaging API</b> and "
            "save — a token is generated automatically (existing tokens are kept).<br/>"
            "3. Use the refresh icon beside the token to rotate it; copy the bearer "
            "token for send requests only.<br/>"
            "4. For My own Jasmin, set <b>REST API base URL</b> (port 8080) if you want "
            f"bulk via <font face='{FONT_MONO}'>sendbatch</font>.<br/>"
            "5. Optionally set <b>External DLR URL</b> (method, retry delay, max retries).",
            body,
        )
    )

    story.append(Paragraph("Your send endpoint", h2))
    story.append(
        Paragraph(
            "Use this absolute URL for your workspace (host may vary by environment):",
            body,
        )
    )
    story.append(Preformatted(f"POST {send_url}", code))

    story.append(Paragraph("Authentication", h2))
    story.append(Paragraph("All send requests require a bearer token:", body))
    story.append(Preformatted("Authorization: Bearer <messaging_api_token>", code))
    story.append(Paragraph("Alternatively:", body))
    story.append(Preformatted("X-Joyce-Token: <messaging_api_token>", code))

    story.append(Paragraph("Send SMS", h2))
    story.append(
        Paragraph(
            "Joyce inspects the payload and chooses single vs bulk automatically. "
            f"<font face='{FONT_MONO}'>username</font> must be an <b>enabled</b> Jasmin "
            "user in that workspace.",
            body,
        )
    )

    story.append(Paragraph("Single destination", h3))
    story.append(
        Preformatted(
            '{\n'
            '  "username": "u1_myuser",\n'
            '  "to": "256700000001",\n'
            '  "content": "Hello",\n'
            '  "from": "JOYCE",\n'
            '  "client_message_id": "ord-100-sms-1",\n'
            '  "client_batch_id": "campaign-42",\n'
            '  "dlr_level": 3,\n'
            '  "priority": 0\n'
            "}",
            code,
        )
    )

    story.append(Paragraph("Same content, many destinations", h3))
    story.append(
        Preformatted(
            '{\n'
            '  "username": "u1_myuser",\n'
            '  "to": ["256700000001", "256700000002"],\n'
            '  "content": "Promo text",\n'
            '  "client_batch_id": "broadcast-99",\n'
            '  "client_message_ids": ["msg-a", "msg-b"]\n'
            "}",
            code,
        )
    )

    story.append(Paragraph("Personalized messages", h3))
    story.append(
        Preformatted(
            '{\n'
            '  "username": "u1_myuser",\n'
            '  "client_batch_id": "orders-2026-07-13",\n'
            '  "messages": [\n'
            '    {"to": "256700000001", "content": "Order #100 is ready",\n'
            '     "client_message_id": "ord-100"},\n'
            '    {"to": "256700000002", "content": "Order #101 is ready",\n'
            '     "client_message_id": "ord-101"}\n'
            "  ],\n"
            '  "from": "JOYCE",\n'
            '  "dlr_level": 3\n'
            "}",
            code,
        )
    )

    story.append(Paragraph("Optional correlation IDs (max 128 chars)", h3))
    story.append(
        _table(
            [
                ["Field", "Scope"],
                [
                    "client_message_id",
                    "One destination (top-level or per messages[]). Alias: message_id.",
                ],
                [
                    "client_message_ids",
                    "Parallel list matching a multi-value to.",
                ],
                [
                    "client_batch_id",
                    "Whole submit / broadcast. Alias: broadcast_id.",
                ],
            ]
        )
    )
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "Jasmin still generates its own message UUID and REST batchId. Your IDs "
            "are stored by Joyce and echoed on DLR forwards.",
            body,
        )
    )

    story.append(Paragraph("Routing behaviour", h3))
    story.append(
        _table(
            [
                ["Destinations", "REST API URL?", "Behaviour"],
                ["1", "n/a", "Sync classic HTTP /send"],
                ["2+", "Yes", "Chunked Jasmin REST sendbatch"],
                ["2+", "No", "Async Celery: classic /send one-by-one"],
            ]
        )
    )

    story.append(Paragraph("Response", h3))
    story.append(
        Paragraph(
            "<b>200</b> for single or REST bulk; <b>202</b> when mode is "
            f"<font face='{FONT_MONO}'>bulk_async</font> (accepted; workers submit in the "
            "background). Mode is one of "
            f"<font face='{FONT_MONO}'>single</font>, "
            f"<font face='{FONT_MONO}'>bulk_rest</font>, "
            f"<font face='{FONT_MONO}'>bulk_async</font>. The "
            f"<font face='{FONT_MONO}'>messages</font> array is capped at 100 rows; use "
            f"<font face='{FONT_MONO}'>batch_id</font> in the Operate UI for the rest.",
            body,
        )
    )
    story.append(
        Preformatted(
            '{\n'
            '  "batch_id": "a1b2c3d4e5f6g7h8",\n'
            '  "client_batch_id": "campaign-42",\n'
            '  "mode": "single",\n'
            '  "message_count": 1,\n'
            '  "jasmin_batch_ids": [],\n'
            '  "messages": [\n'
            "    {\n"
            '      "id": 42,\n'
            '      "to": "256700000001",\n'
            '      "status": "submitted",\n'
            '      "client_message_id": "ord-100-sms-1",\n'
            '      "client_batch_id": "campaign-42",\n'
            '      "jasmin_msg_id": "…",\n'
            '      "error": null\n'
            "    }\n"
            "  ],\n"
            '  "messages_truncated": false\n'
            "}",
            code,
        )
    )

    story.append(Paragraph("Delivery reports", h2))
    story.append(
        Paragraph(
            "1. Jasmin always calls Joyce: "
            f"<font face='{FONT_MONO}'>GET|POST {{JOYCE_PUBLIC_BASE_URL}}/dlr</font> "
            f"(or <font face='{FONT_MONO}'>JOYCE_DLR_CALLBACK_URL</font>).<br/>"
            "2. Joyce updates the outbound message.<br/>"
            "3. If External DLR URL is set, Joyce queues an async forward (GET or POST).<br/>"
            "4. Forward failures are retried up to max retries (default 5), waiting "
            "retry delay seconds (default 60). Internal DLR handling is never blocked "
            "by the external channel.",
            body,
        )
    )

    story.append(Paragraph("External DLR payload", h3))
    story.append(
        Paragraph(
            "Joyce forwards an enriched JSON body (POST) or query params (GET):",
            body,
        )
    )
    story.append(
        _table(
            [
                ["Field", "Meaning"],
                ["client_message_id", "Your optional message id from send"],
                ["client_batch_id", "Your optional broadcast/batch id from send"],
                ["joyce_message_id", "Joyce OutboundMessage primary key"],
                ["joyce_batch_id", "Joyce batch id for the submit"],
                ["jasmin_msg_id", "Jasmin gateway UUID (id on the raw DLR)"],
                ["jasmin_batch_id", "Jasmin REST chunk batch id (when used)"],
                ["to / from", "Addresses"],
                ["status / dlr_status", "Joyce status + raw DLR status"],
            ]
        )
    )
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"Match on <font face='{FONT_MONO}'>client_message_id</font> (or "
            f"<font face='{FONT_MONO}'>client_batch_id</font> + "
            f"<font face='{FONT_MONO}'>to</font>) in your app.",
            body,
        )
    )

    story.append(Paragraph("Batch progress callbacks (REST bulk)", h2))
    story.append(
        Paragraph(
            f"When using <font face='{FONT_MONO}'>sendbatch</font>, Joyce registers "
            f"<font face='{FONT_MONO}'>{{JOYCE_PUBLIC_BASE_URL}}/batch-callback</font>. "
            "Jasmin calls this per successful/failed item so Joyce can store "
            f"<font face='{FONT_MONO}'>jasmin_msg_id</font> for later DLR matching.",
            body,
        )
    )

    doc.build(story)
    return buffer.getvalue()


def write_messaging_api_pdf(
    path: str | Path,
    *,
    send_url: str = "https://your-joyce-host/api/v1/messaging/send/",
    workspace_name: str = "",
) -> Path:
    """Write the guide PDF to disk (for docs/ or local preview)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(
        build_messaging_api_pdf(send_url=send_url, workspace_name=workspace_name)
    )
    return out


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _table(rows: list[list[str]]) -> Table:
    data = [
        [Paragraph(_esc(cell), _cell_style(i == 0)) for cell in row]
        for i, row in enumerate(rows)
    ]
    table = Table(data, colWidths=None, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#171717")),
                ("FONTNAME", (0, 0), (-1, 0), FONT_SANS_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e5e5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _cell_style(header: bool) -> ParagraphStyle:
    return ParagraphStyle(
        "JoyceCellHeader" if header else "JoyceCell",
        fontName=FONT_SANS_BOLD if header else FONT_SANS,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#171717" if header else "#404040"),
    )


if __name__ == "__main__":
    import argparse

    root = Path(__file__).resolve().parents[2]
    default_out = root / "docs" / "joyce-messaging-api.pdf"
    parser = argparse.ArgumentParser(description="Generate Joyce messaging API PDF docs.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_out,
        help=f"Output path (default: {default_out})",
    )
    parser.add_argument(
        "--send-url",
        default="https://your-joyce-host/api/v1/messaging/send/",
        help="Example absolute send URL embedded in the guide",
    )
    parser.add_argument("--workspace", default="", help="Optional workspace name")
    args = parser.parse_args()
    path = write_messaging_api_pdf(
        args.output, send_url=args.send_url, workspace_name=args.workspace
    )
    print(f"Wrote {path} ({path.stat().st_size} bytes)")
