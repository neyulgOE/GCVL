"""
Minimap & World Map View with Fast Travel / Teleportation for Green Valley Tales.
- Corner minimap showing real-time current zone overview
- 'M' key toggles World Map with multi-zone tabs (🌾 Nông Trại vs 🏘️ Thị Trấn)
- Fast Travel Teleportation buttons to instantly teleport between Farm and Town!
- Visual waypoint indicators with pulsing glow animations
"""

import pygame
import math
from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE,
    MAP_COLS, MAP_ROWS, WORLD_WIDTH, WORLD_HEIGHT
)

class MinimapSystem:
    # Corner minimap dimensions
    MINI_W = 160
    MINI_H = 128
    MINI_MARGIN = 12

    # Tile colors for minimap
    COLORS = {
        "grass": (145, 170, 80),
        "biome_steppe": (145, 170, 80),
        "biome_forest": (45, 95, 50),
        "biome_tundra": (220, 230, 240),
        "biome_highlands": (120, 110, 100),
        "biome_swamp": (60, 90, 70),
        "trail": (195, 165, 115),
        "bridge": (165, 125, 75),
        "water": (60, 130, 185),
        "dirt_tilled": (148, 100, 58),
        "dirt_watered": (100, 68, 38),
        "solid": (90, 70, 55),
        "farmable": (130, 190, 85),
        "cobble": (175, 168, 155),
        "stone_road": (185, 160, 130),
        "shelter": (90, 85, 80),
        "campfire": (255, 140, 25),
        "tree": (35, 80, 38),
        "boulder": (95, 90, 85),
        "bone": (235, 230, 210),
        "berry": (210, 50, 60),
        "obstacle": (130, 120, 110),
        "crop": (200, 180, 50),
        "player": (255, 60, 60),
        "animal": (255, 200, 100),
        "merchant": (200, 80, 200),
        "shipping_bin": (170, 110, 50),
        "house": (180, 140, 90),
        "barn": (165, 120, 75),
        "shop": (175, 105, 65),
        "waypoint": (80, 220, 255),
        "npc": (255, 140, 200)
    }

    def __init__(self):
        self.show_full_map = False
        self.viewing_zone = "macro"
        self._farm_surface = None
        self._town_surface = None
        self._dirty = True
        self._rebuild_timer = 0
        self._modal_alpha = 0.0

        # UI Rects
        self.btn_teleport_rect = pygame.Rect(0, 0, 0, 0)
        self.tab_farm_rect = pygame.Rect(0, 0, 0, 0)
        self.tab_town_rect = pygame.Rect(0, 0, 0, 0)
        self.tab_macro_rect = pygame.Rect(0, 0, 0, 0)
        self.tab_flora_rect = pygame.Rect(0, 0, 0, 0)
        self.close_btn_rect = pygame.Rect(0, 0, 0, 0)
        self._macro_map_surface = None
        self._flora_map_surface = None

    def toggle_full_map(self):
        self.show_full_map = not self.show_full_map

    def mark_dirty(self):
        self._dirty = True

    def update(self, dt):
        self._rebuild_timer += dt
        if self._rebuild_timer > 2.0:
            self._rebuild_timer = 0
            self._dirty = True

        target = 1.0 if self.show_full_map else 0.0
        diff = target - self._modal_alpha
        self._modal_alpha += diff * min(1.0, dt * 8.0)
        if abs(diff) < 0.01:
            self._modal_alpha = target

    # -------------------------------------------------------------
    # MAP SURFACE BUILDERS
    # -------------------------------------------------------------
    def _build_farm_surface(self, map_mgr, wildlife_mgr=None, fog_of_war=None):
        base = pygame.Surface((MAP_COLS, MAP_ROWS), pygame.SRCALPHA)
        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                t = map_mgr.terrain[r][c]
                if (c, r) in map_mgr.water_tiles or t == "water":
                    col = self.COLORS["water"]
                elif t in ["bridge_ford", "bridge_log"]:
                    col = self.COLORS["bridge"]
                elif t == "scree_talus":
                    col = self.COLORS["biome_highlands"]
                elif t == "forest_humus":
                    col = self.COLORS["biome_forest"]
                elif t == "riparian_mud":
                    col = self.COLORS["biome_swamp"]
                elif t == "point_bar_sand":
                    col = self.COLORS["trail"]
                elif t in ["biome_steppe", "steppe_meadow"]:
                    col = self.COLORS["biome_steppe"]
                elif t == "biome_tundra":
                    col = self.COLORS["biome_tundra"]
                else:
                    col = self.COLORS["grass"]
                base.set_at((c, r), col)

        # Obstacles & Flora
        for (c, r), obs in map_mgr.obstacles.items():
            if "tree" in obs.obs_type:
                base.set_at((c, r), self.COLORS["tree"])
            elif obs.obs_type in ["boulder", "rock_small", "copper_rock"]:
                base.set_at((c, r), self.COLORS["boulder"])
            elif obs.obs_type == "wild_bush":
                base.set_at((c, r), self.COLORS["berry"])
            else:
                base.set_at((c, r), self.COLORS["obstacle"])

        # Autonomous Prehistoric Wildlife
        if wildlife_mgr and hasattr(wildlife_mgr, "beasts"):
            for beast in wildlife_mgr.beasts:
                if not beast.is_dead:
                    bc = int(beast.x // TILE_SIZE)
                    br = int(beast.y // TILE_SIZE)
                    if 0 <= bc < MAP_COLS and 0 <= br < MAP_ROWS:
                        dot_col = (240, 80, 50) if beast.is_predator else (230, 200, 100)
                        base.set_at((bc, br), dot_col)

        # Mask unexplored tiles if fog of war enabled
        if fog_of_war and fog_of_war.is_enabled:
            for r in range(MAP_ROWS):
                for c in range(MAP_COLS):
                    if not fog_of_war.is_tile_explored(c, r):
                        base.set_at((c, r), (14, 12, 10))

        self._farm_surface = base
        self._town_surface = base

    # -------------------------------------------------------------
    # CORNER MINIMAP
    # -------------------------------------------------------------
    def draw_minimap(self, screen, map_mgr, animals_mgr, player, camera, fog_of_war=None):
        """Draw real-time corner minimap with Fog of War exploration mask."""
        self._rebuild_timer += 1
        if self._dirty or self._farm_surface is None or (self._rebuild_timer % 30 == 0):
            self._build_farm_surface(map_mgr, animals_mgr, fog_of_war)
            self._dirty = False

        surface = self._farm_surface if map_mgr.current_zone == "farm" else self._town_surface

        x = self.MINI_MARGIN
        y = SCREEN_HEIGHT - self.MINI_H - self.MINI_MARGIN - 60

        scaled = pygame.transform.scale(surface, (self.MINI_W, self.MINI_H))

        panel = pygame.Surface((self.MINI_W + 8, self.MINI_H + 28), pygame.SRCALPHA)
        pygame.draw.rect(panel, (20, 16, 12, 195), (0, 0, self.MINI_W + 8, self.MINI_H + 28), border_radius=6)
        screen.blit(panel, (x - 4, y - 24))

        # Zone Label tag
        zone_name = "Thế Giới Tiền Sử"
        font = pygame.font.SysFont("dejavusans", 11, bold=True)
        z_lbl = font.render(zone_name, True, (255, 235, 180))
        screen.blit(z_lbl, (x, y - 20))

        screen.blit(scaled, (x, y))

        # Viewport rectangle
        view_x = camera.offset_x / WORLD_WIDTH * self.MINI_W
        view_y = camera.offset_y / WORLD_HEIGHT * self.MINI_H
        view_w = SCREEN_WIDTH / WORLD_WIDTH * self.MINI_W
        view_h = SCREEN_HEIGHT / WORLD_HEIGHT * self.MINI_H
        pygame.draw.rect(screen, (255, 255, 255, 180),
                        (x + view_x, y + view_y, view_w, view_h), 1)

        # Viewport center or observer target dot
        if player:
            px = player.x / WORLD_WIDTH * self.MINI_W
            py = player.y / WORLD_HEIGHT * self.MINI_H
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 200.0)
            dot_size = int(2 + pulse * 2)
            pygame.draw.circle(screen, (100, 220, 255), (int(x + px), int(y + py)), dot_size)
            pygame.draw.circle(screen, (255, 255, 255), (int(x + px), int(y + py)), dot_size, 1)

        # Border
        pygame.draw.rect(screen, (100, 75, 50, 200), (x - 1, y - 1, self.MINI_W + 2, self.MINI_H + 2), 2, border_radius=3)

        # Prehistoric Animal Bone & Amber Minimap Frame
        if not hasattr(self, "_bone_frame") or self._bone_frame is None:
            import os
            for bf_path in [
                "assets/stone_age/07_ui_hud_and_tech_icons/03_hud_bone_amber_minimap_ring.png",
                "assets/ui/minimap_bone_frame.png",
                "stone_age_rts_complete_all_in_one_bundle/02_SLICED_SPRITES_128_PNG/07_ui_hud_and_tech_icons/03_hud_bone_amber_minimap_ring.png"
            ]:
                if os.path.exists(bf_path):
                    raw_bf = pygame.image.load(bf_path).convert_alpha()
                    self._bone_frame = pygame.transform.smoothscale(raw_bf, (self.MINI_W + 36, self.MINI_H + 36))
                    break

        if getattr(self, "_bone_frame", None):
            screen.blit(self._bone_frame, (x - 18, y - 18))

    # -------------------------------------------------------------
    # FULL-SCREEN MAP & FAST TRAVEL TELEPORTATION
    # -------------------------------------------------------------
    def draw_full_map(self, screen, map_mgr, animals_mgr, player, font_small, font_normal, font_large, fog_of_war=None):
        """Draw interactive full-screen map with Zone selection and Fast Travel Teleportation."""
        if self._modal_alpha < 0.01:
            return

        alpha = self._modal_alpha

        if self._dirty or self._farm_surface is None or self._town_surface is None:
            self._build_farm_surface(map_mgr, animals_mgr, fog_of_war)
            self._build_town_surface(map_mgr)
            self._dirty = False

        # Dim backdrop
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, int(170 * alpha)))
        screen.blit(dim, (0, 0))

        # Main Panel
        pw = 820
        ph = 560
        px = (SCREEN_WIDTH - pw) // 2
        py = (SCREEN_HEIGHT - ph) // 2

        # Shadow
        shadow = pygame.Surface((pw + 18, ph + 18), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, int(70 * alpha)), (0, 0, pw + 18, ph + 18), border_radius=16)
        screen.blit(shadow, (px - 9, py - 5))

        # Panel
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (244, 238, 222, int(250 * alpha)), (0, 0, pw, ph), border_radius=14)
        screen.blit(panel, (px, py))
        pygame.draw.rect(screen, (120, 85, 55, int(255 * alpha)), (px, py, pw, ph), 3, border_radius=14)

        # Title
        title_surf = font_large.render("BẢN ĐỒ ĐẠI LỤC HOANG DÃ THỜI TIỀN SỬ (PRIMEVAL CONTINENT EXPEDITION)", True, (45, 30, 18))
        screen.blit(title_surf, (px + (pw - title_surf.get_width()) // 2, py + 12))

        # Zone Tabs: [🗺️ ĐẠI LỤC TIỀN SỬ], [🏞️ THUNG LŨNG QUAN SÁT], [🌿 SINH THÁI THẢO MỘC]
        self.tab_macro_rect = pygame.Rect(px + 24, py + 48, 235, 32)
        self.tab_farm_rect = pygame.Rect(px + 269, py + 48, 235, 32)
        self.tab_flora_rect = pygame.Rect(px + 514, py + 48, 235, 32)
        self.tab_town_rect = pygame.Rect(0, 0, 0, 0)
        self.close_btn_rect = pygame.Rect(px + pw - 38, py + 12, 26, 26)

        is_view_macro = (self.viewing_zone == "macro")
        is_view_farm = (self.viewing_zone == "farm")
        is_view_flora = (self.viewing_zone == "flora")

        # Tab 1: Macro World Continent
        col_m = (110, 75, 45) if is_view_macro else (210, 195, 175)
        txt_m = (255, 255, 255) if is_view_macro else (90, 65, 40)
        pygame.draw.rect(screen, col_m, self.tab_macro_rect, border_radius=6)
        lbl_m = font_normal.render("🗺️ Đại Lục Tiền Sử (Atlas)", True, txt_m)
        screen.blit(lbl_m, (self.tab_macro_rect.x + (self.tab_macro_rect.w - lbl_m.get_width()) // 2, self.tab_macro_rect.y + 6))

        # Tab 2: Local River Valley
        col_f = (110, 75, 45) if is_view_farm else (210, 195, 175)
        txt_f = (255, 255, 255) if is_view_farm else (90, 65, 40)
        pygame.draw.rect(screen, col_f, self.tab_farm_rect, border_radius=6)
        lbl_f = font_normal.render("🏞️ Thung Lũng Quan Sát", True, txt_f)
        screen.blit(lbl_f, (self.tab_farm_rect.x + (self.tab_farm_rect.w - lbl_f.get_width()) // 2, self.tab_farm_rect.y + 6))

        # Tab 3: Botany & Foraging Atlas
        col_fl = (110, 75, 45) if is_view_flora else (210, 195, 175)
        txt_fl = (255, 255, 255) if is_view_flora else (90, 65, 40)
        pygame.draw.rect(screen, col_fl, self.tab_flora_rect, border_radius=6)
        lbl_fl = font_normal.render("🌿 Sinh Thái Thảo Mộc", True, txt_fl)
        screen.blit(lbl_fl, (self.tab_flora_rect.x + (self.tab_flora_rect.w - lbl_fl.get_width()) // 2, self.tab_flora_rect.y + 6))

        # Close [X]
        pygame.draw.rect(screen, (220, 60, 60), self.close_btn_rect, border_radius=5)
        x_lbl = font_small.render("X", True, (255, 255, 255))
        screen.blit(x_lbl, (self.close_btn_rect.x + 8, self.close_btn_rect.y + 4))

        # Map display area
        map_w = 756
        map_h = 360
        map_x = px + (pw - map_w) // 2
        map_y = py + 88

        if is_view_flora:
            # Render Prehistoric Flora & Foraging Atlas
            if not hasattr(self, "_flora_map_surface") or self._flora_map_surface is None:
                import os
                flora_atlas_path = "assets/sprites/stone_age_flora_foraging_atlas.png"
                if os.path.exists(flora_atlas_path):
                    raw_fa = pygame.image.load(flora_atlas_path).convert_alpha()
                    self._flora_map_surface = pygame.transform.smoothscale(raw_fa, (map_w, map_h))
                else:
                    self._flora_map_surface = pygame.Surface((map_w, map_h))
                    self._flora_map_surface.fill((40, 65, 45))

            screen.blit(self._flora_map_surface, (map_x, map_y))
            pygame.draw.rect(screen, (100, 75, 50), (map_x - 1, map_y - 1, map_w + 2, map_h + 2), 2)

        elif is_view_macro:
            # Render Prehistoric Overworld Macro Map
            if self._macro_map_surface is None:
                import os
                macro_path = "assets/sprites/world_overview_macro.png"
                if os.path.exists(macro_path):
                    raw_macro = pygame.image.load(macro_path).convert_alpha()
                    self._macro_map_surface = pygame.transform.smoothscale(raw_macro, (map_w, map_h))
                else:
                    self._macro_map_surface = pygame.Surface((map_w, map_h))
                    self._macro_map_surface.fill((80, 110, 70))

            screen.blit(self._macro_map_surface, (map_x, map_y))
            pygame.draw.rect(screen, (80, 60, 40), (map_x - 1, map_y - 1, map_w + 2, map_h + 2), 2)

            # Draw Spectator Camera Observation Point on Central Valley
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 160.0)
            spec_x = map_x + int(0.56 * map_w)
            spec_y = map_y + int(0.52 * map_h)

            glow_r = int(10 + pulse * 5)
            glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 215, 60, 80), (glow_r + 2, glow_r + 2), glow_r)
            screen.blit(glow_surf, (spec_x - glow_r - 2, spec_y - glow_r - 2))

            pygame.draw.circle(screen, (255, 230, 80), (spec_x, spec_y), 6)
            pygame.draw.circle(screen, (255, 255, 255), (spec_x, spec_y), 6, 2)

            spec_lbl = font_small.render("👁️ Vị Trí Quan Sát (Thung Lũng Sông)", True, (255, 255, 255))
            spec_tag = pygame.Surface((spec_lbl.get_width() + 10, 18), pygame.SRCALPHA)
            pygame.draw.rect(spec_tag, (24, 32, 45, 220), (0, 0, spec_tag.get_width(), 18), border_radius=4)
            pygame.draw.rect(spec_tag, (255, 215, 60, 200), (0, 0, spec_tag.get_width(), 18), 1, border_radius=4)
            screen.blit(spec_tag, (spec_x - spec_tag.get_width() // 2, spec_y - 24))
            screen.blit(spec_lbl, (spec_x - spec_lbl.get_width() // 2, spec_y - 23))

        else:
            active_surf = self._farm_surface if is_view_farm else self._town_surface
            scaled_map = pygame.transform.scale(active_surf, (map_w, map_h))
            screen.blit(scaled_map, (map_x, map_y))
            pygame.draw.rect(screen, (100, 75, 50), (map_x - 1, map_y - 1, map_w + 2, map_h + 2), 2)

            # Player / Observer marker (only if in the currently viewed zone)
            if map_mgr.current_zone == self.viewing_zone and player:
                pl_x = player.x / WORLD_WIDTH * map_w
                pl_y = player.y / WORLD_HEIGHT * map_h
                pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 150.0)

                # Glow ring
                glow_r = int(7 + pulse * 4)
                glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (255, 80, 80, 70), (glow_r + 2, glow_r + 2), glow_r)
                screen.blit(glow_surf, (int(map_x + pl_x) - glow_r - 2, int(map_y + pl_y) - glow_r - 2))

                pygame.draw.circle(screen, (255, 50, 50), (int(map_x + pl_x), int(map_y + pl_y)), 5)
                pygame.draw.circle(screen, (255, 255, 255), (int(map_x + pl_x), int(map_y + pl_y)), 5, 1)

                p_lbl = font_small.render("Bạn", True, (255, 255, 255))
                p_bg = pygame.Surface((p_lbl.get_width() + 8, 16), pygame.SRCALPHA)
                pygame.draw.rect(p_bg, (255, 50, 50, 200), (0, 0, p_bg.get_width(), 16), border_radius=3)
                screen.blit(p_bg, (int(map_x + pl_x) - p_bg.get_width() // 2, int(map_y + pl_y) - 22))
                screen.blit(p_lbl, (int(map_x + pl_x) - p_lbl.get_width() // 2, int(map_y + pl_y) - 21))

            # Waypoint Marker with pulsing cyan glow
            wp_pos = map_mgr.farm_waypoint if is_view_farm else map_mgr.town_waypoint
            wpx = wp_pos[0] / MAP_COLS * map_w
            wpy = wp_pos[1] / MAP_ROWS * map_h
            wp_pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180.0)

            wp_r = int(8 + wp_pulse * 4)
            wp_glow = pygame.Surface((wp_r * 2 + 4, wp_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(wp_glow, (80, 220, 255, 80), (wp_r + 2, wp_r + 2), wp_r)
            screen.blit(wp_glow, (int(map_x + wpx) - wp_r - 2, int(map_y + wpy) - wp_r - 2))

            pygame.draw.circle(screen, (60, 210, 255), (int(map_x + wpx), int(map_y + wpy)), 5)
            pygame.draw.circle(screen, (255, 255, 255), (int(map_x + wpx), int(map_y + wpy)), 5, 1)

            # Waypoint Label
            wp_name = "Cột Đá Tổ (Khai Hoang)" if is_view_farm else "Cột Đá Tổ (Bản Doanh)"
            wp_lbl = font_small.render(wp_name, True, (255, 255, 255))
            wp_tag = pygame.Surface((wp_lbl.get_width() + 10, 18), pygame.SRCALPHA)
            pygame.draw.rect(wp_tag, (110, 60, 30, 210), (0, 0, wp_tag.get_width(), 18), border_radius=4)
            screen.blit(wp_tag, (int(map_x + wpx) - wp_tag.get_width() // 2, int(map_y + wpy) + 10))
            screen.blit(wp_lbl, (int(map_x + wpx) - wp_lbl.get_width() // 2, int(map_y + wpy) + 11))

        # Bottom Bar: Biome Legend & Spectator Guidance
        legend_rect = pygame.Rect(px + 24, py + ph - 62, pw - 48, 36)
        pygame.draw.rect(screen, (32, 24, 18), legend_rect, border_radius=8)
        pygame.draw.rect(screen, (90, 70, 50), legend_rect, 1, border_radius=8)

        legend_text = "❄️ Núi Tuyết (Bắc)  |  🏜️ Sa Mạc Đất Đỏ (Tây-Nam)  |  🌲 Rừng Nguyên Sinh (Trung Tâm)  |  🍂 Cao Nguyên Thu (Đông-Bắc)"
        leg_surf = font_small.render(legend_text, True, (240, 230, 210))
        screen.blit(leg_surf, (legend_rect.x + (legend_rect.w - leg_surf.get_width()) // 2, legend_rect.y + 10))

        # Bottom tip
        tip_surf = font_small.render("[M] hoặc [ESC] để đóng bản đồ", True, (130, 100, 70))
        screen.blit(tip_surf, (px + pw - tip_surf.get_width() - 24, py + ph - 22))

    # -------------------------------------------------------------
    # EVENT HANDLING
    # -------------------------------------------------------------
    def handle_mouse_down(self, pos, button, map_mgr):
        """
        Handles mouse clicks on Full Map:
        """
        if not self.show_full_map or self._modal_alpha < 0.8:
            return None

        if button != 1:
            return None

        # Close button
        if self.close_btn_rect.collidepoint(pos):
            self.show_full_map = False
            return None

        # Tab Macro Continent
        if hasattr(self, "tab_macro_rect") and self.tab_macro_rect.collidepoint(pos):
            self.viewing_zone = "macro"
            return None

        # Tab Local Valley
        if self.tab_farm_rect.collidepoint(pos):
            self.viewing_zone = "farm"
            return None

        # Tab Flora Ecology Atlas
        if hasattr(self, "tab_flora_rect") and self.tab_flora_rect.collidepoint(pos):
            self.viewing_zone = "flora"
            return None

        return None
