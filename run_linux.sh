#!/usr/bin/env bash
# ==============================================================================
# SAP-net Visualizer Linux 統合ランチャースクリプト
# ==============================================================================
# 使い方:
#   ./run_linux.sh [/path/to/simulation_logs]
#
# 動作フロー:
#   1. ビルド済みスタンドアロンバイナリ (dist/) が存在すれば直接起動 (最速・環境依存ゼロ)
#   2. AppImage が存在すれば直接起動
#   3. Python 仮想環境 (.venv / venv) が存在すれば起動
#   4. システムの python3 環境を検知して起動 (必要パッケージの有無を親切にチェック)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 音声デバイス未検出環境（WSL/サーバー等）での警告抑制
if [ -z "$SDL_AUDIODRIVER" ]; then
    export SDL_AUDIODRIVER=dummy
fi

# 1. スタンドアロンバイナリの探索
STANDALONE_BIN="$SCRIPT_DIR/dist/SAP-net-Visualizer-linux/SAP-net-Visualizer"
if [ -x "$STANDALONE_BIN" ]; then
    echo "[INFO] Running standalone Linux binary: $STANDALONE_BIN"
    exec "$STANDALONE_BIN" "$@"
fi

# 2. AppImage の探索
APPIMAGE_BIN=$(ls "$SCRIPT_DIR/dist"/SAP-net-Visualizer-*.AppImage 2>/dev/null | head -n 1)
if [ -n "$APPIMAGE_BIN" ] && [ -x "$APPIMAGE_BIN" ]; then
    echo "[INFO] Running portable AppImage: $APPIMAGE_BIN"
    exec "$APPIMAGE_BIN" "$@"
fi

# 3. Python 仮想環境の探索
for VENV_CANDIDATE in "$SCRIPT_DIR/.venv" "$SCRIPT_DIR/venv"; do
    if [ -f "$VENV_CANDIDATE/bin/python3" ]; then
        echo "[INFO] Running with virtual environment: $VENV_CANDIDATE"
        exec "$VENV_CANDIDATE/bin/python3" "$SCRIPT_DIR/main.py" "$@"
    fi
done

# 4. システム Python での起動チェック
if command -v python3 >/dev/null 2>&1; then
    # Tkinter および 依存パッケージの簡易チェック
    if ! python3 -c "import tkinter" >/dev/null 2>&1; then
        echo "[WARNING] Tkinter is not installed on your system."
        echo "          To enable GUI folder selector, please run:"
        echo "          sudo apt install python3-tk  (Debian/Ubuntu)"
        echo "          sudo dnf install python3-tkinter (Fedora/RHEL)"
        echo ""
    fi
    echo "[INFO] Running with system Python3..."
    exec python3 "$SCRIPT_DIR/main.py" "$@"
fi

echo "[ERROR] No standalone binary, AppImage, virtual environment, or Python3 found."
echo "        Please build the standalone binary using: python3 packaging/build_linux.py"
echo "        Or run using Docker: ./run_docker.sh"
exit 1
