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
from src.world.map_manager import MapManager
from src.world.natural_terrain_renderer import NaturalTerrainRenderer
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
        self.terrain_renderer = NaturalTerrainRenderer(self.assets)
        self.particle_sys = ParticleSystem()

        # Wildlife & Ecosystem
        self.wildlife_mgr = WildlifeManager(self.map_mgr)
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
                action = self.minimap.handle_mouse_down(event.pos, event.button, self.map_mgr)
                if action and action.get("type") == "teleport_camera":
                    self.free_cam.set_pos(action["x"], action["y"])
                    self.free_cam.camera.snap_to(self.free_cam.target.rect)
                    tile_c = int(action["x"] // TILE_SIZE)
                    tile_r = int(action["y"] // TILE_SIZE)
                    if hasattr(self, "dialog_mgr"):
                        self.dialog_mgr.add_toast(f"🔭 Camera đã bay tới vùng quan sát [{tile_c}, {tile_r}]")
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

        # Apply natural weather response to terrain (soil moistening / drying, river swelling)
        self.map_mgr.apply_weather_response(dt, self.weather_sys.weather)

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

        # 1. Natural Terrain, River Course & Prehistoric Landmarks
        self.terrain_renderer.render(self.screen, self.camera, self.map_mgr.world, self.game_time)

        # 1.5. Prehistoric animal tracks on mud & sand
        for tr in getattr(self.wildlife_mgr, "animal_tracks", []):
            z_offset = self.map_mgr.get_height_screen_offset(tr.get("z", 0.5))
            sx, sy = self.camera.world_to_screen((tr["x"], tr["y"]), z_offset)
            if -10 <= sx <= SCREEN_WIDTH + 10 and -10 <= sy <= SCREEN_HEIGHT + 10:
                alpha = int(120 * (tr["life"] / tr["max_life"]))
                tr_surf = pygame.Surface((10, 8), pygame.SRCALPHA)
                pygame.draw.ellipse(tr_surf, (55, 42, 30, alpha), (0, 0, 4, 6))
                pygame.draw.ellipse(tr_surf, (55, 42, 30, alpha), (5, 2, 4, 6))
                self.screen.blit(tr_surf, (sx - 5, sy - 4))

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
            z_offset = self.map_mgr.get_height_screen_offset_at_tile(col, row)
            var = getattr(obs, "variant", 0)

            # Viewport Frustum Culling
            if not (-ts <= ox - self.camera.offset_x <= SCREEN_WIDTH + ts and
                    -120 <= oy - self.camera.offset_y <= SCREEN_HEIGHT + 120):
                continue

            if obs.obs_type in ["tree", "tree_steppe", "tree_forest", "tree_tundra", "tree_swamp"]:
                v = (col * 17 + row * 31) % 10
                obs_tex = (self.assets.textures.get(f"{obs.obs_type}_{v}") or
                           self.assets.textures.get(obs.obs_type) or
                           self.assets.textures.get(f"tree_{season_id}") or
                           self.assets.textures.get("woodcut_stage_intact"))
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
                def make_draw_obs(tex, pos, s_center, s_size, height_offset):
                    def _draw():
                        s_pos = self.camera.apply_pos(s_center, height_offset)
                        VisualEnhancer.draw_drop_shadow(self.screen, s_pos, s_size[0], s_size[1])
                        self.screen.blit(tex, self.camera.apply_pos(pos, height_offset))
                    return _draw
                draw_queue.append((sort_y, make_draw_obs(obs_tex, draw_pos, shadow_center, shadow_size, z_offset)))

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
            beast_z_offset = self.map_mgr.get_height_screen_offset(beast.z)
            draw_queue.append((beast.y + 12 - beast_z_offset, make_draw_beast(beast)))

        # Sort all items by sort_y (lower Y first -> proper foreground over background)
        draw_queue.sort(key=lambda item: item[0])
        for _, draw_fn in draw_queue:
            draw_fn()

    def _render_lighting(self):
        """Natural day/night atmospheric tint (amber dawn, sunlit afternoon, starry twilight)."""
        light_sources = []
        self.weather_sys.draw_lighting(self.screen, self.time_sys.hour, self.time_sys.minute, light_sources)
