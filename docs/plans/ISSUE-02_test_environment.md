# [ISSUE-02] テスト環境の整備・本番環境（履歴・通信・実画面）からの分離と高速化

| 項目 | 内容 |
| :--- | :--- |
| 優先度 | **P0**（以降のすべての変更検証・品質ゲートの前提） |
| 種別 | test |
| 規模 | S |
| 依存 | なし |
| 対象ファイル | （新規）`requirements-dev.txt`, （新規）`pyproject.toml`, （新規）`tests/conftest.py`, `sap_visualizer/folder_selector_gui.py`, `tests/test_visualizer_gui.py`, `tests/test_integration.py`, `tests/test_updater.py`, `tests/test_folder_selector.py` |
| ブランチ名 | `agy/issue-02-test-environment` |

---

## 1. 背景・現状の課題

2026-11-15 時点でのテスト実行において、以下の 4 点の構造的課題が存在する。

1. **実行時間の遅延（全41件で約66秒）と画面ポップアップ**:
   - `tests/test_visualizer_gui.py` や `tests/test_integration.py` で `SDL_VIDEODRIVER=dummy` が設定されていない箇所があり、テスト実行中に実画面にウィンドウが点滅・ポップアップして開発者の操作を阻害する。
   - テスト完了後に `pygame.quit()` が呼ばれないケースがあり、プロセスやドライバリソースの解放待ちで無駄な待機時間が発生している。
2. **本番ユーザー履歴ファイルへの読み書き**:
   - `FolderHistoryManager` のデフォルトコンストラクタ（`tests/test_updater.py` 等で引数なしで生成される場合）が、実環境のユーザーホームディレクトリ（`~/.sap_visualizer/folder_history.json`）を直接読み書きしている。
   - テストを実行するたびに、開発者の実アプリのフォルダ選択履歴が上書き・消去されるリスクがある。
3. **テスト中の外部ネットワーク通信（GitHub API）**:
   - `tests/test_folder_selector.py` 等で `FolderSelectorDialog` を生成した際、バックグラウンドスレッドで本物の GitHub Releases API（`check_for_updates_async`）へリクエストが飛んでいる。
   - オフライン時や GitHub API レートリミット時にテストが不安定化（flaky）する原因となる。
4. **開発用依存（dev dependencies）の宣言欠落**:
   - `pytest` や `ruff` 等の開発・テストツールが依存ファイルに定義されておらず、新しい環境で再現性のあるテスト実行ができない。

---

## 2. 目的

- `pip install -r requirements-dev.txt` → `pytest` により、**1コマンドで全テストが画面表示なし・数秒以内**で完結すること。
- テスト実行によって本番の設定・履歴ファイル（`~/.sap_visualizer/`）が一切変更されないこと。
- テスト実行中に外部ネットワーク（GitHub API 等）への通信が完全に遮断・モック化されていること。

---

## 3. 作業手順

### 3.1 依存・設定ファイルの新規作成
1. `requirements-dev.txt` を新規作成する:
   ```text
   -r requirements.txt
   pytest>=8.0
   ruff>=0.6
   ```
2. `pyproject.toml` を新規作成する:
   ```toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   addopts = "-ra -q"
   ```

### 3.2 設定・履歴ディレクトリの環境変数分離
3. `sap_visualizer/folder_selector_gui.py`（または `FolderHistoryManager.__init__`）で、設定保存先ディレクトリを環境変数 `SAP_VISUALIZER_CONFIG_DIR` で上書き可能にする:
   ```python
   config_dir = os.environ.get(
       "SAP_VISUALIZER_CONFIG_DIR",
       os.path.join(os.path.expanduser("~"), ".sap_visualizer")
   )
   ```

### 3.3 `tests/conftest.py` による自動分離フィクスチャの実装
4. `tests/conftest.py` を新規作成し、セッション開始時に以下を設定する:
   - 環境変数の設定:
     ```python
     os.environ["SDL_VIDEODRIVER"] = "dummy"
     os.environ["SDL_AUDIODRIVER"] = "dummy"
     ```
   - 一時設定ディレクトリの適用（`autouse=True`）:
     各テストセッションごとに `tmp_path_factory` で作成した一時ディレクトリを `SAP_VISUALIZER_CONFIG_DIR` に指定し、本番の `~/.sap_visualizer` を完全保護する。
   - 外部通信のモック化（`autouse=True`）:
     `sap_visualizer.updater.fetch_latest_release_info` および `check_for_updates_async` を安全なダミー（または即時コールバック・通信なし）でモックし、テスト中の実通信を防止する。
   - 各テスト終了時（teardown）に `pygame.quit()` を呼び出し、リソースを確実・即時に解放する。

### 3.4 既存テストスイートの調整
5. `tests/test_visualizer_gui.py`, `tests/test_integration.py` などの既存テスト内で重複している `SDL_VIDEODRIVER` 設定を整理し、`pytest` 実行時にすべて高速に通過することを確認する。

---

## 4. 完了条件

- [x] 新規環境で `pip install -r requirements-dev.txt` 後、`python -m pytest` が **全件 pass（0 failure, 0 error）** になること
- [x] テスト実行時間が **5秒以内**（従来の 66 秒から大幅短縮）になること
- [x] テスト実行中に Pygame ウィンドウが一切画面にポップアップしないこと
- [x] テスト実行前後で `~/.sap_visualizer/folder_history.json` の内容・タイムスタンプが一切変更されないこと
- [x] ネットワーク切断状態（オフライン環境）でも全テストが安定して通過すること

---

## 5. やらないこと

- テストケースの大規模な削減や仕様変更（既存の検証カバレッジはすべて維持する）
- PySide6 / pytest-qt 等の新規 GUI テストフレームワークの導入
- GitHub Actions CI ワークフローの作成
