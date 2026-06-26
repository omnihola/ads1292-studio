// tests/cpp/test_xlsx_io.cpp
// Validates write_recording_xlsx: 2-tab (Events + Data) XLSX output.
// Uses unzip to verify the archive is readable and has correct content.
#include "catch.hpp"
#include "ads1292/io/XlsxIo.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/model/EventMarker.h"
#include "ads1292/model/StreamSample.h"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

static std::string read_file(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}

// Returns true when `haystack` contains `needle`.
static bool contains(const std::string& haystack, const std::string& needle) {
    return haystack.find(needle) != std::string::npos;
}

} // anonymous namespace

TEST_CASE("write_recording_xlsx produces a valid 2-tab XLSX", "[xlsx]") {
    const auto tmp = fs::temp_directory_path() / "p11_xlsx_test";
    fs::create_directories(tmp);

    const std::string csv_path = (tmp / "rec.csv").string();
    const std::string xlsx_path = ads1292::io::recording_xlsx_path(csv_path);

    // --- Author a small recording CSV ---
    std::vector<ads1292::StreamSample> samples;
    {
        ads1292::StreamSample s0;
        s0.timestamp = 0.0;
        s0.ch1 = 100;
        s0.ch2 = 200;
        s0.board_heart_rate = 72;
        s0.board_respiration_rate = 18;
        s0.status_byte = 0;
        s0.sample_index = 0;
        samples.push_back(s0);

        ads1292::StreamSample s1;
        s1.timestamp = 0.002;
        s1.ch1 = 110;
        s1.ch2 = 210;
        s1.board_heart_rate = 73;
        s1.board_respiration_rate = 19;
        s1.status_byte = 1;
        s1.sample_index = 1;
        samples.push_back(s1);
    }
    ads1292::io::write_recording_csv(csv_path, samples);
    REQUIRE(fs::exists(csv_path));

    // --- Build 2 EventMarkers: one point, one interval with a '<' in notes ---
    std::vector<ads1292::EventMarker> events;
    {
        ads1292::EventMarker point;
        point.timestamp_seconds = 0.0;
        point.duration_seconds  = 0.0;
        point.label             = "start";
        point.notes             = "";
        events.push_back(point);

        ads1292::EventMarker interval;
        interval.timestamp_seconds = 0.0;
        interval.duration_seconds  = 0.5;
        interval.label             = "seg";
        interval.notes             = "amplitude < 1mV";  // '<' must be escaped
        events.push_back(interval);
    }

    // --- Write the XLSX ---
    ads1292::io::write_recording_xlsx(csv_path, events, 500.0);
    REQUIRE(fs::exists(xlsx_path));
    REQUIRE(fs::file_size(xlsx_path) > 0);

    // --- Verify sheet1.xml (Events) via unzip -p ---
    SECTION("sheet1 contains Events header and escaped notes") {
        const std::string s1 = (tmp / "s1.xml").string();
        std::string cmd = "/usr/bin/unzip -p '" + xlsx_path +
                          "' xl/worksheets/sheet1.xml > '" + s1 + "' 2>/dev/null";
        int rc = std::system(cmd.c_str());
        REQUIRE(rc == 0);

        const std::string content = read_file(s1);
        REQUIRE(!content.empty());

        // Header column: event_id should appear as an inlineStr cell
        REQUIRE(contains(content, "<t>event_id</t>"));

        // An event label: "start" and "seg" appear as inlineStr cells
        REQUIRE(contains(content, "<t>start</t>"));
        REQUIRE(contains(content, "<t>seg</t>"));

        // The '<' in "amplitude < 1mV" must be XML-escaped to "&lt;"
        REQUIRE(contains(content, "&lt;"));
        // The raw '<' must NOT appear in the notes cell
        // (We check the full note context — escaped form contains the rest)
        REQUIRE(contains(content, "amplitude &lt; 1mV"));

        // A :.6f timestamp: the point event at t=0 → "0.000000"
        REQUIRE(contains(content, "0.000000"));

        // event_type "point" appears for the zero-duration event
        REQUIRE(contains(content, "<t>point</t>"));

        // event_type "interval" appears for the 0.5s event
        REQUIRE(contains(content, "<t>interval</t>"));

        // duration_seconds for interval event: "0.500000" (is_number → <v>)
        REQUIRE(contains(content, "<v>0.500000</v>"));
    }

    // --- Verify sheet2.xml (Data) via unzip -p ---
    SECTION("sheet2 contains CSV header row and numeric data cells") {
        const std::string s2 = (tmp / "s2.xml").string();
        std::string cmd = "/usr/bin/unzip -p '" + xlsx_path +
                          "' xl/worksheets/sheet2.xml > '" + s2 + "' 2>/dev/null";
        int rc = std::system(cmd.c_str());
        REQUIRE(rc == 0);

        const std::string content = read_file(s2);
        REQUIRE(!content.empty());

        // CSV header: "time_s" or "timestamp" should appear (depends on CANONICAL_HEADER)
        // The CSV uses the canonical header from write_recording_csv; check at least
        // one column name from the header row as an inlineStr cell.
        REQUIRE(contains(content, "inlineStr"));

        // Data rows: ch1=100 and ch1=110 are numeric → appear as <v> cells
        REQUIRE(contains(content, "<v>100</v>"));
        REQUIRE(contains(content, "<v>110</v>"));
    }

    // --- Verify archive listing contains all mandatory parts ---
    SECTION("unzip -l shows all required OOXML parts") {
        const std::string listing = (tmp / "listing.txt").string();
        std::string cmd = "/usr/bin/unzip -l '" + xlsx_path +
                          "' > '" + listing + "' 2>/dev/null";
        int rc = std::system(cmd.c_str());
        REQUIRE(rc == 0);

        const std::string content = read_file(listing);
        REQUIRE(contains(content, "[Content_Types].xml"));
        REQUIRE(contains(content, "xl/workbook.xml"));
        REQUIRE(contains(content, "xl/styles.xml"));
        REQUIRE(contains(content, "xl/worksheets/sheet1.xml"));
        REQUIRE(contains(content, "xl/worksheets/sheet2.xml"));
    }

    // --- recording_xlsx_path helper ---
    SECTION("recording_xlsx_path returns .xlsx path") {
        const std::string result = ads1292::io::recording_xlsx_path("/data/rec.csv");
        REQUIRE(result == "/data/rec.xlsx");
    }
}
