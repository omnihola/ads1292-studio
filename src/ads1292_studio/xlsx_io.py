from __future__ import annotations

import csv
import re
from pathlib import Path
import zipfile
from xml.sax.saxutils import escape

from ads1292_studio.events import (
    EVENTS_CSV_HEADER,
    DEFAULT_EVENT_SAMPLE_RATE_HZ,
    EventMarker,
    event_id,
    event_sample_indices,
)


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"


def recording_xlsx_path(csv_path: Path | str) -> Path:
    return Path(csv_path).with_suffix(".xlsx")


def write_recording_xlsx(
    csv_path: Path | str,
    *,
    events: tuple[EventMarker, ...] | list[EventMarker] = (),
    sample_rate_hz: float = DEFAULT_EVENT_SAMPLE_RATE_HZ,
) -> Path:
    source = Path(csv_path)
    output = recording_xlsx_path(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as workbook:
        _write_static_parts(workbook)
        workbook.writestr("xl/worksheets/sheet1.xml", _events_sheet_xml(tuple(events), sample_rate_hz))
        workbook.writestr("xl/worksheets/sheet2.xml", _data_sheet_xml(source))
    return output


def _write_static_parts(workbook: zipfile.ZipFile) -> None:
    workbook.writestr(
        "[Content_Types].xml",
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
""",
    )
    workbook.writestr(
        "_rels/.rels",
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
""",
    )
    workbook.writestr(
        "xl/workbook.xml",
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Events" sheetId="1" r:id="rId1"/>
    <sheet name="Data" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>
""",
    )
    workbook.writestr(
        "xl/_rels/workbook.xml.rels",
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
""",
    )
    workbook.writestr(
        "xl/styles.xml",
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Arial"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>
""",
    )
    workbook.writestr(
        "docProps/core.xml",
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:creator>ADS1292 Studio</dc:creator>
  <dc:title>ADS1292 recording</dc:title>
</cp:coreProperties>
""",
    )
    workbook.writestr(
        "docProps/app.xml",
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>ADS1292 Studio</Application>
</Properties>
""",
    )


def _events_sheet_xml(events: tuple[EventMarker, ...], sample_rate_hz: float) -> str:
    rows = [EVENTS_CSV_HEADER]
    for marker in (event.normalized() for event in events):
        sample_indices = event_sample_indices(marker, sample_rate_hz)
        rows.append(
            [
                event_id(marker, sample_rate_hz=sample_rate_hz),
                f"{marker.timestamp_seconds:.6f}",
                f"{marker.end_seconds:.6f}",
                f"{marker.duration_seconds:.6f}",
                sample_indices["start_sample_index"],
                sample_indices["end_sample_index"],
                sample_indices["duration_samples"],
                "interval" if marker.duration_seconds > 0 else "point",
                marker.label,
                marker.notes,
            ]
        )
    return _worksheet_xml(rows)


def _data_sheet_xml(csv_path: Path) -> str:
    with csv_path.open(newline="") as handle:
        reader = csv.reader(handle)
        return _worksheet_xml(reader)


def _worksheet_xml(rows) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n',
        "<sheetData>\n",
    ]
    for row_index, row in enumerate(rows, start=1):
        values = tuple(row)
        parts.append(f'<row r="{row_index}">')
        for column_index, value in enumerate(values, start=1):
            parts.append(_cell_xml(row_index, column_index, value))
        parts.append("</row>\n")
    parts.append("</sheetData>\n</worksheet>\n")
    return "".join(parts)


def _cell_xml(row_index: int, column_index: int, value) -> str:
    reference = f"{_column_name(column_index)}{row_index}"
    text = "" if value is None else str(value)
    if _is_number(text):
        return f'<c r="{reference}"><v>{escape(text)}</v></c>'
    return f'<c r="{reference}" t="inlineStr"><is><t>{escape(_xml_safe(text))}</t></is></c>'


def _xml_safe(text: str) -> str:
    """Drop characters illegal in XML 1.0 (C0 controls except tab/newline/CR)
    so a pasted control byte in a label/notes cell can't corrupt the workbook."""
    return "".join(c for c in text if c in "\t\n\r" or ord(c) >= 0x20)


def _column_name(index: int) -> str:
    name = ""
    current = index
    while current:
        current, remainder = divmod(current - 1, 26)
        name = chr(65 + remainder) + name
    return name


_NUMBER_RE = re.compile(r"^-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?$")


def _is_number(value: str) -> bool:
    # Strict OOXML-safe numeric test: no whitespace, no '+', no underscores, no
    # inf/nan, and no leading-zero integers (e.g. a zero-padded "007" id stays
    # text so Excel doesn't strip the leading zeros).
    return bool(_NUMBER_RE.match(value))
