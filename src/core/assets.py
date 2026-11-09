"""
Master Asset Manager for Green Valley Tales.
Loads authentic Stardew Valley-style pixel art:
- High-res PyDew Valley hand-painted world terrain and character animations
- Sprout Lands animated chickens, cows, coops, and shipping chests
- Crisp DejaVu Sans Bold Vietnamese typography (100% diacritics support)
- Studio sound effects and ambient audio
"""

import pygame
import os
import math
from src.settings import TILE_SIZE, PALETTE, SEASONS, CROPS_DATA, FISH_DATA, ANIMAL_DATA

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
        self.town_lamp_positions = []
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

            # Horizontal bedding plane crevices
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

        # Prehistoric Structures (Rock Shelter, Tipis, Workshop, Smoker, Shrine, Palisade Gate)
        bld_map = {
            "rock_shelter": ("stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack/03_buildings_structures/01_ancestral_rock_shelter.png", (256, 213)),
            "tipis": ("stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack/03_buildings_structures/02_hide_tipis_and_thatch_hut.png", (160, 133)),
            "workshop": ("stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack/03_buildings_structures/03_flintknapping_workshop.png", (160, 133)),
            "smoker": ("stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack/03_buildings_structures/04_meat_smoking_and_tanning_racks.png", (160, 133)),
            "shrine": ("stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack/03_buildings_structures/05_megalithic_totem_shrine.png", (160, 133)),
            "palisade": ("stone_age_rts_sliced_assets_pack/stone_age_rts_asset_pack/03_buildings_structures/06_palisade_gate_and_watchtower.png", (180, 150)),
        }
        for bk, (bp, bsz) in bld_map.items():
            if os.path.exists(bp):
                b_raw = pygame.image.load(bp).convert_alpha()
                self.textures[bk] = pygame.transform.smoothscale(b_raw, bsz)

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
        # 2. PLAYER ANIMATIONS (STONE AGE PRIMITIVE HUNTER, 172x124)
        # ---------------------------------------------------------
        self._gen_caveman_player_sprites()

        # ---------------------------------------------------------
        # 3. ANIMALS (SPROUT LANDS CHICKEN & COW)
        # ---------------------------------------------------------
        # Chicken (4 frames)
        c_path = "assets/sprout_lands/Characters/Chicken.png"
        if os.path.exists(c_path):
            c_sheet = pygame.image.load(c_path).convert_alpha()
            for f in range(4):
                # 16x16 per cell
                sub = c_sheet.subsurface(pygame.Rect((f % 2) * 16, (f // 2) * 16, 16, 16))
                scaled = pygame.transform.scale_by(sub, 2.3)
                # Composite with soft shadow
                c_surf = pygame.Surface((44, 44), pygame.SRCALPHA)
                pygame.draw.ellipse(c_surf, (0, 0, 0, 45), (6, 32, 30, 8))
                c_surf.blit(scaled, (4, 4))
                self.textures[f"chicken_{f}"] = c_surf
        else:
            for f in range(4):
                self.textures[f"chicken_{f}"] = pygame.Surface((44, 44), pygame.SRCALPHA)

        # Cow (3 frames)
        cow_path = "assets/sprout_lands/Characters/Cow.png"
        if os.path.exists(cow_path):
            cow_sheet = pygame.image.load(cow_path).convert_alpha()
            for f in range(3):
                # 32x32 per cell
                sub = cow_sheet.subsurface(pygame.Rect(f * 32, 0, 32, 32))
                scaled = pygame.transform.scale_by(sub, 2.2)
                cow_surf = pygame.Surface((78, 78), pygame.SRCALPHA)
                pygame.draw.ellipse(cow_surf, (0, 0, 0, 50), (8, 62, 58, 12))
                cow_surf.blit(scaled, (4, 4))
                self.textures[f"cow_{f}"] = cow_surf
        else:
            for f in range(3):
                self.textures[f"cow_{f}"] = pygame.Surface((78, 78), pygame.SRCALPHA)

        # Aliases for prehistoric livestock
        for f in range(4):
            if f"chicken_{f}" in self.textures:
                self.textures[f"wild_chicken_{f}"] = self.textures[f"chicken_{f}"]
        for f in range(3):
            if f"cow_{f}" in self.textures:
                self.textures[f"aurochs_{f}"] = self.textures[f"cow_{f}"]

        # Animal Products: Egg & Milk
        egg_path = "assets/sprout_lands/Objects/Egg item.png"
        if os.path.exists(egg_path):
            e_img = pygame.image.load(egg_path).convert_alpha()
            self.textures["prod_egg"] = pygame.transform.scale(e_img, (28, 28))
        else:
            e_surf = pygame.Surface((28, 28), pygame.SRCALPHA)
            pygame.draw.ellipse(e_surf, (245, 235, 205), (4, 4, 20, 22))
            self.textures["prod_egg"] = e_surf

        milk_path = "assets/sprout_lands/Objects/Simple Milk and grass item.png"
        if os.path.exists(milk_path):
            m_img = pygame.image.load(milk_path).convert_alpha()
            m_sub = m_img.subsurface(pygame.Rect(0, 0, 16, 16))
            self.textures["prod_milk"] = pygame.transform.scale(m_sub, (28, 28))
        else:
            m_surf = pygame.Surface((28, 28), pygame.SRCALPHA)
            pygame.draw.rect(m_surf, (240, 245, 255), (6, 6, 16, 20), border_radius=4)
            self.textures["prod_milk"] = m_surf

        # ---------------------------------------------------------
        # 4. BUILDINGS & INTERACTIVE OBJECTS
        # ---------------------------------------------------------
        # Shipping Bin (Prehistoric Mammoth Hide & Timber Chest)
        bin_surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.ellipse(bin_surf, (0, 0, 0, 65), (4, 44, 56, 16))
        pygame.draw.rect(bin_surf, (95, 60, 32), (8, 20, 48, 32), border_radius=4)
        pygame.draw.rect(bin_surf, (65, 40, 20), (8, 20, 48, 32), 2, border_radius=4)
        pygame.draw.polygon(bin_surf, (155, 105, 55), [(6, 18), (58, 18), (56, 38), (8, 38)])
        for fx in range(10, 56, 6):
            pygame.draw.polygon(bin_surf, (135, 85, 40), [(fx, 38), (fx + 3, 43), (fx + 6, 38)])
        pygame.draw.line(bin_surf, (80, 50, 25), (18, 18), (18, 50), 3)
        pygame.draw.line(bin_surf, (80, 50, 25), (46, 18), (46, 50), 3)
        pygame.draw.polygon(bin_surf, (245, 240, 225), [(28, 24), (36, 24), (32, 40)])
        pygame.draw.polygon(bin_surf, (200, 195, 180), [(28, 24), (36, 24), (32, 40)], 1)
        pygame.draw.circle(bin_surf, (190, 50, 40), (32, 44), 3)
        pygame.draw.arc(bin_surf, (190, 50, 40), (29, 41, 6, 6), 0, math.pi, 1)
        self.textures["shipping_bin"] = bin_surf

        # Chicken Coop / Prehistoric Fowl Pen (Dry-stone circular pen with straw-thatched dome)
        c_surf = pygame.Surface((108, 108), pygame.SRCALPHA)
        pygame.draw.ellipse(c_surf, (0, 0, 0, 55), (8, 84, 92, 20))
        # Stone wall base
        pygame.draw.ellipse(c_surf, (110, 115, 120), (14, 52, 80, 42))
        pygame.draw.ellipse(c_surf, (75, 80, 85), (14, 52, 80, 42), 3)
        # Thatched cone roof
        pygame.draw.polygon(c_surf, (185, 150, 75), [(10, 64), (54, 12), (98, 64)])
        pygame.draw.polygon(c_surf, (145, 115, 55), [(10, 64), (54, 12), (98, 64)], 3)
        # Straw texture ridges
        for rx, ry in [(25, 54), (40, 42), (54, 30), (68, 42), (83, 54)]:
            pygame.draw.line(c_surf, (220, 185, 95), (rx, ry), (54, 14), 2)
        # Small entrance archway
        pygame.draw.ellipse(c_surf, (35, 25, 20), (44, 70, 20, 24))
        pygame.draw.ellipse(c_surf, (190, 160, 80), (46, 84, 16, 8)) # Straw bedding at doorstep
        self.textures["barn"] = c_surf

        # Merchant
        merch_p = "assets/pydew/objects/merchant.png"
        if os.path.exists(merch_p):
            m_img = pygame.image.load(merch_p).convert_alpha()
            self.textures["merchant"] = pygame.transform.scale(m_img, (60, 72))

        # ---------------------------------------------------------
        # 5. OBSTACLES & NATURE (LAND CLEARING)
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
        # 6. CROPS & FRUITS (64x64)
        # ---------------------------------------------------------
        # Tomato from PyDew (safe fallback if tomato in crops)
        tomato_stages = CROPS_DATA.get("tomato", {}).get("stages", 4)
        for stage in range(tomato_stages):
            # The source sheet has four frames while tomato has five growth
            # stages. Reuse its ripe frame for the mature stage.
            tp = f"assets/pydew/fruit/tomato/{min(stage, 3)}.png"
            if os.path.exists(tp):
                t_img = pygame.image.load(tp).convert_alpha()
                self.textures[f"crop_tomato_{stage}"] = pygame.transform.scale(t_img, (ts, ts))
            else:
                self.textures[f"crop_tomato_{stage}"] = pygame.Surface((ts, ts), pygame.SRCALPHA)

        # Corn from PyDew (safe fallback if corn in crops)
        corn_stages = CROPS_DATA.get("corn", {}).get("stages", 4)
        for stage in range(corn_stages):
            cp = f"assets/pydew/fruit/corn/{min(stage, 3)}.png"
            if os.path.exists(cp):
                c_img = pygame.image.load(cp).convert_alpha()
                self.textures[f"crop_corn_{stage}"] = pygame.transform.scale(c_img, (ts, ts))
            else:
                self.textures[f"crop_corn_{stage}"] = pygame.Surface((ts, ts), pygame.SRCALPHA)

        # Other crops: Turnip, Strawberry, Potato, Pumpkin, etc.
        self._gen_crop_sprites(ts)

        # ---------------------------------------------------------
        # 7. TOOL ICONS & ITEMS
        # ---------------------------------------------------------
        self._gen_item_icons()

        # ---------------------------------------------------------
        # 8. TOWN & RARE EXCAVATION ASSETS
        # ---------------------------------------------------------
        self._gen_town_and_rare_assets(ts)

        # ---------------------------------------------------------
        # 9. STONE AGE ASSETS (PICKUPS, PRIMITIVE TOOLS & FOOD)
        # ---------------------------------------------------------
        self._gen_stone_age_assets(ts)

        # ---------------------------------------------------------
        # 10. ALL-IN-ONE MASTER BUNDLE INTEGRATION (287 SPRITES RGBA)
        # ---------------------------------------------------------
        self._load_all_stone_age_bundle_assets(ts)

    def _gen_crop_sprites(self, ts):
        """Generates pixel-perfect crop stage sprites for non-pydew crops."""
        crop_palettes = {
            "turnip": (235, 80, 80),
            "potato": (210, 160, 95),
            "strawberry": (240, 50, 70),
            "cabbage": (110, 205, 95),
            "pepper": (230, 45, 35),
            "eggplant": (115, 55, 140),
            "pumpkin": (235, 130, 35),
            "carrot": (240, 115, 35)
        }

        for cid, col in crop_palettes.items():
            # Some palette entries are reusable prototype crops rather than
            # currently purchasable crops, so retain a safe four-stage default.
            stage_count = CROPS_DATA.get(cid, {}).get("stages", 4)
            for stage in range(stage_count):
                surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
                if stage == 0:
                    # Sprout
                    pygame.draw.line(surf, (85, 175, 55), (ts // 2, ts - 8), (ts // 2, ts - 20), 3)
                    pygame.draw.circle(surf, (115, 210, 75), (ts // 2 - 5, ts - 21), 4)
                    pygame.draw.circle(surf, (115, 210, 75), (ts // 2 + 5, ts - 21), 4)
                elif stage == 1:
                    # Bush
                    pygame.draw.line(surf, (70, 160, 45), (ts // 2, ts - 8), (ts // 2, ts - 26), 4)
                    pygame.draw.ellipse(surf, (95, 195, 65), (ts // 2 - 14, ts - 28, 14, 10))
                    pygame.draw.ellipse(surf, (95, 195, 65), (ts // 2, ts - 28, 14, 10))
                elif stage == 2:
                    # Blooming
                    pygame.draw.line(surf, (60, 150, 40), (ts // 2, ts - 8), (ts // 2, ts - 32), 4)
                    pygame.draw.ellipse(surf, (90, 185, 60), (ts // 2 - 18, ts - 34, 16, 12))
                    pygame.draw.ellipse(surf, (90, 185, 60), (ts // 2 + 2, ts - 34, 16, 12))
                    pygame.draw.circle(surf, (255, 245, 140), (ts // 2, ts - 26), 5)
                else:
                    # Ripe Fruit
                    pygame.draw.line(surf, (55, 140, 35), (ts // 2, ts - 8), (ts // 2, ts - 36), 4)
                    pygame.draw.ellipse(surf, (80, 175, 50), (ts // 2 - 20, ts - 38, 18, 14))
                    pygame.draw.ellipse(surf, (80, 175, 50), (ts // 2 + 2, ts - 38, 18, 14))
                    # Fruit body
                    pygame.draw.ellipse(surf, (0, 0, 0, 45), (ts // 2 - 12, ts - 18, 24, 8))
                    pygame.draw.circle(surf, col, (ts // 2, ts - 26), 14)
                    darker = (max(0, col[0] - 45), max(0, col[1] - 45), max(0, col[2] - 45))
                    pygame.draw.circle(surf, darker, (ts // 2, ts - 26), 14, 2)
                    lighter = (min(255, col[0] + 65), min(255, col[1] + 65), min(255, col[2] + 65))
                    pygame.draw.circle(surf, lighter, (ts // 2 - 4, ts - 30), 4)

                self.textures[f"crop_{cid}_{stage}"] = surf

    def _gen_item_icons(self):
        sz = 32

        # Tools from PyDew overlay
        tool_files = {
            "tool_hoe": "assets/pydew/overlay/hoe.png",
            "tool_axe": "assets/pydew/overlay/axe.png",
            "tool_water_can": "assets/pydew/overlay/water.png"
        }
        for tid, p in tool_files.items():
            if os.path.exists(p):
                img = pygame.image.load(p).convert_alpha()
                self.textures[tid] = pygame.transform.scale(img, (sz, sz))

        # Pickaxe, Scythe, Fishing Rod
        pick = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(pick, (155, 108, 62), (5, sz - 5), (sz - 7, 7), 4)
        pygame.draw.arc(pick, (215, 222, 230), (sz - 22, 2, 20, 20), 0, math.pi * 0.75, 5)
        self.textures["tool_pickaxe"] = pick

        scy = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(scy, (155, 108, 62), (5, sz - 5), (sz - 7, 7), 4)
        pygame.draw.arc(scy, (225, 232, 240), (sz - 24, 2, 22, 18), 0, math.pi * 0.95, 4)
        self.textures["tool_scythe"] = scy

        rod = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(rod, (175, 125, 75), (4, sz - 4), (sz - 5, 4), 3)
        pygame.draw.circle(rod, (220, 220, 225), (10, sz - 10), 4)
        pygame.draw.line(rod, (240, 240, 250), (sz - 5, 4), (sz - 5, sz - 8), 1)
        pygame.draw.circle(rod, (235, 45, 40), (sz - 5, sz - 8), 4)
        self.textures["tool_fishing_rod"] = rod

        # Seed Bag Icon
        for crop_id in CROPS_DATA:
            seed_bag = pygame.Surface((sz, sz), pygame.SRCALPHA)
            pygame.draw.polygon(seed_bag, (218, 185, 128), [(6, 26), (25, 26), (28, 9), (4, 9)])
            pygame.draw.polygon(seed_bag, (148, 115, 68), [(6, 26), (25, 26), (28, 9), (4, 9)], 2)
            pygame.draw.rect(seed_bag, (188, 52, 42), (7, 12, 18, 8))
            self.textures[f"seed_{crop_id}"] = seed_bag

        # Produce Icons
        crop_colors = {
            "turnip": (235, 80, 80),
            "potato": (210, 160, 95),
            "strawberry": (240, 50, 70),
            "cabbage": (110, 205, 95),
            "tomato": (230, 50, 40),
            "corn": (245, 215, 60),
            "pepper": (230, 45, 35),
            "eggplant": (115, 55, 140),
            "pumpkin": (235, 130, 35),
            "carrot": (240, 115, 35)
        }
        for cid, col in crop_colors.items():
            icon = pygame.Surface((sz, sz), pygame.SRCALPHA)
            pygame.draw.ellipse(icon, (0, 0, 0, 45), (6, 24, 20, 6))
            pygame.draw.circle(icon, col, (16, 17), 11)
            pygame.draw.circle(icon, (max(0, col[0] - 40), max(0, col[1] - 40), max(0, col[2] - 40)), (16, 17), 11, 2)
            pygame.draw.circle(icon, (min(255, col[0] + 65), min(255, col[1] + 65), min(255, col[2] + 65)), (13, 13), 3)
            self.textures[f"produce_{cid}"] = icon

        # Materials
        wood = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.rect(wood, (142, 88, 48), (5, 10, 22, 11), border_radius=3)
        pygame.draw.ellipse(wood, (195, 145, 95), (5, 10, 8, 11))
        self.textures["mat_wood"] = wood

        stone = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.ellipse(stone, (145, 150, 158), (5, 8, 22, 17))
        pygame.draw.ellipse(stone, (85, 90, 96), (5, 8, 22, 17), 2)
        self.textures["mat_stone"] = stone

        fiber = pygame.Surface((sz, sz), pygame.SRCALPHA)
        for ox in [-5, 0, 5]:
            pygame.draw.line(fiber, (108, 175, 55), (16 + ox, 25), (16 + ox * 2, 7), 3)
        self.textures["mat_fiber"] = fiber

        # Hay
        hay = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.rect(hay, (225, 195, 85), (5, 8, 22, 16), border_radius=3)
        pygame.draw.line(hay, (160, 120, 40), (12, 8), (12, 24), 2)
        pygame.draw.line(hay, (160, 120, 40), (20, 8), (20, 24), 2)
        self.textures["supply_hay"] = hay

        # Fish icons
        for fish_id, data in FISH_DATA.items():
            f_surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
            col = data["color"]
            if fish_id == "shrimp":
                pygame.draw.arc(f_surf, col, (6, 6, 20, 20), 0, math.pi * 1.5, 5)
            else:
                pygame.draw.ellipse(f_surf, col, (4, 10, 18, 12))
                pygame.draw.polygon(f_surf, (max(0, col[0] - 30), max(0, col[1] - 30), max(0, col[2] - 30)),
                                    [(19, 16), (28, 9), (28, 23)])
                f_surf.set_at((8, 14), (255, 255, 255))
                f_surf.set_at((7, 14), (20, 20, 20))
            self.textures[f"fish_{fish_id}"] = f_surf

    def _gen_town_and_rare_assets(self, ts):
        """Generates town square composite terrain, shopfronts, NPCs, and rare artifact icons."""
        self.textures["town_composite"] = pygame.Surface((ts, ts))
        self.town_lamp_positions = []
        self.textures["farmhouse_exterior"] = pygame.Surface((ts, ts))

        # 3. Teleport Waypoint Pillar (64x64)
        wp_surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.circle(wp_surf, (120, 220, 255, 90), (ts // 2, ts - 16), 26)
        pygame.draw.circle(wp_surf, (80, 190, 255, 220), (ts // 2, ts - 16), 26, 2)
        pygame.draw.polygon(wp_surf, (200, 245, 255), [(ts // 2, ts - 32), (ts // 2 + 10, ts - 16), (ts // 2 - 10, ts - 16)])
        pygame.draw.polygon(wp_surf, (150, 160, 175), [(ts // 2 - 12, ts - 12), (ts // 2 + 12, ts - 12), (ts // 2 + 8, 12), (ts // 2 - 8, 12)])
        pygame.draw.polygon(wp_surf, (85, 95, 110), [(ts // 2 - 12, ts - 12), (ts // 2 + 12, ts - 12), (ts // 2 + 8, 12), (ts // 2 - 8, 12)], 2)
        pygame.draw.polygon(wp_surf, (100, 225, 255), [(ts // 2, 2), (ts // 2 + 7, 10), (ts // 2, 18), (ts // 2 - 7, 10)])
        pygame.draw.circle(wp_surf, (255, 255, 255), (ts // 2, 10), 3)
        self.textures["teleport_waypoint"] = wp_surf

        # 4. NPC Sprites (64x64)
        # Cô Mai
        mai = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(mai, (0, 0, 0, 45), (14, 52, 36, 10))
        pygame.draw.rect(mai, (90, 160, 100), (20, 28, 24, 26), border_radius=4)
        pygame.draw.rect(mai, (255, 255, 250), (23, 32, 18, 20), border_radius=2)
        pygame.draw.circle(mai, (255, 222, 185), (32, 18), 11)
        pygame.draw.circle(mai, (95, 55, 30), (32, 13), 11)
        pygame.draw.circle(mai, (230, 60, 75), (41, 12), 4)
        self.textures["npc_co_mai"] = mai

        # Bác Bảy
        bay = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(bay, (0, 0, 0, 45), (12, 52, 40, 10))
        pygame.draw.rect(bay, (70, 75, 85), (18, 26, 28, 28), border_radius=4)
        pygame.draw.rect(bay, (150, 90, 45), (21, 30, 22, 22), border_radius=2)
        pygame.draw.circle(bay, (235, 195, 155), (32, 18), 12)
        pygame.draw.ellipse(bay, (75, 75, 80), (22, 20, 20, 12))
        pygame.draw.rect(bay, (50, 50, 55), (20, 8, 24, 7), border_radius=3)
        self.textures["npc_bac_bay"] = bay

        # Cụ Ba Tri
        tri = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(tri, (0, 0, 0, 45), (14, 52, 36, 10))
        pygame.draw.rect(tri, (70, 110, 165), (20, 26, 24, 28), border_radius=4)
        pygame.draw.circle(tri, (245, 215, 180), (32, 18), 11)
        pygame.draw.ellipse(tri, (240, 240, 245), (23, 20, 18, 12))
        pygame.draw.circle(tri, (235, 235, 240), (32, 11), 10)
        pygame.draw.circle(tri, (255, 215, 60), (28, 18), 3, 1)
        pygame.draw.circle(tri, (255, 215, 60), (36, 18), 3, 1)
        self.textures["npc_cu_ba_tri"] = tri

        # 5. Nomadic Valley Trader & Mammoth Fur Trading Mat (128x128)
        rug = pygame.Surface((128, 128), pygame.SRCALPHA)
        # Drop shadow
        pygame.draw.ellipse(rug, (0, 0, 0, 45), (4, 8, 120, 112))
        # Giant stretched mammoth/bison hide mat
        pygame.draw.polygon(rug, (155, 110, 60), [(14, 16), (114, 14), (120, 110), (8, 112)])
        pygame.draw.polygon(rug, (125, 85, 45), [(14, 16), (114, 14), (120, 110), (8, 112)], 3)
        # Fur edge jagged tufts
        for fx in range(16, 114, 10):
            pygame.draw.polygon(rug, (100, 65, 35), [(fx, 14), (fx + 5, 8), (fx + 10, 14)])
            pygame.draw.polygon(rug, (100, 65, 35), [(fx, 110), (fx + 5, 116), (fx + 10, 110)])
        # Sacred tribal spiral and painted sun in center
        pygame.draw.circle(rug, (190, 50, 40), (64, 62), 22, 3)
        pygame.draw.circle(rug, (220, 150, 50), (64, 62), 12)
        # Dried herbal bundles & shiny shells at the four corners
        for cx, cy in [(20, 22), (108, 20), (16, 104), (112, 102)]:
            pygame.draw.circle(rug, (245, 240, 230), (cx, cy), 5)
            pygame.draw.circle(rug, (85, 140, 65), (cx + 3, cy - 2), 4)
        self.textures["magic_rug"] = rug

        # Nomadic Trader NPC (fur cowl, traveler pack with mammoth horns)
        merch = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(merch, (0, 0, 0, 50), (12, 50, 40, 12))
        # Deep leather traveler poncho
        pygame.draw.rect(merch, (120, 75, 45), (18, 24, 28, 30), border_radius=4)
        pygame.draw.rect(merch, (170, 120, 60), (22, 28, 20, 22), border_radius=2)
        # Traveler leather cowl / hood
        pygame.draw.ellipse(merch, (90, 55, 30), (16, 8, 32, 22))
        # Face inside hood
        pygame.draw.circle(merch, (220, 175, 135), (32, 19), 9)
        pygame.draw.circle(merch, (30, 20, 15), (30, 18), 2)
        pygame.draw.circle(merch, (30, 20, 15), (34, 18), 2)
        # Glowing green jade talisman
        pygame.draw.circle(merch, (50, 215, 130), (32, 32), 4)
        # Traveler staff with curved ram horn
        pygame.draw.line(merch, (110, 70, 35), (47, 10), (47, 56), 3)
        pygame.draw.arc(merch, (245, 240, 225), (42, 6, 12, 12), 0, math.pi * 1.5, 3)
        self.textures["wandering_merchant"] = merch

        # 6. Rare Artifacts & Commodities Icons (32x32)
        sz = 32

        # Mystic Geode
        geode = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.ellipse(geode, (80, 85, 95), (4, 4, 24, 24))
        pygame.draw.ellipse(geode, (50, 55, 65), (4, 4, 24, 24), 2)
        pygame.draw.polygon(geode, (185, 80, 240), [(12, 16), (16, 8), (20, 16), (16, 24)])
        pygame.draw.polygon(geode, (80, 230, 255), [(14, 16), (16, 11), (18, 16), (16, 21)])
        self.textures["rare_mystic_geode"] = geode

        # Gold Nugget
        nugget = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.polygon(nugget, (255, 215, 40), [(6, 18), (14, 6), (26, 10), (28, 22), (18, 28)])
        pygame.draw.polygon(nugget, (200, 140, 20), [(6, 18), (14, 6), (26, 10), (28, 22), (18, 28)], 2)
        pygame.draw.polygon(nugget, (255, 245, 150), [(12, 12), (18, 8), (22, 14)])
        self.textures["rare_gold_nugget"] = nugget

        # Ancient Amber
        amber = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.ellipse(amber, (245, 160, 30), (5, 5, 22, 22))
        pygame.draw.ellipse(amber, (190, 100, 15), (5, 5, 22, 22), 2)
        pygame.draw.circle(amber, (255, 215, 90), (11, 11), 3)
        pygame.draw.line(amber, (90, 45, 10), (14, 16), (18, 16), 2)
        pygame.draw.line(amber, (90, 45, 10), (16, 13), (16, 19), 1)
        self.textures["rare_ancient_amber"] = amber

        # Fossil Wood
        fwood = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.ellipse(fwood, (140, 110, 85), (4, 6, 24, 20))
        pygame.draw.ellipse(fwood, (85, 65, 45), (4, 6, 24, 20), 2)
        pygame.draw.ellipse(fwood, (110, 85, 65), (9, 10, 14, 12), 1)
        pygame.draw.circle(fwood, (70, 50, 35), (16, 16), 2)
        self.textures["rare_fossil_wood"] = fwood

        # Ancient Coin
        coin = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.circle(coin, (185, 140, 50), (16, 16), 12)
        pygame.draw.circle(coin, (120, 85, 25), (16, 16), 12, 2)
        pygame.draw.rect(coin, (40, 35, 30), (13, 13, 6, 6))
        self.textures["rare_ancient_coin"] = coin

        # Clay Relic
        pot = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.polygon(pot, (215, 115, 65), [(10, 8), (22, 8), (26, 18), (22, 26), (10, 26), (6, 18)])
        pygame.draw.polygon(pot, (140, 60, 25), [(10, 8), (22, 8), (26, 18), (22, 26), (10, 26), (6, 18)], 2)
        pygame.draw.line(pot, (255, 200, 140), (9, 16), (23, 16), 2)
        self.textures["rare_clay_relic"] = pot

        # Ancient Seed
        aseed = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.ellipse(aseed, (60, 180, 240), (8, 6, 16, 20))
        pygame.draw.ellipse(aseed, (25, 110, 175), (8, 6, 16, 20), 2)
        pygame.draw.circle(aseed, (200, 245, 255), (14, 12), 4)
        self.textures["item_ancient_seed"] = aseed

        # Magic Fertilizer
        mfert = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.polygon(mfert, (160, 65, 195), [(6, 26), (25, 26), (28, 9), (4, 9)])
        pygame.draw.polygon(mfert, (100, 30, 130), [(6, 26), (25, 26), (28, 9), (4, 9)], 2)
        pygame.draw.circle(mfert, (255, 235, 120), (16, 17), 5)
        self.textures["item_magic_fertilizer"] = mfert

        # Legendary Rod
        lrod = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(lrod, (255, 215, 50), (4, sz - 4), (sz - 5, 4), 3)
        pygame.draw.circle(lrod, (65, 215, 140), (10, sz - 10), 5)
        pygame.draw.circle(lrod, (255, 255, 255), (sz - 5, sz - 8), 4)
        self.textures["item_legendary_rod"] = lrod

        # Energy Elixir
        elixir = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.rect(elixir, (200, 160, 120), (13, 4, 6, 4))
        pygame.draw.polygon(elixir, (70, 225, 120), [(11, 8), (21, 8), (26, 24), (6, 24)])
        pygame.draw.polygon(elixir, (30, 135, 65), [(11, 8), (21, 8), (26, 24), (6, 24)], 2)
        pygame.draw.circle(elixir, (230, 255, 240), (16, 15), 4)
        self.textures["item_energy_elixir"] = elixir

        # Bag Voucher
        voucher = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.rect(voucher, (245, 230, 190), (6, 6, 20, 20), border_radius=3)
        pygame.draw.rect(voucher, (180, 140, 60), (6, 6, 20, 20), 2, border_radius=3)
        pygame.draw.circle(voucher, (220, 45, 40), (16, 16), 5)
        self.textures["item_bag_voucher"] = voucher

        # Mineral materials
        copp = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.ellipse(copp, (215, 125, 75), (5, 8, 22, 17))
        pygame.draw.ellipse(copp, (140, 65, 30), (5, 8, 22, 17), 2)
        self.textures["mat_copper_ore"] = copp

        iron = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.ellipse(iron, (185, 190, 205), (5, 8, 22, 17))
        pygame.draw.ellipse(iron, (90, 95, 110), (5, 8, 22, 17), 2)
        self.textures["mat_iron_ore"] = iron

        coal = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.polygon(coal, (45, 45, 50), [(6, 16), (14, 7), (25, 11), (27, 23), (16, 27)])
        pygame.draw.polygon(coal, (20, 20, 25), [(6, 16), (14, 7), (25, 11), (27, 23), (16, 27)], 2)
        self.textures["mat_coal"] = coal

        sbrick = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.rect(sbrick, (155, 150, 140), (5, 9, 22, 14), border_radius=2)
        pygame.draw.rect(sbrick, (90, 85, 80), (5, 9, 22, 14), 2, border_radius=2)
        self.textures["mat_stone_brick"] = sbrick

        # Supplies
        fert = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.polygon(fert, (150, 115, 75), [(6, 26), (25, 26), (28, 9), (4, 9)])
        pygame.draw.polygon(fert, (95, 65, 35), [(6, 26), (25, 26), (28, 9), (4, 9)], 2)
        self.textures["supply_fertilizer"] = fert

        bait = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.circle(bait, (225, 80, 70), (16, 16), 8)
        pygame.draw.circle(bait, (150, 40, 35), (16, 16), 8, 2)
        self.textures["supply_bait"] = bait

        lantern = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.rect(lantern, (180, 120, 45), (10, 8, 12, 16), border_radius=3)
        pygame.draw.rect(lantern, (255, 240, 150), (12, 10, 8, 12))
        self.textures["furn_town_lantern"] = lantern

    def _gen_caveman_player_sprites(self):
        """Generates authentic Stone Age Primitive Hunter animated player sprites (172x124)."""
        SKIN = (215, 165, 125)
        SKIN_SHADOW = (180, 130, 95)
        HAIR = (42, 28, 20)
        BONE = (245, 240, 230)
        FUR = (175, 115, 55)
        FUR_SPOT = (95, 55, 25)
        LEATHER = (110, 70, 40)
        FLINT = (85, 90, 100)
        WOOD = (120, 80, 45)
        WARPAINT = (200, 50, 40)
        CLAY = (175, 95, 55)
        WATER_COL = (80, 180, 240)

        # 1. WALK ANIMATIONS (down, up, left)
        for d in ['down', 'up', 'left']:
            for f in range(4):
                surf = pygame.Surface((172, 124), pygame.SRCALPHA)
                bob = -1 if f in (0, 2) else 0
                l_off = -4 if f == 0 else (4 if f == 2 else 0)
                r_off = 4 if f == 0 else (-4 if f == 2 else 0)

                if d == 'down':
                    # legs
                    pygame.draw.rect(surf, LEATHER, (78, 88 + bob + l_off, 5, 12), border_radius=2)
                    pygame.draw.rect(surf, LEATHER, (89, 88 + bob + r_off, 5, 12), border_radius=2)
                    # feet/fur moccasins
                    pygame.draw.ellipse(surf, FUR, (76, 98 + bob + l_off, 8, 5))
                    pygame.draw.ellipse(surf, FUR, (88, 98 + bob + r_off, 8, 5))
                    # fur pelt tunic
                    pygame.draw.polygon(surf, FUR, [(78, 65 + bob), (94, 65 + bob), (97, 88 + bob), (75, 88 + bob)])
                    pygame.draw.circle(surf, FUR_SPOT, (82, 72 + bob), 2)
                    pygame.draw.circle(surf, FUR_SPOT, (90, 78 + bob), 2)
                    pygame.draw.circle(surf, FUR_SPOT, (84, 83 + bob), 2)
                    pygame.draw.line(surf, LEATHER, (78, 65 + bob), (92, 84 + bob), 3)
                    # bone fang necklace
                    pygame.draw.arc(surf, LEATHER, (80, 60 + bob, 12, 8), 3.14, 0, 2)
                    pygame.draw.polygon(surf, BONE, [(84, 66 + bob), (86, 71 + bob), (88, 66 + bob)])
                    # arms
                    pygame.draw.rect(surf, SKIN, (72, 66 + bob - (l_off // 2), 5, 14), border_radius=2)
                    pygame.draw.rect(surf, SKIN, (95, 66 + bob - (r_off // 2), 5, 14), border_radius=2)
                    # head
                    pygame.draw.circle(surf, SKIN, (86, 52 + bob), 11)
                    pygame.draw.line(surf, WARPAINT, (81, 54 + bob), (83, 56 + bob), 2)
                    pygame.draw.line(surf, WARPAINT, (89, 54 + bob), (91, 56 + bob), 2)
                    pygame.draw.circle(surf, (30, 20, 15), (83, 51 + bob), 2)
                    pygame.draw.circle(surf, (30, 20, 15), (89, 51 + bob), 2)
                    # wild hair & bone hairpin
                    pygame.draw.ellipse(surf, HAIR, (74, 40 + bob, 24, 16))
                    pygame.draw.polygon(surf, HAIR, [(74, 46 + bob), (72, 56 + bob), (76, 52 + bob)])
                    pygame.draw.polygon(surf, HAIR, [(98, 46 + bob), (100, 56 + bob), (96, 52 + bob)])
                    pygame.draw.polygon(surf, BONE, [(76, 42 + bob), (96, 38 + bob), (95, 41 + bob), (75, 45 + bob)])

                elif d == 'up':
                    pygame.draw.rect(surf, LEATHER, (78, 88 + bob + l_off, 5, 12), border_radius=2)
                    pygame.draw.rect(surf, LEATHER, (89, 88 + bob + r_off, 5, 12), border_radius=2)
                    pygame.draw.ellipse(surf, FUR, (76, 98 + bob + l_off, 8, 5))
                    pygame.draw.ellipse(surf, FUR, (88, 98 + bob + r_off, 8, 5))
                    pygame.draw.polygon(surf, FUR, [(78, 65 + bob), (94, 65 + bob), (97, 88 + bob), (75, 88 + bob)])
                    pygame.draw.circle(surf, FUR_SPOT, (83, 74 + bob), 2)
                    pygame.draw.circle(surf, FUR_SPOT, (89, 81 + bob), 2)
                    pygame.draw.rect(surf, SKIN, (72, 66 + bob - (l_off // 2), 5, 14), border_radius=2)
                    pygame.draw.rect(surf, SKIN, (95, 66 + bob - (r_off // 2), 5, 14), border_radius=2)
                    pygame.draw.circle(surf, HAIR, (86, 52 + bob), 12)
                    pygame.draw.ellipse(surf, HAIR, (73, 40 + bob, 26, 22))
                    pygame.draw.polygon(surf, BONE, [(75, 42 + bob), (97, 38 + bob), (96, 41 + bob), (74, 45 + bob)])

                else: # left
                    pygame.draw.rect(surf, LEATHER, (82 + l_off, 88 + bob, 5, 12), border_radius=2)
                    pygame.draw.rect(surf, LEATHER, (86 + r_off, 88 + bob, 5, 12), border_radius=2)
                    pygame.draw.ellipse(surf, FUR, (80 + l_off, 98 + bob, 8, 5))
                    pygame.draw.ellipse(surf, FUR, (84 + r_off, 98 + bob, 8, 5))
                    pygame.draw.polygon(surf, FUR, [(80, 65 + bob), (92, 65 + bob), (94, 88 + bob), (78, 88 + bob)])
                    pygame.draw.circle(surf, FUR_SPOT, (85, 75 + bob), 2)
                    pygame.draw.rect(surf, SKIN, (83 + l_off, 68 + bob, 5, 14), border_radius=2)
                    pygame.draw.circle(surf, SKIN, (84, 52 + bob), 10)
                    pygame.draw.circle(surf, (30, 20, 15), (79, 51 + bob), 2)
                    pygame.draw.line(surf, WARPAINT, (78, 54 + bob), (81, 56 + bob), 2)
                    pygame.draw.ellipse(surf, HAIR, (76, 40 + bob, 22, 16))
                    pygame.draw.polygon(surf, HAIR, [(88, 48 + bob), (96, 56 + bob), (88, 58 + bob)])
                    pygame.draw.polygon(surf, BONE, [(76, 43 + bob), (96, 39 + bob), (95, 42 + bob)])

                self.textures[f'player_{d}_{f}'] = surf

        # 2. IDLE ANIMATIONS (down, up, left)
        for d in ['down', 'up', 'left']:
            for f in range(2):
                surf = pygame.Surface((172, 124), pygame.SRCALPHA)
                breath = -1 if f == 1 else 0
                if d == 'down':
                    pygame.draw.rect(surf, LEATHER, (79, 88, 5, 12), border_radius=2)
                    pygame.draw.rect(surf, LEATHER, (88, 88, 5, 12), border_radius=2)
                    pygame.draw.ellipse(surf, FUR, (77, 98, 8, 5))
                    pygame.draw.ellipse(surf, FUR, (87, 98, 8, 5))
                    pygame.draw.polygon(surf, FUR, [(78, 65 + breath), (94, 65 + breath), (97, 88), (75, 88)])
                    pygame.draw.circle(surf, FUR_SPOT, (82, 72 + breath), 2)
                    pygame.draw.circle(surf, FUR_SPOT, (90, 78 + breath), 2)
                    pygame.draw.line(surf, LEATHER, (78, 65 + breath), (92, 84), 3)
                    pygame.draw.arc(surf, LEATHER, (80, 60 + breath, 12, 8), 3.14, 0, 2)
                    pygame.draw.polygon(surf, BONE, [(84, 66 + breath), (86, 71 + breath), (88, 66 + breath)])
                    pygame.draw.rect(surf, SKIN, (72, 66 + breath, 5, 14), border_radius=2)
                    pygame.draw.rect(surf, SKIN, (95, 66 + breath, 5, 14), border_radius=2)
                    pygame.draw.circle(surf, SKIN, (86, 52 + breath), 11)
                    pygame.draw.line(surf, WARPAINT, (81, 54 + breath), (83, 56 + breath), 2)
                    pygame.draw.line(surf, WARPAINT, (89, 54 + breath), (91, 56 + breath), 2)
                    pygame.draw.circle(surf, (30, 20, 15), (83, 51 + breath), 2)
                    pygame.draw.circle(surf, (30, 20, 15), (89, 51 + breath), 2)
                    pygame.draw.ellipse(surf, HAIR, (74, 40 + breath, 24, 16))
                    pygame.draw.polygon(surf, HAIR, [(74, 46 + breath), (72, 56 + breath), (76, 52 + breath)])
                    pygame.draw.polygon(surf, HAIR, [(98, 46 + breath), (100, 56 + breath), (96, 52 + breath)])
                    pygame.draw.polygon(surf, BONE, [(76, 42 + breath), (96, 38 + breath), (95, 41 + breath), (75, 45 + breath)])
                elif d == 'up':
                    pygame.draw.rect(surf, LEATHER, (79, 88, 5, 12), border_radius=2)
                    pygame.draw.rect(surf, LEATHER, (88, 88, 5, 12), border_radius=2)
                    pygame.draw.ellipse(surf, FUR, (77, 98, 8, 5))
                    pygame.draw.ellipse(surf, FUR, (87, 98, 8, 5))
                    pygame.draw.polygon(surf, FUR, [(78, 65 + breath), (94, 65 + breath), (97, 88), (75, 88)])
                    pygame.draw.circle(surf, FUR_SPOT, (83, 74 + breath), 2)
                    pygame.draw.rect(surf, SKIN, (72, 66 + breath, 5, 14), border_radius=2)
                    pygame.draw.rect(surf, SKIN, (95, 66 + breath, 5, 14), border_radius=2)
                    pygame.draw.circle(surf, HAIR, (86, 52 + breath), 12)
                    pygame.draw.ellipse(surf, HAIR, (73, 40 + breath, 26, 22))
                    pygame.draw.polygon(surf, BONE, [(75, 42 + breath), (97, 38 + breath), (96, 41 + breath), (74, 45 + breath)])
                else: # left
                    pygame.draw.rect(surf, LEATHER, (82, 88, 5, 12), border_radius=2)
                    pygame.draw.rect(surf, LEATHER, (87, 88, 5, 12), border_radius=2)
                    pygame.draw.ellipse(surf, FUR, (80, 98, 8, 5))
                    pygame.draw.polygon(surf, FUR, [(80, 65 + breath), (92, 65 + breath), (94, 88), (78, 88)])
                    pygame.draw.circle(surf, FUR_SPOT, (85, 75 + breath), 2)
                    pygame.draw.rect(surf, SKIN, (84, 68 + breath, 5, 14), border_radius=2)
                    pygame.draw.circle(surf, SKIN, (84, 52 + breath), 10)
                    pygame.draw.circle(surf, (30, 20, 15), (79, 51 + breath), 2)
                    pygame.draw.line(surf, WARPAINT, (78, 54 + breath), (81, 56 + breath), 2)
                    pygame.draw.ellipse(surf, HAIR, (76, 40 + breath, 22, 16))
                    pygame.draw.polygon(surf, HAIR, [(88, 48 + breath), (96, 56 + breath), (88, 58 + breath)])
                    pygame.draw.polygon(surf, BONE, [(76, 43 + breath), (96, 39 + breath), (95, 42 + breath)])

                self.textures[f'player_{d}_idle_{f}'] = surf

        # 3. TOOL ACTIONS (axe, hoe, water)
        for d in ['down', 'up', 'left']:
            for act in ['axe', 'hoe', 'water']:
                for f in range(2):
                    surf = pygame.Surface((172, 124), pygame.SRCALPHA)
                    # Base body
                    pygame.draw.rect(surf, LEATHER, (79, 88, 5, 12), border_radius=2)
                    pygame.draw.rect(surf, LEATHER, (88, 88, 5, 12), border_radius=2)
                    pygame.draw.ellipse(surf, FUR, (77, 98, 8, 5))
                    pygame.draw.ellipse(surf, FUR, (87, 98, 8, 5))
                    pygame.draw.polygon(surf, FUR, [(78, 65), (94, 65), (97, 88), (75, 88)])
                    pygame.draw.circle(surf, FUR_SPOT, (82, 72), 2)
                    if d != 'up':
                        pygame.draw.circle(surf, SKIN, (86 if d == 'down' else 84, 52), 11 if d == 'down' else 10)
                        pygame.draw.ellipse(surf, HAIR, (74 if d == 'down' else 76, 40, 24, 16))
                        pygame.draw.polygon(surf, BONE, [(76, 42), (96, 38), (95, 41)])
                    else:
                        pygame.draw.circle(surf, HAIR, (86, 52), 12)
                        pygame.draw.ellipse(surf, HAIR, (73, 40, 26, 22))
                        pygame.draw.polygon(surf, BONE, [(75, 42), (97, 38), (96, 41)])

                    # Tool specific overlay
                    if act == 'axe':
                        if d == 'down':
                            if f == 0:
                                pygame.draw.line(surf, WOOD, (86, 68), (104, 38), 4)
                                pygame.draw.polygon(surf, FLINT, [(101, 35), (114, 32), (106, 45)])
                            else:
                                pygame.draw.line(surf, WOOD, (86, 75), (86, 102), 4)
                                pygame.draw.polygon(surf, FLINT, [(82, 98), (94, 98), (88, 108)])
                                pygame.draw.arc(surf, (240, 240, 240, 160), (74, 94, 24, 16), 0, math.pi, 2)
                        elif d == 'up':
                            if f == 0:
                                pygame.draw.line(surf, WOOD, (86, 68), (70, 40), 4)
                                pygame.draw.polygon(surf, FLINT, [(67, 37), (56, 34), (64, 47)])
                            else:
                                pygame.draw.line(surf, WOOD, (86, 68), (86, 34), 4)
                                pygame.draw.polygon(surf, FLINT, [(82, 34), (94, 34), (88, 24)])
                        else: # left
                            if f == 0:
                                pygame.draw.line(surf, WOOD, (84, 68), (102, 42), 4)
                                pygame.draw.polygon(surf, FLINT, [(99, 39), (112, 36), (104, 49)])
                            else:
                                pygame.draw.line(surf, WOOD, (84, 72), (60, 94), 4)
                                pygame.draw.polygon(surf, FLINT, [(57, 90), (52, 102), (66, 98)])

                    elif act == 'hoe':
                        if d == 'down':
                            if f == 0:
                                pygame.draw.line(surf, WOOD, (86, 70), (102, 45), 4)
                                pygame.draw.polygon(surf, BONE, [(98, 42), (110, 48), (104, 40)])
                            else:
                                pygame.draw.line(surf, WOOD, (86, 74), (86, 104), 4)
                                pygame.draw.polygon(surf, BONE, [(82, 102), (90, 102), (86, 110)])
                        elif d == 'up':
                            if f == 0:
                                pygame.draw.line(surf, WOOD, (86, 70), (72, 46), 4)
                                pygame.draw.polygon(surf, BONE, [(68, 42), (80, 48), (74, 40)])
                            else:
                                pygame.draw.line(surf, WOOD, (86, 68), (86, 38), 4)
                                pygame.draw.polygon(surf, BONE, [(82, 38), (90, 38), (86, 30)])
                        else: # left
                            if f == 0:
                                pygame.draw.line(surf, WOOD, (84, 70), (98, 48), 4)
                                pygame.draw.polygon(surf, BONE, [(94, 44), (106, 50), (100, 42)])
                            else:
                                pygame.draw.line(surf, WOOD, (84, 72), (64, 98), 4)
                                pygame.draw.polygon(surf, BONE, [(60, 96), (56, 106), (68, 100)])

                    elif act == 'water':
                        if d == 'down':
                            if f == 0:
                                pygame.draw.ellipse(surf, CLAY, (82, 72, 12, 14))
                            else:
                                pygame.draw.ellipse(surf, CLAY, (82, 75, 14, 11))
                                for wy in [88, 93, 98]:
                                    pygame.draw.circle(surf, WATER_COL, (88, wy), 2)
                        elif d == 'up':
                            if f == 0:
                                pygame.draw.ellipse(surf, CLAY, (82, 66, 12, 14))
                            else:
                                pygame.draw.ellipse(surf, CLAY, (82, 63, 14, 11))
                                for wy in [58, 53, 48]:
                                    pygame.draw.circle(surf, WATER_COL, (88, wy), 2)
                        else: # left
                            if f == 0:
                                pygame.draw.ellipse(surf, CLAY, (76, 72, 12, 14))
                            else:
                                pygame.draw.ellipse(surf, CLAY, (72, 75, 14, 11))
                                for wy in [87, 92, 97]:
                                    pygame.draw.circle(surf, WATER_COL, (74, wy), 2)

                    self.textures[f'player_{d}_{act}_{f}'] = surf

        # Flip right from left
        for f in range(4):
            self.textures[f'player_right_{f}'] = pygame.transform.flip(self.textures[f'player_left_{f}'], True, False)
        for f in range(2):
            self.textures[f'player_right_idle_{f}'] = pygame.transform.flip(self.textures[f'player_left_idle_{f}'], True, False)
        for act in ['axe', 'hoe', 'water']:
            for f in range(2):
                self.textures[f'player_right_{act}_{f}'] = pygame.transform.flip(self.textures[f'player_left_{act}_{f}'], True, False)

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

        # -------------------------------------------------------------
        # 2. STONE AGE MATERIAL ICONS (32x32)
        # -------------------------------------------------------------
        # Branch
        mbr = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(mbr, (125, 75, 40), (5, sz - 5), (sz - 6, 6), 4)
        pygame.draw.line(mbr, (100, 55, 28), (12, 10), (sz - 8, sz - 10), 3)
        self.textures["mat_branch"] = mbr

        # Pebble
        mpeb = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.ellipse(mpeb, (155, 160, 165), (6, 12, 14, 11))
        pygame.draw.ellipse(mpeb, (85, 90, 95), (6, 12, 14, 11), 1)
        pygame.draw.ellipse(mpeb, (120, 125, 130), (15, 8, 12, 9))
        self.textures["mat_pebble"] = mpeb

        # Flint
        mflint = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.polygon(mflint, (55, 60, 70), [(8, 24), (16, 5), (25, 16), (20, 26)])
        pygame.draw.polygon(mflint, (125, 135, 150), [(8, 24), (16, 5), (25, 16), (20, 26)], 1)
        pygame.draw.line(mflint, (170, 185, 205), (16, 8), (22, 16), 2)
        self.textures["mat_flint"] = mflint

        # Cord (Dây bện)
        mcord = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.circle(mcord, (190, 150, 80), (16, 16), 10, 3)
        pygame.draw.circle(mcord, (140, 105, 50), (16, 16), 6, 2)
        self.textures["mat_cord"] = mcord

        # Clay lump
        mclay = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.circle(mclay, (185, 105, 55), (16, 16), 10)
        pygame.draw.circle(mclay, (130, 70, 35), (16, 16), 10, 2)
        pygame.draw.circle(mclay, (220, 140, 85), (13, 13), 3)
        self.textures["mat_clay"] = mclay

        # Clay brick
        mbrick = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.rect(mbrick, (195, 95, 50), (5, 9, 22, 14), border_radius=2)
        pygame.draw.rect(mbrick, (130, 55, 25), (5, 9, 22, 14), 2, border_radius=2)
        self.textures["mat_clay_brick"] = mbrick

        # Copper bar (Thỏi đồng)
        mcbar = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.polygon(mcbar, (225, 130, 50), [(5, 22), (23, 22), (27, 10), (9, 10)])
        pygame.draw.polygon(mcbar, (160, 80, 25), [(5, 22), (23, 22), (27, 10), (9, 10)], 2)
        pygame.draw.line(mcbar, (255, 190, 110), (11, 13), (23, 13), 2)
        self.textures["mat_copper_bar"] = mcbar

        # -------------------------------------------------------------
        # 3. STONE AGE FOOD ICONS (32x32)
        # -------------------------------------------------------------
        # Wild Berries
        fber = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.circle(fber, (225, 45, 55), (12, 18), 7)
        pygame.draw.circle(fber, (215, 35, 45), (19, 14), 7)
        pygame.draw.circle(fber, (185, 25, 35), (15, 10), 6)
        pygame.draw.circle(fber, (255, 160, 170), (10, 16), 2)
        self.textures["food_berries"] = fber
        self.textures["food_wild_berries"] = fber

        # Roasted Fish
        rfish = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(rfish, (100, 60, 30), (3, sz - 3), (sz - 4, 4), 3)  # Spit stick
        pygame.draw.ellipse(rfish, (215, 125, 50), (8, 9, 18, 12))  # Golden skin
        pygame.draw.polygon(rfish, (170, 90, 30), [(22, 15), (28, 9), (28, 21)])  # Tail
        pygame.draw.line(rfish, (70, 35, 15), (12, 12), (16, 17), 2)  # Grill marks
        pygame.draw.line(rfish, (70, 35, 15), (16, 12), (20, 17), 2)
        self.textures["food_roasted_fish"] = rfish

        # Roasted Roots
        rroot = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.ellipse(rroot, (185, 135, 80), (6, 10, 20, 13))
        pygame.draw.ellipse(rroot, (100, 65, 30), (6, 10, 20, 13), 2)
        pygame.draw.line(rroot, (50, 30, 15), (10, 14), (16, 18), 2)  # Char mark
        self.textures["food_roasted_roots"] = rroot

        # Smoked Meat
        smeat = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.circle(smeat, (240, 235, 225), (8, 20), 4)  # Bone
        pygame.draw.ellipse(smeat, (175, 55, 45), (10, 8, 17, 15))  # Savory meat
        pygame.draw.ellipse(smeat, (110, 30, 25), (10, 8, 17, 15), 2)
        self.textures["food_smoked_meat"] = smeat

        # Roasted Corn
        rcorn = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.ellipse(rcorn, (230, 185, 45), (8, 8, 16, 16))
        pygame.draw.line(rcorn, (70, 45, 15), (10, 12), (18, 20), 2)  # Char
        self.textures["food_roasted_corn"] = rcorn

        # -------------------------------------------------------------
        # 4. STONE AGE TOOLS (32x32)
        # -------------------------------------------------------------
        # Primitive Axe
        paxe = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(paxe, (120, 75, 40), (5, sz - 5), (sz - 8, 8), 4)  # Wood shaft
        pygame.draw.polygon(paxe, (90, 95, 105), [(18, 6), (28, 4), (25, 16), (15, 12)])  # Flint head
        pygame.draw.circle(paxe, (190, 150, 80), (20, 10), 3)  # Cord lash
        self.textures["tool_primitive_axe"] = paxe

        # Digging Stick
        dstk = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(dstk, (135, 85, 45), (4, sz - 4), (sz - 7, 7), 4)
        pygame.draw.polygon(dstk, (60, 35, 20), [(sz - 8, 8), (sz - 4, 4), (sz - 10, 5)])  # Fire-hardened point
        self.textures["tool_digging_stick"] = dstk

        # Primitive Spear
        pspear = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(pspear, (120, 75, 40), (4, sz - 4), (sz - 6, 6), 3)
        pygame.draw.polygon(pspear, (160, 165, 175), [(sz - 11, 11), (sz - 2, 2), (sz - 7, 15)])  # Flint tip
        self.textures["tool_primitive_spear"] = pspear

        # Stone Pick
        spick = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(spick, (120, 75, 40), (5, sz - 5), (sz - 8, 8), 4)
        pygame.draw.arc(spick, (130, 135, 140), (sz - 22, 2, 20, 20), 0, math.pi * 0.75, 6)
        self.textures["tool_stone_pick"] = spick

        # Flint Striker
        fstr = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.circle(fstr, (60, 65, 75), (12, 18), 7)
        pygame.draw.circle(fstr, (80, 85, 95), (20, 14), 7)
        pygame.draw.circle(fstr, (255, 210, 40), (16, 14), 3)  # Spark!
        self.textures["tool_flint_striker"] = fstr

        # Polished Axe
        plaxe = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(plaxe, (130, 85, 50), (5, sz - 5), (sz - 8, 8), 4)
        pygame.draw.polygon(plaxe, (160, 165, 175), [(17, 5), (29, 3), (26, 17), (14, 13)])
        pygame.draw.polygon(plaxe, (210, 215, 225), [(17, 5), (29, 3), (26, 17), (14, 13)], 1)  # Polished shine
        self.textures["tool_polished_axe"] = plaxe

        # Stone Hoe
        shoe = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(shoe, (125, 80, 45), (5, sz - 5), (sz - 9, 9), 4)
        pygame.draw.rect(shoe, (140, 145, 155), (sz - 18, 4, 14, 8), border_radius=2)
        self.textures["tool_stone_hoe"] = shoe

        # Clay Jug
        cjug = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.rect(cjug, (160, 85, 40), (14, 6, 4, 4))
        pygame.draw.circle(cjug, (185, 105, 55), (16, 18), 9)
        pygame.draw.circle(cjug, (120, 60, 30), (16, 18), 9, 2)
        pygame.draw.arc(cjug, (190, 140, 70), (8, 10, 16, 14), 0, math.pi, 2)  # Cord strap
        self.textures["tool_clay_jug"] = cjug

        # Bone Rod
        brod = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(brod, (135, 90, 50), (4, sz - 4), (sz - 5, 4), 3)
        pygame.draw.line(brod, (240, 240, 250), (sz - 5, 4), (sz - 5, sz - 8), 1)
        pygame.draw.arc(brod, (250, 245, 235), (sz - 9, sz - 12, 8, 8), math.pi * 0.5, math.pi * 1.8, 2)  # Bone hook
        self.textures["tool_bone_rod"] = brod

        # Bone Scythe
        bscy = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(bscy, (130, 85, 45), (5, sz - 5), (sz - 7, 7), 4)
        pygame.draw.arc(bscy, (245, 240, 230), (sz - 24, 2, 22, 18), 0, math.pi * 0.95, 5)
        self.textures["tool_bone_scythe"] = bscy

        # Bronze Tools
        b_axe = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(b_axe, (135, 85, 50), (5, sz - 5), (sz - 8, 8), 4)
        pygame.draw.polygon(b_axe, (225, 130, 50), [(17, 5), (29, 3), (26, 17), (14, 13)])
        pygame.draw.polygon(b_axe, (255, 180, 90), [(17, 5), (29, 3), (26, 17), (14, 13)], 1)
        self.textures["tool_bronze_axe"] = b_axe

        b_hoe = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(b_hoe, (135, 85, 50), (5, sz - 5), (sz - 9, 9), 4)
        pygame.draw.rect(b_hoe, (225, 130, 50), (sz - 18, 4, 14, 8), border_radius=2)
        pygame.draw.rect(b_hoe, (255, 180, 90), (sz - 18, 4, 14, 8), 1, border_radius=2)
        self.textures["tool_bronze_hoe"] = b_hoe

        b_pick = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(b_pick, (135, 85, 50), (5, sz - 5), (sz - 8, 8), 4)
        pygame.draw.arc(b_pick, (225, 130, 50), (sz - 22, 2, 20, 20), 0, math.pi * 0.75, 5)
        self.textures["tool_bronze_pick"] = b_pick

        b_harp = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.line(b_harp, (135, 85, 50), (4, sz - 4), (sz - 6, 6), 3)
        pygame.draw.polygon(b_harp, (225, 130, 50), [(sz - 12, 12), (sz - 2, 2), (sz - 6, 16)])
        self.textures["tool_tribal_harpoon"] = b_harp

        # -------------------------------------------------------------
        # 5. PREHISTORIC CROPS & SEEDS
        # -------------------------------------------------------------
        for crop_id in ["wild_roots", "wild_wheat", "forest_berry", "wild_corn", "giant_squash"]:
            if f"seed_{crop_id}" not in self.textures:
                sbag = pygame.Surface((sz, sz), pygame.SRCALPHA)
                pygame.draw.polygon(sbag, (195, 160, 110), [(6, 26), (25, 26), (28, 9), (4, 9)])
                pygame.draw.polygon(sbag, (120, 95, 55), [(6, 26), (25, 26), (28, 9), (4, 9)], 2)
                pygame.draw.circle(sbag, (120, 190, 80), (16, 17), 4)
                self.textures[f"seed_{crop_id}"] = sbag

            stages = CROPS_DATA.get(crop_id, {}).get("stages", 4)
            crop_col = CROPS_DATA.get(crop_id, {}).get("color", (200, 180, 120))
            for st in range(stages):
                k = f"crop_{crop_id}_{st}"
                if k not in self.textures:
                    csurf = pygame.Surface((ts, ts), pygame.SRCALPHA)
                    if st == 0:
                        pygame.draw.line(csurf, (90, 170, 60), (ts // 2, ts - 8), (ts // 2, ts - 18), 3)
                        pygame.draw.circle(csurf, (115, 205, 80), (ts // 2 - 4, ts - 19), 3)
                    elif st == 1:
                        pygame.draw.line(csurf, (75, 155, 50), (ts // 2, ts - 8), (ts // 2, ts - 25), 4)
                        pygame.draw.ellipse(csurf, (95, 185, 65), (ts // 2 - 12, ts - 26, 12, 10))
                        pygame.draw.ellipse(csurf, (95, 185, 65), (ts // 2, ts - 26, 12, 10))
                    elif st == 2:
                        pygame.draw.line(csurf, (65, 145, 45), (ts // 2, ts - 8), (ts // 2, ts - 30), 4)
                        pygame.draw.ellipse(csurf, (85, 175, 60), (ts // 2 - 15, ts - 32, 15, 12))
                        pygame.draw.ellipse(csurf, (85, 175, 60), (ts // 2, ts - 32, 15, 12))
                    else:
                        # Mature Harvest Stage
                        pygame.draw.line(csurf, (60, 135, 40), (ts // 2, ts - 8), (ts // 2, ts - 34), 4)
                        pygame.draw.ellipse(csurf, (80, 165, 55), (ts // 2 - 16, ts - 35, 16, 14))
                        pygame.draw.ellipse(csurf, (80, 165, 55), (ts // 2, ts - 35, 16, 14))
                        pygame.draw.circle(csurf, crop_col, (ts // 2, ts - 24), 12)
                        pygame.draw.circle(csurf, (60, 45, 30), (ts // 2, ts - 24), 12, 2)
                    self.textures[k] = csurf

        # -------------------------------------------------------------
        # 6. PREHISTORIC FISH ICONS (32x32)
        # -------------------------------------------------------------
        for fish_id in ["river_crayfish", "paleo_carp", "mud_catfish", "river_sturgeon", "golden_paleo_fish"]:
            k = f"fish_{fish_id}"
            if k not in self.textures:
                fsurf = pygame.Surface((sz, sz), pygame.SRCALPHA)
                fcol = FISH_DATA.get(fish_id, {}).get("color", (180, 150, 100))
                pygame.draw.ellipse(fsurf, fcol, (4, 10, 18, 12))
                pygame.draw.polygon(fsurf, (max(0, fcol[0] - 40), max(0, fcol[1] - 40), max(0, fcol[2] - 40)), [(19, 16), (28, 9), (28, 23)])
                fsurf.set_at((8, 14), (255, 255, 255))
                self.textures[k] = fsurf

        # -------------------------------------------------------------
        # 7. STONE TRIBE NPC SPRITES (64x64)
        # -------------------------------------------------------------
        # Thầy Mo Kraa (Shaman with feather warbonnet, runic robes & spirit staff)
        shaman = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(shaman, (0, 0, 0, 45), (14, 52, 36, 10))
        # Shaman robes (emerald & dark ochre)
        pygame.draw.rect(shaman, (45, 95, 75), (20, 26, 24, 28), border_radius=4)
        pygame.draw.rect(shaman, (160, 110, 50), (22, 28, 20, 24), border_radius=2)
        # Sacred bone runes on robe
        pygame.draw.line(shaman, (240, 235, 220), (26, 34), (28, 42), 2)
        pygame.draw.line(shaman, (240, 235, 220), (38, 34), (36, 42), 2)
        pygame.draw.circle(shaman, (240, 235, 220), (32, 38), 3)
        # Head & warpaint
        pygame.draw.circle(shaman, (225, 180, 140), (32, 18), 11)
        pygame.draw.line(shaman, (210, 40, 40), (27, 19), (30, 22), 2)
        pygame.draw.line(shaman, (210, 40, 40), (37, 19), (34, 22), 2)
        # Shaman staff held in right hand
        pygame.draw.line(shaman, (110, 70, 35), (46, 12), (46, 56), 3)
        pygame.draw.polygon(shaman, (245, 240, 225), [(43, 10), (49, 10), (46, 3)])
        pygame.draw.circle(shaman, (80, 220, 240), (46, 11), 3)
        # Feather warbonnet
        pygame.draw.polygon(shaman, (220, 50, 60), [(28, 10), (32, 1), (36, 10)])
        pygame.draw.polygon(shaman, (40, 180, 220), [(22, 12), (25, 3), (28, 12)])
        pygame.draw.polygon(shaman, (255, 215, 50), [(36, 12), (39, 3), (42, 12)])
        self.textures["npc_thay_mo_kraa"] = shaman
        self.textures["npc_co_mai"] = shaman

        # Thợ Săn Boomer (Hunter with fur cowl, bone bandolier & hunting spear)
        hunter = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(hunter, (0, 0, 0, 45), (12, 52, 40, 10))
        # Fur coat
        pygame.draw.rect(hunter, (115, 70, 40), (18, 26, 28, 28), border_radius=4)
        # Bone tooth bandolier
        pygame.draw.line(hunter, (70, 45, 25), (19, 28), (45, 50), 3)
        for bx, by in [(24, 33), (32, 39), (40, 46)]:
            pygame.draw.polygon(hunter, (245, 240, 230), [(bx - 2, by), (bx + 2, by), (bx, by + 5)])
        # Rugged face
        pygame.draw.circle(hunter, (220, 175, 135), (32, 18), 12)
        # Fur hood
        pygame.draw.ellipse(hunter, (150, 100, 60), (19, 6, 26, 17))
        # Flint hunting spear across back
        pygame.draw.line(hunter, (130, 85, 45), (10, 10), (22, 52), 3)
        pygame.draw.polygon(hunter, (85, 90, 100), [(8, 8), (14, 6), (11, 14)])
        self.textures["npc_tho_san_boomer"] = hunter
        self.textures["npc_bac_bay"] = hunter

        # Tộc Trưởng Ogg (Chieftain with horn crown, leopard mantle & sun amulet)
        chieftain = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.ellipse(chieftain, (0, 0, 0, 45), (12, 52, 40, 10))
        # Crimson & leopard mantle
        pygame.draw.rect(chieftain, (150, 50, 35), (18, 24, 28, 30), border_radius=4)
        pygame.draw.rect(chieftain, (185, 130, 60), (22, 28, 20, 24), border_radius=2)
        # Leopard spots
        pygame.draw.circle(chieftain, (90, 50, 20), (26, 34), 2)
        pygame.draw.circle(chieftain, (90, 50, 20), (37, 36), 2)
        pygame.draw.circle(chieftain, (90, 50, 20), (30, 44), 2)
        # Head & wise grey beard
        pygame.draw.circle(chieftain, (230, 185, 145), (32, 18), 12)
        pygame.draw.polygon(chieftain, (215, 215, 220), [(26, 22), (38, 22), (32, 32)])
        # Mammoth horn crown
        pygame.draw.polygon(chieftain, (245, 240, 225), [(18, 14), (13, 0), (23, 9)])
        pygame.draw.polygon(chieftain, (245, 240, 225), [(46, 14), (51, 0), (41, 9)])
        # Golden sun amulet
        pygame.draw.circle(chieftain, (255, 215, 50), (32, 28), 4)
        self.textures["npc_toc_truong_ogg"] = chieftain
        self.textures["npc_cu_ba_tri"] = chieftain

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

        # 2. Structures (6 Master Pieces)
        bld_scales = {
            "rock_shelter": ("01_ancestral_rock_shelter", (256, 213)),
            "tipis": ("02_hide_tipis_and_thatch_hut", (160, 133)),
            "workshop": ("03_flintknapping_workshop", (160, 133)),
            "smoker": ("04_meat_smoking_and_tanning_racks", (160, 133)),
            "shrine": ("05_megalithic_totem_shrine", (160, 133)),
            "palisade": ("06_palisade_gate_and_watchtower", (180, 150)),
        }
        for alias, (src_key, sz) in bld_scales.items():
            if src_key in self.textures:
                self.textures[alias] = pygame.transform.smoothscale(self.textures[src_key], sz)

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

        # 9. Authentic Stone Age NPC & Player Character Sprites
        def _crop_scale(tex_key, sz=(44, 60)):
            raw = self.textures.get(tex_key)
            if not raw:
                return None
            bbox = raw.get_bounding_rect()
            if bbox.width > 0 and bbox.height > 0:
                raw = raw.subsurface(bbox)
            return pygame.transform.smoothscale(raw, sz)

        # A. Town NPCs (Stone Tribe Leaders & Merchant)
        ogg_tex = _crop_scale("unit_mammoth_bone_warrior_01", (46, 62))
        if ogg_tex:
            self.textures["npc_toc_truong_ogg"] = ogg_tex
            self.textures["npc_cu_ba_tri"] = ogg_tex

        kraa_tex = _crop_scale("unit_tribal_shaman_01", (44, 60)) or _crop_scale("unit_tribal_shaman_05", (44, 60))
        if kraa_tex:
            self.textures["npc_thay_mo_kraa"] = kraa_tex
            self.textures["npc_co_mai"] = kraa_tex

        boomer_tex = _crop_scale("unit_flint_spear_hunter_01", (44, 60))
        if boomer_tex:
            self.textures["npc_tho_san_boomer"] = boomer_tex
            self.textures["npc_bac_bay"] = boomer_tex

        merch_tex = _crop_scale("unit_gatherer_builder_02", (44, 60)) or _crop_scale("scout_torch_explorer_01", (44, 60))
        if merch_tex:
            self.textures["wandering_merchant"] = merch_tex

        # B. Player Character Animated Sprites (4 Directions + Tool Actions)
        p_down_idle = _crop_scale("unit_flint_spear_hunter_01", (44, 60))
        p_down_walk = _crop_scale("unit_flint_spear_hunter_02", (44, 60))
        p_down_alt = _crop_scale("unit_flint_spear_hunter_04", (44, 60))
        p_up = _crop_scale("unit_flint_spear_hunter_10", (44, 60))
        p_side_idle = _crop_scale("unit_flint_spear_hunter_09", (44, 60))
        p_side_walk = _crop_scale("unit_flint_spear_hunter_08", (44, 60))
        p_axe = _crop_scale("unit_gatherer_builder_04", (44, 60))
        p_hoe = _crop_scale("unit_flint_spear_hunter_03", (44, 60))
        p_water = _crop_scale("unit_gatherer_builder_06", (44, 60))

        if p_down_idle:
            self.textures["player_down_idle_0"] = p_down_idle
            self.textures["player_down_idle_1"] = p_down_alt or p_down_idle
            self.textures["player_down_0"] = p_down_idle
            self.textures["player_down_1"] = p_down_walk or p_down_idle
            self.textures["player_down_2"] = p_down_idle
            self.textures["player_down_3"] = p_down_alt or p_down_idle

        if p_up:
            self.textures["player_up_idle_0"] = p_up
            self.textures["player_up_idle_1"] = p_up
            for f in range(4):
                self.textures[f"player_up_{f}"] = p_up

        if p_side_idle:
            self.textures["player_right_idle_0"] = p_side_idle
            self.textures["player_right_idle_1"] = p_side_walk or p_side_idle
            self.textures["player_right_0"] = p_side_idle
            self.textures["player_right_1"] = p_side_walk or p_side_idle
            self.textures["player_right_2"] = p_side_idle
            self.textures["player_right_3"] = p_side_walk or p_side_idle

            p_left_idle = pygame.transform.flip(p_side_idle, True, False)
            p_left_walk = pygame.transform.flip(p_side_walk or p_side_idle, True, False)
            self.textures["player_left_idle_0"] = p_left_idle
            self.textures["player_left_idle_1"] = p_left_walk
            self.textures["player_left_0"] = p_left_idle
            self.textures["player_left_1"] = p_left_walk
            self.textures["player_left_2"] = p_left_idle
            self.textures["player_left_3"] = p_left_walk

        # Actions (Axe chop, Hoe dig, Water/Harvest)
        for d in ["down", "up", "right", "left"]:
            d_idle = self.textures.get(f"player_{d}_idle_0", p_down_idle)
            d_flip = (d == "left")

            if p_axe:
                axe_spr = pygame.transform.flip(p_axe, True, False) if d_flip else p_axe
                self.textures[f"player_{d}_axe_0"] = axe_spr
                self.textures[f"player_{d}_axe_1"] = d_idle

            if p_hoe:
                hoe_spr = pygame.transform.flip(p_hoe, True, False) if d_flip else p_hoe
                self.textures[f"player_{d}_hoe_0"] = hoe_spr
                self.textures[f"player_{d}_hoe_1"] = d_idle

            if p_water:
                wat_spr = pygame.transform.flip(p_water, True, False) if d_flip else p_water
                self.textures[f"player_{d}_water_0"] = wat_spr
                self.textures[f"player_{d}_water_1"] = d_idle


    def load_audio(self):
        try:
            audio_map = {
                "dig": "assets/audio/hoe.wav",
                "chop": "assets/audio/axe.mp3",
                "water": "assets/audio/water.mp3",
                "clink": "assets/audio/axe.mp3",
                "swish": "assets/audio/plant.mp3",
                "success": "assets/audio/success.wav",
                "coin": "assets/audio/success.wav"
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
