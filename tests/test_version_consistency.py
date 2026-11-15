import importlib.util
import re
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# プロジェクトルートをインポートパスに追加
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sap_visualizer import __version__
from sap_visualizer.constants import APP_VERSION


def _load_build_module():
    build_path = ROOT_DIR / "packaging" / "build.py"
    spec = importlib.util.spec_from_file_location("sap_packaging_build", build_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


build_script = _load_build_module()


class TestVersionConsistency(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_app_version_format_and_single_source_of_truth(self):
        """constants.APP_VERSION が MAJOR.MINOR.PATCH 形式であり、build.read_app_version と一致すること"""
        self.assertRegex(APP_VERSION, r"^\d+\.\d+\.\d+$")
        self.assertEqual(__version__, APP_VERSION)
        self.assertEqual(build_script.read_app_version(), APP_VERSION)

    def test_installer_iss_has_no_hardcoded_version(self):
        """packaging/installer.iss にハードコードされた #define MyAppVersion が残っていないこと"""
        iss_path = ROOT_DIR / "packaging" / "installer.iss"
        content = iss_path.read_text(encoding="utf-8")
        self.assertIn("#ifndef MyAppVersion", content)
        self.assertIsNone(
            re.search(r'^\s*#define\s+MyAppVersion\s+"', content, flags=re.MULTILINE),
            "installer.iss must not define a hardcoded MyAppVersion",
        )

    def test_version_info_template_placeholders_and_render(self):
        """version_info.template.txt にプレースホルダーが存在し、render_version_info で正しく展開されること"""
        template_path = ROOT_DIR / "packaging" / "version_info.template.txt"
        self.assertTrue(template_path.exists())
        template_content = template_path.read_text(encoding="utf-8")
        for placeholder in ("$MAJOR", "$MINOR", "$PATCH", "$VERSION"):
            self.assertIn(placeholder, template_content)

        out_path = self.temp_dir / "version_info.txt"
        build_script.render_version_info("2.4.9", out_path, template_path=template_path)
        rendered = out_path.read_text(encoding="utf-8")
        self.assertIn("filevers=(2, 4, 9, 0)", rendered)
        self.assertIn("prodvers=(2, 4, 9, 0)", rendered)
        self.assertIn("StringStruct('FileVersion', '2.4.9.0')", rendered)
        self.assertIn("StringStruct('ProductVersion', '2.4.9.0')", rendered)
        self.assertNotIn("$VERSION", rendered)

    def test_requirements_separation(self):
        """requirements.txt に pyinstaller が含まれず、requirements-build.txt に分離されていること"""
        runtime_req = (ROOT_DIR / "requirements.txt").read_text(encoding="utf-8").lower()
        build_req = (ROOT_DIR / "requirements-build.txt").read_text(encoding="utf-8").lower()
        self.assertNotIn("pyinstaller", runtime_req)
        self.assertIn("-r requirements.txt", build_req)
        self.assertIn("pyinstaller", build_req)

    def test_build_aborts_with_nonzero_exit_on_test_failure(self):
        """テスト失敗時に build.main() が仮想環境を作成せず終了コード 1 で停止すること"""
        with patch.object(build_script, "run_prebuild_tests", return_value=False) as mock_tests, \
             patch.object(build_script.subprocess, "run") as mock_subproc:
            rc = build_script.main([])
        self.assertEqual(rc, 1)
        mock_tests.assert_called_once()
        mock_subproc.assert_not_called()

    def test_build_aborts_with_nonzero_exit_on_iscc_failure(self):
        """ISCC コンパイル失敗時に build.main() が終了コード 1 を返し、/DMyAppVersion を渡すこと"""
        fake_iscc = self.temp_dir / "ISCC.exe"
        fake_iscc.write_text("dummy", encoding="utf-8")

        def _subprocess_side_effect(cmd, *args, **kwargs):
            cmd_str = " ".join(str(x) for x in cmd)
            if "ISCC.exe" in cmd_str:
                return MagicMock(returncode=2)
            return MagicMock(returncode=0)

        with patch.object(build_script, "kill_existing_process"), \
             patch.object(build_script, "safe_rmtree"), \
             patch.object(build_script, "render_version_info", return_value=self.temp_dir / "vi.txt"), \
             patch.object(build_script.subprocess, "run", side_effect=_subprocess_side_effect) as mock_subproc, \
             patch.object(build_script.Path, "exists", return_value=True):
            # tempfile.gettempdir() が実際の temp を壊さないよう、venv/build は real temp で safe_rmtree mock 済み
            rc = build_script.main(["--skip-tests"])

        self.assertEqual(rc, 1)
        iscc_calls = [
            call.args[0] for call in mock_subproc.call_args_list
            if any("ISCC.exe" in str(part) for part in call.args[0])
        ]
        self.assertEqual(len(iscc_calls), 1)
        self.assertIn(f"/DMyAppVersion={APP_VERSION}", iscc_calls[0])


if __name__ == "__main__":
    unittest.main()
