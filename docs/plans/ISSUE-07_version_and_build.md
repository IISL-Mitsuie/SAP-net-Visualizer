# [ISSUE-07] バージョンの一元管理とビルドの再現性・整合性テストの整備

| 項目 | 内容 |
| :--- | :--- |
| 優先度 | **P1** |
| 種別 | build |
| 規模 | M |
| 依存 | ISSUE-05 |
| 対象ファイル | `sap_visualizer/constants.py`, `packaging/build.py`, `packaging/build_linux.py`, `packaging/build_appimage.sh`, `packaging/installer.iss`, `packaging/version_info.txt`（→ テンプレート化）, `packaging/SAP-net-Visualizer.spec`, `requirements.txt`, （新規）`requirements-build.txt`, （新規）`tests/test_version_consistency.py` |
| ブランチ名 | `agy/issue-07-version-and-build` |

---

## 1. 背景・現状の課題

1. **バージョン番号の重複と抽出バグ**:
   - バージョン文字列が `constants.py`, `installer.iss`, `version_info.txt` に分散して手動管理されている。
   - `packaging/build.py` L189 や `packaging/build_appimage.sh` L25 は、`sap_visualizer/__init__.py` から `__version__ = ...` 行を抽出しようとしているが、現在の `__init__.py` は `__version__ = APP_VERSION` と記述されているため抽出に失敗し、ハードコード値（`"1.1.0"`）にフォールバックしている。バージョン更新時にバイナリ名が更新されない重大なリスクがある。
2. **ビルド依存の混在**:
   - 実行時の `requirements.txt` に、ビルド専用ツールである `pyinstaller>=6.0.0` が含まれている。
3. **Inno Setup 失敗時の終了コード不備**:
   - `build.py` L162-L167: Inno Setup コンパイラ（ISCC.exe）のコンパイルがエラーで失敗しても、`main()` は `return 0` を返してしまい、自動化スクリプト側でビルド失敗を検知できない。
4. **ビルド前の自動テスト実行の欠如**:
   - テストが壊れた状態でもそのままバイナリがビルドされてしまう。

---

## 2. 目的

- バージョン番号の単一情報源（Single Source of Truth）を `sap_visualizer/constants.py` の `APP_VERSION` に一元化し、他ファイルへの動的注入を行うこと。
- ビルド依存（`pyinstaller`）を実行用 `requirements.txt` から分離すること。
- ISCC 実行失敗やテスト失敗時に確実にビルドが中断し、異常終了コード（1）を返すこと。
- バージョン整合性を機械的に検証する単体テストを配備すること。

---

## 3. 作業手順

### 3.1 バージョン情報源の一元化とテンプレート化
1. `sap_visualizer/constants.py` の `APP_VERSION = "1.1.0"` を単一の情報源とする。
2. `packaging/build.py` に `read_app_version()` ヘルパーを実装し、`constants.py` から正規表現でバージョンを安全に取得する。
3. `packaging/version_info.txt` を `packaging/version_info.template.txt` に改名し、`$MAJOR`, `$MINOR`, `$PATCH`, `$VERSION` プレースホルダーを配置。`build.py` 実行時に一時ビルドディレクトリへ展開する。
4. `packaging/SAP-net-Visualizer.spec` で、動的生成された `version_info.txt` のパスを参照可能にする。
5. `packaging/installer.iss` を `#ifndef MyAppVersion` で囲み、`build.py` から `/DMyAppVersion=<version>` で値を注入する。
6. `packaging/build_linux.py` および `packaging/build_appimage.sh` のバージョン取得ロジックも `constants.py` を直接読むように修正する。

### 3.2 依存関係の分離
7. `requirements.txt` から `pyinstaller` を削除する。
8. `requirements-build.txt` を新規作成し、以下を記述する:
   ```text
   -r requirements.txt
   pyinstaller>=6.0.0
   ```

### 3.3 ビルドスクリプトの堅牢化
9. `build.py` の先頭（またはビルド前）に `pytest -q` を自動実行し、テスト失敗時はビルドを中断して終了コード 1 で停止する（`--skip-tests` オプションでスキップ可能とする）。
10. Inno Setup の `subprocess.run` 戻り値を確認し、コンパイル失敗時は終了コード 1 で即時停止する。

### 3.4 整合性テストの実装
11. `tests/test_version_consistency.py` を新規作成し、以下を検証する:
    - `constants.py` の `APP_VERSION` が `MAJOR.MINOR.PATCH` 形式であること。
    - `packaging/installer.iss` にハードコードされたバージョン定義がないこと。
    - `packaging/version_info.template.txt` に必要なプレースホルダーが存在すること。

---

## 4. 完了条件

- [ ] バージョンを変更する際、`sap_visualizer/constants.py` の 1 箇所のみを更新すれば、インストーラー名・実行ファイルメタデータ・Linux パッケージ名にすべて反映されること
- [ ] `requirements.txt` に `pyinstaller` が含まれていないこと
- [ ] テストが失敗する状態で `python packaging/build.py` を実行するとビルドが中断されること
- [ ] Inno Setup コンパイルエラー時に `build.py` が終了コード 1 を返すこと
- [ ] `tests/test_version_consistency.py` が通過すること
- [ ] `check.bat` がすべて成功すること

---

## 5. やらないこと

- CI（GitHub Actions）上での自動リリースビルド
- 配布バイナリのコード署名（Authenticode）
- PyInstaller の `--onefile` 化（起動速度・展開速度を優先し `--onedir` を維持）
