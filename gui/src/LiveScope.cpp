// gui/src/LiveScope.cpp

#include "ads1292/gui/LiveScope.h"

#include <QVBoxLayout>
#include <vector>

namespace ads1292::gui {

LiveScope::LiveScope(QWidget* parent)
    : QWidget(parent)
    , m_ecgPlot(std::make_unique<QCustomPlotWaveform>())
    , m_respPlot(std::make_unique<QCustomPlotWaveform>())
{
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(0);

    // addWidget reparents the inner QCustomPlot to this widget's hierarchy.
    // QCustomPlotWaveform's parent-aware destructor will not double-delete.
    layout->addWidget(m_ecgPlot->widget());
    layout->addWidget(m_respPlot->widget());
}

void LiveScope::pushStreamSample(const ads1292::StreamSample& s)
{
    indices_.push_back(next_index_++);
    ch1_.push_back(static_cast<double>(s.ch1));
    ch2_.push_back(static_cast<double>(s.ch2));
    status_.push_back(s.status_byte);

    // Trim all four deques to the rolling window cap.
    const auto cap = static_cast<std::size_t>(
        static_cast<int>(display_.time_window_seconds * sample_rate_hz_) + 2);
    while (indices_.size() > cap) { indices_.pop_front(); }
    while (ch1_.size()    > cap) { ch1_.pop_front(); }
    while (ch2_.size()    > cap) { ch2_.pop_front(); }
    while (status_.size() > cap) { status_.pop_front(); }
}

void LiveScope::setFilterSettings(const ads1292::dsp::SoftwareFilterSettings& f)
{
    filter_ = f;
}

void LiveScope::setWindowSeconds(double s)
{
    display_.time_window_seconds = s;
}

void LiveScope::setAutoscale(bool on)
{
    m_ecgPlot->setAutoscale(on);
    m_respPlot->setAutoscale(on);
}

void LiveScope::clear()
{
    indices_.clear();
    ch1_.clear();
    ch2_.clear();
    status_.clear();
    next_index_ = 0;
    last_frame_ = ads1292::view::LiveRenderFrame{};
    refresh();
}

const ads1292::view::LiveRenderFrame& LiveScope::lastFrame() const
{
    return last_frame_;
}

void LiveScope::refresh()
{
    // Copy deques to vectors for build_live_render_frame.
    const std::vector<int>    idx_vec(indices_.begin(), indices_.end());
    const std::vector<double> ch1_vec(ch1_.begin(), ch1_.end());
    const std::vector<double> ch2_vec(ch2_.begin(), ch2_.end());
    const std::vector<int>    status_vec(status_.begin(), status_.end());

    last_frame_ = ads1292::view::build_live_render_frame(
        idx_vec, ch1_vec, ch2_vec, status_vec,
        display_, filter_,
        /*source=*/"CH2",
        sample_rate_hz_,
        /*smoothing_window=*/5,
        /*max_render_points=*/2000,
        /*ecg_inverted=*/false);

    if (last_frame_.valid) {
        // ECG plot (top): decimated trace + R-peak markers
        m_ecgPlot->setData(0, last_frame_.plot_ecg_x, last_frame_.plot_ecg);
        m_ecgPlot->setMarkers(0, last_frame_.peaks_x, last_frame_.peaks_y);
        m_ecgPlot->replotNow();

        // Respiration plot (bottom): decimated trace
        m_respPlot->setData(0, last_frame_.plot_resp_x, last_frame_.plot_resp);
        m_respPlot->replotNow();
    }
}

} // namespace ads1292::gui
