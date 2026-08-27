"""
SAP-net Visualizer ハイパーパラメータ設定ファイル（YAML）読み込み・解説モジュール
"""
import os
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# パラメータ日本語説明辞書
PARAM_DESCRIPTIONS = {
    # Meta
    "META.TARGET_SCRIPT": "実行対象スクリプトファイル名",
    "META.DESCRIPTION": "実験・制御設定の概要メモ",
    # Mode
    "MODE.NAME": "学習モード (RL / S-SAP / Q-SAP)",
    "MODE.USE_SHIELD": "安全性保証シールド機構の有効化",
    # Experiment
    "EXPERIMENT.ENABLE_SAP_VISUALIZER": "SAP動的パラメータ可視化GUIの自動起動",
    "EXPERIMENT.MAX_EPISODES": "最大総エピソード数",
    "EXPERIMENT.MAX_STEPS": "1エピソードあたりの最大ステップ数",
    "EXPERIMENT.GOAL_POSITION": "目標（ゴール）の3次元座標 [X, Y, Z] (m)",
    "EXPERIMENT.INITIAL_POSITION": "ロボット初期配置座標 [X, Y, Z] (m)",
    # Reward
    "REWARD.REWARD_GOAL": "目標到達時のプラス報酬",
    "REWARD.REWARD_COLLISION": "壁衝突時のペナルティ報酬",
    "REWARD.REWARD_STEP": "1ステップごとのタイムペナルティ",
    "REWARD.REWARD_NEAR_WALL": "壁接近時 (<=0.5m) の回避ペナルティ",
    "REWARD.REWARD_SHAPING_COEFF": "距離変化に基づくポテンシャル報酬 (Shaping) 係数",
    "REWARD.REWARD_SHIELD_PENALTY": "シールド介入時のペナルティ",
    # Q-learning
    "QLEARNING.ALPHA": "強化学習の学習率 (alpha)",
    "QLEARNING.GAMMA": "将来報酬の時間割引率 (gamma)",
    "QLEARNING.TAU": "ボルツマン行動選択の温度パラメータ (tau)",
    "QLEARNING.LOAD_Q_TABLE": "既存Qテーブルのロード有効化",
    "QLEARNING.LOAD_Q_TABLE_NAME": "ロード対象Qテーブルファイル名",
    # SAP
    "SAP.ACTIVATION": "知識ノード初期活性値 (Activation)",
    "SAP.THRESHOLD": "知識活性化・転移判断の評価閾値 (Threshold)",
    "SAP.ATTENUATION": "1ステップごとの活性度減衰率 (Attenuation)",
    "SAP.FREQ_ACT": "知識活性化・選択の実行頻度 (ステップ数)",
    "SAP.FREQ_WEIGHT": "知識間重み行列の更新実行頻度 (ステップ数)",
    "SAP.FIRST_WEIGHT": "知識間重み行列の初期値 (Firstweight)",
    "SAP.POSITIVE_ADJUSTMENT": "正の転移発生時の重み増強補正量",
    "SAP.NEGATIVE_ADJUSTMENT": "負の転移発生時の重み抑制補正量",
    "SAP.COLLISION": "負の転移・衝突発生時の活性度ペナルティ",
    "SAP.T_RATE": "他タスク知識の転移適用率 (T_RATE)",
    # Policy
    "POLICY.ALL_POLICY": "登録・管理されている再利用ポリシー（Qテーブル）総数",
    "POLICY.REUSE_POLICY_DIR": "再利用ポリシーファイルの保存ディレクトリ",
    "POLICY.REUSE_POLICY_PREFIX": "ポリシーファイルの接頭辞",
    # Control
    "CONTROL.MOVE_SPEED": "ロボット目標移動速度 (m/s)",
    "CONTROL.STRAFE_VX_CORRECTION": "左右移動時の直進軸補正速度 (m/s)",
    "CONTROL.YAW_KP": "機体姿勢・方角補正のPゲイン",
    "CONTROL.MOVE_DISTANCE": "1行動あたりの移動距離 (m)",
    # Environment
    "ENVIRONMENT.NUM_ACTIONS": "離散行動空間の総行動数",
    "ENVIRONMENT.MIN_DX": "状態空間: X方向相対座標の最小範囲 (m)",
    "ENVIRONMENT.MAX_DX": "状態空間: X方向相対座標の最大範囲 (m)",
    "ENVIRONMENT.MIN_DY": "状態空間: Y方向相対座標の最小範囲 (m)",
    "ENVIRONMENT.MAX_DY": "状態空間: Y方向相対座標の最大範囲 (m)",
}


