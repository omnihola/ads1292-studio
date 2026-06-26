#!/usr/bin/env bash
# deploy_macos.sh — Bundle Qt frameworks + HDF5 transitive deps into the .app,
# rewrite install names with install_name_tool, and verify self-containment.
#
# Usage: ./packaging/deploy_macos.sh [path/to/ads1292_gui.app]
# Default app path: build/gui/ads1292_gui.app
#
# Requires: macdeployqt (at /opt/homebrew/opt/qt/bin/macdeployqt), otool,
#           install_name_tool (all bundled with Xcode Command Line Tools).

set -euo pipefail

APP="${1:-build/gui/ads1292_gui.app}"
EXE="$APP/Contents/MacOS/ads1292_gui"
FRAMEWORKS="$APP/Contents/Frameworks"

echo "==> deploy_macos.sh"
echo "    APP: $APP"
echo "    EXE: $EXE"
echo ""

if [[ ! -f "$EXE" ]]; then
    echo "ERROR: Bundle executable not found: $EXE"
    echo "       Build the project first with MACOSX_BUNDLE enabled."
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 1: macdeployqt — bundles Qt frameworks, plugins, and resources.
# This handles QtCore, QtGui, QtWidgets, QtPrintSupport, QtSerialPort, etc.
# It does NOT handle non-Qt dylibs (e.g. HDF5).
# ---------------------------------------------------------------------------
echo "==> Step 1: Running macdeployqt..."
/opt/homebrew/opt/qt/bin/macdeployqt "$APP" -verbose=1
echo ""

# ---------------------------------------------------------------------------
# Step 1b: Bundle the offscreen platform plugin for headless smoke testing.
# macdeployqt only includes the cocoa plugin (the native macOS platform
# plugin).  We add the offscreen plugin so the smoke test can run without
# a display.  The plugin uses @rpath refs that macdeployqt normally rewrites
# to @executable_path/../Frameworks; we do the same here.
#
# Source: derive the plugin path from macdeployqt's own Qt prefix so we
# always use the exact same Qt version that was used to build the app.
# ---------------------------------------------------------------------------
echo "==> Step 1b: Adding offscreen platform plugin (for smoke test)..."
MACDEPLOYQT="/opt/homebrew/opt/qt/bin/macdeployqt"
QT_PREFIX="$(dirname "$(dirname "$MACDEPLOYQT")")"   # /opt/homebrew/opt/qt
OFFSCREEN_SRC="$QT_PREFIX/share/qt/plugins/platforms/libqoffscreen.dylib"

if [[ -f "$OFFSCREEN_SRC" ]]; then
    PLATFORMS_DIR="$APP/Contents/PlugIns/platforms"
    mkdir -p "$PLATFORMS_DIR"
    cp "$OFFSCREEN_SRC" "$PLATFORMS_DIR/libqoffscreen.dylib"
    chmod +w "$PLATFORMS_DIR/libqoffscreen.dylib"
    # Rewrite @rpath/Qt*.framework refs to @executable_path/../Frameworks
    # (identical to how macdeployqt handles the other platform plugins).
    while IFS= read -r rpath_dep; do
        [[ -z "$rpath_dep" ]] && continue
        framework_part="${rpath_dep#@rpath/}"
        fixed="@executable_path/../Frameworks/$framework_part"
        install_name_tool -change "$rpath_dep" "$fixed" \
            "$PLATFORMS_DIR/libqoffscreen.dylib" 2>/dev/null || true
        echo "  [rpath-fix] $rpath_dep"
    done < <(otool -L "$PLATFORMS_DIR/libqoffscreen.dylib" | grep '@rpath' | awk '{print $1}')
    echo "  Offscreen plugin bundled from: $OFFSCREEN_SRC"
else
    echo "  WARNING: libqoffscreen.dylib not found at $OFFSCREEN_SRC — smoke test may fail."
fi
echo ""

# ---------------------------------------------------------------------------
# Step 2: Fixed-point loop — bundle all remaining /opt/homebrew dylibs and
# rewrite their install names.  macdeployqt handles Qt frameworks but may
# leave non-Qt libs (HDF5, brotli, etc.) with /opt/homebrew paths.  There
# are two distinct cases to handle:
#
#   (A) LC_LOAD_DYLIB — a binary references another lib via /opt/homebrew.
#       Fix: copy the lib to Frameworks/ (if missing), then
#            install_name_tool -change OLD NEW BINARY
#
#   (B) LC_ID_DYLIB — a dylib's own install name is still /opt/homebrew.
#       This happens when macdeployqt copies a lib but forgets to rewrite
#       its id (observed with libbrotlicommon.1.dylib).
#       Fix: install_name_tool -id NEW DYLIB
#       Detection: basename(dep) == basename(binary) → it is the own id.
#
# Iterate until no /opt/homebrew path appears in any bundled binary.
# ---------------------------------------------------------------------------
echo "==> Step 2: Bundling Homebrew dependencies (HDF5 + transitive)..."
mkdir -p "$FRAMEWORKS"

