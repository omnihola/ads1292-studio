// io/src/ReviewHtml.cpp
// Qt-free HTML report builder reproducing report.py::_html structure + values.
// Pure C++17, stdlib only. No Qt, no nlohmann.

#include "ads1292/io/ReviewHtml.h"
#include "ads1292/dsp/QualityMetrics.h"

#include <cstdio>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

namespace {

// ---------------------------------------------------------------------------
// HTML escaping — replicates Python html.escape (& first, then < > " ')
// ---------------------------------------------------------------------------
std::string escape(const std::string& s) {
    std::string out;
    out.reserve(s.size());
    for (char c : s) {
        switch (c) {
            case '&':  out += "&amp;";   break;
            case '<':  out += "&lt;";    break;
            case '>':  out += "&gt;";    break;
            case '"':  out += "&quot;";  break;
            case '\'': out += "&#x27;";  break;
            default:   out += c;         break;
        }
    }
    return out;
}

// ---------------------------------------------------------------------------
// Numeric formatters matching Python f-string specifiers
// ---------------------------------------------------------------------------

/// Fixed N decimal places.
template <int N>
std::string fixed_n(double v) {
    std::ostringstream os;
    os << std::fixed << std::setprecision(N) << v;
    return os.str();
}

/// %g format (like Python :g / C printf %g).
std::string fmt_g(double v) {
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%g", v);
    return buf;
}

// Aliases used in the table rows below.
inline std::string f1(double v) { return fixed_n<1>(v); }
inline std::string f2(double v) { return fixed_n<2>(v); }
inline std::string f3(double v) { return fixed_n<3>(v); }
inline std::string f4(double v) { return fixed_n<4>(v); }

// ---------------------------------------------------------------------------
// Helper: build a single <tr><th>k</th><td>v</td></tr> row.
// ---------------------------------------------------------------------------
std::string tr(const std::string& k, const std::string& v) {
    return "<tr><th>" + escape(k) + "</th><td>" + escape(v) + "</td></tr>";
}

// ---------------------------------------------------------------------------
// Event row — matches report.py::_event_row
// ---------------------------------------------------------------------------
std::string event_row(const ads1292::EventMarker& event) {
    const auto marker = event.normalized();
    std::string out = "<tr>";
    out += "<td>" + f2(marker.timestamp_seconds) + "</td>";
    out += "<td>" + f2(marker.end_seconds()) + "</td>";
    out += "<td>" + f2(marker.duration_seconds) + "</td>";
    out += "<td>" + escape(marker.label) + "</td>";
    out += "<td>" + escape(marker.notes) + "</td>";
    out += "</tr>";
    return out;
}

// ---------------------------------------------------------------------------
// CSS style block — verbatim from report.py::_html
// ---------------------------------------------------------------------------
const char* STYLE = R"(
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; color: #1f2937; }
    h1 { margin-bottom: 4px; }
    .sub { color: #6b7280; margin-bottom: 24px; }
    table { border-collapse: collapse; margin: 16px 0 28px; min-width: 420px; }
    th, td { border: 1px solid #d1d5db; padding: 8px 10px; text-align: left; }
    th { background: #f3f4f6; }
    img { max-width: 100%; border: 1px solid #e5e7eb; margin: 12px 0 24px; }
)";

} // anonymous namespace

namespace ads1292::io {

std::string build_review_html(const ReviewHtmlInputs& in) {
    // -----------------------------------------------------------------------
    // Main metrics table — matches report.py::_html rows list, exact labels +
    // value formats.  Python str(bool) → "True" / "False" (capital).
    // -----------------------------------------------------------------------
    const auto& m = in.metrics;
    const std::string qrs_str   = m.qrs_clear    ? "True" : "False";
    const std::string p_str     = m.p_tentative   ? "tentative" : "not reliable";
    const std::string t_str     = m.t_tentative   ? "tentative" : "not reliable";
    const std::string hr_range  = f1(m.hr_min_bpm) + "-" + f1(m.hr_max_bpm) + " bpm";

    const std::vector<std::pair<std::string,std::string>> metric_rows = {
        { "Quality",             ads1292::dsp::quality_label(m)                    },
        { "ECG source",          m.ecg_source                                      },
        { "Samples",             std::to_string(m.sample_count)                    },
        { "Duration",            f2(m.duration_seconds) + " s"                     },
        { "Contact OK",          f2(m.contact_ok_percent) + "%"                    },
        { "Lead-off bad samples",std::to_string(m.lead_off_bad_samples)            },
        { "R peaks",             std::to_string(m.r_peaks)                         },
        { "Median HR",           f1(m.hr_median_bpm) + " bpm"                      },
        { "HR range",            hr_range                                           },
        { "QRS clear",           qrs_str                                            },
        { "P wave",              p_str                                              },
        { "T wave",              t_str                                              },
        { "Baseline drift",      f1(m.baseline_drift_counts) + " counts"           },
        { "Noise RMS",           f1(m.noise_rms_counts) + " counts"                },
        { "Peak-to-peak",        f1(m.peak_to_peak_counts) + " counts"             },
        { "CH1 score",           f2(m.score_ch1)                                   },
        { "CH2 score",           f2(m.score_ch2)                                   },
    };

    std::string table;
    for (const auto& [k, v] : metric_rows) {
        table += "\n" + tr(k, v);
    }

    // -----------------------------------------------------------------------
    // Optional metadata section
    // -----------------------------------------------------------------------
    std::string metadata_html;
    if (in.metadata.has_value()) {
        const auto meta = in.metadata->normalized();
        std::string meta_table;
        const std::vector<std::pair<std::string,std::string>> meta_rows = {
            { "Session ID",  meta.session_id  },
            { "Subject ID",  meta.subject_id  },
            { "Electrode",   meta.electrode   },
            { "Montage",     meta.montage     },
            { "Operator",    meta.operator_   },
            { "Notes",       meta.notes       },
        };
        for (const auto& [k, v] : meta_rows) {
            meta_table += "\n" + tr(k, v);
        }
        metadata_html = "<h2>Session Metadata</h2><table>" + meta_table + "\n</table>";
    }

    // -----------------------------------------------------------------------
    // Optional events section
    // -----------------------------------------------------------------------
    std::string events_html;
    if (!in.events.empty()) {
        std::string event_rows_html;
        for (const auto& ev : in.events) {
            event_rows_html += "\n" + event_row(ev);
        }
        events_html =
            "<h2>Event Markers</h2>"
            "<table><tr>"
            "<th>Start (s)</th><th>End (s)</th><th>Duration (s)</th>"
            "<th>Label</th><th>Notes</th>"
            "</tr>"
            + event_rows_html +
            "\n</table>";
    }

    // -----------------------------------------------------------------------
    // Calibration section
    // -----------------------------------------------------------------------
    const auto cal = in.calibration.normalized();
    const std::vector<std::pair<std::string,std::string>> cal_rows = {
        { "Label",             cal.label                                           },
        { "Reference voltage", f3(cal.vref_mv / 1000.0) + " V"                   },
        { "PGA gain",          fmt_g(cal.pga_gain)                                },
        { "ADC bits",          std::to_string(cal.adc_bits)                       },
        { "ECG scale",         f4(cal.microvolts_per_count()) + " uV/count"       },
    };
    std::string cal_table;
    for (const auto& [k, v] : cal_rows) {
        cal_table += "\n" + tr(k, v);
    }
    const std::string calibration_html = "<h2>Calibration</h2><table>" + cal_table + "\n</table>";

    // -----------------------------------------------------------------------
    // Quality gate section
    // -----------------------------------------------------------------------
    const auto& g = in.gate;
    const std::string failures_str = g.failures.empty()
        ? "None"
        : [&]() {
            std::string joined;
            for (std::size_t i = 0; i < g.failures.size(); ++i) {
                if (i > 0) joined += "; ";
                joined += g.failures[i];
            }
            return joined;
          }();

    const std::vector<std::pair<std::string,std::string>> gate_rows = {
        { "Status",   g.label()    },
        { "Failures", failures_str },
    };
    std::string gate_table;
    for (const auto& [k, v] : gate_rows) {
        gate_table += "\n" + tr(k, v);
    }
    const std::string gate_html = "<h2>Quality Gate</h2><table>" + gate_table + "\n</table>";

    // -----------------------------------------------------------------------
    // Assemble the full HTML document.
    // Body layout matches report.py::_html return template:
    //   h1 > sub > metadata > [protocol DEFERRED] > [segment DEFERRED] >
    //   [segment_gate DEFERRED] > events > calibration > gate >
    //   Signal Quality table > ECG img > PQRST img > Spectrum img
    // -----------------------------------------------------------------------
    std::string html;
    html.reserve(8192);

    html += "<!doctype html>\n";
    html += "<html lang=\"en\">\n";
    html += "<head>\n";
    html += "  <meta charset=\"utf-8\">\n";
    html += "  <title>" + escape(in.title) + "</title>\n";
    html += "  <style>";
    html += STYLE;
    html += "  </style>\n";
    html += "</head>\n";
    html += "<body>\n";
    html += "  <h1>" + escape(in.title) + "</h1>\n";
    html += "  <div class=\"sub\">Generated by ADS1292 Studio. Research use only; not diagnostic medical software.</div>\n";
    if (!metadata_html.empty()) {
        html += "  " + metadata_html + "\n";
    }
    // protocol_html, segment_html, segment_gate_html — DEFERRED
    if (!events_html.empty()) {
        html += "  " + events_html + "\n";
    }
    html += "  " + calibration_html + "\n";
    html += "  " + gate_html + "\n";
    html += "  <h2>Signal Quality</h2>\n";
    html += "  <table>" + table + "\n</table>\n";
    html += "  <h2>ECG Review</h2>\n";
    html += "  <p>Exported ECG and PQRST plots use a fixed QRS bandpass for review consistency; GUI display filter toggles are not applied to this report.</p>\n";
    html += "  <img src=\"" + escape(in.ecg_png_name) + "\" alt=\"ECG review plot\">\n";
    html += "  <h2>PQRST Review</h2>\n";
    html += "  <img src=\"" + escape(in.pqrst_png_name) + "\" alt=\"PQRST review plot\">\n";
    html += "  <h2>FFT / Histogram</h2>\n";
    html += "  <p>FFT and amplitude histogram are computed from the raw selected ECG channel for exploratory signal review.</p>\n";
    html += "  <img src=\"" + escape(in.spectrum_png_name) + "\" alt=\"FFT spectrum and amplitude histogram\">\n";
    html += "</body>\n";
    html += "</html>\n";

    return html;
}

} // namespace ads1292::io
