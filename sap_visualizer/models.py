"""
SAP-net Visualizer データモデル定義モジュール
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from .constants import EventType, DEFAULT_THRESHOLD


@dataclass
class LogFrame:
    """
    JSONLファイルから読み込んだ1フレーム分の生データを表す型安全なデータモデル。
    外部ログファイルの全フィールド（必須・推奨・任意）に完全対応。
    """
    episode: int
    step: int
    activations: List[float] = field(default_factory=list)          # ログ内の "A"
    weight_matrix: List[List[float]] = field(default_factory=list)     # ログ内の "weight"
    index: int = 0
    event_type: str = EventType.STEP
    plan: Optional[int] = None
    selectplans: List[int] = field(default_factory=list)
    threshold: float = DEFAULT_THRESHOLD
    policyvalue: List[float] = field(default_factory=list)
    reused_action: Optional[int] = None
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogFrame":
        """
        JSONからパースされた生の辞書（dict）を型安全な LogFrame オブジェクトに変換。
        キーの欠損やフォーマットの揺らぎ（最小構成ログやイベント行）を安全に吸収します。
        """
        def _safe_int(val: Any, default: Optional[int] = None) -> Optional[int]:
            if val is None:
                return default
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        def _safe_float(val: Any, default: float = DEFAULT_THRESHOLD) -> float:
            if val is None:
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        raw_a = data.get("A") or []
        raw_weight = data.get("weight") or []
        raw_selectplans = data.get("selectplans") or []
        raw_policyvalue = data.get("policyvalue") or []

        idx_val = _safe_int(data.get("index"), 0)
        ep_val = _safe_int(data.get("episode"), 1)
        st_val = _safe_int(data.get("step"), 0)

        return cls(
            index=idx_val if idx_val is not None else 0,
            episode=ep_val if ep_val is not None else 1,
            step=st_val if st_val is not None else 0,
            event_type=str(data.get("event_type") or EventType.STEP),
            activations=[float(x) for x in raw_a if x is not None],
            weight_matrix=[[float(c) for c in row if c is not None] for row in raw_weight if row],
            plan=_safe_int(data.get("plan"), None),
            selectplans=[int(x) for x in raw_selectplans if x is not None],
            threshold=_safe_float(data.get("threshold"), DEFAULT_THRESHOLD),
            policyvalue=[float(x) for x in raw_policyvalue if x is not None],
            reused_action=_safe_int(data.get("reused_action"), None),
            extra_fields={
                k: v for k, v in data.items()
                if k not in {
                    "index", "episode", "step", "event_type", "A", "weight",
                    "plan", "selectplans", "threshold", "policyvalue", "reused_action"
                }
            }
        )


@dataclass
class ResolvedFrameInfo:
    """
    GUI描画用に過去フレームから欠損値をフォールバック復元した確定情報データモデル。
    """
    plan: Optional[int]
    selectplans: List[int]
    activations: List[float]
    weight_matrix: List[List[float]]
    episode: int
    step: int
    event_type: str
    threshold: float = DEFAULT_THRESHOLD
