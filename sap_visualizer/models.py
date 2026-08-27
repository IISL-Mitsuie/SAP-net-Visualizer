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
        return cls(
            index=int(data.get("index", 0)),
            episode=int(data.get("episode", 1)),
            step=int(data.get("step", 0)),
            event_type=str(data.get("event_type", EventType.STEP)),
            activations=[float(x) for x in data.get("A", []) if x is not None],
            weight_matrix=[[float(c) for c in row] for row in data.get("weight", []) if row],
            plan=int(data["plan"]) if data.get("plan") is not None else None,
            selectplans=[int(x) for x in data.get("selectplans", []) if x is not None],
            threshold=float(data.get("threshold", DEFAULT_THRESHOLD)),
            policyvalue=[float(x) for x in data.get("policyvalue", []) if x is not None],
            reused_action=int(data["reused_action"]) if data.get("reused_action") is not None else None,
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
