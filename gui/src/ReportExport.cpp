// gui/src/ReportExport.cpp
// Qt-linked report assembly: ECG + PQRST + spectrum PNGs + HTML.
//
// GPL isolation: this file does NOT include qcustomplot.h.
// It calls the IWaveformPlot / IXYPlot abstractions through the concrete
// backend headers (QCustomPlotWaveform.h / QCustomPlotXY.h), which forward-
// declare QCustomPlot and keep qcustomplot.h confined to their own .cpp files.

#include "ads1292/gui/ReportExport.h"

#include "ads1292/gui/QCustomPlotWaveform.h"
#include "ads1292/gui/QCustomPlotXY.h"

#include "ads1292/dsp/Display.h"
#include "ads1292/dsp/QualityGate.h"
#include "ads1292/dsp/QualityMetrics.h"
#include "ads1292/dsp/Spectrum.h"
#include "ads1292/io/ReviewHtml.h"
#include "ads1292/view/ReviewRender.h"

#include <cctype>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace ads1292::gui {

namespace {

/// Convert a title string to a URL-safe slug:
/// lowercase, non-alnum characters → '-', consecutive dashes collapsed,
/// leading/trailing dashes trimmed.  Returns "report" for an empty result.
std::string to_slug(const std::string& title)
{
    std::string slug;
    slug.reserve(title.size());
    bool prev_dash = true; // start true so leading dashes are skipped
    for (unsigned char c : title) {
        if (std::isalnum(c)) {
            slug += static_cast<char>(std::tolower(c));
            prev_dash = false;
        } else {
            if (!prev_dash) {
                slug += '-';
                prev_dash = true;
            }
        }
    }
    // Trim trailing dash
    while (!slug.empty() && slug.back() == '-')
        slug.pop_back();
    return slug.empty() ? "report" : slug;
}

} // namespace

// ---------------------------------------------------------------------------
// export_review_report
// ---------------------------------------------------------------------------
ReportExportResult export_review_report(
    const std::vector<ads1292::StreamSample>& samples,
    const std::string& out_dir,
    const std::string& title,
    double sample_rate_hz,
    const std::string& source,
    const std::optional<ads1292::SessionMetadata>& metadata,
    const std::vector<ads1292::EventMarker>& events,
    const ads1292::Calibration& calibration)
{
    std::filesystem::create_directories(out_dir);

    // ── Quality metrics + gate ────────────────────────────────────────────────
    auto metrics = ads1292::dsp::compute_quality_metrics(samples, sample_rate_hz, source);
    auto gate    = ads1292::dsp::evaluate_quality_gate(metrics);

    // ── Deterministic file names (slug-based, no timestamp) ──────────────────
    const std::string slug            = to_slug(title);
    const std::filesystem::path dir   = out_dir;

    const std::string ecg_png_name      = slug + "-ecg.png";
    const std::string pqrst_png_name    = slug + "-pqrst.png";
    const std::string spectrum_png_name = slug + "-spectrum.png";
    const std::string html_name         = slug + ".html";

    const std::string ecg_png_path      = (dir / ecg_png_name).string();
    const std::string pqrst_png_path    = (dir / pqrst_png_name).string();
    const std::string spectrum_png_path = (dir / spectrum_png_name).string();
    const std::string html_path         = (dir / html_name).string();

    // ── Full review render frame (ECG + resp decimated + peaks + pqrst) ──────
    auto frame = ads1292::view::build_review_render_frame(
        samples,
        ads1292::dsp::EcgDisplaySettings{},
        ads1292::dsp::SoftwareFilterSettings{},
        source,
        sample_rate_hz,
        /*smoothing_window=*/5,
        /*max_points=*/5000,
        /*ecg_inverted=*/false,
        /*min_ecg_span_counts=*/50.0,
        /*min_resp_span_counts=*/50.0);

    // ── ECG PNG ───────────────────────────────────────────────────────────────
    // Graph 0 = ECG with R-peak markers; graph 1 = respiration.
    {
        QCustomPlotWaveform wf;
        wf.setData(0, frame.plot_ecg_x, frame.plot_ecg);
        wf.setMarkers(0, frame.peak_x, frame.peak_y);
        wf.setData(1, frame.plot_resp_x, frame.plot_resp);
        wf.setAutoscale(true);
        wf.savePng(ecg_png_path, 1000, 360);
    }

    // ── PQRST PNG ─────────────────────────────────────────────────────────────
    // Reuse the frame's pqrst (already computed on the chosen channel).
    // Guard: savePng is called even when average_beat is empty (empty plot is valid).
    {
        QCustomPlotXY xy;
        xy.setLine(frame.pqrst.time_ms, frame.pqrst.average_beat);
        xy.setTitle("PQRST average beat");
        xy.setAutoscale(true);
        xy.savePng(pqrst_png_path, 1000, 360);
    }

    // ── Spectrum PNG ──────────────────────────────────────────────────────────
    // Use the auto-selected channel from the review frame for consistency.
    // FFT line (frequency vs power) + amplitude histogram bars.
    {
        const std::string spec_src = frame.review_source.channel; // "CH1" or "CH2"
        auto spec = ads1292::dsp::build_spectrum_analysis(
            samples, spec_src, sample_rate_hz, /*max_frequency_hz=*/60.0,
            /*histogram_bins=*/48);

        QCustomPlotXY xy;

        // FFT line
        xy.setLine(spec.ecg_frequency_hz, spec.ecg_power);

        // Histogram bars (guard: need at least 2 edges → 1 bin)
        if (spec.histogram_bin_edges.size() >= 2) {
            const std::size_t n = spec.histogram_counts.size();
            std::vector<double> centers(n);
            std::vector<double> heights(n);
            const double bar_width =
                spec.histogram_bin_edges[1] - spec.histogram_bin_edges[0];
            for (std::size_t i = 0; i < n; ++i) {
                centers[i] = (spec.histogram_bin_edges[i] +
                               spec.histogram_bin_edges[i + 1]) / 2.0;
                heights[i] = static_cast<double>(spec.histogram_counts[i]);
            }
            xy.setBars(centers, heights, bar_width);
        }

        xy.setAutoscale(true);
        xy.savePng(spectrum_png_path, 1000, 360);
    }

    // ── HTML ──────────────────────────────────────────────────────────────────
    ads1292::io::ReviewHtmlInputs in;
    in.title             = title;
    in.metrics           = metrics;
    in.gate              = gate;
    in.calibration       = calibration;
    in.metadata          = metadata;
    in.events            = events;
    in.ecg_png_name      = ecg_png_name;
    in.pqrst_png_name    = pqrst_png_name;
    in.spectrum_png_name = spectrum_png_name;

    {
        std::ofstream ofs(html_path, std::ios::out | std::ios::trunc);
        ofs << ads1292::io::build_review_html(in);
    }

    return {html_path, ecg_png_path, pqrst_png_path, spectrum_png_path};
}

} // namespace ads1292::gui
