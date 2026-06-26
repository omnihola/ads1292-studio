# P8: macOS Packaging (.app bundle + dependency deploy + DMG) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the built `ads1292_gui` into a self-contained, distributable macOS app bundle — `ads1292_gui.app` with bundled Qt frameworks + HDF5 (via `macdeployqt` + an HDF5 fix-up), verified to launch standalone (no Homebrew/dev dylib paths) — and wrap it in a DMG.

**Architecture:** `gui/CMakeLists.txt` marks `ads1292_gui` as a `MACOSX_BUNDLE` with a committed `Info.plist`. A committed `packaging/deploy_macos.sh` runs `macdeployqt` (bundles the Qt frameworks/plugins) then copies the brew `libhdf5` into the bundle's `Contents/Frameworks` and rewrites the install names with `install_name_tool` (macdeployqt does NOT handle non-Qt dylibs). A committed `packaging/make_dmg.sh` builds the DMG. The self-containment GATE is automated: after deploy, `otool -L` on the bundled binary must show NO `/opt/homebrew` dynamic references (all `@rpath`/`@executable_path`/`@loader_path`), and the bundled binary runs `--smoke` (offscreen) → exit 0. The `.app`/`.dmg` are build artifacts (gitignored); the COMMITTED deliverables are the CMake change, `Info.plist`, the two scripts, and a packaging doc.

**Tech Stack:** CMake (MACOSX_BUNDLE), `macdeployqt` (`/opt/homebrew/opt/qt/bin/macdeployqt`), `install_name_tool`/`otool` (macOS), `hdiutil` (DMG). No new code dependencies.

## Global Constraints

- **macOS only** (the app is Qt Widgets; packaging is macOS `.app`/DMG). Keep `core`/`io`/`cli` portable as before — only `gui` becomes a bundle.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored — the `.app`/`.dmg` live there and are NOT committed; commit only CMake/Info.plist/scripts/doc.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j` (Release for distribution). The existing offscreen ctest suite must still pass.
- **Dynamic deps to bundle (from `otool -L build/gui/ads1292_gui`):** Qt frameworks `QtCore/QtGui/QtWidgets/QtPrintSupport/QtSerialPort` (handled by `macdeployqt`) + `libhdf5.320.dylib` (NOT handled by macdeployqt — the script must bundle it). The vendored libs (picosha2, kissfft, qcustomplot) are STATIC and nlohmann is header-only — no bundling needed.
- **Self-containment GATE (the parity-equivalent for packaging):** after `deploy_macos.sh`, `otool -L "<app>/Contents/MacOS/ads1292_gui"` shows NO line containing `/opt/homebrew` (every dynamic dep is `@rpath`/`@executable_path`/`@loader_path`/a system `/usr/lib` path), AND `QT_QPA_PLATFORM=offscreen "<app>/Contents/MacOS/ads1292_gui" --smoke; echo $?` prints `0`.
- **macdeployqt** is at `/opt/homebrew/opt/qt/bin/macdeployqt`. **HDF5** is `/opt/homebrew/opt/hdf5/lib/libhdf5.320.dylib` (resolve the exact basename from `otool -L` at deploy time — version may differ; read it dynamically). HDF5 itself may pull `libsz`/`libaec`/`libz` — chase the transitive non-system deps of libhdf5 (`otool -L` the bundled libhdf5) and bundle+fix those too.

## File Structure

```
gui/CMakeLists.txt          # MODIFY: MACOSX_BUNDLE TRUE + MACOSX_BUNDLE_INFO_PLIST
gui/Info.plist.in           # the bundle Info.plist template (CFBundleExecutable/Identifier/Name/Version/...)
packaging/deploy_macos.sh   # macdeployqt + bundle HDF5 (+ transitive) + install_name_tool rpath fix + self-containment check
packaging/make_dmg.sh       # build the DMG from the deployed .app
docs/PACKAGING.md           # how to build the .app + DMG
```

---

### Task 1: app bundle + dependency deploy + self-containment gate

**Files:** Modify `gui/CMakeLists.txt`; Create `gui/Info.plist.in`; Create `packaging/deploy_macos.sh`.

- [ ] **Step 1: Make `ads1292_gui` a MACOSX_BUNDLE + Info.plist.**
  - In `gui/CMakeLists.txt`: `add_executable(ads1292_gui MACOSX_BUNDLE src/main.cpp)` (or `set_target_properties(ads1292_gui PROPERTIES MACOSX_BUNDLE TRUE)`), and set `MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/Info.plist.in"`, plus the bundle vars: `set_target_properties(ads1292_gui PROPERTIES MACOSX_BUNDLE_BUNDLE_NAME "ADS1292 Studio" MACOSX_BUNDLE_GUI_IDENTIFIER "com.ads1292studio.gui" MACOSX_BUNDLE_BUNDLE_VERSION "1.0.0" MACOSX_BUNDLE_SHORT_VERSION_STRING "1.0.0" MACOSX_BUNDLE_EXECUTABLE_NAME "ads1292_gui")`.
  - Create `gui/Info.plist.in` — a standard Qt-app Info.plist template using the `${MACOSX_BUNDLE_*}` placeholders (`CFBundleExecutable=${MACOSX_BUNDLE_EXECUTABLE_NAME}`, `CFBundleIdentifier=${MACOSX_BUNDLE_GUI_IDENTIFIER}`, `CFBundleName=${MACOSX_BUNDLE_BUNDLE_NAME}`, `CFBundleShortVersionString`, `CFBundleVersion`, `CFBundlePackageType=APPL`, `LSMinimumSystemVersion`, `NSHighResolutionCapable=true`). (Guard the bundle settings behind `if(APPLE)`.)
  - Build (Release): `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j`. Confirm `build/gui/ads1292_gui.app/Contents/MacOS/ads1292_gui` exists. The existing tests must still build/pass.

