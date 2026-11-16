# SAP-net Visualizer

[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![License](https://img.shields.io/badge/License-IISL-green.svg)]()

SAP-net（Spreading Activation Policy Network）の動的パラメータ（知識活性値・重み行列・選択プラン・閾値・ハイパーパラメータ等）を可視化・分析・再生するためのスタンドアロン型デスクトップ GUI アプリケーションです。

強化学習シミュレーション等で出力された動的ログファイル（`.jsonl.gz` / `.jsonl`）を読み込み、アニメーション再生やグラフ描画によって学習・推論過程を詳細に精査できます。また、シミュレーションプログラムと並行起動することで、学習実行中のリアルタイムモニタリングも可能です。

---

## 主な特徴

- **超軽量＆高速起動**:
  - `numpy`, `pygame`, `pyyaml` の最小限の実行時依存関係のみで動作し、軽快に起動・描画します。
- **シミュレーションフォルダ選択 GUI＆履歴参照機能**:
  - 起動時または実行中（`O` キー / `[実験ログフォルダ選択 (O)...]`）に専用の GUI ウィンドウが開き、ファイルダイアログからの新規フォルダ選択に加え、過去に選択した実験ログフォルダの履歴一覧（最終アクセス日時・存在ステータス付き）からワンクリックで読み込み可能。
  - 履歴の個別削除や全クリア、直接パス入力・コピペにも対応しています。履歴ファイルは `~/.sap_visualizer/folder_history.json`（環境変数 `SAP_VISUALIZER_CONFIG_DIR` で上書き可）に保存されます。
- **2つの可視化モード（ワンキー `G` またはヘッダーボタンで瞬時に切替）**:
  - **ステップ詳細表示モード**:
    - 各知識ノードの活性度に応じた動的な円サイズ・カラー（青〜赤）表示。
    - 知識間の結合重み（強度に応じた線の太さ・青色カラー強調、エッジ中央の数値ラベルバッジ表示、交差時の自動オフセット）をリアルタイム可視化。
    - 実行中プラン（金色二重枠）および転移候補知識（緑色二重枠）のハイライト表示。
    - 右側に各知識の活性値をリアルタイムバーチャートで表示（赤色閾値ライン付き）。
  - **活性値推移折れ線グラフモード**:
    - エピソードを通じた各知識ノードの活性度推移をマルチカラー（視認性の高い20色）の折れ線グラフで鳥瞰・精査。
    - **選択知識の直感的提示**: 現在選択中（垂直カーソル位置）の知識を折れ線上の金色二重サークル＆活性値バッジ（`知識N: 0.XX`）、上部情報バッジ、および右側凡例パネルのハイライト（`★選択`）で多角的に強調表示。
    - **大規模ログ（十万ステップ超）対応の超高速描画**: 画面解像度に応じた動的ダウンサンプリング（LOD）を導入し、長大シミュレーションログでも 60FPS 相当の軽快な描画レスポンスを実現。
    - 右側パネルのクリックによる各知識の個別表示/非表示トグル、一括選択/解除ボタン（`[全選択]`, `[全解除]`）。
    - グラフ領域と凡例を白背景の高解像度画像（PNG）としてワンクリック（`S` キー / `[グラフ保存 (S)]`）保存。
- **柔軟なタイムライン再生＆スマートジャンプ**:
  - コマ送り/コマ戻し、再生/一時停止、シークバーによる任意位置ジャンプ。
  - エピソード（`E`）、知識選択（`P`）、活性化拡散（`A`）、重み更新（`W`）の各イベントへのスマートジャンプ（`Shift` 併用で逆方向ジャンプ）。
- **YAML ハイパーパラメータ連動 (`C` キー / `[ハイパーパラメータ]`)**:
  - 実験ログフォルダ内の `config_used_*.yaml` を汎用動的パーサーで自動解析・平坦化し、セクション見出し付きの 2 カラム一覧表（キー・構造 / 型別色分けされた設定値）としてモーダル画面に表示（マウスホイール／上下キーでのスクロールおよびパス単位キャッシュ対応）。
- **リアルタイム追従モード (`L` キー / `[リアルタイム追従]`)**:
  - シミュレーション実行中に最新フレームへ自動追従（Live Follow）するモニタリング機能。
- **自動更新チェック＆安全性検証付きアップデート**:
  - アプリ起動時に GitHub Releases から最新バージョンをバックグラウンド非同期チェック。
  - 新バージョン検出時はリリースノート確認・プログレスバー付きダウンロードに対応し、専用一時ディレクトリでの `.part` ダウンロード、ファイルサイズ／SHA-256 チェックサム検証（不一致時は一時ファイル即破棄）、および Windows `AppMutex`（`SAPNetVisualizer_AppMutex`）連携による安全なインストーラー起動を提供します。
- **ローテーションファイルログ＆未捕捉例外記録**:
  - `~/.sap_visualizer/logs/app.log` に起動情報および未捕捉例外（メインスレッド／ワーカースレッド）のスタックトレースを自動記録（1MB × 3世代ローテーション）。
- **インストーラー配布対応 (Windows)**:
  - Inno Setup と連携し、管理者権限不要（一般ユーザー権限）でインストール・上書き更新可能な Windows セットアップウィザード（`.exe`）および SHA-256 チェックサムファイル（`.exe.sha256`）を生成可能。

---

## 2つの利用シナリオ

| シナリオ | 概要 | 主な用途 |
| :--- | :--- | :--- |
| **① オフライン解析（推奨）** | シミュレーション側で `.jsonl.gz` ログを出力し、本ビューアー（`main.py` またはインストーラー版）でじっくり再生・グラフ分析。 | 実験結果の精査、論文・スライド用グラフ作成、研究発表 |
| **② リアルタイムモニタリング** | シミュレーション実行と並行してビューアーを起動し、学習の進行状況や知識転移の挙動をリアルタイムに画面監視。 | アルゴリズムのデバッグ、シミュレーション動作確認 |

---

## 必要要件

- **OS**: Windows / macOS / Linux（インストーラービルドは Windows 向け）
- **Python**: 3.11 以上
- **実行時ライブラリ**（[requirements.txt](requirements.txt)）:
  - `numpy >= 1.21.0`
  - `pygame >= 2.1.0`
  - `pyyaml >= 6.0`
- **開発・テストツール**（[requirements-dev.txt](requirements-dev.txt)）:
  - `pytest >= 8.0`
  - `ruff >= 0.6`
- **インストーラービルドツール**（[requirements-build.txt](requirements-build.txt)）:
  - `pyinstaller >= 6.0.0`（Windows インストーラー作成時のみ）

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
起動時に自動的にフォルダ選択ダイアログが表示されます。実験ログ（`sap_dynamic_log_*.jsonl.gz` または `*.jsonl`）が保存されているフォルダを選択してください（※ログおよび設定ファイルは選択対象フォルダの直下に配置してください）。

#### 方法 B: ログファイル / フォルダを引数に指定して起動
```bash
# 実験ログフォルダを指定して起動
python main.py "path/to/experiment_log_folder"

# ログファイルを直接指定して起動 (.jsonl.gz または .jsonl)
python main.py "path/to/experiment_log_folder/sap_dynamic_log_20260801_120000.jsonl.gz"
```

---

## 操作方法・キーボードショートカット

ボタン名は実際のアプリ画面上の表示と対応しています。

| 操作項目 | GUI ボタン / マウス | キーボード | 機能説明 |
| :--- | :--- | :---: | :--- |
| **再生 / 一時停止** | `[再生]` / `[一時停止]` | `Space` | フレームの自動コマ送り再生と一時停止を切り替えます。 |
| **コマ送り** | `[コマ送り >>]` | `→` (右矢印) | 1フレーム進めます。 |
| **コマ戻し** | `[<< コマ戻し]` | `←` (左矢印) | 1フレーム戻します。 |
| **リアルタイム追従** | `[リアルタイム追従]` | `L` | 最新フレームへの自動追従（Live Follow）の有効/無効を切り替えます。 |
| **画面モード切替** | `[グラフ画面 (G)]` / `[ステップ画面 (G)]` | `G` | ステップ詳細表示モードと活性値推移折れ線グラフモードを切り替えます。 |
| **グラフ画像保存** | `[グラフ保存 (S)]`（グラフ画面内） | `S` | 折れ線グラフ画面を高解像度 PNG 画像として保存します。 |
| **知識表示一括切替** | `[全選択]` / `[全解除]`（グラフ画面右パネル） | - | 折れ線グラフに表示する知識ノードを一括で ON / OFF します。 |
| **次のエピソード** | `[エピソード >\|]` | `E` | 次のエピソード開始フレームへジャンプします。 |
| **前のエピソード** | `[\|< エピソード]` | `Shift + E` | 前のエピソード開始フレームへジャンプします。 |
| **次の知識選択** | `[知識選択 >\|]` | `P` | 次の知識選択イベント（`SELECT_PLAN`）へジャンプします。 |
| **前の知識選択** | `[\|< 知識選択]` | `Shift + P` | 直前の知識選択イベントへジャンプします。 |
| **次の活性化** | `[活性化 >\|]` | `A` | 次の初期活性化イベント（`ACTIVATION`）へジャンプします。 |
| **前の活性化** | `[\|< 活性化]` | `Shift + A` | 直前の初期活性化イベントへジャンプします。 |
| **次の重み更新** | `[重み更新 >\|]` | `W` | 次の重み更新イベント（`WEIGHT_UPDATE`）へジャンプします。 |
| **前の重み更新** | `[\|< 重み更新]` | `Shift + W` | 直前の重み更新イベントへジャンプします。 |
| **フォルダを開く** | `[実験ログフォルダ選択 (O)...]` | `O` | フォルダ選択ダイアログを開き、別の実験ログを読み込みます。 |
| **設定確認** | `[ハイパーパラメータ]` | `C` | ハイパーパラメータ一覧オーバーレイを開閉します（`↑`/`↓` またはホイールでスクロール）。 |
| **ヘルプ表示** | `[ヘルプ]` | `H` / `?` / `Esc` | 操作ガイドオーバーレイを開閉します。 |
| **最初に戻る** | `[リセット]` | - | フレームインデックス 0（最初）に戻します。 |
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

Windows 環境において、テスト実行、クリーンな一時仮想環境の作成（[requirements-build.txt](requirements-build.txt) を使用）、PyInstaller による exe 化、Inno Setup によるインストーラーおよび `.sha256` チェックサム生成、中間生成物の自動削除までを一括で行う自動化スクリプトを用意しています。バージョン番号は [sap_visualizer/constants.py](sap_visualizer/constants.py) の `APP_VERSION` を単一情報源（SSOT）としてビルド時に動的注入します。

### 前提条件
- Python 3.11 以上およびテスト実行環境（`pip install -r requirements-dev.txt`）
- [Inno Setup 6 (無料)](https://jrsoftware.org/isdl.php) がインストールされていること

### ビルドの実行
```powershell
.\build_all.bat
```
または直接スクリプトを実行することもできます（事前テストを省略する場合は `--skip-tests` を指定）：
```powershell
python packaging\build.py
```

- **生成されるインストーラー**: `dist_installer/SAP_net_Visualizer_Setup_v<APP_VERSION>.exe`
- **生成されるチェックサム**: `dist_installer/SAP_net_Visualizer_Setup_v<APP_VERSION>.exe.sha256`
- **インストール先**: ユーザーの `%LOCALAPPDATA%\Programs\SAP-net-Visualizer`（管理者権限不要、`AppMutex` による起動中プロセス検知および上書き更新対応）

---

## テスト・品質ゲート（開発者向け）

開発時はテスト・リントツールをインストールしたうえで、ローカル品質ゲートを一括実行できます。

### 1. 開発用依存のインストール
```bash
pip install -r requirements-dev.txt
```

### 2. 品質チェックの実行（`ruff` + `pytest`）
Windows では [check.bat](check.bat) により、静的解析（`ruff check --select F,E9`）と全テストスイート（`pytest`）を一括実行できます。
```powershell
.\check.bat
```
Linux / macOS 環境では以下を直接実行します（ヘッドレス環境向けに `SDL_VIDEODRIVER=dummy` 等を指定）。
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m ruff check --select F,E9 sap_visualizer main.py packaging tests
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest -q
```

### 3. git pre-push フックの有効化（任意）
`git push` 前に上記品質チェックを自動実行したい場合は、同梱のフックパスを有効化してください（[.githooks/pre-push](.githooks/pre-push) は Windows / Linux / macOS の OS 判定に対応しています）。
```bash
git config core.hooksPath .githooks
```

---

## ディレクトリ構成

```text
SAP-net-Visualizer/
├── .githooks/
│   └── pre-push                    # push 前自動品質チェック用 git フック
├── .gitignore                      # Git 除外設定
├── DATA_FORMAT.md                  # データフォーマット仕様書 (最小構成/推奨構成)
├── README.md                       # 本ドキュメント (アプリケーション概要・操作方法)
├── build_all.bat                   # ワンクリック全自動クリーンビルドバッチ (Windows)
├── check.bat                       # ローカル品質ゲート (ruff + pytest 一括実行)
├── main.py                         # アプリケーションエントリーポイント
├── pyproject.toml                  # pytest / ruff 設定 (target-version: py311)
├── requirements.txt                # 実行時最小依存パッケージ
├── requirements-dev.txt            # 開発・テスト用依存パッケージ (pytest, ruff)
├── requirements-build.txt          # ビルド用依存パッケージ (pyinstaller)
├── sap_visualizer.md               # シミュレーションプログラム改変・導入ガイド
├── docs/
│   └── plans/                      # 改善計画ロードマップ・Issue 計画書 (00_ROADMAP, ISSUE-01〜09)
├── packaging/                      # Windows 配布・パッケージング設定
│   ├── SAP-net-Visualizer.spec     # PyInstaller 設定 (SAP_VERSION_INFO_PATH 対応)
│   ├── app_icon.ico                # マルチサイズアイコン (16〜256px)
│   ├── build.py                    # 全自動クリーンビルドスクリプト (テスト実行・SSOT注入・SHA-256生成)
│   ├── installer.iss               # Inno Setup 定義スクリプト (MyAppVersion 動的注入・AppMutex)
│   └── version_info.template.txt   # Windows 実行ファイルメタデータテンプレート
├── sap_visualizer/                 # コア可視化パッケージ
│   ├── __init__.py
│   ├── config_loader.py            # YAML 設定動的パースローダー
│   ├── constants.py                # 共通定数・バージョン SSOT (APP_VERSION)・レイアウト定義
│   ├── folder_selector_gui.py      # フォルダ選択 GUI ダイアログ
│   ├── history_manager.py          # フォルダ履歴管理・JSON 永続化 (Tkinter 非依存)
│   ├── logging_setup.py            # ローテーションファイルログ・未捕捉例外フック設定
│   ├── models.py                   # 型安全なデータモデル (LogFrame, ResolvedFrameInfo)
│   ├── sap_visual_logger.py        # ログ解析・欠損値復元キャッシュ ($O(1)$)・検索モジュール
│   ├── sap_visualizer_gui.py       # メイン GUI コントローラー (Pygame)
│   ├── theme.py                    # 統一カラーパレット・デザイントークン
│   ├── update_dialog.py            # アップデート通知・ダウンロード GUI ダイアログ
│   ├── updater.py                  # GitHub Releases 連携・SHA-256/サイズ検証付き更新エンジン
│   ├── utils/                      # 共通ユーティリティ (幾何計算・リソースパス)
│   │   ├── __init__.py
│   │   ├── geometry_utils.py
│   │   └── resource_utils.py
│   └── views/                      # 画面別レンダリングビュー
│       ├── __init__.py
│       ├── base_view.py            # 描画基底クラス
│       ├── chart_view.py           # 活性値推移折れ線グラフビュー
│       ├── overlays.py             # 設定確認・ヘルプモーダルビュー (YAML キャッシュ対応)
│       └── step_view.py            # ステップ詳細表示ビュー
└── tests/                          # テストスイート (pytest / unittest)
    ├── __init__.py
    ├── conftest.py                 # セッション隔離フィクスチャ (dummy ドライバ・履歴/通信保護・Tk リトライ)
    ├── test_config_loader.py       # YAML 設定ローダー単体テスト
    ├── test_folder_selector.py     # フォルダ選択 GUI ダイアログテスト
    ├── test_geometry_utils.py      # 幾何計算ユーティリティ単体テスト
    ├── test_history_manager.py     # 履歴管理単体テスト
    ├── test_integration.py         # 全体パイプライン統合テスト
    ├── test_logger.py              # ロガー単体テスト (解凍・耐障害性・O(1) キャッシュ・検索)
    ├── test_logging_setup.py       # ファイルロギング・ローテーション・例外フックテスト
    ├── test_models.py              # データモデル単体テスト
    ├── test_updater.py             # アップデータ単体テスト (SHA-256/サイズ検証・.part クリーンアップ・UI)
    ├── test_version_consistency.py # バージョン SSOT・テンプレート・ビルド中断テスト
    └── test_visualizer_gui.py      # 可視化 GUI 単体テスト (描画・フォルダ切替リセット・キャッシュ)
```

---

## ドキュメント一覧

- **[sap_visualizer.md](sap_visualizer.md)**: SAP-net を利用したシミュレーションプログラムへの可視化・ログ機能 導入・改変ガイド
- **[DATA_FORMAT.md](DATA_FORMAT.md)**: 動的ログデータ（JSONL）およびハイパーパラメータ設定（YAML）の詳細仕様書
- **[docs/plans/00_ROADMAP.md](docs/plans/00_ROADMAP.md)**: 改善提案ロードマップ・各 Issue の設計計画書

---

## 著作権・ライセンス

Copyright (C) 2026 Mitsuie. All rights reserved.
