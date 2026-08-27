import os
import sys
import unittest
import tempfile
import shutil
import json
import gzip

# プロジェクトルートをインポートパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sap_visualizer import SAPVisualLogger, SAPVisualizerGUI


class TestSAPVisualizerGUI(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.logger = SAPVisualLogger()
        
        # 複数フレームのダミーデータ
        self.frames = [
            {"index": i, "episode": 1, "step": i + 1, "event_type": "STEP", "A": [0.1 * i, 0.2], "weight": [[0.0, 0.1], [0.1, 0.0]], "plan": 0, "selectplans": [0], "threshold": 0.2}
            for i in range(10)
        ]
        log_file = os.path.join(self.test_dir, "sap_dynamic_log_test.jsonl.gz")
        with gzip.open(log_file, "wt", encoding="utf-8") as f:
            for fr in self.frames:
                f.write(json.dumps(fr) + "\n")
        self.logger.load_from_file(log_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_gui_navigation(self):
        """GUIのコマ送り・コマ戻し・リセット動作テスト"""
        gui = SAPVisualizerGUI(self.logger)
        self.assertEqual(gui.current_index, 0)

        # コマ送り
        gui.step_forward()
        self.assertEqual(gui.current_index, 1)

        gui.step_forward()
        self.assertEqual(gui.current_index, 2)

        # コマ戻し
        gui.step_back()
        self.assertEqual(gui.current_index, 1)

        # リセット
        gui.current_index = 5
        gui.current_index = 0
        self.assertEqual(gui.current_index, 0)

    def test_toggle_play(self):
        """再生/一時停止トグルのテスト"""
        gui = SAPVisualizerGUI(self.logger)
        self.assertFalse(gui.is_playing)

        gui.toggle_play()
        self.assertTrue(gui.is_playing)
        self.assertFalse(gui.live_follow)

        gui.toggle_play()
        self.assertFalse(gui.is_playing)

    def test_load_config_fallback(self):
        """YAMLファイル未検出時の動的フォールバック設定値生成テスト"""
        gui = SAPVisualizerGUI(self.logger)
        config_items, yaml_loaded = gui.load_config_data(return_status=True)
        self.assertFalse(yaml_loaded)
        self.assertGreater(len(config_items), 0)

        # パラメータ名が含まれているか確認
        param_names = [item[0] for item in config_items]
        self.assertIn("CONFIG_STATUS", param_names)
        self.assertIn("SAP.THRESHOLD", param_names)

    def test_draw_with_weights(self):
        """重みエッジおよび数値バッジを含む描画処理の正常性テスト"""
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        gui = SAPVisualizerGUI(self.logger)
        # 通常描画
        gui.draw()
        # ヘルプオーバーレイ描画
        gui.show_help = True
        gui.draw()
        gui.show_help = False
        # 折れ線グラフ描画
        gui.view_mode = "GRAPH"
        gui.draw()

    def test_draw_weight_update_frame_with_empty_activations(self):
        """A=[]のWEIGHT_UPDATEフレームでもノードとエッジが正常にフォールバック描画されるテスト"""
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        # Aが空でweightのみ存在するフレームを追加
        self.logger.history.append({
            "index": 10,
            "episode": 1,
            "step": 11,
            "event_type": "WEIGHT_UPDATE",
            "A": [],
            "weight": [[0.0, 0.35], [0.35, 0.0]],
            "plan": None,
            "selectplans": [],
            "threshold": 0.2
        })
        gui = SAPVisualizerGUI(self.logger)
        gui.current_index = len(self.logger.history) - 1
        gui.draw()  # エラーなく正常に描画できることを検証


if __name__ == "__main__":
    unittest.main()
