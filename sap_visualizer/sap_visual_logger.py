import os
import json
import gzip

class SAPVisualLogger:
    """
    SAP-netの動的パラメータログファイル（.jsonl.gz / .jsonl）の読み込み・パース
    およびメモリバッファ管理を行うクラス（ビューアー用）。
    """
    def __init__(self, log_dir=None, timestamp=None, enabled=True, **kwargs):
        self.enabled = enabled
        self.log_dir = log_dir
        self.timestamp = timestamp
        self.history = []  # メモリ内の全フレーム記録リスト
        self.log_file_path = None
        self.last_error_msg = ""
        self.last_missing_file_type = ""

    def load_from_file(self, log_file_path):
        """
        保存されたJSONL (.jsonl / .jsonl.gz) ファイルからログを読み込む（オフラインビューアー用）。
        中途終了等でファイル末尾が破損している場合でも、正常に解凍・パースできたフレームを最大限レスキューします。
        """
        self.history = []
        self.log_file_path = log_file_path
        if not os.path.exists(log_file_path):
            self.last_error_msg = f"SAP動的ログファイルが見つかりません: {log_file_path}"
            self.last_missing_file_type = "SAP動的パラメータログファイル (*.jsonl.gz / *.jsonl)"
            print(f"[ERROR] {self.last_error_msg}")
            return False
            
        is_gz = log_file_path.endswith(".gz")
        read_error = None
        
        try:
            open_func = gzip.open if is_gz else open
            with open_func(log_file_path, "rt", encoding="utf-8", errors="replace") as f:
                while True:
                    try:
                        line = f.readline()
                        if not line:
                            break
                        line_str = line.strip()
                        if line_str:
                            self.history.append(json.loads(line_str))
                    except json.JSONDecodeError as je:
                        print(f"[WARNING] Skipping corrupted JSON line in log file: {je}")
                    except Exception as err:
                        read_error = err
                        print(f"[WARNING] Compressed stream ended or corrupted during read: {err}")
                        break
        except Exception as open_err:
            self.last_error_msg = f"ログファイルの解凍/オープンに失敗しました ({type(open_err).__name__}: {open_err})"
            self.last_missing_file_type = "SAP動的パラメータログファイル (オープン不可)"
            print(f"[ERROR] {self.last_error_msg}")
            return False

        if len(self.history) > 0:
            if read_error:
                print(f"[WARNING] Loaded {len(self.history)} valid frames, but log was truncated ({read_error})")
                self.last_error_msg = f"一部データが末尾破損により切れていますが、正常な {len(self.history)} フレームを救出・復元しました ({read_error})"
            else:
                print(f"[INFO] Loaded {len(self.history)} SAP visual log frames from {log_file_path}")
            return True
        else:
            err_detail = f" ({read_error})" if read_error else " (有効データ0件)"
            self.last_error_msg = f"SAP動的ログファイルから有効なデータフレームが読み込めませんでした{err_detail}。"
            self.last_missing_file_type = "SAP動的パラメータログファイル (破損・データなし)"
            print(f"[ERROR] {self.last_error_msg}")
            return False

    def load_from_folder(self, folder_path):
        """
        指定された実験ログフォルダから SAP動的ログファイル (*.jsonl.gz / *.jsonl) を探索して読み込む
        """
        self.last_error_msg = ""
        self.last_missing_file_type = ""

        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            self.last_error_msg = f"指定されたフォルダが存在しません: {folder_path}"
            self.last_missing_file_type = "実験ログフォルダ"
            print(f"[ERROR] {self.last_error_msg}")
            return False

        import glob
        # 1. 優先パターン: sap_dynamic_log_*.jsonl.gz / *.jsonl
        log_files = glob.glob(os.path.join(folder_path, "sap_dynamic_log_*.jsonl*"))
        if not log_files:
            # 2. 汎用パターン: *.jsonl.gz / *.jsonl
            log_files = glob.glob(os.path.join(folder_path, "*.jsonl*"))

        if not log_files:
            # 3. サブフォルダ探索フォールバック
            log_files = glob.glob(os.path.join(folder_path, "**", "sap_dynamic_log_*.jsonl*"), recursive=True)

        if not log_files:
            self.last_error_msg = "フォルダ内に【SAP動的パラメータログファイル (*.jsonl.gz / *.jsonl)】が見つかりませんでした。"
            self.last_missing_file_type = "SAP動的パラメータログファイル (*.jsonl.gz / *.jsonl)"
            print(f"[ERROR] {self.last_error_msg} ({folder_path})")
            return False

        # 複数存在する場合は最も更新日時の新しいファイルを採用
        target_log_file = max(log_files, key=os.path.getmtime)
        print(f"[INFO] Found log file in folder: {target_log_file}")

        success = self.load_from_file(target_log_file)
        if not success:
            file_name = os.path.basename(target_log_file)
            detail = f"\n詳細: {self.last_error_msg}" if self.last_error_msg else ""
            self.last_error_msg = f"【SAP動的パラメータログファイル ({file_name})】の読み込み・パースに失敗しました。{detail}"
            self.last_missing_file_type = "SAP動的パラメータログファイル (破損・パースエラー)"

        return success

    def get_frame(self, index):
        """指定したインデックスのフレームを返す"""
        if 0 <= index < len(self.history):
            return self.history[index]
        return None

    def find_next_event_index(self, current_index, event_type):
        """指定したイベント種別（ACTIVATION, SELECT_PLAN, WEIGHT_UPDATE, NEW_EPISODE）の次のフレームインデックスを検索"""
        for i in range(current_index + 1, len(self.history)):
            frame = self.history[i]
            if event_type == "NEW_EPISODE":
                if frame["episode"] > self.history[current_index]["episode"]:
                    return i
            elif frame["event_type"] == event_type:
                return i
        return current_index

    def find_prev_event_index(self, current_index, event_type):
        """指定したイベント種別の直前のフレームインデックスを逆順検索"""
        if current_index <= 0 or not self.history:
            return 0

        curr_ep = self.history[current_index]["episode"]

        for i in range(current_index - 1, -1, -1):
            frame = self.history[i]
            if event_type == "NEW_EPISODE":
                if frame["episode"] < curr_ep:
                    target_ep = frame["episode"]
                    for j in range(i, -1, -1):
                        if self.history[j]["episode"] < target_ep:
                            return j + 1
                    return 0
            elif frame["event_type"] == event_type:
                return i
        return 0
