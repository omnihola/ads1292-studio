#include "ads1292/io/H5Io.h"
#include <hdf5.h>
#include <vector>
#include "H5Raii.h"

namespace ads1292 {
namespace io {
using detail::Hid;

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
  std::vector<int32_t> read(data.size(), 0);
  {
    Hid file(H5Fopen(path.c_str(), H5F_ACC_RDONLY, H5P_DEFAULT), H5Fclose);
    Hid dset(H5Dopen2(file.get(), "v", H5P_DEFAULT), H5Dclose);
    H5Dread(dset.get(), H5T_NATIVE_INT32, H5S_ALL, H5S_ALL, H5P_DEFAULT, read.data());
  }
  return read == data;
}

}  // namespace io
}  // namespace ads1292
