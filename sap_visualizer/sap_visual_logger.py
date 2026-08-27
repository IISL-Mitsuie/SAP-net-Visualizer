"""
SAP-net Visualizer ログローダー・データバッファ管理モジュール
"""
import os
import json
import gzip
import glob
import logging
from typing import List, Optional
from .models import LogFrame, ResolvedFrameInfo
from .constants import EventType, DEFAULT_THRESHOLD
from .config_loader import get_config_threshold

logger = logging.getLogger(__name__)


class SAPVisualLogger:
    """
    SAP-netの動的パラメータログファイル（.jsonl.gz / .jsonl）の読み込み・パース
    およびメモリバッファ管理を行うクラス（ビューアー用）。
    """
    def __init__(self, log_dir: Optional[str] = None, timestamp: Optional[str] = None, enabled: bool = True, **kwargs):
        self.enabled = enabled
        self.log_dir = log_dir
        self.timestamp = timestamp
        self.history: List[LogFrame] = []
        self.log_file_path: Optional[str] = None
        self.max_nodes: int = 0
        self.config_threshold: Optional[float] = None
        self.dominant_threshold: Optional[float] = None
        self.last_error_msg: str = ""
        self.last_missing_file_type: str = ""

    def _update_metadata_cache(self) -> None:
        """ログ読み込み完了時にメタデータ（最大ノード数、パラメータ閾値等）を計算してキャッシュ"""
        max_n = 0
        for f in self.history:
            if len(f.activations) > max_n:
                max_n = len(f.activations)
            if len(f.weight_matrix) > max_n:
                max_n = len(f.weight_matrix)
        self.max_nodes = max_n


        # 1. config_used_*.yaml から SAP.THRESHOLD を探索・取得 (最優先パラメータ)
        self.config_threshold = get_config_threshold(self.log_file_path)

        # 2. ログ内の STEP イベント行から基準 threshold を検出 (イベント行デフォルト値とのブレ防止)
        self.dominant_threshold = None
        if self.history:
            for f in self.history:
                if f.event_type == EventType.STEP and f.threshold is not None:
                    self.dominant_threshold = f.threshold
                    break
            if self.dominant_threshold is None and self.history:
                self.dominant_threshold = self.history[0].threshold

    @property
    def active_threshold(self) -> float:
        """現在アクティブな基準活性化閾値 (float)"""
        if self.config_threshold is not None:
            return self.config_threshold
        if self.dominant_threshold is not None:
            return self.dominant_threshold
        if self.history and self.history[0].threshold is not None:
            return self.history[0].threshold
        return DEFAULT_THRESHOLD


    def load_from_file(self, log_file_path: str) -> bool:
        """
        保存されたJSONL (.jsonl / .jsonl.gz) ファイルからログを読み込む。
        中途終了等でファイル末尾が破損している場合でも、正常に解凍・パースできたフレームを最大限レスキューします。
        """
        self.history = []
        self.max_nodes = 0
        self.log_file_path = log_file_path

        if not os.path.exists(log_file_path):
            self.last_error_msg = f"SAP動的ログファイルが見つかりません: {log_file_path}"
            self.last_missing_file_type = "SAP動的パラメータログファイル (*.jsonl.gz / *.jsonl)"
            logger.error(self.last_error_msg)
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
                            raw_dict = json.loads(line_str)
                            self.history.append(LogFrame.from_dict(raw_dict))
                    except json.JSONDecodeError as je:
                        logger.warning(f"Skipping corrupted JSON line in log file: {je}")
                    except Exception as err:
                        read_error = err
                        logger.warning(f"Compressed stream ended or corrupted during read: {err}")
                        break
        except Exception as open_err:
            self.last_error_msg = f"ログファイルの解凍/オープンに失敗しました ({type(open_err).__name__}: {open_err})"
            self.last_missing_file_type = "SAP動的パラメータログファイル (オープン不可)"
            logger.error(self.last_error_msg)
            return False

        if len(self.history) > 0:
            self._update_metadata_cache()
            if read_error:
                logger.warning(f"Loaded {len(self.history)} valid frames, but log was truncated ({read_error})")
                self.last_error_msg = f"一部データが末尾破損により切れていますが、正常な {len(self.history)} フレームを救出・復元しました ({read_error})"
            else:
                logger.info(f"Loaded {len(self.history)} SAP visual log frames from {log_file_path}")
            return True
        else:
            err_detail = f" ({read_error})" if read_error else " (有効データ0件)"
            self.last_error_msg = f"SAP動的ログファイルから有効なデータフレームが読み込めませんでした{err_detail}。"
            self.last_missing_file_type = "SAP動的パラメータログファイル (破損・データなし)"
            logger.error(self.last_error_msg)
            return False

    def load_from_folder(self, folder_path: str) -> bool:
        """
        指定された実験ログフォルダから SAP動的ログファイル (*.jsonl.gz / *.jsonl) を探索して読み込む。
        """
        self.last_error_msg = ""
        self.last_missing_file_type = ""

        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            self.last_error_msg = f"指定されたフォルダが存在しません: {folder_path}"
            self.last_missing_file_type = "実験ログフォルダ"
            logger.error(self.last_error_msg)
            return False

        # 1. 優先パターン: sap_dynamic_log_*.jsonl.gz / *.jsonl
        log_files = glob.glob(os.path.join(folder_path, "sap_dynamic_log_*.jsonl*"))
        if not log_files:
            # 2. 汎用パターン: *.jsonl.gz / *.jsonl
            log_files = glob.glob(os.path.join(folder_path, "*.jsonl*"))
        if not log_files:
            # 3. サブフォルダ探索
            log_files = glob.glob(os.path.join(folder_path, "**", "sap_dynamic_log_*.jsonl*"), recursive=True)

        if not log_files:
            self.last_error_msg = "フォルダ内に【SAP動的パラメータログファイル (*.jsonl.gz / *.jsonl)】が見つかりませんでした。"
            self.last_missing_file_type = "SAP動的パラメータログファイル (*.jsonl.gz / *.jsonl)"
            logger.error(f"{self.last_error_msg} ({folder_path})")
            return False

        # 複数存在する場合は最新のファイルを採用
        target_log_file = max(log_files, key=os.path.getmtime)
        logger.info(f"Found log file in folder: {target_log_file}")

        success = self.load_from_file(target_log_file)
        if not success:
            file_name = os.path.basename(target_log_file)
            detail = f"\n詳細: {self.last_error_msg}" if self.last_error_msg else ""
            self.last_error_msg = f"【SAP動的パラメータログファイル ({file_name})】の読み込み・パースに失敗しました。{detail}"
            self.last_missing_file_type = "SAP動的パラメータログファイル (破損・パースエラー)"

        return success

    def get_frame(self, index: int) -> Optional[LogFrame]:
        """指定したインデックスのフレームを返す"""
        if 0 <= index < len(self.history):
            return self.history[index]
        return None

    def resolve_frame(self, index: int) -> ResolvedFrameInfo:
        """
        指定インデックスのフレーム情報について、欠損値（A, weight, plan 等）を
        直前の有効フレームから復元（Resolve）した確定情報オブジェクトを生成して返す。
        """
        if not self.history or index < 0 or index >= len(self.history):
            return ResolvedFrameInfo(
                plan=None,
                selectplans=[],
                activations=[],
                weight_matrix=[],
                episode=1,
                step=0,
                event_type=EventType.STEP
            )

        frame = self.history[index]
        plan = frame.plan
        selectplans = frame.selectplans
        A_raw = frame.activations
        weight_raw = frame.weight_matrix
        episode = frame.episode
        step = frame.step
        event_type = frame.event_type
        threshold = frame.threshold

        # 1. 活性値 A の欠損フォールバック
        if not A_raw:
            for k in range(index - 1, -1, -1):
                prev_a = self.history[k].activations
                if prev_a:
                    A_raw = prev_a
                    break

        # 2. 重み行列 weight の欠損フォールバック
        if not weight_raw:
            for k in range(index - 1, -1, -1):
                prev_w = self.history[k].weight_matrix
                if prev_w:
                    weight_raw = prev_w
                    break

        # 3. 選択知識 plan の欠損フォールバック
        if plan is None:
            for k in range(index - 1, -1, -1):
                prev_plan = self.history[k].plan
                if prev_plan is not None:
                    plan = prev_plan
                    break

        # 4. 転移候補 selectplans の欠損フォールバック
        if not selectplans:
            for k in range(index - 1, -1, -1):
                prev_sel = self.history[k].selectplans
                if prev_sel:
                    selectplans = prev_sel
                    break

        # 5. 活性化閾値 threshold の決定（設定ファイルパラメータ最優先 ＆ ログ内一貫性の保証）
        if self.config_threshold is not None:
            threshold = self.config_threshold
        elif self.dominant_threshold is not None:
            threshold = self.dominant_threshold
        else:
            threshold = frame.threshold

        return ResolvedFrameInfo(
            plan=plan,
            selectplans=selectplans,
            activations=A_raw,
            weight_matrix=weight_raw,
            episode=episode,
            step=step,
            event_type=event_type,
            threshold=threshold
        )


    def find_next_event_index(self, current_index: int, event_type: str) -> int:
        """指定したイベント種別の次のフレームインデックスを検索"""
        for i in range(current_index + 1, len(self.history)):
            frame = self.history[i]
            if event_type == EventType.NEW_EPISODE:
                if frame.episode > self.history[current_index].episode:
                    return i
            elif frame.event_type == event_type:
                return i
        return current_index

    def find_prev_event_index(self, current_index: int, event_type: str) -> int:
        """指定したイベント種別の直前のフレームインデックスを逆順検索"""
        if current_index <= 0 or not self.history:
            return 0

        curr_ep = self.history[current_index].episode

        for i in range(current_index - 1, -1, -1):
            frame = self.history[i]
            if event_type == EventType.NEW_EPISODE:
                if frame.episode < curr_ep:
                    target_ep = frame.episode
                    for j in range(i, -1, -1):
                        if self.history[j].episode < target_ep:
                            return j + 1
                    return 0
            elif frame.event_type == event_type:
                return i
        return 0
