"""
SAP-net Visualizer 描画基底クラス BaseView
"""
import pygame
from typing import Dict, Any
from ..theme import FONT_FAMILY_CANDIDATES, COLOR_TEXT_BODY


class BaseView:
    """描画コンポーネントの共通基底クラス"""
    def __init__(self, screen: pygame.Surface, fonts: Dict[str, pygame.font.Font]):
        self.screen = screen
        self.fonts = fonts
        
        self.font_tiny = fonts.get("tiny")
        self.font_small = fonts.get("small")
        self.font_medium = fonts.get("medium")
        self.font_title = fonts.get("title")

        # サブヘッダー水平スクロール状態
        self.header_scroll_offset = 0.0
        self.header_scroll_dir = 1.0
        self.header_scroll_pause_timer = 0

    @classmethod
    def create_default_fonts(cls) -> Dict[str, pygame.font.Font]:
        """日本語対応フォントを一括生成して返す"""
        return {
            "tiny": pygame.font.SysFont(FONT_FAMILY_CANDIDATES, 11, bold=True),
            "small": pygame.font.SysFont(FONT_FAMILY_CANDIDATES, 13),
            "medium": pygame.font.SysFont(FONT_FAMILY_CANDIDATES, 15, bold=True),
            "title": pygame.font.SysFont(FONT_FAMILY_CANDIDATES, 18, bold=True),
        }

    def draw_subheader_info(self, info_str: str, y_pos: int = 46, max_width: int = 660) -> None:
        """サブヘッダー情報（フレーム・エピソード・ステップ等）をクリッピング＆長文時に水平動的自動スクロール描画"""
        info_surf = self.font_medium.render(info_str, True, COLOR_TEXT_BODY)
        txt_w = info_surf.get_width()

        if txt_w <= max_width:
            self.screen.blit(info_surf, (20, y_pos))
        else:
            old_clip = self.screen.get_clip()
            clip_rect = pygame.Rect(20, y_pos - 2, max_width, info_surf.get_height() + 4)
            self.screen.set_clip(clip_rect)

            max_scroll = float(txt_w - max_width)
            speed = 0.8  # スクロールスピード

            if self.header_scroll_pause_timer > 0:
                self.header_scroll_pause_timer -= 1
            else:
                self.header_scroll_offset += self.header_scroll_dir * speed
                if self.header_scroll_offset >= max_scroll:
                    self.header_scroll_offset = max_scroll
                    self.header_scroll_dir = -1.0
                    self.header_scroll_pause_timer = 35  # 端で一定フレーム一時停止
                elif self.header_scroll_offset <= 0.0:
                    self.header_scroll_offset = 0.0
                    self.header_scroll_dir = 1.0
                    self.header_scroll_pause_timer = 35

            render_x = 20 - int(self.header_scroll_offset)
            self.screen.blit(info_surf, (render_x, y_pos))
            self.screen.set_clip(old_clip)
