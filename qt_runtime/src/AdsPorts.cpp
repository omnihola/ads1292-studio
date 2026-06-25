#include "ads1292/qt/AdsPorts.h"
#include <QSerialPortInfo>
#include <QString>

namespace ads1292 { namespace qt {

namespace {
    constexpr int kVidTi      = 0x2047;
    constexpr int kPidAds1x9x = 0x0300;
}  // namespace

bool is_ads_candidate_port(int vid, int pid) {
    return vid == kVidTi && pid == kPidAds1x9x;
}

std::vector<AdsPort> list_ads_ports() {
    std::vector<AdsPort> result;
    for (const QSerialPortInfo& info : QSerialPortInfo::availablePorts()) {
        if (!info.hasVendorIdentifier() || !info.hasProductIdentifier()) {
            continue;
        }
        const int vid = static_cast<int>(info.vendorIdentifier());
        const int pid = static_cast<int>(info.productIdentifier());
        if (!is_ads_candidate_port(vid, pid)) {
            continue;
        }
        const std::string hwid =
            QString::asprintf("USB VID:PID=%04X:%04X", vid, pid).toStdString();
        result.push_back(AdsPort{
            info.systemLocation().toStdString(),
            info.description().toStdString(),
            hwid,
        });
    }
    return result;
}

}}  // namespace ads1292::qt
