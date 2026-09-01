"""
Unit tests for the SAP-net Visualizer updater module
"""
import unittest
from unittest.mock import patch, MagicMock
import io
import json
import urllib.error

from sap_visualizer.updater import (
    parse_version_tuple,
    compare_versions,
    is_newer_version,
    fetch_latest_release_info,
    UpdateInfo,
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


if __name__ == "__main__":
    unittest.main()
