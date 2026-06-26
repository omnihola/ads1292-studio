/// ads1292_devcli — device command-line interface
///
/// Subcommands:
///   ports                            List all detected ADS1x9x serial ports.
///   firmware --port <port>           Query firmware version from a connected device.
///   stream --port <port> --seconds <n> [--csv <file>]
///                                    Acquire samples for N seconds, optionally saving to CSV.
///                                    Converts seconds to a sample budget at 500 Hz:
///                                    max_samples = round(seconds * 500.0)
///
/// Real-serial open errors print a clean message to stderr and exit with status 1.

#include <iostream>
#include <stdexcept>
#include <string>
#include <cmath>
#include "ads1292/devcli/DevCli.h"
#include "ads1292/qt/QSerialByteTransport.h"
#include "ads1292/acq/AdsProtocolDevice.h"
#include <QCoreApplication>
#include <QString>

static constexpr double kSampleRateHz = 500.0;

static void print_usage(const char* argv0) {
    std::cerr << "Usage:\n"
              << "  " << argv0 << " ports\n"
              << "  " << argv0 << " firmware --port <port>\n"
              << "  " << argv0 << " stream --port <port> --seconds <n> [--csv <file>]\n";
}

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);

    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    const std::string subcmd = argv[1];

    // ── ports ──────────────────────────────────────────────────────────────
    if (subcmd == "ports") {
        return ads1292::devcli::run_ports(std::cout);
    }

    // ── firmware ───────────────────────────────────────────────────────────
    if (subcmd == "firmware") {
        std::string port;
        for (int i = 2; i + 1 < argc; ++i) {
            if (std::string(argv[i]) == "--port") {
                port = argv[i + 1];
            }
        }
        if (port.empty()) {
            std::cerr << "Error: --port is required for the firmware subcommand\n";
            print_usage(argv[0]);
            return 1;
        }
        try {
            ads1292::qt::QSerialByteTransport transport(QString::fromStdString(port));
            ads1292::acq::AdsProtocolDevice dev(transport, kSampleRateHz);
            return ads1292::devcli::run_firmware(std::cout, dev);
        } catch (const std::exception& e) {
            std::cerr << "Error opening port " << port << ": " << e.what() << "\n";
            return 1;
        }
    }

    // ── stream ─────────────────────────────────────────────────────────────
    if (subcmd == "stream") {
        std::string port;
        double seconds = 0.0;
        std::string csv_path;
        for (int i = 2; i + 1 < argc; ++i) {
            const std::string arg = argv[i];
            if (arg == "--port")    { port = argv[i + 1]; }
            else if (arg == "--seconds") {
                try {
                    seconds = std::stod(argv[i + 1]);
                } catch (const std::exception&) {
                    std::cerr << "invalid --seconds value: " << argv[i + 1] << "\n";
                    return 1;
                }
            }
            else if (arg == "--csv")     { csv_path = argv[i + 1]; }
        }
        if (port.empty()) {
            std::cerr << "Error: --port is required for the stream subcommand\n";
            print_usage(argv[0]);
            return 1;
        }
        if (seconds <= 0.0) {
            std::cerr << "Error: --seconds must be a positive number\n";
            print_usage(argv[0]);
            return 1;
        }
        // Convert duration to a sample budget via the ADS1292 sample rate (500 Hz).
        ads1292::devcli::StreamOptions opt;
        opt.max_samples = static_cast<int>(std::round(seconds * kSampleRateHz));
        opt.csv_path = csv_path;
        try {
            ads1292::qt::QSerialByteTransport transport(QString::fromStdString(port));
            ads1292::acq::AdsProtocolDevice dev(transport, kSampleRateHz);
            return ads1292::devcli::run_stream(std::cout, dev, opt);
        } catch (const std::exception& e) {
            std::cerr << "Error opening port " << port << ": " << e.what() << "\n";
            return 1;
        }
    }

    std::cerr << "Unknown subcommand: " << subcmd << "\n";
    print_usage(argv[0]);
    return 1;
}
