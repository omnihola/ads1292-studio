// io/src/XlsxIo.cpp
// Ports xlsx_io.py write_recording_xlsx — 2-tab (Events + Data) XLSX writer.
// NO Qt dependency; uses ZipStoreWriter, event_id, event_sample_indices.
#include "ads1292/io/XlsxIo.h"
#include "ads1292/io/ZipStoreWriter.h"
#include "ads1292/event/EventId.h"

#include <cstdio>
#include <fstream>
#include <regex>
#include <sstream>
#include <string>
#include <vector>

namespace ads1292::io {

// ---------------------------------------------------------------------------
// Path helper
// ---------------------------------------------------------------------------

std::string recording_xlsx_path(const std::string& csv_path) {
    // Replace extension with ".xlsx"
    auto dot = csv_path.rfind('.');
    if (dot != std::string::npos) {
        return csv_path.substr(0, dot) + ".xlsx";
    }
    return csv_path + ".xlsx";
}

// ---------------------------------------------------------------------------
// File-local XML helpers — porting xlsx_io.py exactly
// ---------------------------------------------------------------------------

namespace {

/// Bijective base-26: 1→A, 26→Z, 27→AA.
/// Ports _column_name verbatim.
std::string column_name(int index) {
    std::string name;
    int current = index;
    while (current > 0) {
        int remainder = (current - 1) % 26;
        name = static_cast<char>('A' + remainder) + name;
        current = (current - 1) / 26;
    }
    return name;
}

/// Strict OOXML-safe numeric test.
/// Regex: ^-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?$
/// Leading-zero integers (e.g. "007") → false (stay text).
/// Ports _is_number verbatim.
bool is_number(const std::string& value) {
    static const std::regex NUMBER_RE(
        R"(^-?(0|[1-9]\d*)(\.\d+)?([eE][+-]?\d+)?$)");
    return std::regex_match(value, NUMBER_RE);
}

/// Replace &→&amp;, <→&lt;, >→&gt; (&amp; FIRST, no quote escaping).
/// Ports xml.sax.saxutils.escape default behaviour.
std::string xml_escape(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 16);
    for (char c : s) {
        if (c == '&')       out += "&amp;";
        else if (c == '<')  out += "&lt;";
        else if (c == '>')  out += "&gt;";
        else                out += c;
    }
    return out;
}

/// Drop C0 control chars except \t, \n, \r.
/// Ports _xml_safe verbatim.
std::string xml_safe(const std::string& text) {
    std::string out;
    out.reserve(text.size());
    for (char c : text) {
        if (c == '\t' || c == '\n' || c == '\r' ||
            static_cast<unsigned char>(c) >= 0x20) {
            out += c;
        }
    }
    return out;
}

/// Build a single OOXML cell element.
/// Ports _cell_xml verbatim.
std::string cell_xml(int row, int col, const std::string& value) {
    std::string ref = column_name(col) + std::to_string(row);
    if (is_number(value)) {
        return R"(<c r=")" + ref + R"("><v>)" + xml_escape(value) + "</v></c>";
    }
    return R"(<c r=")" + ref + R"(" t="inlineStr"><is><t>)" +
           xml_escape(xml_safe(value)) + "</t></is></c>";
}

/// Build a complete worksheet XML string from a vector of rows.
/// Ports _worksheet_xml verbatim.
std::string worksheet_xml(const std::vector<std::vector<std::string>>& rows) {
    std::string out;
    out += "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n";
    out += "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">\n";
    out += "<sheetData>\n";
    int row_index = 1;
    for (const auto& row : rows) {
        out += "<row r=\"" + std::to_string(row_index) + "\">";
        int col_index = 1;
        for (const auto& value : row) {
            out += cell_xml(row_index, col_index, value);
            ++col_index;
        }
        out += "</row>\n";
        ++row_index;
    }
    out += "</sheetData>\n</worksheet>\n";
    return out;
}

/// EVENTS_CSV_HEADER from events.py line 73+
static const std::vector<std::string> EVENTS_CSV_HEADER = {
    "event_id",
    "start_seconds",
    "end_seconds",
    "duration_seconds",
    "start_sample_index",
    "end_sample_index",
    "duration_samples",
    "event_type",
    "label",
    "notes",
};

/// Format a double with 6 decimal places, matching Python's f"{x:.6f}".
std::string fmt6(double v) {
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%.6f", v);
    return buf;
}

/// Build the Events worksheet XML.
/// Ports _events_sheet_xml verbatim.
std::string events_sheet_xml(const std::vector<ads1292::EventMarker>& events,
                              double sample_rate_hz) {
    std::vector<std::vector<std::string>> rows;
    rows.push_back(EVENTS_CSV_HEADER);
    for (const auto& ev_raw : events) {
        ads1292::EventMarker ev = ev_raw.normalized();
        ads1292::EventSampleIndices idx =
            ads1292::event_sample_indices(ev, sample_rate_hz);
        std::string eid = ads1292::event_id(ev, sample_rate_hz);
        std::string event_type = (ev.duration_seconds > 0.0) ? "interval" : "point";
        rows.push_back({
            eid,
            fmt6(ev.timestamp_seconds),
            fmt6(ev.end_seconds()),
            fmt6(ev.duration_seconds),
            std::to_string(idx.start_sample_index),
            std::to_string(idx.end_sample_index),
            std::to_string(idx.duration_samples),
            event_type,
            ev.label,
            ev.notes,
        });
    }
    return worksheet_xml(rows);
}

/// Build the Data worksheet XML from the raw CSV file.
/// Ports _data_sheet_xml: reads file line by line, splits on ','.
/// (Recording CSVs have no embedded commas/quotes — simple split is correct.)
std::string data_sheet_xml(const std::string& csv_path) {
    std::vector<std::vector<std::string>> rows;
    std::ifstream file(csv_path);
    std::string line;
    while (std::getline(file, line)) {
        // Strip trailing \r (Windows line endings)
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty()) continue;
        // Split on ','
        std::vector<std::string> fields;
        std::istringstream ss(line);
        std::string field;
        while (std::getline(ss, field, ',')) {
            fields.push_back(field);
        }
        rows.push_back(std::move(fields));
    }
    return worksheet_xml(rows);
}

