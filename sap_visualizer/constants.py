"""
SAP-net Visualizer 共通定数定義モジュール
"""

APP_VERSION = "1.1.0"
APP_NAME = "SAP-net Visualizer"


class EventType:
    """SAP-net 動的ログのイベント種別定数"""
    STEP = "STEP"
    ACTIVATION = "ACTIVATION"
    SELECT_PLAN = "SELECT_PLAN"
    WEIGHT_UPDATE = "WEIGHT_UPDATE"
    NEW_EPISODE = "NEW_EPISODE"

    ALL_EVENTS = (STEP, ACTIVATION, SELECT_PLAN, WEIGHT_UPDATE, NEW_EPISODE)


class ViewMode:
    """画面表示モード定数"""
    STEP = "STEP"
    LINE_CHART = "LINE_CHART"


# ウィンドウ・描画基本定数
DEFAULT_WINDOW_WIDTH = 920
DEFAULT_WINDOW_HEIGHT = 690
DEFAULT_FPS = 30
DEFAULT_THRESHOLD = 0.18

# UIレイアウト定数 (タイムラインスライダー: 活性値推移グラフのX座標・横幅と完全一致)
SLIDER_X = 50
SLIDER_WIDTH = 680
SLIDER_MARGIN_X = 50
SLIDER_Y = 550
SLIDER_HEIGHT = 15


# ヘッダー領域
SUBHEADER_Y = 46
SUBHEADER_MAX_WIDTH = 880

