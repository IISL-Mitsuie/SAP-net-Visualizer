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
from sap_visualizer.models import LogFrame
from sap_visualizer.constants import ViewMode


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
        gui._handle_button_action("step_forward")
        self.assertEqual(gui.current_index, 1)

        gui._handle_button_action("step_forward")
        self.assertEqual(gui.current_index, 2)

        # コマ戻し
        gui._handle_button_action("step_back")
        self.assertEqual(gui.current_index, 1)

        # リセット
        gui.current_index = 5
        gui._handle_button_action("reset_index")
        self.assertEqual(gui.current_index, 0)

    def test_toggle_play(self):
        """再生/一時停止トグルのテスト"""
        gui = SAPVisualizerGUI(self.logger)
        self.assertFalse(gui.is_playing)

        gui._handle_button_action("toggle_play")
        self.assertTrue(gui.is_playing)

        gui._handle_button_action("toggle_play")
        self.assertFalse(gui.is_playing)

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
        gui.view_mode = ViewMode.LINE_CHART
        gui.draw()

    def test_draw_weight_update_frame_with_empty_activations(self):
        """A=[]のWEIGHT_UPDATEフレームでもノードとエッジが正常にフォールバック描画されるテスト"""
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        raw_frame = {
            "index": 10,
            "episode": 1,
            "step": 11,
            "event_type": "WEIGHT_UPDATE",
            "A": [],
            "weight": [[0.0, 0.35], [0.35, 0.0]],
            "plan": None,
            "selectplans": [],
            "threshold": 0.2
        }
        self.logger.history.append(LogFrame.from_dict(raw_frame))
        self.logger._update_metadata_cache()

        gui = SAPVisualizerGUI(self.logger)
        gui.current_index = len(self.logger.history) - 1
        gui.draw()

    def test_get_resolved_frame_info(self):
        """get_resolved_frame_infoによる欠損値フォールバック復元テスト"""
        f0 = LogFrame.from_dict({"index": 0, "episode": 1, "step": 1, "event_type": "STEP", "A": [0.5, 0.8], "weight": [[0.0, 0.2], [0.2, 0.0]], "plan": 1, "selectplans": [0, 1]})
        f1 = LogFrame.from_dict({"index": 1, "episode": 1, "step": 1, "event_type": "WEIGHT_UPDATE", "A": [], "weight": [[0.0, 0.5], [0.5, 0.0]], "plan": None, "selectplans": []})
        self.logger.history = [f0, f1]
        self.logger._update_metadata_cache()

        gui = SAPVisualizerGUI(self.logger)
        
        # フレーム0の検証
        plan0, sel0, A0, W0, ep0, st0, ev0 = gui.get_resolved_frame_info(0)
        self.assertEqual(plan0, 1)
        self.assertEqual(sel0, [0, 1])
        self.assertEqual(A0, [0.5, 0.8])
        self.assertEqual(ev0, "STEP")
        
        # フレーム1のフォールバック検証
        plan1, sel1, A1, W1, ep1, st1, ev1 = gui.get_resolved_frame_info(1)
        self.assertEqual(plan1, 1)  # 直前フレームから復元
        self.assertEqual(sel1, [0, 1])  # 直前フレームから復元
        self.assertEqual(A1, [0.5, 0.8])  # 直前フレームから復元
        self.assertEqual(W1, [[0.0, 0.5], [0.5, 0.0]])  # 自フレームの重み
        self.assertEqual(ev1, "WEIGHT_UPDATE")

    def test_line_chart_selected_knowledge(self):
        """折れ線グラフ画面での選択知識強調および大規模ログ間引き描画テスト"""
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        f0 = LogFrame.from_dict({"index": 0, "episode": 1, "step": 1, "event_type": "STEP", "A": [0.2, 0.9], "weight": [[0.0, 0.2], [0.2, 0.0]], "plan": 1, "selectplans": [0, 1], "threshold": 0.2})
        f1 = LogFrame.from_dict({"index": 1, "episode": 1, "step": 2, "event_type": "STEP", "A": [0.4, 0.7], "weight": [[0.0, 0.3], [0.3, 0.0]], "plan": 0, "selectplans": [1, 1], "threshold": 0.2})
        self.logger.history = [f0, f1]
        self.logger._update_metadata_cache()

        gui = SAPVisualizerGUI(self.logger)
        gui.view_mode = ViewMode.LINE_CHART
        gui.current_index = 0
        gui.draw()

    def test_line_chart_many_nodes_and_scrolling(self):
        """13個以上の多数知識ノードにおける1列スクロール描画およびスクロール動作テスト"""
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        num_nodes = 20
        f0 = LogFrame.from_dict({
            "index": 0, "episode": 1, "step": 1, "event_type": "STEP",
            "A": [0.05 * i for i in range(num_nodes)],
            "weight": [[0.0] * num_nodes for _ in range(num_nodes)],
            "plan": 2, "selectplans": [0] * num_nodes, "threshold": 0.2
        })
        self.logger.history = [f0]
        self.logger.max_nodes = num_nodes
        self.logger._update_metadata_cache()

        gui = SAPVisualizerGUI(self.logger)
        gui.view_mode = ViewMode.LINE_CHART
        gui.draw()

        # 1列スクロール表示で可視領域内のトグルrectが生成されていることを確認
        self.assertGreater(len(gui.chart_view.node_toggle_rects), 0)
        self.assertLessEqual(len(gui.chart_view.node_toggle_rects), num_nodes)
        self.assertGreater(gui.chart_view.max_filter_scroll, 0)

        # スクロール動作テスト
        gui.chart_view.scroll_filter(1)
        self.assertGreater(gui.chart_view.filter_scroll_y, 0)
        gui.chart_view.scroll_filter(-1)
        self.assertEqual(gui.chart_view.filter_scroll_y, 0)

    def test_open_folder_selector_resets_state(self):
        """フォルダ再選択成功後にlive_follow=Falseや表示設定がリセットされること"""
        import unittest.mock as mock

        os.environ["SDL_VIDEODRIVER"] = "dummy"
        new_exp_dir = os.path.join(self.test_dir, "new_exp")
        os.makedirs(new_exp_dir, exist_ok=True)
        new_log = os.path.join(new_exp_dir, "sap_dynamic_log_new.jsonl")
        with open(new_log, "w", encoding="utf-8") as f:
            f.write(json.dumps({"index": 0, "episode": 1, "step": 1, "A": [0.4, 0.6], "threshold": 0.2}) + "\n")
            f.write(json.dumps({"index": 1, "episode": 1, "step": 2, "A": [0.5, 0.5], "threshold": 0.2}) + "\n")

        gui = SAPVisualizerGUI(self.logger)
        gui.current_index = 5
        gui.live_follow = True
        gui.is_playing = True
        gui.show_config = True
        gui.show_help = True
        gui.chart_view.visible_nodes[0] = False
        gui.chart_view.filter_scroll_y = 40
        gui.config_scroll_y = 80

        with mock.patch("sap_visualizer.sap_visualizer_gui.FolderSelectorDialog") as mock_dlg_cls:
            mock_dlg_cls.return_value.show.return_value = new_exp_dir
            gui.open_folder_selector()

        self.assertEqual(gui.current_index, 0)
        self.assertFalse(gui.live_follow)
        self.assertFalse(gui.is_playing)
        self.assertFalse(gui.show_config)
        self.assertFalse(gui.show_help)
        self.assertEqual(gui.chart_view.visible_nodes, {})
        self.assertEqual(gui.chart_view.filter_scroll_y, 0)
        self.assertEqual(gui.config_scroll_y, 0)
        self.assertEqual(len(gui.logger.history), 2)

    def test_export_chart_includes_threshold_and_handles_empty_activations(self):
        """export_chart_surfaceに閾値線が描かれ、A=[]フレームでも0.0へ急落しないこと"""
        from sap_visualizer.theme import COLOR_ACCENT_RED, NODE_COLORS

        os.environ["SDL_VIDEODRIVER"] = "dummy"
        f0 = LogFrame.from_dict({"index": 0, "episode": 1, "step": 1, "event_type": "STEP", "A": [0.8], "threshold": 0.5})
        f1 = LogFrame.from_dict({"index": 1, "episode": 1, "step": 2, "event_type": "WEIGHT_UPDATE", "A": [], "threshold": 0.5})
        f2 = LogFrame.from_dict({"index": 2, "episode": 1, "step": 3, "event_type": "STEP", "A": [0.8], "threshold": 0.5})
        self.logger.history = [f0, f1, f2]
        self.logger.max_nodes = 1
        self.logger._update_metadata_cache()

        gui = SAPVisualizerGUI(self.logger)
        surf = gui.chart_view.export_chart_surface(self.logger.history, self.logger.max_nodes, threshold=0.5)
        self.assertIsNotNone(surf)

        # gx=70, gy=25, gw=800, gh=420 -> threshold=0.5 の Y は 25 + 420 - 210 = 235
        thresh_y = 25 + 420 - int(0.5 * 420)
        self.assertEqual(surf.get_at((72, thresh_y))[:3], COLOR_ACCENT_RED)

        # 中間フレーム(x = 70 + 400 = 470)の活性値0.8(y = 25 + 420 - int(0.8*420) = 109)に線色があり、底辺(y=445)に急落していない
        mid_x = 70 + int((1 / 2) * 800)
        expected_y = 25 + 420 - int(0.8 * 420)
        bottom_y = 25 + 420
        self.assertEqual(surf.get_at((mid_x, expected_y))[:3], NODE_COLORS[0])
        self.assertNotEqual(surf.get_at((mid_x, bottom_y))[:3], NODE_COLORS[0])


if __name__ == "__main__":
    unittest.main()
