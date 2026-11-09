"""
Dialogs, Modals, and UI Popups for Stone Age: Dawn of Tribe.
Includes:
- Toast Notifications (sliding animated toasts)
- Sleep / Rest Confirmation at primitive shelter
- Overnight Tribe Harvest & Barter Summary Report
- Prehistoric Survival & Controls Guide [H]
"""

import pygame
import math
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, PALETTE, CURRENCY_ICON
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

        txt_surf = font.render(self.text, True, (255, 240, 200))
        w = txt_surf.get_width() + 32
        h = 24
        # Centered at top of screen to never obstruct viewport or gameplay
        x = (screen.get_width() - w) // 2
        y = 12 + y_offset

        bg_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # Deep tribal leather / parchment gradient
        pygame.draw.rect(bg_surf, (32, 22, 14, min(220, alpha)), (0, 0, w, h), border_radius=6)
        pygame.draw.rect(bg_surf, (190, 130, 45, min(230, alpha)), (0, 0, w, h), 1, border_radius=6)
        # Small amber jewel pins on both ends
        pygame.draw.circle(bg_surf, (255, 185, 50, alpha), (8, h // 2), 2)
        pygame.draw.circle(bg_surf, (255, 185, 50, alpha), (w - 8, h // 2), 2)

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
        
        # Modal states
        self.show_sleep_confirm = False
        self.show_summary_report = False
        self.summary_data = None
        self.show_shop = False
        self.shop_items = []
        self.shop_selected_idx = 0
        self.show_help = False

        self._modal_alpha = 0
        self._modal_scale = 0.85

    def add_toast(self, text):
        # Keep at most 1 sleek active toast at a time to prevent UI clutter
        self.toasts = [ToastNotification(text)]

    def update(self, dt):
        self.toasts = [t for t in self.toasts if t.update(dt)]
        
        is_any_modal = (self.show_sleep_confirm or self.show_summary_report or 
                        self.show_shop or self.show_help)
        
        target_alpha = 255 if is_any_modal else 0
        target_scale = 1.0 if is_any_modal else 0.85
        
        self._modal_alpha += (target_alpha - self._modal_alpha) * min(1.0, dt * 10)
        self._modal_scale += (target_scale - self._modal_scale) * min(1.0, dt * 10)

    def draw(self, screen):
        y_offset = 0
        for toast in self.toasts:
            toast.draw(screen, self.font_small, y_offset)
            y_offset += 42

        if self._modal_alpha > 5:
            if self.show_sleep_confirm:
                self._draw_sleep_confirm(screen)
            elif self.show_summary_report and self.summary_data:
                self._draw_summary_report(screen)
            elif self.show_shop:
                self._draw_shop(screen)
            elif self.show_help:
                self._draw_help(screen)

    def _draw_modal_panel(self, screen, width, height, title):
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
        pygame.draw.rect(header_surf, (65, 45, 30, 240), (0, 0, scaled_w, 48), border_radius=10)
        pygame.draw.rect(header_surf, (150, 100, 60), (0, 0, scaled_w, 48), 2, border_radius=10)
        screen.blit(header_surf, (x, y))

        t_surf = self.font_title.render(title, True, (255, 235, 195))
        screen.blit(t_surf, (x + (scaled_w - t_surf.get_width()) // 2, y + 10))

        return x, y, scaled_w, scaled_h

    def _draw_sleep_confirm(self, screen):
        x, y, w, h = self._draw_modal_panel(screen, 500, 200, "NGHỈ NGƠI TRONG MÁI ẤM")

        q_txt = self.font_large.render("Bạn có muốn bước vào chòi lá nghỉ ngơi qua đêm?", True, (50, 35, 22))
        sub_txt = self.font_small.render("(Hồi phục 100% Thể Lực và Lưu dữ liệu bộ lạc)", True, (110, 80, 50))
        
        screen.blit(q_txt, (x + (w - q_txt.get_width()) // 2, y + 68))
        screen.blit(sub_txt, (x + (w - sub_txt.get_width()) // 2, y + 96))

        btn_y = y + 134
        yes_rect = pygame.Rect(x + 35, btn_y, 195, 38)
        pygame.draw.rect(screen, (50, 140, 60), yes_rect, border_radius=8)
        pygame.draw.rect(screen, (35, 110, 45), yes_rect, 2, border_radius=8)
        yes_txt = self.font_normal.render("[Y / SPACE] Nghỉ ngơi", True, (255, 255, 255))
        screen.blit(yes_txt, (yes_rect.x + (yes_rect.width - yes_txt.get_width()) // 2, yes_rect.y + 9))

        no_rect = pygame.Rect(x + w - 230, btn_y, 195, 38)
        pygame.draw.rect(screen, (165, 55, 45), no_rect, border_radius=8)
        pygame.draw.rect(screen, (130, 40, 35), no_rect, 2, border_radius=8)
        no_txt = self.font_normal.render("[N / ESC] Tiếp tục", True, (255, 255, 255))
        screen.blit(no_txt, (no_rect.x + (no_rect.width - no_txt.get_width()) // 2, no_rect.y + 9))

    def _draw_summary_report(self, screen):
        x, y, w, h = self._draw_modal_panel(screen, 560, 440, "CHIẾN TÍCH & DOANH THU BỘ LẠC")

        d = self.summary_data
        categories = [
            ("🌾 Cây trồng & Nông sản dại:", f"+{d.get('crops', 0):,} 🐚", (50, 140, 40)),
            ("🐟 Cá & Thủy sản suối nguồn:", f"+{d.get('fish', 0):,} 🐚", (40, 110, 185)),
            ("🐔 Thú nuôi (Trứng & Sữa):", f"+{d.get('animals', 0):,} 🐚", (190, 130, 30)),
            ("🪵 Vật liệu nhặt nhạnh & khai thác:", f"+{d.get('materials', 0):,} 🐚", (150, 90, 40)),
        ]

        row_y = y + 80
        for i, (cat_name, val_str, col) in enumerate(categories):
            row_rect = pygame.Rect(x + 24, row_y + i * 48 - 4, w - 48, 42)
            row_bg = (245, 238, 225) if i % 2 == 0 else (240, 232, 218)
            pygame.draw.rect(screen, row_bg, row_rect, border_radius=6)
            pygame.draw.rect(screen, col, (row_rect.x, row_rect.y + 6, 3, 30), border_radius=1)
            
            lbl = self.font_normal.render(cat_name, True, (60, 50, 40))
            val = self.font_large.render(val_str, True, col)
            screen.blit(lbl, (row_rect.x + 14, row_rect.y + 8))
            screen.blit(val, (row_rect.right - val.get_width() - 14, row_rect.y + 6))

        total_y = row_y + len(categories) * 48 + 16
        tot_rect = pygame.Rect(x + 24, total_y + 12, w - 48, 50)
        pygame.draw.rect(screen, (255, 245, 220), tot_rect, border_radius=8)
        pygame.draw.rect(screen, (200, 160, 90), tot_rect, 2, border_radius=8)
        
        tot_lbl = self.font_title.render("TỔNG THU:", True, (50, 30, 20))
        tot_val = self.font_title.render(f"+{d.get('total', 0):,} {CURRENCY_ICON}", True, (210, 140, 20))
        screen.blit(tot_lbl, (tot_rect.x + 18, tot_rect.y + 12))
        screen.blit(tot_val, (tot_rect.right - tot_val.get_width() - 18, tot_rect.y + 12))

        tip = self.font_normal.render("Nhấn [SPACE] hoặc [ENTER] để đón ngày mới!", True, (110, 80, 50))
        screen.blit(tip, (x + (w - tip.get_width()) // 2, y + h - 48))

    def _draw_shop(self, screen):
        pass

    def _draw_help(self, screen):
        x, y, w, h = self._draw_modal_panel(screen, 760, 580, "CẨM NANG SINH TỒN THỜI ĐỒ ĐÁ")

        lines = [
            ("WASD / Mũi tên", "Di chuyển người tiền sử 4 hướng", (170, 70, 30)),
            ("Chuột Trái / SPACE", "Dùng công cụ | Nhặt nhạnh cành cây, đá cuội", (170, 70, 30)),
            ("Phím C", "Mở BÀN CHẾ TÁC & XÂY DỰNG (Rìu, Cuốc, Nhà, Lửa)", (40, 140, 55)),
            ("Phím Q", "Bật / Tắt theo dõi MỤC TIÊU KỶ NGUYÊN", (40, 140, 55)),
            ("Chuột Phải / E", "Tương tác: Nấu nướng tại Lửa Trại, Ngủ tại Chòi Lá", (170, 70, 30)),
            ("Phím 1-8 / Cuộn chuột", "Chọn công cụ & vật phẩm trên Hotbar", (170, 70, 30)),
            ("Tab", "Mở / Đóng Túi đan lau sậy (Kéo thả đồ)", (40, 130, 50)),
            ("Phím M", "Bản đồ thế giới & Sang Bản Doanh Bộ Lạc Núi Đá", (40, 130, 50)),
            ("Đống Lửa Trại", "Đứng gần bấm [E] nướng cá, củ rừng hồi Thể Lực!", (190, 110, 30)),
            ("Chòi Lá / Lều", "Đứng gần bấm [E] để ngủ qua đêm & Lưu game", (190, 110, 30)),
            ("Tiến Hóa Kỷ Nguyên", "Đồ Đá Cũ ⟶ Đồ Đá Mới ⟶ Đồ Đồng & Hưng Thịnh", (190, 130, 30)),
            ("H / F1", "Bật / Tắt cẩm nang sinh tồn này", (130, 90, 60)),
        ]

        row_y = y + 68
        for i, (key_str, desc_str, key_col) in enumerate(lines):
            row_rect = pygame.Rect(x + 20, row_y + i * 38, w - 40, 34)
            if i % 2 == 0:
                pygame.draw.rect(screen, (245, 238, 225, 200), row_rect, border_radius=5)

            k_surf = self.font_normal.render(key_str, True, key_col)
            screen.blit(k_surf, (row_rect.x + 14, row_rect.y + 6))
            
            d_surf = self.font_normal.render(desc_str, True, (50, 40, 30))
            screen.blit(d_surf, (x + 235, row_rect.y + 6))

        close_txt = self.font_normal.render("Nhấn [H] hoặc [ESC] để quay lại trò chơi", True, (110, 80, 50))
        screen.blit(close_txt, (x + (w - close_txt.get_width()) // 2, y + h - 38))
