// gui/src/Preferences.cpp
// Implementation of Preferences::to_map and Preferences::from_map.
// Mirrors preferences.py: to_dict() + from_dict() + _to_bool().

#include "ads1292/gui/Preferences.h"

#include <algorithm>
#include <cctype>
#include <string>

namespace ads1292::gui {

namespace {

// Mirrors Python _to_bool: lowercase the string, then check against the
// accepted truthy set {"1", "true", "yes", "on"}.
bool to_bool(const std::string& value) {
    std::string lower = value;
    std::transform(lower.begin(), lower.end(), lower.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return lower == "1" || lower == "true" || lower == "yes" || lower == "on";
}

} // namespace

std::map<std::string, std::string> Preferences::to_map() const {
    return {
        {"port",      port},
        {"mode",      mode},
        {"save_csv",  save_csv  ? "true" : "false"},
        {"save_h5",   save_h5   ? "true" : "false"},
        {"save_xlsx", save_xlsx ? "true" : "false"},
        {"window",    window},
        {"gain",      gain},
        {"speed",     speed},
    };
}

Preferences Preferences::from_map(const std::map<std::string, std::string>& m) {
    Preferences p{};

    auto apply_str = [&](const std::string& key, std::string& field) {
        auto it = m.find(key);
        if (it != m.end()) {
            field = it->second;
        }
    };

    auto apply_bool = [&](const std::string& key, bool& field) {
        auto it = m.find(key);
        if (it != m.end()) {
            field = to_bool(it->second);
        }
    };

    apply_str ("port",      p.port);
    apply_str ("mode",      p.mode);
    apply_bool("save_csv",  p.save_csv);
    apply_bool("save_h5",   p.save_h5);
    apply_bool("save_xlsx", p.save_xlsx);
    apply_str ("window",    p.window);
    apply_str ("gain",      p.gain);
    apply_str ("speed",     p.speed);

    return p;
}

} // namespace ads1292::gui
