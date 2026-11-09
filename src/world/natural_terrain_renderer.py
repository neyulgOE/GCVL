"""
Natural Terrain & Hydrology Renderer for Stone Age Nature Observation Simulator.
Renders continuous multi-horizon ground, 2.5D craggy rock cliffs,
meandering river hydrology with harmonic shoreline foam, specular caustics,
and rounded river stepping stones.
"""

import math
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE


class NaturalTerrainRenderer:
    def __init__(self, assets):
        self.assets = assets

    def render(self, screen: pygame.Surface, camera, world, game_time: float):
        ts = TILE_SIZE
        start_col = max(0, int(camera.offset_x // ts))
        end_col = min(world.cols, int((camera.offset_x + SCREEN_WIDTH) // ts) + 2)
        start_row = max(0, int(camera.offset_y // ts))
        end_row = min(world.rows, int((camera.offset_y + SCREEN_HEIGHT) // ts) + 2)

        # -------------------------------------------------------------
        # 1. GROUND MATERIAL HORIZONS
        # -------------------------------------------------------------
        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                screen_pos = camera.apply_pos((c * ts, r * ts))
                h = (r * 31 + c * 17) % 4
                t_type = world.terrain[r][c]

                if t_type == "scree_talus":
                    base_tex = self.assets.textures.get("scree_talus") or self.assets.textures.get("biome_highlands")
                elif t_type == "forest_humus":
                    base_tex = self.assets.textures.get("forest_humus") or self.assets.textures.get("biome_forest")
                elif t_type == "riparian_mud":
                    base_tex = self.assets.textures.get("riparian_mud") or self.assets.textures.get("biome_swamp")
                elif t_type in ("point_bar_sand", "settlement_loam", "water", "bridge_ford"):
                    base_tex = self.assets.textures.get("point_bar_sand") or self.assets.textures.get("pebble_shore")
                else:
                    base_tex = (self.assets.textures.get(f"biome_steppe_{h}") or
                                self.assets.textures.get("steppe_meadow") or
                                self.assets.textures.get("biome_steppe"))

                if base_tex:
                    screen.blit(base_tex, screen_pos)

        # -------------------------------------------------------------
        # 2. 2.5D CRAGGY ROCK CLIFF FACINGS & CONTOUR SHADOWS
        # -------------------------------------------------------------
        cliff_s = self.assets.textures.get("cliff_face_south")
        cliff_tall = self.assets.textures.get("cliff_face_south_tall")
        cliff_e = self.assets.textures.get("cliff_edge_east")
        cliff_w = self.assets.textures.get("cliff_edge_west")

        c_start_row = max(0, start_row - 1)
        c_end_row = min(world.rows, end_row + 1)
        for r in range(c_start_row, c_end_row):
            for c in range(start_col, end_col):
                if cliff_e and world.cliff_east[r][c] > 0:
                    e_sx = c * ts + ts - 16 - camera.offset_x
                    e_sy = r * ts - camera.offset_y
                    screen.blit(cliff_e, (e_sx, e_sy))

                if cliff_w and world.cliff_west[r][c] > 0:
                    w_sx = c * ts - camera.offset_x
                    w_sy = r * ts - camera.offset_y
                    screen.blit(cliff_w, (w_sx, w_sy))

                s_drop = world.cliff_south[r][c]
                if s_drop > 0:
                    cw_x = c * ts - camera.offset_x
                    cw_y = (r + 1) * ts - 6 - camera.offset_y
                    v_idx = (c * 7 + r * 13) % 4
                    if s_drop >= 2:
                        c_tex = self.assets.textures.get(f"cliff_face_south_tall_{v_idx}") or cliff_tall
                    else:
                        c_tex = self.assets.textures.get(f"cliff_face_south_{v_idx}") or cliff_s
                    if c_tex:
                        screen.blit(c_tex, (cw_x, cw_y))

        # -------------------------------------------------------------
        # 3. ORGANIC RIVER COURSE, POINT BAR SHORELINE & WAVE DYNAMICS
        # -------------------------------------------------------------
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

        view_top = -16
        view_bottom = SCREEN_HEIGHT + 16
        sample_step = 8

        for sy in range(view_top, view_bottom + sample_step, sample_step):
            wy = camera.offset_y + sy
            row_f = wy / float(ts)
            rc = world.get_river_center_float(row_f) * ts + 32.0
            hw = world.get_river_half_width_float(row_f) * ts
            s_xl = rc - hw - camera.offset_x
            s_xr = rc + hw - camera.offset_x

            pts_l.append((s_xl, sy))
            pts_r.append((s_xr, sy))
            pts_sh_l.append((s_xl + 26.0, sy))
            pts_sh_r.append((s_xr - 26.0, sy))

            # Inner bend forms sunlit amber pebble point bar; outer bend forms steep cutbank
            point_bar_deposit = 58.0 * math.exp(-((row_f - 39.0) ** 2) / 64.0)
            bw_l = 36.0 + 8.0 * math.sin(row_f * 0.75 + 1.2) + point_bar_deposit
            cutbank_pinch = 14.0 * math.exp(-((row_f - 39.0) ** 2) / 64.0)
            bw_r = max(18.0, 34.0 + 8.0 * math.cos(row_f * 0.65) - cutbank_pinch)

            pts_beach_outer_l.append((s_xl - bw_l, sy))
            pts_beach_outer_r.append((s_xr + bw_r, sy))
            pts_beach_fade_l.append((s_xl - bw_l - 18.0, sy))
            pts_beach_fade_r.append((s_xr + bw_r + 14.0, sy))

            # Shoreline wave foam with harmonic phase
            f_xl = s_xl + 3.8 * math.sin(2.4 * game_time + sy * 0.05)
            f_xr = s_xr - 3.8 * math.sin(2.4 * game_time + sy * 0.05 + 1.2)
            foam_l.append((f_xl, sy))
            foam_r.append((f_xr, sy))

        min_xl = min(p[0] for p in pts_beach_fade_l)
        max_xr = max(p[0] for p in pts_beach_fade_r)
        if min_xl < SCREEN_WIDTH + 80 and max_xr > -80:
            river_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

            # Soft beach edge feathering into grassy meadows
            poly_fade_l = pts_beach_fade_l + list(reversed(pts_beach_outer_l))
            pygame.draw.polygon(river_surf, (198, 185, 142, 110), poly_fade_l)

            poly_fade_r = pts_beach_outer_r + list(reversed(pts_beach_fade_r))
            pygame.draw.polygon(river_surf, (198, 185, 142, 110), poly_fade_r)

            # Main amber sandy beach & pebble point bar
            poly_beach_l = pts_beach_outer_l + list(reversed(pts_l))
            pygame.draw.polygon(river_surf, (216, 202, 164, 255), poly_beach_l)

            poly_beach_r = pts_r + list(reversed(pts_beach_outer_r))
            pygame.draw.polygon(river_surf, (192, 178, 140, 255), poly_beach_r)

            # Smooth river pebbles scattered along the shoreline
            for sy in range(view_top, view_bottom, 24):
                wy = camera.offset_y + sy
                row_f = wy / float(ts)
                rc = world.get_river_center_float(row_f) * ts + 32.0
                hw = world.get_river_half_width_float(row_f) * ts
                s_xl = rc - hw - camera.offset_x
                s_xr = rc + hw - camera.offset_x
                point_bar_deposit = 58.0 * math.exp(-((row_f - 39.0) ** 2) / 64.0)
                bw_l = 36.0 + 8.0 * math.sin(row_f * 0.75 + 1.2) + point_bar_deposit
                bw_r = max(18.0, 34.0 + 8.0 * math.cos(row_f * 0.65))

                plx = int(s_xl - bw_l * 0.55 + 5.0 * math.sin(wy * 0.13))
                pygame.draw.circle(river_surf, (145, 130, 95, 190), (plx, sy), 3)
                pygame.draw.circle(river_surf, (215, 200, 160, 210), (plx + 1, sy - 1), 1)

                prx = int(s_xr + bw_r * 0.55 + 5.0 * math.cos(wy * 0.15))
                pygame.draw.circle(river_surf, (145, 130, 95, 190), (prx, sy), 3)
                pygame.draw.circle(river_surf, (215, 200, 160, 210), (prx + 1, sy - 1), 1)

            # Deep Sapphire/Turquoise Central Channel
            poly_deep = pts_l + list(reversed(pts_r))
            pygame.draw.polygon(river_surf, (37, 104, 143, 245), poly_deep)

            # Shallow Shoreline Water Bands
            poly_sh_l = pts_l + list(reversed(pts_sh_l))
            pygame.draw.polygon(river_surf, (72, 162, 192, 160), poly_sh_l)

            poly_sh_r = pts_sh_r + list(reversed(pts_r))
            pygame.draw.polygon(river_surf, (72, 162, 192, 160), poly_sh_r)

            # Flowing Specular Caustics (Downstream drift)
            flow_y_offset = int((game_time * 38.0) % 36.0)
            for cy in range(-36 + flow_y_offset, SCREEN_HEIGHT + 36, 36):
                c_wy = camera.offset_y + cy
                c_row_f = c_wy / float(ts)
                c_rc = world.get_river_center_float(c_row_f) * ts + 32.0
                c_hw = world.get_river_half_width_float(c_row_f) * ts
                c_xl = c_rc - c_hw - camera.offset_x + 30.0
                c_xr = c_rc + c_hw - camera.offset_x - 30.0
                if c_xr > c_xl:
                    c_pts = []
                    for cx in range(int(c_xl), int(c_xr) + 8, 12):
                        w_sine = cy + int(2.5 * math.sin(cx * 0.08 + game_time * 2.0))
                        c_pts.append((cx, w_sine))
                    if len(c_pts) >= 2:
                        for idx in range(len(c_pts) - 1):
                            pygame.draw.line(river_surf, (180, 230, 248, 85), c_pts[idx], c_pts[idx + 1], 1)

            # Shoreline Foam Lines
            if len(foam_l) >= 2:
                pygame.draw.lines(river_surf, (235, 248, 255, 215), False, foam_l, 2)
            if len(foam_r) >= 2:
                pygame.draw.lines(river_surf, (235, 248, 255, 215), False, foam_r, 2)

            screen.blit(river_surf, (0, 0))

        # -------------------------------------------------------------
        # 4. NATURAL STEPPING STONE FORD AT ROW 36
        # -------------------------------------------------------------
        r36_sy = int(36 * ts + 32 - camera.offset_y)
        if -80 <= r36_sy <= SCREEN_HEIGHT + 80:
            rc_36 = world.get_river_center_float(36.0) * ts + 32.0
            hw_36 = world.get_river_half_width_float(36.0) * ts
            num_stones = 9
            for s_i in range(num_stones):
                t_frac = (s_i + 0.5) / float(num_stones)
                st_world_x = (rc_36 - hw_36 * 0.85) + t_frac * (hw_36 * 1.7)
                st_sx = int(st_world_x - camera.offset_x)
                st_sy = int(36.0 * ts + 32.0 - camera.offset_y + 4.0 * math.sin(s_i * 1.4))
                st_tex = self.assets.textures.get(f"stepping_stone_{s_i % 4}")
                if st_tex and -50 <= st_sx <= SCREEN_WIDTH + 50 and -50 <= st_sy <= SCREEN_HEIGHT + 50:
                    sw, sh = st_tex.get_size()
                    screen.blit(st_tex, (st_sx - sw // 2, st_sy - sh // 2))

        # -------------------------------------------------------------
        # 5. NATURAL LANDMARKS (COLOSSAL RIB FOSSIL, CASCADE & MONOLITH)
        # -------------------------------------------------------------
        landmarks = getattr(world, "natural_landmarks", [])
        for lm in landmarks:
            lx = lm["col"] * ts
            ly = lm["row"] * ts
            lm_type = lm["type"]

            # Frustum Culling
            sx = lx - camera.offset_x
            sy = ly - camera.offset_y
            if not (-160 <= sx <= SCREEN_WIDTH + 160 and -160 <= sy <= SCREEN_HEIGHT + 160):
                continue

            if lm_type == "colossal_rib_fossils":
                # Mammoth fossil rib cage along point bar (Image 2)
                for idx in range(5):
                    rib_x = sx + idx * 28
                    rib_y = sy + idx * 18
                    # Ground shadow cast on sandy beach
                    sh_surf = pygame.Surface((90, 36), pygame.SRCALPHA)
                    pygame.draw.ellipse(sh_surf, (20, 24, 28, 90), (0, 8, 86, 22))
                    screen.blit(sh_surf, (rib_x - 35, rib_y + 42))

                    # Dark socket planted into the sand
                    pygame.draw.polygon(screen, (72, 64, 54), [
                        (rib_x + 12, rib_y + 56), (rib_x + 28, rib_y + 56), (rib_x + 18, rib_y + 28)
                    ])

                    # Tall ivory rib bone arching toward the river
                    arc_rect = pygame.Rect(rib_x - 48, rib_y - 34, 76, 92)
                    pygame.draw.arc(screen, (228, 220, 202), arc_rect, 0.15, math.pi * 0.78, 8)
                    pygame.draw.arc(screen, (148, 138, 122), (arc_rect.x + 2, arc_rect.y + 3, 76, 92), 0.15, math.pi * 0.78, 3)

            elif lm_type == "upstream_boulder_cascade":
                # Cascading rock rapids with white foam (Image 1 & 3)
                for bx_off, by_off, bw, bh in [(-45, -10, 52, 34), (0, -4, 60, 38), (42, -12, 48, 32)]:
                    pygame.draw.ellipse(screen, (68, 64, 62), (sx + bx_off, sy + by_off + 6, bw, bh))
                    pygame.draw.ellipse(screen, (136, 132, 128), (sx + bx_off, sy + by_off, bw, bh - 6))
                    # Rushing whitewater foam across the rocks
                    foam_pulse = 2.0 * math.sin(game_time * 4.0 + bx_off)
                    pygame.draw.line(screen, (240, 250, 255),
                                     (sx + bx_off + bw // 2, sy + by_off + bh - 4),
                                     (sx + bx_off + bw // 2, sy + by_off + bh + 24 + foam_pulse), 5)

            elif lm_type == "mossy_monolith":
                # Prehistoric standing monolith rock with moss
                pygame.draw.ellipse(screen, (25, 30, 28, 110), (sx - 8, sy + 38, 56, 22))
                pygame.draw.polygon(screen, (90, 94, 88), [
                    (sx, sy + 44), (sx + 38, sy + 44), (sx + 28, sy - 18), (sx + 10, sy - 18)
                ])
                pygame.draw.polygon(screen, (128, 134, 124), [
                    (sx + 4, sy + 40), (sx + 22, sy + 40), (sx + 18, sy - 14), (sx + 12, sy - 14)
                ])
                # Green moss patches
                pygame.draw.ellipse(screen, (74, 108, 48), (sx + 6, sy + 18, 16, 12))
