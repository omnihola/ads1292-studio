#include "ads1292/qt/AdsPorts.h"
#include <QSerialPortInfo>
#include <QString>
#include <algorithm>
#include <cctype>

namespace ads1292 { namespace qt {

namespace {
    constexpr int kVidTi      = 0x2047;
    constexpr int kPidAds1x9x = 0x0300;

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

std::vector<AdsPort> list_ads_ports() {
    std::vector<AdsPort> result;
    for (const QSerialPortInfo& info : QSerialPortInfo::availablePorts()) {
        const std::string desc = info.description().toStdString();
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
        // C8: include port if VID/PID matches OR description contains "ADS1x9x"
        if (!vid_pid_match && !is_ads_description_match(desc)) {
            continue;
        }
        result.push_back(AdsPort{
            info.systemLocation().toStdString(),
            desc,
            hwid,
        });
    }
    return result;
}

}}  // namespace ads1292::qt
