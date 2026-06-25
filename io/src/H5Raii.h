#pragma once
#include <hdf5.h>
#include <stdexcept>
#include <string>

namespace ads1292 {
namespace io {
namespace detail {

// Owns an hid_t and closes it with the provided closer (H5Fclose, H5Dclose, ...).
class Hid {
 public:
  Hid() = default;
  Hid(hid_t id, herr_t (*closer)(hid_t)) : id_(id), closer_(closer) {
    if (id_ < 0) throw std::runtime_error("HDF5 returned an invalid handle");
  }
  ~Hid() { reset(); }
  Hid(const Hid&) = delete;
  Hid& operator=(const Hid&) = delete;
  Hid(Hid&& o) noexcept : id_(o.id_), closer_(o.closer_) { o.id_ = -1; o.closer_ = nullptr; }
  Hid& operator=(Hid&& o) noexcept {
    if (this != &o) { reset(); id_ = o.id_; closer_ = o.closer_; o.id_ = -1; o.closer_ = nullptr; }
    return *this;
  }
  hid_t get() const { return id_; }
  void reset() { if (id_ >= 0 && closer_) closer_(id_); id_ = -1; closer_ = nullptr; }

 private:
  hid_t id_ = -1;
  herr_t (*closer_)(hid_t) = nullptr;
};

}  // namespace detail
}  // namespace io
}  // namespace ads1292
