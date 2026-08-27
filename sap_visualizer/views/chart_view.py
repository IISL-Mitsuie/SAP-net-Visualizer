"""
SAP-net Visualizer 活性値推移折れ線グラフ画面 ＆ 高精細画像保存ビュー
"""
import os
import re
import datetime
import logging
import pygame
from typing import Dict, List, Optional, Tuple
from .base_view import BaseView
from ..models import LogFrame, ResolvedFrameInfo
from ..utils.geometry_utils import calculate_downsampled_indices, calculate_legend_layout
from ..theme import (
    NODE_COLORS,
    COLOR_BG_CARD,
    COLOR_BG_PANEL,
    COLOR_BORDER_DEFAULT,
    COLOR_BORDER_STRONG,
    COLOR_BORDER_FOCUS,
    COLOR_TEXT_TITLE,
    COLOR_TEXT_BODY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_WHITE,
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_BLUE_LIGHT,
    COLOR_ACCENT_GOLD,
    COLOR_ACCENT_RED,
)

logger = logging.getLogger(__name__)


class ChartView(BaseView):
    """活性値変動推移の重ね合わせ折れ線グラフ画面および高精細画像エクスポートを担当するビュークラス"""
    def __init__(self, screen: pygame.Surface, fonts: Dict[str, pygame.font.Font]):
        super().__init__(screen, fonts)

        # グラフ描画領域
        self.chart_rect = pygame.Rect(50, 80, 680, 435)

        # 右側フィルターパネル内ボタン領域
        self.btn_all_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_none_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_save_chart_rect = pygame.Rect(0, 0, 0, 0)
        self.node_toggle_rects: List[Tuple[int, pygame.Rect]] = []

        # 知識ごとの表示/非表示フラグ辞書 {node_index: bool}
        self.visible_nodes: Dict[int, bool] = {}

    def toggle_all_nodes(self, max_nodes: int, visible: bool = True) -> None:
        """全知識ノードの一括表示/非表示切り替え"""
        for i in range(max_nodes):
            self.visible_nodes[i] = visible

    def toggle_node(self, node_index: int) -> None:
        """指定した知識番号の表示/非表示を反転"""
        self.visible_nodes[node_index] = not self.visible_nodes.get(node_index, True)

    def draw(
        self,
        history: List[LogFrame],
        current_index: int,
        resolved_info: ResolvedFrameInfo,
        max_nodes: int
    ) -> None:
        """折れ線グラフ画面のレンダリング"""
        total_frames = len(history)
        c_plan = resolved_info.plan
        c_A = resolved_info.activations
        c_ep = resolved_info.episode
        c_st = resolved_info.step

        # 1. サブヘッダー情報の描画
        if total_frames > 0 and 0 <= current_index < total_frames:
            plan_str = f"知識 {c_plan}" if c_plan is not None else "なし"
            info_str = (
                f"活性値変動推移ビュー | 現在選択: フレーム {current_index}/{total_frames - 1} | "
                f"エピソード: {c_ep} | ステップ: {c_st} | 選択知識: {plan_str}"
            )
        else:
            info_str = "活性値変動推移ビュー | ログ未読み込み"
        self.draw_subheader_info(info_str)


        chart_x, chart_y = self.chart_rect.x, self.chart_rect.y
        chart_w, chart_h = self.chart_rect.width, self.chart_rect.height

        panel_x, panel_y = 745, 80
        panel_w, panel_h = 155, 435

        # グラフ領域背景 ＆ 枠
        pygame.draw.rect(self.screen, COLOR_BG_CARD, (chart_x, chart_y, chart_w, chart_h))
        pygame.draw.rect(self.screen, COLOR_BORDER_DEFAULT, (chart_x, chart_y, chart_w, chart_h), 2)

        # 凡例トグル操作パネル背景 ＆ 枠
        pygame.draw.rect(self.screen, COLOR_BG_PANEL, (panel_x, panel_y, panel_w, panel_h), border_radius=6)
        pygame.draw.rect(self.screen, (200, 210, 225), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=6)

        p_title = self.font_medium.render("知識表示フィルター", True, COLOR_TEXT_BODY)
        self.screen.blit(p_title, (panel_x + 12, panel_y + 8))

        # 全選択・全解除ボタン
        self.btn_all_rect = pygame.Rect(panel_x + 10, panel_y + 32, 63, 24)
        self.btn_none_rect = pygame.Rect(panel_x + 80, panel_y + 32, 63, 24)

        pygame.draw.rect(self.screen, (225, 235, 245), self.btn_all_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_BORDER_STRONG, self.btn_all_rect, 1, border_radius=4)
        t_all = self.font_small.render("全選択", True, COLOR_TEXT_BODY)
        self.screen.blit(t_all, t_all.get_rect(center=self.btn_all_rect.center))

        pygame.draw.rect(self.screen, (225, 235, 245), self.btn_none_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_BORDER_STRONG, self.btn_none_rect, 1, border_radius=4)
        t_none = self.font_small.render("全解除", True, COLOR_TEXT_BODY)
        self.screen.blit(t_none, t_none.get_rect(center=self.btn_none_rect.center))

        # グラフ保存ボタン
        self.btn_save_chart_rect = pygame.Rect(panel_x + 10, panel_y + panel_h - 34, panel_w - 20, 26)
        pygame.draw.rect(self.screen, COLOR_ACCENT_BLUE_LIGHT, self.btn_save_chart_rect, border_radius=4)
        pygame.draw.rect(self.screen, (50, 110, 190), self.btn_save_chart_rect, 1, border_radius=4)
        t_save = self.font_small.render("グラフ保存 (S)", True, (15, 45, 90))
        self.screen.blit(t_save, t_save.get_rect(center=self.btn_save_chart_rect.center))

        # 知識表示/非表示トグルボタンの描画・生成
        self.node_toggle_rects = []
        for i in range(max_nodes):
            if i not in self.visible_nodes:
                self.visible_nodes[i] = True

            by = panel_y + 64 + i * 26
            if by + 24 > panel_y + panel_h - 40:
                break

            btn_rect = pygame.Rect(panel_x + 8, by, panel_w - 16, 23)
            self.node_toggle_rects.append((i, btn_rect))

            is_vis = self.visible_nodes[i]
            is_plan = (c_plan == i)
            c_color = NODE_COLORS[i % len(NODE_COLORS)]

            if is_plan:
                bg_col = (255, 246, 220) if is_vis else (245, 238, 220)
                border_col = (230, 160, 20)
                border_w = 2
            else:
                bg_col = (235, 243, 255) if is_vis else (240, 240, 240)
                border_col = c_color if is_vis else (180, 180, 180)
                border_w = 2 if is_vis else 1

            pygame.draw.rect(self.screen, bg_col, btn_rect, border_radius=4)
            pygame.draw.rect(self.screen, border_col, btn_rect, border_w, border_radius=4)

            # 色丸マーク
            pygame.draw.circle(self.screen, c_color, (btn_rect.x + 14, btn_rect.centery), 6)
            if not is_vis:
                pygame.draw.line(self.screen, (150, 150, 150), (btn_rect.x + 8, btn_rect.centery - 6), (btn_rect.x + 20, btn_rect.centery + 6), 2)

            chk_str = f"知識 {i}" + (" [✓]" if is_vis else " [  ]")
            if is_plan:
                chk_str += " ★選択"
            txt_color = (190, 110, 0) if (is_plan and is_vis) else (COLOR_TEXT_BODY if is_vis else (130, 130, 130))
            n_txt = self.font_small.render(chk_str, True, txt_color)
            self.screen.blit(n_txt, (btn_rect.x + 26, btn_rect.centery - n_txt.get_height() // 2))

        if total_frames <= 1:
            msg = self.font_medium.render("ログデータが読み込まれていません（'O' キーで実験ログフォルダを選択してください）", True, (120, 130, 140))
            self.screen.blit(msg, msg.get_rect(center=(chart_x + chart_w // 2, chart_y + chart_h // 2)))
            return

        # Y軸グリッド ＆ 目盛り（0.0 〜 1.0）
        for y_val in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            cy = chart_y + chart_h - int(y_val * chart_h)
            pygame.draw.line(self.screen, (230, 235, 240), (chart_x, cy), (chart_x + chart_w, cy), 1)
            lbl = self.font_small.render(f"{y_val:.1f}", True, (100, 110, 120))
            self.screen.blit(lbl, (chart_x - 30, cy - 7))

        # X軸グリッド ＆ 目盛り
        num_x_ticks = min(10, total_frames)
        for t in range(num_x_ticks):
            idx = int(t * (total_frames - 1) / max(1, num_x_ticks - 1))
            cx = chart_x + int((idx / float(total_frames - 1)) * chart_w)
            pygame.draw.line(self.screen, (230, 235, 240), (cx, chart_y), (cx, chart_y + chart_h), 1)
            lbl = self.font_small.render(str(idx), True, (100, 110, 120))
            self.screen.blit(lbl, (cx - lbl.get_width() // 2, chart_y + chart_h + 5))

        # 活性化閾値線
        thresh_val = resolved_info.threshold
        thresh_y = chart_y + chart_h - int(thresh_val * chart_h)
        dash_len = 8
        for dash_x in range(chart_x, chart_x + chart_w, dash_len * 2):
            pygame.draw.line(self.screen, COLOR_ACCENT_RED, (dash_x, thresh_y), (min(chart_x + chart_w, dash_x + dash_len), thresh_y), 2)
        t_lbl = self.font_small.render(f"活性化閾値 ({thresh_val:.2f})", True, (200, 40, 40))
        self.screen.blit(t_lbl, (chart_x + chart_w - 120, thresh_y - 18))

        # 時系列折れ線描画 (間引きインデックス適用)
        indices = calculate_downsampled_indices(total_frames, chart_w)

        for i in range(max_nodes):
            if not self.visible_nodes.get(i, True):
                continue

            c_color = NODE_COLORS[i % len(NODE_COLORS)]
            points = []
            for idx in indices:
                px = chart_x + int((idx / float(total_frames - 1)) * chart_w)
                frame_data = history[idx]
                act_list = frame_data.activations
                act_val = act_list[i] if i < len(act_list) else 0.0
                act_val = min(1.0, max(0.0, float(act_val)))
                py = chart_y + chart_h - int(act_val * chart_h)
                points.append((px, py))

            if len(points) >= 2:
                pygame.draw.lines(self.screen, c_color, False, points, 2)

        # 現在選択中フレームの垂直カーソル線 ＆ 選択知識強調マーカー
        if 0 <= current_index < total_frames:
            cur_x = chart_x + int((current_index / float(total_frames - 1)) * chart_w)
            pygame.draw.line(self.screen, (30, 90, 220), (cur_x, chart_y), (cur_x, chart_y + chart_h), 2)

            if c_plan is not None and self.visible_nodes.get(c_plan, True):
                p_act = c_A[c_plan] if c_plan < len(c_A) else 0.0
                p_act = min(1.0, max(0.0, float(p_act)))
                py = chart_y + chart_h - int(p_act * chart_h)
                p_color = NODE_COLORS[c_plan % len(NODE_COLORS)]

                pygame.draw.circle(self.screen, (240, 190, 30), (cur_x, py), 9, 3)
                pygame.draw.circle(self.screen, (255, 255, 255), (cur_x, py), 6)
                pygame.draw.circle(self.screen, p_color, (cur_x, py), 4)

                act_badge_txt = f"知識{c_plan}: {p_act:.2f}"
                act_surf = self.font_tiny.render(act_badge_txt, True, (30, 40, 60))
                bw = act_surf.get_width() + 8
                bh = 16
                bx = cur_x + 10
                if bx + bw > chart_x + chart_w - 4:
                    bx = cur_x - bw - 10
                by = max(chart_y + 4, min(py - 8, chart_y + chart_h - bh - 4))

                b_rect = pygame.Rect(bx, by, bw, bh)
                pygame.draw.rect(self.screen, (255, 248, 220), b_rect, border_radius=3)
                pygame.draw.rect(self.screen, (220, 160, 20), b_rect, 1, border_radius=3)
                self.screen.blit(act_surf, (bx + 4, by + 1))

            # 上部情報バッジ
            plan_label = f"選択知識: 知識 {c_plan}" if c_plan is not None else "選択知識: なし"
            cur_txt = f"フレーム {current_index} (Ep:{c_ep}, Step:{c_st}) | {plan_label}"
            c_surf = self.font_small.render(cur_txt, True, (255, 255, 255))
            c_w = c_surf.get_width() + 16
            c_left = min(max(cur_x - c_w // 2, chart_x + 4), chart_x + chart_w - c_w - 4)
            c_bg = pygame.Rect(c_left, chart_y + 8, c_w, 22)

            bg_col = (20, 50, 110) if c_plan is not None else (40, 60, 90)
            border_col = (240, 200, 40) if c_plan is not None else (100, 140, 200)
            pygame.draw.rect(self.screen, bg_col, c_bg, border_radius=4)
            pygame.draw.rect(self.screen, border_col, c_bg, 2 if c_plan is not None else 1, border_radius=4)
            self.screen.blit(c_surf, (c_bg.x + 8, c_bg.y + 4))

    def export_chart_surface(
        self,
        history: List[LogFrame],
        max_nodes: int
    ) -> Optional[pygame.Surface]:
        """独立した高精細グラフ画像サーフェス（グラフ＋下部凡例）を生成して返す"""
        total_frames = len(history)
        if total_frames <= 1:
            return None

        export_w = 900
        gx, gy, gw, gh = 70, 25, 800, 420

        vis_node_indices = [i for i in range(max_nodes) if self.visible_nodes.get(i, True)]
        get_w_func = lambda s: self.font_small.size(s)[0]
        legend_items, cur_bottom_y = calculate_legend_layout(
            vis_node_indices, get_w_func, gx, gy, gw, gh
        )

        export_h = max(520, cur_bottom_y + 12)
        surf = pygame.Surface((export_w, export_h))
        surf.fill((255, 255, 255))

        # 枠線
        pygame.draw.rect(surf, (255, 255, 255), (gx, gy, gw, gh))
        pygame.draw.rect(surf, (150, 160, 175), (gx, gy, gw, gh), 2)

        # Y軸グリッド & 目盛り
        for y_val in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            cy = gy + gh - int(y_val * gh)
            pygame.draw.line(surf, (230, 235, 240), (gx, cy), (gx + gw, cy), 1)
            lbl = self.font_small.render(f"{y_val:.1f}", True, (80, 90, 100))
            surf.blit(lbl, (gx - 35, cy - 7))

        y_axis_lbl = self.font_small.render("活性度 A", True, (60, 70, 80))
        y_axis_lbl_rot = pygame.transform.rotate(y_axis_lbl, 90)
        surf.blit(y_axis_lbl_rot, (gx - 48, gy + (gh - y_axis_lbl_rot.get_height()) // 2))

        # X軸グリッド & 目盛り
        num_x_ticks = min(10, total_frames)
        for t in range(num_x_ticks):
            idx = int(t * (total_frames - 1) / max(1, num_x_ticks - 1))
            cx = gx + int((idx / max(1, total_frames - 1)) * gw)
            pygame.draw.line(surf, (235, 238, 242), (cx, gy), (cx, gy + gh), 1)
            lbl = self.font_small.render(str(idx), True, (80, 90, 100))
            surf.blit(lbl, (cx - lbl.get_width() // 2, gy + gh + 6))

        x_axis_lbl = self.font_small.render("フレーム数 (Step)", True, (60, 70, 80))
        surf.blit(x_axis_lbl, (gx + (gw - x_axis_lbl.get_width()) // 2, gy + gh + 28))

        # 折れ線描画
        indices = calculate_downsampled_indices(total_frames, gw)
        for i in vis_node_indices:
            points = []
            c_color = NODE_COLORS[i % len(NODE_COLORS)]
            for frame_idx in indices:
                f = history[frame_idx]
                act_list = f.activations
                if i < len(act_list):
                    val = max(0.0, min(1.0, float(act_list[i])))
                    px = gx + int((frame_idx / max(1, total_frames - 1)) * gw)
                    py = gy + gh - int(val * gh)
                    points.append((px, py))

            if len(points) >= 2:
                pygame.draw.lines(surf, c_color, False, points, 2)

        # 凡例プロット
        for i, ix, iy, label_str in legend_items:
            c_color = NODE_COLORS[i % len(NODE_COLORS)]
            pygame.draw.circle(surf, c_color, (ix + 6, iy + 10), 5)
            k_txt = self.font_small.render(label_str, True, (30, 40, 55))
            surf.blit(k_txt, (ix + 16, iy + 2))

        return surf
