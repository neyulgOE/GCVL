"""
NPC Shop and Dynamic Haggling UI Panel for Green Valley Tales.
Full-screen interactive marketplace modal featuring:
- NPC Portrait, Role, and dynamic Dialogue Speech Bubble
- Real-time Patience / Mood Gauge (100% -> 0%)
- Tabbed interface: [MUA HÀNG] (Buy from NPC) vs [BÁN HÀNG] (Sell to NPC)
- Instant Deal vs 3 Tiers of Haggling (-10%/+10%, -20%/+20%, -35%/+35%)
- Visual feedback, Vietnamese flavor quotes, and gold transactions
"""

import pygame
import math
import random
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.economy.npc_shop import HagglingLevel, TownShopManager

class NPCShopPanel:
    def __init__(self, asset_mgr):
        self.assets = asset_mgr
        self.shop_mgr = TownShopManager()
        self.active_npc = None
        self.is_wandering_merchant = False
        self.wandering_ref = None

        # Modal animation
        self.show = False
        self._alpha = 0.0

        # Tabs: "buy" or "sell"
        self.active_tab = "buy"
        self.selected_item_idx = 0
        self.dialogue_text = ""
        self.dialogue_color = (60, 45, 30)

        # Catalogues
        self.buy_items = []
        self.sell_items = []

        # Geometry
        self.w = 760
        self.h = 540
        self.x = (SCREEN_WIDTH - self.w) // 2
        self.y = (SCREEN_HEIGHT - self.h) // 2

        # Button rects
        self.tab_buy_rect = pygame.Rect(self.x + 28, self.y + 112, 130, 32)
        self.tab_sell_rect = pygame.Rect(self.x + 166, self.y + 112, 130, 32)
        self.close_btn_rect = pygame.Rect(self.x + self.w - 42, self.y + 12, 30, 30)

        self.btn_instant_rect = pygame.Rect(self.x + 28, self.y + self.h - 58, 160, 40)
        self.btn_haggle_10_rect = pygame.Rect(self.x + 196, self.y + self.h - 58, 165, 40)
        self.btn_haggle_20_rect = pygame.Rect(self.x + 369, self.y + self.h - 58, 165, 40)
        self.btn_haggle_35_rect = pygame.Rect(self.x + 542, self.y + self.h - 58, 185, 40)

    def is_open(self):
        return self.show or self._alpha > 0.01

    def open_shop(self, npc, current_season_id, inventory, is_wandering=False, wandering_ref=None):
        self.active_npc = npc
        self.is_wandering_merchant = is_wandering
        self.wandering_ref = wandering_ref
        self.active_tab = "buy"
        self.selected_item_idx = 0
        self.show = True

        if is_wandering and wandering_ref:
            self.buy_items = wandering_ref.get_rare_stock()
            self.dialogue_text = random.choice(wandering_ref.greetings)
        else:
            self.buy_items = self.shop_mgr.get_npc_stock(npc.id, current_season_id)
            self.dialogue_text = npc.greeting

        self.refresh_sell_items(inventory)

    def refresh_sell_items(self, inventory):
        if self.is_wandering_merchant and self.wandering_ref:
            # Wandering merchant buys rare items and excavated relics at 1.7x premium
            sellable = []
            all_slots = [s for s in inventory.bag[:inventory.bag_capacity] if s] + [s for s in inventory.hotbar if s and s.get("type") != "tool"]
            for slot in all_slots:
                premium_price = self.wandering_ref.get_premium_buy_rate(slot)
                item_copy = dict(slot)
                item_copy["unit_price"] = premium_price
                sellable.append(item_copy)
            self.sell_items = sellable
        elif self.active_npc:
            self.sell_items = self.shop_mgr.get_player_sellable_items(inventory, self.active_npc.id)

    def close(self):
        self.show = False

    def update(self, dt):
        target = 1.0 if self.show else 0.0
        diff = target - self._alpha
        self._alpha += diff * min(1.0, dt * 9.0)
        if abs(diff) < 0.01:
            self._alpha = target

    # -------------------------------------------------------------
    # EVENT HANDLING
    # -------------------------------------------------------------
    def handle_mouse_down(self, pos, button, inventory, time_sys, dialog_mgr):
        if not self.show or self._alpha < 0.8:
            return False

        if button != 1:
            return False

        # Close button
        if self.close_btn_rect.collidepoint(pos):
            self.close()
            return True

        # Tab switches
        if self.tab_buy_rect.collidepoint(pos):
            self.active_tab = "buy"
            self.selected_item_idx = 0
            self.assets.play_sound("clink")
            return True

        if self.tab_sell_rect.collidepoint(pos):
            self.active_tab = "sell"
            self.selected_item_idx = 0
            self.refresh_sell_items(inventory)
            self.assets.play_sound("clink")
            return True

        # Click on Item List
        list_y = self.y + 154
        current_list = self.buy_items if self.active_tab == "buy" else self.sell_items
        for i in range(len(current_list)):
            row_rect = pygame.Rect(self.x + 28, list_y + i * 52, self.w - 56, 46)
            if row_rect.collidepoint(pos):
                self.selected_item_idx = i
                self.assets.play_sound("clink")
                return True

        # Action Buttons
        if not current_list or self.selected_item_idx >= len(current_list):
            return True

        selected_item = current_list[self.selected_item_idx]

        # 1. Instant Deal (Giá chuẩn)
        if self.btn_instant_rect.collidepoint(pos):
            self._execute_instant_deal(selected_item, inventory, dialog_mgr)
            return True

        # 2. Haggle -10% / +10%
        if self.btn_haggle_10_rect.collidepoint(pos):
            self._execute_haggle(selected_item, HagglingLevel.CAUTIOUS, inventory, dialog_mgr)
            return True

        # 3. Haggle -20% / +20%
        if self.btn_haggle_20_rect.collidepoint(pos):
            self._execute_haggle(selected_item, HagglingLevel.CLEVER, inventory, dialog_mgr)
            return True

        # 4. Haggle -35% / +35%
        if self.btn_haggle_35_rect.collidepoint(pos):
            self._execute_haggle(selected_item, HagglingLevel.AGGRESSIVE, inventory, dialog_mgr)
            return True

        return True

    def _execute_instant_deal(self, item, inventory, dialog_mgr):
        if self.active_tab == "buy":
            price = item["price"]
            if inventory.gold < price:
                self.dialogue_text = "Cậu không đủ tiền vàng rồi! Hãy chăm chỉ kiếm thêm nhé."
                dialog_mgr.add_toast("Không đủ tiền vàng (G)!")
                return

            # Buy execution
            item_dict = {
                "id": item["id"],
                "type": item.get("type", item.get("category", "material")),
                "name": item["name"],
                "price": item.get("price", 10),
                "qty": item.get("qty", 1)
            }
            if inventory.add_item(item_dict, item_dict["qty"]):
                inventory.gold -= price
                self.assets.play_sound("coin")
                self.dialogue_text = "Cảm ơn bạn đã ủng hộ tiệm! Hàng loại một đấy nhé."
                dialog_mgr.add_toast(f"Đã mua {item['name']} (-{price}G)!")
            else:
                dialog_mgr.add_toast("Túi đồ đã đầy!")
        else:
            # Sell execution
            unit_price = item.get("unit_price", item.get("price", 10))
            qty = item.get("qty", 1)
            total = unit_price * qty
            if inventory.remove_item_by_id(item["id"], qty):
                inventory.gold += total
                self.assets.play_sound("coin")
                self.dialogue_text = "Nông sản/khoáng thạch chất lượng lắm! Tiền của bạn đây."
                dialog_mgr.add_toast(f"Đã bán {qty}x {item['name']} (+{total}G)!")
                self.refresh_sell_items(inventory)
                if self.selected_item_idx >= len(self.sell_items):
                    self.selected_item_idx = max(0, len(self.sell_items) - 1)

    def _execute_haggle(self, item, level, inventory, dialog_mgr):
        is_buying = (self.active_tab == "buy")
        
        if self.is_wandering_merchant:
            # Wandering merchant has fixed exotic prices
            self.dialogue_text = "Bảo vật quý từ viễn phương, ta không thể bớt được nữa đâu bạn trẻ!"
            dialog_mgr.add_toast("Thương nhân du mục không chấp nhận trả giá!")
            return

        success, negotiated_price, reply = self.shop_mgr.attempt_bargain(
            self.active_npc, item, is_buying, level
        )
        self.dialogue_text = reply

        if success:
            self.assets.play_sound("success")
            if is_buying:
                if inventory.gold < negotiated_price:
                    self.dialogue_text = "Đã đồng ý bớt giá mà cậu lại không đủ tiền à?"
                    dialog_mgr.add_toast("Không đủ tiền vàng!")
                    return
                item_dict = {
                    "id": item["id"],
                    "type": item.get("type", item.get("category", "material")),
                    "name": item["name"],
                    "price": item.get("price", 10),
                    "qty": item.get("qty", 1)
                }
                if inventory.add_item(item_dict, item_dict["qty"]):
                    inventory.gold -= negotiated_price
                    dialog_mgr.add_toast(f"Mặc cả thành công! Mua {item['name']} giá hời {negotiated_price}G!")
                else:
                    dialog_mgr.add_toast("Túi đồ đã đầy!")
            else:
                qty = item.get("qty", 1)
                if inventory.remove_item_by_id(item["id"], qty):
                    inventory.gold += negotiated_price
                    dialog_mgr.add_toast(f"Thương lượng giá cao thành công! Thu về {negotiated_price}G!")
                    self.refresh_sell_items(inventory)
                    if self.selected_item_idx >= len(self.sell_items):
                        self.selected_item_idx = max(0, len(self.sell_items) - 1)
        else:
            self.assets.play_sound("clink")
            dialog_mgr.add_toast(f"Trả giá thất bại! Kiên nhẫn của {self.active_npc.name} còn {self.active_npc.patience}%")

    # -------------------------------------------------------------
    # DRAW LOOP
    # -------------------------------------------------------------
    def draw(self, screen, inventory):
        if self._alpha < 0.01:
            return

        alpha = self._alpha
        # Backdrop
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, int(150 * alpha)))
        screen.blit(dim, (0, 0))

        # Panel body
        scale = 0.94 + 0.06 * alpha
        sw = int(self.w * scale)
        sh = int(self.h * scale)
        sx = self.x + (self.w - sw) // 2
        sy = self.y + (self.h - sh) // 2

        # Shadow
        shadow = pygame.Surface((sw + 20, sh + 20), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, int(70 * alpha)), (0, 0, sw + 20, sh + 20), border_radius=16)
        screen.blit(shadow, (sx - 10, sy - 5))

        # Parchment panel
        panel = pygame.Surface((sw, sh), pygame.SRCALPHA)
        bg_col = (242, 235, 218) if not self.is_wandering_merchant else (238, 226, 238)
        pygame.draw.rect(panel, (*bg_col, int(250 * alpha)), (0, 0, sw, sh), border_radius=14)
        screen.blit(panel, (sx, sy))

        border_col = (115, 80, 50) if not self.is_wandering_merchant else (135, 55, 145)
        pygame.draw.rect(screen, (*border_col, int(255 * alpha)), (sx, sy, sw, sh), 3, border_radius=14)

        # Header: NPC Avatar & Dialogue
        self._draw_header(screen, sx, sy, sw)

        # Tabs
        self._draw_tabs(screen)

        # Content List
        self._draw_item_list(screen, inventory)

        # Bottom Haggling Controls
        self._draw_bottom_bar(screen, inventory)

    def _draw_header(self, screen, sx, sy, sw):
        # Avatar box (64x64)
        av_rect = pygame.Rect(sx + 24, sy + 18, 70, 70)
        pygame.draw.rect(screen, (220, 205, 185), av_rect, border_radius=8)
        pygame.draw.rect(screen, (130, 95, 65), av_rect, 2, border_radius=8)

        if self.is_wandering_merchant:
            tex = self.assets.textures.get("wandering_merchant")
            if tex:
                screen.blit(tex, (av_rect.x + 3, av_rect.y + 3))
            name_txt = "Lão Hạc (Thương Nhân Du Mục Thần Bí)"
            role_txt = "Bán bảo vật độc bản & Mua khoáng sản/cổ vật quý +70% giá!"
            patience_val = 100
        else:
            tex = self.assets.textures.get(f"npc_{self.active_npc.id}")
            if tex:
                screen.blit(tex, (av_rect.x + 3, av_rect.y + 3))
            name_txt = f"{self.active_npc.name} - {self.active_npc.role}"
            role_txt = f"Độ kiên nhẫn thương lượng: {self.active_npc.patience}%"
            patience_val = self.active_npc.patience

        # Name & Title
        title_surf = self.assets.fonts["large"].render(name_txt, True, (65, 40, 20))
        screen.blit(title_surf, (sx + 104, sy + 16))

        # Patience bar
        pbar_rect = pygame.Rect(sx + 104, sy + 40, 200, 10)
        pygame.draw.rect(screen, (180, 170, 160), pbar_rect, border_radius=5)
        p_w = int(200 * (patience_val / 100.0))
        p_col = (75, 190, 80) if patience_val > 50 else ((235, 175, 40) if patience_val > 25 else (225, 60, 50))
        if p_w > 0:
            pygame.draw.rect(screen, p_col, (pbar_rect.x, pbar_rect.y, p_w, 10), border_radius=5)
        pygame.draw.rect(screen, (90, 75, 60), pbar_rect, 1, border_radius=5)

        # Dialogue speech bubble
        bubble_rect = pygame.Rect(sx + 104, sy + 56, sw - 140, 36)
        pygame.draw.rect(screen, (255, 252, 245), bubble_rect, border_radius=6)
        pygame.draw.rect(screen, (160, 130, 95), bubble_rect, 1, border_radius=6)

        dial_surf = self.assets.fonts["small"].render(f'"{self.dialogue_text}"', True, (60, 45, 30))
        screen.blit(dial_surf, (bubble_rect.x + 10, bubble_rect.y + 9))

        # Close [X] Button
        pygame.draw.rect(screen, (220, 70, 70), self.close_btn_rect, border_radius=6)
        pygame.draw.rect(screen, (140, 30, 30), self.close_btn_rect, 1, border_radius=6)
        x_lbl = self.assets.fonts["normal"].render("X", True, (255, 255, 255))
        screen.blit(x_lbl, (self.close_btn_rect.x + 9, self.close_btn_rect.y + 6))

    def _draw_tabs(self, screen):
        # Tab Buy
        is_buy = (self.active_tab == "buy")
        b_col = (115, 80, 50) if is_buy else (210, 195, 175)
        txt_b = (255, 255, 255) if is_buy else (90, 65, 40)
        pygame.draw.rect(screen, b_col, self.tab_buy_rect, border_radius=6)
        lbl1 = self.assets.fonts["normal"].render("MUA HÀNG", True, txt_b)
        screen.blit(lbl1, (self.tab_buy_rect.x + (self.tab_buy_rect.w - lbl1.get_width()) // 2, self.tab_buy_rect.y + 6))

        # Tab Sell
        is_sell = (self.active_tab == "sell")
        s_col = (115, 80, 50) if is_sell else (210, 195, 175)
        txt_s = (255, 255, 255) if is_sell else (90, 65, 40)
        pygame.draw.rect(screen, s_col, self.tab_sell_rect, border_radius=6)
        lbl2 = self.assets.fonts["normal"].render("BÁN HÀNG", True, txt_s)
        screen.blit(lbl2, (self.tab_sell_rect.x + (self.tab_sell_rect.w - lbl2.get_width()) // 2, self.tab_sell_rect.y + 6))

    def _draw_item_list(self, screen, inventory):
        current_list = self.buy_items if self.active_tab == "buy" else self.sell_items
        list_y = self.y + 154

        if not current_list:
            msg = "Hiện tại không có mặt hàng phù hợp để giao dịch."
            lbl = self.assets.fonts["normal"].render(msg, True, (130, 110, 90))
            screen.blit(lbl, (self.x + 40, list_y + 40))
            return

        for i, item in enumerate(current_list[:6]):
            row_y = list_y + i * 52
            row_rect = pygame.Rect(self.x + 28, row_y, self.w - 56, 46)

            is_sel = (i == self.selected_item_idx)
            bg_col = (255, 245, 215) if is_sel else (235, 225, 205)
            pygame.draw.rect(screen, bg_col, row_rect, border_radius=6)
            bdr_col = (215, 140, 40) if is_sel else (185, 165, 140)
            pygame.draw.rect(screen, bdr_col, row_rect, 2 if is_sel else 1, border_radius=6)

            # Icon
            icon_key = f"produce_{item['id']}" if item.get("type") == "produce" else (
                f"seed_{item['id']}" if item.get("type") == "seed" else (
                    f"rare_{item['id']}" if item.get("is_rare") or "rare" in item.get("type", "") else (
                        f"mat_{item['id']}" if "mat" in item.get("type", "") or item['id'] in ["wood", "stone", "copper_ore", "iron_ore", "coal"] else (
                            f"fish_{item['id']}" if item.get("type") == "fish" else (
                                f"item_{item['id']}" if f"item_{item['id']}" in self.assets.textures else "mat_wood"
                            )
                        )
                    )
                )
            )
            tex = self.assets.textures.get(icon_key, self.assets.textures.get(f"seed_{item['id']}", self.assets.textures.get("mat_wood")))
            if tex:
                screen.blit(tex, (row_rect.x + 8, row_rect.y + 7))

            # Name & Desc
            name_txt = item.get("name", "Vật phẩm")
            name_surf = self.assets.fonts["normal"].render(name_txt, True, (60, 40, 20))
            screen.blit(name_surf, (row_rect.x + 48, row_rect.y + 5))

            desc_txt = item.get("desc", f"Số lượng trong túi: {item.get('qty', 1)}")
            desc_surf = self.assets.fonts["tiny"].render(desc_txt, True, (110, 85, 60))
            screen.blit(desc_surf, (row_rect.x + 48, row_rect.y + 26))

            # Price Tag
            price = item.get("unit_price", item.get("price", 10))
            total_price = price if self.active_tab == "buy" else price * item.get("qty", 1)
            pr_txt = f"{total_price} 🐚"
            pr_surf = self.assets.fonts["large"].render(pr_txt, True, (190, 110, 20))
            screen.blit(pr_surf, (row_rect.right - pr_surf.get_width() - 16, row_rect.y + 12))

    def _draw_bottom_bar(self, screen, inventory):
        current_list = self.buy_items if self.active_tab == "buy" else self.sell_items
        patience = self.active_npc.patience if self.active_npc else 100
        can_haggle = (patience > 0) and not self.is_wandering_merchant

        # Button 1: Instant Deal
        pygame.draw.rect(screen, (75, 140, 65), self.btn_instant_rect, border_radius=6)
        pygame.draw.rect(screen, (45, 95, 40), self.btn_instant_rect, 2, border_radius=6)
        lbl1 = self.assets.fonts["normal"].render("Giao Dịch Nhanh", True, (255, 255, 255))
        screen.blit(lbl1, (self.btn_instant_rect.x + (self.btn_instant_rect.w - lbl1.get_width()) // 2, self.btn_instant_rect.y + 10))

        # Button 2: Haggle 10%
        col2 = (195, 145, 45) if can_haggle else (160, 150, 140)
        pygame.draw.rect(screen, col2, self.btn_haggle_10_rect, border_radius=6)
        pygame.draw.rect(screen, (120, 85, 20), self.btn_haggle_10_rect, 2, border_radius=6)
        lbl2 = self.assets.fonts["small"].render("Trả Giá -10% (82%)", True, (255, 255, 255) if can_haggle else (90, 80, 70))
        screen.blit(lbl2, (self.btn_haggle_10_rect.x + (self.btn_haggle_10_rect.w - lbl2.get_width()) // 2, self.btn_haggle_10_rect.y + 11))

        # Button 3: Haggle 20%
        col3 = (195, 110, 45) if can_haggle else (160, 150, 140)
        pygame.draw.rect(screen, col3, self.btn_haggle_20_rect, border_radius=6)
        pygame.draw.rect(screen, (125, 60, 20), self.btn_haggle_20_rect, 2, border_radius=6)
        lbl3 = self.assets.fonts["small"].render("Trả Giá -20% (58%)", True, (255, 255, 255) if can_haggle else (90, 80, 70))
        screen.blit(lbl3, (self.btn_haggle_20_rect.x + (self.btn_haggle_20_rect.w - lbl3.get_width()) // 2, self.btn_haggle_20_rect.y + 11))

        # Button 4: Haggle 35%
        col4 = (195, 60, 50) if can_haggle else (160, 150, 140)
        pygame.draw.rect(screen, col4, self.btn_haggle_35_rect, border_radius=6)
        pygame.draw.rect(screen, (130, 30, 25), self.btn_haggle_35_rect, 2, border_radius=6)
        lbl4 = self.assets.fonts["small"].render("Ép Giá Gắt -35% (28%)", True, (255, 255, 255) if can_haggle else (90, 80, 70))
        screen.blit(lbl4, (self.btn_haggle_35_rect.x + (self.btn_haggle_35_rect.w - lbl4.get_width()) // 2, self.btn_haggle_35_rect.y + 11))
