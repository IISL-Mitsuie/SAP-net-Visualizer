# [ISSUE-04] 描画ループ内の同期 I/O 排除（設定モーダル YAML キャッシュ化とフレーム解決の O(1) 化）

| 項目 | 内容 |
| :--- | :--- |
| 優先度 | **P1** |
| 種別 | perf |
| 規模 | S |
| 依存 | ISSUE-03（品質ゲートの適用） |
| 対象ファイル | `sap_visualizer/views/overlays.py`, `sap_visualizer/sap_visual_logger.py`, `tests/test_logger.py`, `tests/test_visualizer_gui.py` |
| ブランチ名 | `agy/issue-04-draw-loop-perf` |

---

## 1. 背景・現状の課題

1. **設定確認モーダル（`C` キー）表示中の毎フレーム同期ディスク I/O**:
   - `sap_visualizer/views/overlays.py` L60: `draw_config_overlay()` の内部で、描画フレームごと（30 FPS の場合、**毎秒 30 回**）に `load_config_data(log_file_path)` を直接呼び出している。
   - `load_config_data` はディスク上の `os.listdir`、`yaml.safe_load`、再帰的な辞書平坦化処理を実行するため、Google ドライブ等の同期ストレージ上では著しい FPS 低下やカクつき（ラグ）を発生させている。
2. **`resolve_frame()` による過去方向への線形探索**:
   - `sap_visualizer/sap_visual_logger.py` L172-L247: `resolve_frame(index)` は、活性値・重み・選択知識の欠損を補うため `for k in range(index - 1, -1, -1):` で毎回過去フレームへ向かってループ探索している。
   - 長大なログでスライダーを高速シークしたり、折れ線グラフ描画で複数フレームを連続解決する際に最悪 $O(N)$ の探索コストが累積する。

---

## 2. 目的

- 設定モーダル表示中であってもディスク I/O や YAML 解析をフレームごとに走らせず、滑らかに 30/60 FPS で動作すること。
- `resolve_frame(index)` の呼び出しコストを $O(1)$ 化し、数十万フレームの長大ログでもシーク操作が即応すること。
- 表示内容やフォールバック結果は従来と 100% 同一であること。

---

## 3. 作業手順

### 3.1 `OverlaysView` における YAML 設定データのキャッシュ化
1. `sap_visualizer/views/overlays.py` の `OverlaysView` にキャッシュ用インスタンス変数を追加する:
   ```python
   self._cached_config_path: Optional[str] = None
   self._cached_config_items: List[Dict[str, Any]] = []
   self._cached_yaml_loaded: bool = False
   ```
2. `draw_config_overlay()` 内で、`log_file_path != self._cached_config_path` または未ロードの場合にのみ `load_config_data(log_file_path)` を呼び出してキャッシュを更新し、以降のフレームはキャッシュされた `self._cached_config_items` を描画する。
3. 外部から明示的にキャッシュをクリアできるように `clear_config_cache()` メソッドを提供する。

### 3.2 `SAPVisualLogger` における確定情報の事前フォワードフィル / キャッシュ化
4. `sap_visualizer/sap_visual_logger.py` に `_resolved_cache: List[Optional[ResolvedFrameInfo]]` または事前解決リストを追加する。
5. ログ読み込み完了時（`_update_metadata_cache` 内など）、先頭から順に 1 パス（$O(N)$）走査することで直前の確定状態を保持しながら全フレームの `ResolvedFrameInfo` を事前計算・配列格納する（または必要時に計算して配列へメモ化する）。
6. `resolve_frame(index)` はキャッシュ配列から $O(1)$ で直接 `ResolvedFrameInfo` を返すように変更する。

### 3.3 テストによる検証
7. `tests/test_logger.py` で、キャッシュ導入前後で `resolve_frame` の返却内容が同一であることを確認する回帰テストを追加。
8. `tests/test_visualizer_gui.py` で、設定モーダルを複数回描画しても `load_config_data` の呼び出し回数が増加しないことをモック検証。

---

## 4. 完了条件

- [ ] 設定確認モーダル（`C` キー）を開いている間、`load_config_data` がフレームごとに呼ばれず、初回読み込み時（またはファイルパス変更時）の 1 回のみ呼ばれること
- [ ] `resolve_frame(index)` が $O(1)$ で高速に確定フレーム情報を返すこと
- [ ] 欠損値を含むログにおいて、修正前後で `resolve_frame` の出力結果が完全に一致すること
- [ ] `check.bat` がすべて成功すること

---

## 5. やらないこと

- YAML 設定項目の編集・保存機能（閲覧専用のまま維持）
- 活性値の平滑化やダウンサンプリングアルゴリズムの変更
