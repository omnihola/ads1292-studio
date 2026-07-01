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

/// Returns true when the device path contains a USB-serial marker
/// (usbmodem / usbserial), case-insensitive. Oracle: _is_ads_candidate_port's
/// `is_usb_serial_candidate` (SERIAL_CANDIDATE_MARKERS = ("usbmodem","usbserial")).
/// This is the macOS/generic USB-CDC fallback: most ADS1292 dev boards enumerate
/// as /dev/cu.usbmodem*/cu.usbserial* WITHOUT the TI VID/PID or an "ADS1x9x"
/// description, so this marker is what lets them appear in the port list.
bool is_usb_serial_candidate(const std::string& device_path);

/// Enumerates all connected serial ports and returns those that match the
/// ADS1x9x heuristics via QSerialPortInfo: TI VID/PID, OR an "ADS1x9x"
/// description, OR a usbmodem/usbserial device path (mirrors the Python
/// _is_ads_candidate_port three-way OR). Returns an empty vector when no
/// candidate is attached.
std::vector<AdsPort> list_ads_ports();

}}  // namespace ads1292::qt
