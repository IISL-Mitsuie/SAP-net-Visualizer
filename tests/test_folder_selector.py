import os
import sys
import unittest
import tempfile
import shutil
import tkinter as tk

# プロジェクトルートをインポートパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sap_visualizer.folder_selector_gui import FolderSelectorDialog, FolderHistoryManager


class TestFolderSelectorDialog(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.history_file = os.path.join(self.test_dir, "history.json")
        self.mgr = FolderHistoryManager(history_file=self.history_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_dialog_placeholder_and_tree_interaction(self):
        """ダイアログのプレースホルダーとTreeview操作・パス決定ロジックのテスト"""
        import unittest.mock as mock

        # ダミーログフォルダ追加
        exp_folder = os.path.join(self.test_dir, "exp_sample")
        os.makedirs(exp_folder, exist_ok=True)
        with open(os.path.join(exp_folder, "sap_dynamic_log_2026.jsonl"), "w") as f:
            f.write("{}\n")
        self.mgr.add_folder(exp_folder)

        dialog = FolderSelectorDialog(initial_dir=self.test_dir, history_manager=self.mgr)

        # プレースホルダー初期状態
        self.assertEqual(dialog._get_entry_path(), "")
        self.assertTrue(dialog.placeholder_active)

        orig_tk = tk.Tk

        def mock_tk(*args, **kwargs):
            root = orig_tk(*args, **kwargs)

            def run_gui_checks():
                # Treeviewに正しくデータが入っているか
                children = dialog.tree.get_children()
                self.assertGreaterEqual(len(children), 1)

                # 初期状態ではEntryはプレースホルダー（空文字）
                self.assertEqual(dialog._get_entry_path(), "")

                # 履歴選択シミュレーション
                dialog.tree.selection_set(children[0])
                dialog._on_tree_select(None)
                self.assertEqual(dialog._get_entry_path(), os.path.abspath(exp_folder))
                self.assertFalse(dialog.placeholder_active)

                # プレースホルダー再適用
                dialog._apply_placeholder()
                self.assertEqual(dialog._get_entry_path(), "")
                self.assertTrue(dialog.placeholder_active)

                # 「開く」決定（入力欄が空でもTreeview選択行が採用される）
                dialog._on_confirm()
                self.assertEqual(dialog.selected_folder, os.path.abspath(exp_folder))

            root.after(50, run_gui_checks)
            return root

        with mock.patch("tkinter.Tk", side_effect=mock_tk):
            res = dialog.show()
            self.assertEqual(res, os.path.abspath(exp_folder))

    def test_browse_parent_directory_resolution(self):
        """参照ボタン押下時に選択中フォルダの親階層が初期ディレクトリとして解決されるか検証"""
        import unittest.mock as mock

        parent_dir = os.path.join(self.test_dir, "all_experiments")
        exp_folder = os.path.join(parent_dir, "exp_001")
        os.makedirs(exp_folder, exist_ok=True)

        dialog = FolderSelectorDialog(initial_dir=self.test_dir, history_manager=self.mgr)

        captured_initialdir = []

        def mock_askdirectory(**kwargs):
            captured_initialdir.append(kwargs.get("initialdir"))
            return os.path.join(parent_dir, "exp_002")

        orig_tk = tk.Tk

        def mock_tk(*args, **kwargs):
            root = orig_tk(*args, **kwargs)

            def run_browse_test():
                # 入力欄にフォルダパスを設定
                dialog._set_entry_path(exp_folder)
                self.assertEqual(dialog._get_entry_path(), os.path.abspath(exp_folder))

                with mock.patch("tkinter.filedialog.askdirectory", side_effect=mock_askdirectory):
                    dialog._on_browse()

                # 親ディレクトリが askdirectory の initialdir に渡されたことを検証
                self.assertEqual(len(captured_initialdir), 1)
                self.assertEqual(captured_initialdir[0], os.path.abspath(parent_dir))
                self.assertEqual(dialog._get_entry_path(), os.path.abspath(os.path.join(parent_dir, "exp_002")))

                dialog._on_cancel()

            root.after(50, run_browse_test)
            return root

        with mock.patch("tkinter.Tk", side_effect=mock_tk):
            dialog.show()


if __name__ == "__main__":
    unittest.main()



