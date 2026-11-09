"""
Dialogs, Notifications & Spectator Guide for Stone Age: Primeval World.
Includes:
- Sleek Toast Notifications (weather changes, season notifications)
- Nature Observation & Spectator Controls Guide [H]
"""

import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, PALETTE
from src.core.visual_enhancer import VisualEnhancer


class ToastNotification:
    def __init__(self, text, duration=2.5):
        self.text = text
        self.duration = duration
        self.timer = duration
        self.fade_in = 0.0

    def update(self, dt):
        self.timer -= dt
        if self.fade_in < 1.0:
            self.fade_in = min(1.0, self.fade_in + dt * 6.0)
        return self.timer > 0

    def draw(self, screen, font, y_offset=0):
        fade = min(1.0, self.timer / 0.4) * self.fade_in
        alpha = int(255 * fade)
        if alpha <= 0:
            return

        txt_surf = font.render(self.text, True, (255, 245, 220))
        w = txt_surf.get_width() + 32
        h = 24
        x = (screen.get_width() - w) // 2
        y = 12 + y_offset

        bg_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, (28, 22, 16, min(220, alpha)), (0, 0, w, h), border_radius=6)
        pygame.draw.rect(bg_surf, (180, 130, 60, min(230, alpha)), (0, 0, w, h), 1, border_radius=6)
        pygame.draw.circle(bg_surf, (255, 205, 80, alpha), (8, h // 2), 2)
        pygame.draw.circle(bg_surf, (255, 205, 80, alpha), (w - 8, h // 2), 2)

        screen.blit(bg_surf, (x, y))

        txt_alpha_surf = pygame.Surface(txt_surf.get_size(), pygame.SRCALPHA)
        txt_alpha_surf.blit(txt_surf, (0, 0))
        txt_alpha_surf.set_alpha(alpha)
        screen.blit(txt_alpha_surf, (x + 16, y + (h - txt_surf.get_height()) // 2))


class DialogManager:
    def __init__(self, asset_mgr):
        self.assets = asset_mgr
        self.font_small = asset_mgr.fonts["small"]
        self.font_normal = asset_mgr.fonts["normal"]
        self.font_large = asset_mgr.fonts["large"]
        self.font_title = asset_mgr.fonts["title"]

        self.toasts = []
        self.show_help = False
        self._modal_alpha = 0
        self._modal_scale = 0.85

    def add_toast(self, text):
        self.toasts = [ToastNotification(text)]

    def toggle_help(self):
        self.show_help = not self.show_help

    def update(self, dt):
        self.toasts = [t for t in self.toasts if t.update(dt)]

        target_alpha = 255 if self.show_help else 0
        target_scale = 1.0 if self.show_help else 0.85

        self._modal_alpha += (target_alpha - self._modal_alpha) * min(1.0, dt * 10)
        self._modal_scale += (target_scale - self._modal_scale) * min(1.0, dt * 10)

    def draw(self, screen):
        y_offset = 0
        for toast in self.toasts:
            toast.draw(screen, self.font_small, y_offset)
            y_offset += 42

        if self._modal_alpha > 5 and self.show_help:
            self._draw_help(screen)

    def _draw_help(self, screen):
        width = 720
        height = 480

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        alpha = int(self._modal_alpha * 0.7)
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))

        scaled_w = int(width * self._modal_scale)
        scaled_h = int(height * self._modal_scale)
        x = (SCREEN_WIDTH - scaled_w) // 2
        y = (SCREEN_HEIGHT - scaled_h) // 2
        panel_rect = pygame.Rect(x, y, scaled_w, scaled_h)

        VisualEnhancer.draw_cozy_panel(screen, panel_rect, border_radius=12)

        # Header title
        header_surf = pygame.Surface((scaled_w, 48), pygame.SRCALPHA)
        pygame.draw.rect(header_surf, (55, 42, 28, 240), (0, 0, scaled_w, 48), border_radius=10)
        pygame.draw.rect(header_surf, (140, 100, 55), (0, 0, scaled_w, 48), 2, border_radius=10)
        t_surf = self.font_large.render("HƯỚNG DẪN QUAN SÁT THẾ GIỚI TỰ NHIÊN (SPECTATOR MODE)", True, (255, 235, 180))
        header_surf.blit(t_surf, ((scaled_w - t_surf.get_width()) // 2, 12))
        screen.blit(header_surf, (x, y))

        lines = [
            ("WASD / Phím Mũi Tên", "Di chuyển camera quan sát tự do 4 hướng", (180, 80, 35)),
            ("Giữ Shift + WASD", "Tăng tốc độ di chuyển camera (1.500 px/giây)", (180, 80, 35)),
            ("Giữ Ctrl + WASD", "Di chuyển chậm tỉ mỉ để ngắm cảnh (280 px/giây)", (180, 80, 35)),
            ("Chuột Giữa / Chuột Phải", "Nhấn giữ và kéo thả chuột để lia camera tự do", (45, 135, 60)),
            ("Phím M", "Bật / Tắt Bản Đồ Đại Lục Hoang Dã (Palworld Atlas)", (35, 115, 175)),
            ("Phím H / F1", "Bật / Tắt bảng hướng dẫn quan sát này", (140, 95, 55)),
            ("Phím ESC", "Đóng cửa sổ hướng dẫn / Thoát", (160, 50, 45)),
        ]

        row_y = y + 72
        for i, (key_str, desc_str, key_col) in enumerate(lines):
            row_rect = pygame.Rect(x + 24, row_y + i * 44, scaled_w - 48, 38)
            if i % 2 == 0:
                pygame.draw.rect(screen, (244, 238, 222, 210), row_rect, border_radius=6)

            k_surf = self.font_normal.render(key_str, True, key_col)
            screen.blit(k_surf, (row_rect.x + 14, row_rect.y + 8))

            d_surf = self.font_normal.render(desc_str, True, (50, 38, 26))
            screen.blit(d_surf, (x + 250, row_rect.y + 8))

        close_txt = self.font_normal.render("Nhấn [H] hoặc [ESC] để quay lại màn hình quan sát", True, (110, 80, 50))
        screen.blit(close_txt, (x + (scaled_w - close_txt.get_width()) // 2, y + scaled_h - 42))
