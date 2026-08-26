# SAP-net 動的ログ出力・可視化導入ガイド (`sap_visualizer.md`)

本書は、SAP-net（Spreading Activation Policy Network）強化学習アルゴリズムやロボット制御シミュレーション（Webots、PyBullet、Gymnasium、自作シミュレータ等）に対して、**動的パラメータ（知識活性値・重み行列・選択プラン・閾値・ハイパーパラメータ等）のログ出力機能を組み込むための自己完結型・実装ガイド**です。

本書および付属の [`DATA_FORMAT.md`](DATA_FORMAT.md) のみを参照することで、外部リポジトリのソースコードを参照することなく、シミュレーションプログラムへのログ記録機能の追加を完結させることができます。

---

## 目次

1. [概要と導入メリット](#1-概要と導入メリット)
2. [組み込み用ロガークラス完全実装 (`SAPLogger`)](#2-組み込み用ロガークラス完全実装-saplogger)
3. [システムアーキテクチャと出力フロー](#3-システムアーキテクチャと出力フロー)
4. [シミュレーションプログラム改変手順（ステップ・バイ・ステップ）](#4-シミュレーションプログラム改変手順ステップバイステップ)
   - [Step 1: ロガークラスの配置・インポート](#step-1-ロガークラスの配置インポート)
   - [Step 2: 設定ファイル (`config.yaml`) へのパラメータ追加](#step-2-設定ファイル-configyaml-へのパラメータ追加)
   - [Step 3: シミュレーション初期化時のロガーセットアップ](#step-3-シミュレーション初期化時のロガーセットアップ)
   - [Step 4: 各ステップ・重要イベントでのログ記録 (`record_frame`)](#step-4-各ステップ重要イベントでのログ記録-record_frame)
   - [Step 5: エピソード終了時の追記保存とメモリ解放 (`flush_episode`)](#step-5-エピソード終了時の追記保存とメモリ解放-flush_episode)
   - [Step 6: 実験設定YAMLのエクスポート連動 (`config_used_<timestamp>.yaml`)](#step-6-実験設定yamlのエクスポート連動-config_used_timestampyaml)
5. [実践的な改変パターン別コード例](#5-実践的な改変パターン別コード例)
   - [パターン A: 制御ループ内への直接組み込み（Direct Integration）](#パターン-a-制御ループ内への直接組み込みdirect-integration)
   - [パターン B: Gymnasium / 強化学習環境のラッパーフック（Wrapper Integration）](#パターン-b-gymnasium--強化学習環境のラッパーフックwrapper-integration)
6. [API・記録フィールド・イベント種別リファレンス](#6-api記録フィールドイベント種別リファレンス)
   - [6.1 `SAPLogger` 主要メソッド一覧](#61-saplogger-主要メソッド一覧)
   - [6.2 `record_frame()` 引数仕様一覧](#62-record_frame-引数仕様一覧)
   - [6.3 `event_type` の発行タイミングと目的](#63-event_type-の発行タイミングと目的)
7. [生成ログのビューアーでの閲覧・分析フロー](#7-生成ログのビューアーでの閲覧分析フロー)
8. [パフォーマンス最適化と安定設計のポイント](#8-パフォーマンス最適化と安定設計のポイント)
9. [トラブルシューティング ＆ FAQ](#9-トラブルシューティング--faq)
10. [関連ドキュメント](#10-関連ドキュメント)

---

## 1. 概要と導入メリット

強化学習において SAP-net のような動的転移学習を適用する際、知識ノードの活性化度合い、重みネットワークの変化、転移判断の成否を事後に精査できることは、アルゴリズムの挙動理解・デバッグ・論文報告において極めて重要です。

本ガイドに従ってシミュレーションコードにログ出力を組み込むことで、以下のメリットが得られます。

* **ゼロ遅延・超軽量ロギング**:
  各ステップはオンメモリ配列へ格納し、エピソード終了時に gzip 圧縮ストリームへ一括追記してメモリを即座に解放するため、何千エピソードの長期学習でも計算FPSの低下やメモリ不足（OOM）が発生しません。
* **SAP-net Visualizer との完全互換**:
  出力されたログフォルダは、スタンドアロンビューアー（`SAP-net-Visualizer`）にそのまま読み込ませるだけで、ネットワーク構造の動的描画、知識選択ハイライト、活性値推移折れ線グラフ、高解像度PNG保存、ハイパーパラメータ一覧表示などの高度な分析機能を即座に利用できます。

---

## 2. 組み込み用ロガークラス完全実装 (`SAPLogger`)

シミュレーション側のワークスペースに作成する、**自己完結型のロガークラス**です。
以下のコードをシミュレーションプロジェクト内に `sap_logger.py` として保存するか、メインスクリプト内に直接貼り付けて使用します。

> **依存ライブラリ**: Python標準ライブラリ（`os`, `json`, `gzip`）および `numpy` のみで動作します（Pygame等のGUIライブラリは一切不要です）。

```python
# sap_logger.py
import os
import json
import gzip
import numpy as np

class SAPLogger:
    """
    SAP-netの動的パラメータ（活性値A, 重み行列weight, 選択plan, 活性化候補, 転移評価等）を
    メモリバッファへ蓄積し、gzip圧縮JSONL形式 (.jsonl.gz) として高速追記保存するロガークラス。
    """
    def __init__(self, log_dir=None, timestamp=None, enabled=True):
        self.enabled = enabled
        self.log_dir = log_dir
        self.timestamp = timestamp
        self.history = []  # 現在のエピソード内のフレームバッファ
        self.global_frame_index = 0  # ログ全体の通算フレーム番号
        self.log_file_path = None
        
        if self.enabled and self.log_dir and self.timestamp:
            os.makedirs(self.log_dir, exist_ok=True)
            self.log_file_path = os.path.join(self.log_dir, f"sap_dynamic_log_{self.timestamp}.jsonl.gz")

    def record_frame(self, episode, step, event_type, A, weight=None, plan=None, selectplans=None, policyvalue=None, reused_action=None, threshold=0.18):
        """
        1フレーム（1ステップまたは特定イベント発生時）の状態をメモリバッファ (self.history) にキャプチャする。
        毎ステップのディスク I/O を回避し、シミュレーション速度を最高速に保ちます。
        """
        if not self.enabled:
            return
            
        frame_data = {
            "index": self.global_frame_index,
            "episode": int(episode),
            "step": int(step),
            "event_type": str(event_type),  # "STEP", "ACTIVATION", "SELECT_PLAN", "WEIGHT_UPDATE"
            "A": np.array(A, dtype=float).tolist() if A is not None else [],
            "weight": np.array(weight, dtype=float).tolist() if weight is not None else [],
            "plan": int(plan) if plan is not None else None,
            "selectplans": np.array(selectplans, dtype=int).tolist() if selectplans is not None else [],
            "policyvalue": np.array(policyvalue, dtype=float).tolist() if policyvalue is not None else [],
            "reused_action": int(reused_action) if reused_action is not None else None,
            "threshold": float(threshold) if threshold is not None else 0.18,
        }
        
        self.history.append(frame_data)
        self.global_frame_index += 1

    def flush_episode(self, clear_memory=True):
        """
        メモリ上のフレームバッファを .jsonl.gz ファイルへ追記 (append) 保存し、メモリを解放する。
        各エピソード終了時に呼び出すことで、RAM の肥大化（OOM）を完全に防ぎます。
        """
        if not self.enabled or not self.log_file_path or not self.history:
            return False
            
        try:
            # gzip追記モード ("at") により Multi-stream gzip 形式で安全追記
            with gzip.open(self.log_file_path, "at", encoding="utf-8") as f:
                for frame in self.history:
                    f.write(json.dumps(frame) + "\n")
            
            if clear_memory:
                self.history.clear()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to flush SAP log: {e}")
            return False

    def save_to_file(self, clear_memory=False):
        """
        全フレーム履歴を一括保存する（全シミュレーション完了時のフォールバック用）。
        """
        if not self.enabled or not self.log_file_path or not self.history:
            return False
            
        try:
            with gzip.open(self.log_file_path, "wt", encoding="utf-8") as f:
                for frame in self.history:
                    f.write(json.dumps(frame) + "\n")
            if clear_memory:
                self.history.clear()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save SAP log: {e}")
            return False

    def clear_history(self):
        """メモリ上のフレームバッファをクリア"""
        self.history.clear()
```

---

## 3. システムアーキテクチャと出力フロー

シミュレーション制御ループと `SAPLogger` は、以下のフローで疎結合に連携します。

```mermaid
flowchart TD
    subgraph SimLoop ["シミュレーション制御ループ"]
        Step["各タイムステップ実行"]
        ActEvent["知識活性化・転移判断"]
        WeightEvent["重み更新タイミング"]
        EpEnd["エピソード終了"]
        SimEnd["全シミュレーション完了"]
    end

    subgraph Logger ["SAPLogger (sap_logger.py)"]
        Record["record_frame()"]
        MemBuffer[("オンメモリバッファ<br>self.history")]
        FlushEp["flush_episode(clear_memory=True)<br>(追記保存 ＋ メモリ即時解放)"]
    end

    subgraph Output ["出力ログフォルダ"]
        LogFile[("sap_dynamic_log_<timestamp>.jsonl.gz")]
        YamlFile[("config_used_<timestamp>.yaml")]
    end

    subgraph Viewer ["可視化・分析 (SAP-net Visualizer)"]
        GUIApp["SAP-net-Visualizer<br>(再生・グラフ分析・PNG保存)"]
    end

    Step -->|event_type='STEP'| Record
    ActEvent -->|event_type='ACTIVATION'<br>event_type='SELECT_PLAN'| Record
    WeightEvent -->|event_type='WEIGHT_UPDATE'| Record
    Record --> MemBuffer

    EpEnd -->|毎エピソード終了時| FlushEp
    FlushEp -->|高速gzip追記| LogFile
    SimEnd -.->|実験開始/終了時| YamlFile

    LogFile -->|フォルダごと読み込み| GUIApp
    YamlFile -->|設定確認 (Cキー)| GUIApp
```

---

## 4. シミュレーションプログラム改変手順（ステップ・バイ・ステップ）

既存のシミュレーションコードを改変する具体的な手順です。

### Step 1: ロガークラスの配置・インポート
シミュレーションのプロジェクトルートに `sap_logger.py`（セクション2のコード）を作成し、メインスクリプトまたはエージェントコントローラにインポートを追加します。

```python
import os
import sys
import datetime
import yaml

from sap_logger import SAPLogger
```

---

### Step 2: 設定ファイル (`config.yaml`) へのパラメータ追加
シミュレーションの設定ファイル（YAML等）に、可視化ログ機能の有効化フラグを追加します。

```yaml
EXPERIMENT:
  ENABLE_SAP_VISUALIZER: true  # SAP動的ログ記録の有効/無効
  MAX_EPISODES: 500
  MAX_STEPS: 1000

SAP:
  THRESHOLD: 0.18              # 知識活性化閾値 (可視化の赤色基準線に反映)
  # その他のSAPハイパーパラメータ...
```

---

### Step 3: シミュレーション初期化時のロガーセットアップ
シミュレーション開始時（実験ログフォルダ作成直後）に、ロガーを初期化します。

```python
# 1. ログ出力先フォルダとタイムスタンプの決定
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_dir = os.path.join("experiment_logs", f"{timestamp}_exp1")
os.makedirs(log_dir, exist_ok=True)

# 2. 設定フラグの取得
enable_vis = config.get("EXPERIMENT", {}).get("ENABLE_SAP_VISUALIZER", True)

# 3. SAPLogger の初期化
sap_logger = SAPLogger(
    log_dir=log_dir,
    timestamp=timestamp,
    enabled=enable_vis
)
```

---

### Step 4: 各ステップ・重要イベントでのログ記録 (`record_frame`)
シミュレーションの制御ループ内、および SAP-net の各内部イベント（活性化拡散・知識選択・重み更新）のタイミングで `record_frame()` を呼び出します。

#### ① 通常タイムステップの記録 (`STEP`)
```python
sap_logger.record_frame(
    episode=current_episode,
    step=current_step,
    event_type="STEP",
    A=sap_net.A,                    # 現在の知識活性値 (1D配列またはリスト)
    weight=sap_net.weight,          # 現在の結合重み行列 (2D配列またはリスト)
    plan=selected_plan_id,          # 実行中の知識インデックス (int または None)
    selectplans=candidate_flags,    # 活性化候補フラグ (list[int] または 1D配列)
    policyvalue=transfer_values,    # 転移評価値 (list[float])
    reused_action=action_id,        # 知識推奨行動 (int または None)
    threshold=sap_net.threshold     # 活性化閾値 (float)
)
```

#### ② 活性化拡散イベントの記録 (`ACTIVATION`)
```python
# select_policy 実行直前など、初期活性値や候補知識が決定されたタイミング
sap_logger.record_frame(
    episode=current_episode,
    step=current_step,
    event_type="ACTIVATION",
    A=sap_net.A,
    weight=sap_net.weight,
    selectplans=candidate_flags,
    threshold=sap_net.threshold
)
```

#### ③ 知識選択イベントの記録 (`SELECT_PLAN`)
```python
# sapnet() による活性化拡散と最終知識プラン決定直後
sap_logger.record_frame(
    episode=current_episode,
    step=current_step,
    event_type="SELECT_PLAN",
    A=sap_net.A,
    weight=sap_net.weight,
    plan=final_plan_id,
    selectplans=candidate_flags,
    policyvalue=transfer_values,
    threshold=sap_net.threshold
)
```

#### ④ 重み更新イベントの記録 (`WEIGHT_UPDATE`)
```python
# 重み調整（simpleadjustweight 等）の実行直後
sap_logger.record_frame(
    episode=current_episode,
    step=current_step,
    event_type="WEIGHT_UPDATE",
    A=sap_net.A,
    weight=sap_net.weight,
    policyvalue=transfer_values,
    threshold=sap_net.threshold
)
```

---

### Step 5: エピソード終了時の追記保存とメモリ解放 (`flush_episode`)
各エピソードが完了したタイミングで `flush_episode(clear_memory=True)` を呼び出します。

```python
# エピソード終了時（stepループを抜けた直後）
sap_logger.flush_episode(clear_memory=True)
```

> [!TIP]
> `flush_episode(clear_memory=True)` を呼ぶことで、エピソード中にメモリへ溜まったフレームが `.jsonl.gz` へ即座に書き出され、メモリが解放されます。数千エピソードを実行しても RAM 消費量は常に数MB以下に抑えられます。

---

### Step 6: 実験設定YAMLのエクスポート連動 (`config_used_<timestamp>.yaml`)
ビューアーのハイパーパラメータ確認機能（`C` キー）を有効にするため、実験で使用した設定辞書を `config_used_<timestamp>.yaml` としてログフォルダ内に出力します。

```python
config_export_path = os.path.join(log_dir, f"config_used_{timestamp}.yaml")
with open(config_export_path, "w", encoding="utf-8") as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
```

---

## 5. 実践的な改変パターン別コード例

### パターン A: 制御ループ内への直接組み込み（Direct Integration）
Webots コントローラや自作ロボット制御ループに直接組み込む標準的な実装例です。

```python
import os
import sys
import datetime
import yaml
from sap_logger import SAPLogger

def run_simulation():
    # 1. 実験設定の読み込み
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join("experiment_logs", f"{timestamp}_exp1")
    os.makedirs(log_dir, exist_ok=True)

    # 実験設定YAMLをエクスポート (GUIの C キー連動用)
    with open(os.path.join(log_dir, f"config_used_{timestamp}.yaml"), "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)

    # 2. ロガーの初期化
    enable_vis = config.get("EXPERIMENT", {}).get("ENABLE_SAP_VISUALIZER", True)
    logger = SAPLogger(log_dir=log_dir, timestamp=timestamp, enabled=enable_vis)

    # 3. 学習ループ
    max_episodes = config.get("EXPERIMENT", {}).get("MAX_EPISODES", 100)
    for ep in range(1, max_episodes + 1):
        state = env.reset()
        done = False
        step = 0

        while not done:
            step += 1

            # SAP-net による知識選択
            sap.spread_activation(state)
            logger.record_frame(
                episode=ep, step=step, event_type="ACTIVATION",
                A=sap.A, weight=sap.weight, threshold=sap.threshold
            )

            chosen_plan = sap.select_plan()
            logger.record_frame(
                episode=ep, step=step, event_type="SELECT_PLAN",
                A=sap.A, weight=sap.weight, plan=chosen_plan, threshold=sap.threshold
            )

            # 行動決定・環境ステップ
            action = agent.get_action(state, chosen_plan)
            next_state, reward, done, info = env.step(action)

            # 通常ステップ記録
            logger.record_frame(
                episode=ep, step=step, event_type="STEP",
                A=sap.A, weight=sap.weight, plan=chosen_plan, threshold=sap.threshold
            )

            # 重み更新タイミング
            if sap.should_update_weight():
                sap.update_weight(reward)
                logger.record_frame(
                    episode=ep, step=step, event_type="WEIGHT_UPDATE",
                    A=sap.A, weight=sap.weight, threshold=sap.threshold
                )

            state = next_state

        # エピソード終了時にファイルへ追記保存 ＆ メモリ解放
        logger.flush_episode(clear_memory=True)

    print(f"[INFO] Simulation finished. Logs saved to: {log_dir}")

if __name__ == "__main__":
    run_simulation()
```

---

### パターン B: Gymnasium / 強化学習環境のラッパーフック（Wrapper Integration）
既存の環境コードに手を加えず、`gymnasium.Wrapper` を介して非侵襲に可視化ログを記録する実装例です。

```python
import gymnasium as gym
from sap_logger import SAPLogger

class SAPLoggingWrapper(gym.Wrapper):
    def __init__(self, env, log_dir, timestamp, enabled=True):
        super().__init__(env)
        self.logger = SAPLogger(log_dir=log_dir, timestamp=timestamp, enabled=enabled)
        self.current_episode = 0
        self.current_step = 0

    def reset(self, **kwargs):
        self.current_episode += 1
        self.current_step = 0
        return self.env.reset(**kwargs)

    def step(self, action):
        self.current_step += 1
        obs, reward, terminated, truncated, info = self.env.step(action)

        # info 辞書内に含まれる SAP-net パラメータを自動記録
        if "sap_info" in info:
            s_info = info["sap_info"]
            self.logger.record_frame(
                episode=self.current_episode,
                step=self.current_step,
                event_type="STEP",
                A=s_info.get("A"),
                weight=s_info.get("weight"),
                plan=s_info.get("plan"),
                selectplans=s_info.get("selectplans"),
                threshold=s_info.get("threshold", 0.18)
            )

        if terminated or truncated:
            # エピソード終了時に追記保存 ＆ メモリ解放
            self.logger.flush_episode(clear_memory=True)

        return obs, reward, terminated, truncated, info
```

---

## 6. API・記録フィールド・イベント種別リファレンス

### 6.1 `SAPLogger` 主要メソッド一覧

| メソッド | 引数 | 説明 / 用途 |
| :--- | :--- | :--- |
| **`record_frame(...)`** | `episode, step, event_type, A, weight, plan, ...` | 1フレームの状態をメモリバッファへ高速キャプチャ。通算フレーム番号 `index` を自動付与。 |
| **`flush_episode(clear_memory=True)`** | `clear_memory: bool` | エピソード終了時に `.jsonl.gz` へ追記保存し、メモリを即座に解放。 |
| **`save_to_file(clear_memory=False)`** | `clear_memory: bool` | メモリ上の全フレームを一括新規保存。 |
| **`clear_history()`** | - | メモリ上のフレームバッファを手動クリア。 |

---

### 6.2 `record_frame()` 引数仕様一覧

| 引数名 | 型 | 必須度 | 説明 / 推奨値 | GUI上での反映箇所 |
| :--- | :---: | :---: | :--- | :--- |
| **`episode`** | `int` | **必須** | 現在のエピソード番号（`1, 2, ...`） | ヘッダー情報、`E` / `Shift+E` ジャンプ |
| **`step`** | `int` | **必須** | エピソード内のタイムステップ数（`1, 2, ...`） | ヘッダー情報、スライダー位置 |
| **`event_type`** | `str` | **必須** | イベント種別（`"STEP"`, `"ACTIVATION"`, `"SELECT_PLAN"`, `"WEIGHT_UPDATE"`） | サブヘッダー表示、`A`/`P`/`W` スマートジャンプ |
| **`A`** | `list` / `ndarray` | **必須** | 各知識ノードの活性値リスト（長さ $N$） | ノード円のサイズ＆色、バーチャート、折れ線グラフ |
| **`weight`** | `list` / `ndarray` | 推奨 | 知識ノード間の重み行列（$N \times N$） | 知識間のエッジ線（太さ・透明度） |
| **`plan`** | `int` / `None` | 推奨 | 選択・実行された知識インデックス | ノード周囲の**金色二重リング** |
| **`selectplans`** | `list[int]` | 推奨 | 活性化閾値を超えた転移候補知識フラグ配列 | ノード周囲の**緑色二重リング** |
| **`policyvalue`** | `list[float]` | 任意 | 各知識の転移評価値（累積PT/NT評価など） | 知識ノード情報補足 |
| **`reused_action`** | `int` / `None` | 任意 | 知識転移により再利用された行動ID | 動作ログ補足 |
| **`threshold`** | `float` | 推奨 | 知識活性化の判定閾値（デフォルト `0.18`） | バーチャート・折れ線グラフ上の**赤色基準線** |

---

### 6.3 `event_type` の発行タイミングと目的

| `event_type` | 発行タイミング | 記録の目的とGUI機能 |
| :--- | :--- | :--- |
| **`STEP`** | 毎タイムステップの制御ループ内 | 通常ステップでの活性値減衰や状態遷移の追跡 |
| **`ACTIVATION`** | `select_policy` 内の活性化拡散前 | 擬似次状態予測によって候補となった知識フラグ（`selectplans`）の記録 (`A`キー) |
| **`SELECT_PLAN`** | `sapnet()` による知識決定直後 | 活性化拡散後の活性値分布と最終選択知識 `plan` の記録 (`P`キー) |
| **`WEIGHT_UPDATE`** | 重み調整直後 | 正・負の転移評価反映後の新しい結合重み行列の記録 (`W`キー) |

---

## 7. 生成ログのビューアーでの閲覧・分析フロー

シミュレーション完了後、出力された実験ログフォルダを **SAP-net Visualizer**（可視化ビューアー）で開いて再生・分析します。

### 1. ビューアーの起動
* **インストーラー版（Windows）**: デスクトップの `SAP-net-Visualizer` ショートカットを起動。
* **Pythonスクリプト版**: ビューアー環境にて `python main.py` を実行。

### 2. ログフォルダの選択
* 起動時に表示されるフォルダ選択ダイアログ（または `O` キー）で、シミュレーションが出力した実験フォルダ（例: `experiment_logs/20260821_120000_exp1/`）を選択します。

### 3. 主な操作方法・キーボードショートカット一覧

| キー | 機能 | 説明 |
| :--- | :--- | :--- |
| **`Space`** | 再生 / 一時停止 | 時系列フレームを自動連続再生 |
| **`←` / `→`** | 1ステップ コマ戻し / コマ送り | 1フレーム単位の詳細精査 |
| **`E` / `Shift+E`** | 次 / 直前 のエピソードへジャンプ | エピソード先頭へ即座に移動 |
| **`P` / `Shift+P`** | 次 / 直前 の知識選択へジャンプ | `SELECT_PLAN` イベントへジャンプ |
| **`A` / `Shift+A`** | 次 / 直前 の活性化へジャンプ | `ACTIVATION` イベントへジャンプ |
| **`W` / `Shift+W`** | 次 / 直前 の重み更新へジャンプ | `WEIGHT_UPDATE` イベントへジャンプ |
| **`G`** | 画面モード切替 | ステップ表示 ⇄ 活性値推移折れ線グラフ |
| **`S`** | グラフ画像保存 | 折れ線グラフ画面で高解像度PNG画像をエクスポート |
| **`C`** | 設定確認ダイアログ | `config_used_*.yaml` のパラメータ一覧を日本語解説付きで表示 |
| **`O`** | フォルダを開く | 別の実験ログフォルダを選択してロード |
| **`H` / `Esc`** | ヘルプ表示 | 画面の見方・操作ガイドオーバーレイの表示 |

---

## 8. パフォーマンス最適化と安定設計のポイント

1. **オンメモリバッファリングとエピソード別メモリ解放 (`flush_episode`)**:
   - 各ステップでのディスクI/Oを行わず、エピソード終了時に一括して gzip 圧縮追記保存するため、シミュレーション計算FPSへの影響がゼロです。
   - `flush_episode(clear_memory=True)` により、何千エピソードの長期学習でもメモリ使用量が一定に保たれます。
2. **安全な追記型 gzip ストリーム (Multi-stream gzip)**:
   - gzip 規格（RFC 1952）に準拠した追記ストリーム出力を行うため、シミュレーションが途中で強制中断（Ctrl+C等）された場合でも、中断直前エピソードまでのログが破損なくディスク上に保護されます。
3. **クラウドストレージ同期ロックの回避**:
   - Google Drive 等の同期フォルダにログを出力する場合でも、各エピソード終了時の一括追記保存のためファイルロック競合が発生しません。

---

## 9. トラブルシューティング ＆ FAQ

### Q1. シミュレーションの実行速度（FPS）を落とさずにログを保存できるか？
- はい。`SAPLogger` は各ステップで軽量なオンメモリバッファリングを行い、エピソード終了時に `flush_episode()` で一括追記するため、計算速度への影響は極めて軽微（ほぼゼロ）です。

### Q2. ビューアーの「設定確認（`C`キー）」にパラメータが表示されない
- ログフォルダ内に `config_used_<timestamp>.yaml` が正しく出力されているか確認してください（Step 6 参照）。シミュレーション開始時に設定辞書を YAML として保存することで、ビューアーが自動認識して日本語付きで一覧表示します。

### Q3. シミュレーションが途中で強制終了（Ctrl+C）した場合、ログは壊れないか？
- 壊れません。`flush_episode()` によって直前エピソードまでのデータがすでにディスク上の `.jsonl.gz` に安全に書き込まれているため、直前エピソードまでのログをビューアーで正常に再生できます。

---

## 10. 関連ドキュメント

* **[`DATA_FORMAT.md`](DATA_FORMAT.md)**: ログファイル（JSON Lines）および設定YAMLの詳細データ構造仕様書

