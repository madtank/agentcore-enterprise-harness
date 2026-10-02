#!/usr/bin/env python3
"""Render the architecture Markdown to a self-contained HTML report and PDF."""
from html import escape
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import markdown
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
NAVY = "#152d45"
TEAL = "#087f8c"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")

# Shared simple architecture visualization in SVG and PDF drawing coordinates.
NODES = [
    (225, 30, 200, 75, "Release profile", "versions + reviewed artifacts", "control"),
    (470, 30, 225, 75, "AWS Agent Registry", "approved resource discovery", "control"),
    (20, 175, 145, 85, "Developer", "internal chat / client", "runtime"),
    (210, 175, 215, 85, "Application boundary", "identity, sessions, input validation", "runtime"),
    (470, 175, 215, 85, "AgentCore harness", "managed loop + isolated session", "runtime"),
    (735, 175, 245, 85, "AgentCore Gateway", "authenticated + ENFORCE policy", "runtime"),
    (245, 330, 180, 75, "Approved model", "Bedrock inference", "runtime"),
    (470, 330, 215, 75, "Conversation memory", "actor / session scoping", "runtime"),
    (735, 330, 245, 75, "Knowledge + operations", "retrieval / sandbox reads / drafts", "runtime"),
    (210, 460, 770, 65, "Observability + evaluations + release gates", "telemetry, usage, regression evidence and controlled promotion", "ops"),
]
ARROWS = [(470, 67, 425, 67), (325, 105, 325, 175), (165, 217, 210, 217),
          (425, 217, 470, 217), (685, 217, 735, 217), (530, 260, 365, 330),
          (578, 260, 578, 330), (858, 260, 858, 330), (325, 260, 325, 460),
          (650, 405, 650, 460), (855, 405, 855, 460)]


def svg_diagram():
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 555" role="img" aria-label="AgentCore enterprise MVP architecture">',
             '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#71879a"/></marker></defs>',
             '<rect width="1000" height="555" fill="#f8fafc" rx="16"/>']
    for x1, y1, x2, y2 in ARROWS:
        parts.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="#71879a" stroke-width="2" marker-end="url(#arrow)"/>')
    for x, y, width, height, title, detail, kind in NODES:
        fill, border = ("#eef0fa", "#7681b6") if kind == "control" else (("#e5f5f2", "#399486") if kind == "ops" else ("#ffffff", "#8dafc4"))
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" fill="{fill}" stroke="{border}" stroke-width="1.5"/>')
        parts.append(f'<text x="{x+width/2}" y="{y+height/2-4}" text-anchor="middle" fill="{NAVY}" font-family="Arial,sans-serif" font-size="16" font-weight="700">{escape(title)}</text>')
        parts.append(f'<text x="{x+width/2}" y="{y+height/2+19}" text-anchor="middle" fill="#476277" font-family="Arial,sans-serif" font-size="11">{escape(detail)}</text>')
    parts.append('</svg>')
    return ''.join(parts)


class Architecture(Flowable):
    def __init__(self, width):
        super().__init__()
        self.width = width
        self.height = width * .555

    def draw(self):
        canvas = self.canv
        scale = self.width / 1000
        canvas.saveState()
        canvas.scale(scale, scale)
        canvas.setFillColor(colors.HexColor("#f8fafc"))
        canvas.roundRect(0, 0, 1000, 555, 12, fill=1, stroke=0)
        canvas.setStrokeColor(colors.HexColor("#71879a"))
        for x1, y1, x2, y2 in ARROWS:
            canvas.line(x1, 555-y1, x2, 555-y2)
            angle = math.atan2(y2-y1, x2-x1)
            canvas.setFillColor(colors.HexColor("#71879a"))
            path = canvas.beginPath()
            path.moveTo(x2, 555-y2)
            path.lineTo(x2-8*math.cos(angle-.45), 555-(y2-8*math.sin(angle-.45)))
            path.lineTo(x2-8*math.cos(angle+.45), 555-(y2-8*math.sin(angle+.45)))
            path.close()
            canvas.drawPath(path, fill=1, stroke=0)
        for x, y, width, height, title, detail, kind in NODES:
            fill, border = ("#eef0fa", "#7681b6") if kind == "control" else (("#e5f5f2", "#399486") if kind == "ops" else ("#ffffff", "#8dafc4"))
            bottom = 555-y-height
            canvas.setFillColor(colors.HexColor(fill))
            canvas.setStrokeColor(colors.HexColor(border))
            canvas.roundRect(x, bottom, width, height, 10, fill=1, stroke=1)
            canvas.setFillColor(colors.HexColor(NAVY))
            canvas.setFont("DejaVu-Bold", 16)
            canvas.drawCentredString(x+width/2, 555-y-height/2+4, title)
            canvas.setFillColor(colors.HexColor("#476277"))
            canvas.setFont("DejaVu", 10.8)
            canvas.drawCentredString(x+width/2, 555-y-height/2-19, detail)
        canvas.restoreState()


