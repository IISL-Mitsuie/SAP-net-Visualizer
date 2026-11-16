# [ISSUE-10] 実験設定ファイル（`config_used_*.yaml`）の読み込み耐性強化・閾値抽出精度向上

| 項目 | 内容 |
| :--- | :--- |
| 優先度 | **P0**（実験設定モーダル表示失敗および活性化閾値未反映の解消） |
| 種別 | bug / enhancement |
| 規模 | S |
| 依存 | なし |
| 対象ファイル | `sap_visualizer/config_loader.py`, `sap_visualizer/views/overlays.py`, `tests/test_config_loader.py`, `tests/test_logger.py` |
| ブランチ名 | `fix/config-loader-yaml-compat` |

---

## 1. 背景・現状の課題

[reference/config_used_20261109_222837.yaml](reference/config_used_20261109_222837.yaml)（Robotino RL Controller 継続学習設定ファイル）を現行の [sap_visualizer/config_loader.py](sap_visualizer/config_loader.py) で読み込むと解析に失敗し、ハイパーパラメータ一覧モーダル（`C` キー）および活性化閾値（`sap.threshold`）の自動適用が機能しない。調査の結果、以下の 4 点の課題が特定された。

1. **ダブルクォート文字列内の未エスケープ Windows パス区切り（`\`）による `yaml.scanner.ScannerError` と制御文字化け**:
   - `continual_learning.policy.files`（121〜125行目）において、Windows のファイルパスがダブルクォート囲みで記述されている:
     ```yaml
     - "output_robotino_rl_control\S-SAP_continual\output_20261109_222837\acquired_policies_20261109_222837\policy_task1.npy"
     ```
   - YAML 仕様ではダブルクォート内（`"..."`）の `\` はエスケープ文字として扱われるため、`\S`, `\o`, `\p` 等で `yaml.scanner.ScannerError: found unknown escape character 'S'` が発生し、YAML 全体のロードが `None`（失敗）となる。
   - また、未知のエスケープ文字だけを置換する方式では、パス内の `\a`（`\acquired_policies_...`）や `\t`（`\task1.npy`）、`\n`, `\r`, `\b` 等が YAML の有効なエスケープシーケンス（ASCII BEL `\x07`、タブ `\t`、改行 `\n` 等）として誤変換され、パス文字列が破損・文字化けする。
2. **`get_config_threshold()` における別用途 `*_threshold` パラメータの誤検出リスク**:
   - [reference/config_used_20261109_222837.yaml](reference/config_used_20261109_222837.yaml) には `"threshold"` を含むキーが複数存在する:
     - `environment.goal_distance_thresholds: [0.5, 4.0, 7.5, 11.0]`
     - `reward.near_wall_threshold: 0.5`
     - `sap.threshold: 0.20`（本来の SAP 活性化閾値）
     - `sap.q_span_threshold: 0.5`（同一 `sap` セクション内の別閾値）
     - `runtime.stuck_intervention_threshold: 100`
     - `continual_learning.convergence.success_rate_threshold: 1.0`
     - `continual_learning.convergence.max_step_threshold: null` / `std_step_threshold: null`
   - 現行の [sap_visualizer/config_loader.py](sap_visualizer/config_loader.py) L57 は `if "THRESHOLD" in k_str:`（部分一致）で判定しているため、キーの出現順序やセクション構成によって `q_span_threshold`（`0.5`）や `near_wall_threshold`（`0.5`）、`stuck_intervention_threshold`（`100.0`）を活性化閾値として誤取得する危険がある。
3. **対象 YAML ファイルのパス解決・タイムスタンプ照合の不足**:
   - 現行の `load_raw_config(log_file_path)` は常に `os.path.dirname(os.path.abspath(log_file_path))` の `os.listdir` 先頭要素 `yaml_files[0]` を返すため、複数 `config_used_*.yaml` がある場合にログファイルと同じタイムスタンプの設定ファイルや最新ファイルが確実に選ばれず、また `.yaml` ファイルパスやディレクトリパスを直接渡した場合にも対応していない。
4. **小文字キーや空文字列 `""` の表示整形・色分けの不整合**:
   - [sap_visualizer/views/overlays.py](sap_visualizer/views/overlays.py) L130 の数値色分け判定が `"THRESHOLD" in key_str or "REWARD" in key_str` と大文字固定になっているため、`threshold` や `reward_goal` のような小文字スネークケースのキーにハイライト色が適用されない。
   - [sap_visualizer/config_loader.py](sap_visualizer/config_loader.py) の `_format_yaml_value` において、明示的な空文字列 `""`（例: `reuse_policy_prefix: ""`）が `null`（`None`）と同じ `"-"`（`"none"` 型）に変換され、未設定（`null`）と空文字指定（`""`）が区別できない。

---

## 2. 目的

- ダブルクォート内に Windows パス（未エスケープの `\`）を含む `config_used_*.yaml` をエラーや制御文字化けなしに確実に読み込めること。
- 複数の `*_threshold` キーが存在する設定ファイルから、SAP 活性化閾値（`sap.threshold` / `threshold`）のみを正確に抽出できること。
- ログファイルに対応する `config_used_<timestamp>.yaml`（または最新の `config_used*.yaml`）、および直接指定された YAML / ディレクトリパスを適切に解決できること。
- 小文字キー・ネスト構造・2次元リスト・空文字列 `""`・`null` をハイパーパラメータ一覧モーダル（`C` キー）で視認性良く正確に表示できること。

---

## 3. 作業手順

### 3.1 YAML テキスト前処理（Windows バックスラッシュ安全化）の実装 (`sap_visualizer/config_loader.py`)
1. [sap_visualizer/config_loader.py](sap_visualizer/config_loader.py) に `_sanitize_yaml_text(yaml_text: str) -> str` を追加する:
   - 行内のダブルクォート文字列リテラル `r'"((?:\\.|[^"\r\n\\])*)"'` に対して、内部の `\\`（エスケープ済みバックスラッシュ）と `\"`（エスケープ済みクォート）は維持しつつ、それ以外の単独の `\x` を `\\x` に正規化する:
     ```python
     def _sanitize_yaml_text(yaml_text: str) -> str:
         """
         ダブルクォート文字列内の未エスケープバックスラッシュ（Windowsパス等）を \\ に正規化する。
         既存の \\ や \" は二重エスケープしない。
         """
         def _fix_dq(match: re.Match) -> str:
             content = match.group(1)
             fixed = re.sub(
                 r'\\(.)',
                 lambda m: m.group(0) if m.group(1) in ('\\', '"') else '\\\\' + m.group(1),
                 content,
             )
             return f'"{fixed}"'

         return re.sub(r'"((?:\\.|[^"\r\n\\])*)"', _fix_dq, yaml_text)
     ```