- [ ] **Step 2: Write `packaging/deploy_macos.sh`** — takes the .app path (default `build/gui/ads1292_gui.app`):
  - `set -euo pipefail`.
  - run `/opt/homebrew/opt/qt/bin/macdeployqt "<app>" -verbose=1` (bundles Qt frameworks + the platform plugin into the .app).
  - bundle HDF5: from `otool -L "<app>/Contents/MacOS/ads1292_gui"`, find the `/opt/homebrew/.../libhdf5*.dylib` line → `HDF5_SRC`; `mkdir -p "<app>/Contents/Frameworks"`; `cp "$HDF5_SRC" "<app>/Contents/Frameworks/"`; `install_name_tool -change "$HDF5_SRC" "@executable_path/../Frameworks/$(basename "$HDF5_SRC")" "<app>/Contents/MacOS/ads1292_gui"`; `install_name_tool -id "@executable_path/../Frameworks/$(basename "$HDF5_SRC")" "<app>/Contents/Frameworks/$(basename "$HDF5_SRC")"`.
  - chase libhdf5's own non-system `/opt/homebrew` deps (`otool -L` the bundled libhdf5 → for each `/opt/homebrew/...dylib`, cp into Frameworks + `install_name_tool -change` on the bundled libhdf5 + `-id` on the copied lib) — loop until no `/opt/homebrew` refs remain in any bundled binary/dylib. (A small fixed-point loop, or 2-3 passes covering libhdf5→libsz/libaec/libz.)
  - **Self-containment check (FAIL the script if not met):** `if otool -L "<app>/Contents/MacOS/ads1292_gui" | grep -q "/opt/homebrew"; then echo "FAIL: residual /opt/homebrew dep"; otool -L ...; exit 1; fi`; same grep over each `Contents/Frameworks/*.dylib`. Then `QT_QPA_PLATFORM=offscreen "<app>/Contents/MacOS/ads1292_gui" --smoke; echo "smoke exit=$?"` and fail if non-zero.
  - `chmod +x packaging/deploy_macos.sh`.

- [ ] **Step 3: Run the deploy + verify the gate** from repo root:
  ```
  CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
  cmake --build build -j
  ./packaging/deploy_macos.sh build/gui/ads1292_gui.app
  ```
  Confirm the script prints the self-containment check PASS + `smoke exit=0`, and `otool -L build/gui/ads1292_gui.app/Contents/MacOS/ads1292_gui` shows no `/opt/homebrew`.

- [ ] **Step 4: Confirm the offscreen ctest suite still passes** (the MACOSX_BUNDLE change must not break the test build): `QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`.

- [ ] **Step 5: Commit** (CMake + Info.plist + script only — NOT the .app):
  ```bash
  git add gui/CMakeLists.txt gui/Info.plist.in packaging/deploy_macos.sh
  git commit -m "feat: P8 macOS .app bundle + dependency deploy (macdeployqt + HDF5)"
  ```

---

### Task 2: DMG packaging + doc

**Files:** Create `packaging/make_dmg.sh`; Create `docs/PACKAGING.md`.

