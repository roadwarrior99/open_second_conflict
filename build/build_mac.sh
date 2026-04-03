#!/usr/bin/env bash
# ============================================================
# build_mac.sh — Build the Second Conflict macOS .dmg installer
#
# Requirements:
#   - Python 3.11+  (with pip)
#   - PyInstaller   (installed automatically if missing)
#   - Xcode Command Line Tools (for hdiutil, codesign)
#   - Optional: create-dmg  (brew install create-dmg)
#             for a styled DMG with a background image
#
# Run from the project root:
#   bash build/build_mac.sh
# ============================================================

set -euo pipefail

APP_NAME="Second Conflict"
APP_BUNDLE="dist/${APP_NAME}.app"
DMG_NAME="SecondConflict-macOS"
DMG_OUT="dist/${DMG_NAME}.dmg"

cd "$(dirname "$0")/.."

echo ""
echo "===================================================="
echo "  ${APP_NAME} — macOS Build"
echo "===================================================="
echo ""

# ----------------------------------------------------------
# 1. Ensure PyInstaller is installed
# ----------------------------------------------------------
if ! python3 -m PyInstaller --version &>/dev/null; then
    echo "[INFO] PyInstaller not found. Installing..."
    python3 -m pip install pyinstaller
fi

# ----------------------------------------------------------
# 2. Clean previous build artefacts
# ----------------------------------------------------------
echo "[INFO] Cleaning previous build output..."
rm -rf "dist/${APP_NAME}" "dist/${APP_NAME}.app" "${DMG_OUT}"
rm -rf "build/pyinstaller_work"

# ----------------------------------------------------------
# 3. Run PyInstaller
# ----------------------------------------------------------
echo "[INFO] Running PyInstaller..."
python3 -m PyInstaller build/second_conflict.spec \
    --distpath dist \
    --workpath build/pyinstaller_work \
    --noconfirm

if [ ! -d "${APP_BUNDLE}" ]; then
    echo "[ERROR] PyInstaller did not produce ${APP_BUNDLE}"
    exit 1
fi
echo "[OK] .app bundle created at ${APP_BUNDLE}"

# ----------------------------------------------------------
# 4. Ad-hoc code sign (required for macOS Gatekeeper)
#    Replace '-' with your Developer ID if you have one:
#    codesign --deep --force --sign "Developer ID Application: ..."
# ----------------------------------------------------------
echo "[INFO] Code-signing (ad-hoc)..."
codesign --deep --force --sign - "${APP_BUNDLE}" || \
    echo "[WARN] codesign failed — app may show a Gatekeeper warning on first launch"

# ----------------------------------------------------------
# 5. Build the DMG
# ----------------------------------------------------------

# Prefer create-dmg if available (produces a nicer installer DMG)
if command -v create-dmg &>/dev/null; then
    echo "[INFO] Building DMG with create-dmg..."
    create-dmg \
        --volname "${APP_NAME}" \
        --volicon "build/icon.icns" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 128 \
        --icon "${APP_NAME}.app" 150 185 \
        --hide-extension "${APP_NAME}.app" \
        --app-drop-link 450 185 \
        "${DMG_OUT}" \
        "dist/" || true   # create-dmg exits non-zero when no background; that's ok
else
    # Fallback: plain DMG via hdiutil (ships with macOS)
    echo "[INFO] create-dmg not found — building plain DMG with hdiutil..."
    STAGING="dist/dmg_staging"
    rm -rf "${STAGING}"
    mkdir "${STAGING}"
    cp -R "${APP_BUNDLE}" "${STAGING}/"
    # Symlink /Applications for drag-install UX
    ln -s /Applications "${STAGING}/Applications"

    hdiutil create \
        -volname "${APP_NAME}" \
        -srcfolder "${STAGING}" \
        -ov \
        -format UDZO \
        "${DMG_OUT}"

    rm -rf "${STAGING}"
fi

echo ""
echo "[OK] DMG created at ${DMG_OUT}"
echo ""
echo "To install create-dmg for a styled installer:"
echo "  brew install create-dmg"
echo ""
echo "To distribute without a paid Developer ID, users must right-click"
echo "→ Open the first time to bypass Gatekeeper."