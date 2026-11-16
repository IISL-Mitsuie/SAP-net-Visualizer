# [ISSUE-09] ドキュメント（README.md 等）と実装の不整合解消

| 項目 | 内容 |
| :--- | :--- |
| 優先度 | **P2** |
| 種別 | docs |
| 規模 | S |
| 依存 | ISSUE-08（前段の変更内容をドキュメントに集約するため） |
| 対象ファイル | `README.md`, `DATA_FORMAT.md`, `main.py` docstring |
| ブランチ名 | `agy/issue-09-docs-cleanup` |

---

## 1. 背景・現状の課題

1. **画面操作・ボタン名と README の食い違い**:
   - `README.md` 内の操作説明表に記載されているボタン名（例: `[活性値推移(G)]` など）が、現在の GUI の実際のラベル（例: `グラフ画面 (G)`）と一部異なっている。
2. **新機能（設定画面動的パース・Linux基盤・品質ゲート）の記載漏れ**:
   - YAML 設定確認ダイアログがハードコードから汎用動的パース（2カラム表示）へ刷新された詳細がドキュメントに未反映である。
   - `run_linux.sh` や `run_docker.sh`、AppImage パッケージングなどの Linux 対応機能の簡単な概要がトップレベル README に反映されていない。
   - 開発者向けの `requirements-dev.txt`、`check.bat`（`ruff` + `pytest`）、`requirements-build.txt` によるビルド手順が書かれておらず、旧来の `requirements.txt` のみ記載されている。
3. **Python サポートバージョンの整合**:
   - バッジや記述が Python 3.8+ となっているが、Python 3.11 以上の構文やライブラリ環境に整合させる必要がある。

---

## 2. 目的

- `README.md` を読めば、現在のアプリケーションの機能・画面構成・操作ショートカット・ビルドおよびテスト手順を正確に把握できるようにすること。
- ドキュメント内の記述と実コードの動作仕様を 100% 一致させること。

---

## 3. 作業手順

### 3.1 操作説明および機能一覧の更新
1. `README.md` の「操作方法・キーボードショートカット」表を、現在の `sap_visualizer_gui.py` および `theme.py` の実画面ラベルと完全一致させる。
2. ハイパーパラメータ設定画面（`C` キー）について、実験 YAML（`config_used_*.yaml`）のセクションを動的展開する仕様を正確に説明する。

### 3.2 開発者向け・ビルド手順の拡充
3. `README.md` の「必要要件」を更新（Python 3.11 以上、実行時依存とビルド時依存の分離）。
4. 「テスト・品質ゲート」セクションを追加:
   - `pip install -r requirements-dev.txt`
   - `check.bat`（または `pytest`）の実行手順
   - 任意の git pre-push フック（`git config core.hooksPath .githooks`）の説明
5. 「Windows インストーラービルド」および「Linux 実行環境」セクションを最新のビルド体系（`requirements-build.txt`, `build_all.bat`, `run_linux.sh`, `run_docker.sh`）に合わせて更新する。

### 3.3 データ仕様書の整合
6. `DATA_FORMAT.md` および `main.py` の docstring を確認し、最新のログフォーマット仕様および起動オプションと整合させる。

---

## 4. 完了条件

- [x] `README.md` の全ボタン名・ショートカットキーが実際のアプリ画面と完全に一致していること
- [x] `README.md` に開発者向けのテスト（`check.bat`）およびビルド手順が正しく記載されていること
- [x] ドキュメント内に古いバージョンや存在しないスクリプトへの参照が残っていないこと（※ `run_linux.sh`, `run_docker.sh`, `reference/` 等、現在の `main` ブランチ上に存在しないファイルへの記載・参照は除去済み）
- [x] `check.bat` がすべて成功すること

---

## 5. やらないこと

- 英語版ドキュメントの新規作成（日本語ドキュメントの整合を最優先とする）
- チュートリアル動画や外部ドキュメントサイト（Read the Docs 等）の構築
