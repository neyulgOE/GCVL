"""
Minimap & Overworld Atlas for Stone Age: Primeval World.
- Real-time natural terrain & wildlife tracking minimap with prehistoric frame
- 'M' key toggles Full Continent Atlas with biome exploration
- Autonomous megafauna wildlife markers and free spectator camera tracking
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

    # Tile colors for natural minimap
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
        "solid": (90, 70, 55),
        "tree": (35, 80, 38),
        "boulder": (95, 90, 85),
        "bone": (235, 230, 210),
        "berry": (210, 50, 60),
        "obstacle": (130, 120, 110),
        "animal": (255, 200, 100),
        "waypoint": (80, 220, 255)
    }

    def __init__(self):
        self.show_full_map = False
        self.viewing_zone = "macro"
        self._valley_surface = None
        self._dirty = True
        self._rebuild_timer = 0
        self._modal_alpha = 0.0

        # UI Rects
        self.tab_macro_rect = pygame.Rect(0, 0, 0, 0)
        self.tab_valley_rect = pygame.Rect(0, 0, 0, 0)
        self.tab_flora_rect = pygame.Rect(0, 0, 0, 0)
        self.close_btn_rect = pygame.Rect(0, 0, 0, 0)
        self._macro_map_surface = None
        self._flora_map_surface = None
        self._bone_frame = None

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
    def _build_valley_surface(self, map_mgr, wildlife_mgr=None, fog_of_war=None):
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

        self._valley_surface = base

    # -------------------------------------------------------------
    # CORNER MINIMAP
    # -------------------------------------------------------------
    def draw_minimap(self, screen, map_mgr, wildlife_mgr, spectator_pos, camera, fog_of_war=None):
        """Draw real-time corner minimap with Fog of War exploration mask."""
        self._rebuild_timer += 1
        if self._dirty or self._valley_surface is None or (self._rebuild_timer % 30 == 0):
            self._build_valley_surface(map_mgr, wildlife_mgr, fog_of_war)
            self._dirty = False

        surface = self._valley_surface
        mini_size = 144
        x = self.MINI_MARGIN
        y = SCREEN_HEIGHT - mini_size - self.MINI_MARGIN - 50

        scaled = pygame.transform.scale(surface, (mini_size, mini_size))

        # Circular mask to match the amber bone ring
        circle_surf = pygame.Surface((mini_size, mini_size), pygame.SRCALPHA)
        pygame.draw.circle(circle_surf, (255, 255, 255, 255), (mini_size // 2, mini_size // 2), mini_size // 2 - 2)
        circle_surf.blit(scaled, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        # Background disc
        pygame.draw.circle(screen, (16, 22, 28, 220), (x + mini_size // 2, y + mini_size // 2), mini_size // 2 + 3)
        screen.blit(circle_surf, (x, y))

        # Region Label tag
        region_name = "Thế Giới Tiền Sử"
        font = pygame.font.SysFont("dejavusans", 11, bold=True)
        z_lbl = font.render(region_name, True, (255, 235, 180))
        tag_bg = pygame.Surface((z_lbl.get_width() + 12, 18), pygame.SRCALPHA)
        pygame.draw.rect(tag_bg, (18, 24, 32, 210), (0, 0, tag_bg.get_width(), 18), border_radius=4)
        pygame.draw.rect(tag_bg, (160, 130, 80, 180), (0, 0, tag_bg.get_width(), 18), 1, border_radius=4)
        screen.blit(tag_bg, (x + (mini_size - tag_bg.get_width()) // 2, y - 24))
        screen.blit(z_lbl, (x + (mini_size - z_lbl.get_width()) // 2, y - 23))

        # Viewport indicator
        view_x = camera.offset_x / WORLD_WIDTH * mini_size
        view_y = camera.offset_y / WORLD_HEIGHT * mini_size
        view_w = max(6, SCREEN_WIDTH / WORLD_WIDTH * mini_size)
        view_h = max(6, SCREEN_HEIGHT / WORLD_HEIGHT * mini_size)
        pygame.draw.rect(screen, (255, 255, 255, 200),
                        (x + view_x, y + view_y, view_w, view_h), 1)

        # Observer spectator dot
        if spectator_pos:
            px_dot = spectator_pos.x / WORLD_WIDTH * mini_size
            py_dot = spectator_pos.y / WORLD_HEIGHT * mini_size
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 200.0)
            dot_size = int(3 + pulse * 2)
            pygame.draw.circle(screen, (100, 220, 255), (int(x + px_dot), int(y + py_dot)), dot_size)
            pygame.draw.circle(screen, (255, 255, 255), (int(x + px_dot), int(y + py_dot)), dot_size, 1)

        # Prehistoric Amber Bone Ring Frame
        if self._bone_frame is None:
            import os
            for bf_path in [
                "assets/stone_age/07_ui_hud_and_tech_icons/03_hud_bone_amber_minimap_ring.png",
                "assets/ui/minimap_bone_frame.png",
                "stone_age_rts_complete_all_in_one_bundle/02_SLICED_SPRITES_128_PNG/07_ui_hud_and_tech_icons/03_hud_bone_amber_minimap_ring.png"
            ]:
                if os.path.exists(bf_path):
                    raw_bf = pygame.image.load(bf_path).convert_alpha()
                    self._bone_frame = pygame.transform.smoothscale(raw_bf, (mini_size + 24, mini_size + 24))
                    break

        if self._bone_frame:
            screen.blit(self._bone_frame, (x - 12, y - 12))

    # -------------------------------------------------------------
    # FULL-SCREEN MAP
    # -------------------------------------------------------------
    def draw_full_map(self, screen, map_mgr, wildlife_mgr, spectator_pos, font_small, font_normal, font_large, fog_of_war=None):
        """Draw interactive full-screen map with Overworld Atlas exploration."""
        if self._modal_alpha < 0.01:
            return

        alpha = self._modal_alpha

        if self._dirty or self._valley_surface is None:
            self._build_valley_surface(map_mgr, wildlife_mgr, fog_of_war)
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

        # Tabs: [🗺️ ĐẠI LỤC TIỀN SỬ], [🏞️ THUNG LŨNG QUAN SÁT], [🌿 SINH THÁI THẢO MỘC]
        self.tab_macro_rect = pygame.Rect(px + 24, py + 48, 235, 32)
        self.tab_valley_rect = pygame.Rect(px + 269, py + 48, 235, 32)
        self.tab_flora_rect = pygame.Rect(px + 514, py + 48, 235, 32)
        self.close_btn_rect = pygame.Rect(px + pw - 38, py + 12, 26, 26)

        is_view_macro = (self.viewing_zone == "macro")
        is_view_valley = (self.viewing_zone == "valley")
        is_view_flora = (self.viewing_zone == "flora")

        # Tab 1: Macro World Continent
        col_m = (110, 75, 45) if is_view_macro else (210, 195, 175)
        txt_m = (255, 255, 255) if is_view_macro else (90, 65, 40)
        pygame.draw.rect(screen, col_m, self.tab_macro_rect, border_radius=6)
        lbl_m = font_normal.render("🗺️ Đại Lục Tiền Sử (Atlas)", True, txt_m)
        screen.blit(lbl_m, (self.tab_macro_rect.x + (self.tab_macro_rect.w - lbl_m.get_width()) // 2, self.tab_macro_rect.y + 6))

        # Tab 2: Local River Valley
        col_v = (110, 75, 45) if is_view_valley else (210, 195, 175)
        txt_v = (255, 255, 255) if is_view_valley else (90, 65, 40)
        pygame.draw.rect(screen, col_v, self.tab_valley_rect, border_radius=6)
        lbl_v = font_normal.render("🏞️ Thung Lũng Quan Sát", True, txt_v)
        screen.blit(lbl_v, (self.tab_valley_rect.x + (self.tab_valley_rect.w - lbl_v.get_width()) // 2, self.tab_valley_rect.y + 6))

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
        if is_view_macro:
            # Keep 1:1 true square aspect ratio for the continent map
            map_size = 440
            map_w = map_size
            map_h = map_size
            map_x = px + 24
            map_y = py + 92
        else:
            map_w = 756
            map_h = 360
            map_x = px + (pw - map_w) // 2
            map_y = py + 88

        if is_view_flora:
            # Render Prehistoric Flora & Foraging Atlas
            if self._flora_map_surface is None:
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
            # Render Prehistoric Overworld Macro Map in crisp 1:1 square
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
            pygame.draw.rect(screen, (70, 52, 34), (map_x - 2, map_y - 2, map_w + 4, map_h + 4), 2)

            # Side Info Panel: Continental Expedition Field Log
            info_x = map_x + map_w + 16
            info_w = pw - map_w - 56
            info_h = map_h

            info_bg = pygame.Surface((info_w, info_h), pygame.SRCALPHA)
            pygame.draw.rect(info_bg, (18, 28, 42, 235), (0, 0, info_w, info_h), border_radius=8)
            pygame.draw.rect(info_bg, (195, 175, 130, 180), (0, 0, info_w, info_h), 2, border_radius=8)
            screen.blit(info_bg, (info_x, info_y := map_y))

            # Header
            t_title = font_normal.render("ĐẠI LỤC NGUYÊN SINH", True, (245, 230, 175))
            screen.blit(t_title, (info_x + 14, info_y + 12))
            t_sub = font_small.render("Thế Giới Tự Nhiên Tiền Sử Hoàn Chỉnh", True, (160, 215, 240))
            screen.blit(t_sub, (info_x + 14, info_y + 32))
            pygame.draw.line(screen, (140, 125, 95), (info_x + 14, info_y + 50), (info_x + info_w - 14, info_y + 50), 1)

            # Camera World Coordinates
            if spectator_pos:
                cam_x_tile = int(spectator_pos.x // TILE_SIZE)
                cam_y_tile = int(spectator_pos.y // TILE_SIZE)
                cam_txt = f"Vị trí quan sát: Ô [{cam_x_tile}, {cam_y_tile}]"
            else:
                cam_txt = "Vị trí quan sát: [Thung Lũng Trung Tâm]"
            t_cam = font_small.render(cam_txt, True, (230, 240, 245))
            screen.blit(t_cam, (info_x + 14, info_y + 58))

            # Territory List
            t_ter_title = font_small.render("CÁC VÙNG SINH THÁI ĐẠI LỤC:", True, (255, 215, 100))
            screen.blit(t_ter_title, (info_x + 14, info_y + 82))

            biomes_desc = [
                ("❄️ Dãy Băng Sơn (Ma Mút)", "Đỉnh tuyết vĩnh cửu & hồ băng"),
                ("🌲 Rừng Nhiệt Đới Nguyên Sinh", "Tán rừng rậm rạp & hổ răng kiếm"),
                ("🦌 Thung Lũng Hươu Khổng Lồ", "Lưu vực sông ngòi & bãi bồi"),
                ("🏜️ Hoang Mạc Cát Đỏ", "Cồn cát vàng & đàn Bison cổ đại"),
                ("🌾 Cao Nguyên Hoàng Thổ", "Rừng lá vàng & vách đá dốc"),
                ("🐊 Châu Thổ Đầm Lầy", "Cửa sông phù sa & thủy quái cổ"),
                ("🏝️ Đảo Tiền Tiêu Đông Nam", "Khu bảo tồn động vật hoang dã"),
            ]

            for idx, (b_name, b_sub) in enumerate(biomes_desc):
                by = info_y + 104 + idx * 42
                t_bname = font_small.render(b_name, True, (240, 245, 250))
                t_bsub = font_small.render(f"  • {b_sub}", True, (175, 195, 205))
                screen.blit(t_bname, (info_x + 14, by))
                screen.blit(t_bsub, (info_x + 14, by + 16))

            # Footer tip
            t_tip = font_small.render("[WASD] Bay quan sát | [M] Đóng Atlas", True, (200, 220, 200))
            screen.blit(t_tip, (info_x + 14, info_y + info_h - 26))

            # Dynamic Spectator Position Pin on Macro Map
            if spectator_pos:
                spec_norm_x = max(0.0, min(1.0, spectator_pos.x / max(1.0, float(WORLD_WIDTH))))
                spec_norm_y = max(0.0, min(1.0, spectator_pos.y / max(1.0, float(WORLD_HEIGHT))))
            else:
                spec_norm_x = 0.52
                spec_norm_y = 0.44

            spec_x = map_x + int(spec_norm_x * map_w)
            spec_y = map_y + int(spec_norm_y * map_h)

            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 160.0)
            glow_r = int(10 + pulse * 5)
            glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 215, 60, 90), (glow_r + 2, glow_r + 2), glow_r)
            screen.blit(glow_surf, (spec_x - glow_r - 2, spec_y - glow_r - 2))

            pygame.draw.circle(screen, (255, 230, 80), (spec_x, spec_y), 6)
            pygame.draw.circle(screen, (255, 255, 255), (spec_x, spec_y), 6, 2)

            spec_lbl = font_small.render("👁️ Bạn đang ở đây", True, (255, 255, 255))
            spec_tag = pygame.Surface((spec_lbl.get_width() + 10, 18), pygame.SRCALPHA)
            pygame.draw.rect(spec_tag, (24, 32, 45, 220), (0, 0, spec_tag.get_width(), 18), border_radius=4)
            pygame.draw.rect(spec_tag, (255, 215, 60, 200), (0, 0, spec_tag.get_width(), 18), 1, border_radius=4)
            screen.blit(spec_tag, (spec_x - spec_tag.get_width() // 2, spec_y - 24))
            screen.blit(spec_lbl, (spec_x - spec_lbl.get_width() // 2, spec_y - 23))

        else:
            scaled_map = pygame.transform.scale(self._valley_surface, (map_w, map_h))
            screen.blit(scaled_map, (map_x, map_y))
            pygame.draw.rect(screen, (100, 75, 50), (map_x - 1, map_y - 1, map_w + 2, map_h + 2), 2)

            # Observer spectator marker
            if spectator_pos:
                pl_x = spectator_pos.x / WORLD_WIDTH * map_w
                pl_y = spectator_pos.y / WORLD_HEIGHT * map_h
                pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 150.0)

                glow_r = int(7 + pulse * 4)
                glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (80, 180, 255, 80), (glow_r + 2, glow_r + 2), glow_r)
                screen.blit(glow_surf, (int(map_x + pl_x) - glow_r - 2, int(map_y + pl_y) - glow_r - 2))

                pygame.draw.circle(screen, (80, 200, 255), (int(map_x + pl_x), int(map_y + pl_y)), 5)
                pygame.draw.circle(screen, (255, 255, 255), (int(map_x + pl_x), int(map_y + pl_y)), 5, 1)

                p_lbl = font_small.render("Camera", True, (255, 255, 255))
                p_bg = pygame.Surface((p_lbl.get_width() + 8, 16), pygame.SRCALPHA)
                pygame.draw.rect(p_bg, (40, 100, 160, 200), (0, 0, p_bg.get_width(), 16), border_radius=3)
                screen.blit(p_bg, (int(map_x + pl_x) - p_bg.get_width() // 2, int(map_y + pl_y) - 22))
                screen.blit(p_lbl, (int(map_x + pl_x) - p_lbl.get_width() // 2, int(map_y + pl_y) - 21))

            # Prehistoric Natural Monolith Marker
            wpx = 40.0 / MAP_COLS * map_w
            wpy = 38.0 / MAP_ROWS * map_h
            wp_pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180.0)

            wp_r = int(8 + wp_pulse * 4)
            wp_glow = pygame.Surface((wp_r * 2 + 4, wp_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(wp_glow, (80, 220, 255, 80), (wp_r + 2, wp_r + 2), wp_r)
            screen.blit(wp_glow, (int(map_x + wpx) - wp_r - 2, int(map_y + wpy) - wp_r - 2))

            pygame.draw.circle(screen, (60, 210, 255), (int(map_x + wpx), int(map_y + wpy)), 5)
            pygame.draw.circle(screen, (255, 255, 255), (int(map_x + wpx), int(map_y + wpy)), 5, 1)

            # Marker Label
            wp_name = "Cột Đá Tổ Tiền Sử"
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
        Handles mouse clicks on Full Map tabs:
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
        if hasattr(self, "tab_valley_rect") and self.tab_valley_rect.collidepoint(pos):
            self.viewing_zone = "valley"
            return None

        # Tab Flora Ecology Atlas
        if hasattr(self, "tab_flora_rect") and self.tab_flora_rect.collidepoint(pos):
            self.viewing_zone = "flora"
            return None

        return None