2. `load_raw_config` でファイルを読み込む際、`_sanitize_yaml_text` を適用したテキストを `yaml.safe_load` に渡す（万一例外が発生した場合は生テキストでの `yaml.safe_load` もフォールバック試行する）。

### 3.2 設定 YAML ファイル探索・パス解決の改善 (`sap_visualizer/config_loader.py`)
3. `_resolve_config_yaml_path(log_file_path: Optional[str]) -> Optional[str]` を実装する:
   - `log_file_path` が存在しない場合は `None` を返す。
   - `log_file_path` がファイルであり、拡張子が `.yaml` または `.yml` の場合はその絶対パスをそのまま返す。
   - `log_file_path` がディレクトリならそのディレクトリ、それ以外のファイルなら親ディレクトリを `log_dir` とする。
   - `log_dir` 直下の `config_used*.yaml` / `config_used*.yml` を収集する。
   - `log_file_path` のファイル名からタイムスタンプ（例: `r'(\d{8}_\d{6})'`）が抽出でき、同じタイムスタンプを含む候補ファイルがあればそれを最優先で選択する。
   - 該当がない場合は、候補ファイルのうち更新日時（`os.path.getmtime`）が最新のものを選択する。
4. `load_raw_config` および `load_config_data` のエラーハンドリングで `_resolve_config_yaml_path` を共通利用する。

### 3.3 `get_config_threshold()` の探索精度向上 (`sap_visualizer/config_loader.py`)
5. `get_config_threshold(log_file_path)` の探索ロジックを以下のように修正する:
   - 数値変換ヘルパー `_to_valid_float(val: Any) -> Optional[float]` を用意し、`isinstance(val, bool)` や `val is None`、`list` / `dict` を除外したうえで `float(val)` を返す。
   - **第1優先**: 最上位の `SAP` セクション（`k.upper() == "SAP"`）の辞書内で、キー名の大文字表記が `("THRESHOLD", "ACTIVATION_THRESHOLD", "SAP_THRESHOLD")` に完全一致する項目を探す。
   - **第2優先**: 設定全体を再帰探索し、キー名の大文字表記が `("THRESHOLD", "ACTIVATION_THRESHOLD", "SAP_THRESHOLD")` に完全一致する項目を探す。
   - これにより `q_span_threshold` や `near_wall_threshold`、`stuck_intervention_threshold`、`goal_distance_thresholds` 等の誤検出を防ぐ。

