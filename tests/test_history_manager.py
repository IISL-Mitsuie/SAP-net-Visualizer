import os
import sys
import unittest
import tempfile
import shutil

# プロジェクトルートをインポートパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sap_visualizer.folder_selector_gui import FolderHistoryManager


class TestFolderHistoryManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.history_file = os.path.join(self.test_dir, "test_history.json")
        self.mgr = FolderHistoryManager(history_file=self.history_file, max_history=5)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_initial_state(self):
        """初期状態で履歴が空であることのテスト"""
        self.assertEqual(len(self.mgr.history), 0)

    def test_add_and_lru_ordering(self):
        """フォルダ追加とLRU順序（最新が先頭）のテスト"""
        f1 = os.path.join(self.test_dir, "exp_1")
        f2 = os.path.join(self.test_dir, "exp_2")
        f3 = os.path.join(self.test_dir, "exp_3")

        self.mgr.add_folder(f1)
        self.mgr.add_folder(f2)
        self.mgr.add_folder(f3)

        self.assertEqual(len(self.mgr.history), 3)
        self.assertEqual(self.mgr.history[0]["path"], os.path.abspath(f3))
        self.assertEqual(self.mgr.history[1]["path"], os.path.abspath(f2))
        self.assertEqual(self.mgr.history[2]["path"], os.path.abspath(f1))

        # f1を再追加すると先頭に昇格すること
        self.mgr.add_folder(f1)
        self.assertEqual(len(self.mgr.history), 3)
        self.assertEqual(self.mgr.history[0]["path"], os.path.abspath(f1))
        self.assertEqual(self.mgr.history[1]["path"], os.path.abspath(f3))
        self.assertEqual(self.mgr.history[2]["path"], os.path.abspath(f2))

    def test_max_history_limit(self):
        """最大件数（max_history）超過時の古い履歴切り捨てテスト"""
        for i in range(8):
            folder = os.path.join(self.test_dir, f"exp_{i}")
            self.mgr.add_folder(folder)

        self.assertEqual(len(self.mgr.history), 5)
        self.assertEqual(self.mgr.history[0]["path"], os.path.abspath(os.path.join(self.test_dir, "exp_7")))

    def test_persistence_save_and_load(self):
        """JSONファイルの保存と再読み込みテスト"""
        f1 = os.path.join(self.test_dir, "exp_persist")
        self.mgr.add_folder(f1)

        # 別インスタンスでロード
        mgr2 = FolderHistoryManager(history_file=self.history_file, max_history=5)
        self.assertEqual(len(mgr2.history), 1)
        self.assertEqual(mgr2.history[0]["path"], os.path.abspath(f1))

    def test_remove_and_clear(self):
        """個別削除および全消去のテスト"""
        f1 = os.path.join(self.test_dir, "exp_1")
        f2 = os.path.join(self.test_dir, "exp_2")
        self.mgr.add_folder(f1)
        self.mgr.add_folder(f2)

        self.mgr.remove_folder(f1)
        self.assertEqual(len(self.mgr.history), 1)
        self.assertEqual(self.mgr.history[0]["path"], os.path.abspath(f2))

        self.mgr.clear_history()
        self.assertEqual(len(self.mgr.history), 0)

    def test_detailed_history_status(self):
        """フォルダの存在確認・ログ検出状態の判定テスト"""
        # 1. ログが存在する正常フォルダ
        ok_dir = os.path.join(self.test_dir, "exp_ok")
        os.makedirs(ok_dir, exist_ok=True)
        with open(os.path.join(ok_dir, "sap_dynamic_log_test.jsonl"), "w") as f:
            f.write("{}\n")

        # 2. ログがないフォルダ
        empty_dir = os.path.join(self.test_dir, "exp_empty")
        os.makedirs(empty_dir, exist_ok=True)

        # 3. 存在しないフォルダ
        missing_dir = os.path.join(self.test_dir, "exp_missing")

        self.mgr.add_folder(ok_dir)
        self.mgr.add_folder(empty_dir)
        self.mgr.add_folder(missing_dir)

        detailed = self.mgr.get_detailed_history()
        self.assertEqual(len(detailed), 3)

        # missing_dir
        self.assertFalse(detailed[0]["exists"])
        self.assertIn("未検出", detailed[0]["status"])

        # empty_dir
        self.assertTrue(detailed[1]["exists"])
        self.assertFalse(detailed[1]["log_found"])
        self.assertIn("ログ未検出", detailed[1]["status"])

        # ok_dir
        self.assertTrue(detailed[2]["exists"])
        self.assertTrue(detailed[2]["log_found"])
        self.assertIn("正常", detailed[2]["status"])

    def test_history_manager_module_has_no_tkinter_dependency(self):
        """history_managerモジュールがtkinterに依存せずにインポート可能であること"""
        import ast
        import subprocess
        import sap_visualizer.history_manager as hm_mod

        with open(hm_mod.__file__, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=hm_mod.__file__)

        imported_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.append(node.module)

        self.assertFalse(
            any("tkinter" in name for name in imported_names),
            msg=f"tkinter import found in history_manager.py: {imported_names}",
        )

        # tkinter無効環境でもインポート・インスタンス化できること
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.modules['tkinter'] = None; "
                "from sap_visualizer.history_manager import FolderHistoryManager; "
                "assert FolderHistoryManager is not None",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_backward_compatible_reexports(self):
        """folder_selector_guiおよびパッケージルートからの後方互換インポートが維持されること"""
        from sap_visualizer import FolderHistoryManager as PkgHistoryMgr
        from sap_visualizer.history_manager import FolderHistoryManager as DirectHistoryMgr
        from sap_visualizer.folder_selector_gui import (
            FolderHistoryManager as CompatHistoryMgr,
            UpdateDialog as CompatUpdateDialog,
        )
        from sap_visualizer.update_dialog import UpdateDialog as DirectUpdateDialog

        self.assertIs(PkgHistoryMgr, DirectHistoryMgr)
        self.assertIs(CompatHistoryMgr, DirectHistoryMgr)
        self.assertIs(CompatUpdateDialog, DirectUpdateDialog)


if __name__ == "__main__":
    unittest.main()
