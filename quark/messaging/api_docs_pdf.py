# Copyright (c) 2026
"""Build a print-style PDF manual for Joyce's external messaging API."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

_FONTS_DIR = Path(__file__).resolve().parent / "fonts"
_FONTS_REGISTERED = False

FONT_SANS = "JoyceSans"
FONT_SANS_MED = "JoyceSans-Medium"
FONT_SANS_BOLD = "JoyceSans-Bold"
FONT_SANS_ITALIC = "JoyceSans-Italic"
FONT_MONO = "JoyceMono"
FONT_MONO_MED = "JoyceMono-Medium"

INK = colors.HexColor("#12141a")
INK_SOFT = colors.HexColor("#3d4450")
RULE = colors.HexColor("#e4e0d8")
PAPER = colors.HexColor("#faf8f4")
CODE_BG = colors.HexColor("#f3efe6")
ACCENT = colors.HexColor("#c45c26")
HEAD_BG = colors.HexColor("#12141a")


def _register_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    plex = (
        (FONT_SANS, "IBMPlexSans-Regular.ttf"),
        (FONT_SANS_MED, "IBMPlexSans-Medium.ttf"),
        (FONT_SANS_BOLD, "IBMPlexSans-SemiBold.ttf"),
        (FONT_SANS_ITALIC, "IBMPlexSans-Italic.ttf"),
        (FONT_MONO, "IBMPlexMono-Regular.ttf"),
        (FONT_MONO_MED, "IBMPlexMono-Medium.ttf"),
    )
    liberation = (
        (FONT_SANS, "LiberationSans-Regular.ttf"),
        (FONT_SANS_MED, "LiberationSans-Bold.ttf"),
        (FONT_SANS_BOLD, "LiberationSans-Bold.ttf"),
        (FONT_SANS_ITALIC, "LiberationSans-Italic.ttf"),
        (FONT_MONO, "LiberationMono-Regular.ttf"),
        (FONT_MONO_MED, "LiberationMono-Bold.ttf"),
    )
    use = plex if (_FONTS_DIR / "IBMPlexSans-Regular.ttf").is_file() else liberation
    for name, filename in use:
        path = _FONTS_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing guide font {path}")
        pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily(
        FONT_SANS,
        normal=FONT_SANS,
        bold=FONT_SANS_BOLD,
        italic=FONT_SANS_ITALIC,
        boldItalic=FONT_SANS_BOLD,
    )
    _FONTS_REGISTERED = True


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "kicker": ParagraphStyle(
            "kicker",
            fontName=FONT_SANS_MED,
            fontSize=8,
            leading=11,
            textColor=ACCENT,
            spaceAfter=6,
            tracking=1.2,
        ),
        "title": ParagraphStyle(
            "title",
            fontName=FONT_SANS_BOLD,
            fontSize=26,
            leading=32,
            textColor=INK,
            spaceAfter=8,
        ),
        "lede": ParagraphStyle(
            "lede",
            fontName=FONT_SANS,
            fontSize=11.5,
            leading=17,
            textColor=INK_SOFT,
            spaceAfter=16,
            alignment=TA_JUSTIFY,
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName=FONT_SANS_BOLD,
            fontSize=13.5,
            leading=18,
            textColor=INK,
            spaceBefore=18,
            spaceAfter=8,
        ),
        "h3": ParagraphStyle(
            "h3",
            fontName=FONT_SANS_MED,
            fontSize=11,
            leading=15,
            textColor=INK,
            spaceBefore=12,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "body",
            fontName=FONT_SANS,
            fontSize=10,
            leading=15,
            textColor=INK_SOFT,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
        ),
        "step": ParagraphStyle(
            "step",
            fontName=FONT_SANS,
            fontSize=10,
            leading=15,
            textColor=INK_SOFT,
            leftIndent=14,
            spaceAfter=4,
        ),
        "code": ParagraphStyle(
            "code",
            fontName=FONT_MONO,
            fontSize=8,
            leading=11.5,
            textColor=INK,
        ),
        "cell": ParagraphStyle(
            "cell",
            fontName=FONT_SANS,
            fontSize=9,
            leading=12.5,
            textColor=INK_SOFT,
        ),
        "cellh": ParagraphStyle(
            "cellh",
            fontName=FONT_SANS_MED,
            fontSize=8.5,
            leading=12,
            textColor=INK,
        ),
        "foot": ParagraphStyle(
            "foot",
            fontName=FONT_SANS,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#8a8580"),
        ),
        "footr": ParagraphStyle(
            "footr",
            fontName=FONT_SANS,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#8a8580"),
            alignment=TA_RIGHT,
        ),
    }


def _draw_chrome(canvas, doc) -> None:
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(HEAD_BG)
    canvas.rect(0, h - 14 * mm, w, 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h - 14 * mm, 3.2 * mm, 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(FONT_SANS_MED, 8)
    canvas.drawString(18 * mm, h - 8.6 * mm, "JOYCE")
    canvas.setFont(FONT_SANS, 8)
    canvas.drawRightString(w - 18 * mm, h - 8.6 * mm, "Messaging API  ·  integrator guide")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(18 * mm, 12 * mm, w - 18 * mm, 12 * mm)
    canvas.setFillColor(colors.HexColor("#8a8580"))
    canvas.setFont(FONT_SANS, 8)
    canvas.drawString(18 * mm, 7 * mm, "joyce.oddjobs.tech")
    canvas.drawRightString(w - 18 * mm, 7 * mm, f"{doc.page}")
    canvas.restoreState()


def _code_block(text: str, styles: dict) -> Table:
    inner = Preformatted(text.rstrip() + "\n", styles["code"])
    table = Table([[inner]], colWidths=[170 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("BOX", (0, 0), (-1, -1), 0.3, RULE),
                ("LINEBEFORE", (0, 0), (0, -1), 2.2, ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _table(rows: list[list[str]], styles: dict, col_widths=None) -> Table:
    data = [
        [
            Paragraph(_esc(cell), styles["cellh"] if i == 0 else styles["cell"])
            for cell in row
        ]
        for i, row in enumerate(rows)
    ]
    table = Table(data, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, RULE),
                ("BOX", (0, 0), (-1, -1), 0.4, INK),
            ]
        )
    )
    return table


def build_messaging_api_pdf(*, send_url: str, workspace_name: str = "") -> bytes:
    """Return PDF bytes for the integrator guide."""
    _register_fonts()
    styles = _styles()
    buffer = BytesIO()

    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        title="Joyce Messaging API",
        author="Joyce",
        subject="How to send SMS and receive delivery reports",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="body",
        showBoundary=0,
    )
    doc.addPageTemplates(
        [PageTemplate(id="manual", frames=frame, onPage=_draw_chrome)]
    )

    s = []
    s.append(Paragraph("INTEGRATOR GUIDE", styles["kicker"]))
    s.append(Paragraph("Messaging API", styles["title"]))
    lede = (
        "This is the short manual we would hand a developer who needs to send SMS "
        "from another system. You talk only to Joyce. Joyce talks to Jasmin, "
        "waits for delivery reports, and can optionally ping your own webhook."
    )
    if workspace_name:
        lede += f" Examples below are for the <b>{_esc(workspace_name)}</b> workspace."
    s.append(Paragraph(lede, styles["lede"]))

    s.append(Paragraph("1.  What you are calling", styles["h2"]))
    s.append(
        Paragraph(
            "One HTTPS endpoint accepts every send. Joyce looks at the JSON and "
            "decides whether this is one message, the same text to many numbers, "
            "or a personalised batch. You do not pick a separate bulk URL.",
            styles["body"],
        )
    )
    s.append(_code_block(f"POST {send_url}\nContent-Type: application/json", styles))
    s.append(Spacer(1, 4))
    s.append(
        Paragraph(
            "Put the workspace token on every request. Either header works:",
            styles["body"],
        )
    )
    s.append(
        _code_block(
            "Authorization: Bearer <messaging_api_token>\n"
            "X-Joyce-Token: <messaging_api_token>",
            styles,
        )
    )

    s.append(Paragraph("2.  Turn it on in Joyce", styles["h2"]))
    s.append(Paragraph("Open <b>Workspace settings</b>, then:", styles["body"]))
    s.append(
        Paragraph(
            "1. Enable <b>Joyce messaging API</b> and save. A token is created "
            "for you (an existing token is kept).",
            styles["step"],
        )
    )
    s.append(
        Paragraph(
            "2. Copy the bearer token. Use the refresh icon only when you want to rotate it.",
            styles["step"],
        )
    )
    s.append(
        Paragraph(
            "3. If this workspace uses <b>My own Jasmin</b> and you want true bulk, "
            "set the REST API base URL (usually port 8080) so Joyce can call "
            f"<font face='{FONT_MONO}'>sendbatch</font>.",
            styles["step"],
        )
    )
    s.append(
        Paragraph(
            "4. Optionally set an <b>external DLR URL</b>, HTTP method, retry delay, "
            "and max retries. Joyce still records the receipt even if that webhook is down.",
            styles["step"],
        )
    )

    s.append(Paragraph("3.  Send SMS", styles["h2"]))
    s.append(
        Paragraph(
            f"<font face='{FONT_MONO}'>username</font> must be an enabled Jasmin user "
            "in this workspace. Numbers work best in international form without a plus, "
            f"for example <font face='{FONT_MONO}'>256700000001</font>.",
            styles["body"],
        )
    )

    s.append(Paragraph("One number", styles["h3"]))
    s.append(
        _code_block(
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
            styles,
        )
    )

    s.append(Paragraph("Same text, many numbers", styles["h3"]))
    s.append(
        _code_block(
            '{\n'
            '  "username": "u1_myuser",\n'
            '  "to": ["256700000001", "256700000002"],\n'
            '  "content": "Promo text",\n'
            '  "client_batch_id": "broadcast-99",\n'
            '  "client_message_ids": ["msg-a", "msg-b"]\n'
            "}",
            styles,
        )
    )

    s.append(Paragraph("A different line for each person", styles["h3"]))
    s.append(
        _code_block(
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
            styles,
        )
    )

    s.append(Paragraph("Your own ids (optional, max 128 characters)", styles["h3"]))
    s.append(
        _table(
            [
                ["Field", "What it tags"],
                [
                    "client_message_id",
                    "One destination (top-level or inside messages[]). Alias: message_id.",
                ],
                [
                    "client_message_ids",
                    "List in the same order as a multi-value to.",
                ],
                [
                    "client_batch_id",
                    "The whole submit. Alias: broadcast_id.",
                ],
            ],
            styles,
            col_widths=[48 * mm, 122 * mm],
        )
    )
    s.append(Spacer(1, 6))
    s.append(
        Paragraph(
            "Jasmin still mints its own message UUID (and a REST batch id when bulk "
            "goes through sendbatch). Joyce stores your ids and sends them back on DLR "
            "forwards so your app never has to speak Jasmin’s identifiers.",
            styles["body"],
        )
    )

    s.append(Paragraph("How Joyce routes the submit", styles["h3"]))
    s.append(
        _table(
            [
                ["How many destinations", "REST URL on the workspace?", "What happens"],
                ["1", "Does not matter", "Synchronous classic HTTP /send"],
                ["2 or more", "Yes", "Chunked Jasmin REST sendbatch"],
                ["2 or more", "No", "Celery queue: classic /send, one by one"],
            ],
            styles,
            col_widths=[42 * mm, 52 * mm, 76 * mm],
        )
    )

    s.append(Paragraph("4.  What you get back", styles["h2"]))
    s.append(
        Paragraph(
            "<b>200</b> means Joyce submitted (or queued via REST) in this request. "
            "<b>202</b> means <font face='%s'>bulk_async</font>: accepted, workers "
            "will hit Jasmin in the background. <font face='%s'>mode</font> is "
            "<font face='%s'>single</font>, <font face='%s'>bulk_rest</font>, or "
            "<font face='%s'>bulk_async</font>. The <font face='%s'>messages</font> "
            "array is capped at 100 rows; look up the rest in Operate with "
            "<font face='%s'>batch_id</font>."
            % ((FONT_MONO,) * 7),
            styles["body"],
        )
    )
    s.append(
        _code_block(
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
            styles,
        )
    )

    s.append(Paragraph("5.  Delivery reports", styles["h2"]))
    s.append(
        Paragraph(
            "Jasmin always tells Joyce first. Your webhook is a courtesy copy, not "
            "the source of truth.",
            styles["body"],
        )
    )
    s.append(
        Paragraph(
            "1. Jasmin calls Joyce at "
            f"<font face='{FONT_MONO}'>GET|POST {{JOYCE_PUBLIC_BASE_URL}}/dlr</font>.",
            styles["step"],
        )
    )
    s.append(Paragraph("2. Joyce updates the outbound message row.", styles["step"]))
    s.append(
        Paragraph(
            "3. If you set an external DLR URL, Joyce queues a forward (GET or POST).",
            styles["step"],
        )
    )
    s.append(
        Paragraph(
            "4. Failed forwards retry (default 5 times, 60 seconds apart). A dead "
            "webhook never blocks internal DLR handling.",
            styles["step"],
        )
    )
    s.append(Paragraph("What we send your webhook", styles["h3"]))
    s.append(
        Paragraph(
            "POST is a JSON body. GET uses the same fields as query parameters. "
            "Jasmin’s original DLR keys are included, plus:",
            styles["body"],
        )
    )
    s.append(
        _table(
            [
                ["Field", "Meaning"],
                ["client_message_id", "Your optional id from send"],
                ["client_batch_id", "Your optional broadcast id from send"],
                ["joyce_message_id", "Joyce OutboundMessage primary key"],
                ["joyce_batch_id", "Joyce batch id for the submit"],
                ["jasmin_msg_id", "Gateway UUID (id on the raw DLR)"],
                ["jasmin_batch_id", "REST chunk batch id, when bulk used REST"],
                ["to / from", "Addresses"],
                ["status / dlr_status", "Joyce status and the raw DLR status"],
            ],
            styles,
            col_widths=[48 * mm, 122 * mm],
        )
    )
    s.append(Spacer(1, 8))
    s.append(
        Paragraph(
            f"In your app, match on <font face='{FONT_MONO}'>client_message_id</font>, "
            f"or on <font face='{FONT_MONO}'>client_batch_id</font> plus "
            f"<font face='{FONT_MONO}'>to</font>. You do not need Jasmin to accept "
            "your ids.",
            styles["body"],
        )
    )

    s.append(Paragraph("6.  REST bulk progress", styles["h2"]))
    s.append(
        Paragraph(
            f"When Joyce uses <font face='{FONT_MONO}'>sendbatch</font>, it registers "
            f"<font face='{FONT_MONO}'>{{JOYCE_PUBLIC_BASE_URL}}/batch-callback</font>. "
            "Jasmin calls that URL per item so Joyce can store "
            f"<font face='{FONT_MONO}'>jasmin_msg_id</font> before the DLR arrives. "
            "You do not call this URL yourself.",
            styles["body"],
        )
    )

    doc.build(s)
    return buffer.getvalue()


def write_messaging_api_pdf(
    path: str | Path,
    *,
    send_url: str = "https://joyce.oddjobs.tech/api/v1/messaging/send/",
    workspace_name: str = "",
) -> Path:
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


if __name__ == "__main__":
    import argparse

    root = Path(__file__).resolve().parents[2]
    default_out = root / "docs" / "joyce-messaging-api.pdf"
    parser = argparse.ArgumentParser(description="Generate Joyce messaging API PDF.")
    parser.add_argument("-o", "--output", type=Path, default=default_out)
    parser.add_argument(
        "--send-url",
        default="https://joyce.oddjobs.tech/api/v1/messaging/send/",
    )
    parser.add_argument("--workspace", default="")
    args = parser.parse_args()
    path = write_messaging_api_pdf(
        args.output, send_url=args.send_url, workspace_name=args.workspace
    )
    print(f"Wrote {path} ({path.stat().st_size} bytes)")
