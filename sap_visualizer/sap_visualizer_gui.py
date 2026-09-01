"""
SAP-net Visualizer メインGUIコントローラーモジュール
"""
import os
import sys
import datetime
import logging
import pygame
from typing import Optional, List, Tuple

from .constants import (
    EventType,
    ViewMode,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_FPS,
    SLIDER_X,
    SLIDER_WIDTH,
    SLIDER_MARGIN_X,
    SLIDER_Y,
    SLIDER_HEIGHT,
)
from .theme import (
    COLOR_BG_MAIN,
    COLOR_BG_CARD,
    COLOR_BORDER_DEFAULT,
    COLOR_BORDER_STRONG,
    COLOR_TEXT_TITLE,
    COLOR_TEXT_BODY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_WHITE,
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_BLUE_LIGHT,
    COLOR_LIVE_BG,
    COLOR_LIVE_BORDER,
    COLOR_LIVE_TEXT,
    COLOR_MANUAL_BG,
    COLOR_MANUAL_BORDER,
    COLOR_MANUAL_TEXT,
    COLOR_SLIDER_TRACK,
    COLOR_SLIDER_HANDLE,
)
from .models import ResolvedFrameInfo
from .sap_visual_logger import SAPVisualLogger
from .folder_selector_gui import FolderSelectorDialog
from .views.base_view import BaseView
from .views.step_view import StepView
from .views.chart_view import ChartView
from .views.overlays import OverlaysView

logger = logging.getLogger(__name__)


