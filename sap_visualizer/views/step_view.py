"""
SAP-net Visualizer ステップ表示画面（ネットワーク図 ＋ 棒グラフ）描画ビュー
"""
import pygame
import numpy as np
from typing import Dict
from .base_view import BaseView
from ..models import ResolvedFrameInfo
from ..utils.geometry_utils import calculate_circular_node_positions, calculate_edge_badge_position
from ..theme import (
    COLOR_BG_CARD,
    COLOR_BORDER_STRONG,
    COLOR_BORDER_DEFAULT,
    COLOR_TEXT_TITLE,
    COLOR_TEXT_BODY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_WHITE,
    COLOR_ACCENT_GOLD,
    COLOR_ACCENT_GREEN,
    COLOR_ACCENT_RED,
    COLOR_WEIGHT_DEFAULT,
    COLOR_WEIGHT_ENHANCED,
)


class StepView(BaseView):
    """ステップ表示画面（ネットワーク図 ＋ 活性値棒グラフ ＋ 凡例バー）の描画を担当するビュークラス"""
    def __init__(self, screen: pygame.Surface, fonts: Dict[str, pygame.font.Font]):
        super().__init__(screen, fonts)

    def draw(
        self,
        resolved_info: ResolvedFrameInfo,
        current_index: int,
        total_frames: int
    ) -> None:
        """ステップ表示画面の全コンポーネントを描画"""
        plan = resolved_info.plan
        selectplans = resolved_info.selectplans
        A_raw = resolved_info.activations
        weight_raw = resolved_info.weight_matrix
        ep = resolved_info.episode
        st = resolved_info.step
        ev = resolved_info.event_type

        # 1. サブヘッダー情報の描画
        plan_disp = f"知識 {plan}" if plan is not None else "なし"
        info_str = (
            f"フレーム: {current_index}/{max(0, total_frames - 1)} | "
            f"エピソード: {ep} | ステップ: {st} | イベント: {ev} | 選択知識: {plan_disp}"
        )
        self.draw_subheader_info(info_str, y_pos=46, max_width=660)

        # 2. ネットワーク構造の描画 (左側 400x450 領域)
        self._draw_network_graph(plan, selectplans, A_raw, weight_raw)

        # 3. 活性値 A のリアルタイムバーチャート (右側 360x420 領域)
        self._draw_activation_barchart(plan, A_raw, resolved_info.threshold)

        # 4. コンパクト凡例バー (下部)
        self._draw_legend_bar()

    def _draw_network_graph(
        self,
        plan: int,
        selectplans: list,
        A_raw: list,
        weight_raw: list
    ) -> None:
        """ネットワーク構造（円環ノード ＋ 重みエッジ ＋ 数値バッジ）の描画"""
        net_center_x, net_center_y = 230, 290
        net_radius = 150

        num_nodes = len(A_raw) if len(A_raw) > 0 else (len(weight_raw) if len(weight_raw) > 0 else 0)
        A = np.array(A_raw, dtype=float) if len(A_raw) > 0 else np.zeros(num_nodes, dtype=float)
        weight = np.array(weight_raw, dtype=float) if len(weight_raw) > 0 else np.zeros((num_nodes, num_nodes), dtype=float)

        if num_nodes == 0 and len(weight) > 0:
            num_nodes = len(weight)

        # ノード位置の算出
        node_positions = calculate_circular_node_positions(num_nodes, net_center_x, net_center_y, net_radius)

        # エッジ（重み weight）の描画 ＆ 数値バッジ用データの収集
        edge_draw_list = []
        if len(weight) == num_nodes and num_nodes > 0:
            non_zero_w = weight[weight > 0]
            min_w = float(np.min(non_zero_w)) if len(non_zero_w) > 0 else 0.0
            max_w = float(np.max(non_zero_w)) if len(non_zero_w) > 0 else 0.0

            for i in range(num_nodes):
                for j in range(i + 1, num_nodes):
                    w_val = float(weight[i][j])
                    if w_val > 0:
                        if max_w > min_w:
                            ratio = (w_val - min_w) / (max_w - min_w)
                            thickness = 2 + int(ratio * 4)  # 2px 〜 6px
                            r_c = int(160 - ratio * 125)
                            g_c = int(175 - ratio * 80)
                            b_c = int(195 + ratio * 20)
                            color = (max(0, min(255, r_c)), max(0, min(255, g_c)), max(0, min(255, b_c)))
                            is_enhanced = (ratio > 0.05)
                        else:
                            thickness = 2
                            color = COLOR_WEIGHT_DEFAULT
                            is_enhanced = False

                        pygame.draw.line(self.screen, color, node_positions[i], node_positions[j], thickness)
                        edge_draw_list.append((i, j, w_val, is_enhanced))

        # エッジ中央への重み数値ラベル（バッジ）の描画
        for (i, j, w_val, is_enhanced) in edge_draw_list:
            p1 = node_positions[i]
            p2 = node_positions[j]
            badge_x, badge_y = calculate_edge_badge_position(p1, p2, net_center_x, net_center_y, center_avoidance_dist=30.0)

            val_str = f"{w_val:.2f}".rstrip('0').rstrip('.') if '.' in f"{w_val:.2f}" else f"{w_val:.1f}"
            if "." not in val_str:
                val_str = f"{w_val:.1f}"

            t_surf = self.font_tiny.render(val_str, True, (15, 55, 140) if is_enhanced else (70, 80, 95))
            tw, th = t_surf.get_width(), t_surf.get_height()

            pad_x, pad_y = 4, 2
            badge_rect = pygame.Rect(badge_x - tw // 2 - pad_x, badge_y - th // 2 - pad_y, tw + pad_x * 2, th + pad_y * 2)

            bg_color = (235, 245, 255) if is_enhanced else COLOR_BG_CARD
            border_color = COLOR_WEIGHT_ENHANCED if is_enhanced else (180, 190, 205)
            border_w = 2 if is_enhanced else 1

            pygame.draw.rect(self.screen, bg_color, badge_rect, border_radius=3)
            pygame.draw.rect(self.screen, border_color, badge_rect, border_w, border_radius=3)
            self.screen.blit(t_surf, (badge_x - tw // 2, badge_y - th // 2))

        # ノード（円・リング・番号）の描画
        for i, (nx, ny) in enumerate(node_positions):
            act_val = A[i] if i < len(A) else 0.0
            norm_act = min(1.0, max(0.0, act_val / 0.5))
            r_c = int(255 * norm_act)
            b_c = int(255 * (1.0 - norm_act))
            node_color = (r_c, 80, b_c)

            is_selected = (plan == i)
            is_candidate = (i < len(selectplans) and selectplans[i] == 1)

            if is_selected:
                pygame.draw.circle(self.screen, COLOR_ACCENT_GOLD, (nx, ny), 26)
            elif is_candidate:
                pygame.draw.circle(self.screen, COLOR_ACCENT_GREEN, (nx, ny), 24)

            pygame.draw.circle(self.screen, node_color, (nx, ny), 20)

            n_txt = self.font_medium.render(str(i), True, COLOR_TEXT_WHITE)
            n_rect = n_txt.get_rect(center=(nx, ny))
            self.screen.blit(n_txt, n_rect)

    def _draw_activation_barchart(
        self,
        plan: int,
        A_raw: list,
        threshold: float
    ) -> None:
        """知識活性値 A のリアルタイムバーチャート描画"""
        bar_start_x = 480
        bar_start_y = 90
        bar_width = 360
        bar_height = 420

        pygame.draw.rect(self.screen, COLOR_BG_CARD, (bar_start_x, bar_start_y, bar_width, bar_height))
        pygame.draw.rect(self.screen, COLOR_BORDER_DEFAULT, (bar_start_x, bar_start_y, bar_width, bar_height), 2)

        b_title = self.font_medium.render("知識活性値 (A)", True, COLOR_TEXT_BODY)
        self.screen.blit(b_title, (bar_start_x + 10, bar_start_y + 10))

        # 活性化閾値線
        thresh_val = threshold
        thresh_y = bar_start_y + bar_height - 30 - int((thresh_val / 0.6) * (bar_height - 60))
        pygame.draw.line(self.screen, COLOR_ACCENT_RED, (bar_start_x + 30, thresh_y), (bar_start_x + bar_width - 10, thresh_y), 2)
        t_txt = self.font_small.render(f"活性化閾値 ({thresh_val:.2f})", True, (200, 40, 40))
        self.screen.blit(t_txt, (bar_start_x + bar_width - 130, thresh_y - 18))

        # 各ノードの棒グラフ
        num_nodes = len(A_raw)
        if num_nodes > 0:
            bw = (bar_width - 50) // num_nodes
            for i in range(num_nodes):
                act_val = A_raw[i] if i < len(A_raw) else 0.0
                bh = int((min(0.6, act_val) / 0.6) * (bar_height - 60))
                bx = bar_start_x + 40 + i * bw
                by = bar_start_y + bar_height - 30 - bh

                b_color = (70, 130, 180) if i != plan else (230, 160, 30)
                pygame.draw.rect(self.screen, b_color, (bx, by, bw - 6, bh))

                lbl = self.font_small.render(str(i), True, (50, 50, 50))
                self.screen.blit(lbl, (bx + (bw - 6) // 4, bar_start_y + bar_height - 25))

    def _draw_legend_bar(self) -> None:
        """ネットワークグラフ下部にコンパクト凡例 (Legend Bar) を背景枠に対して均等に描画"""
        lg_x, lg_y = 20, 515
        lg_w, lg_h = 470, 30
        pygame.draw.rect(self.screen, COLOR_BG_CARD, (lg_x, lg_y, lg_w, lg_h), border_radius=4)
        pygame.draw.rect(self.screen, COLOR_BORDER_DEFAULT, (lg_x, lg_y, lg_w, lg_h), 1, border_radius=4)

        legend_items = [
            ("gold_ring", "選択中の知識"),
            ("green_ring", "転移候補知識"),
            ("red_dot", "活性値の高い知識"),
            ("weight_line", "強い知識間重み"),
        ]

        item_widths = []
        rendered_texts = []
        for item_type, text_str in legend_items:
            txt_surf = self.font_small.render(text_str, True, (40, 50, 60))
            rendered_texts.append(txt_surf)
            w_txt = txt_surf.get_width()

            if item_type in ("gold_ring", "green_ring"):
                icon_w = 16 + 5
            elif item_type == "red_dot":
                icon_w = 12 + 5
            elif item_type == "weight_line":
                icon_w = 16 + 5
            else:
                icon_w = 0

            item_widths.append(icon_w + w_txt)

        total_items_w = sum(item_widths)
        num_items = len(legend_items)
        margin = 15
        avail_space = lg_w - 2 * margin
        gap = (avail_space - total_items_w) / max(1, num_items - 1) if num_items > 1 else 0

        curr_x = lg_x + margin
        cy = lg_y + 15

        for i, (item_type, _) in enumerate(legend_items):
            txt_surf = rendered_texts[i]

            if item_type == "gold_ring":
                pygame.draw.circle(self.screen, COLOR_ACCENT_GOLD, (int(curr_x + 8), cy), 8)
                pygame.draw.circle(self.screen, (220, 50, 50), (int(curr_x + 8), cy), 5)
                self.screen.blit(txt_surf, (int(curr_x + 21), lg_y + 7))
            elif item_type == "green_ring":
                pygame.draw.circle(self.screen, COLOR_ACCENT_GREEN, (int(curr_x + 8), cy), 8)
                pygame.draw.circle(self.screen, (50, 80, 200), (int(curr_x + 8), cy), 5)
                self.screen.blit(txt_surf, (int(curr_x + 21), lg_y + 7))
            elif item_type == "red_dot":
                pygame.draw.circle(self.screen, (220, 40, 40), (int(curr_x + 6), cy), 6)
                self.screen.blit(txt_surf, (int(curr_x + 17), lg_y + 7))
            elif item_type == "weight_line":
                pygame.draw.line(self.screen, COLOR_WEIGHT_ENHANCED, (int(curr_x), cy), (int(curr_x + 16), cy), 4)
                self.screen.blit(txt_surf, (int(curr_x + 21), lg_y + 7))

            curr_x += item_widths[i] + gap