MAX_PASSES=10
for pass in $(seq 1 $MAX_PASSES); do
    echo ""
    echo "  --- Pass $pass ---"

    # Rebuild the binary list each pass to include newly copied dylibs.
    binaries=("$EXE")
    while IFS= read -r -d '' f; do
        binaries+=("$f")
    done < <(find "$FRAMEWORKS" -maxdepth 1 -name "*.dylib" -print0 2>/dev/null)

    found_any=0
    for binary in "${binaries[@]}"; do
        # Ensure the binary is writable before install_name_tool calls.
        chmod +w "$binary" 2>/dev/null || true
        bin_base=$(basename "$binary")

        while IFS= read -r dep; do
            [[ -z "$dep" ]] && continue
            found_any=1
            base=$(basename "$dep")
            dest="$FRAMEWORKS/$base"

            # Ensure the dep is present in Frameworks/.
            if [[ ! -f "$dest" ]]; then
                echo "    [copy] $dep"
                cp "$dep" "$dest"
                chmod +w "$dest"
            fi

            if [[ "$base" == "$bin_base" ]]; then
                # Case (B): the /opt/homebrew path is this library's own
                # LC_ID_DYLIB.  Rewrite the id with -id, not -change.
                echo "    [id  ] $bin_base: $dep -> @executable_path/../Frameworks/$base"
                install_name_tool -id "@executable_path/../Frameworks/$base" \
                    "$binary" 2>/dev/null || true
            else
                # Case (A): normal load command — rewrite with -change.
                echo "    [fix ] $bin_base: $dep -> @executable_path/../Frameworks/$base"
                install_name_tool -change "$dep" \
                    "@executable_path/../Frameworks/$base" "$binary" 2>/dev/null || true
            fi
        done < <(otool -L "$binary" | grep '/opt/homebrew' | awk '{print $1}')
    done

    if [[ $found_any -eq 0 ]]; then
        echo ""
        echo "  Fixed-point reached after $pass pass(es) — no Homebrew refs remain."
        break
    fi

    if [[ $pass -eq $MAX_PASSES ]]; then
        echo ""
        echo "ERROR: Could not eliminate all /opt/homebrew references after $MAX_PASSES passes."
        echo "       Residual deps in bundled binaries:"
        for binary in "${binaries[@]}"; do
            if otool -L "$binary" | grep -q '/opt/homebrew'; then
                echo "  -> $(basename "$binary"):"
                otool -L "$binary" | grep '/opt/homebrew'
            fi
        done
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Step 3: Self-containment GATE.
# The script fails (exit 1) if any bundled binary still references
# /opt/homebrew. Every dynamic dep must be @rpath, @executable_path,
# @loader_path, or a system /usr/lib / /System path.
# ---------------------------------------------------------------------------
echo ""
echo "==> Step 3: Self-containment check..."
FAIL=0

if otool -L "$EXE" | grep -q '/opt/homebrew'; then
    echo "FAIL: Residual /opt/homebrew dep in executable:"
    otool -L "$EXE" | grep '/opt/homebrew'
    FAIL=1
fi

for dylib in "$FRAMEWORKS"/*.dylib; do
    [[ -f "$dylib" ]] || continue
    if otool -L "$dylib" | grep -q '/opt/homebrew'; then
        echo "FAIL: Residual /opt/homebrew dep in $(basename "$dylib"):"
        otool -L "$dylib" | grep '/opt/homebrew'
        FAIL=1
    fi
done

if [[ $FAIL -ne 0 ]]; then
    echo ""
    echo "Self-containment: FAIL"
    exit 1
fi

echo "Self-containment: PASS (no /opt/homebrew references in any bundled binary)"

# ---------------------------------------------------------------------------
# Step 4: Smoke test — launch the bundled executable with --smoke flag.
# --smoke constructs the MainWindow, runs a simulator cycle, and quits 0.
# Runs offscreen (no display required).
# ---------------------------------------------------------------------------
echo ""
echo "==> Step 4: Smoke test (offscreen)..."
QT_QPA_PLATFORM=offscreen "$EXE" --smoke
smoke_exit=$?
if [[ $smoke_exit -ne 0 ]]; then
    echo "FAIL: smoke test exited $smoke_exit"
    exit 1
fi

echo ""
echo "==> self-contained: PASS, smoke exit=0"
