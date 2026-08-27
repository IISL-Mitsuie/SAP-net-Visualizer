import os
import unittest
import tempfile
import shutil
import yaml
from sap_visualizer.config_loader import (
    load_config_data,
    load_raw_config,
    get_config_threshold,
    get_param_description,
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
                "MAX_STEPS": 1000
            },
            "SAP": {
                "THRESHOLD": 0.15,
                "ATTENUATION": 0.05
            }
        }
        yaml_path = os.path.join(self.test_dir, "config_used_20260827_120000.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f)

        # ログファイルと同じディレクトリを渡す
        dummy_log_path = os.path.join(self.test_dir, "sap_dynamic_log.jsonl.gz")
        with open(dummy_log_path, "w") as f:
            f.write("")

        items, yaml_loaded = load_config_data(dummy_log_path)
        self.assertTrue(yaml_loaded)
        self.assertEqual(len(items), 4)

        param_names = [item[0] for item in items]
        self.assertIn("EXPERIMENT.MAX_EPISODES", param_names)
        self.assertIn("SAP.THRESHOLD", param_names)

        # 生の辞書取得テスト
        raw_cfg = load_raw_config(dummy_log_path)
        self.assertIsNotNone(raw_cfg)
        self.assertEqual(raw_cfg["SAP"]["THRESHOLD"], 0.15)

        # SAP.THRESHOLD 抽出テスト
        thresh = get_config_threshold(dummy_log_path)
        self.assertEqual(thresh, 0.15)

    def test_load_config_without_yaml(self):
        dummy_log_path = os.path.join(self.test_dir, "sap_dynamic_log.jsonl.gz")
        with open(dummy_log_path, "w") as f:
            f.write("")

        items, yaml_loaded = load_config_data(dummy_log_path)
        self.assertFalse(yaml_loaded)
        # 架空のダミー値は生成されず、未読み込みステータスのみが返ることを検証
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][0], "CONFIG_STATUS")
        self.assertEqual(items[0][1], "未読み込み")

        self.assertIsNone(load_raw_config(dummy_log_path))
        self.assertIsNone(get_config_threshold(dummy_log_path))

    def test_get_param_description(self):
        desc = get_param_description("SAP", "THRESHOLD")
        self.assertIn("閾値", desc)

        unknown_desc = get_param_description("UNKNOWN_SECTION", "UNKNOWN_KEY")
        self.assertEqual(unknown_desc, "詳細不明（未定義パラメータ）")


if __name__ == "__main__":
    unittest.main()

