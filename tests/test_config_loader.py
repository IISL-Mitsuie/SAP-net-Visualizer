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


if __name__ == "__main__":
    unittest.main()
