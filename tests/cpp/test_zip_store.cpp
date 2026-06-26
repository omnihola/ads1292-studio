#include "catch.hpp"
#include "ads1292/io/ZipStoreWriter.h"
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <string>

namespace fs = std::filesystem;

static std::string read_file(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(f),
                       std::istreambuf_iterator<char>());
}

TEST_CASE("ZipStoreWriter produces a valid STORE-method ZIP", "[zip]") {
    ads1292::io::ZipStoreWriter z;
    z.add("hello.txt", "Hello, world");
    z.add("dir/a.xml", "<x/>");

    const auto tmp      = fs::temp_directory_path();
    const auto zip_path = (tmp / "p11_zip.zip").string();

    z.write(zip_path);
    REQUIRE(fs::exists(zip_path));
    REQUIRE(fs::file_size(zip_path) > 0);

    SECTION("hello.txt extracts byte-for-byte") {
        const auto out = (tmp / "p11_zip_hello.txt").string();
        std::string cmd = "/usr/bin/unzip -p '" + zip_path + "' hello.txt > '" + out + "' 2>/dev/null";
        int rc = std::system(cmd.c_str());
        REQUIRE(rc == 0);
        REQUIRE(read_file(out) == "Hello, world");
    }

    SECTION("dir/a.xml extracts byte-for-byte") {
        const auto out = (tmp / "p11_zip_a.xml").string();
        std::string cmd = "/usr/bin/unzip -p '" + zip_path + "' dir/a.xml > '" + out + "' 2>/dev/null";
        int rc = std::system(cmd.c_str());
        REQUIRE(rc == 0);
        REQUIRE(read_file(out) == "<x/>");
    }

    SECTION("unzip -l lists both entries") {
        const auto listing = (tmp / "p11_zip_listing.txt").string();
        std::string cmd = "/usr/bin/unzip -l '" + zip_path + "' > '" + listing + "' 2>/dev/null";
        int rc = std::system(cmd.c_str());
        REQUIRE(rc == 0);
        const std::string contents = read_file(listing);
        REQUIRE(contents.find("hello.txt") != std::string::npos);
        REQUIRE(contents.find("dir/a.xml") != std::string::npos);
    }
}