- [ ] **Step 1: Write `packaging/make_dmg.sh`** — takes the deployed `.app` (default `build/gui/ads1292_gui.app`) + an output path (default `build/ADS1292-Studio.dmg`):
  - `set -euo pipefail`.
  - Prefer `macdeployqt "<app>" -dmg` (it can produce a DMG directly) OR a `hdiutil` path: stage a temp dir with the `.app` + an `Applications` symlink (`ln -s /Applications "<stage>/Applications"`), then `hdiutil create -volname "ADS1292 Studio" -srcfolder "<stage>" -ov -format UDZO "<dmg>"`.
  - Verify: `test -f "<dmg>"` and print its size; optionally `hdiutil attach "<dmg>" -nobrowse -readonly` → check the `.app` is inside → `hdiutil detach`.
  - `chmod +x packaging/make_dmg.sh`.

- [ ] **Step 2: Run it** (after Task 1's deploy):
  ```
  ./packaging/make_dmg.sh build/gui/ads1292_gui.app build/ADS1292-Studio.dmg
  ```
  Confirm the DMG is created (non-zero size) and, if attached, contains `ADS1292 Studio.app`/`ads1292_gui.app` + the Applications symlink.

- [ ] **Step 3: Write `docs/PACKAGING.md`** — document the full pipeline:
  - the Release build command, `./packaging/deploy_macos.sh`, `./packaging/make_dmg.sh`;
  - what each step does (macdeployqt bundles Qt; the script bundles HDF5 + transitive; the self-containment check);
  - the three binaries (`ads1292_gui` packaged as the .app; `ads1292_cli` + `ads1292_devcli` are standalone CLI binaries — note they link HDF5/Qt and would need their own deploy for distribution, or run from the dev env; mention deploying them is a follow-up);
  - codesigning/notarization is OUT OF SCOPE (note it as a future step for Gatekeeper-clean distribution).

- [ ] **Step 4: Commit** (scripts + doc only):
  ```bash
  git add packaging/make_dmg.sh docs/PACKAGING.md
  git commit -m "feat: P8 DMG packaging script + PACKAGING.md"
  ```

---

## Self-Review

**1. Spec coverage:** the `.app` bundle + dependency deploy (Qt via macdeployqt + HDF5 + transitive) + the self-containment gate → Task 1 ✓; DMG + packaging doc → Task 2 ✓. Codesigning/notarization → OUT OF SCOPE (documented). Packaging the CLI binaries (`ads1292_cli`/`ads1292_devcli`) for standalone distribution → noted as a follow-up (the .app is the primary deliverable).

**2. Placeholder scan:** the CMake MACOSX_BUNDLE settings, the Info.plist keys, the macdeployqt + install_name_tool + otool self-containment steps, and the hdiutil DMG path are spelled out concretely. The HDF5 basename + transitive deps are resolved DYNAMICALLY at deploy time (read from otool) since the version may vary — this is called out, not a placeholder. The gate (no /opt/homebrew + --smoke exit 0) is an automated, objective check.

**3. Type consistency:** N/A (build/distribution scripts, no C++ API). The deploy script consumes the `MACOSX_BUNDLE` output from the CMake change; make_dmg consumes the deployed `.app`.

**Risk notes for the executor:**
- The `.app`/`.dmg` are BUILD ARTIFACTS under `build/` (gitignored) — commit ONLY the CMake change, `Info.plist.in`, the scripts, and the doc. Never `git add build/`.
- `macdeployqt` does NOT bundle non-Qt dylibs — HDF5 (and its transitive `/opt/homebrew` deps like libsz/libaec/libz) MUST be bundled + `install_name_tool`-fixed by the script. Resolve the exact dylib names from `otool -L` at deploy time (versions vary).
- The self-containment GATE is the load-bearing verification: `otool -L` shows no `/opt/homebrew` on the bundled exe AND every bundled `Frameworks/*.dylib`, AND the bundled exe runs `--smoke` (offscreen) → exit 0. If the script can't reach a clean state, report the residual deps (do NOT claim self-contained when otool still shows /opt/homebrew).
- Use a Release build for the distributable bundle; confirm the offscreen ctest suite still passes after the MACOSX_BUNDLE change (it must not break the test build — the tests link `ads1292_gui_lib`, not the bundle, so they should be unaffected).
- Codesigning/notarization is OUT OF SCOPE — the unsigned .app/DMG will trigger Gatekeeper on other machines; document this as the next step.
- `Info.plist.in` is a TEMPLATE consumed by CMake's `MACOSX_BUNDLE_INFO_PLIST` (CMake substitutes the `${MACOSX_BUNDLE_*}` vars) — keep the placeholders exactly as CMake expects.
