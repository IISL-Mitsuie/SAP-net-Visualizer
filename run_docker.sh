#!/usr/bin/env bash
# ==============================================================================
# SAP-net Visualizer Docker GUI 起動ラッパースクリプト
# ==============================================================================
# 使い方:
#   1. 通常起動 (GUIフォルダ選択):
#      ./run_docker.sh
#
#   2. ログフォルダを指定して直接起動:
#      ./run_docker.sh /path/to/simulation_logs
# ==============================================================================

set -e

IMAGE_NAME="sap-net-visualizer:latest"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. Docker イメージが存在しない場合は自動ビルド
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "[INFO] Docker image '${IMAGE_NAME}' not found. Building now..."
    docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"
fi

# 2. DISPLAY 環境変数の検証と X11 アクセス許可
if [ -z "$DISPLAY" ]; then
    # WSL2 または デフォルトX11のフォールバック
    if grep -qi microsoft /proc/version 2>/dev/null; then
        export DISPLAY=:0
    else
        echo "[ERROR] DISPLAY environment variable is not set."
        echo "        Please ensure X11/Wayland or SSH X11 forwarding is active."
        exit 1
    fi
fi

# X11 接続許可 (ローカル接続のみ)
if command -v xhost >/dev/null 2>&1; then
    xhost +local:root >/dev/null 2>&1 || true
fi

# 3. 引数の処理（ログフォルダのマウント）
DOCKER_ARGS=(
    --rm
    -it
    --net=host
    -e DISPLAY="$DISPLAY"
    -v /tmp/.X11-unix:/tmp/.X11-unix:ro
    -v "$HOME/.sap_visualizer":/root/.sap_visualizer
)

TARGET_LOG_ARG=""
if [ -n "$1" ]; then
    HOST_LOG_PATH="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
    if [ -d "$HOST_LOG_PATH" ] || [ -f "$HOST_LOG_PATH" ]; then
        CONTAINER_LOG_PATH="/logs/$(basename "$HOST_LOG_PATH")"
        DOCKER_ARGS+=(-v "$HOST_LOG_PATH:$CONTAINER_LOG_PATH")
        TARGET_LOG_ARG="$CONTAINER_LOG_PATH"
        echo "[INFO] Mounted log path: $HOST_LOG_PATH -> $CONTAINER_LOG_PATH"
    else
        echo "[WARNING] Specified log path does not exist: $1"
        TARGET_LOG_ARG="$1"
    fi
fi

echo "[INFO] Launching SAP-net Visualizer inside Docker container..."
if [ -n "$TARGET_LOG_ARG" ]; then
    docker run "${DOCKER_ARGS[@]}" "$IMAGE_NAME" "$TARGET_LOG_ARG"
else
    docker run "${DOCKER_ARGS[@]}" "$IMAGE_NAME"
fi
