#include "ads1292/io/ZipStoreWriter.h"
#include <fstream>
#include <stdexcept>

namespace ads1292::io {

// ---------------------------------------------------------------------------
// CRC-32: standard reflected polynomial 0xEDB88320
// init = 0xFFFFFFFF, final XOR = 0xFFFFFFFF
// ---------------------------------------------------------------------------
static uint32_t compute_crc32(const std::string& data) {
    uint32_t crc = 0xFFFFFFFF;
    for (unsigned char byte : data) {
        crc ^= byte;
        for (int bit = 0; bit < 8; ++bit) {
            if (crc & 1u)
                crc = (crc >> 1) ^ 0xEDB88320u;
            else
                crc >>= 1;
        }
    }
    return crc ^ 0xFFFFFFFF;
}

// ---------------------------------------------------------------------------
// Little-endian helpers
// ---------------------------------------------------------------------------
static void put16(std::string& s, uint16_t v) {
    s += static_cast<char>(v & 0xFF);
    s += static_cast<char>((v >> 8) & 0xFF);
}

static void put32(std::string& s, uint32_t v) {
    s += static_cast<char>(v & 0xFF);
    s += static_cast<char>((v >> 8) & 0xFF);
    s += static_cast<char>((v >> 16) & 0xFF);
    s += static_cast<char>((v >> 24) & 0xFF);
}

// ---------------------------------------------------------------------------
// ZipStoreWriter
// ---------------------------------------------------------------------------
void ZipStoreWriter::add(const std::string& name, const std::string& data) {
    Entry e;
    e.name   = name;
    e.data   = data;
    e.crc    = compute_crc32(data);
    e.offset = 0; // filled during bytes()
    entries_.push_back(std::move(e));
}

std::string ZipStoreWriter::bytes() const {
    std::string out;
    // Reserve a reasonable capacity to avoid many reallocations
    out.reserve(4096);

    // Track per-entry local-header offsets (needed for central directory)
    std::vector<uint32_t> local_offsets;
    local_offsets.reserve(entries_.size());

    // ------------------------------------------------------------------
    // 1. Local file headers + file data
    // ------------------------------------------------------------------
    for (const auto& e : entries_) {
        local_offsets.push_back(static_cast<uint32_t>(out.size()));

        const auto name_len  = static_cast<uint16_t>(e.name.size());
        const auto data_size = static_cast<uint32_t>(e.data.size());

        put32(out, 0x04034b50u); // local file header signature
        put16(out, 20);          // version needed to extract
        put16(out, 0);           // general purpose bit flag
        put16(out, 0);           // compression method (STORE)
        put16(out, 0);           // last mod file time
        put16(out, 0);           // last mod file date
        put32(out, e.crc);       // CRC-32
        put32(out, data_size);   // compressed size
        put32(out, data_size);   // uncompressed size
        put16(out, name_len);    // file name length
        put16(out, 0);           // extra field length
        out += e.name;           // file name
        out += e.data;           // file data
    }

    // ------------------------------------------------------------------
    // 2. Central directory
    // ------------------------------------------------------------------
    const auto cd_offset = static_cast<uint32_t>(out.size());

    for (size_t i = 0; i < entries_.size(); ++i) {
        const auto& e = entries_[i];

        const auto name_len  = static_cast<uint16_t>(e.name.size());
        const auto data_size = static_cast<uint32_t>(e.data.size());

        put32(out, 0x02014b50u);    // central directory header signature
        put16(out, 20);             // version made by
        put16(out, 20);             // version needed to extract
        put16(out, 0);              // general purpose bit flag
        put16(out, 0);              // compression method
        put16(out, 0);              // last mod file time
        put16(out, 0);              // last mod file date
        put32(out, e.crc);          // CRC-32
        put32(out, data_size);      // compressed size
        put32(out, data_size);      // uncompressed size
        put16(out, name_len);       // file name length
        put16(out, 0);              // extra field length
        put16(out, 0);              // file comment length
        put16(out, 0);              // disk number start
        put16(out, 0);              // internal file attributes
        put32(out, 0);              // external file attributes
        put32(out, local_offsets[i]); // relative offset of local header
        out += e.name;              // file name
    }

    // ------------------------------------------------------------------
    // 3. End of central directory record (EOCD)
    // ------------------------------------------------------------------
    const auto cd_size    = static_cast<uint32_t>(out.size()) - cd_offset;
    const auto entry_count = static_cast<uint16_t>(entries_.size());

    put32(out, 0x06054b50u); // EOCD signature
    put16(out, 0);           // disk number
    put16(out, 0);           // disk where central directory starts
    put16(out, entry_count); // number of central directory records on this disk
    put16(out, entry_count); // total number of central directory records
    put32(out, cd_size);     // size of central directory (bytes)
    put32(out, cd_offset);   // offset of start of central directory
    put16(out, 0);           // comment length

    return out;
}

void ZipStoreWriter::write(const std::string& path) const {
    const std::string data = bytes();
    std::ofstream f(path, std::ios::binary);
    if (!f) {
        throw std::runtime_error("ZipStoreWriter::write: cannot open '" + path + "' for writing");
    }
    f.write(data.data(), static_cast<std::streamsize>(data.size()));
    if (!f) {
        throw std::runtime_error("ZipStoreWriter::write: write failed for '" + path + "'");
    }
}

} // namespace ads1292::io
