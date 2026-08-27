import os
import sys
import unittest
import tempfile
import shutil
import json
import gzip

# プロジェクトルートをインポートパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sap_visualizer import SAPVisualLogger, SAPVisualizerGUI, FolderHistoryManager


class TestSystemIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_pipeline_flow(self):
        """シミュレーションログ出力 -> フォルダロード -> 履歴登録 -> 可視化GUI初期化の完全パイプライン統合テスト"""
        exp_dir = os.path.join(self.test_dir, "exp_20260827_full")
        os.makedirs(exp_dir, exist_ok=True)
        log_file = os.path.join(exp_dir, "sap_dynamic_log_20260827_000000.jsonl.gz")

        sample_frame = {
            "index": 0,
            "episode": 1,
            "step": 1,
            "event_type": "STEP",
            "A": [0.2, 0.5, 0.8],
            "weight": [[0.0, 0.1, 0.2], [0.1, 0.0, 0.3], [0.2, 0.3, 0.0]],
            "plan": 1,
            "selectplans": [1],
            "policyvalue": [0.8],
            "reused_action": None,
            "threshold": 0.3
        }

        with gzip.open(log_file, "wt", encoding="utf-8") as f:
            f.write(json.dumps(sample_frame) + "\n")

        # 1. ロガーによるフォルダ読み込み
        logger = SAPVisualLogger()
        success = logger.load_from_folder(exp_dir)
        self.assertTrue(success)
        self.assertEqual(len(logger.history), 1)

        # 2. 履歴マネージャーへの登録
        history_file = os.path.join(self.test_dir, "history.json")
        history_mgr = FolderHistoryManager(history_file=history_file)
        history_mgr.add_folder(exp_dir)

        self.assertEqual(len(history_mgr.history), 1)
        self.assertEqual(history_mgr.history[0]["path"], os.path.abspath(exp_dir))

        # 3. 可視化GUIへの受け渡しと初期状態の確認
        gui = SAPVisualizerGUI(logger)
        self.assertEqual(gui.logger, logger)
        self.assertEqual(gui.current_index, 0)
        self.assertEqual(len(gui.logger.history), 1)


if __name__ == "__main__":
    unittest.main()
