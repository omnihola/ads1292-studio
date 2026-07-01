#include "ads1292/qt/AdsPorts.h"
#include <QSerialPortInfo>
#include <QString>
#include <algorithm>
#include <cctype>

namespace ads1292 { namespace qt {

namespace {
    constexpr int kVidTi      = 0x2047;
    constexpr int kPidAds1x9x = 0x0300;

    // Oracle: device.py SERIAL_CANDIDATE_MARKERS = ("usbmodem", "usbserial").
    constexpr const char* kSerialCandidateMarkers[] = {"usbmodem", "usbserial"};

    // Case-insensitive substring search (ASCII).
    bool icontains(const std::string& haystack, const std::string& needle) {
        if (needle.empty()) return true;
        auto it = std::search(
            haystack.begin(), haystack.end(),
            needle.begin(), needle.end(),
            [](char a, char b) {
                return std::tolower(static_cast<unsigned char>(a)) ==
                       std::tolower(static_cast<unsigned char>(b));
            });
        return it != haystack.end();
    }
}  // namespace

bool is_ads_candidate_port(int vid, int pid) {
    return vid == kVidTi && pid == kPidAds1x9x;
}

// C8: also match when description contains "ADS1x9x" (case-insensitive)
// (oracle: _is_ads_candidate_port checks `"ADS1x9x" in description`)
bool is_ads_description_match(const std::string& description) {
    return icontains(description, "ADS1x9x");
}

// The usbmodem/usbserial device-path fallback — the third arm of Python's
// _is_ads_candidate_port. Without it, an ADS1292 board that enumerates as a
// generic USB-CDC /dev/cu.usbmodem*/cu.usbserial* (no TI VID/PID, no "ADS1x9x"
// description — the common case for dev boards) would never appear in the list.
bool is_usb_serial_candidate(const std::string& device_path) {
    for (const char* marker : kSerialCandidateMarkers) {
        if (icontains(device_path, marker)) return true;
    }
    return false;
}

std::vector<AdsPort> list_ads_ports() {
    std::vector<AdsPort> result;
    for (const QSerialPortInfo& info : QSerialPortInfo::availablePorts()) {
        const std::string desc = info.description().toStdString();
        const std::string device = info.systemLocation().toStdString();
        bool vid_pid_match = false;
        std::string hwid;
        if (info.hasVendorIdentifier() && info.hasProductIdentifier()) {
            const int vid = static_cast<int>(info.vendorIdentifier());
            const int pid = static_cast<int>(info.productIdentifier());
            if (is_ads_candidate_port(vid, pid)) {
                vid_pid_match = true;
                hwid = QString::asprintf("USB VID:PID=%04X:%04X", vid, pid).toStdString();
            }
        }
        // Include a port when ANY of the three heuristics match (mirrors the
        // Python _is_ads_candidate_port OR): TI VID/PID, "ADS1x9x" description,
        // or a usbmodem/usbserial device path (the USB-CDC dev-board case).
        if (!vid_pid_match && !is_ads_description_match(desc) &&
            !is_usb_serial_candidate(device)) {
            continue;
        }
        result.push_back(AdsPort{
            device,
            desc,
            hwid,
        });
    }
    return result;
}

}}  // namespace ads1292::qt