def get_param_description(section: str, key: str) -> str:
    """セクション名とキー名から日本語解説を取得"""
    full_key = f"{section}.{key}".upper()
    return PARAM_DESCRIPTIONS.get(full_key, "詳細不明（未定義パラメータ）")


def load_raw_config(log_file_path: Optional[str] = None) -> Optional[dict]:
    """
    ログファイルのあるディレクトリから config_used_*.yaml を探索し、生の dict として読み込んで返す。
    """
    if not log_file_path or not os.path.exists(log_file_path):
        return None

    log_dir = os.path.dirname(os.path.abspath(log_file_path))
    yaml_files = [
        os.path.join(log_dir, f)
        for f in os.listdir(log_dir)
        if f.startswith("config_used") and f.endswith(".yaml")
    ]

    if not yaml_files:
        return None

    try:
        import yaml
        with open(yaml_files[0], mode="r", encoding="utf-8") as f:
            raw_yaml = yaml.safe_load(f)
            if isinstance(raw_yaml, dict):
                return raw_yaml
    except Exception as e:
        logger.warning(f"Failed to load raw YAML config file ({yaml_files[0]}): {e}")

    return None


def get_config_threshold(log_file_path: Optional[str] = None) -> Optional[float]:
    """
    config_used_*.yaml から SAP.THRESHOLD を float として取得。見つからない場合は None。
    """
    config = load_raw_config(log_file_path)
    if not config or not isinstance(config, dict):
        return None

    # 大文字小文字の揺らぎを吸収
    sap_sec = None
    for k, v in config.items():
        if isinstance(k, str) and k.upper() == "SAP" and isinstance(v, dict):
            sap_sec = v
            break

    if sap_sec:
        for k, v in sap_sec.items():
            if isinstance(k, str) and k.upper() == "THRESHOLD" and v is not None:
                try:
                    return float(v)
                except (ValueError, TypeError):
                    pass

    return None


def load_config_data(log_file_path: Optional[str] = None) -> Tuple[List[Tuple[str, str, str]], bool]:
    """
    ログファイルのあるディレクトリから config_used_*.yaml を探索・パースして返す。
    
    戻り値:
        Tuple[List[Tuple[パラメータ名, 設定値, 日本語説明]], yaml_loaded(bool)]
    """
    config_items: List[Tuple[str, str, str]] = []
    raw_yaml = load_raw_config(log_file_path)
    if raw_yaml is None:
        if not log_file_path or not os.path.exists(log_file_path):
            return [("CONFIG_STATUS", "未読み込み", "実験ログフォルダ内の config_used_*.yaml は検出されていません")], False
        log_dir = os.path.dirname(os.path.abspath(log_file_path))
        yaml_files = [
            os.path.join(log_dir, f)
            for f in os.listdir(log_dir)
            if f.startswith("config_used") and f.endswith(".yaml")
        ]
        if not yaml_files:
            return [("CONFIG_STATUS", "未読み込み", "フォルダ内に config_used_*.yaml が存在しません")], False
        return [("CONFIG_STATUS", "パース失敗", f"設定ファイル ({os.path.basename(yaml_files[0])}) の解析に失敗しました")], False

    for section, params in raw_yaml.items():
        if isinstance(params, dict):
            for key, val in params.items():
                v_str = str(val).strip().replace("\n", "") if val is not None else ""
                if not v_str or v_str.lower() in ("none", "null", "nan", "empty", "[]", "{}"):
                    v_str = "-"
                desc = get_param_description(section, key)
                config_items.append((f"{section}.{key}".upper(), v_str, desc))
    if config_items:
        return config_items, True

    return [("CONFIG_STATUS", "パース失敗", "設定ファイルの解析に失敗しました")], False

