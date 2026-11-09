"""
Inventory Panel UI for Green Valley Tales.
Full-screen inventory panel with:
- Backpack grid (Tab to toggle)
- Storage chest grid (interact with chest)
- Drag-and-drop items between hotbar, bag, and storage
- Upgrade buttons with cost display
"""

import pygame
import math
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, PALETTE, TOOL_WATER_CAN
from src.economy.inventory import BACKPACK_UPGRADES, STORAGE_UPGRADES
from src.core.visual_enhancer import VisualEnhancer


class InventoryPanel:
    SLOT_SIZE = 46
    SLOT_GAP = 4
    COLS = 8  # 8 columns grid

    def __init__(self, assets):
        self.assets = assets
        self.font_tiny = assets.fonts.get("tiny")
        self.font_small = assets.fonts["small"]
        self.font_normal = assets.fonts["normal"]
        self.font_large = assets.fonts["large"]
        self.font_title = assets.fonts["title"]

        # Panel state
        self.show_bag = False
        self.show_storage = False

        # Drag state
        self.dragging = False
        self.drag_item = None
        self.drag_source = None  # ("hotbar", idx), ("bag", idx), ("storage", idx)
        self.drag_offset = (0, 0)
        self.drag_pos = (0, 0)

        # Pre-calculated rects
        self._bag_panel_rect = None
        self._bag_slot_rects = []
        self._hotbar_panel_rects = []
        self._storage_slot_rects = []
        self._upgrade_btn_rect = None
        self._storage_upgrade_btn_rect = None

        self._modal_alpha = 0.0

    def toggle_bag(self):
        self.show_bag = not self.show_bag
        if not self.show_bag:
            self.cancel_drag()
            self.show_storage = False

    def open_storage(self):
        self.show_storage = True
        self.show_bag = True

    def close_all(self):
        self.show_bag = False
        self.show_storage = False
        self.cancel_drag()

    def is_open(self):
        return self.show_bag or self.show_storage

    def cancel_drag(self):
        self.dragging = False
        self.drag_item = None
        self.drag_source = None

    def update(self, dt):
        target = 1.0 if self.show_bag else 0.0
        diff = target - self._modal_alpha
        self._modal_alpha += diff * min(1.0, dt * 8.0)
        if abs(diff) < 0.01:
            self._modal_alpha = target

    def handle_mouse_down(self, pos, button, inventory, storage=None):
        """Handle mouse down in inventory panel. Returns True if consumed."""
        if not self.show_bag:
            return False

        if button == 1:  # Left click
            # Check bag slots
            for i, rect in enumerate(self._bag_slot_rects):
                if i < inventory.bag_capacity and rect.collidepoint(pos):
                    item = inventory.bag[i]
                    if item:
                        self.dragging = True
                        self.drag_item = item
                        self.drag_source = ("bag", i)
                        self.drag_pos = pos
                        inventory.bag[i] = None
                    return True

            # Check hotbar slots in panel
            for i, rect in enumerate(self._hotbar_panel_rects):
                if rect.collidepoint(pos):
                    item = inventory.hotbar[i]
                    if item:
                        self.dragging = True
                        self.drag_item = item
                        self.drag_source = ("hotbar", i)
                        self.drag_pos = pos
                        inventory.hotbar[i] = None
                    return True

            # Check storage slots
            if self.show_storage and storage:
                for i, rect in enumerate(self._storage_slot_rects):
                    if i < storage.capacity and rect.collidepoint(pos):
                        item = storage.slots[i]
                        if item:
                            self.dragging = True
                            self.drag_item = item
                            self.drag_source = ("storage", i)
                            self.drag_pos = pos
                            storage.slots[i] = None
                        return True

            # Check upgrade button
            if self._upgrade_btn_rect and self._upgrade_btn_rect.collidepoint(pos):
                return True  # Handled in mouse_up

            if self._storage_upgrade_btn_rect and self._storage_upgrade_btn_rect.collidepoint(pos):
                return True

            # If clicked outside panel, close
            if self._bag_panel_rect and not self._bag_panel_rect.collidepoint(pos):
                self.close_all()
                return True

        return self.show_bag  # Consume all clicks when open

    def handle_mouse_up(self, pos, button, inventory, storage=None):
        """Handle mouse up - drop dragged item."""
        if not self.show_bag:
            return False

        if button == 1 and self.dragging and self.drag_item:
            dropped = False

            # Try drop on bag slots
            for i, rect in enumerate(self._bag_slot_rects):
                if i < inventory.bag_capacity and rect.collidepoint(pos):
                    # Swap with existing
                    existing = inventory.bag[i]
                    inventory.bag[i] = self.drag_item
                    if existing and self.drag_source:
                        self._put_back(existing, self.drag_source, inventory, storage)
                    dropped = True
                    break

            # Try drop on hotbar slots
            if not dropped:
                for i, rect in enumerate(self._hotbar_panel_rects):
                    if rect.collidepoint(pos):
                        existing = inventory.hotbar[i]
                        inventory.hotbar[i] = self.drag_item
                        if existing and self.drag_source:
                            self._put_back(existing, self.drag_source, inventory, storage)
                        dropped = True
                        break

            # Try drop on storage slots
            if not dropped and self.show_storage and storage:
                for i, rect in enumerate(self._storage_slot_rects):
                    if i < storage.capacity and rect.collidepoint(pos):
                        existing = storage.slots[i]
                        storage.slots[i] = self.drag_item
                        if existing and self.drag_source:
                            self._put_back(existing, self.drag_source, inventory, storage)
                        dropped = True
                        break

            # If not dropped anywhere valid, return to source
            if not dropped and self.drag_source:
                self._put_back(self.drag_item, self.drag_source, inventory, storage)

            self.cancel_drag()
            return True

        # Check upgrade buttons
        if button == 1:
            if self._upgrade_btn_rect and self._upgrade_btn_rect.collidepoint(pos):
                ok, msg = inventory.upgrade_bag()
                return True
            if self._storage_upgrade_btn_rect and self._storage_upgrade_btn_rect.collidepoint(pos):
                if storage:
                    ok, msg = storage.upgrade(inventory)
                return True

        return self.show_bag

    def _put_back(self, item, source, inventory, storage):
        """Put an item back to its source slot."""
        src_type, src_idx = source
        if src_type == "bag" and src_idx < inventory.bag_capacity:
            inventory.bag[src_idx] = item
        elif src_type == "hotbar":
            inventory.hotbar[src_idx] = item
        elif src_type == "storage" and storage and src_idx < storage.capacity:
            storage.slots[src_idx] = item

    def handle_mouse_move(self, pos):
        if self.dragging:
            self.drag_pos = pos

    def draw(self, screen, inventory, storage=None):
        if self._modal_alpha < 0.01:
            return

        alpha = self._modal_alpha

        # Dim backdrop
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, int(140 * alpha)))
        screen.blit(dim, (0, 0))

        # Calculate layout
        has_storage = self.show_storage and storage is not None
        
        if has_storage:
            # Side by side: bag left, storage right
            total_w = 520 * 2 + 30
            panel_x = (SCREEN_WIDTH - total_w) // 2
            self._draw_bag_panel(screen, inventory, panel_x, alpha)
            self._draw_storage_panel(screen, storage, inventory, panel_x + 540, alpha)
        else:
            # Centered bag panel
            panel_x = (SCREEN_WIDTH - 520) // 2
            self._draw_bag_panel(screen, inventory, panel_x, alpha)

        # Draw dragged item on top
        if self.dragging and self.drag_item:
            self._draw_item_at(screen, self.drag_item, self.drag_pos[0] - 20, self.drag_pos[1] - 20)

    def _draw_bag_panel(self, screen, inventory, x, alpha):
        bag_rows = math.ceil(inventory.bag_capacity / self.COLS)
        panel_h = 70 + bag_rows * (self.SLOT_SIZE + self.SLOT_GAP) + 90 + 50
        panel_w = 500
        y = max(20, (SCREEN_HEIGHT - panel_h) // 2)

        self._bag_panel_rect = pygame.Rect(x, y, panel_w, panel_h)

        # Panel background
        scale = 0.9 + 0.1 * alpha
        sw = int(panel_w * scale)
        sh = int(panel_h * scale)
        sx = x + (panel_w - sw) // 2
        sy = y + (panel_h - sh) // 2

        # Shadow
        shadow = pygame.Surface((sw + 12, sh + 12), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, int(50 * alpha)), (0, 0, sw + 12, sh + 12), border_radius=14)
        screen.blit(shadow, (sx - 6, sy - 2))

        # Main panel
        panel = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for row in range(sh):
            t = row / max(1, sh - 1)
            r = int(245 - 10 * t)
            g = int(238 - 12 * t)
            b = int(218 - 16 * t)
            pygame.draw.line(panel, (r, g, b, int(245 * alpha)), (0, row), (sw, row))
        mask = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255), (0, 0, sw, sh), border_radius=12)
        panel.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        screen.blit(panel, (sx, sy))
        pygame.draw.rect(screen, (120, 80, 50, int(255 * alpha)), (sx, sy, sw, sh), 3, border_radius=12)

        # Title with drop shadow
        tier_name = f"Túi đồ ({inventory.bag_capacity} ô)"
        VisualEnhancer.draw_text_with_shadow(
            screen, tier_name, self.font_large, 
            (sx + (sw - self.font_large.size(tier_name)[0]) // 2, sy + 10),
            text_color=(75, 48, 25), shadow_color=(240, 225, 200)
        )

        # Shells display with drop shadow
        gold_str = f"🐚 {inventory.gold:,} Vỏ Sò"
        VisualEnhancer.draw_text_with_shadow(
            screen, gold_str, self.font_small,
            (sx + sw - self.font_small.size(gold_str)[0] - 16, sy + 14),
            text_color=(190, 140, 30), shadow_color=(240, 225, 200)
        )

        # Divider
        pygame.draw.line(screen, (180, 150, 110, int(200 * alpha)),
                        (sx + 16, sy + 38), (sx + sw - 16, sy + 38), 1)

        # --- Hotbar Section ---
        hotbar_label = self.font_small.render("Thanh Hotbar (đang sử dụng)", True, (100, 80, 60))
        screen.blit(hotbar_label, (sx + 16, sy + 44))

        self._hotbar_panel_rects = []
        hb_start_x = sx + (sw - self.COLS * (self.SLOT_SIZE + self.SLOT_GAP)) // 2
        hb_y = sy + 64

        for i in range(inventory.HOTBAR_SLOTS):
            slot_x = hb_start_x + i * (self.SLOT_SIZE + self.SLOT_GAP)
            rect = pygame.Rect(slot_x, hb_y, self.SLOT_SIZE, self.SLOT_SIZE)
            self._hotbar_panel_rects.append(rect)

            is_selected = (i == inventory.selected_index)
            if is_selected:
                glow = pygame.Surface((rect.width + 4, rect.height + 4), pygame.SRCALPHA)
                pygame.draw.rect(glow, (255, 210, 50, 60), (0, 0, rect.width + 4, rect.height + 4), border_radius=8)
                screen.blit(glow, (rect.x - 2, rect.y - 2))

            self._draw_slot(screen, rect, inventory.hotbar[i], is_selected=is_selected)

        # --- Bag Section ---
        bag_label = self.font_small.render(f"Túi đồ ({self._count_items(inventory.bag, inventory.bag_capacity)}/{inventory.bag_capacity})", True, (100, 80, 60))
        bag_section_y = hb_y + self.SLOT_SIZE + 16
        screen.blit(bag_label, (sx + 16, bag_section_y))

        self._bag_slot_rects = []
        bag_start_y = bag_section_y + 22

        for i in range(inventory.MAX_BAG_CAPACITY):
            col = i % self.COLS
            row = i // self.COLS
            slot_x = hb_start_x + col * (self.SLOT_SIZE + self.SLOT_GAP)
            slot_y = bag_start_y + row * (self.SLOT_SIZE + self.SLOT_GAP)
            rect = pygame.Rect(slot_x, slot_y, self.SLOT_SIZE, self.SLOT_SIZE)
            self._bag_slot_rects.append(rect)

            if i < inventory.bag_capacity:
                self._draw_slot(screen, rect, inventory.bag[i])
            else:
                # Locked slot
                pygame.draw.rect(screen, (60, 50, 40, 120), rect, border_radius=5)
                pygame.draw.rect(screen, (80, 65, 50), rect, 1, border_radius=5)
                lock = self.font_tiny.render("🔒", True, (120, 100, 80))
                screen.blit(lock, (rect.centerx - lock.get_width() // 2,
                                  rect.centery - lock.get_height() // 2))

            if i + 1 >= inventory.bag_capacity:
                if row >= bag_rows:
                    break

        # Upgrade button
        upgrade_info = inventory.get_bag_upgrade_info()
        if upgrade_info:
            btn_y = bag_start_y + bag_rows * (self.SLOT_SIZE + self.SLOT_GAP) + 8
            self._upgrade_btn_rect = pygame.Rect(sx + 16, btn_y, sw - 32, 36)
            can_up, _ = inventory.can_upgrade_bag()
            btn_col = (60, 140, 60) if can_up else (100, 90, 80)
            pygame.draw.rect(screen, btn_col, self._upgrade_btn_rect, border_radius=8)
            pygame.draw.rect(screen, (40, 100, 40) if can_up else (70, 60, 50),
                           self._upgrade_btn_rect, 2, border_radius=8)

            mats = ", ".join(f"{v}x {k}" for k, v in upgrade_info["materials"].items())
            btn_text = f"⬆ Nâng cấp: {upgrade_info['name']} — {upgrade_info['gold']:,} 🐚 + {mats}"
            btn_surf = self.font_small.render(btn_text, True, (255, 255, 255))
            screen.blit(btn_surf, (self._upgrade_btn_rect.x + (self._upgrade_btn_rect.width - btn_surf.get_width()) // 2,
                                  self._upgrade_btn_rect.y + 9))
        else:
            self._upgrade_btn_rect = None

    def _draw_storage_panel(self, screen, storage, inventory, x, alpha):
        stor_rows = math.ceil(storage.capacity / self.COLS)
        panel_h = 60 + stor_rows * (self.SLOT_SIZE + self.SLOT_GAP) + 60
        panel_w = 500
        y = max(20, (SCREEN_HEIGHT - panel_h) // 2)

        scale = 0.9 + 0.1 * alpha
        sw = int(panel_w * scale)
        sh = int(panel_h * scale)
        sx = x + (panel_w - sw) // 2
        sy = y + (panel_h - sh) // 2

        # Shadow
        shadow = pygame.Surface((sw + 12, sh + 12), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, int(50 * alpha)), (0, 0, sw + 12, sh + 12), border_radius=14)
        screen.blit(shadow, (sx - 6, sy - 2))

        # Panel
        panel = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for row in range(sh):
            t = row / max(1, sh - 1)
            r = int(240 - 8 * t)
            g = int(235 - 10 * t)
            b = int(225 - 14 * t)
            pygame.draw.line(panel, (r, g, b, int(245 * alpha)), (0, row), (sw, row))
        mask = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255), (0, 0, sw, sh), border_radius=12)
        panel.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        screen.blit(panel, (sx, sy))
        pygame.draw.rect(screen, (100, 75, 50, int(255 * alpha)), (sx, sy, sw, sh), 3, border_radius=12)

        # Title
        title = self.font_large.render(f"Kho đồ ({storage.capacity} ô)", True, (70, 45, 25))
        screen.blit(title, (sx + (sw - title.get_width()) // 2, sy + 10))

        pygame.draw.line(screen, (180, 150, 110, int(200 * alpha)),
                        (sx + 16, sy + 38), (sx + sw - 16, sy + 38), 1)

        # Storage slots
        self._storage_slot_rects = []
        hb_start_x = sx + (sw - self.COLS * (self.SLOT_SIZE + self.SLOT_GAP)) // 2
        slot_start_y = sy + 46

        for i in range(storage.MAX_CAPACITY):
            col = i % self.COLS
            row = i // self.COLS
            slot_x = hb_start_x + col * (self.SLOT_SIZE + self.SLOT_GAP)
            slot_y = slot_start_y + row * (self.SLOT_SIZE + self.SLOT_GAP)
            rect = pygame.Rect(slot_x, slot_y, self.SLOT_SIZE, self.SLOT_SIZE)
            self._storage_slot_rects.append(rect)

            if i < storage.capacity:
                self._draw_slot(screen, rect, storage.slots[i])
            else:
                pygame.draw.rect(screen, (60, 50, 40, 120), rect, border_radius=5)
                pygame.draw.rect(screen, (80, 65, 50), rect, 1, border_radius=5)
                lock = self.font_tiny.render("🔒", True, (120, 100, 80))
                screen.blit(lock, (rect.centerx - lock.get_width() // 2,
                                  rect.centery - lock.get_height() // 2))

            if row >= stor_rows:
                break

        # Upgrade button
        upgrade_info = storage.get_upgrade_info()
        if upgrade_info:
            btn_y = slot_start_y + stor_rows * (self.SLOT_SIZE + self.SLOT_GAP) + 8
            self._storage_upgrade_btn_rect = pygame.Rect(sx + 16, btn_y, sw - 32, 36)
            can_up, _ = storage.can_upgrade(inventory)
            btn_col = (60, 120, 140) if can_up else (100, 90, 80)
            pygame.draw.rect(screen, btn_col, self._storage_upgrade_btn_rect, border_radius=8)
            pygame.draw.rect(screen, (40, 90, 110) if can_up else (70, 60, 50),
                           self._storage_upgrade_btn_rect, 2, border_radius=8)

            mats = ", ".join(f"{v}x {k}" for k, v in upgrade_info["materials"].items())
            btn_text = f"⬆ Nâng cấp: {upgrade_info['name']} — {upgrade_info['gold']:,} 🐚 + {mats}"
            btn_surf = self.font_small.render(btn_text, True, (255, 255, 255))
            screen.blit(btn_surf, (self._storage_upgrade_btn_rect.x + 
                                  (self._storage_upgrade_btn_rect.width - btn_surf.get_width()) // 2,
                                  self._storage_upgrade_btn_rect.y + 9))
        else:
            self._storage_upgrade_btn_rect = None

    def _draw_slot(self, screen, rect, item, is_selected=False):
        """Draw a single inventory slot with cozy 3D inset bevel."""
        if is_selected:
            bg = (255, 250, 230, 245)
            border = (255, 200, 40)
            bw = 2
        else:
            bg = (242, 232, 210, 225)
            border = (135, 100, 68)
            bw = 1

        slot_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(slot_surf, bg, (0, 0, rect.width, rect.height), border_radius=6)
        # 3D Inset shading: top/left inner shadow, bottom/right highlight
        pygame.draw.line(slot_surf, (150, 120, 85, 110), (2, 2), (rect.width - 3, 2))
        pygame.draw.line(slot_surf, (150, 120, 85, 110), (2, 2), (2, rect.height - 3))
        pygame.draw.line(slot_surf, (255, 255, 245, 130), (2, rect.height - 2), (rect.width - 2, rect.height - 2))
        pygame.draw.line(slot_surf, (255, 255, 245, 130), (rect.width - 2, 2), (rect.width - 2, rect.height - 2))

        screen.blit(slot_surf, rect.topleft)
        pygame.draw.rect(screen, border, rect, bw, border_radius=6)

        if item:
            self._draw_item_in_slot(screen, item, rect)

    def _draw_item_in_slot(self, screen, item, rect):
        """Draw item icon and quantity in slot."""
        itype = item.get("type")
        iid = item.get("id")
        tex = self._get_item_texture(itype, iid)

        if tex:
            ix = rect.x + (rect.width - tex.get_width()) // 2
            iy = rect.y + (rect.height - tex.get_height()) // 2
            screen.blit(tex, (ix, iy))

        # Water meter
        if itype == "tool" and iid == TOOL_WATER_CAN:
            water = item.get("water", 0)
            max_w = item.get("max_water", 40)
            bar_w = rect.width - 10
            fill_w = int((water / max_w) * bar_w)
            bx = rect.x + 5
            by = rect.y + rect.height - 7
            pygame.draw.rect(screen, (30, 50, 80, 180), (bx, by, bar_w, 4), border_radius=1)
            if fill_w > 0:
                pygame.draw.rect(screen, (90, 185, 245), (bx, by, fill_w, 4), border_radius=1)

        # Quantity badge
        qty = item.get("qty", 1)
        if itype != "tool" and qty > 1:
            q_txt = self.font_tiny.render(str(qty), True, (255, 255, 255))
            badge_w = max(14, q_txt.get_width() + 6)
            badge_x = rect.right - badge_w - 2
            badge_y = rect.bottom - 14
            badge = pygame.Surface((badge_w, 13), pygame.SRCALPHA)
            pygame.draw.rect(badge, (40, 30, 20, 200), (0, 0, badge_w, 13), border_radius=4)
            screen.blit(badge, (badge_x, badge_y))
            screen.blit(q_txt, (badge_x + (badge_w - q_txt.get_width()) // 2, badge_y + 1))

    def _draw_item_at(self, screen, item, x, y):
        """Draw item icon at arbitrary position (for drag)."""
        itype = item.get("type")
        iid = item.get("id")
        tex = self._get_item_texture(itype, iid)

        # Semi-transparent background
        bg = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.rect(bg, (255, 240, 200, 180), (0, 0, 40, 40), border_radius=6)
        pygame.draw.rect(bg, (200, 160, 80, 220), (0, 0, 40, 40), 2, border_radius=6)
        screen.blit(bg, (x, y))

        if tex:
            screen.blit(tex, (x + (40 - tex.get_width()) // 2, y + (40 - tex.get_height()) // 2))

        name_txt = self.font_tiny.render(item.get("name", ""), True, (255, 255, 230))
        name_bg = pygame.Surface((name_txt.get_width() + 8, 14), pygame.SRCALPHA)
        pygame.draw.rect(name_bg, (20, 15, 10, 200), (0, 0, name_bg.get_width(), 14), border_radius=3)
        screen.blit(name_bg, (x, y + 42))
        screen.blit(name_txt, (x + 4, y + 43))

    def _get_item_texture(self, itype, iid):
        if itype == "tool":
            return self.assets.textures.get(f"tool_{iid}")
        elif itype == "seed":
            return self.assets.textures.get(f"seed_{iid}")
        elif itype == "material":
            return self.assets.textures.get(f"mat_{iid}")
        elif itype == "crop":
            return self.assets.textures.get(f"produce_{iid}")
        elif itype == "fish":
            return self.assets.textures.get(f"fish_{iid}")
        elif itype == "animal_product":
            return self.assets.textures.get(f"prod_{iid}")
        return None

    def _count_items(self, slots, capacity):
        return sum(1 for i in range(capacity) if slots[i] is not None)
