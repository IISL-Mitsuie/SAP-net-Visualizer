# SAP-net Visualizer

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![License](https://img.shields.io/badge/License-IISL-green.svg)]()

SAP-net（Spreading Activation Policy Network）の動的パラメータ（知識活性値・重み行列・選択プラン・閾値・ハイパーパラメータ等）を可視化・分析・再生するためのスタンドアロン型デスクトップGUIアプリケーションです。

強化学習シミュレーション等で出力された動的ログファイル（`.jsonl.gz` / `.jsonl`）を読み込み、アニメーション再生やグラフ描画によって学習・推論過程を詳細に精査できます。

---

## 主な特徴

- **超軽量＆高速起動**:
  - `numpy`, `pygame`, `pyyaml` の最小限の依存関係のみで動作し、ミリ秒単位で瞬時に起動します。
- **2つの可視化モード**:
  - **ステップ表示モード**: 各タイムステップにおける知識ノードの活性度、重みネットワーク、選択プラン、活性化閾値をグラフィカルに表示。
  - **活性値推移グラフモード**: エピソードを通じた各知識ノードの活性度推移をマルチカラーの折れ線グラフで鳥瞰・精査。
- **柔軟なタイムライン再生**:
  - コマ送り/戻し、再生/一時停止、エピソード・知識選択・活性化・重み更新イベントへのスマートジャンプ。
- **YAMLハイパーパラメータ連動**:
  - 実験時の設定ファイル（`config_used_*.yaml`）を自動解析し、GUI上でパラメータ一覧を日本語解説付きで確認可能。
- **高精細グラフエクスポート**:
  - 活性値グラフをワンキー（`S`キー）で高解像度画像（PNG）として保存可能。
- **インストーラー配布対応 (Windows)**:
  - Inno Setup と連携し、管理者権限不要（一般ユーザー権限）でインストール可能な Windows セットアップウィザード（`.exe`）を生成可能。

---

## 必要要件

- **OS**: Windows / macOS / Linux
- **Python**: 3.8 以上（Windowsインストーラー作成時は 3.10 以上）
- **必須ライブラリ**:
  - `numpy >= 1.21.0`
  - `pygame >= 2.1.0`
  - `pyyaml >= 6.0`
  - `pyinstaller >= 6.0.0` (インストーラー作成時のみ)

---

## クイックスタート

### 1. リポジトリのクローンと依存パッケージのインストール

```bash
git clone https://github.com/IISL-Mitsuie/SAP-net-Visualizer.git
cd SAP-net-Visualizer
pip install -r requirements.txt
```

### 2. アプリケーションの起動

#### 方法 A: 実験ログフォルダ選択ダイアログから起動
```bash
python main.py
```
起動時に自動的にフォルダ選択ダイアログが表示されます。実験ログ（`sap_dynamic_log_*.jsonl.gz`）が保存されているフォルダを選択してください。

#### 方法 B: ログファイル / フォルダを引数に指定して起動
```bash
# 実験ログフォルダを指定して起動
python main.py "path/to/experiment_log_folder"

# ログファイルを直接指定して起動 (.jsonl.gz または .jsonl)
python main.py "path/to/experiment_log_folder/sap_dynamic_log_20260801_120000.jsonl.gz"
```

---

## 操作方法・キーボードショートカット

| キー / 操作 | 動作内容 |
| :--- | :--- |
| **Space** | 再生 / 一時停止 |
| **← / →** | 1ステップ コマ戻し / コマ送り |
| **E / Shift + E** | 次 / 前 のエピソードへジャンプ |
| **P / Shift + P** | 次 / 前 の知識選択（Plan Selection）イベントへジャンプ |
| **A / Shift + A** | 次 / 前 の活性化（Activation）イベントへジャンプ |
| **W / Shift + W** | 次 / 前 の重み更新（Weight Update）イベントへジャンプ |
| **G** | 画面表示モード切替（ステップ表示 ⇄ 活性値推移折れ線グラフ） |
| **S** | 折れ線グラフ画面で高精細グラフ画像を保存（`capture_*.png`） |
| **O** | 実験ログフォルダ選択ダイアログを開く |
| **C** | ハイパーパラメータ設定一覧の表示 / 非表示 |
| **L** | リアルタイム追従モードの切り替え |
| **H** | 画面の見方・ヘルプの表示 / 非表示 |
| **Esc** | 各種オーバーレイ画面（ヘルプ・設定一覧）を閉じる |
| **マウス操作** | タイムラインスライダーのドラッグ / 各種コントロールボタンのクリック |

---

## 対応ログフォーマット仕様

本ビューアーは、以下の構造を持つ gzip 圧縮 JSON Lines（`.jsonl.gz`）または通常の JSON Lines（`.jsonl`）形式のログを読み込みます。
詳細な仕様や最小構成・推奨構成の比較については **[DATA_FORMAT.md](DATA_FORMAT.md)** をご覧ください。

### 1フレームのデータ構造例
```json
{
  "index": 0,
  "episode": 1,
  "step": 1,
  "event_type": "STEP",
  "A": [0.12, 0.45, 0.89, 0.05],
  "weight": [[0.0, 0.25], [0.25, 0.0]],
  "plan": 2,
  "selectplans": [2],
  "policyvalue": [0.85],
  "reused_action": null,
  "threshold": 0.18
}
```

### シミュレーション側でのログ出力コード例
シミュレーション本体や学習スクリプト側では、`sap_visualizer` パッケージを用いて以下のように簡単にログを出力できます。

```python
from sap_visualizer import SAPVisualLogger

# ロガーの初期化
logger = SAPVisualLogger(log_dir="output_folder", timestamp="20260801_120000", enabled=True)

# 各ステップやイベント発生時にフレームを記録（メモリ上に蓄積）
logger.record_frame(
    episode=ep,
    step=step_count,
    event_type="STEP",
    A=activations,
    weight=weight_matrix,
    plan=chosen_plan,
    threshold=threshold_value
)

# シミュレーション終了時またはエピソード終了時に一括保存
logger.save_to_file()
```

---

## Windows インストーラー（Setup.exe）のビルド

Windows 環境において、専用のクリーンな一時仮想環境の作成から exe 化、Inno Setup によるインストーラー作成、中間生成物の自動削除までを一括で行う自動化スクリプトを用意しています。

### 前提条件
- [Inno Setup 6 (無料)](https://jrsoftware.org/isdl.php) がインストールされていること

### ビルドの実行
```powershell
# 方法 1: バッチファイル（ダブルクリックでも実行可能）
.\build_all.bat

# 方法 2: PowerShell スクリプト
.\build_all.ps1
```

- **生成されるインストーラー**: `dist_installer/SAP_net_Visualizer_Setup_v1.0.0.exe`
- **インストール先**: ユーザーの `%LOCALAPPDATA%\Programs\SAP-net-Visualizer`（管理者権限不要）

---

## ディレクトリ構成

```text
SAP-net-Visualizer/
├── build_all.bat                   # ワンクリック全自動クリーンビルドバッチ (cmd)
├── build_all.ps1                   # ワンクリック全自動クリーンビルドスクリプト (PowerShell)
├── .gitignore                      # Git除外設定
├── README.md                       # 本ドキュメント
├── DATA_FORMAT.md                  # データフォーマット仕様書 (最小構成/推奨構成)
├── requirements.txt                # 最小限の依存関係
├── main.py                         # アプリケーションエントリーポイント
├── image_icon.png                  # アプリアイコン元画像
├── packaging/                      # 配布・パッケージング設定
│   ├── app_icon.ico                # マルチサイズアイコン (16〜256px)
│   ├── build.py                    # クロスプラットフォーム全自動ビルドエンジン
│   ├── version_info.txt            # Windows実行ファイル用メタデータ
│   ├── SAP-net-Visualizer.spec     # PyInstaller 設定
│   └── installer.iss               # Inno Setup 定義スクリプト
└── sap_visualizer/                 # コア可視化パッケージ
    ├── __init__.py
    ├── sap_visual_logger.py        # ログ解析・データ管理モジュール
    └── sap_visualizer_gui.py       # Pygame/Tkinter によるGUI描画エンジン
```

---

## 著作権・ライセンス

Copyright (C) 2026 Mitsuie. All rights reserved.
