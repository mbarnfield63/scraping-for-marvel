#!/usr/bin/env python3
"""Convert every HTML <table> in MinerU full.md files to one sheet each in an .xlsx.

Usage: python scripts/md_tables_to_xlsx.py <full.md | dir> [...]
A directory is searched recursively for full.md. Output: <key>_tables.xlsx next to each full.md.
Sheet "T<n>" = n-th table in the file; row 1 = nearest preceding "Table ..." caption (if any),
table starts at row 3. Cells are kept as text exactly as OCR'd (no number conversion, LaTeX untouched).
Stdlib only (hand-written minimal xlsx), so no openpyxl needed.
"""
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.sax.saxutils import escape

BAD = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


class Grid(HTMLParser):
    """Parse one <table> into a rectangular list of rows, expanding rowspan/colspan."""

    def __init__(self):
        super().__init__()
        self.rows, self.cell, self.pend = [], None, {}  # pend: (row, col) -> text for rowspan carry

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tr":
            self.flush()
            self.rows.append([])
        elif tag in ("td", "th"):
            self.cell = {"t": "", "rs": int(a.get("rowspan") or 1), "cs": int(a.get("colspan") or 1)}
        elif tag == "br" and self.cell is not None:
            self.cell["t"] += " "

    def flush(self):  # append trailing slots of the current row covered by an earlier rowspan
        if self.rows:
            r, row = len(self.rows) - 1, self.rows[-1]
            while (r, len(row)) in self.pend:
                row.append(self.pend.pop((r, len(row))))

    def handle_data(self, d):
        if self.cell is not None:
            self.cell["t"] += d

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            r, row, c = len(self.rows) - 1, self.rows[-1], self.cell
            while (r, len(row)) in self.pend:  # skip slots covered by an earlier rowspan
                row.append(self.pend.pop((r, len(row))))
            t = " ".join(c["t"].split())
            for i in range(c["cs"]):
                row.append(t if i == 0 else "")
                for k in range(1, c["rs"]):
                    self.pend[(r + k, len(row) - 1)] = t if i == 0 else ""
            self.cell = None


def col(n):  # 0 -> A
    s = ""
    n += 1
    while n:
        n, m = divmod(n - 1, 26)
        s = chr(65 + m) + s
    return s


def sheet_xml(rows):
    out = []
    for r, row in enumerate(rows, 1):
        cells = "".join(
            f'<c r="{col(c)}{r}" t="inlineStr"><is><t xml:space="preserve">{escape(BAD.sub("", v))}</t></is></c>'
            for c, v in enumerate(row) if v != ""
        )
        out.append(f'<row r="{r}">{cells}</row>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            + "".join(out) + "</sheetData></worksheet>")


def write_xlsx(path, sheets):  # sheets: [(name, rows)]
    n = len(sheets)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, n + 1))
                   + "</Types>")
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="{escape(nm)}" sheetId="{i}" r:id="rId{i}"/>' for i, (nm, _) in enumerate(sheets, 1))
                   + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, n + 1))
                   + "</Relationships>")
        for i, (_, rows) in enumerate(sheets, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml(rows))


def convert(md):
    text = Path(md).read_text(encoding="utf-8")
    sheets, last = [], 0
    for m in re.finditer(r"<table>.*?</table>", text, re.S):
        g = Grid()
        g.feed(m.group(0))
        g.flush()
        before = [l.strip() for l in text[last:m.start()].splitlines() if l.strip()]
        cap = before[-1] if before and re.match(r"(?i)\W*table\b", before[-1]) else ""
        w = max((len(r) for r in g.rows), default=0)
        rows = [[cap]] + [[]] + [r + [""] * (w - len(r)) for r in g.rows]
        sheets.append((f"T{len(sheets) + 1}", rows))
        last = m.end()
    if sheets:
        out = Path(md).with_name(f"{Path(md).parent.name}_tables.xlsx")
        write_xlsx(out, sheets)
        print(f"{out}: {len(sheets)} tables")
    else:
        print(f"{md}: no tables")


if __name__ == "__main__":
    for a in sys.argv[1:] or ["."]:
        p = Path(a)
        for f in sorted(p.rglob("full.md")) if p.is_dir() else [p]:
            convert(f)
