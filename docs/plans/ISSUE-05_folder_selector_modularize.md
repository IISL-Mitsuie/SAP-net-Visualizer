# [ISSUE-05] `folder_selector_gui.py` の責務分離リファクタリング（履歴管理・更新ダイアログの分割）

| 項目 | 内容 |
| :--- | :--- |
| 優先度 | **P1** |
| 種別 | refactor |
| 規模 | S〜M |
| 依存 | ISSUE-03 |
| 対象ファイル | `sap_visualizer/folder_selector_gui.py`, （新規）`sap_visualizer/history_manager.py`, （新規）`sap_visualizer/update_dialog.py`, `sap_visualizer/__init__.py`, `tests/test_folder_selector.py`, `tests/test_history_manager.py`, `tests/test_updater.py` |
| ブランチ名 | `agy/issue-05-folder-selector-modularize` |

---

## 1. 背景・現状の課題

- `sap_visualizer/folder_selector_gui.py` は **1,340行（約50KB）** に肥大化しており、以下の 3 つの全く異なる責務が 1 ファイルに混在している:
  1. `FolderHistoryManager`: 履歴の JSON 永続化と LRU 管理（GUI 非依存の純粋なロジック）。
  2. `UpdateDialog`: GitHub Releases からの更新案内・プログレス付きインストーラーダウンロード（アップデート専用 Tkinter UI）。
  3. `FolderSelectorDialog` / `select_simulation_folder`: フォルダ一覧テーブル・ツリービュー・パス選択（フォルダ選択専用 Tkinter UI）。
- この混在により、単体テストで `FolderHistoryManager` を使うだけでも GUI 関連の巨大なモジュールが読み込まれ、保守性・可読性が低下している。

---

## 2. 目的

- 責務ごとに 3 ファイルへ分割し、コードの見通しと単体テスト容易性を向上させること。
- `from sap_visualizer import FolderHistoryManager, FolderSelectorDialog, select_simulation_folder` や、`sap_visualizer.folder_selector_gui` からの既存インポートを後方互換として完全に維持すること。

---

## 3. 作業手順

### 3.1 ファイルの新規作成とコード移動
1. **`sap_visualizer/history_manager.py` を新規作成**:
   - `FolderHistoryManager` クラスを移動する。
   - `tkinter` や UI ライブラリに依存しないクリーンなモジュールとする。
2. **`sap_visualizer/update_dialog.py` を新規作成**:
   - `UpdateDialog` クラスを移動する。
   - アップデート用 UI コンポーネントおよびダウンロードスレッド制御を集約する。
3. **`sap_visualizer/folder_selector_gui.py` のスリム化**:
   - `FolderSelectorDialog` および `select_simulation_folder` を残す。
   - 上記で切り出した `history_manager` と `update_dialog` をインポートして連携する。
   - 後方互換のため、`FolderHistoryManager` と `UpdateDialog` を `folder_selector_gui.py` からも再エクスポートする:
     ```python
     from .history_manager import FolderHistoryManager
     from .update_dialog import UpdateDialog
     ```

### 3.2 パッケージエントリーポイントの整合
4. `sap_visualizer/__init__.py` でインポート元を整理し、`__all__` に含まれるシンボルが従来どおり利用できることを確認する。

### 3.3 単体テストのパス確認
5. `tests/test_history_manager.py`, `tests/test_folder_selector.py`, `tests/test_updater.py` を実行し、インポートエラーや動作不整合がないことを検証する。

---

## 4. 完了条件

- [x] `FolderHistoryManager` が `sap_visualizer/history_manager.py` に分離され、Tkinter なしでも import 可能なこと
- [x] `UpdateDialog` が `sap_visualizer/update_dialog.py` に分離されていること
- [x] `folder_selector_gui.py` の行数が大幅に削減（1343行 → 830行に削減）されていること
- [x] `from sap_visualizer import FolderHistoryManager, FolderSelectorDialog` や `from sap_visualizer.folder_selector_gui import FolderHistoryManager` が従来どおり動作すること
- [x] `check.bat` がすべて成功すること

---

## 5. やらないこと

- Tkinter ウィジェットの配置・デザイン・配色の変更
- フォルダ履歴 JSON フォーマットの変更
