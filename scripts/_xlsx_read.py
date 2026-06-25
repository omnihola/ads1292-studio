# scripts/_xlsx_read.py
from __future__ import annotations

import re
import zipfile
from html import unescape
from pathlib import Path

_SHEET_NAME_RE = re.compile(r'<sheet [^>]*name="([^"]*)"')
_ROW_RE = re.compile(r"<row\b[^>]*>(.*?)</row>", re.DOTALL)
# Each cell carries exactly one of <v>..</v> (number) or <t>..</t> (inline string).
_CELL_VALUE_RE = re.compile(r"<v>(.*?)</v>|<t>(.*?)</t>", re.DOTALL)


def read_xlsx_semantic(path: Path) -> dict:
    """Semantic-only XLSX read: sheet names (workbook.xml order) + cell text per row.

    Deliberately ignores styles, column widths, formulas, and zip internals.
    sheet1.xml / sheet2.xml are matched to sheet names by their workbook order.
    """
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        workbook = zf.read("xl/workbook.xml").decode("utf-8")
        sheet_names = _SHEET_NAME_RE.findall(workbook)
        sheets: dict[str, list[list[str]]] = {}
        for order, name in enumerate(sheet_names, start=1):
            xml = zf.read(f"xl/worksheets/sheet{order}.xml").decode("utf-8")
            sheets[name] = _rows(xml)
    return {"sheet_names": sheet_names, "sheets": sheets}


def _rows(xml: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for row_xml in _ROW_RE.findall(xml):
        cells = [unescape(v if v else t) for v, t in _CELL_VALUE_RE.findall(row_xml)]
        rows.append(cells)
    return rows
