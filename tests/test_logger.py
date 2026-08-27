import os
import sys
import unittest
import tempfile
import shutil
import json
import gzip

# プロジェクトルートをインポートパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sap_visualizer import SAPVisualLogger


class TestSAPVisualLogger(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_sample_frames(self):
        return [
            {
                "index": 0,
                "episode": 1,
                "step": 1,
                "event_type": "STEP",
                "A": [0.1, 0.2],
                "weight": [[0.0, 0.5], [0.5, 0.0]],
                "plan": 0,
                "selectplans": [0],
                "threshold": 0.2
            },
            {
                "index": 1,
                "episode": 1,
                "step": 2,
                "event_type": "ACTIVATION",
                "A": [0.8, 0.3],
                "weight": [[0.0, 0.5], [0.5, 0.0]],
                "plan": 0,
                "selectplans": [0],
                "threshold": 0.2
            },
            {
                "index": 2,
                "episode": 1,
                "step": 3,
                "event_type": "SELECT_PLAN",
                "A": [0.9, 0.2],
                "weight": [[0.0, 0.5], [0.5, 0.0]],
                "plan": 1,
                "selectplans": [1],
                "threshold": 0.2
            },
            {
                "index": 3,
                "episode": 1,
                "step": 4,
                "event_type": "WEIGHT_UPDATE",
                "A": [0.7, 0.2],
                "weight": [[0.0, 0.6], [0.6, 0.0]],
                "plan": 1,
                "selectplans": [1],
                "threshold": 0.2
            },
            {
                "index": 4,
                "episode": 2,
                "step": 1,
                "event_type": "STEP",
                "A": [0.1, 0.1],
                "weight": [[0.0, 0.6], [0.6, 0.0]],
                "plan": 0,
                "selectplans": [0],
                "threshold": 0.2
            }
        ]

    def test_load_from_file_gzip(self):
        """gzip圧縮JSONLファイルの読み込みテスト"""
        frames = self._create_sample_frames()
        gz_path = os.path.join(self.test_dir, "sap_dynamic_log_sample.jsonl.gz")
        with gzip.open(gz_path, "wt", encoding="utf-8") as f:
            for fr in frames:
                f.write(json.dumps(fr) + "\n")

        logger = SAPVisualLogger()
        success = logger.load_from_file(gz_path)
        self.assertTrue(success)
        self.assertEqual(len(logger.history), len(frames))
        self.assertEqual(logger.history[0].episode, 1)
        self.assertEqual(logger.history[4].episode, 2)

    def test_load_from_file_plain_jsonl(self):
        """非圧縮JSONLファイルの読み込みテスト"""
        frames = self._create_sample_frames()
        jsonl_path = os.path.join(self.test_dir, "sap_dynamic_log_sample.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for fr in frames:
                f.write(json.dumps(fr) + "\n")

        logger = SAPVisualLogger()
        success = logger.load_from_file(jsonl_path)
        self.assertTrue(success)
        self.assertEqual(len(logger.history), len(frames))

    def test_load_from_file_with_corrupted_lines(self):
        """途中に破損JSON行が存在する場合でも正常行を救出する耐性テスト"""
        gz_path = os.path.join(self.test_dir, "corrupted.jsonl.gz")
        with gzip.open(gz_path, "wt", encoding="utf-8") as f:
            f.write(json.dumps({"index": 0, "episode": 1, "step": 1, "event_type": "STEP"}) + "\n")
            f.write("CORRUPTED_NON_JSON_DATA_LINE\n")
            f.write(json.dumps({"index": 1, "episode": 1, "step": 2, "event_type": "ACTIVATION"}) + "\n")

        logger = SAPVisualLogger()
        success = logger.load_from_file(gz_path)
        self.assertTrue(success)
        self.assertEqual(len(logger.history), 2)

    def test_load_from_nonexistent_file(self):
        """存在しないファイル指定時の安全なエラーハンドリングテスト"""
        logger = SAPVisualLogger()
        success = logger.load_from_file(os.path.join(self.test_dir, "not_found.jsonl"))
        self.assertFalse(success)
        self.assertEqual(len(logger.history), 0)

    def test_load_from_folder(self):
        """フォルダからのログ自動検出・読み込みテスト"""
        folder_path = os.path.join(self.test_dir, "exp_folder")
        os.makedirs(folder_path, exist_ok=True)
        log_path = os.path.join(folder_path, "sap_dynamic_log_20260827_120000.jsonl.gz")
        with gzip.open(log_path, "wt", encoding="utf-8") as f:
            f.write(json.dumps({"index": 0, "episode": 1, "step": 1, "event_type": "STEP"}) + "\n")

        logger = SAPVisualLogger()
        success = logger.load_from_folder(folder_path)
        self.assertTrue(success)
        self.assertEqual(len(logger.history), 1)

    def test_event_navigation(self):
        """イベント種別（ACTIVATION, SELECT_PLAN, WEIGHT_UPDATE, NEW_EPISODE）の前後ジャンプ検索テスト"""
        frames = self._create_sample_frames()
        gz_path = os.path.join(self.test_dir, "events.jsonl.gz")
        with gzip.open(gz_path, "wt", encoding="utf-8") as f:
            for fr in frames:
                f.write(json.dumps(fr) + "\n")

        logger = SAPVisualLogger()
        logger.load_from_file(gz_path)

        # ACTIVATION 検索
        idx = logger.find_next_event_index(0, "ACTIVATION")
        self.assertEqual(idx, 1)
        self.assertEqual(logger.find_prev_event_index(2, "ACTIVATION"), 1)

        # SELECT_PLAN 検索
        idx = logger.find_next_event_index(0, "SELECT_PLAN")
        self.assertEqual(idx, 2)

        # WEIGHT_UPDATE 検索
        idx = logger.find_next_event_index(0, "WEIGHT_UPDATE")
        self.assertEqual(idx, 3)

        # NEW_EPISODE 検索
        idx = logger.find_next_event_index(0, "NEW_EPISODE")
        self.assertEqual(idx, 4)
        self.assertEqual(logger.find_prev_event_index(4, "NEW_EPISODE"), 0)

    def test_threshold_consistency_with_mixed_log_frames(self):
        """STEPが0.15、ACTIVATIONが0.18等、ログ内で混在していても基準閾値が一貫して適用されることをテスト"""
        mixed_frames = [
            {"index": 0, "episode": 1, "step": 1, "event_type": "ACTIVATION", "A": [0.1, 0.2], "threshold": 0.18},
            {"index": 1, "episode": 1, "step": 1, "event_type": "SELECT_PLAN", "A": [0.1, 0.2], "threshold": 0.18},
            {"index": 2, "episode": 1, "step": 1, "event_type": "STEP", "A": [0.1, 0.2], "threshold": 0.15},
            {"index": 3, "episode": 1, "step": 2, "event_type": "STEP", "A": [0.1, 0.2], "threshold": 0.15},
        ]
        log_path = os.path.join(self.test_dir, "mixed.jsonl")
        with open(log_path, "w", encoding="utf-8") as f:
            for fr in mixed_frames:
                f.write(json.dumps(fr) + "\n")

        logger = SAPVisualLogger()
        logger.load_from_file(log_path)

        # YAML設定がない場合でも、STEPイベント基準の dominant_threshold (0.15) が全フレームに一貫して適用される
        self.assertEqual(logger.active_threshold, 0.15)
        for i in range(len(mixed_frames)):
            res = logger.resolve_frame(i)
            self.assertEqual(res.threshold, 0.15)

    def test_threshold_prioritizes_config_used_yaml(self):
        """config_used_*.yaml に SAP.THRESHOLD が存在する場合、それが最優先で全フレームに反映されるテスト"""
        mixed_frames = [
            {"index": 0, "episode": 1, "step": 1, "event_type": "ACTIVATION", "threshold": 0.18},
            {"index": 1, "episode": 1, "step": 1, "event_type": "STEP", "threshold": 0.15},
        ]
        log_path = os.path.join(self.test_dir, "exp_log.jsonl")
        with open(log_path, "w", encoding="utf-8") as f:
            for fr in mixed_frames:
                f.write(json.dumps(fr) + "\n")

        # 同一ディレクトリに config_used_*.yaml を作成 (SAP.THRESHOLD: 0.25)
        yaml_path = os.path.join(self.test_dir, "config_used_20260827_999999.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write("SAP:\n  THRESHOLD: 0.25\n")

        logger = SAPVisualLogger()
        logger.load_from_file(log_path)

        self.assertEqual(logger.config_threshold, 0.25)
        self.assertEqual(logger.active_threshold, 0.25)
        for i in range(len(mixed_frames)):
            res = logger.resolve_frame(i)
            self.assertEqual(res.threshold, 0.25)


if __name__ == "__main__":
    unittest.main()

