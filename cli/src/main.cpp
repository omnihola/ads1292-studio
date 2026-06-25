// cli/src/main.cpp
// ads1292_cli entry point: dispatches subcommands.
// Qt-free — links ads1292_core + ads1292_io only.

#include "ads1292/cli/Cli.h"

#include <iostream>
#include <string>
#include <string_view>
#include <vector>

static void print_usage(const char* prog) {
    std::cerr << "Usage: " << prog << " <subcommand> [options]\n"
              << "\n"
              << "Subcommands:\n"
              << "  qc <csv> [--source CH1|CH2|Auto]\n"
              << "      Quality-gate check on a recording. Exit 0 = pass, 2 = fail, 1 = error.\n"
              << "  report <csv> [--source CH1|CH2|Auto]\n"
              << "      Print textual quality/HR summary. Exit 0 = ok, 1 = error.\n"
              << "  verify <h5>\n"
              << "      Verify HDF5 recording integrity. Exit 0 = ok, 2 = fail, 1 = error.\n";
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    const std::string_view subcmd{argv[1]};

    if (subcmd == "qc") {
        if (argc < 3) {
            std::cerr << "Usage: " << argv[0] << " qc <csv> [--source CH1|CH2|Auto]\n";
            return 1;
        }

        ads1292::cli::QcOptions opt;
        opt.csv_path = argv[2];

        // Parse optional flags
        for (int i = 3; i < argc; ++i) {
            const std::string_view flag{argv[i]};
            if (flag == "--source" && i + 1 < argc) {
                opt.source = argv[++i];
            } else {
                std::cerr << "Unknown option: " << flag << "\n";
                std::cerr << "Usage: " << argv[0] << " qc <csv> [--source CH1|CH2|Auto]\n";
                return 1;
            }
        }

        return ads1292::cli::run_qc(std::cout, opt);
    }

    if (subcmd == "report") {
        if (argc < 3) {
            std::cerr << "Usage: " << argv[0] << " report <csv> [--source CH1|CH2|Auto]\n";
            return 1;
        }

        ads1292::cli::ReportOptions opt;
        opt.csv_path = argv[2];

        for (int i = 3; i < argc; ++i) {
            const std::string_view flag{argv[i]};
            if (flag == "--source" && i + 1 < argc) {
                opt.source = argv[++i];
            } else {
                std::cerr << "Unknown option: " << flag << "\n";
                std::cerr << "Usage: " << argv[0] << " report <csv> [--source CH1|CH2|Auto]\n";
                return 1;
            }
        }

        return ads1292::cli::run_report(std::cout, opt);
    }

    if (subcmd == "verify") {
        if (argc < 3) {
            std::cerr << "Usage: " << argv[0] << " verify <h5>\n";
            return 1;
        }

        ads1292::cli::VerifyOptions opt;
        opt.h5_path = argv[2];

        return ads1292::cli::run_verify(std::cout, opt);
    }

    // Unknown subcommand
    std::cerr << "Unknown subcommand: " << subcmd << "\n";
    print_usage(argv[0]);
    return 1;
}
