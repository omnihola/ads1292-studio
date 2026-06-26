#pragma once
#include <ostream>
#include <string>
#include "ads1292/acq/AdsProtocolDevice.h"
#include "ads1292/acq/IDeviceSource.h"

namespace ads1292 { namespace devcli {

/// Options for the stream subcommand.
/// max_samples: stop after collecting this many samples (0 = collect until source exhausted).
/// csv_path: if non-empty, write the collected samples to this CSV file.
struct StreamOptions {
    int max_samples = 0;
    std::string csv_path;
};

/// Print all detected ADS1x9x serial ports to out.
/// Format: "<device>\t<description>\t<hwid>\n" per port.
/// Returns 0 if at least one port found; 1 if none (prints diagnostic).
int run_ports(std::ostream& out);

/// Query firmware version from dev and print to out.
/// Returns 0.
int run_firmware(std::ostream& out, ads1292::acq::AdsProtocolDevice& dev);

/// Stream samples from dev, collecting until opt.max_samples reached (or source exhausted).
/// Optionally writes CSV to opt.csv_path.
/// Prints "samples=N\n" to out.
/// Returns 0.
///
/// Note: the binary converts --seconds to a sample budget via 500 Hz sample rate.
/// E.g., --seconds 10 -> max_samples = 5000.
int run_stream(std::ostream& out, ads1292::acq::IDeviceSource& dev, const StreamOptions& opt);

}}  // namespace ads1292::devcli
