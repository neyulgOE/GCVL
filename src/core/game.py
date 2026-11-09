"""
Main Game Coordinator for Stone Age Nature Observation Simulator.
A pure prehistoric natural world simulation featuring free spectator camera,
dynamic weather & seasons, procedural river hydraulics, and autonomous prehistoric wildlife.
"""

import pygame
import sys
import math
import random
from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TITLE, FPS, TILE_SIZE,
    WORLD_WIDTH, WORLD_HEIGHT
)
from src.core.assets import AssetManager
from src.core.camera import Camera
from src.core.free_camera import FreeCamera
from src.world.time_system import TimeSystem
from src.world.weather_system import WeatherSystem
from src.world.map_manager import MapManager, ZONE_FARM
from src.world.particle_system import ParticleSystem
from src.world.wildlife_manager import WildlifeManager
from src.world.fog_of_war import FogOfWar
from src.ui.dialog import DialogManager
from src.ui.minimap import MinimapSystem
from src.core.visual_enhancer import VisualEnhancer


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(f"{TITLE} - Thế Giới Tự Nhiên Thời Đồ Đá")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_time = 0.0

        # Core Assets & Subsystems
        self.assets = AssetManager.get()
        self.camera = Camera()
        # Free Spectator Camera centered around central prehistoric river valley
        self.free_cam = FreeCamera(self.camera, start_x=40.0 * 64.0, start_y=38.0 * 64.0)
        self.time_sys = TimeSystem()
        self.weather_sys = WeatherSystem()
        self.map_mgr = MapManager()
        self.particle_sys = ParticleSystem()

        # Wildlife & Ecosystem
        self.wildlife_mgr = WildlifeManager()
        self.fog_of_war = FogOfWar()
        # In nature observation mode, entire continent is revealed
        self.fog_of_war.is_enabled = False

        # UI & Minimap
        self.dialog_mgr = DialogManager(self.assets)
        self.minimap = MinimapSystem()

        # Welcome guidance
        self.dialog_mgr.add_toast("🌿 Thế Giới Tự Nhiên Tiền Sử: [WASD]/[Mũi tên] Di chuyển | Giữ [Shift] Bay nhanh | [M] Bản đồ | [F1] Trợ giúp")

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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            # Camera panning (mouse drag / key controls)
            if self.free_cam.handle_event(event):
                continue

            # Full Map View Mouse Handling
            if self.minimap.show_full_map and event.type == pygame.MOUSEBUTTONDOWN:
                self.minimap.handle_mouse_down(event.pos, event.button, self.map_mgr)
                continue

            # Keyboard Shortcuts
            if event.type == pygame.KEYDOWN:
                # Toggle Full Map (M)
                if event.key == pygame.K_m:
                    self.minimap.viewing_zone = self.map_mgr.current_zone
                    self.minimap.toggle_full_map()
                    continue

                # Toggle Help Guide (F1)
                if event.key == pygame.K_F1:
                    self.dialog_mgr.show_help = not self.dialog_mgr.show_help
                    continue

                # Close any overlay with ESC
                if event.key == pygame.K_ESCAPE:
                    if self.minimap.show_full_map:
                        self.minimap.show_full_map = False
                    elif self.dialog_mgr.show_help:
                        self.dialog_mgr.show_help = False
                    continue

    # -------------------------------------------------------------
    # UPDATE LOOP
    # -------------------------------------------------------------
    def update(self, dt):
        self.dialog_mgr.update(dt)
        self.game_time = getattr(self, "game_time", 0.0) + dt
        self.particle_sys.update(dt)
        self.free_cam.update(dt)
        self.minimap.update(dt)

        # Screen shake from storm/earth tremors
        self.camera.set_shake(self.weather_sys.screen_shake_x, self.weather_sys.screen_shake_y)

        # Nature time advancement
        self.time_sys.update(dt)

        # Dynamic Weather & Climate
        self.weather_sys.update(dt)

        # Ambient particles (leaves, pollen, fireflies, snow)
        is_night = (self.time_sys.hour >= 19 or self.time_sys.hour < 5)
        self.particle_sys.update_ambient(dt, self.time_sys.season_id, self.weather_sys.weather, is_night)

        # River & Map water animation
        self.map_mgr.update(dt)

        # Prehistoric Wildlife simulation
        self.wildlife_mgr.update(dt, [], None, None)

    # -------------------------------------------------------------
    # RENDER LOOP
    # -------------------------------------------------------------
    def render(self):
        self.screen.fill((18, 14, 22))

        # 1. Natural Terrain & River Course
        self._render_terrain()

        # 2. Y-Sorted World Entities (Flora, Boulders, Wildlife)
        self._render_ysorted_entities()

        # 3. World-Space Particles
        self.particle_sys.draw_world(
            self.screen,
            self.camera.offset_x + self.camera.shake_x,
            self.camera.offset_y + self.camera.shake_y
        )

        # 4. Weather Particles
        self.weather_sys.draw_weather(self.screen)

        # 5. Ambient Screen Particles
        self.particle_sys.draw_screen(self.screen)

        # 6. Atmospheric Lighting & Day/Night Gradient
        self._render_lighting()

        # 7. Spectator Information Overlay
        self._render_nature_overlay()

        # 8. Corner Minimap
        if not self.minimap.show_full_map:
            self.minimap.draw_minimap(
                self.screen, self.map_mgr, self.wildlife_mgr,
                self.free_cam.target, self.camera, self.fog_of_war
            )

        # 9. Dialog / Toasts
        self.dialog_mgr.draw(self.screen)

        # 10. Full Map View (over world)
        if self.minimap._modal_alpha > 0.01:
            self.minimap.draw_full_map(
                self.screen, self.map_mgr, None,
                self.free_cam.target, self.assets.fonts["small"],
                self.assets.fonts["normal"], self.assets.fonts["large"],
                self.fog_of_war
            )

        pygame.display.flip()

    def _render_nature_overlay(self):
        """Minimalist, elegant spectator badge displaying Time, Season, Weather & Camera location."""
        season_names = {
            "spring": "Mùa Xuân (Sinh Sôi)",
            "summer": "Mùa Hạ (Trù Phú)",
            "fall": "Mùa Thu (Thu Hoạch)",
            "winter": "Mùa Đông (Băng Giá)"
        }
        weather_names = {
            "sunny": "Nắng Ấm ☀️",
            "rain": "Mưa Rào 🌧️",
            "storm": "Bão Tố ⚡",
            "snow": "Tuyết Rơi ❄️"
        }
        s_name = season_names.get(self.time_sys.season_id, self.time_sys.season_id.title())
        w_name = weather_names.get(self.weather_sys.weather, self.weather_sys.weather.title())
        time_str = f"Năm {self.time_sys.year} - {s_name} - Ngày {self.time_sys.day:02d} | {self.time_sys.hour:02d}:{self.time_sys.minute:02d}"

        font = self.assets.fonts["small"]
        t_surf = font.render(time_str, True, (245, 240, 225))
        w_surf = font.render(f"Khí hậu: {w_name}", True, (215, 235, 255))
        cam_col = int(self.free_cam.target.x // TILE_SIZE)
        cam_row = int(self.free_cam.target.y // TILE_SIZE)
        coord_surf = self.assets.fonts["tiny"].render(f"Tọa độ Camera: [{cam_col}, {cam_row}] (Tự do)", True, (180, 195, 175))

        pad = 10
        bw = max(t_surf.get_width(), w_surf.get_width(), coord_surf.get_width()) + pad * 2
        bh = 66
        bx = SCREEN_WIDTH - bw - 14
        by = 12

        badge = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(badge, (22, 18, 14, 195), (0, 0, bw, bh), border_radius=8)
        pygame.draw.rect(badge, (110, 90, 65, 180), (0, 0, bw, bh), 1, border_radius=8)
        self.screen.blit(badge, (bx, by))

        self.screen.blit(t_surf, (bx + pad, by + 6))
        self.screen.blit(w_surf, (bx + pad, by + 26))
        self.screen.blit(coord_surf, (bx + pad, by + 46))

    def _render_terrain(self):
        """Renders 5 soil horizons, terraced rock cliffs, and organic meandering river."""
        ts = TILE_SIZE
        start_col = max(0, int(self.camera.offset_x // ts))
        end_col = min(self.map_mgr.cols, int((self.camera.offset_x + SCREEN_WIDTH) // ts) + 2)
        start_row = max(0, int(self.camera.offset_y // ts))
        end_row = min(self.map_mgr.rows, int((self.camera.offset_y + SCREEN_HEIGHT) // ts) + 2)

        # 1. Base Ground Horizons
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
                elif t_type in ("point_bar_sand", "water", "bridge_ford", "bridge_log"):
                    base_tex = self.assets.textures.get("point_bar_sand") or self.assets.textures.get("pebble_shore")
                else:
                    base_tex = (self.assets.textures.get(f"biome_steppe_{h}") or
                                self.assets.textures.get("steppe_meadow") or
                                self.assets.textures.get("biome_steppe"))

                if base_tex:
                    self.screen.blit(base_tex, screen_pos)

        # 2. 2.5D Terraced Cliff Facings & Shading
        cliff_s = self.assets.textures.get("cliff_face_south")
        cliff_tall = self.assets.textures.get("cliff_face_south_tall")
        cliff_e = self.assets.textures.get("cliff_edge_east")
        cliff_w = self.assets.textures.get("cliff_edge_west")

        c_start_row = max(0, start_row - 1)
        c_end_row = min(self.map_mgr.rows, end_row + 1)
        for r in range(c_start_row, c_end_row):
            for c in range(start_col, end_col):
                if cliff_e and self.map_mgr.farm_cliff_east[r][c] > 0:
                    e_sx = c * ts + ts - 16 - self.camera.offset_x
                    e_sy = r * ts - self.camera.offset_y
                    self.screen.blit(cliff_e, (e_sx, e_sy))

                if cliff_w and self.map_mgr.farm_cliff_west[r][c] > 0:
                    w_sx = c * ts - self.camera.offset_x
                    w_sy = r * ts - self.camera.offset_y
                    self.screen.blit(cliff_w, (w_sx, w_sy))

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

        # 3. Smooth Continuous Organic River Course, Riparian Pebble Shoreline & Wave VFX
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
            point_bar_deposit = 58.0 * math.exp(-((row_f - 39.0) ** 2) / 64.0)
            bw_l = 36.0 + 8.0 * math.sin(row_f * 0.75 + 1.2) + point_bar_deposit
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

        min_xl = min(p[0] for p in pts_beach_fade_l)
        max_xr = max(p[0] for p in pts_beach_fade_r)
        if min_xl < SCREEN_WIDTH + 80 and max_xr > -80:
            river_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

            # Shoreline feathering
            poly_fade_l = pts_beach_fade_l + list(reversed(pts_beach_outer_l))
            pygame.draw.polygon(river_surf, (198, 185, 142, 110), poly_fade_l)

            poly_fade_r = pts_beach_outer_r + list(reversed(pts_beach_fade_r))
            pygame.draw.polygon(river_surf, (198, 185, 142, 110), poly_fade_r)

            # Main pebble beach & point bar
            poly_beach_l = pts_beach_outer_l + list(reversed(pts_l))
            pygame.draw.polygon(river_surf, (216, 202, 164, 255), poly_beach_l)

            poly_beach_r = pts_r + list(reversed(pts_beach_outer_r))
            pygame.draw.polygon(river_surf, (192, 178, 140, 255), poly_beach_r)

            # Scattered smooth river pebbles
            for sy in range(view_top, view_bottom, 24):
                wy = self.camera.offset_y + sy
                row_f = wy / float(ts)
                rc = self.map_mgr.get_river_center_float(row_f) * ts + 32.0
                hw = self.map_mgr.get_river_half_width_float(row_f) * ts
                s_xl = rc - hw - self.camera.offset_x
                s_xr = rc + hw - self.camera.offset_x
                point_bar_deposit = 58.0 * math.exp(-((row_f - 39.0) ** 2) / 64.0)
                bw_l = 36.0 + 8.0 * math.sin(row_f * 0.75 + 1.2) + point_bar_deposit
                bw_r = max(18.0, 34.0 + 8.0 * math.cos(row_f * 0.65))

                plx = int(s_xl - bw_l * 0.55 + 5.0 * math.sin(wy * 0.13))
                pygame.draw.circle(river_surf, (145, 130, 95, 190), (plx, sy), 3)
                pygame.draw.circle(river_surf, (215, 200, 160, 210), (plx + 1, sy - 1), 1)

                prx = int(s_xr + bw_r * 0.55 + 5.0 * math.cos(wy * 0.15))
                pygame.draw.circle(river_surf, (145, 130, 95, 190), (prx, sy), 3)
                pygame.draw.circle(river_surf, (215, 200, 160, 210), (prx + 1, sy - 1), 1)

            # Deep River Channel
            poly_deep = pts_l + list(reversed(pts_r))
            pygame.draw.polygon(river_surf, (37, 104, 143, 245), poly_deep)

            # Shallow Shoreline Bands
            poly_sh_l = pts_l + list(reversed(pts_sh_l))
            pygame.draw.polygon(river_surf, (72, 162, 192, 160), poly_sh_l)

            poly_sh_r = pts_sh_r + list(reversed(pts_r))
            pygame.draw.polygon(river_surf, (72, 162, 192, 160), poly_sh_r)

            # Flowing Specular Caustics
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

            # Shoreline Wave Foam
            if len(foam_l) >= 2:
                pygame.draw.lines(river_surf, (235, 248, 255, 215), False, foam_l, 2)
            if len(foam_r) >= 2:
                pygame.draw.lines(river_surf, (235, 248, 255, 215), False, foam_r, 2)

            self.screen.blit(river_surf, (0, 0))

        # 4. Natural River Stepping Stone Ford at r=36
        r36_sy = int(36 * ts + 32 - self.camera.offset_y)
        if -80 <= r36_sy <= SCREEN_HEIGHT + 80:
            rc_36 = self.map_mgr.get_river_center_float(36.0) * ts + 32.0
            hw_36 = self.map_mgr.get_river_half_width_float(36.0) * ts
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

    def _render_ysorted_entities(self):
        """
        Renders purely natural world objects with proper 2.5D depth ordering (Y-sorting).
        Only trees, boulders, flora, and prehistoric wildlife are drawn. Zero human/building clutter.
        """
        ts = TILE_SIZE
        season_id = self.time_sys.season_id
        draw_queue = []

        # 1. Natural Obstacles & Flora
        for (col, row), obs in self.map_mgr.obstacles.items():
            # Skip bones (signs of human butchery) to maintain pure primeval nature
            if obs.obs_type == "prop_bone":
                continue

            jx = getattr(obs, "jitter_x", 0)
            jy = getattr(obs, "jitter_y", 0)
            ox = col * ts + jx
            oy = row * ts + jy
            var = getattr(obs, "variant", 0)

            # Viewport Frustum Culling
            if not (-ts <= ox - self.camera.offset_x <= SCREEN_WIDTH + ts and
                    -120 <= oy - self.camera.offset_y <= SCREEN_HEIGHT + 120):
                continue

            if obs.obs_type in ["tree", "tree_steppe", "tree_forest", "tree_tundra", "tree_swamp"]:
                obs_tex = self.assets.textures.get(obs.obs_type) or self.assets.textures.get(f"tree_{season_id}") or self.assets.textures.get("woodcut_stage_intact")
                draw_pos = (ox + obs.shake_offset - 24, oy - 70)
                sort_y = oy + 54
                shadow_center = (ox + 32, oy + 50)
                shadow_size = (68, 24)
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

        # 2. Autonomous Prehistoric Wildlife
        for beast in self.wildlife_mgr.beasts:
            bx, by = beast.x, beast.y
            # Viewport Frustum Culling
            if not (-100 <= bx - self.camera.offset_x <= SCREEN_WIDTH + 100 and
                    -100 <= by - self.camera.offset_y <= SCREEN_HEIGHT + 100):
                continue

            def make_draw_beast(b):
                def _draw():
                    b.draw(self.screen, self.camera, self.assets.fonts)
                return _draw
            draw_queue.append((beast.y + 12, make_draw_beast(beast)))

        # Sort all items by sort_y (lower Y first -> proper foreground over background)
        draw_queue.sort(key=lambda item: item[0])
        for _, draw_fn in draw_queue:
            draw_fn()

    def _render_lighting(self):
        """Natural day/night atmospheric tint (amber dawn, golden afternoon, starry twilight)."""
        light_sources = []
        self.weather_sys.draw_lighting(self.screen, self.time_sys.hour, self.time_sys.minute, light_sources)
