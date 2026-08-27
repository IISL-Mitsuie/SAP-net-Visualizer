"""
SAP-net Visualizer モーダルダイアログ（設定確認 ＆ 操作ガイド）描画ビュー
"""
import pygame
from typing import Dict, Optional, List, Tuple
from .base_view import BaseView
from ..config_loader import load_config_data
from ..utils.geometry_utils import wrap_text_to_lines
from ..theme import (
    COLOR_BG_CARD,
    COLOR_BG_ZEBRA,
    COLOR_BORDER_FOCUS,
    COLOR_BORDER_DEFAULT,
    COLOR_BORDER_LIGHT,
    COLOR_TEXT_TITLE,
    COLOR_TEXT_BODY,
    COLOR_TEXT_MUTED,
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GOLD,
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_RED,
    COLOR_WEIGHT_ENHANCED,
)


class OverlaysView(BaseView):
    """ハイパーパラメータ設定モーダルおよびヘルプ・操作ガイドモーダルを担当するビュークラス"""
    def __init__(self, screen: pygame.Surface, fonts: Dict[str, pygame.font.Font]):
        super().__init__(screen, fonts)

    def draw_config_overlay(
        self,
        log_file_path: Optional[str],
        scroll_y: int,
        window_width: int,
        window_height: int
    ) -> int:
        """
        ハイパーパラメータ・学習設定一覧ダイアログの描画 (1列高視認性・文字自動改行＆スクロール対応)
        戻り値: max_scroll (int) スクロール最大可能量
        """
        # 1. 暗色半透明バックドロップ
        overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        overlay.fill((10, 20, 30, 215))
        self.screen.blit(overlay, (0, 0))

        # 2. メインモーダルウィンドウ枠 (860 x 635 px)
        dlg_x, dlg_y = 30, 25
        dlg_w, dlg_h = 860, 635
        pygame.draw.rect(self.screen, (250, 252, 255), (dlg_x, dlg_y, dlg_w, dlg_h), border_radius=10)
        pygame.draw.rect(self.screen, COLOR_BORDER_FOCUS, (dlg_x, dlg_y, dlg_w, dlg_h), 3, border_radius=10)

        # 3. タイトルヘッダー
        cfg_title = self.font_title.render("ハイパーパラメータ ＆ システム学習設定一覧", True, COLOR_TEXT_TITLE)
        self.screen.blit(cfg_title, (dlg_x + 25, dlg_y + 16))
        pygame.draw.line(self.screen, COLOR_BORDER_DEFAULT, (dlg_x + 20, dlg_y + 50), (dlg_x + dlg_w - 20, dlg_y + 50), 2)

        # 4. データ読み込み
        config_items, yaml_loaded = load_config_data(log_file_path)

        # 5. カラムヘッダー描画
        head_y = dlg_y + 58
        th_param = self.font_medium.render("パラメータ名", True, COLOR_TEXT_MUTED)
        th_val = self.font_medium.render("設定値", True, COLOR_TEXT_MUTED)
        th_desc = self.font_medium.render("概要・説明", True, COLOR_TEXT_MUTED)

        col_param_x = dlg_x + 25
        col_val_x = dlg_x + 265
        col_desc_x = dlg_x + 425

        self.screen.blit(th_param, (col_param_x, head_y))
        self.screen.blit(th_val, (col_val_x, head_y))
        self.screen.blit(th_desc, (col_desc_x, head_y))
        pygame.draw.line(self.screen, (200, 212, 230), (dlg_x + 20, head_y + 24), (dlg_x + dlg_w - 20, head_y + 24), 2)

        # 6. テーブルコンテンツのクリッピング可視領域定義
        content_top = head_y + 28
        content_h = dlg_h - 145
        content_rect = pygame.Rect(dlg_x + 15, content_top, dlg_w - 30, content_h)

        old_clip = self.screen.get_clip()
        self.screen.set_clip(content_rect)

        y_curr = content_top - scroll_y
        get_w_func = lambda s: self.font_small.size(s)[0]

        for idx, item in enumerate(config_items):
            name_str = str(item[0]).strip().replace("\n", "")
            val_str = str(item[1]).strip().replace("\n", "") if item[1] is not None else "-"
            desc_str = str(item[2]).strip().replace("\n", "") if len(item) > 2 else ""

            name_lines = wrap_text_to_lines(name_str, get_w_func, 230)
            val_lines = wrap_text_to_lines(val_str, lambda s: self.font_medium.size(s)[0], 150)
            desc_lines = wrap_text_to_lines(desc_str, get_w_func, 400)

            val_color = COLOR_ACCENT_RED if ("SAP" in name_str or "REWARD" in name_str) else (25, 115, 45)

            name_surfs = [self.font_small.render(l, True, (25, 55, 115)) for l in name_lines]
            val_surfs = [self.font_medium.render(l, True, val_color) for l in val_lines]
            desc_surfs = [self.font_small.render(l, True, (80, 90, 110)) for l in desc_lines]

            max_lines = max(len(name_surfs), len(val_surfs), len(desc_surfs), 1)
            line_h = 19
            row_padding = 8
            item_h = max(30, max_lines * line_h + row_padding)

            if y_curr + item_h >= content_top and y_curr <= content_top + content_h:
                if idx % 2 == 1:
                    pygame.draw.rect(self.screen, COLOR_BG_ZEBRA, (dlg_x + 20, y_curr, dlg_w - 40, item_h - 2), border_radius=4)

                for i, srf in enumerate(name_surfs):
                    self.screen.blit(srf, (col_param_x, y_curr + 4 + i * line_h))

                for i, srf in enumerate(val_surfs):
                    self.screen.blit(srf, (col_val_x, y_curr + 4 + i * line_h))

                for i, srf in enumerate(desc_surfs):
                    self.screen.blit(srf, (col_desc_x, y_curr + 4 + i * line_h))

                pygame.draw.line(self.screen, COLOR_BORDER_LIGHT, (dlg_x + 20, y_curr + item_h - 1), (dlg_x + dlg_w - 20, y_curr + item_h - 1), 1)

            y_curr += item_h

        self.screen.set_clip(old_clip)

        # 7. スクロールバー計算
        total_content_height = y_curr + scroll_y - content_top
        max_config_scroll = max(0, total_content_height - content_h)

        if max_config_scroll > 0:
            sb_x = dlg_x + dlg_w - 18
            sb_y = content_top
            sb_w = 6
            sb_h = content_h
            pygame.draw.rect(self.screen, (220, 225, 235), (sb_x, sb_y, sb_w, sb_h), border_radius=3)

            handle_h = max(25, int(content_h * (content_h / float(total_content_height))))
            handle_y = sb_y + int((scroll_y / float(max_config_scroll)) * (sb_h - handle_h))
            pygame.draw.rect(self.screen, (100, 140, 200), (sb_x, handle_y, sb_w, handle_h), border_radius=3)

        # 8. フッターメッセージ
        footer_y = dlg_y + dlg_h - 45
        footer_h = 40
        pygame.draw.rect(self.screen, (245, 248, 252), (dlg_x + 3, footer_y, dlg_w - 6, footer_h), border_bottom_left_radius=8, border_bottom_right_radius=8)
        pygame.draw.line(self.screen, (200, 212, 230), (dlg_x + 20, footer_y), (dlg_x + dlg_w - 20, footer_y), 2)

        close_txt = self.font_medium.render("'C' / 'Esc' キー（またはマウスホイールでスクロール） | 閉じる", True, (80, 105, 140))
        c_rect = close_txt.get_rect(center=(dlg_x + dlg_w // 2, footer_y + 20))
        self.screen.blit(close_txt, c_rect)

        return max_config_scroll

    def draw_help_overlay(
        self,
        current_threshold: float,
        window_width: int,
        window_height: int
    ) -> None:
        """詳細操作ガイド ＆ ヘルプオーバーレイパネルの描画"""
        overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        overlay.fill((10, 20, 30, 210))
        self.screen.blit(overlay, (0, 0))

        dlg_x, dlg_y = 30, 25
        dlg_w, dlg_h = 860, 635
        pygame.draw.rect(self.screen, (252, 254, 255), (dlg_x, dlg_y, dlg_w, dlg_h), border_radius=10)
        pygame.draw.rect(self.screen, (50, 90, 150), (dlg_x, dlg_y, dlg_w, dlg_h), 3, border_radius=10)

        # ヘッダー
        h_title = self.font_title.render("画面の見方・操作ガイド", True, COLOR_TEXT_TITLE)
        self.screen.blit(h_title, (dlg_x + 25, dlg_y + 18))
        pygame.draw.line(self.screen, COLOR_BORDER_DEFAULT, (dlg_x + 20, dlg_y + 52), (dlg_x + dlg_w - 20, dlg_y + 52), 2)

        col1_x = dlg_x + 25
        col2_x = dlg_x + 440
        y_curr = dlg_y + 65

        # Section 1: 画面エレメントの見方
        sec1_title = self.font_medium.render("【画面エレメントの見方】", True, COLOR_TEXT_TITLE)
        self.screen.blit(sec1_title, (col1_x, y_curr))

        items_sec1 = [
            ("icon_gold", "選択中の知識 (金色二重枠/マーカー)", "実行中知識（グラフ上でも金色サークル＆バッジで強調）"),
            ("icon_green", "転移候補知識 (緑色二重枠)", f"活性化基準(閾値 {current_threshold:.2f})を超えた転移候補知識"),
            ("icon_color", "ノードの色 (活性度 A)", "赤: 活性値の高い知識 A>=0.5 / 青: 非活性 A=0"),
            ("icon_weight", "強い知識間重みの線", "太く濃い青色の線ほど結合が強固（数値バッジ付き）"),
            ("icon_barchart", "活性値バーグラフ (右側)", "各知識の活性値 A のリアルタイムバーチャート"),
            ("icon_linechart", "活性値変動推移グラフ (Gキー)", "全知識の活性値の時系列変化（選択中の知識を金色強調）"),
            ("icon_threshold", f"活性化閾値線 ({current_threshold:.2f})", f"活性化閾値 ({current_threshold:.2f}) の赤色線"),
            ("icon_live", "リアルタイム追従モード", "シミュレーションの最新ステップにリアルタイム自動追従"),
        ]

        y_p = y_curr + 28
        for icon_type, title_str, desc_str in items_sec1:
            icon_cx = col1_x + 16
            icon_cy = y_p + 10

            if icon_type == "icon_gold":
                pygame.draw.circle(self.screen, COLOR_ACCENT_GOLD, (icon_cx, icon_cy), 8)
                pygame.draw.circle(self.screen, (50, 80, 200), (icon_cx, icon_cy), 5)
            elif icon_type == "icon_green":
                pygame.draw.circle(self.screen, COLOR_ACCENT_GREEN, (icon_cx, icon_cy), 7)
                pygame.draw.circle(self.screen, (50, 80, 200), (icon_cx, icon_cy), 4)
            elif icon_type == "icon_color":
                pygame.draw.circle(self.screen, (220, 40, 40), (icon_cx - 5, icon_cy), 5)
                pygame.draw.circle(self.screen, (40, 80, 200), (icon_cx + 5, icon_cy), 5)
            elif icon_type == "icon_weight":
                pygame.draw.line(self.screen, COLOR_WEIGHT_ENHANCED, (icon_cx - 8, icon_cy), (icon_cx + 8, icon_cy), 4)
            elif icon_type == "icon_barchart":
                pygame.draw.rect(self.screen, (70, 130, 220), (icon_cx - 8, icon_cy - 4, 4, 10))
                pygame.draw.rect(self.screen, (70, 130, 220), (icon_cx - 2, icon_cy - 8, 4, 14))
                pygame.draw.rect(self.screen, (70, 130, 220), (icon_cx + 4, icon_cy - 2, 4, 8))
            elif icon_type == "icon_linechart":
                pygame.draw.line(self.screen, (220, 120, 30), (icon_cx - 8, icon_cy + 4), (icon_cx - 2, icon_cy - 6), 2)
                pygame.draw.line(self.screen, (220, 120, 30), (icon_cx - 2, icon_cy - 6), (icon_cx + 4, icon_cy + 2), 2)
                pygame.draw.line(self.screen, (220, 120, 30), (icon_cx + 4, icon_cy + 2), (icon_cx + 8, icon_cy - 6), 2)
            elif icon_type == "icon_threshold":
                pygame.draw.line(self.screen, COLOR_ACCENT_RED, (icon_cx - 8, icon_cy), (icon_cx + 8, icon_cy), 2)
            elif icon_type == "icon_live":
                pygame.draw.circle(self.screen, (40, 160, 60), (icon_cx, icon_cy), 6)

            t_title = self.font_medium.render(title_str, True, COLOR_TEXT_BODY)
            t_desc = self.font_small.render(desc_str, True, COLOR_TEXT_MUTED)
            self.screen.blit(t_title, (col1_x + 34, y_p))
            self.screen.blit(t_desc, (col1_x + 34, y_p + 20))
            y_p += 54

        # Section 2: 操作方法・ショートカットキー
        sec2_title = self.font_medium.render("【キーボード ＆ ボタン操作】", True, COLOR_TEXT_TITLE)
        self.screen.blit(sec2_title, (col2_x, y_curr))

        items_sec2 = [
            ("G キー", "画面表示モード切替（ステップ表示 ⇄ 折れ線グラフ）"),
            ("Space キー", "再生 / 一時停止"),
            ("← / → 矢印キー", "1ステップ コマ戻し / コマ送り"),
            ("E / Shift+E キー", "次 / 直前 のエピソードへジャンプ"),
            ("P / Shift+P キー", "次 / 直前 の知識選択へジャンプ"),
            ("A / Shift+A キー", "次 / 直前 の活性化へジャンプ"),
            ("W / Shift+W キー", "次 / 直前 の重み更新へジャンプ"),
            ("L キー", "リアルタイム追従モードのON/OFF切替"),
            ("C キー", "ハイパーパラメータ設定一覧の表示 / 非表示"),
            ("O キー", "実験ログフォルダ選択ダイアログを開く"),
            ("H / ? / Esc キー", "ヘルプ画面の表示 / 非表示"),
        ]

        y_p2 = y_curr + 28
        for key_str, desc_str in items_sec2:
            t_k = self.font_medium.render(key_str, True, (20, 80, 160))
            t_d = self.font_small.render(desc_str, True, (60, 70, 90))
            self.screen.blit(t_k, (col2_x + 10, y_p2))
            self.screen.blit(t_d, (col2_x + 10, y_p2 + 18))
            y_p2 += 44

        # フッター閉じる案内
        close_txt = self.font_medium.render("'H' キーまたは 'Esc' キー（または 'ヘルプ' ボタン）で閉じる", True, (100, 120, 150))
        c_rect = close_txt.get_rect(center=(dlg_x + dlg_w // 2, dlg_y + dlg_h - 22))
        self.screen.blit(close_txt, c_rect)
