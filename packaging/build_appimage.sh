#!/usr/bin/env bash
# ==============================================================================
# SAP-net Visualizer AppImage 生成スクリプト (Linux 向け単一実行可能ファイル)
# ==============================================================================
# 前提:
#   1. packaging/build_linux.py で dist/SAP-net-Visualizer-linux が生成済みであること
#      (未生成の場合は自動で build_linux.py を実行します)
#   2. wget または curl, file 等の標準ツールが利用可能であること
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

echo "============================================================"
echo "  SAP-net Visualizer AppImage Packaging Script"
echo "============================================================"

# 1. バージョン番号の取得
APP_VERSION="1.1.0"
if [ -f "sap_visualizer/__init__.py" ]; then
    EXTRACTED_VER=$(grep -E '__version__\s*=' sap_visualizer/__init__.py | sed -E 's/.*["'"'"']([^"'"'"']+)["'"'"'].*/\1/')
    if [ -n "$EXTRACTED_VER" ]; then
        APP_VERSION="$EXTRACTED_VER"
    fi
fi
echo "[INFO] Target Version: v${APP_VERSION}"

# 2. PyInstaller ビルド成果物の確認
DIST_DIR="$ROOT_DIR/dist"
LINUX_STANDALONE="$DIST_DIR/SAP-net-Visualizer-linux"

if [ ! -d "$LINUX_STANDALONE" ] || [ ! -f "$LINUX_STANDALONE/SAP-net-Visualizer" ]; then
    echo "[INFO] Standalone binary not found. Running packaging/build_linux.py..."
    python3 "$SCRIPT_DIR/build_linux.py"
fi

# 3. AppDir 構造の構築
APPDIR="$DIST_DIR/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

echo "[INFO] Copying application files to AppDir..."
cp -r "$LINUX_STANDALONE/"* "$APPDIR/usr/bin/"

# アイコンのコピー (ico または png)
if [ -f "$SCRIPT_DIR/app_icon.ico" ]; then
    cp "$SCRIPT_DIR/app_icon.ico" "$APPDIR/app_icon.ico"
    cp "$SCRIPT_DIR/app_icon.ico" "$APPDIR/.DirIcon"
fi

# .desktop ファイルの作成
cat << 'EOF' > "$APPDIR/SAP-net-Visualizer.desktop"
[Desktop Entry]
Type=Application
Name=SAP-net Visualizer
GenericName=SAP-net Simulation Visualizer
Comment=Interactive dynamic parameter visualizer for SAP-net reinforcement learning
Exec=SAP-net-Visualizer
Icon=app_icon
Terminal=false
Categories=Science;Education;Development;
EOF

# AppRun スクリプトの作成
cat << 'EOF' > "$APPDIR/AppRun"
#!/usr/bin/env bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/bin:${LD_LIBRARY_PATH}"

# 音声デバイス未検出環境（WSL/サーバー等）での警告抑制
if [ -z "$SDL_AUDIODRIVER" ]; then
    export SDL_AUDIODRIVER=dummy
fi

exec "${HERE}/usr/bin/SAP-net-Visualizer" "$@"
EOF

chmod +x "$APPDIR/AppRun"
chmod +x "$APPDIR/usr/bin/SAP-net-Visualizer"

# 4. appimagetool の準備
ARCH=$(uname -m)
APPIMAGETOOL="$DIST_DIR/appimagetool-${ARCH}.AppImage"

if [ ! -f "$APPIMAGETOOL" ]; then
    echo "[INFO] Downloading appimagetool for ${ARCH}..."
    DOWNLOAD_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage"
    if command -v curl >/dev/null 2>&1; then
        curl -L -o "$APPIMAGETOOL" "$DOWNLOAD_URL"
    elif command -v wget >/dev/null 2>&1; then
        wget -O "$APPIMAGETOOL" "$DOWNLOAD_URL"
    else
        echo "[ERROR] Neither curl nor wget found. Please install curl or wget."
        exit 1
    fi
    chmod +x "$APPIMAGETOOL"
fi

# 5. AppImage の生成
OUTPUT_APPIMAGE="$DIST_DIR/SAP-net-Visualizer-${APP_VERSION}-${ARCH}.AppImage"
echo "[INFO] Building AppImage: ${OUTPUT_APPIMAGE}..."

# WSL2やコンテナ内での FUSE 非対応環境向けに --appimage-extract-and-run を付与
ARCH=${ARCH} "$APPIMAGETOOL" --appimage-extract-and-run "$APPDIR" "$OUTPUT_APPIMAGE"

chmod +x "$OUTPUT_APPIMAGE"
rm -rf "$APPDIR"

echo "============================================================"
echo "  APPIMAGE BUILD SUCCESSFUL!"
echo "  Location: ${OUTPUT_APPIMAGE}"
echo "  Usage   : chmod +x ${OUTPUT_APPIMAGE} && ./${OUTPUT_APPIMAGE} [log_dir]"
echo "============================================================"
