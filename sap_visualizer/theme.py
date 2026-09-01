"""
SAP-net Visualizer デザインテーマ・カラーパレット・フォント定義モジュール
"""
from typing import Tuple, List

# ==============================================================================
# 統一カラーパレット定義 (RGBタプル & HEX文字列)
# ==============================================================================

# 背景色
COLOR_BG_MAIN: Tuple[int, int, int] = (240, 243, 246)       # #f0f3f6 メイン背景
COLOR_BG_CARD: Tuple[int, int, int] = (255, 255, 255)       # #ffffff カード・パネル背景
COLOR_BG_HEADER: Tuple[int, int, int] = (228, 235, 243)     # #e4ebf3 テーブルヘッダー
COLOR_BG_ZEBRA: Tuple[int, int, int] = (242, 246, 252)      # テーブル奇数行背景
COLOR_BG_PANEL: Tuple[int, int, int] = (248, 250, 253)      # 凡例・操作パネル背景

# 枠線色
COLOR_BORDER_DEFAULT: Tuple[int, int, int] = (190, 205, 225) # #becde1 通常枠線
COLOR_BORDER_STRONG: Tuple[int, int, int] = (140, 160, 180)  # 強調枠線
COLOR_BORDER_FOCUS: Tuple[int, int, int] = (40, 100, 180)    # フォーカス枠線
COLOR_BORDER_LIGHT: Tuple[int, int, int] = (230, 236, 244)   # 区切り線

# テキスト色
COLOR_TEXT_TITLE: Tuple[int, int, int] = (20, 40, 75)        # 濃紺タイトル
COLOR_TEXT_BODY: Tuple[int, int, int] = (30, 50, 80)         # 本文テキスト
COLOR_TEXT_MUTED: Tuple[int, int, int] = (90, 115, 142)      # 補足・注釈
COLOR_TEXT_WHITE: Tuple[int, int, int] = (255, 255, 255)     # 白文字

# アクセント・状態色
COLOR_ACCENT_BLUE: Tuple[int, int, int] = (30, 80, 162)      # プライマリブルー
COLOR_ACCENT_BLUE_LIGHT: Tuple[int, int, int] = (215, 235, 255)
COLOR_ACCENT_GOLD: Tuple[int, int, int] = (255, 215, 0)      # 選択中知識 (ゴールド)
COLOR_ACCENT_GREEN: Tuple[int, int, int] = (50, 205, 50)     # 転移候補 (グリーン)
COLOR_ACCENT_RED: Tuple[int, int, int] = (220, 50, 50)       # 閾値・活性高 (レッド)

# インジケーター・バッジ用
COLOR_LIVE_BG: Tuple[int, int, int] = (225, 245, 230)
COLOR_LIVE_BORDER: Tuple[int, int, int] = (40, 160, 60)
COLOR_LIVE_TEXT: Tuple[int, int, int] = (20, 100, 40)

COLOR_MANUAL_BG: Tuple[int, int, int] = (255, 243, 220)
COLOR_MANUAL_BORDER: Tuple[int, int, int] = (210, 140, 20)
COLOR_MANUAL_TEXT: Tuple[int, int, int] = (140, 80, 10)

# 重みエッジ用
COLOR_WEIGHT_DEFAULT: Tuple[int, int, int] = (160, 175, 195)
COLOR_WEIGHT_ENHANCED: Tuple[int, int, int] = (35, 95, 215)

# スライダー用
COLOR_SLIDER_TRACK: Tuple[int, int, int] = (200, 210, 220)
COLOR_SLIDER_HANDLE: Tuple[int, int, int] = (40, 100, 220)

# 知識別折れ線グラフ用マルチカラーパレット (視認性の高い20色)
NODE_COLORS: List[Tuple[int, int, int]] = [
    (31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189),
    (140, 86, 75), (227, 119, 194), (127, 127, 127), (188, 189, 34), (23, 190, 207),
    (255, 152, 150), (174, 199, 232), (152, 223, 138), (197, 176, 213), (196, 156, 148),
    (247, 182, 210), (199, 199, 199), (219, 219, 141), (158, 218, 229), (255, 187, 120)
]

# ==============================================================================
# Tkinter用 HEX カラー定義 (Pygame メイン画面デザインシステムと完全同期)
# ==============================================================================
TK_BG_MAIN = "#f0f3f6"
TK_BG_CARD = "#ffffff"
TK_BG_HEADER = "#e4ebf3"
TK_BG_ZEBRA = "#f7f9fc"
TK_BG_PANEL = "#f8fafd"

TK_BORDER_COLOR = "#becde1"
TK_BORDER_STRONG = "#8ca0b4"
TK_BORDER_FOCUS = "#2864b4"
TK_BORDER_LIGHT = "#e6ecf4"

TK_TEXT_TITLE = "#14284b"
TK_TEXT_BODY = "#1e3250"
TK_TEXT_MUTED = "#5a738e"
TK_TEXT_PLACEHOLDER = "#8c9ba5"

# プライマリボタン (濃紺)
TK_ACCENT_BLUE = "#1e50a2"
TK_ACCENT_BLUE_HOVER = "#143c7d"
TK_ACCENT_BLUE_LIGHT = "#d7ebff"

# セカンダリボタン (白・ソフトブルー ＋ くっきりとしたブルー枠線)
TK_BTN_SECONDARY_BG = "#ffffff"
TK_BTN_SECONDARY_HOVER = "#d5e5f8"
TK_BTN_SECONDARY_BORDER = "#7c9ec4"
TK_BTN_SECONDARY_TEXT = "#14284b"

# 危険・削除ボタン (白・ソフトレッド ＋ くっきりとしたレッド枠線)
TK_BTN_DANGER_BG = "#ffffff"
TK_BTN_DANGER_HOVER = "#fde2e2"
TK_BTN_DANGER_BORDER = "#d87878"
TK_BTN_DANGER_TEXT = "#a02020"


# 状態バッジカラー
TK_STATUS_OK_BG = "#e1f5e6"
TK_STATUS_OK_FG = "#146428"
TK_STATUS_WARN_BG = "#fff3dc"
TK_STATUS_WARN_FG = "#a05a00"
TK_STATUS_ERR_BG = "#f0f2f5"
TK_STATUS_ERR_FG = "#788898"


# ==============================================================================
# フォント候補リスト
# ==============================================================================
FONT_FAMILY_CANDIDATES: List[str] = [
    "meiryo", "msgothic", "yugothic", "hiragino sans", "takao gothic", "arial"
]
