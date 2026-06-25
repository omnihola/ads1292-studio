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

}  // namespace io
}  // namespace ads1292
