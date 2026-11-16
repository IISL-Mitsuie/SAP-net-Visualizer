import os
import unittest
import tempfile
import shutil
import yaml
from sap_visualizer.config_loader import (
    load_config_data,
    load_raw_config,
    get_config_threshold,
)


class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_load_config_with_valid_yaml(self):
        config_dict = {
            "EXPERIMENT": {
                "MAX_EPISODES": 500,
                "MAX_STEPS": 1000,
                "GOAL_POSITION": [1.0, 2.0, 0.5]
            },
            "SAP": {
                "THRESHOLD": 0.15,
                "ATTENUATION": 0.05,
                "ENABLE_LOG": True
            },
            "CUSTOM_SIMULATION_SECTION": {
                "DRONE_MASS": 1.25,
                "PID_GAINS": {
                    "KP": 1.0,
                    "KI": 0.1,
                    "KD": 0.05
                }
            }
        }
        yaml_path = os.path.join(self.test_dir, "config_used_20260827_120000.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f)

        dummy_log_path = os.path.join(self.test_dir, "sap_dynamic_log.jsonl.gz")
        with open(dummy_log_path, "w") as f:
            f.write("")

        items, yaml_loaded = load_config_data(dummy_log_path)
        self.assertTrue(yaml_loaded)

        # セクション見出しとパラメータデータ行の存在確認
        section_headers = [it["key"] for it in items if it["is_section"]]
        self.assertIn("EXPERIMENT", section_headers)
        self.assertIn("SAP", section_headers)
        self.assertIn("CUSTOM_SIMULATION_SECTION", section_headers)

        param_keys = [it["key"] for it in items if not it["is_section"]]
        self.assertIn("MAX_EPISODES", param_keys)
        self.assertIn("THRESHOLD", param_keys)
        self.assertIn("GOAL_POSITION", param_keys)
        # ネストされたキーの展開確認
        self.assertIn("PID_GAINS.KP", param_keys)

        # 生の辞書取得テスト
        raw_cfg = load_raw_config(dummy_log_path)
        self.assertIsNotNone(raw_cfg)
        self.assertEqual(raw_cfg["SAP"]["THRESHOLD"], 0.15)
        self.assertEqual(raw_cfg["CUSTOM_SIMULATION_SECTION"]["DRONE_MASS"], 1.25)

        # SAP.THRESHOLD 抽出テスト
        thresh = get_config_threshold(dummy_log_path)
        self.assertEqual(thresh, 0.15)

    def test_load_config_without_yaml(self):
        dummy_log_path = os.path.join(self.test_dir, "sap_dynamic_log.jsonl.gz")
        with open(dummy_log_path, "w") as f:
            f.write("")

        items, yaml_loaded = load_config_data(dummy_log_path)
        self.assertFalse(yaml_loaded)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["key"], "CONFIG_STATUS")

        self.assertIsNone(load_raw_config(dummy_log_path))
        self.assertIsNone(get_config_threshold(dummy_log_path))

    def test_load_windows_path_and_lowercase_continual_yaml(self):
        r"""Windowsパス(\S,\o,\a,\p,\t等)・小文字キー・2次元リスト・空文字・nullを含むYAMLの読み込み"""
        yaml_text = """\
meta:
  target_script: "robotino_rl_control.py"
mode:
  name: S-SAP
git:
  commit_hash: "812f063"
control:
  move_speed: 0.1
environment:
  goal_distance_thresholds: [0.5, 4.0, 7.5, 11.0]
reward:
  reward_goal: 100.0
  near_wall_threshold: 0.5
qlearning:
  alpha: 0.1
sap:
  q_span_threshold: 0.5
  activation: 0.15
  threshold: 0.20
runtime:
  stuck_intervention_threshold: 100
continual_learning:
  goal_list:
    - [11.0, 3.0, 0.0]
    - [15.0, 5.0, 0.0]
  policy:
    reuse_policy_prefix: ""
    escaped_quote: "say \\"hi\\""
    already_escaped: "dir\\\\sub"
    files:
      - "output_robotino_rl_control\\S-SAP_continual\\output_20261109_222837\\acquired_policies_20261109_222837\\policy_task1.npy"
      - "output_robotino_rl_control\\S-SAP_continual\\output_20261109_222837\\acquired_policies_20261109_222837\\task2.npy"
  convergence:
    success_rate_threshold: 1.0
    step_tolerance:
    max_step_threshold: null
"""
        yaml_path = os.path.join(self.test_dir, "config_used_20261109_222837.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_text)

        dummy_log_path = os.path.join(self.test_dir, "sap_dynamic_log_20261109_222837.jsonl.gz")
        with open(dummy_log_path, "w", encoding="utf-8") as f:
            f.write("")

        raw_cfg = load_raw_config(dummy_log_path)
        self.assertIsNotNone(raw_cfg)

        # \a, \t, \S, \o, \p が制御文字化けやエラーにならずそのまま保持されること
        policy_cfg = raw_cfg["continual_learning"]["policy"]
        self.assertEqual(
            policy_cfg["files"][0],
            r"output_robotino_rl_control\S-SAP_continual\output_20261109_222837\acquired_policies_20261109_222837\policy_task1.npy",
        )
        self.assertEqual(
            policy_cfg["files"][1],
            r"output_robotino_rl_control\S-SAP_continual\output_20261109_222837\acquired_policies_20261109_222837\task2.npy",
        )
        self.assertNotIn("\x07", policy_cfg["files"][0])
        self.assertNotIn("\t", policy_cfg["files"][1])
        self.assertEqual(policy_cfg["escaped_quote"], 'say "hi"')
        self.assertEqual(policy_cfg["already_escaped"], r"dir\sub")

        # 他の *_threshold が先に存在しても sap.threshold (0.20) のみ正確に取得すること
        self.assertEqual(get_config_threshold(dummy_log_path), 0.20)

        # load_config_data で全10セクション・空文字 "" と null の区別・2次元リストが整形されること
        items, yaml_loaded = load_config_data(dummy_log_path)
        self.assertTrue(yaml_loaded)
        section_headers = [it["key"] for it in items if it["is_section"]]
        self.assertEqual(
            section_headers,
            [
                "META",
                "MODE",
                "GIT",
                "CONTROL",
                "ENVIRONMENT",
                "REWARD",
                "QLEARNING",
                "SAP",
                "RUNTIME",
                "CONTINUAL_LEARNING",
            ],
        )

        by_key = {it["key"]: it for it in items if not it["is_section"]}
        self.assertEqual(by_key["policy.reuse_policy_prefix"]["value"], '""')
        self.assertEqual(by_key["policy.reuse_policy_prefix"]["val_type"], "str")
        self.assertEqual(by_key["convergence.step_tolerance"]["value"], "-")
        self.assertEqual(by_key["convergence.step_tolerance"]["val_type"], "none")
        self.assertEqual(by_key["convergence.max_step_threshold"]["value"], "-")
        self.assertEqual(by_key["convergence.max_step_threshold"]["val_type"], "none")
        self.assertEqual(by_key["goal_list"]["val_type"], "list")
        self.assertIn("[11.0, 3.0, 0.0]", by_key["goal_list"]["value"])

    def test_get_config_threshold_ignores_bool_and_non_exact_keys(self):
        """bool型やq_span_threshold/near_wall_threshold等を誤検出せず、全体フォールバックも厳密一致すること"""
        yaml_path = os.path.join(self.test_dir, "config_used_20261110_010101.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(
                """\
reward:
  near_wall_threshold: 0.5
sap:
  q_span_threshold: 0.5
  threshold: true
other:
  sap_threshold: 0.35
"""
            )
        # sap.threshold が bool のためスキップされ、全体探索の exact match (sap_threshold=0.35) を返す
        self.assertEqual(get_config_threshold(yaml_path), 0.35)

    def test_resolve_yaml_direct_path_dir_and_timestamp_priority(self):
        """YAML直接指定・ディレクトリ指定・タイムスタンプ一致ファイルの優先選択"""
        import time

        yaml_old = os.path.join(self.test_dir, "config_used_20261101_100000.yaml")
        yaml_new = os.path.join(self.test_dir, "config_used_20261109_222837.yaml")
        with open(yaml_old, "w", encoding="utf-8") as f:
            f.write("sap:\n  threshold: 0.11\n")
        with open(yaml_new, "w", encoding="utf-8") as f:
            f.write("sap:\n  threshold: 0.22\n")

        # mtime を明示的に yaml_new > yaml_old に設定
        now = time.time()
        os.utime(yaml_old, (now - 100, now - 100))
        os.utime(yaml_new, (now, now))

        # 1. YAML ファイル直接指定
        self.assertEqual(get_config_threshold(yaml_old), 0.11)
        self.assertEqual(get_config_threshold(yaml_new), 0.22)

        # 2. タイムスタンプ付きログファイル指定時は、更新日時に依らず一致する YAML を優先
        log_old_ts = os.path.join(self.test_dir, "sap_dynamic_log_20261101_100000.jsonl.gz")
        with open(log_old_ts, "w", encoding="utf-8") as f:
            f.write("")
        self.assertEqual(get_config_threshold(log_old_ts), 0.11)

        # 3. ディレクトリ指定時は最新の config_used*.yaml を選択
        self.assertEqual(get_config_threshold(self.test_dir), 0.22)

    def test_overlays_view_highlights_lowercase_threshold_and_reward_keys(self):
        """小文字キー(threshold, reward_goal)でもOverlaysViewの数値ハイライト判定が機能すること"""
        from unittest.mock import MagicMock, patch
        import pygame
        from sap_visualizer.views.overlays import OverlaysView
        from sap_visualizer.theme import COLOR_ACCENT_RED

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.init()

        yaml_path = os.path.join(self.test_dir, "config_used_20261109_222837.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write("reward:\n  reward_goal: 100.0\nsap:\n  threshold: 0.20\nqlearning:\n  alpha: 0.1\n")

        screen = pygame.Surface((920, 700))
        font_small = pygame.font.Font(None, 16)
        font_medium = pygame.font.Font(None, 18)
        font_title = pygame.font.Font(None, 24)

        render_calls = []
        orig_render = font_medium.render

        def spy_render(text, antialias, color, *args, **kwargs):
            render_calls.append((text, color))
            return orig_render(text, antialias, color, *args, **kwargs)

        mock_font_medium = MagicMock(wraps=font_medium)
        mock_font_medium.render.side_effect = spy_render

        view = OverlaysView(
            screen,
            {"small": font_small, "medium": mock_font_medium, "title": font_title},
        )
        with patch.object(view, "font_medium", mock_font_medium):
            view.draw_config_overlay(yaml_path, 0, 920, 700)

        rendered_colors = {text: color for text, color in render_calls}
        self.assertEqual(rendered_colors.get("100.0"), COLOR_ACCENT_RED)
        self.assertEqual(rendered_colors.get("0.2"), COLOR_ACCENT_RED)
        self.assertEqual(rendered_colors.get("0.1"), (20, 90, 180))


if __name__ == "__main__":
    unittest.main()
