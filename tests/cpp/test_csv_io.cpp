// tests/cpp/test_csv_io.cpp
// Regression tests for CsvIo.cpp — C1: fallback column resolution.
//
// The CSV oracle (csv_io.py) resolves column names through _resolve_column_indices
// which falls back through priority lists when the canonical name is absent.
// The C++ read_recording_csv must match that behaviour exactly.
#include "catch.hpp"
#include "ads1292/io/CsvIo.h"
#include <filesystem>
#include <fstream>
#include <string>

namespace {
// Write a small CSV with only the FALLBACK column names (not the canonical ones).
// After C1 fix the reader must still populate all fields; before the fix all
// non-timestamp fields would be 0 because header_index would return -1.
std::string write_fallback_csv(const std::string& path) {
    std::ofstream out(path);
    // Header uses secondary / fallback names only:
    //   ecg_counts  (fallback for ch1_counts)
    //   resp_counts (fallback for ch2_counts)
    //   heart_rate  (fallback for board_heart_rate)
    //   respiration_rate (fallback for board_respiration_rate)
    //   lead_off_bits — the nibble-merge column; no status_byte or sample_index
    out << "time_s,ecg_counts,resp_counts,heart_rate,respiration_rate,lead_off_bits\r\n";
    // Row 0: known non-zero values; lead_off_bits = 5
    out << "0.000000,1234,567,72,18,5\r\n";
    // Row 1: different values; lead_off_bits = 3
    out << "0.002000,4321,890,75,20,3\r\n";
    return path;
}
}  // namespace

TEST_CASE("read_recording_csv resolves fallback column names (C1 regression)", "[csv]") {
    const std::string path =
        (std::filesystem::temp_directory_path() / "c1_fallback.csv").string();
    write_fallback_csv(path);

    auto samples = ads1292::io::read_recording_csv(path);
    REQUIRE(samples.size() == 2);

    // ch1 must come from ecg_counts (1234), not be 0
    REQUIRE(samples[0].ch1 == 1234);
    // ch2 must come from resp_counts (567)
    REQUIRE(samples[0].ch2 == 567);
    // board_heart_rate from heart_rate (72)
    REQUIRE(samples[0].board_heart_rate == 72);
    // board_respiration_rate from respiration_rate (18)
    REQUIRE(samples[0].board_respiration_rate == 18);

    // lead_off_bits=5 merges low nibble into status_byte:
    // status_byte = (0 & ~0x0F) | (5 & 0x0F) = 5
    REQUIRE(samples[0].status_byte == 5);

    // No sample_index or index column → defaults to row index
    REQUIRE(samples[0].sample_index.has_value());
    REQUIRE(samples[0].sample_index.value() == 0);

    // Row 1
    REQUIRE(samples[1].ch1 == 4321);
    REQUIRE(samples[1].ch2 == 890);
    REQUIRE(samples[1].board_heart_rate == 75);
    REQUIRE(samples[1].board_respiration_rate == 20);
    REQUIRE(samples[1].status_byte == 3);   // lead_off_bits=3 → low nibble=3
    REQUIRE(samples[1].sample_index.has_value());
    REQUIRE(samples[1].sample_index.value() == 1);

    std::filesystem::remove(path);
}

TEST_CASE("read_recording_csv sets sample_index to row index when column absent (C1)", "[csv]") {
    // CSV with NO index column at all
    const std::string path =
        (std::filesystem::temp_directory_path() / "c1_no_index.csv").string();
    {
        std::ofstream out(path);
        out << "timestamp,ch1_counts,ch2_counts\r\n";
        out << "0.000000,10,20\r\n";
        out << "0.002000,11,21\r\n";
        out << "0.004000,12,22\r\n";
    }
    auto samples = ads1292::io::read_recording_csv(path);
    REQUIRE(samples.size() == 3);
    for (int i = 0; i < 3; ++i) {
        REQUIRE(samples[i].sample_index.has_value());
        REQUIRE(samples[i].sample_index.value() == i);
    }
    std::filesystem::remove(path);
}
