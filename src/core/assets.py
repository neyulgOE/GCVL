"""
Master Asset Manager for Stone Age: Primeval World.
Loads authentic prehistoric pixel art, megafauna wildlife, natural biomes,
terrain layers, and ambient environmental audio.
"""

import pygame
import os
import math
from src.settings import TILE_SIZE, PALETTE, SEASONS

class AssetManager:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.textures = {}
        self.sounds = {}
        self.fonts = {}
        self.init_fonts()
        self.load_all_assets()
        self.load_audio()

    def init_fonts(self):
        pygame.font.init()
        font_path = "assets/fonts/DejaVuSans-Bold.ttf"
        if not os.path.exists(font_path):
            font_path = "assets/fonts/DejaVuSans.ttf"

        if os.path.exists(font_path):
            try:
                self.fonts["tiny"] = pygame.font.Font(font_path, 11)
                self.fonts["small"] = pygame.font.Font(font_path, 13)
                self.fonts["normal"] = pygame.font.Font(font_path, 15)
                self.fonts["large"] = pygame.font.Font(font_path, 18)
                self.fonts["title"] = pygame.font.Font(font_path, 24)
                return
            except Exception as e:
                print("Lỗi nạp font DejaVu:", e)

        # Fallback to system font
        self.fonts["tiny"] = pygame.font.SysFont("dejavusans", 11, bold=True)
        self.fonts["small"] = pygame.font.SysFont("dejavusans", 13, bold=True)
        self.fonts["normal"] = pygame.font.SysFont("dejavusans", 15, bold=True)
        self.fonts["large"] = pygame.font.SysFont("dejavusans", 18, bold=True)
        self.fonts["title"] = pygame.font.SysFont("dejavusans", 24, bold=True)

    def load_all_assets(self):
        ts = TILE_SIZE  # 64

        # ---------------------------------------------------------
        # 1. WORLD COMPOSITE & TERRAIN FALLBACK
        # ---------------------------------------------------------
        self.textures["world_composite"] = pygame.Surface((3200, 2560))
        self.textures["world_composite"].fill((160, 185, 104))

        # Animated River Water (64x64)
        for i in range(4):
            w_path = f"assets/pydew/water/{i}.png"
            if os.path.exists(w_path):
                w_img = pygame.image.load(w_path).convert_alpha()
                self.textures[f"water_{i}"] = pygame.transform.scale(w_img, (ts, ts))
            else:
                w_surf = pygame.Surface((ts, ts))
                w_surf.fill((65, 140, 195))
                self.textures[f"water_{i}"] = w_surf

        # Tilled Soil from extracted prehistoric tiles (64x64)
        ex_soil = "assets/tiles_extracted/tile_r0_c2.png"
        soil_path = ex_soil if os.path.exists(ex_soil) else "assets/pydew/soil/o.png"
        if not os.path.exists(soil_path):
            soil_path = "assets/pydew/soil/bm.png"
        if os.path.exists(soil_path):
            soil_img = pygame.image.load(soil_path).convert_alpha()
            self.textures["dirt_tilled"] = pygame.transform.scale(soil_img, (ts, ts))
        else:
            surf_t = pygame.Surface((ts, ts))
            surf_t.fill((168, 120, 75))
            self.textures["dirt_tilled"] = surf_t

        # Watered Soil from extracted prehistoric mud tiles (64x64)
        ex_mud = "assets/tiles_extracted/tile_r0_c4.png"
        watered_soil_path = ex_mud if os.path.exists(ex_mud) else "assets/pydew/soil_water/0.png"
        if os.path.exists(watered_soil_path):
            w_soil_img = pygame.image.load(watered_soil_path).convert_alpha()
            self.textures["dirt_watered"] = pygame.transform.scale(w_soil_img, (ts, ts))
        else:
            surf_w = pygame.Surface((ts, ts))
            surf_w.fill((112, 75, 42))
            self.textures["dirt_watered"] = surf_w

        # Prehistoric Environmental Props (Rib bones, mushrooms, flint, ferns)
        prop_map = {
            "prop_bone": "assets/tiles_extracted/tile_r8_c7.png",
            "prop_mushroom": "assets/tiles_extracted/tile_r8_c8.png",
            "prop_flint": "assets/tiles_extracted/tile_r9_c8.png",
            "prop_fern": "assets/tiles_extracted/tile_r9_c7.png",
        }
        for pk, pp in prop_map.items():
            if os.path.exists(pp):
                self.textures[pk] = pygame.image.load(pp).convert_alpha()

        # Prehistoric Biome Terrain Tiles (64x64) from Sliced Master Bundle
        terrain_tile_dir = "assets/stone_age/12_seamless_64x64_terrain_tiles"
        if not os.path.exists(terrain_tile_dir):
            terrain_tile_dir = "stone_age_rts_complete_all_in_one_bundle/02_SLICED_SPRITES_128_PNG/12_seamless_64x64_terrain_tiles"

        def _get_tile_or_fallback(fname, fallback_col):
            p = os.path.join(terrain_tile_dir, fname)
            if os.path.exists(p):
                try:
                    raw = pygame.image.load(p).convert_alpha()
                    return pygame.transform.scale(raw, (ts, ts))
                except Exception:
                    pass
            fb = pygame.Surface((ts, ts))
            fb.fill(fallback_col)
            return fb

        # 1. Authentic Steppe Grassland (Savanna Ochre & Olive Grass - Mean RGB [125, 156, 66])
        base_steppe = _get_tile_or_fallback("tile_01_steppe_grass.png", (125, 156, 66))
        self.textures["biome_steppe"] = base_steppe
        self.textures["biome_steppe_0"] = base_steppe

        # Variant 1: Subtle dry grass / straw blades
        v1 = base_steppe.copy()
        for x, y in [(14, 22), (42, 18), (30, 48), (52, 42), (18, 54)]:
            pygame.draw.line(v1, (168, 152, 75, 180), (x, y), (x + 2, y - 5), 1)
            pygame.draw.line(v1, (155, 140, 68, 160), (x + 1, y), (x - 2, y - 4), 1)
        self.textures["biome_steppe_1"] = v1

        # Variant 2: Weathered loam flecks and small granite pebble specks
        v2 = base_steppe.copy()
        for x, y in [(20, 32), (36, 14), (16, 50), (48, 28), (56, 52)]:
            pygame.draw.circle(v2, (140, 120, 80, 140), (x, y), 2)
            pygame.draw.circle(v2, (170, 160, 145, 180), (x + 1, y + 1), 1)
        self.textures["biome_steppe_2"] = v2

        # Variant 3: Warm dry savanna ochre wash
        v3 = base_steppe.copy()
        ochre_wash = pygame.Surface((ts, ts), pygame.SRCALPHA)
        ochre_wash.fill((165, 142, 65, 24))
        v3.blit(ochre_wash, (0, 0))
        for x, y in [(28, 24), (46, 38)]:
            pygame.draw.line(v3, (175, 155, 80, 190), (x, y), (x + 3, y - 6), 1)
        self.textures["biome_steppe_3"] = v3

        # 2. Forest, Tundra, Highlands, Swamp & Mud
        base_forest = _get_tile_or_fallback("tile_02_primeval_forest_floor.png", (54, 97, 45))
        self.textures["biome_forest"] = base_forest
        self.textures["biome_forest_0"] = base_forest
        self.textures["biome_forest_1"] = base_forest

        base_tundra = _get_tile_or_fallback("tile_09_tundra_permafrost_snow.png", (218, 229, 236))
        self.textures["biome_tundra"] = base_tundra
        self.textures["biome_tundra_0"] = base_tundra
        self.textures["biome_tundra_1"] = base_tundra

        base_highlands = _get_tile_or_fallback("tile_08_megalithic_granite_rock.png", (124, 112, 97))
        self.textures["biome_highlands"] = base_highlands
        self.textures["biome_highlands_0"] = base_highlands
        self.textures["biome_highlands_1"] = base_highlands

        base_swamp = _get_tile_or_fallback("tile_07_ancient_swamp_mud.png", (68, 91, 66))
        self.textures["biome_swamp"] = base_swamp
        self.textures["biome_swamp_0"] = base_swamp
        self.textures["biome_swamp_1"] = base_swamp

        # 3. Trampled Loam (Human Settlement Apron) & Pebble River Shore
        base_loam = _get_tile_or_fallback("tile_03_trampled_dirt_trail.png", (155, 127, 88)).convert_alpha()
        self.textures["tile_03_trampled_dirt_trail"] = base_loam
        self.textures["settlement_loam"] = base_loam
        self.textures["trail_dirt"] = base_loam

        # Pre-bake 16 autotile feathered edge variants for settlement loam against wild steppe grass
        fade_dist = 22.0
        ts = 64
        for up in (True, False):
            for down in (True, False):
                for left in (True, False):
                    for right in (True, False):
                        if up and down and left and right:
                            self.textures[f"loam_{int(up)}{int(down)}{int(left)}{int(right)}"] = base_loam
                            continue
                        f_loam = base_loam.copy()
                        for y in range(ts):
                            for x in range(ts):
                                d_top = y if not up else ts
                                d_bottom = (ts - 1 - y) if not down else ts
                                d_left = x if not left else ts
                                d_right = (ts - 1 - x) if not right else ts
                                min_d = min(d_top, d_bottom, d_left, d_right)
                                if min_d < fade_dist:
                                    noise = ((x * 17 + y * 31 + (x ^ y)) % 9) - 4.0
                                    jittered_d = max(0.0, min_d + noise)
                                    frac = max(0.0, min(1.0, jittered_d / fade_dist))
                                    smooth_frac = frac * frac * (3.0 - 2.0 * frac)
                                    c = f_loam.get_at((x, y))
                                    f_loam.set_at((x, y), (c[0], c[1], c[2], int(255 * smooth_frac)))
                        self.textures[f"loam_{int(up)}{int(down)}{int(left)}{int(right)}"] = f_loam

        base_pebble = _get_tile_or_fallback("tile_04_pebble_river_shore.png", (189, 173, 132))
        self.textures["tile_04_pebble_river_shore"] = base_pebble
        self.textures["pebble_shore"] = base_pebble

        # 5 Ground Material Horizons
        self.textures["scree_talus"] = base_highlands
        self.textures["steppe_meadow"] = base_steppe
        self.textures["forest_humus"] = base_forest
        self.textures["riparian_mud"] = base_swamp
        self.textures["point_bar_sand"] = base_pebble
        self.textures["tundra_snow"] = base_tundra

        # Pre-bake 2.5D Cliff Facings (South-facing terrace drop wall)
        # 4 Natural Sedimentary / Granite Rock Variants (eliminates repeating patterns!)
        for v in range(4):
            # Tier 1 Drop (height 22px): Horizontal stratified layers, unique natural cracks, moss & soft shadow
            c_face = pygame.Surface((ts, 22), pygame.SRCALPHA)
            for y in range(2, 16):
                shade = 86 - int(y * 2.2) + ((v * 5 + y * 7) % 6)
                r_col = (shade + 22, shade + 15, shade + 6)
                pygame.draw.line(c_face, r_col, (0, y), (ts - 1, y))

            # Horizontal geological strata crevices
            pygame.draw.line(c_face, (42, 34, 26), (0, 7), (ts - 1, 7), 1)
            pygame.draw.line(c_face, (36, 28, 22), (0, 13), (ts - 1, 13), 1)

            # Top sunlit bevel rim
            pygame.draw.line(c_face, (215, 205, 190), (0, 1), (ts - 1, 1), 2)
            pygame.draw.line(c_face, (175, 165, 150), (0, 2), (ts - 1, 2), 1)

            # Natural vertical/angled cracks unique to this variant
            if v == 0:
                pygame.draw.line(c_face, (30, 24, 18), (18, 2), (16, 15), 1)
                pygame.draw.line(c_face, (200, 190, 175), (19, 2), (17, 13), 1)
                pygame.draw.circle(c_face, (82, 102, 60), (20, 10), 2)
            elif v == 1:
                pygame.draw.line(c_face, (30, 24, 18), (44, 2), (47, 15), 1)
                pygame.draw.line(c_face, (200, 190, 175), (45, 2), (48, 13), 1)
                pygame.draw.circle(c_face, (82, 102, 60), (42, 12), 2)
            elif v == 2:
                pygame.draw.line(c_face, (30, 24, 18), (32, 4), (30, 14), 1)
                pygame.draw.circle(c_face, (82, 102, 60), (12, 8), 2)
                pygame.draw.circle(c_face, (82, 102, 60), (52, 9), 2)
            else:
                pygame.draw.line(c_face, (30, 24, 18), (10, 3), (12, 14), 1)
                pygame.draw.line(c_face, (30, 24, 18), (54, 2), (52, 15), 1)

            # Bottom contact shadow onto lower tier
            for sy in range(6):
                a = int(150 * (1.0 - sy / 6.0))
                pygame.draw.line(c_face, (18, 15, 12, a), (0, 16 + sy), (ts - 1, 16 + sy))

            self.textures[f"cliff_face_south_{v}"] = c_face
            if v == 0:
                self.textures["cliff_face_south"] = c_face

            # Tier 2+ Drop (Tall Cliff height 38px)
            c_face_tall = pygame.Surface((ts, 38), pygame.SRCALPHA)
            for y in range(2, 30):
                shade = 82 - int(y * 1.5) + ((v * 7 + y * 5) % 6)
                r_col = (shade + 22, shade + 15, shade + 6)
                pygame.draw.line(c_face_tall, r_col, (0, y), (ts - 1, y))

            pygame.draw.line(c_face_tall, (42, 34, 26), (0, 10), (ts - 1, 10), 1)
            pygame.draw.line(c_face_tall, (38, 30, 24), (0, 20), (ts - 1, 20), 1)
            pygame.draw.line(c_face_tall, (34, 26, 20), (0, 28), (ts - 1, 28), 1)

            pygame.draw.line(c_face_tall, (218, 208, 192), (0, 1), (ts - 1, 1), 2)
            pygame.draw.line(c_face_tall, (178, 168, 152), (0, 2), (ts - 1, 2), 1)

            crk_x = (14 + v * 12) % 52 + 6
            pygame.draw.line(c_face_tall, (28, 22, 16), (crk_x, 2), (crk_x + (v % 2) * 4 - 2, 28), 2)
            pygame.draw.line(c_face_tall, (205, 195, 178), (crk_x + 1, 2), (crk_x + (v % 2) * 4 - 1, 26), 1)
            pygame.draw.circle(c_face_tall, (80, 100, 58), (crk_x - 3, 16), 3)

            for sy in range(8):
                a = int(160 * (1.0 - sy / 8.0))
                pygame.draw.line(c_face_tall, (18, 15, 12, a), (0, 30 + sy), (ts - 1, 30 + sy))

            self.textures[f"cliff_face_south_tall_{v}"] = c_face_tall
            if v == 0:
                self.textures["cliff_face_south_tall"] = c_face_tall

        # Natural Ramp Incline Surface (Connects Upper Terraces smoothly)
        ramp_surf = pygame.Surface((ts, 26), pygame.SRCALPHA)
        for y in range(24):
            frac = y / 24.0
            r = int(140 - frac * 15)
            g = int(115 - frac * 15)
            b = int(78 - frac * 12)
            a = int(220 + frac * 35)
            pygame.draw.line(ramp_surf, (r, g, b, a), (4, y), (ts - 5, y))
        for x in range(4):
            for y in range(24):
                c = ramp_surf.get_at((4 + x, y))
                ramp_surf.set_at((4 - 1 - x, y), (c[0], c[1], c[2], int(c[3] * (x / 4.0))))
                c_r = ramp_surf.get_at((ts - 5 - x, y))
                ramp_surf.set_at((ts - 4 + x, y), (c_r[0], c_r[1], c_r[2], int(c_r[3] * (x / 4.0))))
        for px, py in [(18, 8), (42, 6), (28, 16), (46, 18), (32, 10)]:
            pygame.draw.circle(ramp_surf, (175, 168, 150, 180), (px, py), 2)
            pygame.draw.circle(ramp_surf, (100, 85, 65, 180), (px + 1, py + 1), 1)
        self.textures["ramp_slope_south"] = ramp_surf

        # East cliff side shadow overlay (right edge of elevated tile)
        c_edge_e = pygame.Surface((16, ts), pygame.SRCALPHA)
        for x in range(16):
            sh_alpha = int(130 * (x / 16.0))
            pygame.draw.line(c_edge_e, (15, 18, 22, sh_alpha), (x, 0), (x, ts))
        self.textures["cliff_edge_east"] = c_edge_e

        # West cliff bevel rim overlay (left edge of elevated tile)
        c_edge_w = pygame.Surface((16, ts), pygame.SRCALPHA)
        for x in range(16):
            bevel_alpha = int(150 * (1.0 - x / 16.0))
            pygame.draw.line(c_edge_w, (215, 205, 190, bevel_alpha), (x, 0), (x, ts))
        self.textures["cliff_edge_west"] = c_edge_w

        # Stepping Stones (River Crossing Ford at row 36)
        for s_idx, s_rad in enumerate([18, 15, 19, 16]):
            stone_surf = pygame.Surface((s_rad * 2 + 10, s_rad * 2 + 10), pygame.SRCALPHA)
            scx = s_rad + 5
            scy = s_rad + 5
            # Submerged underwater refraction
            pygame.draw.circle(stone_surf, (40, 95, 120, 140), (scx, scy + 3), s_rad + 4)
            # Wet lower granite rim
            pygame.draw.ellipse(stone_surf, (82, 75, 68, 245), (scx - s_rad, scy - s_rad + 2, s_rad * 2, s_rad * 2))
            # Dry top granite dome
            pygame.draw.ellipse(stone_surf, (145, 136, 122, 255), (scx - s_rad + 2, scy - s_rad, s_rad * 2 - 4, s_rad * 2 - 4))
            # Sunlight specular highlight on top curvature
            pygame.draw.ellipse(stone_surf, (198, 188, 172, 220), (scx - s_rad // 2, scy - s_rad + 2, s_rad, s_rad // 2 + 2))
            # Lichen fleck
            pygame.draw.circle(stone_surf, (92, 108, 68, 180), (scx + 3, scy - 2), 2)
            self.textures[f"stepping_stone_{s_idx}"] = stone_surf

        # 4. River Water (Deep Channel & Shallow Ford) + 4-frame flow caustics
        base_deep_water = _get_tile_or_fallback("tile_06_deep_river_water.png", (37, 104, 143))
        self.textures["biome_water"] = base_deep_water
        self.textures["tile_06_deep_river_water"] = base_deep_water

        base_shallow_water = _get_tile_or_fallback("tile_05_shallow_ford_water.png", (72, 162, 192))
        self.textures["tile_05_shallow_ford_water"] = base_shallow_water
        self.textures["water_shallow"] = base_shallow_water
        self.textures["tile_ford"] = base_shallow_water

        for f in range(4):
            w_frame = base_deep_water.copy()
            # Flowing specular caustic ripples moving downstream (+y)
            for i in range(4):
                y_base = int((i * 16 + f * 4) % ts)
                pts = []
                for x in range(0, ts + 4, 8):
                    y_wave = y_base + int(2.5 * math.sin(x * 0.15 + f * 1.5))
                    pts.append((x, max(0, min(ts - 1, y_wave))))
                if len(pts) >= 2:
                    for p_idx in range(len(pts) - 1):
                        pygame.draw.line(w_frame, (160, 215, 235, 75), pts[p_idx], pts[p_idx + 1], 1)
            self.textures[f"water_{f}"] = w_frame

        # Generate smooth organic directional shoreline edge overlays (feathered sand & foam)
        # These eliminate hard 90° cuts when water tiles meet steppe grass or mud!
        sand_col = (185, 162, 118)
        wet_sand_col = (130, 110, 80)
        foam_col = (220, 245, 250)

        # West edge (water is to the left of land)
        edge_w = pygame.Surface((ts, ts), pygame.SRCALPHA)
        for x in range(16):
            alpha = int(220 * (1.0 - x / 16.0))
            col = wet_sand_col if x < 6 else sand_col
            pygame.draw.line(edge_w, (*col, alpha), (x, 0), (x, ts))
        # subtle foam dots on the outer waterline
        for fy in range(4, ts, 8):
            pygame.draw.circle(edge_w, (*foam_col, 200), (2 + (fy % 4), fy), 2)
        self.textures["shore_edge_w"] = edge_w

        # East edge (water is to the right of land)
        edge_e = pygame.Surface((ts, ts), pygame.SRCALPHA)
        for x in range(16):
            alpha = int(220 * (x / 16.0))
            col = sand_col if x < 10 else wet_sand_col
            pygame.draw.line(edge_e, (*col, alpha), (ts - 16 + x, 0), (ts - 16 + x, ts))
        for fy in range(6, ts, 8):
            pygame.draw.circle(edge_e, (*foam_col, 200), (ts - 3 - (fy % 4), fy), 2)
        self.textures["shore_edge_e"] = edge_e

        # North edge (water is above land)
        edge_n = pygame.Surface((ts, ts), pygame.SRCALPHA)
        for y in range(16):
            alpha = int(220 * (1.0 - y / 16.0))
            col = wet_sand_col if y < 6 else sand_col
            pygame.draw.line(edge_n, (*col, alpha), (0, y), (ts, y))
        for fx in range(4, ts, 8):
            pygame.draw.circle(edge_n, (*foam_col, 200), (fx, 2 + (fx % 4)), 2)
        self.textures["shore_edge_n"] = edge_n

        # South edge (water is below land)
        edge_s = pygame.Surface((ts, ts), pygame.SRCALPHA)
        for y in range(16):
            alpha = int(220 * (y / 16.0))
            col = sand_col if y < 10 else wet_sand_col
            pygame.draw.line(edge_s, (*col, alpha), (0, ts - 16 + y), (ts, ts - 16 + y))
        for fx in range(6, ts, 8):
            pygame.draw.circle(edge_s, (*foam_col, 200), (fx, ts - 3 - (fx % 4)), 2)
        self.textures["shore_edge_s"] = edge_s

        # Organic Beaten Earth & Gravel Footpaths (64x64 Feathered Alpha Overlays)
        # Soft irregular earthen edges that blend seamlessly over steppe grass and mud
        dirt_trail = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(dirt_trail, (128, 92, 54, 155), (2, 8, ts - 4, ts - 16))
        pygame.draw.ellipse(dirt_trail, (150, 112, 68, 135), (8, 14, ts - 16, ts - 28))
        # Small worn pebbles & trampled footprints along the track
        pygame.draw.circle(dirt_trail, (170, 165, 150, 180), (16, 26), 2)
        pygame.draw.circle(dirt_trail, (110, 105, 95, 180), (44, 34), 2)
        pygame.draw.circle(dirt_trail, (185, 178, 160, 160), (32, 22), 2)
        self.textures["trail_dirt"] = dirt_trail

        gravel_trail = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(gravel_trail, (115, 108, 98, 160), (2, 6, ts - 4, ts - 12))
        pygame.draw.ellipse(gravel_trail, (140, 132, 120, 130), (8, 12, ts - 16, ts - 24))
        for gx, gy in [(14, 20), (28, 32), (44, 24), (22, 42), (38, 16)]:
            pygame.draw.circle(gravel_trail, (185, 180, 170, 210), (gx, gy), 2)
        self.textures["trail_gravel"] = gravel_trail
        self.textures["trail_causeway"] = gravel_trail

        # River Crossing Bridges (Full Multi-Tile Span & Single-Tile Stepping Stones)
        ford_p = "stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack/09_trailblazing_and_waypoints/river_crossing_bridge_01.png"
        log_p = "stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack/09_trailblazing_and_waypoints/river_crossing_bridge_02.png"
        if os.path.exists(ford_p):
            raw_ford = pygame.image.load(ford_p).convert_alpha()
            self.textures["bridge_ford_full"] = raw_ford
            # Clean stepping stones for single tile
            self.textures["bridge_ford"] = pygame.transform.smoothscale(raw_ford, (ts, ts))
        if os.path.exists(log_p):
            raw_log = pygame.image.load(log_p).convert_alpha()
            self.textures["bridge_log_full"] = raw_log
            self.textures["bridge_log"] = pygame.transform.smoothscale(raw_log, (ts, ts))


        # Waypoints & Navigational Totem Markers
        waypoint_map = {
            "waypoint_inukshuk": "stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack/09_trailblazing_and_waypoints/waypoint_marker_01.png",
            "waypoint_skull_pole": "stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack/09_trailblazing_and_waypoints/waypoint_marker_02.png",
            "waypoint_carved_tree": "stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack/09_trailblazing_and_waypoints/waypoint_marker_03.png",
            "waypoint_blaze_post": "stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack/09_trailblazing_and_waypoints/waypoint_marker_04.png",
        }
        for wk, wp in waypoint_map.items():
            if os.path.exists(wp):
                w_img = pygame.image.load(wp).convert_alpha()
                self.textures[wk] = pygame.transform.scale(w_img, (64, 80))

        # Prehistoric Forageable Flora Sprites & Trees
        flora_assets = {
            "wild_bush": "assets/stone_age/05_forageable_flora_3stages/flora_berry_bush_stage_05.png",
            "flora_berries": "assets/stone_age/05_forageable_flora_3stages/flora_berry_bush_stage_05.png",
            "flora_grain": "assets/stone_age/05_forageable_flora_3stages/flora_grain_fiber_reed_stage_04.png",
            "flora_grain_0": "assets/stone_age/05_forageable_flora_3stages/flora_grain_fiber_reed_stage_04.png",
            "flora_grain_1": "assets/stone_age/05_forageable_flora_3stages/flora_grain_fiber_reed_stage_05.png",
            "flora_mushroom": "assets/stone_age/05_forageable_flora_3stages/flora_mushroom_herb_stage_04.png",
            "flora_mushroom_0": "assets/stone_age/05_forageable_flora_3stages/flora_mushroom_herb_stage_04.png",
            "flora_mushroom_1": "assets/stone_age/05_forageable_flora_3stages/flora_mushroom_herb_stage_05.png",
            "flora_tuber": "assets/stone_age/05_forageable_flora_3stages/flora_tuber_root_garlic_stage_04.png",
            "branch_wood": "assets/stone_age/04_prehistoric_trees_and_wood/woodcut_split_timber_11.png",
            "branch_logs": "assets/stone_age/04_prehistoric_trees_and_wood/woodcut_logs_bundle_10.png",
        }
        for fk, fp in flora_assets.items():
            if os.path.exists(fp):
                f_img = pygame.image.load(fp).convert_alpha()
                if "branch" in fk:
                    self.textures[fk] = pygame.transform.smoothscale(f_img, (48, 48))
                else:
                    self.textures[fk] = pygame.transform.smoothscale(f_img, (56, 56))

        # Multi-variant Trees across all 4 Prehistoric Biomes
        tree_categories = {
            "tree_steppe": ("assets/stone_age/04_prehistoric_trees_and_wood/tree_steppe_oak_pine_{:02d}.png", 10, (120, 142)),
            "tree_forest": ("assets/stone_age/04_prehistoric_trees_and_wood/tree_primeval_fern_cycad_{:02d}.png", 10, (116, 138)),
            "tree_tundra": ("assets/stone_age/04_prehistoric_trees_and_wood/tree_tundra_spruce_birch_{:02d}.png", 10, (110, 140)),
            "tree_swamp": ("assets/stone_age/04_prehistoric_trees_and_wood/tree_swamp_mangrove_{:02d}.png", 2, (114, 136)),
        }
        for prefix, (pattern, count, sz) in tree_categories.items():
            for i in range(1, count + 1):
                tp = pattern.format(i)
                if os.path.exists(tp):
                    raw_t = pygame.image.load(tp).convert_alpha()
                    scaled_t = pygame.transform.smoothscale(raw_t, sz)
                    self.textures[f"{prefix}_{i - 1}"] = scaled_t
                    if i == 1:
                        self.textures[prefix] = scaled_t
                        if prefix == "tree_steppe":
                            self.textures["tree"] = scaled_t

        # Berry Bush Variants (9 stages)
        for i in range(1, 10):
            bp = f"assets/stone_age/05_forageable_flora_3stages/flora_berry_bush_stage_{i:02d}.png"
            if os.path.exists(bp):
                b_raw = pygame.image.load(bp).convert_alpha()
                self.textures[f"wild_bush_{i - 1}"] = pygame.transform.smoothscale(b_raw, (56, 56))

        # Soft trampled dirt decals (anchor buildings naturally into the earth)
        dirt_decal_w, dirt_decal_h = 160, 48
        dirt_decal = pygame.Surface((dirt_decal_w, dirt_decal_h), pygame.SRCALPHA)
        pygame.draw.ellipse(dirt_decal, (68, 52, 34, 115), (0, 0, dirt_decal_w, dirt_decal_h))
        pygame.draw.ellipse(dirt_decal, (50, 38, 24, 150), (16, 6, dirt_decal_w - 32, dirt_decal_h - 12))
        self.textures["trampled_dirt_decal"] = dirt_decal

        # ---------------------------------------------------------
        # 2. OBSTACLES & NATURE (LAND CLEARING)
        # ---------------------------------------------------------
        # Tree Medium (96x124)
        tree_p = "assets/pydew/objects/tree_medium.png"
        if os.path.exists(tree_p):
            t_img = pygame.image.load(tree_p).convert_alpha()
            for s in ["spring", "summer", "fall", "winter"]:
                t_surf = pygame.Surface((104, 134), pygame.SRCALPHA)
                pygame.draw.ellipse(t_surf, (0, 0, 0, 55), (14, 114, 76, 16))
                t_scaled = t_img.copy()
                if s == "fall":
                    tint = pygame.Surface(t_scaled.get_size(), pygame.SRCALPHA)
                    tint.fill((210, 110, 40, 85))
                    t_scaled.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                elif s == "winter":
                    tint = pygame.Surface(t_scaled.get_size(), pygame.SRCALPHA)
                    tint.fill((200, 225, 245, 105))
                    t_scaled.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                t_surf.blit(t_scaled, (4, 4))
                self.textures[f"tree_{s}"] = t_surf
            self.textures["tree"] = self.textures["tree_spring"]
        else:
            for s in ["spring", "summer", "fall", "winter"]:
                self.textures[f"tree_{s}"] = pygame.Surface((104, 134), pygame.SRCALPHA)
            self.textures["tree"] = self.textures["tree_spring"]

        # Tree Stumps
        stump_p = "assets/pydew/objects/stump_medium.png"
        if os.path.exists(stump_p):
            st_img = pygame.image.load(stump_p).convert_alpha()
            st_scaled = pygame.transform.scale(st_img, (52, 52))
            st_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.ellipse(st_surf, (0, 0, 0, 45), (4, 42, 48, 12))
            st_surf.blit(st_scaled, (4, 4))
            self.textures["tree_stump"] = st_surf
        else:
            self.textures["tree_stump"] = pygame.Surface((60, 60), pygame.SRCALPHA)

        # Log
        log_p = "assets/pydew/objects/stump_small.png"
        if os.path.exists(log_p):
            l_img = pygame.image.load(log_p).convert_alpha()
            l_scaled = pygame.transform.scale(l_img, (44, 48))
            l_surf = pygame.Surface((56, 56), pygame.SRCALPHA)
            pygame.draw.ellipse(l_surf, (0, 0, 0, 45), (4, 38, 44, 12))
            l_surf.blit(l_scaled, (4, 4))
            self.textures["log"] = l_surf
        else:
            self.textures["log"] = pygame.Surface((56, 56), pygame.SRCALPHA)

        # Weeds / Bushes
        bush_p = "assets/pydew/objects/bush.png"
        if os.path.exists(bush_p):
            b_img = pygame.image.load(bush_p).convert_alpha()
            b_scaled = pygame.transform.scale(b_img, (54, 52))
            b_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.ellipse(b_surf, (0, 0, 0, 40), (4, 42, 48, 12))
            b_surf.blit(b_scaled, (4, 4))
            self.textures["weeds"] = b_surf
        else:
            self.textures["weeds"] = pygame.Surface((60, 60), pygame.SRCALPHA)

        # Small Rock (Clean Pixel Art)
        rock_s = pygame.Surface((52, 48), pygame.SRCALPHA)
        pygame.draw.ellipse(rock_s, (0, 0, 0, 45), (4, 32, 44, 14))
        pygame.draw.ellipse(rock_s, (148, 154, 160), (6, 12, 38, 28))
        pygame.draw.ellipse(rock_s, (90, 95, 100), (6, 12, 38, 28), 2)
        pygame.draw.arc(rock_s, (225, 232, 240), (10, 14, 30, 18), math.pi * 0.3, math.pi * 1.1, 3)
        self.textures["rock_small"] = rock_s

        # Boulder (Large Granite)
        boulder = pygame.Surface((64, 60), pygame.SRCALPHA)
        pygame.draw.ellipse(boulder, (0, 0, 0, 50), (4, 40, 56, 16))
        pygame.draw.ellipse(boulder, (125, 130, 136), (4, 10, 54, 42))
        pygame.draw.polygon(boulder, (172, 178, 186), [(14, 14), (36, 12), (48, 26), (30, 32)])
        pygame.draw.polygon(boulder, (88, 92, 98), [(8, 30), (28, 46), (48, 44), (54, 32)])
        pygame.draw.ellipse(boulder, (60, 64, 70), (4, 10, 54, 42), 2)
        self.textures["boulder"] = boulder

        # ---------------------------------------------------------
        # 3. STONE AGE NATURAL PICKUPS & FORAGING
        # ---------------------------------------------------------
        self._gen_stone_age_assets(ts)

        # ---------------------------------------------------------
        # 4. ALL-IN-ONE MASTER BUNDLE (MEGAFAUNA & WILD FLORA)
        # ---------------------------------------------------------
        self._load_all_stone_age_bundle_assets(ts)

    def _gen_stone_age_assets(self, ts):
        """Generates authentic pixel-art assets for the Stone Age progression."""
        sz = 32

        # -------------------------------------------------------------
        # 1. GROUND PICKUPS & FORAGING OBSTACLES (64x64)
        # -------------------------------------------------------------
        # Branch (Dried Fallen Sticks)
        branch_s = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(branch_s, (0, 0, 0, 35), (8, 44, 48, 12))
        pygame.draw.line(branch_s, (110, 68, 36), (12, 48), (52, 28), 5)
        pygame.draw.line(branch_s, (85, 48, 22), (18, 30), (46, 50), 4)
        pygame.draw.line(branch_s, (130, 85, 45), (32, 38), (40, 24), 3)
        pygame.draw.line(branch_s, (80, 130, 50), (42, 24), (45, 20), 2)  # Tiny green leaf
        self.textures["branch"] = branch_s

        # Pebble (River Stones & Flint)
        pebble_s = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(pebble_s, (0, 0, 0, 40), (10, 38, 44, 14))
        pygame.draw.ellipse(pebble_s, (150, 155, 160), (14, 28, 20, 14))
        pygame.draw.ellipse(pebble_s, (90, 95, 100), (14, 28, 20, 14), 2)
        pygame.draw.ellipse(pebble_s, (120, 125, 130), (28, 32, 18, 12))
        pygame.draw.ellipse(pebble_s, (70, 75, 80), (28, 32, 18, 12), 2)
        # Sharp Flint Shard in the cluster
        pygame.draw.polygon(pebble_s, (50, 55, 65), [(24, 22), (32, 16), (28, 30)])
        pygame.draw.polygon(pebble_s, (110, 120, 140), [(24, 22), (32, 16), (28, 30)], 1)
        self.textures["pebble"] = pebble_s

        # Wild Bush (Bụi Dâu Rừng)
        bush_s = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(bush_s, (0, 0, 0, 45), (6, 42, 52, 14))
        pygame.draw.ellipse(bush_s, (55, 135, 45), (10, 16, 44, 34))
        pygame.draw.ellipse(bush_s, (75, 165, 60), (14, 18, 36, 26))
        pygame.draw.ellipse(bush_s, (35, 95, 30), (10, 16, 44, 34), 2)
        # Wild berries glowing on bush
        berry_locs = [(18, 26), (28, 22), (38, 25), (22, 34), (32, 36), (42, 32)]
        for bx, by in berry_locs:
            pygame.draw.circle(bush_s, (220, 40, 50), (bx, by), 4)
            pygame.draw.circle(bush_s, (255, 140, 150), (bx - 1, by - 1), 2)
        self.textures["wild_bush"] = bush_s

        # Clay Patch (Đất Sét Bờ Suối)
        clay_s = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(clay_s, (165, 95, 50), (8, 20, 48, 30))
        pygame.draw.ellipse(clay_s, (195, 120, 70), (14, 24, 36, 20))
        pygame.draw.ellipse(clay_s, (120, 65, 30), (8, 20, 48, 30), 2)
        pygame.draw.circle(clay_s, (220, 150, 90), (22, 30), 4)
        self.textures["clay_patch"] = clay_s

        # Copper Rock (Tảng Đá Quặng Đồng)
        crock_s = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(crock_s, (0, 0, 0, 50), (6, 40, 52, 16))
        pygame.draw.ellipse(crock_s, (120, 125, 130), (8, 14, 48, 36))
        pygame.draw.ellipse(crock_s, (70, 75, 80), (8, 14, 48, 36), 2)
        # Copper ore glittering veins
        pygame.draw.polygon(crock_s, (225, 120, 40), [(18, 24), (26, 20), (32, 28), (22, 32)])
        pygame.draw.polygon(crock_s, (255, 160, 70), [(30, 24), (38, 18), (44, 26), (36, 30)])
        pygame.draw.circle(crock_s, (255, 210, 130), (24, 23), 2)
        pygame.draw.circle(crock_s, (255, 210, 130), (36, 22), 2)
        self.textures["copper_rock"] = crock_s


    def _load_all_stone_age_bundle_assets(self, ts=64):
        """
        Loads and registers all 287+ transparent PNG sprites, megafauna wildlife,
        woodcutting progression, 3-stage flora lifecycles, and tribal UI from
        assets/stone_age/ and the all-in-one master bundle.
        """
        import os
        base_dir = "assets/stone_age"
        if not os.path.exists(base_dir):
            base_dir = "stone_age_rts_complete_all_in_one_bundle/02_SLICED_SPRITES_128_PNG"
        if not os.path.exists(base_dir):
            base_dir = "stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack"
        if not os.path.exists(base_dir):
            return

        # 1. Bulk load all PNG files across all subcategories
        for root, _, files in os.walk(base_dir):
            for f in sorted(files):
                if not f.endswith(".png"):
                    continue
                full_path = os.path.join(root, f)
                base_name = os.path.splitext(f)[0]
                try:
                    surf = pygame.image.load(full_path).convert_alpha()
                    self.textures[base_name] = surf
                    self.textures[f] = surf
                except Exception:
                    continue


        # 3. Megafauna Wildlife Sprites
        beast_scales = {
            "mammoth_walk": ("wildlife_mammoth_and_smilodon_01", (96, 76)),
            "mammoth_idle": ("wildlife_mammoth_and_smilodon_02", (96, 76)),
            "mammoth_action": ("wildlife_mammoth_and_smilodon_03", (96, 76)),
            "sabertooth_idle": ("wildlife_mammoth_and_smilodon_04", (68, 50)),
            "sabertooth_stalk": ("wildlife_mammoth_and_smilodon_05", (68, 50)),
            "sabertooth_pounce": ("wildlife_mammoth_and_smilodon_06", (68, 50)),
            "bison_charge": ("wildlife_steppe_bison_01", (78, 62)),
            "bison_graze": ("wildlife_steppe_bison_03", (78, 62)),
            "cave_bear_walk": ("wildlife_cavebear_and_direwolf_01", (76, 58)),
            "cave_bear_stand": ("wildlife_cavebear_and_direwolf_02", (76, 58)),
            "dire_wolf_run": ("wildlife_cavebear_and_direwolf_04", (56, 42)),
            "dire_wolf_howl": ("wildlife_cavebear_and_direwolf_05", (56, 42)),
            "wild_boar": ("wildlife_wild_boar_01", (52, 38)),
            "marsh_crocodile": ("wildlife_crocodilian_and_fish_01", (80, 42)),
            "fish_shoal": ("wildlife_crocodilian_and_fish_04", (40, 26)),
        }
        for alias, (src_key, sz) in beast_scales.items():
            if src_key in self.textures:
                self.textures[alias] = pygame.transform.smoothscale(self.textures[src_key], sz)

        # 4. Woodcutting Progression (4 Stages)
        if "woodcut_stage1_intact_oak_06" in self.textures:
            self.textures["woodcut_stage_intact"] = pygame.transform.smoothscale(self.textures["woodcut_stage1_intact_oak_06"], (120, 138))
            self.textures["tree"] = self.textures["woodcut_stage_intact"]
        if "woodcut_stage2_notched_oak_07" in self.textures:
            self.textures["woodcut_stage_notched"] = pygame.transform.smoothscale(self.textures["woodcut_stage2_notched_oak_07"], (120, 138))
        if "woodcut_stage3_felled_stump_08" in self.textures:
            stump_surf = pygame.transform.smoothscale(self.textures["woodcut_stage3_felled_stump_08"], (64, 52))
            self.textures["woodcut_stage_stump"] = stump_surf
            self.textures["tree_stump"] = stump_surf
        if "woodcut_logs_bundle_10" in self.textures:
            logs_surf = pygame.transform.smoothscale(self.textures["woodcut_logs_bundle_10"], (56, 48))
            self.textures["woodcut_stage_logs"] = logs_surf
            self.textures["log"] = logs_surf
            self.textures["branch_logs"] = logs_surf
        if "woodcut_split_timber_11" in self.textures:
            timber_surf = pygame.transform.smoothscale(self.textures["woodcut_split_timber_11"], (48, 48))
            self.textures["woodcut_stage_timber"] = timber_surf
            self.textures["branch_wood"] = timber_surf
            self.textures["branch"] = timber_surf

        # Trees for Biomes
        if "tree_primeval_fern_cycad_01" in self.textures:
            self.textures["tree_forest"] = pygame.transform.smoothscale(self.textures["tree_primeval_fern_cycad_01"], (112, 134))
        if "tree_tundra_spruce_birch_01" in self.textures:
            self.textures["tree_tundra"] = pygame.transform.smoothscale(self.textures["tree_tundra_spruce_birch_01"], (112, 134))
        if "tree_swamp_mangrove_01" in self.textures:
            self.textures["tree_swamp"] = pygame.transform.smoothscale(self.textures["tree_swamp_mangrove_01"], (112, 134))

        # 5. Forageable Flora (3-Stage Growth: Sprout, Ripe, Depleted)
        # Berry Bush
        for i, idx in enumerate(["01", "02", "03"]):
            k = f"flora_berry_bush_stage_{idx}"
            if k in self.textures:
                self.textures[f"wild_bush_sprout_{i}"] = pygame.transform.smoothscale(self.textures[k], (46, 46))
        for i, idx in enumerate(["04", "05", "06"]):
            k = f"flora_berry_bush_stage_{idx}"
            if k in self.textures:
                s = pygame.transform.smoothscale(self.textures[k], (56, 56))
                self.textures[f"wild_bush_{i}"] = s
                self.textures[f"wild_bush_ripe_{i}"] = s
                if i == 0:
                    self.textures["wild_bush"] = s
                    self.textures["flora_berries"] = s
        for i, idx in enumerate(["07", "08", "09"]):
            k = f"flora_berry_bush_stage_{idx}"
            if k in self.textures:
                self.textures[f"wild_bush_depleted_{i}"] = pygame.transform.smoothscale(self.textures[k], (48, 48))

        # Grain / Fiber Reeds
        for i, idx in enumerate(["04", "05", "06"]):
            k = f"flora_grain_fiber_reed_stage_{idx}"
            if k in self.textures:
                s = pygame.transform.smoothscale(self.textures[k], (56, 56))
                self.textures[f"flora_grain_{i}"] = s
                if i == 0:
                    self.textures["flora_grain"] = s

        # Prehistoric Mushrooms & Herbs
        for i, idx in enumerate(["04", "05", "06"]):
            k = f"flora_mushroom_herb_stage_{idx}"
            if k in self.textures:
                s = pygame.transform.smoothscale(self.textures[k], (56, 56))
                self.textures[f"flora_mushroom_{i}"] = s
                if i == 0:
                    self.textures["flora_mushroom"] = s
                    self.textures["prop_mushroom"] = s

        # 6. UI HUD & Minimap Frame
        if "03_hud_bone_amber_minimap_ring" in self.textures:
            ring = pygame.transform.smoothscale(self.textures["03_hud_bone_amber_minimap_ring"], (188, 188))
            self.textures["hud_minimap_round_frame"] = ring
            self.textures["minimap_bone_frame"] = ring

        if "01_hud_stone_panel_slots" in self.textures:
            self.textures["hud_stone_panel"] = self.textures["01_hud_stone_panel_slots"]
        if "02_hud_stone_panel_inventory" in self.textures:
            self.textures["hud_inventory"] = self.textures["02_hud_stone_panel_inventory"]

        # Stone Age Resource & Tech Icons
        icon_map = {
            "icon_meat": "04_icon_res_raw_meat",
            "icon_berries": "05_icon_res_crimson_berries",
            "icon_flint": "06_icon_res_flint_spearhead",
            "icon_wood": "07_icon_res_timber_logs",
            "icon_bone": "08_icon_res_mammoth_ivory",
            "icon_ivory": "08_icon_res_mammoth_ivory",
            "icon_warmth": "09_icon_res_campfire_warmth",
            "tech_fire": "10_tech_fire_mastery",
            "tech_flintknapping": "11_tech_flintknapping",
            "tech_hunting": "12_tech_spear_hunting",
            "tech_clothing": "13_tech_hide_clothing",
            "tech_rituals": "14_tech_megalithic_rituals",
            "tech_domestication": "15_tech_mammoth_domestication",
        }
        for alias, src_k in icon_map.items():
            if src_k in self.textures:
                self.textures[alias] = pygame.transform.smoothscale(self.textures[src_k], (36, 36))

        # 7. Bridges and Waypoints
        if "river_crossing_bridge_01" in self.textures:
            self.textures["bridge_ford_full"] = self.textures["river_crossing_bridge_01"]
            self.textures["bridge_ford"] = pygame.transform.smoothscale(self.textures["river_crossing_bridge_01"], (ts, ts))
        if "river_crossing_bridge_02" in self.textures:
            self.textures["bridge_log_full"] = self.textures["river_crossing_bridge_02"]
            self.textures["bridge_log"] = pygame.transform.smoothscale(self.textures["river_crossing_bridge_02"], (ts, ts))

        for idx, wkey in [("01", "waypoint_inukshuk"), ("02", "waypoint_skull_pole"), ("03", "waypoint_carved_tree"), ("04", "waypoint_blaze_post")]:
            k = f"waypoint_marker_{idx}"
            if k in self.textures:
                self.textures[wkey] = pygame.transform.scale(self.textures[k], (64, 80))

        # 8. Fog of War & VFX
        if "fow_tile_row1_01" in self.textures:
            self.textures["fow_shroud"] = pygame.transform.scale(self.textures["fow_tile_row1_01"], (ts, ts))
        if "fow_tile_row2_01" in self.textures:
            self.textures["fow_memory"] = pygame.transform.scale(self.textures["fow_tile_row2_01"], (ts, ts))
        if "vision_cone_upper_01" in self.textures:
            self.textures["fow_vision_cone"] = self.textures["vision_cone_upper_01"]
        if "blind_ping_sound_and_tracks_01" in self.textures:
            self.textures["blind_ping_sound"] = self.textures["blind_ping_sound_and_tracks_01"]

    def load_audio(self):
        try:
            audio_map = {
                "water": "assets/audio/water.mp3",
                "swish": "assets/audio/plant.mp3",
                "ambient": "assets/audio/bg.mp3",
                "success": "assets/audio/success.wav",
            }
            for name, path in audio_map.items():
                if os.path.exists(path):
                    self.sounds[name] = pygame.mixer.Sound(path)
                    self.sounds[name].set_volume(0.3)
        except Exception as e:
            print("Lỗi nạp audio:", e)

    def play_sound(self, name):
        if name in self.sounds and self.sounds[name]:
            try:
                self.sounds[name].play()
            except Exception:
                pass
