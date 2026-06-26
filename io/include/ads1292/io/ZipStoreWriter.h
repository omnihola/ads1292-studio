#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace ads1292::io {

/// Minimal, dependency-free ZIP writer using STORE method (compression 0).
/// Builds local file headers + central directory + EOCD per the ZIP spec.
/// CRC-32 is computed internally; no zlib required.
class ZipStoreWriter {
public:
    /// Accumulate one entry. `name` is the in-archive path; `data` is the raw bytes.
    void add(const std::string& name, const std::string& data);

    /// Serialize to a complete, spec-compliant ZIP byte string.
    std::string bytes() const;

    /// Write bytes() to a file at `path`.
    void write(const std::string& path) const;

private:
    struct Entry {
        std::string name;
        std::string data;
        uint32_t    crc;
        uint32_t    offset; // byte offset of this entry's local header in the output
    };
    std::vector<Entry> entries_;
};

} // namespace ads1292::io