// ---------------------------------------------------------------------------
// Static parts — verbatim XML strings from xlsx_io.py _write_static_parts
// ---------------------------------------------------------------------------

static const std::string CONTENT_TYPES_XML =
R"(<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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
)";

static const std::string RELS_XML =
R"(<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
)";

static const std::string WORKBOOK_XML =
R"(<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Events" sheetId="1" r:id="rId1"/>
    <sheet name="Data" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>
)";

static const std::string WORKBOOK_RELS_XML =
R"(<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
)";

static const std::string STYLES_XML =
R"(<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Arial"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>
)";

static const std::string CORE_XML =
R"(<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:creator>ADS1292 Studio</dc:creator>
  <dc:title>ADS1292 recording</dc:title>
</cp:coreProperties>
)";

static const std::string APP_XML =
R"(<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>ADS1292 Studio</Application>
</Properties>
)";

} // anonymous namespace

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

void write_recording_xlsx(const std::string& csv_path,
                          const std::vector<ads1292::EventMarker>& events,
                          double sample_rate_hz) {
    ZipStoreWriter z;

    // 5 static parts
    z.add("[Content_Types].xml",        CONTENT_TYPES_XML);
    z.add("_rels/.rels",                RELS_XML);
    z.add("xl/workbook.xml",            WORKBOOK_XML);
    z.add("xl/_rels/workbook.xml.rels", WORKBOOK_RELS_XML);
    z.add("xl/styles.xml",              STYLES_XML);
    z.add("docProps/core.xml",          CORE_XML);
    z.add("docProps/app.xml",           APP_XML);

    // Dynamic sheets
    z.add("xl/worksheets/sheet1.xml", events_sheet_xml(events, sample_rate_hz));
    z.add("xl/worksheets/sheet2.xml", data_sheet_xml(csv_path));

    z.write(recording_xlsx_path(csv_path));
}

} // namespace ads1292::io
