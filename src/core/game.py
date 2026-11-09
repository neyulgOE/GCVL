"""
Main Game Coordinator for Green Valley Tales.
Integrates World, Multi-Zone Architecture (Farm Zone & Town Zone), Fast Travel Teleportation,
NPC Haggling & Marketplace, Wandering Rare Merchant, Entities, Inventory Panel, Storage,
Minimap, and Full Interactive Systems.
"""

import pygame
import sys
import math
import random
from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TITLE, FPS, TILE_SIZE,
    TOOL_HOE, TOOL_WATER_CAN, TOOL_AXE, TOOL_PICKAXE, TOOL_SCYTHE, TOOL_FISHING_ROD
)
from src.core.assets import AssetManager
from src.core.camera import Camera
from src.world.time_system import TimeSystem
from src.world.weather_system import WeatherSystem
from src.world.map_manager import MapManager, ZONE_FARM, ZONE_TOWN
from src.world.particle_system import ParticleSystem
from src.core.animals_manager import AnimalsManager
from src.fishing.fishing_system import FishingSystem
from src.entities.player import Player
from src.economy.inventory import Inventory, StorageChest
from src.economy.shipping_bin import ShippingBin
from src.economy.shop import Shop
from src.economy.wandering_merchant import WanderingMerchant
from src.ui.hud import HUD
from src.ui.dialog import DialogManager
from src.ui.inventory_panel import InventoryPanel
from src.ui.minimap import MinimapSystem
from src.ui.npc_shop_panel import NPCShopPanel
from src.core.save_system import SaveSystem
from src.core.visual_enhancer import VisualEnhancer
from src.crafting.crafting_system import CraftingSystem
from src.ui.crafting_panel import CraftingPanel
from src.world.primitive_structures import PrimitiveStructures
from src.world.era_quest_system import EraQuestSystem
from src.world.tribe_manager import TribeSettlementManager
from src.world.fog_of_war import FogOfWar
from src.world.wildlife_manager import WildlifeManager
from src.ui.rts_controller import RTSController

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_time = 0.0

        # Core Assets & Subsystems
        self.assets = AssetManager.get()
        self.camera = Camera()
        self.time_sys = TimeSystem()
        self.weather_sys = WeatherSystem()
        self.map_mgr = MapManager()
        self.particle_sys = ParticleSystem()
        self.animals_mgr = AnimalsManager(self.map_mgr.barn_col, self.map_mgr.barn_row)
        self.fishing_sys = FishingSystem()
        self.inventory = Inventory()
        self.storage = StorageChest()
        self.shipping_bin = ShippingBin()
        self.shop = Shop()
        self.wandering_merchant = WanderingMerchant()
        
        # Player (Spawns at Central Tribal Campfire Hearth in 80x80 Prehistoric Continent)
        spawn_x = 40.0 * 64.0
        spawn_y = 39.0 * 64.0
        self.player = Player(spawn_x, spawn_y)
        self.camera.snap_to(self.player.rect)

        # UI Managers
        self.hud = HUD(self.assets)
        self.dialog_mgr = DialogManager(self.assets)
        self.inv_panel = InventoryPanel(self.assets)
        self.minimap = MinimapSystem()
        self.npc_shop_panel = NPCShopPanel(self.assets)

        # Stone Age Crafting, Buildings & Era Progression
        self.crafting_sys = CraftingSystem()
        self.crafting_panel = CraftingPanel(self.assets)
        self.primitive_structures = PrimitiveStructures()
        self.era_quest_sys = EraQuestSystem()

        # Tribal Population, Wildlife & RTS Controller
        self.tribe_mgr = TribeSettlementManager(self.primitive_structures)
        self.fog_of_war = FogOfWar()
        self.wildlife_mgr = WildlifeManager()
        self.rts_controller = RTSController(self.tribe_mgr, self.camera, self.wildlife_mgr)

        # Storage chest world position (Tribal Cache at Central Camp)
        self.storage_pos = (43, 38)

        # Check wandering merchant on start
        if self.wandering_merchant.check_daily_appearance(self.time_sys.day, self.time_sys.season_id, self.time_sys.year):
            self.dialog_mgr.add_toast("🌟 Thương nhân du mục huyền bí Lão Hạc đã ghé thăm bộ lạc hôm nay!")

        # Load existing save file if present
        if SaveSystem.save_exists():
            if SaveSystem.load_game(self.time_sys, self.weather_sys, self.player, 
                                   self.inventory, self.map_mgr, self.animals_mgr, 
                                   self.shipping_bin, self.storage,
                                   self.crafting_sys, self.primitive_structures, self.era_quest_sys):
                self.camera.snap_to(self.player.rect)
                self.dialog_mgr.add_toast("Đã nạp dữ liệu bộ lạc tiền sử thành công!")

        # Initial welcome toast
        self.dialog_mgr.add_toast("Chào mừng đến Thời Đồ Đá! [C]: Chế tác & Xây dựng | [Q]: Nhiệm vụ | [H]: Hướng dẫn")

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.render()
        pygame.quit()
        sys.exit()

    # -------------------------------------------------------------
    # EVENT HANDLING
    # -------------------------------------------------------------
    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        world_x, world_y = self.camera.screen_to_world(mouse_pos)
        target_col = int(world_x // TILE_SIZE)
        target_row = int(world_y // TILE_SIZE)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            # --- Crafting & Building Panel Mouse Handling ---
            if self.crafting_panel.is_open:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    consumed = self.crafting_panel.handle_mouse_down(
                        event.pos, event.button, self.crafting_sys, self.inventory,
                        self.primitive_structures, self.dialog_mgr
                    )
                    if consumed:
                        continue

            # --- NPC Shop & Haggling Modal Mouse Handling ---
            if self.npc_shop_panel.is_open():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    consumed = self.npc_shop_panel.handle_mouse_down(
                        event.pos, event.button, self.inventory, self.time_sys, self.dialog_mgr
                    )
                    if consumed:
                        continue

            # --- Inventory Panel Mouse Handling ---
            if self.inv_panel.is_open():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    storage_ref = self.storage if self.inv_panel.show_storage else None
                    consumed = self.inv_panel.handle_mouse_down(event.pos, event.button, self.inventory, storage_ref)
                    if consumed:
                        continue
                elif event.type == pygame.MOUSEBUTTONUP:
                    storage_ref = self.storage if self.inv_panel.show_storage else None
                    consumed = self.inv_panel.handle_mouse_up(event.pos, event.button, self.inventory, storage_ref)
                    if consumed:
                        continue
                elif event.type == pygame.MOUSEMOTION:
                    self.inv_panel.handle_mouse_move(event.pos)
                    continue

            # --- Full Map View Mouse Handling & Fast Travel ---
            if self.minimap.show_full_map and event.type == pygame.MOUSEBUTTONDOWN:
                teleport_action = self.minimap.handle_mouse_down(event.pos, event.button, self.map_mgr)
                if teleport_action == "TELEPORT_TOWN":
                    self.execute_teleport(ZONE_TOWN)
                    continue
                elif teleport_action == "TELEPORT_FARM":
                    self.execute_teleport(ZONE_FARM)
                    continue

            # Mouse wheel switches active hotbar slot
            if event.type == pygame.MOUSEWHEEL:
                if not self.inv_panel.is_open() and not self.npc_shop_panel.is_open() and not self.crafting_panel.is_open:
                    new_idx = (self.inventory.selected_index - event.y) % 8
                    self.inventory.set_active_slot(new_idx)

            # Keyboard Input
            if event.type == pygame.KEYDOWN:
                # Toggle Crafting Panel (C)
                if event.key == pygame.K_c:
                    if not self.npc_shop_panel.is_open() and not self.inv_panel.is_open():
                        self.crafting_panel.toggle()
                    continue

                # Toggle Quest Tracker (Q)
                if event.key == pygame.K_q:
                    self.era_quest_sys.show_tracker = not self.era_quest_sys.show_tracker
                    state = "mở" if self.era_quest_sys.show_tracker else "thu gọn"
                    self.dialog_mgr.add_toast(f"Đã {state} bảng theo dõi Mục Tiêu Kỷ Nguyên.")
                    continue

                # Toggle Inventory Panel (Tab)
                if event.key == pygame.K_TAB:
                    if not self.npc_shop_panel.is_open() and not self.crafting_panel.is_open:
                        self.inv_panel.toggle_bag()
                    continue

                # Toggle Full Map (M)
                if event.key == pygame.K_m:
                    if not self.inv_panel.is_open() and not self.npc_shop_panel.is_open() and not self.crafting_panel.is_open:
                        self.minimap.viewing_zone = self.map_mgr.current_zone
                        self.minimap.toggle_full_map()
                    continue

                # Toggle Help Guide (F1)
                if event.key == pygame.K_F1:
                    if not self.inv_panel.is_open() and not self.minimap.show_full_map and not self.npc_shop_panel.is_open() and not self.crafting_panel.is_open:
                        self.dialog_mgr.show_help = not self.dialog_mgr.show_help
                    continue

                # RTS Hotkeys ([,] for idle villager, [H] for camp center)
                if not self.inv_panel.is_open() and not self.minimap.show_full_map and not self.npc_shop_panel.is_open() and not self.crafting_panel.is_open:
                    if self.rts_controller.handle_key_down(event, self.player):
                        continue

                # Close any modal with ESC
                if event.key == pygame.K_ESCAPE:
                    if self.crafting_panel.is_open:
                        self.crafting_panel.close()
                    elif self.npc_shop_panel.is_open():
                        self.npc_shop_panel.close()
                    elif self.inv_panel.is_open():
                        self.inv_panel.close_all()
                    elif self.minimap.show_full_map:
                        self.minimap.show_full_map = False
                    elif self.dialog_mgr.show_help:
                        self.dialog_mgr.show_help = False
                    elif self.dialog_mgr.show_shop:
                        self.dialog_mgr.show_shop = False
                    elif self.dialog_mgr.show_sleep_confirm:
                        self.dialog_mgr.show_sleep_confirm = False
                    elif self.fishing_sys.state != FishingSystem.IDLE:
                        self.fishing_sys.cancel()
                    continue

                # Block gameplay input when panels are open
                if self.inv_panel.is_open() or self.minimap.show_full_map or self.npc_shop_panel.is_open() or self.crafting_panel.is_open:
                    continue

                # Modal: Summary Report Close
                if self.dialog_mgr.show_summary_report:
                    if event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                        self.dialog_mgr.show_summary_report = False
                    continue

                # Modal: Sleep Confirm
                if self.dialog_mgr.show_sleep_confirm:
                    if event.key in [pygame.K_y, pygame.K_SPACE, pygame.K_RETURN]:
                        self.dialog_mgr.show_sleep_confirm = False
                        self.execute_sleep(pass_out=False)
                    elif event.key in [pygame.K_n, pygame.K_ESCAPE]:
                        self.dialog_mgr.show_sleep_confirm = False
                    continue

                # Hotbar Number Keys (1..8)
                if pygame.K_1 <= event.key <= pygame.K_8:
                    slot_idx = event.key - pygame.K_1
                    self.inventory.set_active_slot(slot_idx)

                # Keyboard Primary Action (SPACE)
                if event.key == pygame.K_SPACE:
                    if self.player.is_in_reach(target_col, target_row):
                        self.player.face_towards(world_x, world_y)
                        self.handle_primary_action(target_col, target_row)
                    else:
                        fc, fr = self.player.forward_tile
                        self.handle_primary_action(fc, fr)

                # Keyboard Secondary Action (E key)
                if event.key == pygame.K_e:
                    if self.player.is_in_reach(target_col, target_row):
                        self.player.face_towards(world_x, world_y)
                        self.handle_secondary_action(target_col, target_row)
                    else:
                        fc, fr = self.player.forward_tile
                        self.handle_secondary_action(fc, fr)

            # Mouse Motion (RTS drag tracking)
            if event.type == pygame.MOUSEMOTION:
                if not self.inv_panel.is_open() and not self.minimap.show_full_map and not self.npc_shop_panel.is_open():
                    self.rts_controller.handle_mouse_motion(event)

            # Mouse Button Up (RTS marquee release / click)
            if event.type == pygame.MOUSEBUTTONUP:
                if not self.inv_panel.is_open() and not self.minimap.show_full_map and not self.npc_shop_panel.is_open():
                    if self.rts_controller.handle_mouse_up(event):
                        continue

            # Mouse Button Down (gameplay)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.inv_panel.is_open() or self.minimap.show_full_map or self.npc_shop_panel.is_open() or self.crafting_panel.is_open:
                    continue

                # Quick HUD shortcuts: Crafting button and Quest tracker
                if self.hud.craft_btn_rect.collidepoint(event.pos):
                    self.crafting_panel.toggle()
                    continue

                if self.hud.quest_tracker_rect.collidepoint(event.pos):
                    self.era_quest_sys.show_tracker = not self.era_quest_sys.show_tracker
                    continue

                # Modals capture click first
                if (self.dialog_mgr.show_sleep_confirm or self.dialog_mgr.show_summary_report or 
                    self.dialog_mgr.show_shop or self.dialog_mgr.show_help):
                    if self.dialog_mgr.show_sleep_confirm:
                        self.dialog_mgr.show_sleep_confirm = False
                        self.execute_sleep(pass_out=False)
                    elif self.dialog_mgr.show_summary_report:
                        self.dialog_mgr.show_summary_report = False
                    continue

                # Hotbar click check
                clicked_slot = self.hud.get_clicked_hotbar_slot(event.pos)
                if clicked_slot is not None:
                    self.inventory.set_active_slot(clicked_slot)
                    continue

                # Right Click on World (RTS command or player secondary action)
                if event.button == 3:
                    if self.rts_controller.handle_mouse_down(event):
                        continue
                    if self.player.is_in_reach(target_col, target_row):
                        self.player.face_towards(world_x, world_y)
                        self.handle_secondary_action(target_col, target_row)
                    else:
                        self.player.set_move_target(world_x, world_y)

                # Left Click on World
                elif event.button == 1:
                    # Start RTS drag box
                    self.rts_controller.handle_mouse_down(event)
                    if self.fishing_sys.state == FishingSystem.BITE:
                        self.fishing_sys.start_minigame(self.time_sys.season_id, self.weather_sys.weather, self.time_sys.hour)
                    elif self.fishing_sys.state == FishingSystem.MINIGAME:
                        pass
                    else:
                        if self.player.is_in_reach(target_col, target_row):
                            self.player.face_towards(world_x, world_y)
                            self.handle_primary_action(target_col, target_row)
                        else:
                            # Only set move target if no RTS box drag started
                            if not self.tribe_mgr.get_selected_villagers():
                                self.player.set_move_target(world_x, world_y)

        # Continuous right mouse move tracking
        if not self.inv_panel.is_open() and not self.minimap.show_full_map and not self.npc_shop_panel.is_open():
            buttons = pygame.mouse.get_pressed()
            if buttons[2]:  # Right button held
                mx, my = pygame.mouse.get_pos()
                wx, wy = self.camera.screen_to_world((mx, my))
                tc = int(wx // TILE_SIZE)
                tr = int(wy // TILE_SIZE)
                if not self.player.is_in_reach(tc, tr):
                    self.player.set_move_target(wx, wy)

    # -------------------------------------------------------------
    # PRIMARY ACTION (TOOLS, SEEDS, FORAGING)
    # -------------------------------------------------------------
    def handle_primary_action(self, target_col, target_row):
        active = self.inventory.active_item
        tile_cx = target_col * TILE_SIZE + TILE_SIZE // 2
        tile_cy = target_row * TILE_SIZE + TILE_SIZE // 2

        # 1. Obstacle & Ground Pickup Interaction (Can harvest with hands or any tool)
        if (target_col, target_row) in self.map_mgr.obstacles:
            tool_id = "hands"
            if active and active.get("type") == "tool":
                tool_id = active.get("id")

            self.player.trigger_action("axe")
            msg, sfx = self.map_mgr.handle_tool_action(tool_id, target_col, target_row, self.player, self.inventory)
            if sfx:
                self.assets.play_sound(sfx)
                if sfx == "chop":
                    self.particle_sys.emit_wood_chips(tile_cx, tile_cy, 7)
                    self.particle_sys.emit_leaf_burst(tile_cx, tile_cy - 18, 6)
                    self.camera.trigger_shake(2.8, 0.12)
                elif sfx == "clink":
                    self.particle_sys.emit_rock_sparks(tile_cx, tile_cy, 6)
                    self.camera.trigger_shake(3.2, 0.12)
                else:
                    self.particle_sys.emit_leaf_burst(tile_cx, tile_cy, 5)
            if msg:
                self.dialog_mgr.add_toast(msg)
                self.minimap.mark_dirty()
            return

        if not active:
            return

        if active.get("type") == "tool":
            tool_id = active.get("id")
            tool_type = active.get("tool_type", tool_id)

            # Fishing Rod / Spear
            if tool_type == TOOL_FISHING_ROD or tool_id in ["primitive_spear", "bone_rod", "tribal_harpoon", TOOL_FISHING_ROD]:
                if self.map_mgr.current_zone != ZONE_FARM:
                    self.dialog_mgr.add_toast("Chỉ có thể câu cá ở dòng suối tiền sử!")
                    return
                if self.map_mgr.is_water(target_col, target_row):
                    bobber_pos = (target_col * TILE_SIZE + 16, target_row * TILE_SIZE + 16)
                    self.fishing_sys.start_fishing(bobber_pos)
                    self.assets.play_sound("cast")
                    self.player.consume_stamina(self.player.get_tool_stamina_cost(tool_type))
                    self.dialog_mgr.add_toast("Đã quăng giáo/cần bắt cá! Chờ cá cắn câu...")
                    self.particle_sys.emit_water_splash(bobber_pos[0], bobber_pos[1], 4)
                else:
                    self.dialog_mgr.add_toast("Chỉ có thể câu cá ở vùng nước suối!")
                return

            if tool_type == TOOL_HOE or tool_id in ["digging_stick", "stone_hoe", "bronze_hoe", TOOL_HOE]:
                self.player.trigger_action("hoe")
                self.particle_sys.emit_dirt_puff(tile_cx, tile_cy, 8)
                self.era_quest_sys.has_tilled_or_planted = True
            elif tool_type == TOOL_WATER_CAN or tool_id in ["clay_jug", TOOL_WATER_CAN]:
                self.player.trigger_action("water")
                self.particle_sys.emit_water_splash(tile_cx, tile_cy, 6)
            elif tool_type in [TOOL_AXE, TOOL_PICKAXE, TOOL_SCYTHE]:
                self.player.trigger_action("axe")

            msg, sfx = self.map_mgr.handle_tool_action(tool_id, target_col, target_row, self.player, self.inventory)
            if sfx:
                self.assets.play_sound(sfx)
                if sfx == "chop":
                    self.particle_sys.emit_wood_chips(tile_cx, tile_cy, 7)
                    self.particle_sys.emit_leaf_burst(tile_cx, tile_cy - 18, 6)
                    self.camera.trigger_shake(2.8, 0.12)
                elif sfx == "clink":
                    self.particle_sys.emit_rock_sparks(tile_cx, tile_cy, 6)
                    self.camera.trigger_shake(3.2, 0.12)
                elif tool_type == TOOL_SCYTHE:
                    self.particle_sys.emit_leaf_burst(tile_cx, tile_cy, 7)
                    self.camera.trigger_shake(1.8, 0.08)
                elif sfx == "dig":
                    self.particle_sys.emit_dirt_puff(tile_cx, tile_cy, 6)
                    self.camera.trigger_shake(1.5, 0.08)
            if msg:
                self.dialog_mgr.add_toast(msg)
                self.minimap.mark_dirty()

        elif active.get("type") == "seed":
            crop_id = active.get("id")
            ok, msg = self.map_mgr.plant_seed(crop_id, target_col, target_row, self.inventory)
            self.dialog_mgr.add_toast(msg)
            if ok:
                self.era_quest_sys.has_tilled_or_planted = True
                self.assets.play_sound("dig")
                self.particle_sys.emit_dirt_puff(tile_cx, tile_cy, 4)
                self.minimap.mark_dirty()

    # -------------------------------------------------------------
    # SECONDARY ACTION (INTERACT, HARVEST, PET, SHIPPING, STORAGE, NPC, TELEPORT)
    # -------------------------------------------------------------
    def handle_secondary_action(self, target_col, target_row):
        tile_cx = target_col * TILE_SIZE + TILE_SIZE // 2
        tile_cy = target_row * TILE_SIZE + TILE_SIZE // 2
        player_cx = self.player.x + 16
        player_cy = self.player.y + 16

        # --- A. TOWN ZONE INTERACTIONS ---
        if self.map_mgr.current_zone == ZONE_TOWN:
            # 1. Interact with NPCs
            for npc in self.map_mgr.npcs.values():
                if npc.is_player_near(player_cx, player_cy) or (target_col == npc.col and abs(target_row - npc.row) <= 1):
                    self.npc_shop_panel.open_shop(npc, self.time_sys.season_id, self.inventory)
                    self.assets.play_sound("clink")
                    return

            # 2. Interact with Town Waypoint Pillar (Fast Travel)
            if abs(target_col - self.map_mgr.town_waypoint[0]) <= 1 and abs(target_row - self.map_mgr.town_waypoint[1]) <= 1:
                self.minimap.viewing_zone = "farm"
                self.minimap.show_full_map = True
                return

            return

        # --- B. FARM ZONE INTERACTIONS ---
        # 0. Ground pickup gather by hand
        if (target_col, target_row) in self.map_mgr.obstacles:
            obs = self.map_mgr.obstacles[(target_col, target_row)]
            if obs.is_ground_pickup:
                msg, sfx = self.map_mgr.handle_tool_action("hands", target_col, target_row, self.player, self.inventory)
                if sfx:
                    self.assets.play_sound(sfx)
                if msg:
                    self.dialog_mgr.add_toast(msg)
                    self.minimap.mark_dirty()
                return

        # 1. Campfire Cooking Interaction
        if self.primitive_structures.is_near_campfire(player_cx, player_cy) or (target_col, target_row) == self.primitive_structures.campfire_pos:
            self.crafting_panel.active_category = "cooking"
            self.crafting_panel.is_open = True
            self.assets.play_sound("clink")
            self.dialog_mgr.add_toast("🔥 Đứng bên Đống Lửa Trại! Chọn món nướng sinh tồn.")
            return

        # 2. Primitive Shelter Interaction (Sleep & Save)
        if self.primitive_structures.is_near_shelter(player_cx, player_cy) or (target_col, target_row) == self.map_mgr.bed_pos or (
            self.primitive_structures.shelter_pos[0] <= target_col <= self.primitive_structures.shelter_pos[0] + 3 and
            self.primitive_structures.shelter_pos[1] <= target_row <= self.primitive_structures.shelter_pos[1] + 3
        ):
            self.dialog_mgr.show_sleep_confirm = True
            return

        # 3. Wandering Rare Merchant
        if self.wandering_merchant.is_present and self.wandering_merchant.is_player_near(player_cx, player_cy):
            self.npc_shop_panel.open_shop(
                None, self.time_sys.season_id, self.inventory, is_wandering=True, wandering_ref=self.wandering_merchant
            )
            self.assets.play_sound("coin")
            return

        # 4. Farm Fast Travel Waypoint
        if abs(target_col - self.map_mgr.farm_waypoint[0]) <= 1 and abs(target_row - self.map_mgr.farm_waypoint[1]) <= 1:
            self.minimap.viewing_zone = "town"
            self.minimap.show_full_map = True
            return

        # 5. Storage Chest interaction
        if (target_col, target_row) == self.storage_pos:
            self.inv_panel.open_storage()
            return

        # 5. Shipping Bin interaction
        if (target_col, target_row) == self.map_mgr.shipping_bin_pos:
            active = self.inventory.active_item
            if active and active.get("type") != "tool":
                qty_to_ship = active.get("qty", 1)
                item_name = active.get("name", "Vật phẩm")
                if self.shipping_bin.deposit(active, qty_to_ship):
                    self.inventory.remove_active_item(qty_to_ship)
                    self.assets.play_sound("coin")
                    self.dialog_mgr.add_toast(f"Đã bỏ {qty_to_ship}x {item_name} vào thùng xuất hàng!")
                    self.particle_sys.emit_harvest_sparkle(tile_cx, tile_cy - 20, 6)
            else:
                bin_count = len(self.shipping_bin.items)
                self.dialog_mgr.add_toast(f"Thùng xuất hàng: hiện có {bin_count} loại mặt hàng đang chờ bán qua đêm.")
            return

        # 6. Harvest Crop
        harvested, msg = self.map_mgr.harvest_crop(target_col, target_row, self.inventory)
        if harvested:
            self.era_quest_sys.has_harvested_any = True
            self.assets.play_sound("success")
            self.dialog_mgr.add_toast(msg)
            self.particle_sys.emit_harvest_sparkle(tile_cx, tile_cy, 10)
            self.minimap.mark_dirty()
            return
        elif msg:
            self.dialog_mgr.add_toast(msg)
            return

        # 7. Animal Interaction
        anim_res, sfx = self.animals_mgr.interact_with_nearby_animal(player_cx, player_cy)
        if anim_res:
            if sfx:
                self.assets.play_sound(sfx)
            if isinstance(anim_res, dict):
                self.inventory.add_item(anim_res, 1)
                self.assets.play_sound("success")
                self.dialog_mgr.add_toast(f"Thu hoạch {anim_res['name']} (+{anim_res['price']}G)!")
                self.particle_sys.emit_harvest_sparkle(player_cx, player_cy - 20, 8)
            else:
                self.dialog_mgr.add_toast(anim_res)

    # -------------------------------------------------------------
    # FAST TRAVEL TELEPORTATION
    # -------------------------------------------------------------
    def execute_teleport(self, target_zone):
        """Teleports player between Farm and Town with magic sparkle effects."""
        self.map_mgr.switch_zone(target_zone, self.player)
        self.camera.snap_to(self.player.rect)
        self.particle_sys.emit_harvest_sparkle(self.player.x, self.player.y, 25)
        self.assets.play_sound("success")
        dest_name = "Quảng Trường Thị Trấn Hương Đồng" if target_zone == ZONE_TOWN else "Nông Trại Hương Đồng"
        self.dialog_mgr.add_toast(f"⚡ Đã dịch chuyển tức thời đến {dest_name}!")
        self.minimap.mark_dirty()

    # -------------------------------------------------------------
    # OVERNIGHT SLEEP & PASS-OUT LOGIC
    # -------------------------------------------------------------
    def execute_sleep(self, pass_out=False):
        if pass_out:
            self.player.recover_stamina(50.0)
            self.dialog_mgr.add_toast("Bạn đã ngất xỉu vì làm việc quá khuya! (Hồi 50% thể lực)")
        else:
            self.player.recover_stamina(100.0)

        new_day_info = self.time_sys.sleep_and_advance_day()
        self.weather_sys.pick_next_day_weather(new_day_info["season_id"])
        is_raining = (self.weather_sys.weather in ["rain", "storm"])

        self.map_mgr.advance_day(new_day_info["season_id"], is_raining=is_raining)
        self.animals_mgr.advance_day()

        # Check Wandering Merchant arrival
        if self.wandering_merchant.check_daily_appearance(new_day_info["day"], new_day_info["season_id"], new_day_info["year"]):
            self.dialog_mgr.add_toast("🌟 Thương nhân du mục huyền bí Lão Hạc đã ghé thăm bộ lạc hôm nay!")

        earnings = self.shipping_bin.calculate_overnight_earnings()
        if earnings["total"] > 0:
            self.inventory.gold += earnings["total"]
            self.dialog_mgr.summary_data = earnings
            self.dialog_mgr.show_summary_report = True
            self.assets.play_sound("success")

        # Sleep brings player home to shelter in primitive valley
        self.map_mgr.switch_zone(ZONE_FARM, self.player, spawn_tile=(self.primitive_structures.shelter_pos[0] + 1, self.primitive_structures.shelter_pos[1] + 2))
        self.camera.snap_to(self.player.rect)
        self.player.move_target = None
        self.minimap.mark_dirty()

        SaveSystem.save_game(self.time_sys, self.weather_sys, self.player,
                             self.inventory, self.map_mgr, self.animals_mgr, 
                             self.shipping_bin, self.storage,
                             self.crafting_sys, self.primitive_structures, self.era_quest_sys)

    # -------------------------------------------------------------
    # UPDATE LOOP
    # -------------------------------------------------------------
    def update(self, dt):
        is_modal_active = (self.dialog_mgr.show_summary_report or 
                           self.dialog_mgr.show_sleep_confirm or 
                           self.dialog_mgr.show_shop or 
                           self.dialog_mgr.show_help or
                           self.npc_shop_panel.is_open() or
                           self.crafting_panel.is_open)

        self.dialog_mgr.update(dt)
        self.game_time = getattr(self, "game_time", 0.0) + dt
        self.particle_sys.update(dt)
        self.inv_panel.update(dt)
        self.minimap.update(dt)
        self.npc_shop_panel.update(dt)
        self.primitive_structures.update(dt)
        self.tribe_mgr.update(dt, self.time_sys, self.map_mgr.obstacles)
        self.rts_controller.update(dt)

        # Update Fog of War active vision & Prehistoric Wildlife
        vision_sources = [
            (self.player.x, self.player.y, 8),
            (self.primitive_structures.campfire_pos[0] * TILE_SIZE + 32,
             self.primitive_structures.campfire_pos[1] * TILE_SIZE + 32, 6)
        ]
        for v in self.tribe_mgr.alive_villagers:
            vision_sources.append((v.x, v.y, 6))

        self.fog_of_war.update_visibility(vision_sources)
        self.wildlife_mgr.update(dt, self.tribe_mgr.alive_villagers, self.player, self.tribe_mgr)

        # Check prehistoric era quest progress
        self.era_quest_sys.check_progress(
            self.inventory, self.crafting_sys, self.primitive_structures,
            self.dialog_mgr, self.assets
        )

        if is_modal_active or self.inv_panel.is_open() or self.minimap.show_full_map or self.crafting_panel.is_open:
            return

        # 1. Player Movement & Input
        keys = pygame.key.get_pressed()
        self.player.handle_keyboard_input(keys)
        self.player.update(dt, self.map_mgr)
        if self.player.footstep_emitted:
            self.particle_sys.emit_dirt_puff(self.player.x, self.player.y + 10, count=1)
            self.player.footstep_emitted = False
        self.camera.update(self.player.rect, dt)

        # 2. Check seamless border road transitions (Farm <-> Town)
        border_msg = self.map_mgr.check_border_transition(self.player)
        if border_msg:
            self.camera.snap_to(self.player.rect)
            self.dialog_mgr.add_toast(border_msg)
            self.minimap.mark_dirty()

        # 3. Screen shake
        self.camera.set_shake(self.weather_sys.screen_shake_x, 
                             self.weather_sys.screen_shake_y)

        # 4. Time update
        time_event = self.time_sys.update(dt)
        if time_event == "PASS_OUT":
            self.execute_sleep(pass_out=True)

        # 5. Weather
        self.weather_sys.update(dt)

        # 6. Ambient particles & Chimney Smoke
        is_night = (self.time_sys.hour >= 19 or self.time_sys.hour < 5)
        self.particle_sys.update_ambient(dt, self.time_sys.season_id, self.weather_sys.weather, is_night)
        self._smoke_timer = getattr(self, "_smoke_timer", 0.0) + dt
        if self._smoke_timer >= 0.16:
            self._smoke_timer = 0.0
            if self.map_mgr.current_zone == ZONE_FARM:
                # Farmhouse chimney at col 20 + 88px, row 18 + 24px
                self.particle_sys.emit_chimney_smoke(20 * TILE_SIZE + 88, 18 * TILE_SIZE + 24)
            elif self.map_mgr.current_zone == ZONE_TOWN:
                # Blacksmith forge chimney at col 32 + 480px, row 9 + 24px
                self.particle_sys.emit_chimney_smoke(32 * TILE_SIZE + 480, 9 * TILE_SIZE + 24)

        # 7. Map & Water animation
        self.map_mgr.update(dt)

        # 8. Animals (Farm only)
        if self.map_mgr.current_zone == ZONE_FARM:
            self.animals_mgr.update(dt)

        # 9. Fishing (Farm only)
        if self.map_mgr.current_zone == ZONE_FARM:
            holding_space = keys[pygame.K_SPACE] or pygame.mouse.get_pressed()[0]
            fish_event = self.fishing_sys.update(
                dt, holding_space, self.time_sys.season_id, 
                self.weather_sys.weather, self.time_sys.hour
            )
            if fish_event == "PLAY_BITE_SFX":
                self.assets.play_sound("bite")
            elif fish_event == "PLAY_SUCCESS_SFX":
                self.assets.play_sound("success")
                caught = self.fishing_sys.caught_fish_item
                if caught:
                    self.inventory.add_item(caught, 1)
                    self.dialog_mgr.add_toast(f"Bắt được {caught['name']} (+{caught['price']}G)!")
                    self.particle_sys.emit_harvest_sparkle(
                        self.player.x, self.player.y - 30, 12)
                self.fishing_sys.cancel()

    # -------------------------------------------------------------
    # RENDER LOOP
    # -------------------------------------------------------------
    def render(self):
        self.screen.fill((18, 14, 22))

        # 1. Terrain (Farm or Town)
        self._render_terrain()

        # 2. Click-to-Move Marker
        self.player.draw_click_marker(self.screen, self.camera)

        # 3. Buildings & Town Elements
        self._render_buildings()

        # Primitive Structures (Campfire, Shelter, Kiln, Totem) on Farm Zone
        if self.map_mgr.current_zone == ZONE_FARM:
            self.primitive_structures.draw(self.screen, self.camera, self.assets.fonts)

        # 4. Crops (Farm only)
        if self.map_mgr.current_zone == ZONE_FARM:
            self._render_crops()

        # 5. Fishing Bobber (Farm only)
        if self.map_mgr.current_zone == ZONE_FARM:
            self.fishing_sys.draw_bobber(self.screen, self.camera)

        # 6. Y-Sorted World Entities (Player, Obstacles, Animals, NPCs)
        self._render_ysorted_entities()

        # 9. World-Space Particles
        self.particle_sys.draw_world(self.screen, 
                                      self.camera.offset_x + self.camera.shake_x,
                                      self.camera.offset_y + self.camera.shake_y)

        # 10. Weather Particles
        self.weather_sys.draw_weather(self.screen)

        # 11. Ambient Particles
        self.particle_sys.draw_screen(self.screen)

        # 12. Lighting
        self._render_lighting()

        # 12.3 Fog of War (AOE 3-tier fog overlay)
        if self.map_mgr.current_zone == ZONE_FARM:
            self.fog_of_war.draw(self.screen, self.camera)

        # 12.5. RTS Controller & Tribal Settlement UI
        if not self.minimap.show_full_map and not self.inv_panel.is_open() and not self.npc_shop_panel.is_open():
            self.rts_controller.draw(self.screen, self.assets.fonts)
            self.tribe_mgr.draw_events(self.screen, self.assets.fonts)

        # 13. Fishing Minigame
        if self.fishing_sys.state == FishingSystem.MINIGAME:
            self.fishing_sys.draw_minigame(self.screen, SCREEN_WIDTH - 80, SCREEN_HEIGHT // 2 - 100)

        # 14. Minimap (corner)
        if not self.inv_panel.is_open() and not self.npc_shop_panel.is_open():
            self.minimap.draw_minimap(self.screen, self.map_mgr, self.animals_mgr, 
                                      self.player, self.camera, self.fog_of_war)

        # 15. HUD
        if not self.minimap.show_full_map and not self.inv_panel.is_open() and not self.npc_shop_panel.is_open() and not self.crafting_panel.is_open:
            self.hud.draw(self.screen, self.player, self.inventory, self.time_sys, self.weather_sys, self.camera,
                          self.crafting_sys, self.era_quest_sys)

        # 16. Modals, Menus, Toasts
        self.dialog_mgr.draw(self.screen)

        # 17. Inventory Panel (Tab)
        self.inv_panel.draw(self.screen, self.inventory, self.storage)

        # 17.5. Crafting & Building Panel (C)
        self.crafting_panel.draw(self.screen, self.crafting_sys, self.inventory)

        # 18. NPC Shop & Haggling Panel (over world)
        self.npc_shop_panel.draw(self.screen, self.inventory)

        # 19. Full Map View (over everything)
        if self.minimap._modal_alpha > 0.01:
            self.minimap.draw_full_map(self.screen, self.map_mgr, self.animals_mgr,
                                       self.player, self.assets.fonts["small"],
                                       self.assets.fonts["normal"], self.assets.fonts["large"],
                                       self.fog_of_war)

        pygame.display.flip()

    def _render_terrain(self):
        ts = TILE_SIZE
        if self.map_mgr.current_zone == ZONE_FARM:
            start_col = max(0, int(self.camera.offset_x // ts))
            end_col = min(self.map_mgr.cols, int((self.camera.offset_x + SCREEN_WIDTH) // ts) + 2)
            start_row = max(0, int(self.camera.offset_y // ts))
            end_row = min(self.map_mgr.rows, int((self.camera.offset_y + SCREEN_HEIGHT) // ts) + 2)

            t_loam = self.assets.textures.get("settlement_loam") or self.assets.textures.get("tile_03_trampled_dirt_trail")
            t_pebble = self.assets.textures.get("pebble_shore") or self.assets.textures.get("tile_04_pebble_river_shore")
            t_tilled = self.assets.textures.get("dirt_tilled")
            t_watered = self.assets.textures.get("dirt_watered")

            # 1. Base Ground & Terrain Horizons (5 distinct soil horizons from MapManager)
            for r in range(start_row, end_row):
                for c in range(start_col, end_col):
                    screen_pos = self.camera.apply_pos((c * ts, r * ts))
                    h = (r * 31 + c * 17) % 4
                    t_type = self.map_mgr.terrain[r][c]

                    if t_type == "scree_talus":
                        base_tex = self.assets.textures.get("scree_talus") or self.assets.textures.get("biome_highlands")
                    elif t_type == "forest_humus":
                        base_tex = self.assets.textures.get("forest_humus") or self.assets.textures.get("biome_forest")
                    elif t_type == "riparian_mud":
                        base_tex = self.assets.textures.get("riparian_mud") or self.assets.textures.get("biome_swamp")
                    elif t_type == "point_bar_sand":
                        base_tex = self.assets.textures.get("point_bar_sand") or self.assets.textures.get("pebble_shore")
                    elif t_type == "water" or t_type in ("bridge_ford", "bridge_log"):
                        base_tex = self.assets.textures.get("point_bar_sand") or self.assets.textures.get("pebble_shore")
                    else:
                        base_tex = self.assets.textures.get(f"biome_steppe_{h}") or self.assets.textures.get("steppe_meadow") or self.assets.textures.get("biome_steppe")

                    if base_tex:
                        self.screen.blit(base_tex, screen_pos)

                    if t_type in ["settlement_loam", "trail_dirt", "trail_gravel", "trail_causeway"]:
                        loam_set = {"settlement_loam", "trail_dirt", "trail_gravel", "trail_causeway"}
                        n_up = 1 if (r > 0 and self.map_mgr.terrain[r - 1][c] in loam_set) else 0
                        n_down = 1 if (r < self.map_mgr.rows - 1 and self.map_mgr.terrain[r + 1][c] in loam_set) else 0
                        n_left = 1 if (c > 0 and self.map_mgr.terrain[r][c - 1] in loam_set) else 0
                        n_right = 1 if (c < self.map_mgr.cols - 1 and self.map_mgr.terrain[r][c + 1] in loam_set) else 0
                        loam_tex = self.assets.textures.get(f"loam_{n_up}{n_down}{n_left}{n_right}") or t_loam
                        if loam_tex:
                            self.screen.blit(loam_tex, screen_pos)
                    elif t_type == "dirt_tilled" and t_tilled:
                        self.screen.blit(t_tilled, screen_pos)
                    elif t_type == "dirt_watered" and t_watered:
                        self.screen.blit(t_watered, screen_pos)

            # 1.5. 2.5D Terraced Cliff Facings & Shading (Levels 0..4 Topography)
            # Rendered north to south so cliffs overhang lower tiers naturally
            cliff_s = self.assets.textures.get("cliff_face_south")
            cliff_tall = self.assets.textures.get("cliff_face_south_tall")
            cliff_e = self.assets.textures.get("cliff_edge_east")
            cliff_w = self.assets.textures.get("cliff_edge_west")

            c_start_row = max(0, start_row - 1)
            c_end_row = min(self.map_mgr.rows, end_row + 1)
            for r in range(c_start_row, c_end_row):
                for c in range(start_col, end_col):
                    # East cliff side shadow
                    if cliff_e and self.map_mgr.farm_cliff_east[r][c] > 0:
                        e_sx = c * ts + ts - 16 - self.camera.offset_x
                        e_sy = r * ts - self.camera.offset_y
                        self.screen.blit(cliff_e, (e_sx, e_sy))

                    # West cliff edge bevel highlight
                    if cliff_w and self.map_mgr.farm_cliff_west[r][c] > 0:
                        w_sx = c * ts - self.camera.offset_x
                        w_sy = r * ts - self.camera.offset_y
                        self.screen.blit(cliff_w, (w_sx, w_sy))

                    # South cliff drop wall (Stratified 2.5D natural rock facings)
                    s_drop = self.map_mgr.farm_cliff_south[r][c]
                    if s_drop > 0:
                        cw_x = c * ts - self.camera.offset_x
                        cw_y = (r + 1) * ts - 6 - self.camera.offset_y
                        v_idx = (c * 7 + r * 13) % 4
                        if s_drop >= 2:
                            c_tex = self.assets.textures.get(f"cliff_face_south_tall_{v_idx}") or cliff_tall
                        else:
                            c_tex = self.assets.textures.get(f"cliff_face_south_{v_idx}") or cliff_s
                        if c_tex:
                            self.screen.blit(c_tex, (cw_x, cw_y))

            # 2. Smooth Continuous Organic River Course, Riparian Pebble Shoreline & Wave VFX
            # Sample continuous river banks and pebble shores at 8px vertical intervals
            pts_l = []
            pts_r = []
            pts_sh_l = []
            pts_sh_r = []
            pts_beach_outer_l = []
            pts_beach_outer_r = []
            pts_beach_fade_l = []
            pts_beach_fade_r = []
            foam_l = []
            foam_r = []

            gt = getattr(self, "game_time", 0.0)
            view_top = -16
            view_bottom = SCREEN_HEIGHT + 16
            sample_step = 8

            for sy in range(view_top, view_bottom + sample_step, sample_step):
                wy = self.camera.offset_y + sy
                row_f = wy / float(ts)
                rc = self.map_mgr.get_river_center_float(row_f) * ts + 32.0
                hw = self.map_mgr.get_river_half_width_float(row_f) * ts
                s_xl = rc - hw - self.camera.offset_x
                s_xr = rc + hw - self.camera.offset_x

                pts_l.append((s_xl, sy))
                pts_r.append((s_xr, sy))
                pts_sh_l.append((s_xl + 26.0, sy))
                pts_sh_r.append((s_xr - 26.0, sy))

                # Riparian Pebble Shoreline & Point Bar Geomorphology
                # Inner bend (left/west bank, camp side) forms an expansive sandy pebble point bar
                point_bar_deposit = 58.0 * math.exp(-((row_f - 39.0) ** 2) / 64.0)
                bw_l = 36.0 + 8.0 * math.sin(row_f * 0.75 + 1.2) + point_bar_deposit
                # Outer bend (right/east bank) forms a steep erosional cutbank
                cutbank_pinch = 14.0 * math.exp(-((row_f - 39.0) ** 2) / 64.0)
                bw_r = max(18.0, 34.0 + 8.0 * math.cos(row_f * 0.65) - cutbank_pinch)
                pts_beach_outer_l.append((s_xl - bw_l, sy))
                pts_beach_outer_r.append((s_xr + bw_r, sy))
                pts_beach_fade_l.append((s_xl - bw_l - 18.0, sy))
                pts_beach_fade_r.append((s_xr + bw_r + 14.0, sy))

                # Harmonic lapping wave foam
                f_xl = s_xl + 3.8 * math.sin(2.4 * gt + sy * 0.05)
                f_xr = s_xr - 3.8 * math.sin(2.4 * gt + sy * 0.05 + 1.2)
                foam_l.append((f_xl, sy))
                foam_r.append((f_xr, sy))

            # Only render river corridor if river intersects the current viewport
            min_xl = min(p[0] for p in pts_beach_fade_l)
            max_xr = max(p[0] for p in pts_beach_fade_r)
            if min_xl < SCREEN_WIDTH + 80 and max_xr > -80:
                river_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

                # A. Riparian Pebble Shoreline & Great Point Bar (Multi-layer organic sand & gravel)
                # Outer soft feathering transition into steppe grass
                poly_fade_l = pts_beach_fade_l + list(reversed(pts_beach_outer_l))
                pygame.draw.polygon(river_surf, (198, 185, 142, 110), poly_fade_l)

                poly_fade_r = pts_beach_outer_r + list(reversed(pts_beach_fade_r))
                pygame.draw.polygon(river_surf, (198, 185, 142, 110), poly_fade_r)

                # Main continuous pebble beach & sunlit point bar sand
                poly_beach_l = pts_beach_outer_l + list(reversed(pts_l))
                pygame.draw.polygon(river_surf, (216, 202, 164, 255), poly_beach_l)

                poly_beach_r = pts_r + list(reversed(pts_beach_outer_r))
                pygame.draw.polygon(river_surf, (192, 178, 140, 255), poly_beach_r)

                # Scattered natural smooth river pebbles & flint flakes
                for sy in range(view_top, view_bottom, 24):
                    wy = self.camera.offset_y + sy
                    row_f = wy / float(ts)
                    rc = self.map_mgr.get_river_center_float(row_f) * ts + 32.0
                    hw = self.map_mgr.get_river_half_width_float(row_f) * ts
                    s_xl = rc - hw - self.camera.offset_x
                    s_xr = rc + hw - self.camera.offset_x
                    point_bar_deposit = 58.0 * math.exp(-((row_f - 39.0) ** 2) / 64.0)
                    bw_l = 36.0 + 8.0 * math.sin(row_f * 0.75 + 1.2) + point_bar_deposit
                    cutbank_pinch = 14.0 * math.exp(-((row_f - 39.0) ** 2) / 64.0)
                    bw_r = max(18.0, 34.0 + 8.0 * math.cos(row_f * 0.65) - cutbank_pinch)

                    # Left bank pebbles (Concentrated on Great Point Bar)
                    plx = int(s_xl - bw_l * 0.55 + 5.0 * math.sin(wy * 0.13))
                    pygame.draw.circle(river_surf, (145, 130, 95, 190), (plx, sy), 3)
                    pygame.draw.circle(river_surf, (215, 200, 160, 210), (plx + 1, sy - 1), 1)
                    if point_bar_deposit > 20.0:
                        # Extra dry pebbles & amber sand flecks on point bar
                        plx2 = int(s_xl - bw_l * 0.25 + 3.0 * math.cos(wy * 0.19))
                        pygame.draw.circle(river_surf, (168, 142, 98, 180), (plx2, sy + 6), 2)
                        pygame.draw.circle(river_surf, (225, 210, 175, 200), (plx2 + 1, sy + 5), 1)

                    # Right bank pebbles
                    prx = int(s_xr + bw_r * 0.55 + 5.0 * math.cos(wy * 0.15))
                    pygame.draw.circle(river_surf, (145, 130, 95, 190), (prx, sy), 3)
                    pygame.draw.circle(river_surf, (215, 200, 160, 210), (prx + 1, sy - 1), 1)

                # B. Deep River Channel
                poly_deep = pts_l + list(reversed(pts_r))
                pygame.draw.polygon(river_surf, (37, 104, 143, 245), poly_deep)

                # C. Shallow Ford Shoreline Bands (Sub-tile depth gradation)
                poly_sh_l = pts_l + list(reversed(pts_sh_l))
                pygame.draw.polygon(river_surf, (72, 162, 192, 160), poly_sh_l)

                poly_sh_r = pts_sh_r + list(reversed(pts_r))
                pygame.draw.polygon(river_surf, (72, 162, 192, 160), poly_sh_r)

                # D. Flowing Specular Caustics (Moving downstream North -> South)
                flow_y_offset = int((gt * 38.0) % 36.0)
                for cy in range(-36 + flow_y_offset, SCREEN_HEIGHT + 36, 36):
                    c_wy = self.camera.offset_y + cy
                    c_row_f = c_wy / float(ts)
                    c_rc = self.map_mgr.get_river_center_float(c_row_f) * ts + 32.0
                    c_hw = self.map_mgr.get_river_half_width_float(c_row_f) * ts
                    c_xl = c_rc - c_hw - self.camera.offset_x + 30.0
                    c_xr = c_rc + c_hw - self.camera.offset_x - 30.0
                    if c_xr > c_xl:
                        c_pts = []
                        for cx in range(int(c_xl), int(c_xr) + 8, 12):
                            w_sine = cy + int(2.5 * math.sin(cx * 0.08 + gt * 2.0))
                            c_pts.append((cx, w_sine))
                        if len(c_pts) >= 2:
                            for idx in range(len(c_pts) - 1):
                                pygame.draw.line(river_surf, (180, 230, 248, 85), c_pts[idx], c_pts[idx + 1], 1)

                # E. Harmonic Shoreline Wave Lapping & Foam
                if len(foam_l) >= 2:
                    pygame.draw.lines(river_surf, (235, 248, 255, 215), False, foam_l, 2)
                if len(foam_r) >= 2:
                    pygame.draw.lines(river_surf, (235, 248, 255, 215), False, foam_r, 2)

                self.screen.blit(river_surf, (0, 0))

            # 3. River Crossings (Stepping Stone Ford at r=36 & Log Bridge at r=48)
            # Row 36: Stepping Stone Ford
            r36_sy = int(36 * ts + 32 - self.camera.offset_y)
            if -80 <= r36_sy <= SCREEN_HEIGHT + 80:
                rc_36 = self.map_mgr.get_river_center_float(36.0) * ts + 32.0
                hw_36 = self.map_mgr.get_river_half_width_float(36.0) * ts
                r36_rc_sx = int(rc_36 - self.camera.offset_x)

                # Shallow clear turquoise ford wash across the crossing (reveals riverbed stones)
                f_w = int(hw_36 * 2.1)
                ford_wash = pygame.Surface((f_w, 48), pygame.SRCALPHA)
                pygame.draw.ellipse(ford_wash, (95, 195, 225, 115), (0, 0, f_w, 48))
                pygame.draw.ellipse(ford_wash, (160, 230, 248, 80), (12, 8, f_w - 24, 32))
                self.screen.blit(ford_wash, (int(rc_36 - hw_36 * 1.05 - self.camera.offset_x), r36_sy - 24))

                # Natural rounded granite river stepping stones spanning across the shallow water
                num_stones = 9
                for s_i in range(num_stones):
                    t_frac = (s_i + 0.5) / float(num_stones)
                    st_world_x = (rc_36 - hw_36 * 0.85) + t_frac * (hw_36 * 1.7)
                    st_sx = int(st_world_x - self.camera.offset_x)
                    st_sy = int(36.0 * ts + 32.0 - self.camera.offset_y + 4.0 * math.sin(s_i * 1.4))
                    st_tex = self.assets.textures.get(f"stepping_stone_{s_i % 4}")
                    if st_tex and -50 <= st_sx <= SCREEN_WIDTH + 50 and -50 <= st_sy <= SCREEN_HEIGHT + 50:
                        sw, sh = st_tex.get_size()
                        self.screen.blit(st_tex, (st_sx - sw // 2, st_sy - sh // 2))

            # Row 48: Log Bridge
            r48_sy = int(48 * ts + 32 - self.camera.offset_y)
            if -64 <= r48_sy <= SCREEN_HEIGHT + 64:
                r48_rc_sx = int(self.map_mgr.get_river_center_float(48) * ts + 32 - self.camera.offset_x)
                log_full = self.assets.textures.get("bridge_log_full")
                if log_full:
                    lw, lh = log_full.get_size()
                    self.screen.blit(log_full, (r48_rc_sx - lw // 2, r48_sy - lh // 2))
        else:
            # Town Composite
            town_comp = self.assets.textures.get("town_composite")
            if town_comp:
                self.screen.blit(town_comp, self.camera.apply_pos((0, 0)))

    def _render_buildings(self):
        ts = TILE_SIZE

        if self.map_mgr.current_zone == ZONE_FARM:
            # Prehistoric Waypoint Marker (Inukshuk Stone Cairn)
            fwp_pos = self.camera.apply_pos((self.map_mgr.farm_waypoint[0] * ts, self.map_mgr.farm_waypoint[1] * ts))
            wp_tex = self.assets.textures.get("waypoint_inukshuk") or self.assets.textures.get("teleport_waypoint")
            if wp_tex:
                # Stone base drop shadow
                VisualEnhancer.draw_drop_shadow(self.screen, (fwp_pos[0] + 32, fwp_pos[1] + 52), 48, 18)
                self.screen.blit(wp_tex, (fwp_pos[0], fwp_pos[1] - 16))

            # Tribal Resource Cache (Kho Tài Nguyên Bộ Tộc - Woven Basket & Timber Stockpile)
            stor_pos = self.camera.apply_pos((self.storage_pos[0] * ts, self.storage_pos[1] * ts))
            stor_tex = self.assets.textures.get("branch_logs") or self.assets.textures.get("shipping_bin")
            if stor_tex:
                VisualEnhancer.draw_drop_shadow(self.screen, (stor_pos[0] + 32, stor_pos[1] + 46), 44, 16)
                self.screen.blit(stor_tex, stor_pos)

            # Wandering Rare Merchant
            if self.wandering_merchant.is_present:
                rug_pos = self.camera.apply_pos((self.wandering_merchant.col * ts, self.wandering_merchant.row * ts))
                rug_tex = self.assets.textures.get("magic_rug")
                if rug_tex:
                    self.screen.blit(rug_tex, rug_pos)

                merch_pos = self.camera.apply_pos((self.wandering_merchant.col * ts + 32, self.wandering_merchant.row * ts + 20))
                merch_tex = self.assets.textures.get("wandering_merchant")
                if merch_tex:
                    self.screen.blit(merch_tex, merch_pos)
            if self.wandering_merchant.is_present:
                rug_pos = self.camera.apply_pos((self.wandering_merchant.col * ts, self.wandering_merchant.row * ts))
                rug_tex = self.assets.textures.get("magic_rug")
                if rug_tex:
                    self.screen.blit(rug_tex, rug_pos)

                merch_pos = self.camera.apply_pos((self.wandering_merchant.col * ts + 32, self.wandering_merchant.row * ts + 20))
                merch_tex = self.assets.textures.get("wandering_merchant")
                if merch_tex:
                    self.screen.blit(merch_tex, merch_pos)
                    # Label
                    mlbl = self.assets.fonts["tiny"].render("Lão Hạc (Thương Nhân)", True, (255, 235, 120))
                    mbg = pygame.Surface((mlbl.get_width() + 6, 14), pygame.SRCALPHA)
                    pygame.draw.rect(mbg, (90, 25, 110, 200), (0, 0, mbg.get_width(), 14), border_radius=3)
                    self.screen.blit(mbg, (merch_pos[0] + 32 - mbg.get_width() // 2, merch_pos[1] - 14))
                    self.screen.blit(mlbl, (merch_pos[0] + 32 - mlbl.get_width() // 2 + 1, merch_pos[1] - 13))

        else:
            # --- TOWN BUILDINGS & PROPS ---
            # 1. Shop Cô Mai (cols 10..18, rows 9..14)
            sm_pos = self.camera.apply_pos((10 * ts, 9 * ts))
            sm_tex = self.assets.textures.get("shop_co_mai")
            if sm_tex:
                self.screen.blit(sm_tex, sm_pos)

            # 2. Shop Bác Bảy (cols 32..40, rows 9..14)
            sb_pos = self.camera.apply_pos((32 * ts, 9 * ts))
            sb_tex = self.assets.textures.get("shop_bac_bay")
            if sb_tex:
                self.screen.blit(sb_tex, sb_pos)

            # 3. Shop Cụ Ba Tri (cols 20..30, rows 3..8)
            st_pos = self.camera.apply_pos((20 * ts, 3 * ts))
            st_tex = self.assets.textures.get("shop_cu_ba_tri")
            if st_tex:
                self.screen.blit(st_tex, st_pos)

            # 4. Town Waypoint Pillar (col 25, row 24)
            twp_pos = self.camera.apply_pos((self.map_mgr.town_waypoint[0] * ts, self.map_mgr.town_waypoint[1] * ts))
            wp_tex = self.assets.textures.get("teleport_waypoint")
            if wp_tex:
                self.screen.blit(wp_tex, twp_pos)
                wp_lbl = self.assets.fonts["tiny"].render("Cột Đá Tổ (Bản Doanh)", True, (255, 255, 255))
                wp_bg = pygame.Surface((wp_lbl.get_width() + 6, 14), pygame.SRCALPHA)
                pygame.draw.rect(wp_bg, (120, 65, 30, 190), (0, 0, wp_bg.get_width(), 14), border_radius=3)
                self.screen.blit(wp_bg, (twp_pos[0] + 32 - wp_bg.get_width() // 2, twp_pos[1] - 14))
                self.screen.blit(wp_lbl, (twp_pos[0] + 32 - wp_lbl.get_width() // 2 + 1, twp_pos[1] - 13))


    def _render_crops(self):
        ts = TILE_SIZE
        for (col, row), crop in self.map_mgr.crops.items():
            screen_pos = self.camera.apply_pos((col * ts, row * ts))
            if crop.is_dead:
                pygame.draw.line(self.screen, (115, 80, 50), (screen_pos[0] + 32, screen_pos[1] + 54), 
                                 (screen_pos[0] + 32, screen_pos[1] + 24), 3)
            else:
                tex = self.assets.textures.get(f"crop_{crop.crop_id}_{crop.current_stage}")
                if tex:
                    self.screen.blit(tex, screen_pos)

    def _render_ysorted_entities(self):
        """
        Renders world objects with proper 2.5D depth ordering (Y-sorting).
        Objects with lower foot Y are drawn behind objects with higher foot Y.
        """
        ts = TILE_SIZE
        season_id = self.time_sys.season_id
        draw_queue = []

        # 1. Player
        d = self.player.direction
        f_walk = self.player.anim_frame % 4
        f_idle = self.player.anim_frame % 2
        if self.player.action_state:
            act = self.player.action_state
            f_act = 0 if self.player.action_timer > 0.18 else 1
            p_tex = self.assets.textures.get(f"player_{d}_{act}_{f_act}")
            if not p_tex:
                p_tex = self.assets.textures.get(f"player_{d}_{f_walk}")
        elif self.player.is_moving:
            p_tex = self.assets.textures.get(f"player_{d}_{f_walk}")
        else:
            p_tex = self.assets.textures.get(f"player_{d}_idle_{f_idle}")

        if p_tex:
            p_sort_y = self.player.y + 10
            def make_draw_player(tex, px, py):
                def _draw():
                    pw, ph = tex.get_size()
                    # Soft ellipse drop shadow right under player's feet
                    foot_screen = self.camera.apply_pos((px, py + 4))
                    VisualEnhancer.draw_drop_shadow(self.screen, foot_screen, 36, 14)
                    self.screen.blit(tex, self.camera.apply_pos((px - pw // 2, py - ph + 6)))
                return _draw
            draw_queue.append((p_sort_y, make_draw_player(p_tex, self.player.x, self.player.y)))

        # 2. Obstacles (trees, boulders, stumps, organic bushes, etc.)
        for (col, row), obs in self.map_mgr.obstacles.items():
            jx = getattr(obs, "jitter_x", 0)
            jy = getattr(obs, "jitter_y", 0)
            ox = col * ts + jx
            oy = row * ts + jy
            var = getattr(obs, "variant", 0)

            # Frustum culling
            if not (-ts <= ox - self.camera.offset_x <= SCREEN_WIDTH + ts and
                    -120 <= oy - self.camera.offset_y <= SCREEN_HEIGHT + 120):
                continue

            if obs.obs_type == "tree":
                if 0 < obs.health < obs.max_health:
                    obs_tex = self.assets.textures.get("woodcut_stage_notched") or self.assets.textures.get("woodcut_stage_intact")
                else:
                    obs_tex = self.assets.textures.get("woodcut_stage_intact") or self.assets.textures.get(f"tree_{season_id}")
                draw_pos = (ox + obs.shake_offset - 20, oy - 62)
                sort_y = oy + 54  # tree base
                shadow_center = (ox + 32, oy + 50)
                shadow_size = (64, 22)
            elif obs.obs_type in ["tree_steppe", "tree_forest", "tree_tundra", "tree_swamp"]:
                if 0 < obs.health < obs.max_health:
                    obs_tex = self.assets.textures.get("woodcut_stage_notched") or self.assets.textures.get(obs.obs_type)
                else:
                    obs_tex = self.assets.textures.get(obs.obs_type) or self.assets.textures.get("woodcut_stage_intact")
                draw_pos = (ox + obs.shake_offset - 24, oy - 70)
                sort_y = oy + 54  # tree base
                shadow_center = (ox + 32, oy + 50)
                shadow_size = (68, 24)
            elif obs.obs_type == "prop_bone":
                obs_tex = self.assets.textures.get("prop_bone")
                draw_pos = (ox + obs.shake_offset + 8, oy + 8)
                sort_y = oy + 32
                shadow_center = (ox + 32, oy + 32)
                shadow_size = (36, 14)
            elif obs.obs_type == "prop_mushroom":
                obs_tex = self.assets.textures.get(f"flora_mushroom_{var % 2}") or self.assets.textures.get("flora_mushroom")
                draw_pos = (ox + obs.shake_offset + 4, oy + 4)
                sort_y = oy + 30
                shadow_center = (ox + 28, oy + 30)
                shadow_size = (32, 12)
            elif obs.obs_type == "boulder":
                obs_tex = self.assets.textures.get("boulder")
                draw_pos = (ox + obs.shake_offset, oy + 4)
                sort_y = oy + 44
                shadow_center = (ox + 32, oy + 40)
                shadow_size = (54, 20)
            elif obs.obs_type == "rock_small":
                obs_tex = self.assets.textures.get("rock_small")
                draw_pos = (ox + obs.shake_offset + 6, oy + 8)
                sort_y = oy + 36
                shadow_center = (ox + 32, oy + 32)
                shadow_size = (34, 14)
            elif obs.obs_type == "tree_stump":
                obs_tex = self.assets.textures.get("woodcut_stage_stump") or self.assets.textures.get("tree_stump")
                draw_pos = (ox + obs.shake_offset + 2, oy + 4)
                sort_y = oy + 40
                shadow_center = (ox + 32, oy + 36)
                shadow_size = (46, 18)
            elif obs.obs_type in ["log", "branch_logs"]:
                obs_tex = self.assets.textures.get("woodcut_stage_logs") or self.assets.textures.get("log")
                draw_pos = (ox + obs.shake_offset + 4, oy + 6)
                sort_y = oy + 36
                shadow_center = (ox + 32, oy + 34)
                shadow_size = (54, 18)
            elif obs.obs_type == "weeds":
                obs_tex = self.assets.textures.get("weeds")
                draw_pos = (ox + obs.shake_offset + 2, oy + 4)
                sort_y = oy + 30
                shadow_center = (ox + 32, oy + 28)
                shadow_size = (28, 12)
            elif obs.obs_type == "branch":
                obs_tex = self.assets.textures.get("branch_wood") or self.assets.textures.get("branch")
                draw_pos = (ox + obs.shake_offset + 4, oy + 4)
                sort_y = oy + 28
                shadow_center = (ox + 28, oy + 30)
                shadow_size = (38, 14)
            elif obs.obs_type == "pebble":
                obs_tex = self.assets.textures.get("pebble")
                draw_pos = (ox + obs.shake_offset, oy)
                sort_y = oy + 28
                shadow_center = (ox + 32, oy + 32)
                shadow_size = (32, 12)
            elif obs.obs_type == "wild_bush":
                stg = getattr(obs, "growth_stage", "ripe")
                if stg == "sprout":
                    obs_tex = self.assets.textures.get(f"wild_bush_sprout_{var}") or self.assets.textures.get("wild_bush_sprout_0")
                elif stg == "depleted":
                    obs_tex = self.assets.textures.get(f"wild_bush_depleted_{var}") or self.assets.textures.get("wild_bush_depleted_0")
                else:
                    obs_tex = self.assets.textures.get(f"wild_bush_{var}") or self.assets.textures.get("wild_bush")
                draw_pos = (ox + obs.shake_offset + 2, oy + 2)
                sort_y = oy + 38
                shadow_center = (ox + 30, oy + 36)
                shadow_size = (44, 16)
            elif obs.obs_type == "clay_patch":
                obs_tex = self.assets.textures.get("clay_patch")
                draw_pos = (ox + obs.shake_offset, oy)
                sort_y = oy + 24
                shadow_center = (ox + 32, oy + 32)
                shadow_size = (36, 14)
            elif obs.obs_type == "copper_rock":
                obs_tex = self.assets.textures.get("copper_rock")
                draw_pos = (ox + obs.shake_offset, oy + 4)
                sort_y = oy + 42
                shadow_center = (ox + 32, oy + 40)
                shadow_size = (50, 18)
            else:
                obs_tex = self.assets.textures.get(obs.obs_type)
                draw_pos = (ox + obs.shake_offset, oy)
                sort_y = oy + 32
                shadow_center = (ox + 32, oy + 30)
                shadow_size = (32, 12)

            if obs_tex:
                def make_draw_obs(tex, pos, s_center, s_size):
                    def _draw():
                        s_pos = self.camera.apply_pos(s_center)
                        VisualEnhancer.draw_drop_shadow(self.screen, s_pos, s_size[0], s_size[1])
                        self.screen.blit(tex, self.camera.apply_pos(pos))
                    return _draw
                draw_queue.append((sort_y, make_draw_obs(obs_tex, draw_pos, shadow_center, shadow_size)))

        # 3. Animals & Ground Products (Farm Zone)
        if self.map_mgr.current_zone == ZONE_FARM:
            for gp in self.animals_mgr.ground_products:
                prod_id = gp["item"]["id"]
                prod_tex = self.assets.textures.get(f"prod_{prod_id}")
                if prod_tex:
                    gx, gy = gp["x"], gp["y"]
                    def make_draw_prod(tex, gx, gy):
                        def _draw():
                            VisualEnhancer.draw_drop_shadow(self.screen, self.camera.apply_pos((gx + 16, gy + 22)), 22, 10)
                            self.screen.blit(tex, self.camera.apply_pos((gx, gy)))
                        return _draw
                    draw_queue.append((gy + 16, make_draw_prod(prod_tex, gx, gy)))

            for anim in self.animals_mgr.animals:
                a_tex = self.assets.textures.get(f"{anim.animal_type}_{anim.anim_frame}")
                if a_tex:
                    if anim.direction == "left":
                        a_tex = pygame.transform.flip(a_tex, True, False)
                    ax, ay = anim.x, anim.y
                    def make_draw_anim(tex, an, ax, ay):
                        def _draw():
                            screen_pos = self.camera.apply_pos((ax, ay))
                            # Draw shadow at animal feet
                            if an.animal_type == "chicken":
                                shadow_pos = (screen_pos[0] + 22, screen_pos[1] + 34)
                                VisualEnhancer.draw_drop_shadow(self.screen, shadow_pos, 28, 12)
                            else:  # cow
                                shadow_pos = (screen_pos[0] + 39, screen_pos[1] + 64)
                                VisualEnhancer.draw_drop_shadow(self.screen, shadow_pos, 52, 16)
                            self.screen.blit(tex, screen_pos)
                            if an.heart_popup_timer > 0:
                                hx = screen_pos[0] + 16
                                hy = screen_pos[1] - 16 - int((2.0 - an.heart_popup_timer) * 10)
                                heart_alpha = min(255, int(an.heart_popup_timer * 200))
                                heart_surf = pygame.Surface((24, 24), pygame.SRCALPHA)
                                pygame.draw.circle(heart_surf, (240, 50, 80, heart_alpha // 3), (12, 12), 10)
                                pygame.draw.circle(heart_surf, (240, 50, 80, heart_alpha), (8, 8), 5)
                                pygame.draw.circle(heart_surf, (240, 50, 80, heart_alpha), (16, 8), 5)
                                pygame.draw.polygon(heart_surf, (240, 50, 80, heart_alpha), 
                                                   [(4, 10), (20, 10), (12, 20)])
                                pygame.draw.circle(heart_surf, (255, 150, 170, heart_alpha), (7, 6), 2)
                                self.screen.blit(heart_surf, (hx - 12, hy - 12))
                        return _draw
                    draw_queue.append((ay + 24, make_draw_anim(a_tex, anim, ax, ay)))

            # Tribal Villagers (Stone Age Population)
            for vil in self.tribe_mgr.villagers:
                def make_draw_vil(v):
                    def _draw():
                        v.draw(self.screen, self.camera, self.assets.fonts)
                    return _draw
                draw_queue.append((vil.y + 8, make_draw_vil(vil)))

            # Prehistoric Beasts & Apex Predators
            for beast in self.wildlife_mgr.beasts:
                col = int(beast.x // TILE_SIZE)
                row = int(beast.y // TILE_SIZE)
                if beast.is_dead:
                    if not self.fog_of_war.is_tile_explored(col, row):
                        continue
                else:
                    if not self.fog_of_war.is_tile_visible(col, row):
                        continue

                def make_draw_beast(b):
                    def _draw():
                        b.draw(self.screen, self.camera, self.assets.fonts)
                    return _draw
                draw_queue.append((beast.y + 12, make_draw_beast(beast)))

        else:
            # Town NPCs (Town Zone)
            for npc in self.map_mgr.npcs.values():
                npc_tex = self.assets.textures.get(f"npc_{npc.id}")
                if npc_tex:
                    nx, ny = npc.x, npc.y
                    def make_draw_npc(tex, n, nx, ny):
                        def _draw():
                            npc_pos = self.camera.apply_pos((nx, ny))
                            pw, ph = tex.get_size()
                            # Draw shadow at NPC feet
                            shadow_pos = (npc_pos[0] + 32, npc_pos[1] + 54)
                            VisualEnhancer.draw_drop_shadow(self.screen, shadow_pos, 36, 14)
                            self.screen.blit(tex, (npc_pos[0] + 32 - pw // 2, npc_pos[1] + 54 - ph + 4))
                            lbl = self.assets.fonts["tiny"].render(f"{n.name} [E]", True, (255, 255, 255))
                            lbg = pygame.Surface((lbl.get_width() + 6, 14), pygame.SRCALPHA)
                            pygame.draw.rect(lbg, (50, 35, 25, 200), (0, 0, lbg.get_width(), 14), border_radius=3)
                            self.screen.blit(lbg, (npc_pos[0] + 32 - lbg.get_width() // 2, npc_pos[1] + 54 - ph - 16))
                            self.screen.blit(lbl, (npc_pos[0] + 32 - lbl.get_width() // 2 + 1, npc_pos[1] + 54 - ph - 15))
                        return _draw
                    draw_queue.append((ny + 56, make_draw_npc(npc_tex, npc, nx, ny)))

        # Sort all items by sort_y (lower Y first, higher Y later -> foreground over background)
        draw_queue.sort(key=lambda item: item[0])

        for _, draw_fn in draw_queue:
            draw_fn()

    def _render_lighting(self):
        light_sources = []
        _, ambient_alpha = self.weather_sys.get_time_color_and_alpha(self.time_sys.hour, self.time_sys.minute)

        # Only cast night light sources when dusk or darkness falls
        if ambient_alpha >= 60:
            if self.map_mgr.current_zone == ZONE_FARM:
                # Primitive Campfire Warm Amber Night Light
                if self.primitive_structures.campfire_level > 0:
                    cf_light_pos = self.camera.apply_pos((
                        self.primitive_structures.campfire_pos[0] * TILE_SIZE + 32,
                        self.primitive_structures.campfire_pos[1] * TILE_SIZE + 32
                    ))
                    radius = 160 if self.primitive_structures.campfire_level >= 2 else 130
                    light_sources.append((cf_light_pos, radius))

                # Tribal Totem Sacred Spirit Aura
                if self.primitive_structures.totem_level > 0:
                    totem_light_pos = self.camera.apply_pos((
                        self.primitive_structures.totem_pos[0] * TILE_SIZE + 32,
                        self.primitive_structures.totem_pos[1] * TILE_SIZE + 32
                    ))
                    light_sources.append((totem_light_pos, 110))

                # Prehistoric Inukshuk Waypoint Glow
                waypoint_pos = self.camera.apply_pos((self.map_mgr.farm_waypoint[0] * TILE_SIZE + 32,
                                                      self.map_mgr.farm_waypoint[1] * TILE_SIZE + 32))
                light_sources.append((waypoint_pos, 90))
        else:
            # Town Square Streetlamps (All 8 Victorian iron street lamps around plaza)
            for lx, ly in getattr(self.assets, "town_lamp_positions", []):
                lamp_pos = self.camera.apply_pos((lx, ly - 28))
                light_sources.append((lamp_pos, 135))

            # Town Waypoint
            twp_pos = self.camera.apply_pos((self.map_mgr.town_waypoint[0] * TILE_SIZE + 32,
                                             self.map_mgr.town_waypoint[1] * TILE_SIZE + 32))
            light_sources.append((twp_pos, 110))

            # Shopfront Window Glows
            for sx in [14 * TILE_SIZE + 32, 35 * TILE_SIZE + 32, 25 * TILE_SIZE + 32]:
                sy = 14 * TILE_SIZE if sx != 25 * TILE_SIZE + 32 else 31 * TILE_SIZE
                shop_win = self.camera.apply_pos((sx, sy))
                light_sources.append((shop_win, 120))

        self.weather_sys.draw_lighting(self.screen, self.time_sys.hour, self.time_sys.minute, light_sources)

