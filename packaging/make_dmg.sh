#!/bin/bash
# make_dmg.sh — Create a distributable DMG from a deployed .app bundle.
#
# Usage: ./packaging/make_dmg.sh [path/to/ads1292_gui.app] [output.dmg]
#
# Defaults:
#   APP = build/gui/ads1292_gui.app
#   DMG = build/ADS1292-Studio.dmg
#
# Prerequisites:
#   - The .app must already be deployed (run packaging/deploy_macos.sh first).
#   - hdiutil must be available (standard on macOS).
#
# The DMG is a build artifact — it is gitignored and NOT committed.

set -euo pipefail

APP="${1:-build/gui/ads1292_gui.app}"
DMG="${2:-build/ADS1292-Studio.dmg}"

echo "==> make_dmg.sh"
echo "    APP: $APP"
echo "    DMG: $DMG"
echo ""

# Guard: the .app must exist (produced by deploy_macos.sh).
if [ ! -d "$APP" ]; then
    echo "ERROR: no .app at $APP — run deploy_macos.sh first"
    exit 1
fi

# ---------------------------------------------------------------------------
# Stage a temp directory containing the .app and an Applications symlink so
# the DMG presents the standard drag-to-install UI.
# ---------------------------------------------------------------------------
STAGE="$(mktemp -d)"
echo "==> Staging DMG contents in $STAGE ..."
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
echo "    $(ls "$STAGE")"
echo ""

# ---------------------------------------------------------------------------
# Create the compressed DMG.
# ---------------------------------------------------------------------------
rm -f "$DMG"
echo "==> Creating DMG (UDZO / zlib compressed)..."
hdiutil create \
    -volname "ADS1292 Studio" \
    -srcfolder "$STAGE" \
    -ov \
    -format UDZO \
    "$DMG"
echo ""

# Clean up the staging dir.
rm -rf "$STAGE"

# ---------------------------------------------------------------------------
# Verify: the file must exist and be non-empty.
# ---------------------------------------------------------------------------
if ! test -f "$DMG"; then
    echo "ERROR: DMG not created at $DMG"
    exit 1
fi
echo "==> DMG created:"
ls -lh "$DMG"
echo ""

# ---------------------------------------------------------------------------
# Attach the DMG read-only and confirm the .app + Applications symlink are
# present inside, then detach.
# ---------------------------------------------------------------------------
echo "==> Verifying DMG contents (attach read-only)..."
ATTACH_OUT="$(hdiutil attach "$DMG" -nobrowse -readonly)"
echo "$ATTACH_OUT"
# hdiutil output columns are tab-separated; use -F'\t' so that a volume
# name with spaces (e.g. "ADS1292 Studio") is captured as one field.
MNT="$(echo "$ATTACH_OUT" | grep '/Volumes/' | awk -F'\t' '{print $NF}')"
echo ""
echo "    Mounted at: $MNT"
echo "    Contents:"
ls "$MNT"
echo ""

# Confirm the .app is present inside the DMG.
APP_BASE="$(basename "$APP")"
if [ ! -d "$MNT/$APP_BASE" ]; then
    echo "ERROR: $APP_BASE not found inside DMG at $MNT"
    hdiutil detach "$MNT" -quiet || true
    exit 1
fi

hdiutil detach "$MNT" -quiet
echo "==> DMG: PASS"
