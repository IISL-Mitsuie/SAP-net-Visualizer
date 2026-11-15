# [ISSUE-06] ロギング基盤の整備（配布版でのファイルログ保存と例外フック）

| 項目 | 内容 |
| :--- | :--- |
| 優先度 | **P1** |
| 種別 | quality |
| 規模 | S |
| 依存 | ISSUE-05 |
| 対象ファイル | （新規）`sap_visualizer/logging_setup.py`, `main.py`, `sap_visualizer/__init__.py`, （新規）`tests/test_logging_setup.py` |
| ブランチ名 | `agy/issue-06-logging` |

---

## 1. 背景・現状の課題

- 本アプリの Windows 配布版（PyInstaller `console=False`）では、コンソールウィンドウが開かないため、`print()` や標準ロガーの出力がすべて破棄される。
- `main.py` L9-L12 では GUI モード起動時に `sys.stdout = open(os.devnull, "w")`, `sys.stderr = open(os.devnull, "w")` で出力を完全に捨てている。
- 配布版アプリで不意のエラーやクラッシュが発生した場合に、**原因を特定するためのログやトレースバックが端末上のどこにも残らない**。
- `RL-Log-Comparator` の ISSUE-07 と同様に、ユーザー設定ディレクトリ配下に回転ファイルログ（`RotatingFileHandler`）を保持し、予期せぬ例外を記録する基盤が必要である。

---

## 2. 目的

- 配布版（`console=False`）であっても、起動情報・警告・エラー・未捕捉例外のスタックトレースが `%USERPROFILE%/.sap_visualizer/logs/app.log` に確実に記録されること。
- ログファイルの肥大化を防ぐため、容量制限（1MB × 3世代）による自動ローテーションを行うこと。
- 開発時のコンソール実行時は、標準出力とファイル出力の双方が利用できること。

---

## 3. 作業手順

### 3.1 `sap_visualizer/logging_setup.py` の新規作成
1. `sap_visualizer/logging_setup.py` を作成し、以下を提供する:
   - `get_log_dir() -> str`:
     環境変数 `SAP_VISUALIZER_CONFIG_DIR`（未指定時は `~/.sap_visualizer`）配下の `logs` フォルダパスを返し、存在しなければ作成する。
   - `setup_logging(level=logging.INFO) -> None`:
     ルートロガーに `RotatingFileHandler(app.log, maxBytes=1_000_000, backupCount=3, encoding="utf-8")` を登録。
     フォーマット: `"%(asctime)s [%(levelname)s] %(name)s: %(message)s"`
     `sys.stderr` が利用可能な場合は `StreamHandler` も追加する。
   - `install_exception_hooks() -> None`:
     `sys.excepthook` および `threading.excepthook` を登録し、捕捉されなかった例外を `logger.critical(..., exc_info=True)` で自動記録する。

### 3.2 `main.py` でのロギング初期化統合
2. `main.py` の `setup_logging()` を `sap_visualizer.logging_setup` の関数に差し替え、起動直後に `install_exception_hooks()` を適用する。
3. 起動時にバージョン番号、Python バージョン、OS 情報を 1 行ログ出力する。

### 3.3 単体テストの追加
4. `tests/test_logging_setup.py` を新規作成し、一時ディレクトリ下でログファイルが生成されること、未捕捉例外ハンドラがログに記録することを確認する。

---

## 4. 完了条件

- [x] アプリ起動時に `~/.sap_visualizer/logs/app.log`（または指定先）に起動ログが記録されること
- [x] ログファイルが 1MB を超過した際に自動でローテーション（世代管理）されること
- [x] スレッド内やメインループで未捕捉例外が発生した際に `app.log` にスタックトレースが記録されること
- [x] テスト環境（`conftest.py` の一時設定ディレクトリ）で本番のログファイルが汚染されないこと
- [x] `check.bat` がすべて成功すること

---

## 5. やらないこと

- 外部サーバーへのログ送信・テレメトリ機能（一切行わない）
- エラー発生時のクラッシュリポーター GUI の新設（ログ記録に留める）
