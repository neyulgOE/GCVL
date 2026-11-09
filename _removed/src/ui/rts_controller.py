"""
RTS Controller for Stone Age: Dawn of Tribe.
Bộ điều khiển Chiến thuật Thời gian thực (AOE Style):
- Kéo quét chuột trái chọn nhiều dân (Drag-box selection marquee)
- Nhấp chuột phải ra lệnh di chuyển / khai thác / chiến đấu (Smart RMB)
- Phím tắt kinh điển: [,] chọn dân rảnh rỗi, [H] về trại chính, [B] dựng lều
- Bảng thông tin dân cư & Thanh trạng thái tài nguyên bộ tộc trên đầu màn hình
"""

import pygame
import math
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT

class RTSController:
    def __init__(self, settlement_manager, camera, wildlife_mgr=None):
        self.settlement_mgr = settlement_manager
        self.camera = camera
        self.wildlife_mgr = wildlife_mgr

        # Drag-box state
        self.is_dragging = False
        self.drag_start = (0, 0)
        self.drag_current = (0, 0)

        # Right-click command feedback animation
        self.click_marker_pos = None
        self.click_marker_timer = 0.0

        # UI & Resource Icon Cache
        self._res_icons = {}
        import os
        for k in ["meat", "berries", "wood", "flint", "ivory", "warmth"]:
            p = f"assets/ui/icons/icon_{k}.png"
            if os.path.exists(p):
                raw = pygame.image.load(p).convert_alpha()
                self._res_icons[k] = pygame.transform.smoothscale(raw, (22, 22))
            else:
                self._res_icons[k] = None

        uc_p = "assets/ui/unit_card_frame.png"
        self._unit_card_frame = pygame.image.load(uc_p).convert_alpha() if os.path.exists(uc_p) else None

    def handle_mouse_down(self, event):
        """Mouse button pressed."""
        if event.button == 1:
            # Left Click: Start drag-box selection marquee
            self.is_dragging = True
            self.drag_start = event.pos
            self.drag_current = event.pos
            return False

        elif event.button == 3:
            # Right Click: Command selected villagers
            wx, wy = self.camera.screen_to_world(event.pos)
            selected = self.settlement_mgr.get_selected_villagers()
            if selected:
                # Check if clicked on a wild prehistoric beast
                target_beast = None
                if self.wildlife_mgr:
                    target_beast = self.wildlife_mgr.get_beast_at_world(wx, wy)

                if target_beast:
                    for v in selected:
                        v.command_interact("animal", (target_beast.x, target_beast.y), target_beast)
                    self.settlement_mgr.add_event_notification(f"🏹 Đội thợ săn bắt đầu bao vây {target_beast.name}!")
                else:
                    self.settlement_mgr.command_selected_move(wx, wy)

                self.click_marker_pos = (wx, wy)
                self.click_marker_timer = 0.4
                return True
        return False

    def handle_mouse_motion(self, event):
        """Mouse movement while dragging."""
        if self.is_dragging:
            self.drag_current = event.pos

    def handle_mouse_up(self, event):
        """Mouse button released: finalize selection."""
        if event.button == 1 and self.is_dragging:
            self.is_dragging = False
            x1, y1 = self.drag_start
            x2, y2 = self.drag_current

            rect_w = abs(x2 - x1)
            rect_h = abs(y2 - y1)

            if rect_w < 8 and rect_h < 8:
                # Single Click Selection
                wx, wy = self.camera.screen_to_world(event.pos)
                found = self.settlement_mgr.select_single_at_world(wx, wy)
                if not found:
                    self.settlement_mgr.deselect_all()
            else:
                # Box Selection Marquee
                rx = min(x1, x2)
                ry = min(y1, y2)
                sel_rect = pygame.Rect(rx, ry, rect_w, rect_h)
                self.settlement_mgr.select_in_box(sel_rect, self.camera)
            return True
        return False

    def handle_key_down(self, event, player):
        """Handles hotkeys: [,] for idle villager, [H] for camp, etc."""
        if event.key in [pygame.K_COMMA, pygame.K_PERIOD]:
            # Cycle to next Idle Villager
            idle = self.settlement_mgr.get_idle_villager()
            if idle:
                self.settlement_mgr.deselect_all()
                idle.is_selected = True
                # Move camera towards idle villager
                self.camera.snap_to(idle.hitbox)
                self.settlement_mgr.add_event_notification(f"📍 Đã chọn dân rảnh rỗi: {idle.name} ({idle.role})")
                return True
            else:
                self.settlement_mgr.add_event_notification("Tất cả dân cư đều đang có việc làm!")
                return True

        elif event.key == pygame.K_h:
            # Home key: center on central campfire
            cf_x, cf_y = self.settlement_mgr.get_campfire_center()
            camp_rect = pygame.Rect(int(cf_x - 16), int(cf_y - 16), 32, 32)
            self.camera.snap_to(camp_rect)
            self.settlement_mgr.add_event_notification("🏠 Quay về Hốc Đá & Lửa Trại Cội Nguồn")
            return True

        return False

    def update(self, dt):
        """Updates animation markers."""
        if self.click_marker_timer > 0:
            self.click_marker_timer -= dt

    def draw(self, surface, fonts):
        """Draws RTS UI elements: drag marquee, right-click marker, top banner, selection card."""
        font_sm = fonts.get("small", pygame.font.SysFont("dejavusans", 12, bold=True))
        font_tiny = fonts.get("tiny", pygame.font.SysFont("dejavusans", 10, bold=True))

        # 1. Right Click Move Command Ripple Marker
        if self.click_marker_pos and self.click_marker_timer > 0:
            scr_pos = self.camera.world_to_screen(self.click_marker_pos)
            progress = 1.0 - (self.click_marker_timer / 0.4)
            rad = int(8 + progress * 16)
            alpha = int((1.0 - progress) * 220)
            
            rip_surf = pygame.Surface((rad * 2 + 4, rad * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(rip_surf, (80, 240, 140, alpha), (rad + 2, rad + 2), rad, 2)
            pygame.draw.circle(rip_surf, (255, 255, 255, alpha), (rad + 2, rad + 2), 3)
            surface.blit(rip_surf, (scr_pos[0] - rad - 2, scr_pos[1] - rad - 2))

        # 2. RTS Drag-box Selection Marquee
        if self.is_dragging:
            x1, y1 = self.drag_start
            x2, y2 = self.drag_current
            rx = min(x1, x2)
            ry = min(y1, y2)
            rw = abs(x2 - x1)
            rh = abs(y2 - y1)

            if rw > 4 or rh > 4:
                # Translucent fill
                box_surf = pygame.Surface((rw, rh), pygame.SRCALPHA)
                box_surf.fill((80, 240, 130, 45))
                surface.blit(box_surf, (rx, ry))
                # Crisp green dashed-like border
                pygame.draw.rect(surface, (100, 255, 150, 220), (rx, ry, rw, rh), 1)

        # 3. Top HUD: Tribal Settlement Resource & Population Bar
        self._draw_settlement_top_bar(surface, font_sm, font_tiny)

        # 4. Bottom Selection Card: Info of Selected Villager(s)
        self._draw_selection_card(surface, font_sm, font_tiny)

    def _draw_settlement_top_bar(self, surface, font_sm, font_tiny):
        """Draws top banner showing Population, Food, Wood, Stone, and Warmth status."""
        mgr = self.settlement_mgr
        bar_w = 640
        bar_h = 32
        bx = (surface.get_width() - bar_w) // 2
        by = 8

        # Background panel
        p_surf = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        pygame.draw.rect(p_surf, (24, 18, 14, 215), (0, 0, bar_w, bar_h), border_radius=6)
        pygame.draw.rect(p_surf, (140, 95, 45, 220), (0, 0, bar_w, bar_h), 2, border_radius=6)
        surface.blit(p_surf, (bx, by))

        # Stats strings
        pop_cur = mgr.current_population
        pop_max = mgr.housing_capacity
        is_full = (pop_cur >= pop_max)
        pop_col = (255, 100, 90) if is_full else (255, 235, 170)
        pop_txt = f"👥 Dân: {pop_cur}/{pop_max}" + (" (ĐẦY LỀU!)" if is_full else "")
        pop_lbl = font_sm.render(pop_txt, True, pop_col)

        # Blit stats across top bar with authentic prehistoric icons
        surface.blit(pop_lbl, (bx + 14, by + 6))

        cur_x = bx + 195
        if self._res_icons.get("meat"):
            surface.blit(self._res_icons["meat"], (cur_x, by + 5))
            cur_x += 24
        food_lbl = font_sm.render(f"{mgr.total_food_units}", True, (255, 220, 140))
        surface.blit(food_lbl, (cur_x, by + 6))
        cur_x += food_lbl.get_width() + 14

        if self._res_icons.get("wood"):
            surface.blit(self._res_icons["wood"], (cur_x, by + 5))
            cur_x += 24
        wood_lbl = font_sm.render(f"{mgr.stockpile['wood']}", True, (215, 215, 220))
        surface.blit(wood_lbl, (cur_x, by + 6))
        cur_x += wood_lbl.get_width() + 14

        if self._res_icons.get("flint"):
            surface.blit(self._res_icons["flint"], (cur_x, by + 5))
            cur_x += 24
        flint_lbl = font_sm.render(f"{mgr.stockpile['stone']}", True, (215, 215, 220))
        surface.blit(flint_lbl, (cur_x, by + 6))
        cur_x += flint_lbl.get_width() + 14

        if self._res_icons.get("ivory"):
            surface.blit(self._res_icons["ivory"], (cur_x, by + 5))
            cur_x += 24
        pelt_lbl = font_sm.render(f"{mgr.stockpile['pelt']}", True, (215, 215, 220))
        surface.blit(pelt_lbl, (cur_x, by + 6))

        # Hotkey hint on the right
        hint_lbl = font_tiny.render("[,] Dân rảnh | [H] Về Trại", True, (180, 160, 130))
        surface.blit(hint_lbl, (bx + bar_w - hint_lbl.get_width() - 10, by + 8))

    def _draw_selection_card(self, surface, font_sm, font_tiny):
        """Draws detailed status card at bottom screen when villager(s) are selected."""
        selected = self.settlement_mgr.get_selected_villagers()
        if not selected:
            return

        cw = 420
        ch = 72
        cx = (surface.get_width() - cw) // 2
        cy = surface.get_height() - ch - 12

        if self._unit_card_frame:
            scaled_frame = pygame.transform.smoothscale(self._unit_card_frame, (cw, ch))
            surface.blit(scaled_frame, (cx, cy))
        else:
            card_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            pygame.draw.rect(card_surf, (22, 16, 12, 230), (0, 0, cw, ch), border_radius=8)
            pygame.draw.rect(card_surf, (80, 200, 120, 220), (0, 0, cw, ch), 2, border_radius=8)
            surface.blit(card_surf, (cx, cy))

        if len(selected) == 1:
            v = selected[0]
            # Name & Role & Age
            role_map = {
                "chieftain": "Tộc Trưởng", "shaman": "Thầy Mo", "hunter": "Thợ Săn",
                "gatherer": "Hái Lượm", "worker": "Lao Động", "child": "Trẻ Nhỏ"
            }
            r_str = role_map.get(v.role, v.role)
            stage_str = "Trẻ" if v.stage == "child" else ("Tráng niên" if v.stage == "adult" else "Lão niên")
            title_txt = f"{v.name} ({r_str} - {stage_str}, {v.age_seasons // 4} tuổi)"
            surface.blit(font_sm.render(title_txt, True, (140, 255, 170)), (cx + 12, cy + 8))

            # Health & Hunger bars
            # Health
            surface.blit(font_tiny.render("Máu:", True, (220, 220, 220)), (cx + 12, cy + 32))
            pygame.draw.rect(surface, (40, 30, 25), (cx + 46, cy + 33, 90, 8), border_radius=2)
            hw = int((v.health / v.max_health) * 90)
            pygame.draw.rect(surface, (70, 210, 85), (cx + 46, cy + 33, hw, 8), border_radius=2)

            # Hunger
            surface.blit(font_tiny.render("No:", True, (220, 220, 220)), (cx + 150, cy + 32))
            pygame.draw.rect(surface, (40, 30, 25), (cx + 176, cy + 33, 90, 8), border_radius=2)
            nw = int((v.hunger / 100.0) * 90)
            pygame.draw.rect(surface, (230, 160, 40), (cx + 176, cy + 33, nw, 8), border_radius=2)

            # Warmth
            surface.blit(font_tiny.render("Ấm:", True, (220, 220, 220)), (cx + 280, cy + 32))
            pygame.draw.rect(surface, (40, 30, 25), (cx + 310, cy + 33, 90, 8), border_radius=2)
            ww = int((v.warmth / 100.0) * 90)
            pygame.draw.rect(surface, (210, 90, 50), (cx + 310, cy + 33, ww, 8), border_radius=2)

            # Current task state
            task_map = {
                "idle": "Đang rảnh rỗi quanh trại",
                "walk": "Đang di chuyển đến mục tiêu",
                "gather": "Đang hái quả / nhặt cành khô",
                "chop": "Đang chặt gỗ",
                "hunt": "Đang săn mồi / chiến đấu",
                "carry_back": "Đang khiêng tài nguyên về kho",
                "dead": "Đã ngã xuống"
            }
            state_txt = f"Hành động: {task_map.get(v.state, v.state)}"
            surface.blit(font_tiny.render(state_txt, True, (200, 190, 175)), (cx + 12, cy + 50))
        else:
            # Multi-selection summary
            title_txt = f"Đang chọn {len(selected)} cư dân bộ tộc"
            surface.blit(font_sm.render(title_txt, True, (140, 255, 170)), (cx + 14, cy + 12))
            
            names = ", ".join([v.name for v in selected[:5]])
            if len(selected) > 5:
                names += f" và {len(selected) - 5} người khác"
            surface.blit(font_tiny.render(f"Thành viên: {names}", True, (220, 215, 200)), (cx + 14, cy + 34))
            surface.blit(font_tiny.render("Nhấp chuột phải lên mặt đất để di chuyển đội hình", True, (180, 160, 130)), (cx + 14, cy + 50))
