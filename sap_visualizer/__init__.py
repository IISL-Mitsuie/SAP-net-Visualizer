"""
SAP-net Visualizer & Logger Package
"""
from .constants import APP_VERSION, APP_NAME
from .sap_visual_logger import SAPVisualLogger
from .sap_visualizer_gui import SAPVisualizerGUI
from .history_manager import FolderHistoryManager
from .folder_selector_gui import FolderSelectorDialog, select_simulation_folder
from .logging_setup import get_log_dir, setup_logging, install_exception_hooks
from .updater import (
    UpdateInfo,
    UpdateVerificationError,
    compare_versions,
    is_newer_version,
    fetch_latest_release_info,
    check_for_updates_async,
    download_installer,
    launch_installer,
    launch_installer_and_exit,
)

__version__ = APP_VERSION

__all__ = [
    "__version__",
    "APP_VERSION",
    "APP_NAME",
    "SAPVisualLogger",
    "SAPVisualizerGUI",
    "FolderHistoryManager",
    "FolderSelectorDialog",
    "select_simulation_folder",
    "get_log_dir",
    "setup_logging",
    "install_exception_hooks",
    "UpdateInfo",
    "UpdateVerificationError",
    "compare_versions",
    "is_newer_version",
    "fetch_latest_release_info",
    "check_for_updates_async",
    "download_installer",
    "launch_installer",
    "launch_installer_and_exit",
]

