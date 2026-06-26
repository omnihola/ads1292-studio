// gui/include/ads1292/gui/Preferences.h
// Pure-data struct mirroring the Python Preferences dataclass (preferences.py).
// No Qt dependency — std::map + std::string only.
#pragma once

#include <map>
#include <string>

namespace ads1292::gui {

struct Preferences {
    std::string port     = "";
    std::string mode     = "Live Monitor";
    bool        save_csv = true;
    bool        save_h5  = true;
    bool        save_xlsx = false;
    std::string window   = "8 s";
    std::string gain     = "1x";
    std::string speed    = "25 mm/s";

    /// Serialize all fields to a string→string map.
    /// Bool fields are encoded as "true" or "false".
    std::map<std::string, std::string> to_map() const;

    /// Deserialize from a string→string map.
    /// Keys not present in m keep their default values.
    /// Bool fields are parsed case-insensitively: "true"/"1"/"yes"/"on" → true.
    static Preferences from_map(const std::map<std::string, std::string>& m);
};

} // namespace ads1292::gui
