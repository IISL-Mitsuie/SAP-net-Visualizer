# [ISSUE-01] 不具合修正（更新ダイアログの未定義変数・ログパース耐障害性・折れ線グラフ欠損値・フォルダ切替リセット）

| 項目 | 内容 |
| :--- | :--- |
| 優先度 | **P0**（アプリケーションのクラッシュ・データ欠落・表示不具合の直接修正） |
| 種別 | bug |
| 規模 | S |
| 依存 | なし |
| 対象ファイル | `sap_visualizer/folder_selector_gui.py`, `sap_visualizer/models.py`, `sap_visualizer/sap_visual_logger.py`, `sap_visualizer/views/chart_view.py`, `sap_visualizer/sap_visualizer_gui.py`, `tests/test_folder_selector.py`, `tests/test_logger.py`, `tests/test_visualizer_gui.py` |
| ブランチ名 | `agy/issue-01-bug-fixes` |

---

## 1. 背景・現状の課題

実機検証および静的解析により、以下の 4 点の不具合が特定されている。

1. **更新ダイアログにおける未定義変数例外（2箇所）**:
   - `sap_visualizer/folder_selector_gui.py` L466-L468: `except Exception as e:` 内で `self.dialog.after(0, lambda: self._on_download_failed(str(e)))` を呼び出している。Python 3 の仕様上、`except` 節を抜けると例外オブジェクト変数 `e` がスコープから削除されるため、後からメインスレッドでコールバックが呼ばれた際に `NameError: free variable 'e' referenced before assignment` でクラッシュし、失敗ダイアログが表示されない。
   - `sap_visualizer/folder_selector_gui.py` L516: `_open_installer_folder()` 内で `subprocess.Popen` を呼んでいるが、同モジュールで `subprocess` がインポートされておらず `NameError: name 'subprocess' is not defined` でフォルダが開けない。
2. **JSONL パース時の例外による後続フレーム全欠落**:
   - `sap_visualizer/models.py` L35-L45: JSONL 行に `"threshold": null` や `"plan": null` 等の欠損・不正値が含まれていた場合、`float(data.get("threshold", DEFAULT_THRESHOLD))` の呼び出しで `TypeError: float() argument must be a string or a real number, not 'NoneType'` が発生する。
   - `sap_visualizer/sap_visual_logger.py` L98-L105: これが `load_from_file` の内側ループの広域 `except Exception as err:` で捕捉され、「圧縮ストリームの終端・破損」とみなされて `break` してしまい、その行以降に存在する正常なフレームがすべて読み込まれずに切り捨てられる。
3. **折れ線グラフでの欠損フレーム急落と画像エクスポート時の閾値線漏れ**:
   - `sap_visualizer/views/chart_view.py` L238-L243: `WEIGHT_UPDATE` や `SELECT_PLAN` 等で `A: []` のフレームが存在する場合、ステップ表示画面では直前の確定情報から活性値を取得するのに対し、折れ線グラフ画面では `0.0` としてプロットするため、重み更新フレームの箇所で折れ線が `0.0` へ垂直に急落する。
   - `sap_visualizer/views/chart_view.py` L291-L365: `export_chart_surface`（`S` キーによる画像保存）において、画面上にはある「活性化閾値線（赤破線およびラベル）」のプロット処理が漏れており、保存画像に閾値線が出力されない。
4. **フォルダ再選択（`O` キー）時の状態リセット不備**:
   - `sap_visualizer/sap_visualizer_gui.py` L456-L465: 初回起動時は手動探索モード（`live_follow = False`）で先頭フレーム（0）から閲覧できるのに対し、`O` キーで別フォルダを選択すると `self.live_follow = True` に設定され、直後の `update()` で最終フレームへ強制スクロールしてしまう。
   - また、`chart_view.visible_nodes` やスクロールオフセット、再生状態（`is_playing`）が初期化されず、前回の実験の表示状態が引き継がれてしまう。

---

## 2. 目的

- インストーラーダウンロード失敗時およびフォルダ表示時に `NameError` が発生せず、適切なダイアログと動作を提供すること。
- 不正値や欠損値を含むログ行があっても、その行のみを安全にスキップ（またはデフォルト補完）し、後続の有効フレームを正常にすべてロードできること。
- 折れ線グラフにおいて重み更新フレームでも滑らかに推移が表示され、保存画像にも活性化閾値線が正しく描画されること。
- フォルダ再選択時に初期状態（手動探索モード・先頭フレーム・停止状態・フィルター初期化）に確実にリセットされること。

