# ADS1292 Studio — macOS Packaging

This document describes the full pipeline for building a self-contained, distributable macOS `.app` bundle and DMG for `ads1292_gui`.

---

## Prerequisites

- macOS with Xcode Command Line Tools (`xcode-select --install`)
- Qt 6 via Homebrew: `brew install qt`
- HDF5 via Homebrew: `brew install hdf5`
- `macdeployqt` at `/opt/homebrew/opt/qt/bin/macdeployqt`
- `hdiutil` (standard macOS utility)

---

## Step 1: Release Build

Build all targets in Release mode (required for distribution — debug builds include development paths):

```bash
CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" \
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release

cmake --build build -j
```

After building, the raw (not yet self-contained) app bundle is at:

```
build/gui/ads1292_gui.app/
```

---

## Step 2: Deploy the .app (macdeployqt + HDF5 bundling)

```bash
./packaging/deploy_macos.sh build/gui/ads1292_gui.app
```

What this script does:

1. **macdeployqt** — copies all required Qt frameworks (`QtCore`, `QtGui`, `QtWidgets`, `QtPrintSupport`, `QtSerialPort`, etc.) and platform plugins into `Contents/Frameworks/` and `Contents/PlugIns/`, and rewrites their install names to `@executable_path`-relative paths. macdeployqt does **not** handle non-Qt dylibs.

2. **Offscreen platform plugin** — copies `libqoffscreen.dylib` into `Contents/PlugIns/platforms/` and rewrites its `@rpath` references (needed for the smoke test and for users running the app without a display).

3. **HDF5 + transitive deps** — runs a fixed-point loop (up to 10 passes) that:
   - scans every bundled binary and dylib with `otool -L` for `/opt/homebrew` references,
   - copies each unresolved Homebrew dylib (`libhdf5`, `libsz`/`libaec`, `libbrotli*`, etc.) into `Contents/Frameworks/`,
   - rewrites its install name in the referencing binary with `install_name_tool -change`,
   - rewrites its own `LC_ID_DYLIB` with `install_name_tool -id`,
   - repeats until no `/opt/homebrew` reference remains in any bundled file.

4. **Self-containment gate** — scans every file under `Contents/MacOS/`, `Contents/Frameworks/`, and `Contents/PlugIns/`. If any file still references `/opt/homebrew`, the script exits 1 with a diagnostic. Pass means every dynamic dependency resolves to `@rpath`, `@executable_path`, `@loader_path`, or a macOS system path (`/usr/lib`, `/System`).

5. **Smoke test** — runs the bundled executable offscreen:
   ```
   QT_QPA_PLATFORM=offscreen build/gui/ads1292_gui.app/Contents/MacOS/ads1292_gui --smoke
   ```
   Must exit 0 (constructs `MainWindow`, runs a simulator cycle, quits cleanly).

The script fails loudly if either gate is not met.

---

## Step 3: Make the DMG

```bash
./packaging/make_dmg.sh build/gui/ads1292_gui.app build/ADS1292-Studio.dmg
```

What this script does:

1. Validates the `.app` exists (produced by `deploy_macos.sh`).
2. Stages a temp directory with the `.app` and an `Applications` symlink (standard drag-to-install UI).
3. Creates a compressed DMG (`hdiutil create -format UDZO`) with the volume name **ADS1292 Studio**.
4. Verifies the DMG is non-empty, then attaches it read-only, confirms the `.app` and `Applications` symlink are present, and detaches.
5. Prints `DMG: PASS` on success.

The DMG is a **build artifact** (`build/` is gitignored) — it is **not committed**.

---

## The Three Binaries

| Binary | Type | Distribution |
|---|---|---|
| `ads1292_gui` | Qt Widgets GUI — packaged as `ads1292_gui.app` / DMG | Self-contained via `deploy_macos.sh` + `make_dmg.sh` |
| `ads1292_cli` | Qt-free analysis CLI (`qc`, `report`, `verify`, `index`, `batch`) — links HDF5 via `io` | Runs from `build/cli/ads1292_cli`; standalone deploy is a follow-up |
| `ads1292_devcli` | Device CLI (`ports`, `firmware`, `stream`) — links Qt SerialPort | Runs from `build/devcli/ads1292_devcli`; standalone deploy is a follow-up |

`ads1292_cli` and `ads1292_devcli` are currently not packaged for standalone distribution. They run correctly from the build directory in a dev environment with Homebrew Qt and HDF5 installed. Deploying them standalone (bundling their dylibs similarly to `deploy_macos.sh`) is a planned follow-up task.

---

## Codesigning and Notarization (Out of Scope)

The `.app` and DMG produced above are **unsigned**. On macOS, unsigned apps from the internet trigger Gatekeeper and cannot be opened without the user manually overriding the security setting.

For Gatekeeper-clean distribution, the next steps are:

```bash
# Sign the .app (requires a Developer ID Application certificate)
codesign --deep --force --sign "Developer ID Application: <Team Name> (<Team ID>)" \
    build/gui/ads1292_gui.app

# Notarize the DMG with Apple
xcrun notarytool submit build/ADS1292-Studio.dmg \
    --apple-id "<apple-id>" \
    --team-id "<team-id>" \
    --password "<app-specific-password>" \
    --wait

# Staple the notarization ticket
xcrun stapler staple build/ADS1292-Studio.dmg
```

Codesigning and notarization are **not automated** in this repo and are out of scope for the current packaging pipeline.
