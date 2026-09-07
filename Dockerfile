# ==============================================================================
# SAP-net Visualizer Dockerfile (GUI & Japanese Font Ready)
# ==============================================================================
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV SDL_AUDIODRIVER=dummy

# 1. 必要なGUI・フォント・共有ライブラリのインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-tk \
    tk-dev \
    fonts-takao-gothic \
    fonts-noto-cjk \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    libglib2.0-0 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 2. 作業ディレクトリの設定とPython依存関係のインストール
WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 3. アプリケーションコードと設定ファイルのコピー
COPY main.py /app/
COPY sap_visualizer /app/sap_visualizer
COPY packaging /app/packaging

# 4. 外部ログフォルダ用マウントポイント
RUN mkdir -p /logs

# 5. エントリーポイント（引数があればそのままmain.pyに渡す）
ENTRYPOINT ["python", "/app/main.py"]
CMD []
