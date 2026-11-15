"""
SAP-net Visualizer フォルダ選択履歴管理モジュール
"""
import os
import json
import glob
import datetime
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class FolderHistoryManager:
    """
    SAP-netシミュレーションログフォルダの選択履歴を管理・永続化するクラス。
    ユーザー設定ディレクトリ（~/.sap_visualizer/folder_history.json）にJSON形式で保存。
    """
    def __init__(self, history_file: Optional[str] = None, max_history: int = 30):
        self.max_history = max_history
        if history_file:
            self.history_file = history_file
        else:
            config_dir = os.environ.get("SAP_VISUALIZER_CONFIG_DIR") or os.path.join(
                os.path.expanduser("~"), ".sap_visualizer"
            )
            try:
                os.makedirs(config_dir, exist_ok=True)
                self.history_file = os.path.join(config_dir, "folder_history.json")
            except Exception:
                self.history_file = os.path.abspath("folder_history.json")

        self.history: List[Dict[str, str]] = []
        self.load_history()

    def load_history(self) -> List[Dict[str, str]]:
        """JSONファイルから履歴を読み込む"""
        self.history = []
        if not os.path.exists(self.history_file):
            return self.history

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "recent_folders" in data:
                    raw_list = data["recent_folders"]
                elif isinstance(data, list):
                    raw_list = data
                else:
                    raw_list = []

                for item in raw_list:
                    if isinstance(item, dict) and "path" in item:
                        item["path"] = os.path.abspath(item["path"])
                        self.history.append(item)
        except Exception as e:
            logger.warning(f"Failed to load folder history: {e}")
            self.history = []

        return self.history

    def save_history(self) -> bool:
        """現在の履歴リストをJSONファイルに保存する"""
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            data = {
                "version": "1.0",
                "max_history": self.max_history,
                "recent_folders": self.history[:self.max_history]
            }
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.warning(f"Failed to save folder history: {e}")
            return False

    def add_folder(self, folder_path: str, note: str = "") -> None:
        """フォルダを履歴の先頭に追加（既存にある場合は最新タイムスタンプで先頭に移動）"""
        if not folder_path:
            return

        abs_path = os.path.abspath(folder_path)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.history = [item for item in self.history if os.path.abspath(item.get("path", "")) != abs_path]

        new_entry = {
            "path": abs_path,
            "last_opened": now_str,
            "note": note
        }
        self.history.insert(0, new_entry)

        if len(self.history) > self.max_history:
            self.history = self.history[:self.max_history]

        self.save_history()

    def remove_folder(self, folder_path: str) -> None:
        """指定したパスを履歴から削除"""
        abs_path = os.path.abspath(folder_path)
        self.history = [item for item in self.history if os.path.abspath(item.get("path", "")) != abs_path]
        self.save_history()

    def clear_history(self) -> None:
        """すべての履歴をクリア"""
        self.history = []
        self.save_history()

    def get_detailed_history(self) -> List[Dict[str, str]]:
        """UI表示用に各履歴フォルダの存在確認・ログ状態を付与した詳細リストを返す"""
        detailed = []
        for item in self.history:
            path = item.get("path", "")
            last_opened = item.get("last_opened", "")

            exists = os.path.exists(path) and os.path.isdir(path)
            status_text = ""
            log_found = False

            if not exists:
                status_text = "✕ フォルダ未検出"
            else:
                log_files = glob.glob(os.path.join(path, "sap_dynamic_log_*.jsonl*"))
                if not log_files:
                    log_files = glob.glob(os.path.join(path, "*.jsonl*"))

                if log_files:
                    status_text = "● 正常 (ログ検出)"
                    log_found = True
                else:
                    status_text = "▲ ログ未検出"

            folder_name = os.path.basename(path) if path else ""
            if not folder_name and path:
                folder_name = path

            detailed.append({
                "folder_name": folder_name,
                "path": path,
                "last_opened": last_opened,
                "status": status_text,
                "exists": exists,
                "log_found": log_found
            })
        return detailed
