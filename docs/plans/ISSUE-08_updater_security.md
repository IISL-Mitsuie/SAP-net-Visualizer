# [ISSUE-08] 自動アップデートの安全性向上（SHA-256・サイズ検証、.part 保存、AppMutex）

| 項目 | 内容 |
| :--- | :--- |
| 優先度 | **P1** |
| 種別 | security / bug |
| 規模 | M |
| 依存 | ISSUE-06, ISSUE-07 |
| 対象ファイル | `sap_visualizer/updater.py`, `sap_visualizer/update_dialog.py`, `main.py`, `packaging/installer.iss`, `packaging/build.py`, `tests/test_updater.py` |
| ブランチ名 | `agy/issue-08-updater-security` |

---

## 1. 背景・現状の課題

1. **ダウンロード整合性・完全性の未検証**:
   - `sap_visualizer/updater.py` L196-L236 の `download_installer()` は、ダウンロードしたファイルのハッシュ（SHA-256）やファイルサイズを検証していない。通信の瞬断で途中で切れたファイルや破損したファイルでもそのまま実行しようとする。
2. **予測可能な固定パスへの上書き**:
   - 保存先が `%TEMP%/<ファイル名>` という固定パスになっており、別プロセスとの衝突や破損ファイルへの上書きが懸念される。
3. **強制終了によるセッション・データ不整合**:
   - `launch_installer_and_exit()` が `sys.exit(0)` を呼ぶため、Pygame や GUI の通常の終了クリーンアップ処理（リソース解放・未保存データ処理）をスキップしてしまう。
4. **起動中プロセスの検知と上書き競合**:
   - `packaging/installer.iss` に `CloseApplications=yes` はあるものの、アプリ側で Inno Setup 標準の `AppMutex` が作成されていないため、Windows 上で実行中プロセスの検出が確実でない。

---

## 2. 目的

- 破損したインストーラーやサイズ・ハッシュ不一致のファイルを**絶対に実行しない**こと。
- ダウンロードを `.part` 一時ファイルで行い、検証成功時のみ正規ファイルへアトミックに昇格すること。
- アプリ起動中に名前付きミューテックス（`AppMutex`）を保持し、インストーラーが起動中のアプリを安全に検知・待機できるようにすること。

---

## 3. 作業手順

### 3.1 SHA-256 ハッシュおよびサイズ検証の実装
1. `UpdateInfo` データクラスに `expected_sha256: Optional[str] = None` を追加する。
2. `fetch_latest_release_info` で、リリースアセット一覧から `<installer_name>.sha256` を探索（または GitHub API の `digest`）して期待ハッシュを取得できるようにする。
3. `download_installer` を改修する:
   - `tempfile.mkdtemp(prefix="sap_vis_update_")` で専用の一時フォルダを作成する。
   - ダウンロード中は `<target_filename>.part` として保存し、チャンク受信ごとに `hashlib.sha256()` を更新する。
   - 完了時にサイズおよび SHA-256（期待値がある場合）を検証。一致した場合のみ `os.replace` で正規ファイル名に変更してパスを返す。
   - 検証不一致時は `.part` を即座に削除し、`UpdateVerificationError` 例外を送出する。

### 3.2 `build.py` での `.sha256` ファイル出力
4. `packaging/build.py` で、Windows インストーラー（`Setup_v*.exe`）生成後に、同じ出力ディレクトリへ `<インストーラー名>.sha256`（`certutil` / `sha256sum` 互換のフォーマット）を出力する。

### 3.3 AppMutex の設定と安全な終了処理
5. `main.py` の起動処理で、Windows 環境の場合に `ctypes.windll.kernel32.CreateMutexW(None, False, "SAPNetVisualizer_AppMutex")` を呼び出し、プロセス終了までハンドルを保持する。
6. `packaging/installer.iss` の `[Setup]` セクションに `AppMutex=SAPNetVisualizer_AppMutex` を明記する。
7. `sap_visualizer/updater.py` の `launch_installer_and_exit` から `sys.exit(0)` を分離し、`launch_installer(path)`（インストーラーの起動のみ担当）に変更。アプリの終了は呼び出し元 UI（`UpdateDialog`）が適切にイベントループを終了させて行う。

---

## 4. 完了条件

- [ ] ハッシュやサイズが一致しないファイルが実行されず、`.part` ファイルが安全に削除されること
- [ ] `build.py` でインストーラー生成と同時に `.sha256` ファイルが出力されること
- [ ] アプリ起動中にインストーラーを実行した際、`AppMutex` により起動中アプリの終了を促すダイアログが表示されること
- [ ] 既存テストがすべて通過すること
- [ ] `check.bat` がすべて成功すること

---

## 5. やらないこと

- 配布バイナリのコード署名（Authenticode）（研究室内での利用が前提のため現状は対象外）
- サイレントインストールの強制
