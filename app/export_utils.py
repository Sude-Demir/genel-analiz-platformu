"""Tüm panellerde ortak kullanılan JSON ve PDF export yardımcıları.

PDF üretimi için fpdf2 + DejaVu Sans (açık lisanslı, Türkçe karakter destekli)
kullanılır; böylece harici bir servise bağımlı olmadan, ş/ğ/ı/ö/ü/ç gibi
karakterleri doğru basan raporlar üretilir.
"""
import json
import os
from datetime import datetime

from fpdf import FPDF

FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "DejaVuSans.ttf")
PAGE_WIDTH = 190  # A4, varsayılan 10mm kenar boşluklarıyla kullanılabilir genişlik


def to_json_bytes(data: dict) -> bytes:
    """Bir sonuç sözlüğünü UTF-8 JSON byte dizisine çevirir (indirme butonları için)."""
    return json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")


class ReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("DejaVu", "", FONT_PATH)
        self.set_auto_page_break(auto=True, margin=15)
        self.set_font("DejaVu", size=11)

    def add_title(self, text: str):
        self.set_font("DejaVu", size=18)
        self.multi_cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
        self.set_font("DejaVu", size=9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"Oluşturulma: {datetime.now():%Y-%m-%d %H:%M}", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def add_heading(self, text: str):
        self.set_font("DejaVu", size=13)
        self.ln(2)
        self.multi_cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(self.get_x(), self.get_y(), self.get_x() + PAGE_WIDTH, self.get_y())
        self.ln(2)
        self.set_font("DejaVu", size=11)

    def add_paragraph(self, text: str):
        self.set_font("DejaVu", size=11)
        self.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def add_bullets(self, items: list[str]):
        self.set_font("DejaVu", size=11)
        for item in items:
            self.multi_cell(0, 6, f"-  {item}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def add_table(self, headers: list[str], rows: list[list], col_widths: list[float] | None = None):
        self.set_font("DejaVu", size=9)
        n = len(headers)
        widths = col_widths or [PAGE_WIDTH / n] * n
        for h, w in zip(headers, widths):
            self.cell(w, 7, str(h), border=1)
        self.ln()
        for row in rows:
            for val, w in zip(row, widths):
                text = str(val)
                if len(text) > 60:
                    text = text[:57] + "..."
                self.cell(w, 7, text, border=1)
            self.ln()
        self.ln(2)


def build_pdf(title: str, blocks: list[dict]) -> bytes:
    """Basit blok listesinden bir PDF raporu üretir.

    Her blok: {"heading": str | None, "type": "paragraph"|"bullets"|"table", "content": ...}
    - paragraph: content bir metin
    - bullets: content bir metin listesi
    - table: content (headers, rows) tuple'ı
    """
    pdf = ReportPDF()
    pdf.add_page()
    pdf.add_title(title)
    for block in blocks:
        if block.get("heading"):
            pdf.add_heading(block["heading"])
        btype = block.get("type", "paragraph")
        content = block.get("content")
        if btype == "bullets":
            pdf.add_bullets(content or ["—"])
        elif btype == "table":
            headers, rows = content
            pdf.add_table(headers, rows)
        else:
            pdf.add_paragraph(content or "—")
    return bytes(pdf.output())