class SAPVisualizerGUI:
    """
    SAP-net Visualizer メインGUIコントローラークラス。
    ユーザー入力・再生制御・ビューの統括を担当。
    """
    def __init__(
        self,
        logger: SAPVisualLogger,
        window_width: int = DEFAULT_WINDOW_WIDTH,
        window_height: int = DEFAULT_WINDOW_HEIGHT
    ):
        self.logger = logger
        self.width = window_width
        self.height = window_height

        # 状態変数
        self.current_index = 0
        self.is_playing = False
        self.live_follow = True
        self.is_active = True
        self.show_help = False
        self.show_config = False
        self.config_scroll_y = 0
        self.max_config_scroll = 0
        self.play_speed = 1.0
        self.view_mode = ViewMode.STEP

        # トースト通知
        self.toast_msg = ""
        self.toast_timer = 0

        # Pygame初期化
        pygame.init()
        pygame.display.set_caption("SAP-net Visualizer")
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()

        # フォント生成
        self.fonts = BaseView.create_default_fonts()
        self.font_tiny = self.fonts["tiny"]
        self.font_small = self.fonts["small"]
        self.font_medium = self.fonts["medium"]
        self.font_title = self.fonts["title"]

        # ビューコンポーネント初期化
        self.step_view = StepView(self.screen, self.fonts)
        self.chart_view = ChartView(self.screen, self.fonts)
        self.overlays_view = OverlaysView(self.screen, self.fonts)

        # UIレイアウト領域
        self.view_btn_rect = pygame.Rect(560, 10, 130, 30)
        self.header_btn_rect = pygame.Rect(700, 10, 200, 30)
        self.slider_rect = pygame.Rect(SLIDER_X, SLIDER_Y, SLIDER_WIDTH, SLIDER_HEIGHT)
        self.is_dragging_slider = False


        self._setup_buttons()

    def _setup_buttons(self) -> None:
        """ボタンレイアウト（上段8個・下段7個）の構築"""
        margin_left = 20
        margin_right = 20
        avail_w = self.width - margin_left - margin_right

        # 上段: イベントジャンプ
        row1_items = [
            ("|< エピソード", "prev_ep"),
            ("エピソード >|", "next_ep"),
            ("|< 知識選択", "prev_plan"),
            ("知識選択 >|", "next_plan"),
            ("|< 活性化", "prev_act"),
            ("活性化 >|", "next_act"),
            ("|< 重み更新", "prev_weight"),
            ("重み更新 >|", "next_weight"),
        ]
        gap1 = 8
        n1 = len(row1_items)
        w1 = (avail_w - (n1 - 1) * gap1) // n1
        y1 = 578
        h1 = 30

        # 下段: 再生 ＆ システム
        row2_items = [
            ("<< コマ戻し", "step_back", 110),
            ("再生/一時停止", "toggle_play", 115),
            ("コマ送り >>", "step_forward", 110),
            ("リアルタイム追従", "toggle_live", 125),
            ("ハイパーパラメータ", "toggle_config", 145),
            ("ヘルプ", "toggle_help", 105),
            ("リセット", "reset_index", 110),
        ]
        gap2 = 10
        y2 = 622
        h2 = 35

        self.buttons = []

        # 上段配置
        for i, (label, action) in enumerate(row1_items):
            x = margin_left + i * (w1 + gap1)
            rect = pygame.Rect(x, y1, w1, h1)
            self.buttons.append({"label": label, "action": action, "rect": rect, "type": "event"})

        # 下段配置
        total_custom_w = sum(item[2] for item in row2_items)
        auto_gap = max(6, (avail_w - total_custom_w) // (len(row2_items) - 1)) if len(row2_items) > 1 else gap2
        curr_x = margin_left

        for item in row2_items:
            label, action, b_width = item[0], item[1], item[2]
            rect = pygame.Rect(curr_x, y2, b_width, h2)
            self.buttons.append({"label": label, "action": action, "rect": rect, "type": "control"})
            curr_x += b_width + auto_gap

    def get_resolved_frame_info(self, frame_index: int) -> Tuple[Optional[int], list, list, list, int, int, str]:
        """
        指定したフレームインデックスにおける動的パラメータ情報を取得する。
        （テストや外部呼び出しとの互換タプル返却）
        """
        resolved = self.logger.resolve_frame(frame_index)
        return (
            resolved.plan,
            resolved.selectplans,
            resolved.activations,
            resolved.weight_matrix,
            resolved.episode,
            resolved.step,
            resolved.event_type
        )

    def handle_events(self) -> None:
        """Pygame入力イベントの処理"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_active = False

            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_down(event)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.is_dragging_slider = False

            elif event.type == pygame.MOUSEMOTION:
                if self.is_dragging_slider:
                    self._update_slider_position(event.pos[0])

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        """キーボード操作のハンドリング"""
        # Escキー: モーダルを閉じる
        if event.key == pygame.K_ESCAPE:
            if self.show_help or self.show_config:
                self.show_help = False
                self.show_config = False
            return

        # ヘルプ・設定表示中は矢印キーやホイールでスクロール
        if self.show_config:
            if event.key == pygame.K_UP:
                self.config_scroll_y = max(0, self.config_scroll_y - 30)
                return
            elif event.key == pygame.K_DOWN:
                self.config_scroll_y = min(self.max_config_scroll, self.config_scroll_y + 30)
                return

        # 通常操作ショートカット
        if event.key == pygame.K_g:
            self.view_mode = ViewMode.LINE_CHART if self.view_mode == ViewMode.STEP else ViewMode.STEP

        elif event.key == pygame.K_s and self.view_mode == ViewMode.LINE_CHART:
            self.save_chart_image()

        elif event.key == pygame.K_SPACE:
            self.is_playing = not self.is_playing

        elif event.key == pygame.K_LEFT:
            self.is_playing = False
            self.live_follow = False
            self.current_index = max(0, self.current_index - 1)

        elif event.key == pygame.K_RIGHT:
            self.is_playing = False
            self.live_follow = False
            total_frames = len(self.logger.history)
            self.current_index = min(max(0, total_frames - 1), self.current_index + 1)

        elif event.key == pygame.K_e:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                self.current_index = self.logger.find_prev_event_index(self.current_index, EventType.NEW_EPISODE)
            else:
                self.current_index = self.logger.find_next_event_index(self.current_index, EventType.NEW_EPISODE)
            self.live_follow = False

        elif event.key == pygame.K_p:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                self.current_index = self.logger.find_prev_event_index(self.current_index, EventType.SELECT_PLAN)
            else:
                self.current_index = self.logger.find_next_event_index(self.current_index, EventType.SELECT_PLAN)
            self.live_follow = False

        elif event.key == pygame.K_a:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                self.current_index = self.logger.find_prev_event_index(self.current_index, EventType.ACTIVATION)
            else:
                self.current_index = self.logger.find_next_event_index(self.current_index, EventType.ACTIVATION)
            self.live_follow = False

        elif event.key == pygame.K_w:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                self.current_index = self.logger.find_prev_event_index(self.current_index, EventType.WEIGHT_UPDATE)
            else:
                self.current_index = self.logger.find_next_event_index(self.current_index, EventType.WEIGHT_UPDATE)
            self.live_follow = False

        elif event.key == pygame.K_l:
            self.live_follow = not self.live_follow

        elif event.key == pygame.K_c:
            self.show_config = not self.show_config
            if self.show_config:
                self.show_help = False
                self.config_scroll_y = 0

        elif event.key == pygame.K_o:
            self.open_folder_selector()

        elif event.key in (pygame.K_h, pygame.K_SLASH):
            self.show_help = not self.show_help
            if self.show_help:
                self.show_config = False

    def _handle_mouse_down(self, event: pygame.event.Event) -> None:
        """マウス押下イベントのハンドリング"""
        # マウスホイールによるスクロール
        if event.button == 4:  # Wheel Up
            if self.show_config:
                self.config_scroll_y = max(0, self.config_scroll_y - 40)
            elif self.view_mode == ViewMode.LINE_CHART:
                self.chart_view.scroll_filter(-1)
            return
        elif event.button == 5:  # Wheel Down
            if self.show_config:
                self.config_scroll_y = min(self.max_config_scroll, self.config_scroll_y + 40)
            elif self.view_mode == ViewMode.LINE_CHART:
                self.chart_view.scroll_filter(1)
            return

        if event.button != 1:
            return

        pos = event.pos

        # モーダル表示中のクリック
        if self.show_help or self.show_config:
            self.show_help = False
            self.show_config = False
            return

        # ヘッダーボタンの判定
        if self.view_btn_rect.collidepoint(pos):
            self.view_mode = ViewMode.LINE_CHART if self.view_mode == ViewMode.STEP else ViewMode.STEP
            return

        if self.header_btn_rect.collidepoint(pos):
            self.open_folder_selector()
            return

        # 折れ線グラフ画面での個別ボタン・トグル判定
        if self.view_mode == ViewMode.LINE_CHART:
            if self.chart_view.btn_all_rect.collidepoint(pos):
                self.chart_view.toggle_all_nodes(self.logger.max_nodes, visible=True)
                return
            if self.chart_view.btn_none_rect.collidepoint(pos):
                self.chart_view.toggle_all_nodes(self.logger.max_nodes, visible=False)
                return
            if self.chart_view.btn_save_chart_rect.collidepoint(pos):
                self.save_chart_image()
                return

            for node_idx, r in self.chart_view.node_toggle_rects:
                if r.collidepoint(pos):
                    self.chart_view.toggle_node(node_idx)
                    return

            if self.chart_view.chart_rect.collidepoint(pos):
                total_frames = len(self.logger.history)
                if total_frames > 1:
                    rel_x = max(0, min(pos[0] - self.chart_view.chart_rect.x, self.chart_view.chart_rect.width))
                    ratio = rel_x / float(self.chart_view.chart_rect.width)
                    self.current_index = int(round(ratio * (total_frames - 1)))
                    self.live_follow = False
                return

        # タイムラインスライダーの判定
        if self.slider_rect.collidepoint(pos):
            self.is_dragging_slider = True
            self._update_slider_position(pos[0])
            return

        # 下部ボタン群の判定
        for btn in self.buttons:
            if btn["rect"].collidepoint(pos):
                self._handle_button_action(btn["action"])
                return

    def _update_slider_position(self, mouse_x: int) -> None:
        """スライダー位置からフレームインデックスを更新"""
        total_frames = len(self.logger.history)
        if total_frames <= 1:
            return

        rel_x = max(0, min(mouse_x - self.slider_rect.x, self.slider_rect.width))
        ratio = rel_x / float(self.slider_rect.width)
        self.current_index = int(round(ratio * (total_frames - 1)))
        self.live_follow = False

    def _handle_button_action(self, action: str) -> None:
        """ボタンアクションの実行"""
        total_frames = len(self.logger.history)

        if action == "step_back":
            self.is_playing = False
            self.live_follow = False
            self.current_index = max(0, self.current_index - 1)

        elif action == "step_forward":
            self.is_playing = False
            self.live_follow = False
            self.current_index = min(max(0, total_frames - 1), self.current_index + 1)

        elif action == "toggle_play":
            self.is_playing = not self.is_playing

        elif action == "toggle_live":
            self.live_follow = not self.live_follow
            if self.live_follow and total_frames > 0:
                self.current_index = total_frames - 1

        elif action == "toggle_config":
            self.show_config = not self.show_config
            if self.show_config:
                self.show_help = False
                self.config_scroll_y = 0

        elif action == "toggle_help":
            self.show_help = not self.show_help
            if self.show_help:
                self.show_config = False

        elif action == "reset_index":
            self.current_index = 0
            self.is_playing = False
            self.live_follow = False

        elif action == "prev_ep":
            self.current_index = self.logger.find_prev_event_index(self.current_index, EventType.NEW_EPISODE)
            self.live_follow = False

        elif action == "next_ep":
            self.current_index = self.logger.find_next_event_index(self.current_index, EventType.NEW_EPISODE)
            self.live_follow = False

        elif action == "prev_plan":
            self.current_index = self.logger.find_prev_event_index(self.current_index, EventType.SELECT_PLAN)
            self.live_follow = False

        elif action == "next_plan":
            self.current_index = self.logger.find_next_event_index(self.current_index, EventType.SELECT_PLAN)
            self.live_follow = False

        elif action == "prev_act":
            self.current_index = self.logger.find_prev_event_index(self.current_index, EventType.ACTIVATION)
            self.live_follow = False

        elif action == "next_act":
            self.current_index = self.logger.find_next_event_index(self.current_index, EventType.ACTIVATION)
            self.live_follow = False

        elif action == "prev_weight":
            self.current_index = self.logger.find_prev_event_index(self.current_index, EventType.WEIGHT_UPDATE)
            self.live_follow = False

        elif action == "next_weight":
            self.current_index = self.logger.find_next_event_index(self.current_index, EventType.WEIGHT_UPDATE)
            self.live_follow = False

    def open_folder_selector(self) -> None:
        """フォルダ選択ダイアログを開き、新しいログをロード"""
        initial_dir = None
        if self.logger.log_file_path:
            initial_dir = os.path.dirname(os.path.abspath(self.logger.log_file_path))

        dialog = FolderSelectorDialog(initial_dir=initial_dir)
        chosen_folder = dialog.show()

        if chosen_folder:
            success = self.logger.load_from_folder(chosen_folder)
            if success:
                self.current_index = 0
                self.live_follow = True
                self.toast_msg = f"ログを読み込みました: {len(self.logger.history)} フレーム"
                self.toast_timer = 90
            else:
                self.toast_msg = f"読み込み失敗: {self.logger.last_error_msg[:40]}..."
                self.toast_timer = 120

    def save_chart_image(self) -> bool:
        """折れ線グラフの高精細PNG画像保存"""
        total_frames = len(self.logger.history)
        if total_frames <= 1:
            self.toast_msg = "保存失敗: ログデータがありません"
            self.toast_timer = 90
            return False

        export_surf = self.chart_view.export_chart_surface(self.logger.history, self.logger.max_nodes)
        if not export_surf:
            return False

        default_dir = os.path.dirname(os.path.abspath(self.logger.log_file_path)) if self.logger.log_file_path else os.getcwd()
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_file = f"sap_activation_chart_{now_str}.png"
        out_path = os.path.join(default_dir, default_file)

        try:
            pygame.image.save(export_surf, out_path)
            self.toast_msg = f"グラフ画像を保存しました: {default_file}"
            self.toast_timer = 100
            logger.info(f"Chart saved to {out_path}")
            return True
        except Exception as e:
            self.toast_msg = f"保存エラー: {e}"
            self.toast_timer = 100
            logger.error(f"Failed to save chart image: {e}")
            return False

    def update(self) -> None:
        """フレームごとの状態更新"""
        total_frames = len(self.logger.history)

        if self.live_follow and total_frames > 0:
            self.current_index = total_frames - 1

        if self.is_playing and total_frames > 0:
            if self.current_index < total_frames - 1:
                self.current_index += 1
            else:
                self.is_playing = False

        if self.toast_timer > 0:
            self.toast_timer -= 1

    def draw(self) -> None:
        """画面描画オーケストレーション"""
        self.screen.fill(COLOR_BG_MAIN)
        total_frames = len(self.logger.history)

        # 1. ヘッダー上部（タイトル、状態バッジ、画面切替、フォルダ選択）
        title_surf = self.font_title.render("SAP-net Visualizer", True, COLOR_TEXT_TITLE)
        self.screen.blit(title_surf, (20, 12))

        # リアルタイム/手動バッジ
        badge_x = 200
        if self.live_follow:
            b_text = self.font_tiny.render("● LIVE追従", True, COLOR_LIVE_TEXT)
            bw = b_text.get_width() + 14
            b_rect = pygame.Rect(badge_x, 15, bw, 20)
            pygame.draw.rect(self.screen, COLOR_LIVE_BG, b_rect, border_radius=10)
            pygame.draw.rect(self.screen, COLOR_LIVE_BORDER, b_rect, 1, border_radius=10)
            self.screen.blit(b_text, (badge_x + 7, 18))
        else:
            b_text = self.font_tiny.render("■ 手動探索", True, COLOR_MANUAL_TEXT)
            bw = b_text.get_width() + 14
            b_rect = pygame.Rect(badge_x, 15, bw, 20)
            pygame.draw.rect(self.screen, COLOR_MANUAL_BG, b_rect, border_radius=10)
            pygame.draw.rect(self.screen, COLOR_MANUAL_BORDER, b_rect, 1, border_radius=10)
            self.screen.blit(b_text, (badge_x + 7, 18))

        # 画面切替ボタン
        view_label = "グラフ画面 (G)" if self.view_mode == ViewMode.STEP else "ステップ画面 (G)"
        pygame.draw.rect(self.screen, COLOR_ACCENT_BLUE_LIGHT, self.view_btn_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_ACCENT_BLUE, self.view_btn_rect, 1, border_radius=4)
        v_txt = self.font_small.render(view_label, True, (20, 60, 130))
        self.screen.blit(v_txt, v_txt.get_rect(center=self.view_btn_rect.center))

        # 実験ログフォルダ選択ボタン
        pygame.draw.rect(self.screen, (220, 232, 245), self.header_btn_rect, border_radius=4)
        pygame.draw.rect(self.screen, (100, 140, 190), self.header_btn_rect, 1, border_radius=4)
        f_txt = self.font_small.render("実験ログフォルダ選択 (O)...", True, (15, 45, 90))
        self.screen.blit(f_txt, f_txt.get_rect(center=self.header_btn_rect.center))

        # 2. メインビュー描画（StepView または ChartView）
        resolved_info = self.logger.resolve_frame(self.current_index)

        if self.view_mode == ViewMode.STEP:
            self.step_view.draw(resolved_info, self.current_index, total_frames)
        else:
            self.chart_view.draw(self.logger.history, self.current_index, resolved_info, self.logger.max_nodes)

        # 3. タイムラインスライダー
        pygame.draw.rect(self.screen, COLOR_SLIDER_TRACK, self.slider_rect, border_radius=4)
        if total_frames > 1:
            ratio = self.current_index / float(total_frames - 1)
            handle_x = int(self.slider_rect.x + ratio * self.slider_rect.width)
            handle_rect = pygame.Rect(handle_x - 6, self.slider_rect.y - 3, 12, self.slider_rect.height + 6)
            pygame.draw.rect(self.screen, COLOR_SLIDER_HANDLE, handle_rect, border_radius=3)
            pygame.draw.rect(self.screen, (255, 255, 255), handle_rect, 1, border_radius=3)

            # スライダー右側のフレーム進捗表示
            pct = ratio * 100.0
            slider_info_txt = f"{self.current_index + 1}/{total_frames} ({pct:.1f}%)"
            slider_info_surf = self.fonts["small"].render(slider_info_txt, True, COLOR_TEXT_MUTED)
            self.screen.blit(slider_info_surf, (self.slider_rect.right + 15, self.slider_rect.centery - slider_info_surf.get_height() // 2))


        # 4. ボタン群描画
        for btn in self.buttons:
            r = btn["rect"]
            action = btn["action"]
            label = btn["label"]

            if action == "toggle_play":
                label = "一時停止" if self.is_playing else "再生"
                bg_col = (255, 235, 215) if self.is_playing else (225, 245, 230)
                border_col = (220, 130, 30) if self.is_playing else (40, 160, 60)
            elif action == "toggle_live":
                bg_col = (225, 245, 230) if self.live_follow else (240, 243, 246)
                border_col = (40, 160, 60) if self.live_follow else (180, 195, 210)
            else:
                bg_col = (245, 248, 252) if btn["type"] == "event" else (235, 242, 250)
                border_col = (195, 208, 225) if btn["type"] == "event" else (140, 170, 210)

            pygame.draw.rect(self.screen, bg_col, r, border_radius=4)
            pygame.draw.rect(self.screen, border_col, r, 1, border_radius=4)

            t_col = (20, 50, 90) if btn["type"] == "event" else (15, 35, 70)
            t_surf = self.font_small.render(label, True, t_col)
            self.screen.blit(t_surf, t_surf.get_rect(center=r.center))

        # 5. オーバーレイモーダル
        if self.show_config:
            self.max_config_scroll = self.overlays_view.draw_config_overlay(
                self.logger.log_file_path, self.config_scroll_y, self.width, self.height
            )
        elif self.show_help:
            self.overlays_view.draw_help_overlay(
                resolved_info.threshold, self.width, self.height
            )

        # 6. トースト通知
        if self.toast_timer > 0 and self.toast_msg:
            t_surf = self.font_medium.render(self.toast_msg, True, (255, 255, 255))
            tw, th = t_surf.get_width() + 24, t_surf.get_height() + 12
            tx = (self.width - tw) // 2
            ty = 50
            t_bg = pygame.Rect(tx, ty, tw, th)
            pygame.draw.rect(self.screen, (20, 35, 60), t_bg, border_radius=6)
            pygame.draw.rect(self.screen, (100, 150, 220), t_bg, 2, border_radius=6)
            self.screen.blit(t_surf, (tx + 12, ty + 6))

        pygame.display.flip()

    def run(self) -> None:
        """GUIメインループ"""
        while self.is_active:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(DEFAULT_FPS)

        pygame.quit()
