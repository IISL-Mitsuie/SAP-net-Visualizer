import os
import sys
import shutil
import logging
import tempfile
import threading
import unittest
from logging.handlers import RotatingFileHandler
from unittest.mock import patch

# プロジェクトルートをインポートパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sap_visualizer.logging_setup import (
    get_log_dir,
    setup_logging,
    install_exception_hooks,
    _clear_managed_handlers,
)


class TestLoggingSetup(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_sys_excepthook = sys.excepthook
        self.orig_threading_excepthook = threading.excepthook

    def tearDown(self):
        sys.excepthook = self.orig_sys_excepthook
        threading.excepthook = self.orig_threading_excepthook
        _clear_managed_handlers(logging.getLogger())
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_log_dir_respects_env_var(self):
        """SAP_VISUALIZER_CONFIG_DIR配下のlogsディレクトリが作成・返却されること"""
        with patch.dict(os.environ, {"SAP_VISUALIZER_CONFIG_DIR": self.test_dir}):
            log_dir = get_log_dir()
            expected = os.path.join(self.test_dir, "logs")
            self.assertEqual(log_dir, expected)
            self.assertTrue(os.path.isdir(expected))

    def test_setup_logging_creates_file_and_rotates(self):
        """app.logが生成され、1MB超過時にRotatingFileHandlerでローテーションされること"""
        with patch.dict(os.environ, {"SAP_VISUALIZER_CONFIG_DIR": self.test_dir}):
            log_path = setup_logging()

        self.assertTrue(os.path.exists(log_path))
        root = logging.getLogger()
        rotating_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        self.assertEqual(len(rotating_handlers), 1)
        self.assertEqual(rotating_handlers[0].maxBytes, 1_000_000)
        self.assertEqual(rotating_handlers[0].backupCount, 3)

        test_logger = logging.getLogger("test_rotation")
        payload = "X" * 2048
        for _ in range(550):
            test_logger.info(payload)
        for h in rotating_handlers:
            h.flush()

        rotated_path = f"{log_path}.1"
        self.assertTrue(os.path.exists(rotated_path), "1MB超過後にapp.log.1が生成されるべき")

    def test_setup_logging_skips_stream_handler_when_stderr_is_devnull(self):
        """windowed起動でsys.stderrがdevnullのときはStreamHandlerが追加されないこと"""
        with patch.dict(os.environ, {"SAP_VISUALIZER_CONFIG_DIR": self.test_dir}), \
             open(os.devnull, "w", encoding="utf-8") as devnull_f, \
             patch.object(sys, "stderr", devnull_f):
            setup_logging()
            root = logging.getLogger()
            managed_non_file = [
                h for h in root.handlers
                if getattr(h, "_sap_visualizer_managed", False)
                and not isinstance(h, RotatingFileHandler)
            ]
            self.assertEqual(managed_non_file, [])

    def test_install_exception_hooks_logs_main_and_thread_exceptions(self):
        """メインスレッドとワーカースレッドの未捕捉例外がapp.logに記録されること"""
        with patch.dict(os.environ, {"SAP_VISUALIZER_CONFIG_DIR": self.test_dir}):
            log_path = setup_logging()

        with open(os.devnull, "w", encoding="utf-8") as devnull_f, \
             patch.object(sys, "stderr", devnull_f):
            install_exception_hooks()

            # メインスレッド未捕捉例外のシミュレート
            try:
                raise RuntimeError("main_thread_boom")
            except RuntimeError as e:
                sys.excepthook(type(e), e, e.__traceback__)

            # ワーカースレッド未捕捉例外のシミュレート
            def _worker():
                raise ValueError("worker_thread_boom")

            t = threading.Thread(target=_worker, name="test-worker")
            t.start()
            t.join(timeout=3.0)

        for h in logging.getLogger().handlers:
            h.flush()

        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Uncaught exception in main thread", content)
        self.assertIn("RuntimeError: main_thread_boom", content)
        self.assertIn("Uncaught exception in thread 'test-worker'", content)
        self.assertIn("ValueError: worker_thread_boom", content)


if __name__ == "__main__":
    unittest.main()
