"""
SAP-net Visualizer ファイルロギング・未捕捉例外フック設定モジュール
"""
import os
import sys
import logging
import threading
from logging.handlers import RotatingFileHandler
from typing import Optional

DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
MAX_LOG_BYTES = 1_000_000
LOG_BACKUP_COUNT = 3
_MANAGED_HANDLER_ATTR = "_sap_visualizer_managed"


def get_log_dir() -> str:
    """ログ保存先ディレクトリ (~/.sap_visualizer/logs 等) を取得し、存在しなければ作成する"""
    config_dir = os.environ.get("SAP_VISUALIZER_CONFIG_DIR") or os.path.join(
        os.path.expanduser("~"), ".sap_visualizer"
    )
    log_dir = os.path.join(config_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def _clear_managed_handlers(root_logger: logging.Logger) -> None:
    """setup_logging が登録した既存のハンドラをクローズして除去する"""
    for handler in list(root_logger.handlers):
        if getattr(handler, _MANAGED_HANDLER_ATTR, False):
            root_logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass


def setup_logging(level: int = logging.INFO, log_dir: Optional[str] = None) -> str:
    """
    ルートロガーへ RotatingFileHandler (1MB × 3世代) と、利用可能な場合は StreamHandler を登録する。
    戻り値: 作成した app.log のファイルパス
    """
    target_dir = log_dir or get_log_dir()
    os.makedirs(target_dir, exist_ok=True)
    log_file_path = os.path.join(target_dir, "app.log")

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    _clear_managed_handlers(root_logger)

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    setattr(file_handler, _MANAGED_HANDLER_ATTR, True)
    root_logger.addHandler(file_handler)

    if sys.stderr is not None and getattr(sys.stderr, "name", None) != os.devnull:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        setattr(stream_handler, _MANAGED_HANDLER_ATTR, True)
        root_logger.addHandler(stream_handler)

    return log_file_path


def install_exception_hooks() -> None:
    """メインスレッドおよびワーカースレッドの未捕捉例外をログ記録するフックを登録する"""
    unhandled_logger = logging.getLogger("sap_visualizer.unhandled")
    prev_sys_hook = sys.excepthook
    prev_threading_hook = threading.excepthook

    def _sys_excepthook(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            prev_sys_hook(exc_type, exc_value, exc_traceback)
            return
        unhandled_logger.critical(
            "Uncaught exception in main thread",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        if sys.stderr is not None and getattr(sys.stderr, "name", None) != os.devnull:
            prev_sys_hook(exc_type, exc_value, exc_traceback)

    def _threading_excepthook(args: threading.ExceptHookArgs) -> None:
        if issubclass(args.exc_type, KeyboardInterrupt):
            prev_threading_hook(args)
            return
        thread_name = args.thread.name if args.thread is not None else "unknown"
        unhandled_logger.critical(
            f"Uncaught exception in thread '{thread_name}'",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        if sys.stderr is not None and getattr(sys.stderr, "name", None) != os.devnull:
            prev_threading_hook(args)

    sys.excepthook = _sys_excepthook
    threading.excepthook = _threading_excepthook
