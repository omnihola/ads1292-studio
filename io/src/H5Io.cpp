#include "ads1292/io/H5Io.h"
#include "ads1292/crypto/Sha256.h"
#include <hdf5.h>
#include <cstdint>
#include <cstdio>
#include <sstream>
#include <stdexcept>
#include <vector>
#include "H5Raii.h"

namespace ads1292 {
namespace io {
using detail::Hid;

// ── smoke round-trip (Task 2) ────────────────────────────────────────────────
bool h5_smoke_roundtrip(const std::string& path) {
  const std::vector<int32_t> data = {1, 2, 3, -4};
  {
    Hid file(H5Fcreate(path.c_str(), H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT), H5Fclose);
    hsize_t dims[1] = {data.size()};
    Hid space(H5Screate_simple(1, dims, nullptr), H5Sclose);
    Hid dset(H5Dcreate2(file.get(), "v", H5T_STD_I32LE, space.get(),
                        H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT), H5Dclose);
    H5Dwrite(dset.get(), H5T_NATIVE_INT32, H5S_ALL, H5S_ALL, H5P_DEFAULT, data.data());
  }
  std::vector<int32_t> read_buf(data.size(), 0);
  {
    Hid file(H5Fopen(path.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT), H5Fclose);
    Hid dset(H5Dopen2(file.get(), "v", H5P_DEFAULT), H5Dclose);
    H5Dread(dset.get(), H5T_NATIVE_INT32, H5S_ALL, H5S_ALL, H5P_DEFAULT, read_buf.data());
  }
  return read_buf == data;
}

// ── dataset_float64_sha256 ───────────────────────────────────────────────────
std::string dataset_float64_sha256(const std::vector<double>& values) {
  return sha256_hex(reinterpret_cast<const uint8_t*>(values.data()),
                    values.size() * sizeof(double));
}

// ── helpers ──────────────────────────────────────────────────────────────────

// Read a string attribute from an HDF5 object (handles both fixed and variable-
// length string types).  Returns the string value.
static std::string read_str_attr(hid_t obj, const char* attr_name) {
  hid_t attr_raw = H5Aopen(obj, attr_name, H5P_DEFAULT);
  if (attr_raw < 0) throw std::runtime_error(std::string("Cannot open attr: ") + attr_name);
  Hid attr(attr_raw, H5Aclose);

  hid_t ftype_raw = H5Aget_type(attr.get());
  if (ftype_raw < 0) throw std::runtime_error("H5Aget_type failed");
  Hid ftype(ftype_raw, H5Tclose);

  std::string result;

  if (H5Tis_variable_str(ftype.get()) > 0) {
    // Variable-length string attribute
    hid_t memtype_raw = H5Tcopy(H5T_C_S1);
    H5Tset_size(memtype_raw, H5T_VARIABLE);
    H5Tset_cset(memtype_raw, H5T_CSET_UTF8);
    Hid memtype(memtype_raw, H5Tclose);

    char* buf = nullptr;
    herr_t err = H5Aread(attr.get(), memtype.get(), &buf);
    if (err < 0) throw std::runtime_error(std::string("H5Aread failed for attr: ") + attr_name);
    if (buf) {
      result = buf;
      H5free_memory(buf);
    }
  } else {
    // Fixed-length string attribute
    hsize_t sz = H5Tget_size(ftype.get());
    std::vector<char> buf(sz + 1, '\0');
    Hid memtype(H5Tcopy(H5T_C_S1), H5Tclose);
    H5Tset_size(memtype.get(), sz);
    H5Tset_cset(memtype.get(), H5T_CSET_UTF8);
    H5Tset_strpad(memtype.get(), H5T_STR_NULLTERM);
    herr_t err = H5Aread(attr.get(), memtype.get(), buf.data());
    if (err < 0) throw std::runtime_error(std::string("H5Aread fixed failed for attr: ") + attr_name);
    // Strip null padding
    result = std::string(buf.data());
  }

  return result;
}

// Read variable-length string scalar dataset
static std::string read_vlen_str_dataset(hid_t file, const char* ds_name) {
  hid_t dset_raw = H5Dopen2(file, ds_name, H5P_DEFAULT);
  if (dset_raw < 0) throw std::runtime_error(std::string("Cannot open dataset: ") + ds_name);
  Hid dset(dset_raw, H5Dclose);

  hid_t memtype_raw = H5Tcopy(H5T_C_S1);
  H5Tset_size(memtype_raw, H5T_VARIABLE);
  H5Tset_cset(memtype_raw, H5T_CSET_UTF8);
  Hid memtype(memtype_raw, H5Tclose);

  char* buf = nullptr;
  herr_t err = H5Dread(dset.get(), memtype.get(), H5S_ALL, H5S_ALL, H5P_DEFAULT, &buf);
  if (err < 0) throw std::runtime_error(std::string("H5Dread failed for: ") + ds_name);

  std::string result;
  if (buf) {
    result = buf;
    H5free_memory(buf);
  }
  return result;
}

// ── read_recording_h5 ────────────────────────────────────────────────────────
H5Recording read_recording_h5(const std::string& path) {
  Hid file(H5Fopen(path.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT), H5Fclose);

  H5Recording rec;

  // ── Root attributes ──────────────────────────────────────────────────────
  rec.attrs.schema      = read_str_attr(file.get(), "schema");
  rec.attrs.created_at  = read_str_attr(file.get(), "created_at");
  rec.attrs.csv_name    = read_str_attr(file.get(), "csv_name");

  // sample_rate_hz stored as float — read and format to match sidecar "500.0"
  {
    hid_t attr_raw = H5Aopen(file.get(), "sample_rate_hz", H5P_DEFAULT);
    if (attr_raw < 0) throw std::runtime_error("Cannot open attr: sample_rate_hz");
    Hid attr(attr_raw, H5Aclose);
    double val = 0.0;
    H5Aread(attr.get(), H5T_NATIVE_DOUBLE, &val);
    // Format: produce e.g. "500.0" — one decimal place when it's a whole number
    char buf[64];
    // Check if it is a whole number
    if (val == static_cast<long long>(val)) {
      std::snprintf(buf, sizeof(buf), "%.1f", val);
    } else {
      std::snprintf(buf, sizeof(buf), "%g", val);
    }
    rec.attrs.sample_rate_hz = buf;
  }

  // sample_count stored as int attr — read and format as decimal string "50"
  {
    hid_t attr_raw = H5Aopen(file.get(), "sample_count", H5P_DEFAULT);
    if (attr_raw < 0) throw std::runtime_error("Cannot open attr: sample_count");
    Hid attr(attr_raw, H5Aclose);

    // Determine the stored type to read correctly
    hid_t ftype_raw = H5Aget_type(attr.get());
    Hid ftype(ftype_raw, H5Tclose);
    H5T_class_t cls = H5Tget_class(ftype.get());

    long long val = 0;
    if (cls == H5T_INTEGER) {
      H5Aread(attr.get(), H5T_NATIVE_LLONG, &val);
    } else if (cls == H5T_FLOAT) {
      double dval = 0.0;
      H5Aread(attr.get(), H5T_NATIVE_DOUBLE, &dval);
      val = static_cast<long long>(dval);
    } else {
      // Try as string
      rec.attrs.sample_count = read_str_attr(file.get(), "sample_count");
      goto done_sample_count;
    }
    {
      char buf[32];
      std::snprintf(buf, sizeof(buf), "%lld", val);
      rec.attrs.sample_count = buf;
    }
    done_sample_count:;
  }

  // ── Sample datasets ──────────────────────────────────────────────────────
  hsize_t n = 0;
  {
    Hid dset(H5Dopen2(file.get(), "samples/timestamp", H5P_DEFAULT), H5Dclose);
    Hid space(H5Dget_space(dset.get()), H5Sclose);
    n = static_cast<hsize_t>(H5Sget_simple_extent_npoints(space.get()));
  }

  std::vector<double>   timestamp(n);
  std::vector<int32_t>  ch1(n), ch2(n);
  std::vector<uint16_t> status_byte(n);
  std::vector<int16_t>  board_heart_rate(n), board_respiration_rate(n);

  auto read_ds = [&](const char* name, hid_t memtype, void* buf) {
    Hid dset(H5Dopen2(file.get(), name, H5P_DEFAULT), H5Dclose);
    herr_t err = H5Dread(dset.get(), memtype, H5S_ALL, H5S_ALL, H5P_DEFAULT, buf);
    if (err < 0) throw std::runtime_error(std::string("H5Dread failed: ") + name);
  };

  read_ds("samples/timestamp",              H5T_NATIVE_DOUBLE,  timestamp.data());
  read_ds("samples/ch1",                    H5T_NATIVE_INT32,   ch1.data());
  read_ds("samples/ch2",                    H5T_NATIVE_INT32,   ch2.data());
  read_ds("samples/status_byte",            H5T_NATIVE_UINT16,  status_byte.data());
  read_ds("samples/board_heart_rate",       H5T_NATIVE_INT16,   board_heart_rate.data());
  read_ds("samples/board_respiration_rate", H5T_NATIVE_INT16,   board_respiration_rate.data());

  rec.samples.resize(n);
  for (hsize_t i = 0; i < n; ++i) {
    rec.samples[i].timestamp             = timestamp[i];
    rec.samples[i].ch1                   = ch1[i];
    rec.samples[i].ch2                   = ch2[i];
    rec.samples[i].status_byte           = static_cast<int>(status_byte[i]);
    rec.samples[i].board_heart_rate      = static_cast<int>(board_heart_rate[i]);
    rec.samples[i].board_respiration_rate = static_cast<int>(board_respiration_rate[i]);
  }

  // ── bundle_json ──────────────────────────────────────────────────────────
  rec.bundle_json = read_vlen_str_dataset(file.get(), "bundle_json");

  return rec;
}

// ── helpers for write ────────────────────────────────────────────────────────

// Write a fixed-length UTF-8 string attribute on an HDF5 object.
static void write_str_attr(hid_t obj, const char* name, const std::string& value) {
  hid_t strtype_raw = H5Tcopy(H5T_C_S1);
  H5Tset_size(strtype_raw, value.size() + 1);
  H5Tset_cset(strtype_raw, H5T_CSET_UTF8);
  H5Tset_strpad(strtype_raw, H5T_STR_NULLTERM);
  Hid strtype(strtype_raw, H5Tclose);

  Hid space(H5Screate(H5S_SCALAR), H5Sclose);
  hid_t attr_raw = H5Acreate2(obj, name, strtype.get(), space.get(), H5P_DEFAULT, H5P_DEFAULT);
  Hid attr(attr_raw, H5Aclose);
  H5Awrite(attr.get(), strtype.get(), value.c_str());
}

// Write a scalar string attribute using the same type as the value buffer.
static void write_str_attr_value(hid_t obj, const char* name, const std::string& value) {
  write_str_attr(obj, name, value);
}

// Write a 1-D typed dataset into a group.
template <typename T>
static void write_typed_dataset(hid_t group, const char* name, hid_t h5type,
                                const std::vector<T>& data) {
  hsize_t dims[1] = {data.size()};
  Hid space(H5Screate_simple(1, dims, nullptr), H5Sclose);
  Hid dset(H5Dcreate2(group, name, h5type, space.get(),
                      H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT), H5Dclose);

  // Determine the native memory type for T
  hid_t memtype = H5T_NATIVE_DOUBLE;
  if constexpr (std::is_same_v<T, int32_t>)  memtype = H5T_NATIVE_INT32;
  else if constexpr (std::is_same_v<T, uint16_t>) memtype = H5T_NATIVE_UINT16;
  else if constexpr (std::is_same_v<T, int16_t>)  memtype = H5T_NATIVE_INT16;
  // else double -> H5T_NATIVE_DOUBLE

  herr_t err = H5Dwrite(dset.get(), memtype, H5S_ALL, H5S_ALL, H5P_DEFAULT, data.data());
  if (err < 0) throw std::runtime_error(std::string("H5Dwrite failed: ") + name);
}

// ── write_recording_h5 ───────────────────────────────────────────────────────
void write_recording_h5(const std::string& path,
                        const std::vector<StreamSample>& samples,
                        const std::string& bundle_json,
                        const H5Attrs& attrs) {
  Hid file(H5Fcreate(path.c_str(), H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT), H5Fclose);

  // ── Root attributes ──────────────────────────────────────────────────────
  write_str_attr(file.get(), "schema",     attrs.schema.empty() ? "ads1292-h5/1" : attrs.schema);
  write_str_attr(file.get(), "created_at", attrs.created_at);
  write_str_attr(file.get(), "csv_name",   attrs.csv_name);

  // sample_rate_hz as float64 attr
  {
    double rate = 0.0;
    try { rate = std::stod(attrs.sample_rate_hz); } catch (...) {}
    Hid space(H5Screate(H5S_SCALAR), H5Sclose);
    Hid attr(H5Acreate2(file.get(), "sample_rate_hz", H5T_IEEE_F64LE, space.get(),
                        H5P_DEFAULT, H5P_DEFAULT), H5Aclose);
    H5Awrite(attr.get(), H5T_NATIVE_DOUBLE, &rate);
  }

  // sample_count as int64 attr
  {
    int64_t count = static_cast<int64_t>(samples.size());
    Hid space(H5Screate(H5S_SCALAR), H5Sclose);
    Hid attr(H5Acreate2(file.get(), "sample_count", H5T_STD_I64LE, space.get(),
                        H5P_DEFAULT, H5P_DEFAULT), H5Aclose);
    H5Awrite(attr.get(), H5T_NATIVE_INT64, &count);
  }

  // ── Build typed vectors ──────────────────────────────────────────────────
  const hsize_t n = samples.size();
  std::vector<double>   timestamp(n);
  std::vector<int32_t>  ch1(n), ch2(n);
  std::vector<uint16_t> status_byte(n);
  std::vector<int16_t>  board_heart_rate(n), board_respiration_rate(n);

  for (hsize_t i = 0; i < n; ++i) {
    timestamp[i]              = samples[i].timestamp;
    ch1[i]                    = static_cast<int32_t>(samples[i].ch1);
    ch2[i]                    = static_cast<int32_t>(samples[i].ch2);
    status_byte[i]            = static_cast<uint16_t>(samples[i].status_byte);
    board_heart_rate[i]       = static_cast<int16_t>(samples[i].board_heart_rate);
    board_respiration_rate[i] = static_cast<int16_t>(samples[i].board_respiration_rate);
  }

  // ── Group samples + datasets ─────────────────────────────────────────────
  Hid samples_grp(H5Gcreate2(file.get(), "samples", H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT),
                  H5Gclose);
  write_typed_dataset(samples_grp.get(), "timestamp",              H5T_IEEE_F64LE, timestamp);
  write_typed_dataset(samples_grp.get(), "ch1",                    H5T_STD_I32LE,  ch1);
  write_typed_dataset(samples_grp.get(), "ch2",                    H5T_STD_I32LE,  ch2);
  write_typed_dataset(samples_grp.get(), "status_byte",            H5T_STD_U16LE,  status_byte);
  write_typed_dataset(samples_grp.get(), "board_heart_rate",       H5T_STD_I16LE,  board_heart_rate);
  write_typed_dataset(samples_grp.get(), "board_respiration_rate", H5T_STD_I16LE,  board_respiration_rate);

  // ── bundle_json scalar variable-length UTF-8 string dataset ─────────────
  {
    hid_t strtype_raw = H5Tcopy(H5T_C_S1);
    H5Tset_size(strtype_raw, H5T_VARIABLE);
    H5Tset_cset(strtype_raw, H5T_CSET_UTF8);
    Hid strtype(strtype_raw, H5Tclose);

    Hid space(H5Screate(H5S_SCALAR), H5Sclose);
    Hid dset(H5Dcreate2(file.get(), "bundle_json", strtype.get(), space.get(),
                        H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT), H5Dclose);
    const char* ptr = bundle_json.c_str();
    herr_t err = H5Dwrite(dset.get(), strtype.get(), H5S_ALL, H5S_ALL, H5P_DEFAULT, &ptr);
    if (err < 0) throw std::runtime_error("H5Dwrite failed for bundle_json");
  }

  // ── Integrity group: native-dtype SHA-256 for each array ─────────────────
  Hid integrity_grp(H5Gcreate2(file.get(), "integrity", H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT),
                    H5Gclose);

  auto write_integrity_attr = [&](const char* attr_name, const void* data_ptr, size_t byte_count) {
    std::string hash = sha256_hex(static_cast<const uint8_t*>(data_ptr), byte_count);
    write_str_attr(integrity_grp.get(), attr_name, hash);
  };

  write_integrity_attr("sha256_timestamp",
      timestamp.data(),              n * sizeof(double));
  write_integrity_attr("sha256_ch1",
      ch1.data(),                    n * sizeof(int32_t));
  write_integrity_attr("sha256_ch2",
      ch2.data(),                    n * sizeof(int32_t));
  write_integrity_attr("sha256_status_byte",
      status_byte.data(),            n * sizeof(uint16_t));
  write_integrity_attr("sha256_board_heart_rate",
      board_heart_rate.data(),       n * sizeof(int16_t));
  write_integrity_attr("sha256_board_respiration_rate",
      board_respiration_rate.data(), n * sizeof(int16_t));
}

// ── verify_recording_h5 ──────────────────────────────────────────────────────
H5Verification verify_recording_h5(const std::string& path) {
  H5Verification result{true, 0, {}};

  Hid file(H5Fopen(path.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT), H5Fclose);

  // Read sample_count attr
  long long expected_count = 0;
  {
    hid_t attr_raw = H5Aopen(file.get(), "sample_count", H5P_DEFAULT);
    if (attr_raw < 0) {
      result.ok = false;
      result.failures.push_back("Cannot open sample_count attr");
      return result;
    }
    Hid attr(attr_raw, H5Aclose);
    hid_t ftype_raw = H5Aget_type(attr.get());
    Hid ftype(ftype_raw, H5Tclose);
    H5T_class_t cls = H5Tget_class(ftype.get());
    if (cls == H5T_INTEGER) {
      H5Aread(attr.get(), H5T_NATIVE_LLONG, &expected_count);
    } else {
      double dval = 0.0;
      H5Aread(attr.get(), H5T_NATIVE_DOUBLE, &dval);
      expected_count = static_cast<long long>(dval);
    }
  }

  // Open integrity group
  hid_t integrity_raw = H5Gopen2(file.get(), "integrity", H5P_DEFAULT);
  if (integrity_raw < 0) {
    result.ok = false;
    result.failures.push_back("Cannot open integrity group");
    return result;
  }
  Hid integrity_grp(integrity_raw, H5Gclose);

  // Helper: read a string attr from the integrity group
  auto read_integrity_hash = [&](const char* attr_name) -> std::string {
    hid_t attr_raw = H5Aopen(integrity_grp.get(), attr_name, H5P_DEFAULT);
    if (attr_raw < 0) return "";
    Hid attr(attr_raw, H5Aclose);

    hid_t ftype_raw = H5Aget_type(attr.get());
    Hid ftype(ftype_raw, H5Tclose);

    if (H5Tis_variable_str(ftype.get()) > 0) {
      hid_t memtype_raw = H5Tcopy(H5T_C_S1);
      H5Tset_size(memtype_raw, H5T_VARIABLE);
      H5Tset_cset(memtype_raw, H5T_CSET_UTF8);
      Hid memtype(memtype_raw, H5Tclose);
      char* buf = nullptr;
      H5Aread(attr.get(), memtype.get(), &buf);
      std::string s;
      if (buf) { s = buf; H5free_memory(buf); }
      return s;
    } else {
      hsize_t sz = H5Tget_size(ftype.get());
      std::vector<char> buf(sz + 1, '\0');
      Hid memtype(H5Tcopy(H5T_C_S1), H5Tclose);
      H5Tset_size(memtype.get(), sz);
      H5Tset_cset(memtype.get(), H5T_CSET_UTF8);
      H5Tset_strpad(memtype.get(), H5T_STR_NULLTERM);
      H5Aread(attr.get(), memtype.get(), buf.data());
      return std::string(buf.data());
    }
  };

  // Per-dataset verification: read typed buffer, recompute native hash, compare
  struct DsInfo {
    const char* ds_path;       // e.g. "samples/timestamp"
    const char* integrity_key; // e.g. "sha256_timestamp"
    hid_t       memtype;       // native memory type for reading
    size_t      elem_size;     // sizeof element in the typed buffer
  };

  const DsInfo datasets[] = {
    {"samples/timestamp",              "sha256_timestamp",              H5T_NATIVE_DOUBLE,  sizeof(double)},
    {"samples/ch1",                    "sha256_ch1",                    H5T_NATIVE_INT32,   sizeof(int32_t)},
    {"samples/ch2",                    "sha256_ch2",                    H5T_NATIVE_INT32,   sizeof(int32_t)},
    {"samples/status_byte",            "sha256_status_byte",            H5T_NATIVE_UINT16,  sizeof(uint16_t)},
    {"samples/board_heart_rate",       "sha256_board_heart_rate",       H5T_NATIVE_INT16,   sizeof(int16_t)},
    {"samples/board_respiration_rate", "sha256_board_respiration_rate", H5T_NATIVE_INT16,   sizeof(int16_t)},
  };

  for (const auto& ds : datasets) {
    hid_t dset_raw = H5Dopen2(file.get(), ds.ds_path, H5P_DEFAULT);
    if (dset_raw < 0) {
      result.ok = false;
      result.failures.push_back(std::string("Cannot open dataset: ") + ds.ds_path);
      continue;
    }
    Hid dset(dset_raw, H5Dclose);

    // Get element count
    Hid space(H5Dget_space(dset.get()), H5Sclose);
    hssize_t n = H5Sget_simple_extent_npoints(space.get());
    if (n < 0) {
      result.ok = false;
      result.failures.push_back(std::string("Cannot get extent for: ") + ds.ds_path);
      continue;
    }

    // Check count matches sample_count attr
    if (n != expected_count) {
      result.ok = false;
      result.failures.push_back(std::string("Length mismatch for: ") + ds.ds_path);
    }

    // Read into raw byte buffer
    size_t byte_count = static_cast<size_t>(n) * ds.elem_size;
    std::vector<uint8_t> buf(byte_count, 0);
    herr_t err = H5Dread(dset.get(), ds.memtype, H5S_ALL, H5S_ALL, H5P_DEFAULT, buf.data());
    if (err < 0) {
      result.ok = false;
      result.failures.push_back(std::string("H5Dread failed for: ") + ds.ds_path);
      continue;
    }

    // Recompute native-byte hash
    std::string computed = sha256_hex(buf.data(), byte_count);
    std::string stored   = read_integrity_hash(ds.integrity_key);

    if (stored.empty()) {
      result.ok = false;
      result.failures.push_back(std::string("Missing integrity attr: ") + ds.integrity_key);
    } else if (computed != stored) {
      result.ok = false;
      result.failures.push_back(std::string("Hash mismatch for: ") + ds.ds_path
                                 + " expected=" + stored + " got=" + computed);
    }

    ++result.checked;
  }

  return result;
}

}  // namespace io
}  // namespace ads1292