### 3.4 値フォーマットとオーバーレイ色分けの改善 (`sap_visualizer/config_loader.py`, `sap_visualizer/views/overlays.py`)
6. [sap_visualizer/config_loader.py](sap_visualizer/config_loader.py) の `_format_yaml_value(val: Any)` において:
   - `val == ""`（空文字列）の場合は `return '""', "str"` を返し、`None`（`"-", "none"`）と明確に区別できるようにする。
7. [sap_visualizer/views/overlays.py](sap_visualizer/views/overlays.py) の `draw_config_overlay`（L129-130付近）において:
   - キー名を大文字化した `key_upper = key_str.upper()` を用いて判定し、小文字キー（`threshold`, `reward_goal` 等）でも大文字キーと同様に色分けされるようにする。

### 3.5 単体テストの追加 (`tests/test_config_loader.py`, `tests/test_logger.py`)
8. [tests/test_config_loader.py](tests/test_config_loader.py) に以下のテストケースを追加する:
   - [reference/config_used_20261109_222837.yaml](reference/config_used_20261109_222837.yaml) と同等の構造（ダブルクォート内の Windows パス `\S-SAP_continual\...\acquired_policies_...\policy_task1.npy`、小文字セクション・キー、2次元リスト `goal_list`、空文字列 `""`、`null`、複数の `*_threshold` キー）を持つ YAML の読み込みテスト。
   - `\a` や `\t` を含む Windows パス文字列が制御文字（`\x07` やタブ）に化けず、そのまま文字列として取得できることの検証。
   - `sap` セクション内に `q_span_threshold: 0.5` が `threshold: 0.20` より先に定義されていても、また他セクションに `near_wall_threshold: 0.5` 等があっても、`get_config_threshold` が正確に `0.20` を返すことの検証。
   - YAML ファイルパス直接指定・ディレクトリパス指定・タイムスタンプ一致ファイルの優先選択の検証。
9. [tests/test_logger.py](tests/test_logger.py) に、Windows パス入り `config_used_*.yaml` が存在するフォルダを `SAPVisualLogger.load_from_folder` で読み込んだ際、`config_threshold` が `0.20` になる統合テストを追加する。

---

## 4. 完了条件

- [x] ダブルクォート内に未エスケープの Windows パス（`\S`, `\o`, `\a`, `\p`, `\t` 等）を含む YAML が `ScannerError` や文字化けを起こさず `load_raw_config` / `load_config_data` で正常に読み込めること
- [x] [reference/config_used_20261109_222837.yaml](reference/config_used_20261109_222837.yaml) に対して `load_config_data` が `yaml_loaded=True` を返し、全 10 セクション（`META`, `MODE`, `GIT`, `CONTROL`, `ENVIRONMENT`, `REWARD`, `QLEARNING`, `SAP`, `RUNTIME`, `CONTINUAL_LEARNING`）が展開されること
- [x] 複数の `*_threshold`（`q_span_threshold`, `near_wall_threshold`, `stuck_intervention_threshold` 等）が含まれる設定から、`get_config_threshold` が `sap.threshold`（`0.20`）を正確に返すこと
- [x] 空文字列 `""` が `"-"`（`none`）に潰されず `'""'` として整形され、`null`（`-`）と区別されること
- [x] 小文字キーの YAML でも `OverlaysView` の数値ハイライト判定が機能すること
- [x] `check.bat`（`ruff check` + `pytest`）がすべてパスすること

---

## 5. やらないこと

- シミュレーション側（YAML 出力元プログラム）のコード変更や、元の `config_used_*.yaml` ファイル自体の書き換え
- ハイパーパラメータ一覧モーダル（`OverlaysView`）の2カラムUIレイアウト自体の変更や編集機能の追加
- 新規外部ライブラリの追加（既存の `PyYAML` と標準ライブラリのみで実装する）

---

## 6. 質問・未決事項（既定値）

- 特になし（上記仕様で自己完結して実装可能）
