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
        self.assertEqual(logger.max_nodes, 2)


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

    def test_load_from_file_with_null_and_malformed_fields(self):
        """threshold=nullや不正型を含む行があっても後続フレームが切り捨てられず全てロードされるテスト"""
        log_path = os.path.join(self.test_dir, "null_fields.jsonl")
        lines = [
            {"index": 0, "episode": 1, "step": 1, "event_type": "STEP", "A": [0.3, 0.4], "threshold": None, "plan": None},
            {"index": 1, "episode": 1, "step": 2, "event_type": "STEP", "A": None, "plan": "invalid", "threshold": "bad"},
            ["not_a_dict"],
            {"index": 2, "episode": 1, "step": 3, "event_type": "STEP", "A": [0.7, 0.2], "plan": 0, "threshold": 0.25},
        ]
        with open(log_path, "w", encoding="utf-8") as f:
            for item in lines:
                f.write(json.dumps(item) + "\n")

        logger = SAPVisualLogger()
        success = logger.load_from_file(log_path)
        self.assertTrue(success)
        self.assertEqual(len(logger.history), 3)
        self.assertEqual(logger.history[0].index, 0)
        self.assertIsNone(logger.history[1].plan)
        self.assertEqual(logger.history[2].index, 2)
        self.assertEqual(logger.history[2].activations, [0.7, 0.2])

    def test_resolve_frame_cache_consistency_and_edge_cases(self):
        """resolve_frameのO(1)キャッシュが欠損値補完・境界値・再ロードで整合すること"""
        from sap_visualizer.models import LogFrame

        log_path = os.path.join(self.test_dir, "resolve_cache.jsonl")
        frames = [
            {"index": 0, "episode": 1, "step": 1, "event_type": "STEP", "A": [0.1, 0.2], "weight": [[0.0, 0.5], [0.5, 0.0]], "plan": 1, "selectplans": [1, 2], "threshold": 0.3},
            {"index": 1, "episode": 1, "step": 2, "event_type": "REPLAN", "A": [], "weight": [], "plan": None, "selectplans": []},
            {"index": 2, "episode": 2, "step": 1, "event_type": "STEP", "A": [0.9, 0.8], "weight": [], "plan": 0, "selectplans": [0], "threshold": 0.4},
        ]
        with open(log_path, "w", encoding="utf-8") as f:
            for item in frames:
                f.write(json.dumps(item) + "\n")

        logger = SAPVisualLogger()
        self.assertTrue(logger.load_from_file(log_path))

        # 範囲外インデックスのフォールバック
        out_low = logger.resolve_frame(-1)
        out_high = logger.resolve_frame(99)
        self.assertEqual(out_low.activations, [])
        self.assertEqual(out_high.activations, [])

        # フレーム1はフレーム0の有効値をフォワードフィルし、フレーム2で部分更新
        r0 = logger.resolve_frame(0)
        r1 = logger.resolve_frame(1)
        r2 = logger.resolve_frame(2)
        self.assertEqual(r0.plan, 1)
        self.assertEqual(r1.plan, 1)
        self.assertEqual(r1.selectplans, [1, 2])
        self.assertEqual(r1.activations, [0.1, 0.2])
        self.assertEqual(r1.weight_matrix, [[0.0, 0.5], [0.5, 0.0]])
        self.assertEqual(r1.event_type, "REPLAN")
        self.assertEqual(r2.plan, 0)
        self.assertEqual(r2.selectplans, [0])
        self.assertEqual(r2.activations, [0.9, 0.8])
        self.assertEqual(r2.weight_matrix, [[0.0, 0.5], [0.5, 0.0]])

        # history直接変更時もresolve_frameが長さ不一致を検知してキャッシュを再構築すること
        logger.history.append(
            LogFrame(index=3, episode=2, step=2, event_type="STEP", activations=[], weight_matrix=[], plan=None, selectplans=[])
        )
        r3 = logger.resolve_frame(3)
        self.assertEqual(r3.activations, [0.9, 0.8])
        self.assertEqual(r3.plan, 0)

    def test_resolve_frame_large_history_fast(self):
        """大量フレームでもresolve_frameがO(1)で返却されること"""
        from sap_visualizer.models import LogFrame

        logger = SAPVisualLogger()
        logger.history = [
            LogFrame(
                index=i,
                episode=1,
                step=i + 1,
                event_type="STEP",
                activations=[0.5, 0.5] if i == 0 else [],
                weight_matrix=[[0.0, 0.2], [0.2, 0.0]] if i == 0 else [],
                plan=0 if i == 0 else None,
                selectplans=[0] if i == 0 else [],
            )
            for i in range(5000)
        ]
        # 末尾から参照してもキャッシュ再構築1回 + O(1)参照で即時完了する
        res_last = logger.resolve_frame(4999)
        self.assertEqual(res_last.activations, [0.5, 0.5])
        self.assertEqual(res_last.plan, 0)


if __name__ == "__main__":
    unittest.main()

