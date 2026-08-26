# SAP-net Visualizer

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![License](https://img.shields.io/badge/License-IISL-green.svg)]()

SAP-net（Spreading Activation Policy Network）の動的パラメータ（知識活性値・重み行列・選択プラン・閾値・ハイパーパラメータ等）を可視化・分析・再生するためのスタンドアロン型デスクトップGUIアプリケーションです。

強化学習シミュレーション等で出力された動的ログファイル（`.jsonl.gz` / `.jsonl`）を読み込み、アニメーション再生やグラフ描画によって学習・推論過程を詳細に精査できます。また、シミュレーションプログラムに組み込むことで、学習実行中のリアルタイムモニタリングも可能です。

---

## 主な特徴

- **超軽量＆高速起動**:
  - `numpy`, `pygame`, `pyyaml` の最小限の依存関係のみで動作し、ミリ秒単位で瞬時に起動します。
- **2つの可視化モード（ワンキー `G` で瞬時に切替）**:
  - **ステップ詳細表示モード**:
    - 各知識ノードの活性度に応じた動的な円サイズ・カラー（青〜赤）表示。
    - 知識間の結合重み（エッジ線の太さ・濃さ）をリアルタイム可視化。
    - 実行中プラン（金色二重枠）および転移候補知識（緑色二重枠）のハイライト表示。
    - 右側に各知識の活性値をリアルタイムバーチャートで表示（赤色閾値ライン付き）。
  - **活性値推移折れ線グラフモード**:
    - エピソードを通じた各知識ノードの活性度推移をマルチカラー（視認性の高い20色）の折れ線グラフで鳥瞰・精査。
    - 下部凡例のクリックによる各ノードの個別表示/非表示トグル、一括選択/解除ボタン（`[全表示]`, `[全解除]`）。
    - グラフ領域と凡例を白背景の高解像度画像（PNG）としてワンクリック（`S`キー）保存。
- **柔軟なタイムライン再生＆スマートジャンプ**:
  - コマ送り/コマ戻し、再生/一時停止、シークバーによる任意位置ジャンプ。
  - エピソード（`E`）、知識選択（`P`）、活性化拡散（`A`）、重み更新（`W`）の各イベントへのスマートジャンプ。
- **YAMLハイパーパラメータ連動 (`C`キー)**:
  - 実験設定ファイル（`config_used_*.yaml`）を自動解析し、モーダル画面上でパラメータ一覧を日本語解説付きで閲覧可能（マウスホイールスクロール対応）。
- **リアルタイム追従モード (`L`キー)**:
  - シミュレーション実行中に最新フレームへ自動追従（Live Follow）するモニタリング機能。
- **インストーラー配布対応 (Windows)**:
  - Inno Setup と連携し、管理者権限不要（一般ユーザー権限）でインストール可能な Windows セットアップウィザード（`.exe`）を生成可能。

---

## 2つの利用シナリオ

| シナリオ | 概要 | 主な用途 |
| :--- | :--- | :--- |
| **① オフライン解析（推奨）** | シミュレーション側で `.jsonl.gz` ログを出力し、本ビューアー（`main.py` またはインストーラー版）でじっくり再生・グラフ分析。 | 実験結果の精査、論文・スライド用グラフ作成、研究発表 |
| **② リアルタイムモニタリング** | シミュレーション実行と並行してビューアーを起動し、学習の進行状況や知識転移の挙動をリアルタイムに画面監視。 | アルゴリズムのデバッグ、シミュレーション動作確認 |

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

| 操作項目 | GUIボタン / マウス | キーボード | 機能説明 |
| :--- | :--- | :---: | :--- |
| **再生 / 一時停止** | `[再生/一時停止]` | `Space` | フレームの自動コマ送り再生と一時停止を切り替えます。 |
| **コマ送り** | `[コマ送り >>]` | `→` (右矢印) | 1フレーム進めます。 |
| **コマ戻し** | `[<< コマ戻し]` | `←` (左矢印) | 1フレーム戻します。 |
| **リアルタイム追従** | `[リアルタイム追従]` | `L` | 最新フレームへの自動追従（Live Follow）の有効/無効を切り替えます。 |
| **画面モード切替** | `[活性値推移(G)]` | `G` | ステップ詳細表示モードと折れ線グラフモードを切り替えます。 |
| **グラフ画像保存** | `[グラフ画像を保存]` | `S` | 折れ線グラフ画面を高解像度PNG画像として保存します。 |
| **次のエピソード** | `[エピソード >\|]` | `E` | 次のエピソード開始フレームへジャンプします。 |
| **前のエピソード** | `[\|< エピソード]` | `Shift + E` | 前のエピソード開始フレームへジャンプします。 |
| **次の知識選択** | `[知識選択 >\|]` | `P` | 次の知識選択イベント（`SELECT_PLAN`）へジャンプします。 |
| **前の知識選択** | `[\|< 知識選択]` | `Shift + P` | 直前の知識選択イベントへジャンプします。 |
| **次の活性化** | `[活性化 >\|]` | `A` | 次の初期活性化イベント（`ACTIVATION`）へジャンプします。 |
| **前の活性化** | `[\|< 活性化]` | `Shift + A` | 直前の初期活性化イベントへジャンプします。 |
| **次の重み更新** | `[重み更新 >\|]` | `W` | 次の重み更新イベント（`WEIGHT_UPDATE`）へジャンプします。 |
| **前の重み更新** | `[\|< 重み更新]` | `Shift + W` | 直前の重み更新イベントへジャンプします。 |
| **フォルダを開く** | `[実験ログフォルダを開く]` | `O` | フォルダ選択ダイアログを開き、別の実験ログを読み込みます。 |
| **設定確認** | `[設定確認]` | `C` | ハイパーパラメータ一覧オーバーレイを開閉します。 |
| **ヘルプ表示** | `[ヘルプ]` | `H` / `?` / `Esc` | 操作ガイドオーバーレイを開閉します。 |
| **最初に戻る** | `[リセット]` | - | フレームインデックス0（最初）に戻します。 |
| **シークバー** | スライダークリック / ドラッグ | - | 任意の再生位置へジャンプします。 |

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

---

## Windows インストーラー（Setup.exe）のビルド

Windows 環境において、専用のクリーンな一時仮想環境の作成から exe 化、Inno Setup によるインストーラー作成、中間生成物の自動削除までを一括で行う自動化スクリプトを用意しています。

### 前提条件
- [Inno Setup 6 (無料)](https://jrsoftware.org/isdl.php) がインストールされていること

### ビルドの実行
```powershell
.\build_all.bat
```

- **生成されるインストーラー**: `dist_installer/SAP_net_Visualizer_Setup_v1.0.1.exe`
- **インストール先**: ユーザーの `%LOCALAPPDATA%\Programs\SAP-net-Visualizer`（管理者権限不要）
- **詳細な手順**: [reference/SAP_VIEWER_PACKAGING_GUIDE.md](reference/SAP_VIEWER_PACKAGING_GUIDE.md) をご覧ください。

---

## ディレクトリ構成

```text
SAP-net-Visualizer/
├── build_all.bat                   # ワンクリック全自動クリーンビルドバッチ (cmd)
├── .gitignore                      # Git除外設定
├── README.md                       # 本ドキュメント (アプリケーション概要・操作方法)
├── sap_visualizer.md               # シミュレーションプログラム改変・導入ガイド
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
├── reference/                      # 各種技術リファレンス
│   ├── SAP_VIEWER_MIGRATION_GUIDE.md   # 独立リポジトリ移行・構成ガイド
│   └── SAP_VIEWER_PACKAGING_GUIDE.md   # アプリケーション化＆インストーラー作成ガイド
└── sap_visualizer/                 # コア可視化パッケージ
    ├── __init__.py
    ├── sap_visual_logger.py        # ログ解析・データ管理モジュール
    └── sap_visualizer_gui.py       # Pygame/Tkinter によるGUI描画エンジン
```

---

## ドキュメント一覧

- **[sap_visualizer.md](sap_visualizer.md)**: SAP-net を利用したシミュレーションプログラムへの可視化・ログ機能 導入・改変ガイド
- **[DATA_FORMAT.md](DATA_FORMAT.md)**: 動的ログデータ（JSONL）およびハイパーパラメータ設定（YAML）の詳細仕様書
- **[reference/SAP_VIEWER_MIGRATION_GUIDE.md](reference/SAP_VIEWER_MIGRATION_GUIDE.md)**: 独立リポジトリ移行とアーキテクチャの解説リファレンス
- **[reference/SAP_VIEWER_PACKAGING_GUIDE.md](reference/SAP_VIEWER_PACKAGING_GUIDE.md)**: Windows インストーラー作成とパッケージングの完全手順書

---

## 著作権・ライセンス

Copyright (C) 2026 Mitsuie. All rights reserved.
