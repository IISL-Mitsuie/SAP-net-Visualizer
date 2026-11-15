"""
Unit tests for the SAP-net Visualizer updater module
"""
import hashlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error

from sap_visualizer.updater import (
    parse_version_tuple,
    compare_versions,
    is_newer_version,
    fetch_latest_release_info,
    download_installer,
    launch_installer,
    UpdateInfo,
    UpdateVerificationError,
)


class TestUpdater(unittest.TestCase):
    """アップデータモジュールの単体テスト"""

    def test_parse_version_tuple(self):
        self.assertEqual(parse_version_tuple("1.0.0"), (1, 0, 0))
        self.assertEqual(parse_version_tuple("v1.2.3"), (1, 2, 3))
        self.assertEqual(parse_version_tuple("V2.10.5"), (2, 10, 5))
        self.assertEqual(parse_version_tuple("1.0.0-rc1"), (1, 0, 0))
        self.assertEqual(parse_version_tuple(""), (0,))
        self.assertEqual(parse_version_tuple(None), (0,))

    def test_compare_versions(self):
        # v1 > v2 -> 1
        self.assertEqual(compare_versions("1.1.0", "1.0.1"), 1)
        self.assertEqual(compare_versions("v2.0.0", "1.9.9"), 1)
        self.assertEqual(compare_versions("1.0.1", "1.0.0"), 1)
        self.assertEqual(compare_versions("1.0.1", "1.0"), 1)

        # v1 == v2 -> 0
        self.assertEqual(compare_versions("1.0.0", "1.0.0"), 0)
        self.assertEqual(compare_versions("v1.0.0", "1.0"), 0)
        self.assertEqual(compare_versions("1.0", "1.0.0.0"), 0)

        # v1 < v2 -> -1
        self.assertEqual(compare_versions("1.0.1", "1.1.0"), -1)
        self.assertEqual(compare_versions("1.0.0", "2.0.0"), -1)
        self.assertEqual(compare_versions("0.9.9", "1.0.0"), -1)

    def test_is_newer_version(self):
        self.assertTrue(is_newer_version("1.0.0", "1.0.1"))
        self.assertTrue(is_newer_version("1.0.1", "1.1.0"))
        self.assertTrue(is_newer_version("1.1.0", "2.0.0"))
        self.assertFalse(is_newer_version("1.1.0", "1.1.0"))
        self.assertFalse(is_newer_version("1.1.0", "1.0.9"))

    @patch("urllib.request.urlopen")
    def test_fetch_latest_release_info_success(self, mock_urlopen):
        mock_response_data = {
            "tag_name": "v1.2.0",
            "name": "SAP-net Visualizer Release 1.2.0",
            "body": "## What's Changed\n* New features and improvements",
            "html_url": "https://github.com/IISL-Mitsuie/SAP-net-Visualizer/releases/tag/v1.2.0",
            "published_at": "2026-09-01T12:00:00Z",
            "assets": [
                {
                    "name": "SAP_net_Visualizer_Setup_v1.2.0.exe",
                    "browser_download_url": "https://github.com/IISL-Mitsuie/SAP-net-Visualizer/releases/download/v1.2.0/SAP_net_Visualizer_Setup_v1.2.0.exe",
                    "size": 52428800,
                }
            ],
        }

        mock_cm = MagicMock()
        mock_cm.status = 200
        mock_cm.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_cm.__enter__.return_value = mock_cm
        mock_urlopen.return_value = mock_cm

        info = fetch_latest_release_info(current_version="1.1.0")

        self.assertIsNotNone(info)
        self.assertEqual(info.version, "1.2.0")
        self.assertEqual(info.tag_name, "v1.2.0")
        self.assertTrue(info.is_update_available)
        self.assertEqual(info.installer_name, "SAP_net_Visualizer_Setup_v1.2.0.exe")
        self.assertEqual(info.installer_size, 52428800)
        self.assertTrue(info.installer_download_url.endswith(".exe"))

    @patch("urllib.request.urlopen")
    def test_fetch_latest_release_info_no_update(self, mock_urlopen):
        mock_response_data = {
            "tag_name": "v1.1.0",
            "name": "SAP-net Visualizer Release 1.1.0",
            "body": "Current release",
            "html_url": "https://github.com/IISL-Mitsuie/SAP-net-Visualizer/releases/tag/v1.1.0",
            "published_at": "2026-09-01T12:00:00Z",
            "assets": [],
        }

        mock_cm = MagicMock()
        mock_cm.status = 200
        mock_cm.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_cm.__enter__.return_value = mock_cm
        mock_urlopen.return_value = mock_cm

        info = fetch_latest_release_info(current_version="1.1.0")

        self.assertIsNotNone(info)
        self.assertEqual(info.version, "1.1.0")
        self.assertFalse(info.is_update_available)

    @patch("urllib.request.urlopen")
    def test_fetch_latest_release_info_offline(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")

        info = fetch_latest_release_info(current_version="1.1.0")
        # ネットワーク障害時は例外を出さず None を返すこと
        self.assertIsNone(info)

    def test_folder_selector_button_restyle_safe(self):
        """FolderSelectorDialog の _restyle_button が Tkinter の TclError を起こさず動作することを検証"""
        try:
            import tkinter as tk
            from sap_visualizer.folder_selector_gui import FolderSelectorDialog
        except ImportError:
            self.skipTest("Tkinter is not available")

        root = tk.Tk()
        root.withdraw()
        try:
            dialog = FolderSelectorDialog()
            dialog.root = root
            btn = dialog._create_styled_button(
                root,
                text="テスト",
                command=lambda: None,
                bg="#ffffff",
                fg="#000000",
                hover_bg="#f0f0f0"
            )
            dialog.update_badge_btn = btn

            # 更新可能状態への切り替え（TclError が出ないこと）
            update_info = UpdateInfo(
                version="1.2.0",
                tag_name="v1.2.0",
                title="v1.2.0",
                release_notes="Notes",
                release_url="http://example.com",
                published_at="2026-09-01T00:00:00Z",
                is_update_available=True
            )
            dialog._apply_update_info(update_info, silent=True)
            self.assertIn("1.2.0", btn.cget("text"))

            # 最新版状態への切り替え（TclError が出ないこと）
            current_info = UpdateInfo(
                version="1.1.0",
                tag_name="v1.1.0",
                title="v1.1.0",
                release_notes="Notes",
                release_url="http://example.com",
                published_at="2026-09-01T00:00:00Z",
                is_update_available=False
            )
            dialog._apply_update_info(current_info, silent=True)
            self.assertIn("最新版", btn.cget("text"))

        finally:
            root.destroy()

    def test_update_dialog_download_error_callback_no_nameerror(self):
        """_start_downloadのワーカーで例外が発生してもコールバック内でNameErrorにならないこと"""
        import threading
        from sap_visualizer.update_dialog import UpdateDialog

        dlg = UpdateDialog.__new__(UpdateDialog)
        dlg.update_info = UpdateInfo(
            version="1.2.0",
            tag_name="v1.2.0",
            title="v1.2.0",
            release_notes="",
            release_url="https://example.com",
            published_at="2026-09-01T00:00:00Z",
            installer_name="setup.exe",
            installer_download_url="https://example.com/setup.exe",
            is_update_available=True,
        )
        dlg.cancel_event = threading.Event()
        dlg.update_now_btn = MagicMock()
        dlg.close_btn = MagicMock()
        dlg.progress_frame = MagicMock()
        dlg.progress_bar = {}
        dlg.progress_lbl = MagicMock()
        dlg.dialog = MagicMock()

        captured_callbacks = []
        dlg.dialog.after.side_effect = lambda _delay, fn: captured_callbacks.append(fn)
        dlg._on_download_failed = MagicMock()

        with patch("sap_visualizer.update_dialog.download_installer", side_effect=RuntimeError("boom")):
            dlg._start_download()
            dlg.download_thread.join(timeout=2.0)

        self.assertEqual(len(captured_callbacks), 1)
        # except ブロックを抜けた後にラムダを実行しても NameError にならないことを検証
        captured_callbacks[0]()
        dlg._on_download_failed.assert_called_once_with("boom")

    def test_update_dialog_open_installer_folder(self):
        """_open_installer_folderがsubprocess未定義エラーにならず動作すること"""
        from sap_visualizer.update_dialog import UpdateDialog

        dlg = UpdateDialog.__new__(UpdateDialog)
        with patch("sap_visualizer.update_dialog.sys.platform", "win32"), \
             patch("sap_visualizer.update_dialog.subprocess.Popen") as mock_popen:
            dlg._open_installer_folder("C:/temp/setup.exe")
            mock_popen.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_fetch_latest_release_info_parses_sha256_asset_and_digest(self, mock_urlopen):
        """fetch_latest_release_infoが.sha256アセットおよびasset.digestから期待SHA-256を取得すること"""
        payload_bytes = b"installer binary content"
        expected_hash = hashlib.sha256(payload_bytes).hexdigest()

        # 1. .sha256 アセットからの取得
        api_json = {
            "tag_name": "v1.3.0",
            "name": "v1.3.0",
            "body": "",
            "html_url": "https://example.com/v1.3.0",
            "published_at": "2026-10-01T00:00:00Z",
            "assets": [
                {
                    "name": "SAP_net_Visualizer_Setup_v1.3.0.exe",
                    "browser_download_url": "https://example.com/setup.exe",
                    "size": len(payload_bytes),
                },
                {
                    "name": "SAP_net_Visualizer_Setup_v1.3.0.exe.sha256",
                    "browser_download_url": "https://example.com/setup.exe.sha256",
                    "size": 128,
                },
            ],
        }
        api_cm = MagicMock()
        api_cm.status = 200
        api_cm.read.return_value = json.dumps(api_json).encode("utf-8")
        api_cm.__enter__.return_value = api_cm

        sha_cm = MagicMock()
        sha_cm.status = 200
        sha_cm.read.return_value = f"{expected_hash}  SAP_net_Visualizer_Setup_v1.3.0.exe\n".encode("utf-8")
        sha_cm.__enter__.return_value = sha_cm

        mock_urlopen.side_effect = [api_cm, sha_cm]
        info = fetch_latest_release_info(current_version="1.1.0")
        self.assertIsNotNone(info)
        self.assertEqual(info.expected_sha256, expected_hash)

        # 2. GitHub API asset.digest フィールドからの取得
        api_digest_json = {
            "tag_name": "v1.4.0",
            "name": "v1.4.0",
            "body": "",
            "html_url": "https://example.com/v1.4.0",
            "published_at": "2026-11-01T00:00:00Z",
            "assets": [
                {
                    "name": "SAP_net_Visualizer_Setup_v1.4.0.exe",
                    "browser_download_url": "https://example.com/setup4.exe",
                    "size": 123,
                    "digest": f"sha256:{expected_hash.upper()}",
                }
            ],
        }
        digest_cm = MagicMock()
        digest_cm.status = 200
        digest_cm.read.return_value = json.dumps(api_digest_json).encode("utf-8")
        digest_cm.__enter__.return_value = digest_cm
        mock_urlopen.side_effect = [digest_cm]

        info2 = fetch_latest_release_info(current_version="1.1.0")
        self.assertIsNotNone(info2)
        self.assertEqual(info2.expected_sha256, expected_hash)

    def _mock_download_response(self, content: bytes):
        class _FakeResp(io.BytesIO):
            def __init__(self, data: bytes):
                super().__init__(data)
                self.headers = {"Content-Length": str(len(data))}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                self.close()

        return _FakeResp(content)

    def test_download_installer_verifies_hash_and_cleans_part_on_mismatch(self):
        """SHA-256・サイズ検証成功時は正規ファイルが返り、不一致時は.partが削除され例外になること"""
        work_root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(work_root, ignore_errors=True))

        payload = b"valid installer payload bytes" * 100
        good_hash = hashlib.sha256(payload).hexdigest()

        with patch("sap_visualizer.updater.tempfile.mkdtemp", side_effect=lambda prefix="": str(work_root / "dl1")), \
             patch("urllib.request.urlopen", return_value=self._mock_download_response(payload)):
            os.makedirs(work_root / "dl1", exist_ok=True)
            dest = download_installer(
                "https://example.com/SAP_net_Visualizer_Setup_v1.2.0.exe",
                target_filename="SAP_net_Visualizer_Setup_v1.2.0.exe",
                expected_size=len(payload),
                expected_sha256=good_hash,
            )
        self.assertTrue(os.path.exists(dest))
        self.assertFalse(os.path.exists(dest + ".part"))

        # SHA-256 不一致
        dl_bad_hash = work_root / "dl_bad_hash"
        os.makedirs(dl_bad_hash, exist_ok=True)
        with patch("sap_visualizer.updater.tempfile.mkdtemp", return_value=str(dl_bad_hash)), \
             patch("urllib.request.urlopen", return_value=self._mock_download_response(payload)):
            with self.assertRaises(UpdateVerificationError):
                download_installer(
                    "https://example.com/setup.exe",
                    target_filename="setup.exe",
                    expected_size=len(payload),
                    expected_sha256="0" * 64,
                )
        self.assertFalse((dl_bad_hash / "setup.exe.part").exists())
        self.assertFalse((dl_bad_hash / "setup.exe").exists())
        self.assertFalse(dl_bad_hash.exists())

        # サイズ不一致
        dl_bad_size = work_root / "dl_bad_size"
        os.makedirs(dl_bad_size, exist_ok=True)
        with patch("sap_visualizer.updater.tempfile.mkdtemp", return_value=str(dl_bad_size)), \
             patch("urllib.request.urlopen", return_value=self._mock_download_response(payload)):
            with self.assertRaises(UpdateVerificationError):
                download_installer(
                    "https://example.com/setup.exe",
                    target_filename="setup.exe",
                    expected_size=len(payload) + 10,
                    expected_sha256=good_hash,
                )
        self.assertFalse((dl_bad_size / "setup.exe.part").exists())
        self.assertFalse((dl_bad_size / "setup.exe").exists())
        self.assertFalse(dl_bad_size.exists())

        # キャンセル時
        dl_cancel = work_root / "dl_cancel"
        os.makedirs(dl_cancel, exist_ok=True)
        cancel_ev = threading.Event()
        cancel_ev.set()
        with patch("sap_visualizer.updater.tempfile.mkdtemp", return_value=str(dl_cancel)), \
             patch("urllib.request.urlopen", return_value=self._mock_download_response(payload)):
            with self.assertRaises(InterruptedError):
                download_installer(
                    "https://example.com/setup.exe",
                    target_filename="setup.exe",
                    cancel_event=cancel_ev,
                )
        self.assertFalse((dl_cancel / "setup.exe.part").exists())
        self.assertFalse(dl_cancel.exists())

    def test_launch_installer_does_not_call_sys_exit(self):
        """launch_installerがPopenを起動しつつsys.exitを呼ばないこと"""
        temp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        dummy_exe = temp_dir / "setup.exe"
        dummy_exe.write_bytes(b"MZ")

        with patch("sap_visualizer.updater.subprocess.Popen") as mock_popen, \
             patch("sap_visualizer.updater.sys.exit") as mock_exit:
            launch_installer(str(dummy_exe))
            mock_popen.assert_called_once()
            mock_exit.assert_not_called()

    def test_build_write_sha256_file_and_app_mutex_configured(self):
        """build.write_sha256_fileの出力とinstaller.iss/main.pyのAppMutex定義を検証"""
        root_dir = Path(__file__).resolve().parent.parent
        build_path = root_dir / "packaging" / "build.py"
        spec = importlib.util.spec_from_file_location("sap_packaging_build_u", build_path)
        build_mod = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(build_mod)

        temp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        sample_file = temp_dir / "SAP_net_Visualizer_Setup_v1.1.0.exe"
        content = b"setup binary test data"
        sample_file.write_bytes(content)

        sha_path = build_mod.write_sha256_file(sample_file)
        self.assertTrue(sha_path.exists())
        expected = hashlib.sha256(content).hexdigest()
        self.assertEqual(sha_path.read_text(encoding="utf-8").strip(), f"{expected}  {sample_file.name}")

        iss_text = (root_dir / "packaging" / "installer.iss").read_text(encoding="utf-8")
        main_text = (root_dir / "main.py").read_text(encoding="utf-8")
        self.assertIn("AppMutex=SAPNetVisualizer_AppMutex", iss_text)
        self.assertIn("SAPNetVisualizer_AppMutex", main_text)


if __name__ == "__main__":
    unittest.main()