---

## 3. 作業手順

### 3.1 `folder_selector_gui.py` の NameError 解消
1. `sap_visualizer/folder_selector_gui.py` の先頭インポートに `import subprocess` を追加する。
2. `_start_download` のワーカー内例外処理を以下のように修正する:
   ```python
   except Exception as e:
       err_msg = str(e)
       logger.error(f"Download failed: {err_msg}")
       self.dialog.after(0, lambda msg=err_msg: self._on_download_failed(msg))
   ```

### 3.2 `models.py` と `sap_visual_logger.py` のパース耐障害性強化
3. `sap_visualizer/models.py` の `LogFrame.from_dict` で、`threshold` や各配列の `None` 安全性を徹底する:
   ```python
   thresh_val = data.get("threshold")
   try:
       threshold = float(thresh_val) if thresh_val is not None else DEFAULT_THRESHOLD
   except (ValueError, TypeError):
       threshold = DEFAULT_THRESHOLD
   ```
   `plan`, `reused_action` も `try-except` で安全に変換する。
4. `sap_visualizer/sap_visual_logger.py` の `load_from_file` で、各行のパースブロックを個別の `try-except` で保護し、特定行のパースエラー時は `logger.warning` を出してその行のみをスキップし、後続行の読み込み（`while True` ループ）を継続する。`break` するのは `gzip` ストリームの EOF/解凍破損時のみとする。

### 3.3 折れ線グラフの欠損値フォールバックと保存画像閾値線追加
5. `sap_visualizer/views/chart_view.py` の `draw()` および `export_chart_surface()` において、フレーム `idx` の活性値が空の場合は直前の有効フレームの活性値を参照（または `SAPVisualLogger.resolve_frame(idx).activations` を利用）してプロットする。
6. `export_chart_surface()` に、活性化閾値線（赤破線）および「活性化閾値 (0.XX)」のラベルテキスト描画を追加する（`draw()` の描画処理を共通化または同等処理を実装）。

### 3.4 フォルダ再選択時の初期化処理修正
7. `sap_visualizer/sap_visualizer_gui.py` の `open_folder_selector()` で、ログ読み込み成功時に以下を設定する:
   ```python
   self.current_index = 0
   self.live_follow = False  # 手動探索モードを維持
   self.is_playing = False
   self.chart_view.visible_nodes.clear()
   self.chart_view.filter_scroll_y = 0
   self.config_scroll_y = 0
   ```

### 3.5 テストの追加・検証
8. `tests/test_updater.py` または `tests/test_folder_selector.py` に、ダウンロード例外ハンドラおよびエクスプローラー起動メソッドの単体テストを追加。
9. `tests/test_logger.py` に、`"threshold": null` 等の欠損フィールドを含む行があってもファイル全体が読み飛ばされず正常フレームが取得できるテストを追加。
10. `tests/test_visualizer_gui.py` に、`O` キー後の状態初期化の検証テストを追加。

---

## 4. 完了条件

- [x] `_start_download` で例外が発生した際、`NameError` にならず `_on_download_failed` が正常に呼ばれること
- [x] `_open_installer_folder` が `NameError: name 'subprocess' is not defined` を起こさないこと
- [x] 不正行（`"threshold": null` 等）を含む JSONL を読み込んだ際、後続行が破棄されずに全正常行がロードされること
- [x] 重み更新イベント（`A: []`）が含まれるログでも折れ線グラフが `0.0` に落ちずに滑らかにプロットされること
- [x] `export_chart_surface` で保存された PNG サーフェスに活性化閾値線が含まれていること
- [x] フォルダ再選択後に `live_follow` が `False` のまま先頭フレームに留まり、表示設定がリセットされること
- [x] 既存のテストスイートがすべて通過すること

---

## 5. やらないこと

- GUI レイアウトやカラーテーマの大幅変更
- フォルダ履歴管理クラスのファイル分割（ISSUE-05 で実施）
- 自動アップデートの SHA-256 検証追加（ISSUE-08 で実施）