def inline(element):
    result = escape(element.text or "")
    for child in element:
        body = inline(child)
        if child.tag in ("strong", "b"):
            body = f"<b>{body}</b>"
        elif child.tag in ("em", "i"):
            body = f"<i>{body}</i>"
        elif child.tag == "code":
            body = f'<font face="DejaVuMono" size="8.2">{body}</font>'
        elif child.tag == "a":
            href = escape(child.attrib.get("href", ""), quote=True)
            body = f'<a href="{href}" color="{TEAL}">{body}</a>'
        elif child.tag == "br":
            body = "<br/>"
        result += body + escape(child.tail or "")
    return result


def render_pdf(html, destination):
    for name, file in (("DejaVu", "DejaVuSans.ttf"), ("DejaVu-Bold", "DejaVuSans-Bold.ttf"),
                       ("DejaVu-Italic", "DejaVuSans-Oblique.ttf"), ("DejaVuMono", "DejaVuSansMono.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
    pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu-Italic", boldItalic="DejaVu-Bold")
    width = A4[0]-84
    styles = {
        "body": ParagraphStyle("body", fontName="DejaVu", fontSize=9.2, leading=14.2, textColor=colors.HexColor(NAVY), spaceAfter=8),
        "h1": ParagraphStyle("h1", fontName="DejaVu-Bold", fontSize=25, leading=30, spaceAfter=16, textColor=colors.HexColor(NAVY)),
        "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=15, leading=21, spaceBefore=18, spaceAfter=10, keepWithNext=True, textColor=colors.HexColor(TEAL)),
        "h3": ParagraphStyle("h3", fontName="DejaVu-Bold", fontSize=11, leading=16, spaceBefore=10, spaceAfter=7, keepWithNext=True, textColor=colors.HexColor(NAVY)),
        "cell": ParagraphStyle("cell", fontName="DejaVu", fontSize=7.8, leading=11.7, alignment=TA_LEFT),
        "code": ParagraphStyle("code", fontName="DejaVuMono", fontSize=7.4, leading=10.5, wordWrap="CJK", backColor=colors.HexColor("#f1f5f9"), borderPadding=6, spaceAfter=8),
    }
    story = []
    root = ET.fromstring("<main>" + html + "</main>")
    for element in root:
        tag = element.tag
        if tag in ("h1", "h2", "h3"):
            story.append(Paragraph(inline(element), styles[tag]))
        elif tag == "p":
            story.append(Paragraph(inline(element), styles["body"]))
        elif tag in ("ul", "ol"):
            for number, item in enumerate(element.findall("li"), 1):
                prefix = "•" if tag == "ul" else f"{number}."
                story.append(Paragraph(prefix + " " + inline(item), styles["body"]))
        elif tag == "pre":
            code = element.find("code")
            if code is not None and code.attrib.get("class") == "language-mermaid":
                story.append(Architecture(width))
                story.append(Spacer(1, 10))
            else:
                content = "".join(element.itertext())
                story.append(Paragraph(escape(content).replace("\n", "<br/>"), styles["code"]))
        elif tag == "table":
            rows = []
            for row in element.findall(".//tr"):
                rows.append([Paragraph(inline(cell), styles["cell"]) for cell in row])
            columns = len(rows[0])
            fractions = {3: (.20, .37, .43), 4: (.20, .30, .29, .21)}.get(columns)
            col_widths = [width*f for f in fractions] if fractions else [width/columns]*columns
            table = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT", splitInRow=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e7eef4")),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f7f9fb")]),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("BOTTOMPADDING", (0,0), (-1,-1), 8), ("TOPPADDING", (0,0), (-1,-1), 8),
                ("LEFTPADDING", (0,0), (-1,-1), 7), ("RIGHTPADDING", (0,0), (-1,-1), 7),
                ("LINEBELOW", (0,0), (-1,0), .7, colors.HexColor("#9ab3c7")),
            ]))
            story.extend([table, Spacer(1, 10)])

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d5e0e9"))
        canvas.line(42, 35, A4[0]-42, 35)
        canvas.setFont("DejaVu", 7)
        canvas.setFillColor(colors.HexColor("#607589"))
        canvas.drawString(42, 23, "AWS enterprise agent harness · Development MVP · 2 October 2026")
        canvas.drawRightString(A4[0]-42, 23, str(document.page))
        canvas.restoreState()

    document = SimpleDocTemplate(str(destination), pagesize=A4, rightMargin=42, leftMargin=42,
                                 topMargin=40, bottomMargin=48, title="Enterprise agent harness on AWS",
                                 author="Architecture research and MVP planning")
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def main():
    text = (ROOT / "ENTERPRISE-HARNESS-PLAN.md").read_text()
    mermaid = re.search(r'```mermaid\n(.*?)\n```', text, re.S)
    (ROOT / "architecture.mmd").write_text(mermaid.group(1) + "\n")
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc"])
    diagram = svg_diagram()
    (ROOT / "architecture.svg").write_text(diagram)
    visual_body = re.sub(r'<pre><code class="language-mermaid">.*?</code></pre>', diagram, body, flags=re.S)
    css = '''body{margin:0;background:#eef3f7;color:#152d45;font:16px/1.65 system-ui,sans-serif}main{max-width:1000px;margin:40px auto;background:white;padding:48px 64px;border-radius:16px;box-shadow:0 12px 40px #152d4510}h1{font-size:42px;line-height:1.15;max-width:850px}h2{font-size:27px;color:#087f8c;margin-top:46px;line-height:1.3}h3{font-size:20px;margin-top:28px}a{color:#087f8c}table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.5;margin:24px 0}td,th{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #e5edf3}th{background:#e7eef4}tr:nth-child(even){background:#f8fafc}pre{overflow:auto;background:#f2f6f9;padding:20px;border-radius:9px}code{font-size:.9em}svg{width:100%;height:auto;margin:20px 0}li{margin:8px 0}nav{border-left:4px solid #087f8c;background:#f5fafb;padding:14px 22px;margin:28px 0;font-size:14px}nav ul{list-style:none;padding:0}nav li{margin:3px 0} .stamp{font-size:12px;letter-spacing:2px;color:#607589} @media(max-width:700px){main{margin:0;padding:24px 18px;border-radius:0}h1{font-size:32px}table{font-size:12px}td,th{padding:7px}}@media print{body{background:white}main{box-shadow:none;margin:0;padding:0;max-width:none}nav{display:none}h2,h3{break-after:avoid}tr{break-inside:avoid}a{color:inherit}pre{white-space:pre-wrap}}'''
    headings = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body)
    nav = '<nav aria-label="Contents"><strong>Contents</strong><ul>' + ''.join(f'<li><a href="#{id_}">{title}</a></li>' for id_, title in headings) + '</ul></nav>'
    visual_body = visual_body.replace('</h1>', '</h1>'+nav, 1)
    html = f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Enterprise agent harness on AWS</title><style>{css}</style><main><div class="stamp">ARCHITECTURE • RESEARCH • IMPLEMENTATION</div>{visual_body}</main></html>'
    (ROOT / "ENTERPRISE-HARNESS-PLAN.html").write_text(html)
    render_pdf(body, ROOT / "ENTERPRISE-HARNESS-PLAN.pdf")
    print("Rendered HTML, PDF and standalone architecture SVG.")


if __name__ == "__main__":
    main()
