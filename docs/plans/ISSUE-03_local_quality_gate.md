# [ISSUE-03] ローカル品質ゲート（`check.bat`：ruff + pytest）の導入と lint エラー解消

| 項目 | 内容 |
| :--- | :--- |
| 優先度 | **P1** |
| 種別 | quality |
| 規模 | S |
| 依存 | ISSUE-02（テスト環境・pytest が整っていること） |
| 対象ファイル | `pyproject.toml`, （新規）`check.bat`, （新規）`.githooks/pre-push`, `sap_visualizer/`, `main.py`, `packaging/`, `tests/` 全般の未使用 import 解消, `README.md` |
| ブランチ名 | `agy/issue-03-local-quality-gate` |

---

## 1. 背景・現状の課題

- 現在、静的解析ツールが導入されておらず、コード内に未使用インポートや未定義参照、構文的ミスが検出されないまま放置されている。
- `python -m ruff check --select F,E9` を実行すると、現時点で **33 件のエラー**（`F401`: 未使用インポート、`F821`: 未定義名）が検出される。
- 外部 CI サービス（GitHub Actions）を使わない方針のため、開発者や AI エージェントが手元で **1 コマンド** で品質を担保できる仕組み（`check.bat`）が必要である。

---

## 2. 目的

- `check.bat` を実行するだけで、`ruff` による静的チェックと `pytest` による全単体テストを連続実行し、成功（0）または失敗（1）を判定できること。
- 現存する 33 件の lint エラー（未使用インポート等）をすべて解消し、常に警告ゼロのクリーンな状態を維持すること。
- 必要に応じて `git push` 前に自動チェックできるフック（`pre-push`）を提供すること。

---

## 3. 作業手順

### 3.1 `pyproject.toml` への ruff 設定追加
1. `pyproject.toml` に以下の ruff 構成を追加する:
   ```toml
   [tool.ruff]
   target-version = "py311"
   line-length = 120
   extend-exclude = [
       "reference",
       "log_AI-output",
       "dist",
       "dist_installer"
   ]

   [tool.ruff.lint]
   select = ["F", "E9"]
   ```

### 3.2 既存の lint 指摘（33件）の修正
2. `python -m ruff check --select F,E9 sap_visualizer main.py packaging tests` を実行し、指摘を修正する:
   - **F401（未使用インポート）**: 削除する。
     - 例: `main.py` の `import pygame`
     - `sap_visualizer_gui.py` の `sys`, `List`, `SLIDER_MARGIN_X` 等
     - `views/chart_view.py`, `views/overlays.py`, `views/step_view.py` の未使用カラー定数や `List`, `Tuple`
     - `tests/test_updater.py` の `io`
     - ※ただし `__init__.py` のように意図的に再エクスポートしているものは `__all__` に含めるか `# noqa: F401` を付与して外部公開を崩さない。
   - **F821（未定義変数）**:
     - `folder_selector_gui.py` の `subprocess` および `e` の参照（ISSUE-01 で修正済みであることを確認）。

### 3.3 `check.bat` の新規作成
3. プロジェクトルートに `check.bat` を作成する:
   ```bat
   @echo off
   setlocal
   cd /d "%~dp0"
   set SDL_VIDEODRIVER=dummy
   set SDL_AUDIODRIVER=dummy
   set PYTHONUTF8=1

   echo [1/2] ruff check
   python -m ruff check --select F,E9 sap_visualizer main.py packaging tests
   if errorlevel 1 goto :fail

   echo [2/2] pytest
   python -m pytest -q
   if errorlevel 1 goto :fail

   echo.
   echo [OK] all checks passed
   exit /b 0

   :fail
   echo.
   echo [NG] checks failed
   exit /b 1
   ```

### 3.4 git pre-push フックの配置
4. `.githooks/pre-push` を新規作成する:
   ```sh
   #!/bin/sh
   cmd.exe //c check.bat
   ```
   README に `git config core.hooksPath .githooks` による有効化手順を記載する。

---

## 4. 完了条件

- [x] `check.bat` を実行し、`ruff check` と `pytest` が両方実行されて `[OK] all checks passed` で正常終了（終了コード 0）すること
- [x] `python -m ruff check --select F,E9 sap_visualizer main.py packaging tests` がエラー 0 件になること
- [x] 意図的に未使用インポートや構文エラーを混入させた場合に `check.bat` が検知して終了コード 1 で停止すること
- [x] 既存の全テストが通過すること

---

## 5. やらないこと

- `ruff format`（自動コードフォーマッタ）による大規模な差分発生（レビュー性を保つため実施しない）
- 複雑な型検査（mypy 等）の導入
- GitHub Actions CI ワークフローの追加
