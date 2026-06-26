#include "ads1292/devcli/DevCli.h"
#include "ads1292/qt/AdsPorts.h"
#include "ads1292/io/CsvIo.h"
#include <vector>

namespace ads1292 { namespace devcli {

int run_ports(std::ostream& out) {
    auto ports = ads1292::qt::list_ads_ports();
    if (ports.empty()) {
        out << "No ADS1x9x ports found\n";
        return 1;
    }
    for (const auto& p : ports) {
        out << p.device << "\t" << p.description << "\t" << p.hwid << "\n";
    }
    return 0;
}

int run_firmware(std::ostream& out, ads1292::acq::AdsProtocolDevice& dev) {
    out << dev.query_firmware() << "\n";
    return 0;
}

int run_stream(std::ostream& out, ads1292::acq::IDeviceSource& dev, const StreamOptions& opt) {
    std::vector<ads1292::StreamSample> samples;
    dev.start_stream();
    // B9: wrap the read loop so stop_stream() is called even on exception
    // (oracle: cli.py cmd_stream uses try/finally: device.stop_stream())
    try {
        while (true) {
            auto batch = dev.read_stream_batch();
            if (batch.empty()) {
                if (dev.stream_done()) break;   // finite source exhausted (simulator) -> stop
                continue;                        // real-hardware inter-frame gap -> keep collecting toward max_samples
            }
            samples.insert(samples.end(), batch.begin(), batch.end());
            if (opt.max_samples > 0 && static_cast<int>(samples.size()) >= opt.max_samples) break;
        }
    } catch (...) {
        dev.stop_stream();
        throw;
    }
    dev.stop_stream();
    if (!opt.csv_path.empty()) {
        ads1292::io::write_recording_csv(opt.csv_path, samples);
    }
    out << "samples=" << samples.size() << "\n";
    return 0;
}

}}  // namespace ads1292::devcli
