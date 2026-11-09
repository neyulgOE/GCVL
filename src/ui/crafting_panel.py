"""
Crafting and Building UI Panel for Stone Age: Dawn of Tribe.
Interactive modal window for crafting primitive tools, constructing shelter/structures,
campfire cooking, and materials processing.
"""

import pygame
import math
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, PALETTE, ERAS_DATA

CATEGORIES = [
    {"id": "tools", "title": "1. Công Cụ Đá & Kim Khí"},
    {"id": "structures", "title": "2. Xây Dựng Căn Cứ"},
    {"id": "cooking", "title": "3. Nấu Nướng Lửa Trại"},
    {"id": "materials", "title": "4. Chế Biến Vật Liệu"}
]

class CraftingPanel:
    PANEL_W = 680
    PANEL_H = 480

    def __init__(self, assets):
        self.assets = assets
        self.font_tiny = assets.fonts.get("tiny", pygame.font.SysFont("dejavusans", 10, bold=True))
        self.font_sm = assets.fonts.get("small", pygame.font.SysFont("dejavusans", 12, bold=True))
        self.font_norm = assets.fonts.get("normal", pygame.font.SysFont("dejavusans", 14, bold=True))
        self.font_large = assets.fonts.get("large", pygame.font.SysFont("dejavusans", 17, bold=True))
        self.font_title = assets.fonts.get("title", pygame.font.SysFont("dejavusans", 22, bold=True))

        self.is_open = False
        self.active_category = "tools"
        self.scroll_y = 0

        # Modal rect centered on screen
        self.x = (SCREEN_WIDTH - self.PANEL_W) // 2
        self.y = (SCREEN_HEIGHT - self.PANEL_H) // 2
        self.panel_rect = pygame.Rect(self.x, self.y, self.PANEL_W, self.PANEL_H)

        # Tab rects
        self.tab_rects = []
        self._init_tabs()

        # Cache of clickable craft buttons: list of (Rect, recipe)
        self.craft_btn_rects = []
        self.close_btn_rect = pygame.Rect(self.x + self.PANEL_W - 38, self.y + 12, 26, 26)

    def _init_tabs(self):
        tab_w = 155
        tab_h = 32
        start_x = self.x + 20
        start_y = self.y + 54
        self.tab_rects = []
        for i, cat in enumerate(CATEGORIES):
            rect = pygame.Rect(start_x + i * (tab_w + 5), start_y, tab_w, tab_h)
            self.tab_rects.append((cat["id"], rect, cat["title"]))

    def toggle(self):
        self.is_open = not self.is_open
        if self.is_open:
            self.scroll_y = 0

    def open(self):
        self.is_open = True
        self.scroll_y = 0

    def close(self):
        self.is_open = False

    def handle_mouse_down(self, pos, button, crafting_sys, inventory, primitive_structures, dialog_mgr):
        if not self.is_open:
            return False

        if not self.panel_rect.collidepoint(pos):
            # Click outside closes panel
            self.close()
            return True

        # Close button
        if self.close_btn_rect.collidepoint(pos):
            self.close()
            return True

        # Category Tabs
        for cat_id, rect, _ in self.tab_rects:
            if rect.collidepoint(pos):
                self.active_category = cat_id
                self.scroll_y = 0
                self.assets.play_sound("clink")
                return True

        # Craft Buttons
        if button == 1:
            for btn_rect, recipe, can_craft in self.craft_btn_rects:
                if btn_rect.collidepoint(pos):
                    if can_craft:
                        ok, msg, sfx = crafting_sys.craft(recipe, inventory, primitive_structures)
                        if sfx:
                            self.assets.play_sound(sfx)
                        if msg:
                            dialog_mgr.add_toast(msg)
                    else:
                        dialog_mgr.add_toast("Chưa đủ nguyên liệu chế tác!")
                    return True

        # Mouse wheel scroll
        if button == 4:  # Wheel up
            self.scroll_y = max(0, self.scroll_y - 40)
            return True
        elif button == 5:  # Wheel down
            self.scroll_y += 40
            return True

        return True  # Consume all clicks inside panel

    def draw(self, surface, crafting_sys, inventory):
        if not self.is_open:
            return

        # Dim dark backdrop
        dark_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 160))
        surface.blit(dark_overlay, (0, 0))

        # 1. Main Stone/Wood Slab Panel
        pygame.draw.rect(surface, (44, 34, 28), self.panel_rect, border_radius=10)
        pygame.draw.rect(surface, (140, 95, 60), self.panel_rect, 4, border_radius=10)
        # Inner decorative border
        inner_rect = pygame.Rect(self.x + 8, self.y + 8, self.PANEL_W - 16, self.PANEL_H - 16)
        pygame.draw.rect(surface, (70, 52, 42), inner_rect, 2, border_radius=8)

        # 2. Header Title with Prehistoric Runes
        era_info = ERAS_DATA.get(crafting_sys.current_era, {})
        title_str = f"⚒ BÀN CHẾ TÁC & XÂY DỰNG - {era_info.get('name', 'Thời Đồ Đá')}"
        title_surf = self.font_large.render(title_str, True, (255, 220, 160))
        surface.blit(title_surf, (self.x + 20, self.y + 16))

        # Close button [X]
        pygame.draw.rect(surface, (160, 50, 40), self.close_btn_rect, border_radius=4)
        pygame.draw.rect(surface, (230, 90, 80), self.close_btn_rect, 2, border_radius=4)
        x_lbl = self.font_sm.render("X", True, (255, 255, 255))
        surface.blit(x_lbl, (self.close_btn_rect.centerx - x_lbl.get_width() // 2, self.close_btn_rect.centery - x_lbl.get_height() // 2))

        # 3. Category Tabs
        for cat_id, rect, title in self.tab_rects:
            is_active = (cat_id == self.active_category)
            bg_col = (130, 85, 50) if is_active else (55, 42, 34)
            border_col = (255, 200, 120) if is_active else (90, 68, 52)
            pygame.draw.rect(surface, bg_col, rect, border_radius=5)
            pygame.draw.rect(surface, border_col, rect, 2 if is_active else 1, border_radius=5)

            txt_col = (255, 240, 200) if is_active else (180, 160, 140)
            t_surf = self.font_tiny.render(title, True, txt_col)
            surface.blit(t_surf, (rect.centerx - t_surf.get_width() // 2, rect.centery - t_surf.get_height() // 2))

        # 4. Recipes List Viewport
        list_rect = pygame.Rect(self.x + 20, self.y + 95, self.PANEL_W - 40, self.PANEL_H - 110)
        pygame.draw.rect(surface, (32, 24, 20), list_rect, border_radius=6)
        pygame.draw.rect(surface, (80, 60, 48), list_rect, 2, border_radius=6)

        # Set clipping area for scrolling
        surface.set_clip(list_rect)

        recipes = crafting_sys.get_recipes_by_category(self.active_category)
        self.craft_btn_rects = []

        item_h = 76
        start_item_y = list_rect.y + 6 - self.scroll_y

        for i, r in enumerate(recipes):
            card_y = start_item_y + i * (item_h + 6)
            card_rect = pygame.Rect(list_rect.x + 6, card_y, list_rect.width - 12, item_h)

            if card_rect.bottom < list_rect.top or card_rect.top > list_rect.bottom:
                continue

            can_craft, reason = crafting_sys.can_craft(r, inventory)

            # Card background
            card_bg = (52, 40, 32) if can_craft else (38, 30, 25)
            card_border = (160, 120, 70) if can_craft else (75, 60, 50)
            pygame.draw.rect(surface, card_bg, card_rect, border_radius=5)
            pygame.draw.rect(surface, card_border, card_rect, 1, border_radius=5)

            # Recipe Name
            name_col = (255, 230, 170) if can_craft else (160, 145, 130)
            name_surf = self.font_norm.render(r["name"], True, name_col)
            surface.blit(name_surf, (card_rect.x + 10, card_rect.y + 6))

            # Recipe Description
            desc_surf = self.font_tiny.render(r.get("desc", ""), True, (175, 160, 140))
            surface.blit(desc_surf, (card_rect.x + 10, card_rect.y + 26))

            # Ingredients formatted: "Cành: 3/3, Đá: 2/2"
            ing_parts = []
            for item_id, req_qty in r.get("ingredients", {}).items():
                cur_qty = crafting_sys._count_item(inventory, item_id)
                col_hex = "#5cdb5c" if cur_qty >= req_qty else "#ff6666"
                name_vn = "Cành Cây" if item_id == "branch" else ("Đá Cuội" if item_id == "pebble" else ("Đá Lửa" if item_id == "flint" else ("Sợi Cỏ" if item_id == "fiber" else ("Gỗ" if item_id == "wood" else ("Đất Sét" if item_id == "clay" else ("Thỏi Đồng" if item_id == "copper_bar" else item_id))))))
                ing_parts.append((f"{name_vn}: {cur_qty}/{req_qty}", cur_qty >= req_qty))

            ix = card_rect.x + 10
            for ing_str, has_enough in ing_parts:
                ic_col = (110, 220, 110) if has_enough else (240, 90, 90)
                ic_surf = self.font_tiny.render(ing_str + "   ", True, ic_col)
                surface.blit(ic_surf, (ix, card_rect.y + 50))
                ix += ic_surf.get_width()

            # Craft Action Button
            btn_w = 95
            btn_h = 32
            btn_rect = pygame.Rect(card_rect.right - btn_w - 10, card_rect.centery - btn_h // 2, btn_w, btn_h)

            btn_bg = (40, 130, 50) if can_craft else (70, 55, 45)
            btn_border = (80, 210, 100) if can_craft else (100, 80, 65)
            pygame.draw.rect(surface, btn_bg, btn_rect, border_radius=4)
            pygame.draw.rect(surface, btn_border, btn_rect, 2, border_radius=4)

            btn_txt = "Chế Tác" if r.get("category") != "structures" else "Xây Dựng"
            if r.get("category") == "cooking":
                btn_txt = "Nướng"
            btn_col = (255, 255, 255) if can_craft else (140, 130, 120)
            btn_surf = self.font_sm.render(btn_txt, True, btn_col)
            surface.blit(btn_surf, (btn_rect.centerx - btn_surf.get_width() // 2, btn_rect.centery - btn_surf.get_height() // 2))

            # Store for click detection
            self.craft_btn_rects.append((btn_rect, r, can_craft))

        # Reset clipping
        surface.set_clip(None)
