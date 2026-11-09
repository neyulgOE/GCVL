"""
Enhanced Heads-Up Display (HUD) for Stone Age: Dawn of Tribe.
Primitive glassmorphism UI with smooth animations, carved stone calendar,
Era Milestones tracker, Crafting shortcut pill, and tribal shell currency.
"""

import pygame
import math
from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, PALETTE,
    PLAYER_MAX_STAMINA, TOOL_WATER_CAN, CURRENCY_ICON, ERAS_DATA, ERA_PALEOLITHIC
)
from src.core.visual_enhancer import VisualEnhancer

class HUD:
    def __init__(self, asset_mgr):
        self.assets = asset_mgr
        self.font_tiny = asset_mgr.fonts.get("tiny", pygame.font.SysFont("dejavusans", 10, bold=True))
        self.font_small = asset_mgr.fonts["small"]
        self.font_normal = asset_mgr.fonts["normal"]
        self.font_large = asset_mgr.fonts["large"]
        
        self.hotbar_rects = []
        self._init_hotbar_layout()

        # Animation timers
        self._pulse_timer = 0
        self._tooltip_alpha = 0
        self._tooltip_target_slot = -1
        self._stamina_display = PLAYER_MAX_STAMINA
        self._prev_gold = 0
        self._gold_flash_timer = 0

        # Clickable button rects
        self.craft_btn_rect = pygame.Rect(16, 114, 175, 26)
        self.quest_tracker_rect = pygame.Rect(16, 44, 280, 62)

    def _init_hotbar_layout(self):
        slot_size = 48
        spacing = 5
        total_slots = 8
        total_w = total_slots * slot_size + (total_slots - 1) * spacing
        start_x = (SCREEN_WIDTH - total_w) // 2
        start_y = SCREEN_HEIGHT - slot_size - 14
        
        self.hotbar_rects = []
        for i in range(total_slots):
            sx = start_x + i * (slot_size + spacing)
            self.hotbar_rects.append(pygame.Rect(sx, start_y, slot_size, slot_size))

    def get_clicked_hotbar_slot(self, mouse_pos):
        """Returns slot index (0..7) if clicked, or None."""
        for i, rect in enumerate(self.hotbar_rects):
            if rect.collidepoint(mouse_pos):
                return i
        return None

    def draw(self, screen, player, inventory, time_sys, weather_sys, camera, crafting_sys=None, quest_sys=None):
        mouse_pos = pygame.mouse.get_pos()
        hovered_slot = self.get_clicked_hotbar_slot(mouse_pos)

        # Update animation timers
        self._pulse_timer += 1 / 60.0

        # 1. Target reticle on hovered tile (Mouse-aimed)
        if hovered_slot is None and not self.craft_btn_rect.collidepoint(mouse_pos) and not self.quest_tracker_rect.collidepoint(mouse_pos):
            self._draw_mouse_target_reticle(screen, player, camera, mouse_pos)

        # 2. Top-Right Clock & Stone Age Calendar Panel
        self._draw_clock_panel(screen, time_sys, weather_sys, inventory)

        # 3. Top-Left Stamina Bar
        self._draw_stamina_bar(screen, player)

        # 4. Top-Left Era Quest Tracker
        if quest_sys:
            self._draw_quest_tracker(screen, quest_sys, crafting_sys, inventory)

        # 5. Crafting Quick Shortcut Button
        self._draw_craft_shortcut_button(screen)

        # 6. Bottom Hotbar & Hover Tooltips
        self._draw_hotbar(screen, inventory, hovered_slot)

    def _draw_rounded_gradient_rect(self, screen, rect, color_top, color_bot, radius=8, border_color=None, border_width=2):
        """Draw a panel with a vertical gradient and rounded corners."""
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for y in range(rect.height):
            t = y / max(1, rect.height - 1)
            r = int(color_top[0] + (color_bot[0] - color_top[0]) * t)
            g = int(color_top[1] + (color_bot[1] - color_top[1]) * t)
            b = int(color_top[2] + (color_bot[2] - color_top[2]) * t)
            a = color_top[3] if len(color_top) > 3 else 255
            pygame.draw.line(surf, (r, g, b, a), (0, y), (rect.width, y))
        
        mask_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask_surf, (255, 255, 255, 255), (0, 0, rect.width, rect.height), border_radius=radius)
        surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        
        screen.blit(surf, rect.topleft)
        if border_color:
            pygame.draw.rect(screen, border_color, rect, border_width, border_radius=radius)

    def _draw_mouse_target_reticle(self, screen, player, camera, mouse_pos):
        world_x, world_y = camera.screen_to_world(mouse_pos)
        target_col = int(world_x // TILE_SIZE)
        target_row = int(world_y // TILE_SIZE)

        rect_world = pygame.Rect(target_col * TILE_SIZE, target_row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        rect_screen = camera.apply(rect_world)

        in_reach = player.is_in_reach(target_col, target_row)
        
        pulse = 0.5 + 0.5 * math.sin(self._pulse_timer * 4)

        if in_reach:
            bracket_alpha = int(180 + 75 * pulse)
            bracket_col = (255, 235, 110, bracket_alpha)
            corner_len = 10
            line_w = 2
        else:
            bracket_alpha = int(100 + 60 * pulse)
            bracket_col = (200, 220, 240, bracket_alpha)
            corner_len = 7
            line_w = 1

        reticle_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        if in_reach:
            fill_alpha = int(15 + 10 * pulse)
            pygame.draw.rect(reticle_surf, (255, 235, 110, fill_alpha), 
                           (2, 2, TILE_SIZE - 4, TILE_SIZE - 4), border_radius=3)

        corners = [
            ((0, 0), (corner_len, 0), (0, corner_len)),
            ((TILE_SIZE - 1, 0), (TILE_SIZE - 1 - corner_len, 0), (TILE_SIZE - 1, corner_len)),
            ((0, TILE_SIZE - 1), (corner_len, TILE_SIZE - 1), (0, TILE_SIZE - 1 - corner_len)),
            ((TILE_SIZE - 1, TILE_SIZE - 1), (TILE_SIZE - 1 - corner_len, TILE_SIZE - 1),
             (TILE_SIZE - 1, TILE_SIZE - 1 - corner_len))
        ]
        for corner, h_end, v_end in corners:
            pygame.draw.line(reticle_surf, bracket_col, corner, h_end, line_w)
            pygame.draw.line(reticle_surf, bracket_col, corner, v_end, line_w)

        screen.blit(reticle_surf, rect_screen.topleft)

    def _draw_clock_panel(self, screen, time_sys, weather_sys, inventory):
        panel_w = 220
        panel_h = 105
        x = SCREEN_WIDTH - panel_w - 12
        y = 12

        panel_rect = pygame.Rect(x, y, panel_w, panel_h)
        VisualEnhancer.draw_cozy_panel(screen, panel_rect, border_radius=10)

        # Season badge with gradient
        season_color = time_sys.season_info["color"]
        badge_rect = pygame.Rect(x + 10, y + 8, panel_w - 20, 24)
        darker = (max(0, season_color[0] - 25), max(0, season_color[1] - 25), max(0, season_color[2] - 25))
        self._draw_rounded_gradient_rect(
            screen, badge_rect, season_color, darker,
            radius=5, border_color=(max(0, season_color[0] - 50),
                                    max(0, season_color[1] - 50),
                                    max(0, season_color[2] - 50)),
            border_width=1
        )
        season_str = f"{time_sys.season_name} - Ngày {time_sys.day}"
        VisualEnhancer.draw_text_with_shadow(
            screen, season_str, self.font_small, (x + 16, y + 12),
            text_color=(255, 255, 240), shadow_color=(35, 40, 25)
        )

        # Time & Weather with icons
        weather_labels = {"sunny": "☀ Nắng Rực", "rain": "🌧 Mưa Dầm", "storm": "⛈ Bão Tiền Sử", "snow": "❄ Băng Giá"}
        w_text = weather_labels.get(weather_sys.weather, "☀ Nắng")
        VisualEnhancer.draw_text_with_shadow(
            screen, time_sys.time_string, self.font_large, (x + 14, y + 40),
            text_color=(75, 48, 25), shadow_color=(235, 220, 195)
        )

        VisualEnhancer.draw_text_with_shadow(
            screen, w_text, self.font_small, (x + 115, y + 44),
            text_color=(95, 70, 45), shadow_color=(235, 220, 195)
        )

        # Shells indicator (Currency)
        shell_rect = pygame.Rect(x + 10, y + 70, panel_w - 20, 25)
        self._draw_rounded_gradient_rect(
            screen, shell_rect,
            (245, 225, 210, 255), (220, 195, 180, 255),
            radius=5, border_color=(170, 120, 95), border_width=1
        )
        
        # Shell Icon & count
        shell_str = f"🐚 {inventory.gold:,} Vỏ Sò"
        VisualEnhancer.draw_text_with_shadow(
            screen, shell_str, self.font_normal, (x + 18, y + 74),
            text_color=(90, 45, 25), shadow_color=(245, 230, 215)
        )

    def _draw_stamina_bar(self, screen, player):
        x = 16
        y = 16
        bar_w = 168
        bar_h = 20

        target = player.stamina
        self._stamina_display += (target - self._stamina_display) * 0.12

        bg_rect = pygame.Rect(x - 3, y - 3, bar_w + 6, bar_h + 6)
        pygame.draw.rect(screen, (30, 22, 18, 220), bg_rect, border_radius=6)
        pygame.draw.rect(screen, (60, 45, 35), (x, y, bar_w, bar_h), border_radius=5)

        ratio = max(0.0, min(1.0, self._stamina_display / PLAYER_MAX_STAMINA))
        fill_w = int(bar_w * ratio)

        if ratio > 0.5:
            col_left = (55, 185, 65)
            col_right = (80, 210, 90)
        elif ratio > 0.2:
            col_left = (215, 165, 30)
            col_right = (240, 195, 50)
        else:
            col_left = (200, 50, 40)
            col_right = (230, 70, 55)
            pulse = 0.7 + 0.3 * math.sin(self._pulse_timer * 6)
            col_left = (int(col_left[0] * pulse), int(col_left[1] * pulse), int(col_left[2] * pulse))
            col_right = (int(col_right[0] * pulse), int(col_right[1] * pulse), int(col_right[2] * pulse))

        if fill_w > 0:
            fill_surf = pygame.Surface((fill_w, bar_h), pygame.SRCALPHA)
            for fx in range(fill_w):
                t = fx / max(1, fill_w - 1)
                r = int(col_left[0] + (col_right[0] - col_left[0]) * t)
                g = int(col_left[1] + (col_right[1] - col_left[1]) * t)
                b = int(col_left[2] + (col_right[2] - col_left[2]) * t)
                pygame.draw.line(fill_surf, (r, g, b), (fx, 0), (fx, bar_h))
            
            mask_s = pygame.Surface((fill_w, bar_h), pygame.SRCALPHA)
            pygame.draw.rect(mask_s, (255, 255, 255), (0, 0, fill_w, bar_h), border_radius=5)
            fill_surf.blit(mask_s, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            screen.blit(fill_surf, (x, y))

        pygame.draw.rect(screen, (85, 60, 45), (x, y, bar_w, bar_h), 2, border_radius=5)

        stamina_str = f"Thể lực: {int(player.stamina)}/{int(PLAYER_MAX_STAMINA)}"
        VisualEnhancer.draw_text_with_shadow(
            screen, stamina_str, self.font_small, (x + 10, y + 3),
            text_color=(255, 255, 255), shadow_color=(25, 20, 20)
        )

    def _draw_quest_tracker(self, screen, quest_sys, crafting_sys, inventory):
        """Draws current Stone Age Era Milestone objective widget."""
        rect = self.quest_tracker_rect
        if not quest_sys.show_tracker:
            # Mini collapsed bar
            mini_rect = pygame.Rect(rect.x, rect.y, 140, 22)
            pygame.draw.rect(screen, (34, 26, 20, 210), mini_rect, border_radius=5)
            pygame.draw.rect(screen, (110, 80, 55), mini_rect, 1, border_radius=5)
            lbl = self.font_tiny.render("🎯 Mục tiêu [Q]", True, (240, 220, 180))
            screen.blit(lbl, (mini_rect.x + 8, mini_rect.y + 4))
            return

        # Full Tracker Banner
        pygame.draw.rect(screen, (32, 24, 18, 225), rect, border_radius=6)
        pygame.draw.rect(screen, (130, 90, 55), rect, 2, border_radius=6)

        # Header: Era Name
        era_id = crafting_sys.current_era if crafting_sys else ERA_PALEOLITHIC
        era_data = ERAS_DATA.get(era_id, {})
        era_name = era_data.get("name", "Thời Đồ Đá")
        era_col = era_data.get("badge_color", (180, 140, 90))

        era_lbl = self.font_tiny.render(f"🏛 {era_name} [Q]", True, era_col)
        screen.blit(era_lbl, (rect.x + 8, rect.y + 5))

        # Quest Title
        q = quest_sys.current_quest
        if q:
            title_lbl = self.font_small.render(q["title"], True, (255, 240, 200))
            screen.blit(title_lbl, (rect.x + 8, rect.y + 22))

            # Progress details
            prog_str = quest_sys.get_progress_string(inventory, crafting_sys, None)
            prog_lbl = self.font_tiny.render(f"Tiến độ: {prog_str}", True, (130, 220, 130))
            screen.blit(prog_lbl, (rect.x + 8, rect.y + 42))
        else:
            done_lbl = self.font_small.render("👑 Bộ Lạc Hoàn Toàn Hưng Thịnh!", True, (255, 215, 50))
            screen.blit(done_lbl, (rect.x + 8, rect.y + 28))

    def _draw_craft_shortcut_button(self, screen):
        """Draws prominent clickable shortcut pill for opening Crafting menu."""
        rect = self.craft_btn_rect
        is_hovered = rect.collidepoint(pygame.mouse.get_pos())
        bg_col = (75, 48, 28) if is_hovered else (50, 34, 22)
        border_col = (255, 190, 80) if is_hovered else (140, 95, 55)

        pygame.draw.rect(screen, bg_col, rect, border_radius=5)
        pygame.draw.rect(screen, border_col, rect, 2, border_radius=5)

        lbl = self.font_small.render("⚒ [C] Chế Tác & Xây Dựng", True, (255, 240, 210))
        screen.blit(lbl, (rect.x + 8, rect.y + 5))

    def _draw_hotbar(self, screen, inventory, hovered_slot):
        if self.hotbar_rects:
            bar_bg = pygame.Rect(
                self.hotbar_rects[0].x - 8,
                self.hotbar_rects[0].y - 6,
                self.hotbar_rects[-1].right - self.hotbar_rects[0].x + 16,
                self.hotbar_rects[0].height + 12
            )
            pygame.draw.rect(screen, (20, 16, 12, 180), bar_bg, border_radius=10)
            pygame.draw.rect(screen, (100, 70, 48, 200), bar_bg, 2, border_radius=10)

        for i, rect in enumerate(self.hotbar_rects):
            is_selected = (i == inventory.selected_index)
            is_hovered = (i == hovered_slot)

            if is_selected:
                pulse = 0.8 + 0.2 * math.sin(self._pulse_timer * 3)
                glow_alpha = int(80 * pulse)
                glow_rect = rect.inflate(6, 6)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (255, 210, 50, glow_alpha),
                               (0, 0, glow_rect.width, glow_rect.height), border_radius=8)
                screen.blit(glow_surf, glow_rect.topleft)
                
                bg_col = (255, 252, 230, 245)
                border_col = (255, 200, 35)
                border_thick = 3
            elif is_hovered:
                bg_col = (255, 250, 240, 235)
                border_col = (200, 145, 75)
                border_thick = 2
            else:
                bg_col = (248, 238, 218, 215)
                border_col = (130, 90, 60)
                border_thick = 1

            slot_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(slot_surf, bg_col, (0, 0, rect.width, rect.height), border_radius=7)
            pygame.draw.rect(slot_surf, (255, 255, 255, 30), (2, 2, rect.width - 4, rect.height // 3), border_radius=5)
            screen.blit(slot_surf, rect.topleft)
            pygame.draw.rect(screen, border_col, rect, border_thick, border_radius=7)

            # Slot number label
            num_surf = self.font_tiny.render(str(i + 1), True, (150, 130, 110))
            screen.blit(num_surf, (rect.x + 3, rect.y + 2))

            # Item icon
            item = inventory.slots[i]
            if item:
                self._draw_item_icon(screen, item, rect)

        # Tooltip for hovered slot OR active item banner
        if hovered_slot is not None and inventory.slots[hovered_slot]:
            self._draw_tooltip(screen, inventory.slots[hovered_slot], self.hotbar_rects[hovered_slot])
        else:
            active = inventory.active_item
            if active:
                item_name = active.get("name", "")
                lbl = self.font_small.render(item_name, True, (255, 255, 240))
                start_y = self.hotbar_rects[0].y
                lbl_w = lbl.get_width() + 20
                lbl_rect = pygame.Rect(SCREEN_WIDTH // 2 - lbl_w // 2, start_y - 28, lbl_w, 22)
                
                banner_surf = pygame.Surface((lbl_rect.width, lbl_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(banner_surf, (25, 20, 15, 180), 
                               (0, 0, lbl_rect.width, lbl_rect.height), border_radius=5)
                pygame.draw.rect(banner_surf, (200, 160, 90, 120),
                               (0, 0, lbl_rect.width, lbl_rect.height), 1, border_radius=5)
                screen.blit(banner_surf, lbl_rect.topleft)
                screen.blit(lbl, (lbl_rect.x + 10, lbl_rect.y + 3))

    def _draw_item_icon(self, screen, item, rect):
        itype = item.get("type")
        iid = item.get("id")
        tex = None

        if itype == "tool":
            tex = self.assets.textures.get(f"tool_{iid}") or self.assets.textures.get(f"tool_{item.get('tool_type')}")
        elif itype == "seed":
            tex = self.assets.textures.get(f"seed_{iid}") or self.assets.textures.get("seed_bag")
        elif itype == "material":
            tex = self.assets.textures.get(f"mat_{iid}")
        elif itype == "crop":
            tex = self.assets.textures.get(f"produce_{iid}")
        elif itype == "food":
            tex = self.assets.textures.get(f"food_{iid}") or self.assets.textures.get(f"produce_{iid}")
        elif itype == "fish":
            tex = self.assets.textures.get(f"fish_{iid}")
        elif itype == "animal_product":
            tex = self.assets.textures.get(f"prod_{iid}")

        if tex:
            ix = rect.x + (rect.width - tex.get_width()) // 2
            iy = rect.y + (rect.height - tex.get_height()) // 2
            screen.blit(tex, (ix, iy))
        else:
            # Fallback simple primitive item glyph
            col = (200, 160, 110)
            if "axe" in iid or "rìu" in item.get("name", "").lower():
                col = (140, 140, 150)
            elif "stick" in iid or "branch" in iid or "cành" in item.get("name", "").lower():
                col = (120, 75, 40)
            elif "flint" in iid or "pebble" in iid or "đá" in item.get("name", "").lower():
                col = (110, 115, 120)
            elif "berry" in iid or "dâu" in item.get("name", "").lower():
                col = (210, 50, 60)
            pygame.draw.circle(screen, col, (rect.centerx, rect.centery), 12)
            pygame.draw.circle(screen, (50, 40, 30), (rect.centerx, rect.centery), 12, 2)

        # Water Can / Clay Jug water meter
        if itype == "tool" and ("water" in iid or "jug" in iid or item.get("tool_type") == TOOL_WATER_CAN):
            water = item.get("water", 0)
            max_w = item.get("max_water", 35)
            bar_w = rect.width - 10
            fill_w = int((water / max(1, max_w)) * bar_w)
            bx = rect.x + 5
            by = rect.y + rect.height - 8
            pygame.draw.rect(screen, (30, 50, 80, 180), (bx, by, bar_w, 5), border_radius=2)
            if fill_w > 0:
                water_surf = pygame.Surface((fill_w, 5), pygame.SRCALPHA)
                for wx in range(fill_w):
                    t = wx / max(1, fill_w - 1)
                    r = int(60 + 40 * t)
                    g = int(160 + 40 * t)
                    b = int(220 + 30 * t)
                    pygame.draw.line(water_surf, (r, g, b, 230), (wx, 0), (wx, 5))
                screen.blit(water_surf, (bx, by))
            pygame.draw.rect(screen, (50, 80, 120), (bx, by, bar_w, 5), 1, border_radius=2)

        # Quantity badge
        qty = item.get("qty", 1)
        if itype != "tool" and qty > 1:
            q_txt = self.font_tiny.render(str(qty), True, (255, 255, 255))
            badge_w = max(14, q_txt.get_width() + 6)
            badge_x = rect.right - badge_w - 2
            badge_y = rect.bottom - 14
            badge_surf = pygame.Surface((badge_w, 13), pygame.SRCALPHA)
            pygame.draw.rect(badge_surf, (40, 30, 20, 200), (0, 0, badge_w, 13), border_radius=4)
            screen.blit(badge_surf, (badge_x, badge_y))
            screen.blit(q_txt, (badge_x + (badge_w - q_txt.get_width()) // 2, badge_y + 1))

    def _draw_tooltip(self, screen, item, slot_rect):
        """Displays rich tooltip box when hovering over hotbar slot."""
        name = item.get("name", "Vật phẩm")
        itype = item.get("type", "")
        price = item.get("price")
        stamina_restore = item.get("stamina_restore")
        
        info_lines = [name]
        if price:
            info_lines.append(f"Giá trị: {price} {CURRENCY_ICON}")
        if stamina_restore:
            info_lines.append(f"Hồi phục: +{stamina_restore} Thể Lực")
        if itype == "tool" and ("water" in item.get("id", "") or "jug" in item.get("id", "")):
            info_lines.append(f"Nước: {item.get('water', 0)}/{item.get('max_water', 35)}")

        surfs = []
        colors = []
        for i, line in enumerate(info_lines):
            if i == 0:
                colors.append((255, 255, 245))
            elif "Hồi phục" in line:
                colors.append((120, 240, 130))
            else:
                colors.append((255, 215, 80))
            surfs.append(self.font_small.render(line, True, colors[-1]))
        
        max_w = max(s.get_width() for s in surfs) + 20
        total_h = sum(s.get_height() for s in surfs) + 14
        
        tx = slot_rect.centerx - max_w // 2
        ty = slot_rect.top - total_h - 10
        tx = max(8, min(tx, SCREEN_WIDTH - max_w - 8))

        tip_rect = pygame.Rect(tx, ty, max_w, total_h)
        
        tip_surf = pygame.Surface((max_w, total_h), pygame.SRCALPHA)
        pygame.draw.rect(tip_surf, (20, 16, 12, 230), (0, 0, max_w, total_h), border_radius=6)
        pygame.draw.rect(tip_surf, (255, 255, 255, 15), (2, 2, max_w - 4, total_h // 3), border_radius=4)
        screen.blit(tip_surf, tip_rect.topleft)
        pygame.draw.rect(screen, (190, 145, 85), tip_rect, 2, border_radius=6)

        arrow_x = slot_rect.centerx
        arrow_y = tip_rect.bottom
        pygame.draw.polygon(screen, (20, 16, 12, 230),
                          [(arrow_x - 6, arrow_y - 1), (arrow_x + 6, arrow_y - 1),
                           (arrow_x, arrow_y + 5)])

        curr_y = ty + 7
        for s in surfs:
            screen.blit(s, (tx + 10, curr_y))
            curr_y += s.get_height()
