# SAP-net Visualizer データフォーマット仕様書

本書は、**SAP-net Visualizer**（`main.py` および配布バイナリ）で実験ログを読み込み、正常に可視化・再生・分析を行うためのデータフォーマット仕様についてまとめたものです。

用途に合わせて **最小構成（Minimal）** と **推奨構成（Recommended）** を定義しています。

---

## 目次

1. [ファイル・ディレクトリ構成](#1-ファイルディレクトリ構成)
   - [最小構成 (Minimal)](#11-ファイルディレクトリ構成---最小構成-minimal)
   - [推奨構成 (Recommended)](#12-ファイルディレクトリ構成---推奨構成-recommended)
2. [動的ログデータ仕様 (JSON Lines)](#2-動的ログデータ仕様-json-lines)
   - [各データフィールド一覧](#21-各データフィールド一覧)
   - [最小構成のデータ例](#22-ログデータ---最小構成-minimal)
   - [推奨構成のデータ例](#23-ログデータ---推奨構成-recommended)
3. [ハイパーパラメータ設定ファイル仕様 (YAML)](#3-ハイパーパラメータ設定ファイル仕様-yaml)
4. [Python からのデータ出力方法](#4-python-からのデータ出力方法)
   - [方法 A: 公式ロガー (SAPVisualLogger) を利用（推奨）](#41-方法-a-公式ロガー-sapvisuallogger-を利用推奨)
   - [方法 B: 自作スクリプト・他言語から直接 JSONL を出力](#42-方法-b-自作スクリプト他言語から直接-jsonl-を出力)
5. [各データフィールドと GUI 機能の対応表](#5-各データフィールドと-gui-機能の対応表)

---

## 1. ファイル・ディレクトリ構成

### 1.1 ファイル・ディレクトリ構成 - 最小構成 (Minimal)

可視化を行うために最低限必要なのは、**単一の動的ログファイル（`.jsonl` または `.jsonl.gz`）** のみです。

```text
任意のフォルダ/
└── sap_dynamic_log.jsonl.gz  (または .jsonl)
```

- **起動方法**:
  ```bash
  python main.py "path/to/sap_dynamic_log.jsonl.gz"
  ```
  または `python main.py` 起動後に表示されるファイル選択ダイアログで指定します。

---

### 1.2 ファイル・ディレクトリ構成 - 推奨構成 (Recommended)

実験フォルダ内に **動的ログファイル** と **実験ハイパーパラメータ設定ファイル (YAML)** を対にして配置する構成です。

```text
experiment_logs/
└── 20260821_120000_exp1/                       # 実験ごとのログフォルダ
    ├── sap_dynamic_log_20260821_120000.jsonl.gz  # 動的パラメータログ (gzip圧縮)
    └── config_used_20260821_120000.yaml          # 実験ハイパーパラメータ設定
```

- **メリット**:
  - `python main.py` 起動時にフォルダを選択するだけで、最新のログとパラメータを自動検出して一括ロード。
  - GUI上で `C` キーを押すことで、実験設定一覧を日本語解説付きで閲覧可能。
  - `.jsonl.gz` 形式により、ディスク容量を約 90% 削減し、I/Oを高速化。

---

## 2. 動的ログデータ仕様 (JSON Lines)

ログファイルは **JSON Lines 形式**（1行につき1つの JSON オブジェクト、改行区切り）で記録します。通常テキスト（`.jsonl`）または gzip 圧縮（`.jsonl.gz`）の双読に対応しています。

### 2.1 各データフィールド一覧

| フィールド名 | 型 | 必須度 | 説明 | デフォルト / 補足 |
| :--- | :--- | :---: | :--- | :--- |
| `episode` | `int` | **必須** | 現在のエピソード番号 | 例: `1` |
| `step` | `int` | **必須** | 現在のエピソード内のタイムステップ数 | 例: `10` |
| `A` | `list[float]` | **必須** | 各知識ノードの活性値リスト (長さ $N$) | 範囲: 概ね `0.0` 〜 `1.0` |
| `index` | `int` | 推奨 | ログ全体の通しフレーム番号 | `0, 1, 2, ...` |
| `event_type` | `str` | 推奨 | フレームのイベント種別 | `"STEP"`, `"ACTIVATION"`, `"SELECT_PLAN"`, `"WEIGHT_UPDATE"` |
| `weight` | `list[list[float]]` | 推奨 | 知識ノード間の重み行列 ($N \times N$) | 結合線の太さ・濃さに反映 |
| `plan` | `int` \| `null` | 推奨 | 現在選択・実行中の知識ノード番号 | GUI上で金色二重枠でハイライト |
| `selectplans` | `list[int]` | 推奨 | 活性化閾値を超えた転移候補知識番号のリスト | GUI上で緑色二重枠でハイライト |
| `threshold` | `float` | 推奨 | 知識活性化・転移判断の評価閾値 | 未指定時は `0.18` |
| `policyvalue` | `list[float]` | 任意 | 各知識の価値評価値 (Q値など) | 知識ノード情報補足 |
| `reused_action` | `int` \| `null` | 任意 | 転移再利用された行動ID | 動作ログ補足 |

---

### 2.2 ログデータ - 最小構成 (Minimal)

ステップごとの活性値推移とタイムライン再生を行うための最小限の JSON 行です。

```json
{"episode": 1, "step": 1, "A": [0.12, 0.45, 0.89, 0.05]}
{"episode": 1, "step": 2, "A": [0.15, 0.42, 0.92, 0.08]}
{"episode": 1, "step": 3, "A": [0.20, 0.38, 0.95, 0.12]}
```

---

### 2.3 ログデータ - 推奨構成 (Recommended)

SAP-net Visualizer の全機能（ネットワークグラフ描画、選択・転移リング表示、イベントジャンプ、閾値表示など）を完全活用するための JSON 行です。

```json
{
  "index": 0,
  "episode": 1,
  "step": 1,
  "event_type": "STEP",
  "A": [0.12, 0.45, 0.89, 0.05],
  "weight": [
    [0.00, 0.25, 0.10, 0.00],
    [0.25, 0.00, 0.00, 0.30],
    [0.10, 0.00, 0.00, 0.15],
    [0.00, 0.30, 0.15, 0.00]
  ],
  "plan": 2,
  "selectplans": [2],
  "policyvalue": [0.15, 0.35, 0.89, 0.20],
  "reused_action": 3,
  "threshold": 0.18
}
```

---

## 3. ハイパーパラメータ設定ファイル仕様 (YAML)

ログフォルダ内に `config_used_*.yaml` を配置することで、GUI上の設定確認モーダル（`C` キー）に自動読み込みされます。

### 推奨 YAML 例 (`config_used_20260821_120000.yaml`)

```yaml
META:
  TARGET_SCRIPT: "train_robot.py"
  DESCRIPTION: "Robot navigation experiment with SAP-net transfer"

MODE:
  NAME: "Q-SAP"
  USE_SHIELD: true

EXPERIMENT:
  ENABLE_SAP_VISUALIZER: true
  MAX_EPISODES: 500
  MAX_STEPS: 1000
  GOAL_POSITION: [2.5, 3.0, 0.0]
  INITIAL_POSITION: [0.0, 0.0, 0.0]

SAP:
  ACTIVATION: 0.0
  THRESHOLD: 0.18
  ATTENUATION: 0.05
  FREQ_ACT: 1
  FREQ_WEIGHT: 5
  FIRST_WEIGHT: 0.1
  POSITIVE_ADJUSTMENT: 0.05
  NEGATIVE_ADJUSTMENT: 0.02
  COLLISION: 0.30
  T_RATE: 0.80

QLEARNING:
  ALPHA: 0.1
  GAMMA: 0.95
  TAU: 0.5
  LOAD_Q_TABLE: false

REWARD:
  REWARD_GOAL: 100.0
  REWARD_COLLISION: -50.0
  REWARD_STEP: -0.1
  REWARD_NEAR_WALL: -1.0
  REWARD_SHAPING_COEFF: 1.0
```

---

## 4. Python からのデータ出力方法

### 4.1 方法 A: 公式ロガー (`SAPVisualLogger`) を利用（推奨）

本パッケージに含まれる `sap_visualizer.SAPVisualLogger` を利用すると、メモリバッファリングと一括 gzip 保存が自動で行われます。

```python
from sap_visualizer import SAPVisualLogger

# 1. ロガーの初期化 (ログ出力先フォルダとタイムスタンプを指定)
logger = SAPVisualLogger(
    log_dir="experiment_logs/20260821_120000_exp1",
    timestamp="20260821_120000",
    enabled=True
)

# 2. 各ステップで状態を記録 (メモリ上に蓄積)
logger.record_frame(
    episode=1,
    step=10,
    event_type="STEP",                # "STEP", "ACTIVATION", "SELECT_PLAN", "WEIGHT_UPDATE"
    A=activations,                    # listまたは1D numpy array
    weight=weight_matrix,             # listまたは2D numpy array
    plan=selected_plan,               # int
    selectplans=candidate_plans,      # list[int]
    policyvalue=q_values,             # list[float]
    reused_action=action_id,          # int
    threshold=0.18                    # float
)

# 3. エピソード終了時や実験完了時に一括ファイル保存 (.jsonl.gz が生成される)
logger.save_to_file()
```

---

### 4.2 方法 B: 自作スクリプト・他言語から直接 JSONL を出力

標準の `json` および `gzip` モジュールを用いて直接ファイル出力することも可能です。

```python
import gzip
import json

log_file_path = "sap_dynamic_log_sample.jsonl.gz"

with gzip.open(log_file_path, "wt", encoding="utf-8") as f:
    for ep in range(1, 3):
        for st in range(1, 100):
            frame = {
                "index": (ep - 1) * 100 + st,
                "episode": ep,
                "step": st,
                "event_type": "STEP",
                "A": [0.1 * (st % 10), 0.05 * (st % 20), 0.8],
                "weight": [[0.0, 0.2], [0.2, 0.0]],
                "plan": 0,
                "selectplans": [0],
                "threshold": 0.18
            }
            f.write(json.dumps(frame) + "\n")
```

---

## 5. 各データフィールドと GUI 機能の対応表

| データフィールド | GUI 上の対応画面 / 機能 | ショートカット / 表示箇所 |
| :--- | :--- | :--- |
| `A` (活性値) | 各知識ノードの円のサイズ・色（青〜赤）、右側リアルタイムバーチャート、折れ線グラフ | メイン画面 / `G` キー（グラフ切替） |
| `weight` (重み行列) | 知識ノード間を繋ぐエッジ線（太さ・透明度） | ステップ表示画面 |
| `plan` (選択プラン) | 対象ノードの周囲に**金色二重リング**を描画 | ステップ表示画面 / `P` キー（ジャンプ） |
| `selectplans` (転移候補) | 対象ノードの周囲に**緑色二重リング**を描画 | ステップ表示画面 |
| `threshold` (閾値) | バーチャートおよび折れ線グラフ上の**赤色基準線** | メイン画面 / 折れ線グラフ画面 |
| `event_type` | サブヘッダーのイベント表示、スマートジャンプ対象の検知 | `A`, `P`, `W` キー（各イベントへ即時ジャンプ） |
| `episode` / `step` | サブヘッダー表示、タイムラインスライダー位置、エピソードジャンプ | `E` / `Shift+E` キー |
| `config_used_*.yaml` | ハイパーパラメータ設定モーダル（パラメータ名・値・日本語解説） | `C` キー |
