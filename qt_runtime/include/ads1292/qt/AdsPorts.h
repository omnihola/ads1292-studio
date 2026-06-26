#pragma once
#include <string>
#include <vector>

namespace ads1292 { namespace qt {

/// Describes a detected ADS1x9x serial port.
struct AdsPort {
    std::string device;       ///< System device path (e.g. /dev/cu.usbmodemXXX)
    std::string description;  ///< Human-readable port description
    std::string hwid;         ///< Hardware identifier string (e.g. USB VID:PID=2047:0300)
};

/// Returns true when the VID/PID pair identifies an ADS1x9x device.
/// Pure function — no Qt, no I/O, trivially unit-testable.
/// VID 0x2047 = Texas Instruments, PID 0x0300 = ADS1x9x EVM.
bool is_ads_candidate_port(int vid, int pid);

/// Returns true when the port description contains "ADS1x9x" (case-insensitive).
/// Oracle: _is_ads_candidate_port checks `"ADS1x9x" in description`.
bool is_ads_description_match(const std::string& description);

/// Enumerates all connected serial ports and returns those that match
/// the ADS1x9x VID/PID filter via QSerialPortInfo.
///
/// Returns an empty vector when no ADS device is attached (expected in CI).
/// The macOS name-based fallback (cu.usbmodem*/cu.usbserial* glob) is deferred.
std::vector<AdsPort> list_ads_ports();

}}  // namespace ads1292::qt
