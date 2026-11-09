"""
Natural World & Ecosystem Generator for Stone Age Nature Observation Simulator.
Implements a 100% primeval, human-free wilderness using:
- Multi-octave Perlin-style Fractal Brownian Motion (FBM) with domain warping
- Continuous 5-tier elevation topography from Northern Glacial Crags to Southern Mangrove Delta
- Geomorphologically accurate meandering river with point bar deposition and cutbank erosion
- 5 organic soil horizons: Dry Talus Scree, Forest Humus, Steppe Meadow, Riparian Mud, and River Pebble Sand
- Authentic ecological clustering for prehistoric flora, boulders, and mineral deposits
"""

import math
import random
import pygame
from src.settings import TILE_SIZE, MAP_COLS, MAP_ROWS, WORLD_WIDTH, WORLD_HEIGHT
from src.entities.obstacles import Obstacle


class FastNoise2D:
    """Self-contained 2D gradient noise generator for multi-octave terrain synthesis."""
    def __init__(self, seed: int = 1905):
        self.seed = seed
        rng = random.Random(seed)
        self.perm = list(range(256))
        rng.shuffle(self.perm)
        self.perm += self.perm
        self.gradients = [
            (math.cos(2.0 * math.pi * i / 12.0), math.sin(2.0 * math.pi * i / 12.0))
            for i in range(12)
        ]

    @staticmethod
    def _fade(t: float) -> float:
        return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + t * (b - a)

    def _grad(self, hash_val: int, x: float, y: float) -> float:
        gx, gy = self.gradients[hash_val % 12]
        return gx * x + gy * y

    def noise2d(self, x: float, y: float) -> float:
        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)

        u = self._fade(xf)
        v = self._fade(yf)

        aa = self.perm[self.perm[xi] + yi]
        ab = self.perm[self.perm[xi] + yi + 1]
        ba = self.perm[self.perm[xi + 1] + yi]
        bb = self.perm[self.perm[xi + 1] + yi + 1]

        x1 = self._lerp(self._grad(aa, xf, yf), self._grad(ba, xf - 1.0, yf), u)
        x2 = self._lerp(self._grad(ab, xf, yf - 1.0), self._grad(bb, xf - 1.0, yf - 1.0), u)
        return self._lerp(x1, x2, v)

    def fbm(self, x: float, y: float, octaves: int = 4, persistence: float = 0.5,
            lacunarity: float = 2.0, base_scale: float = 0.035) -> float:
        """Evaluates Fractal Brownian Motion noise normalized into [0.0, 1.0]."""
        total = 0.0
        amplitude = 1.0
        frequency = base_scale
        max_value = 0.0

        for _ in range(octaves):
            total += self.noise2d(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity

        return max(0.0, min(1.0, 0.5 + (total / max_value) * 0.75))


class NaturalWorld:
    """
    Simulates a living prehistoric wilderness without human intervention.
    """
    def __init__(self, cols=MAP_COLS, rows=MAP_ROWS, seed=777):
        self.cols = cols
        self.rows = rows
        self.seed = seed
        self.noise = FastNoise2D(seed)
        self.warp_noise = FastNoise2D(seed + 101)
        self.moisture_noise = FastNoise2D(seed + 202)

        # Grids
        self.elevation = [[0.5 for _ in range(cols)] for _ in range(rows)]
        self.elevation_tier = [[2 for _ in range(cols)] for _ in range(rows)]
        self.moisture = [[0.5 for _ in range(cols)] for _ in range(rows)]
        self.terrain = [["steppe_meadow" for _ in range(cols)] for _ in range(rows)]
        self.obstacles = {}
        self.water_tiles = set()
        self.solid_tiles = set()

        # Cliff drops for 2.5D rendering
        self.cliff_south = [[0 for _ in range(cols)] for _ in range(rows)]
        self.cliff_east = [[0 for _ in range(cols)] for _ in range(rows)]
        self.cliff_west = [[0 for _ in range(cols)] for _ in range(rows)]

        # Water caustics & animation
        self.water_anim_timer = 0.0
        self.water_frame = 0

        self.generate()

    @staticmethod
    def get_river_center_float(r: float) -> float:
        """Smooth meandering river spline through the 80x80 continent."""
        return 49.0 + 8.5 * math.sin(r * 0.08) + 4.2 * math.cos(r * 0.16)

    @staticmethod
    def get_river_half_width_float(r: float) -> float:
        """Dynamic river width: narrow upper gorge, broad stepping stone ford at r=36, wide delta."""
        ford_broaden = 1.35 * math.exp(-((r - 36.0) ** 2) / 7.0)
        if r >= 62:
            return 2.8 + 0.8 * math.sin(r * 0.12)
        elif r <= 22:
            return 1.6 + 0.3 * math.sin(r * 0.2)
        return 2.3 + 0.6 * math.sin(r * 0.18 + 0.5) + ford_broaden

    def generate(self):
        """Generates continuous heightfields, soil horizons, and ecological vegetation clusters."""
        # 1. Heightfield with Domain Warping
        for r in range(self.rows):
            # Macro North-to-South elevation gradient: North is alpine glacier, South is ocean/delta
            lat_elev = 0.78 * (1.0 - (r / float(self.rows))) ** 0.85

            for c in range(self.cols):
                # Domain warp offset
                wx = self.warp_noise.noise2d(c * 0.06, r * 0.06) * 5.0
                wy = self.warp_noise.noise2d((c + 50) * 0.06, (r + 50) * 0.06) * 5.0

                # Multi-octave FBM
                raw_noise = self.noise.fbm(c + wx, r + wy, octaves=4, persistence=0.5, lacunarity=2.0, base_scale=0.038)
                elev = lat_elev * 0.65 + raw_noise * 0.45

                # Carve deep meandering river valley
                rc = self.get_river_center_float(r)
                hw = self.get_river_half_width_float(r)
                dist_to_river = abs((c + 0.5) - rc)

                if dist_to_river <= hw:
                    # In river channel
                    elev = min(elev, 0.08)
                elif dist_to_river <= hw + 4.0:
                    # River valley gorge depression
                    valley_blend = (dist_to_river - hw) / 4.0
                    elev = 0.08 + (elev - 0.08) * valley_blend

                self.elevation[r][c] = max(0.0, min(1.0, elev))

                # Moisture Map
                m_noise = self.moisture_noise.fbm(c, r, octaves=3, base_scale=0.04)
                # Proximity to river significantly elevates moisture
                river_moisture = max(0.0, 1.0 - (dist_to_river / 12.0)) * 0.45
                self.moisture[r][c] = max(0.0, min(1.0, m_noise * 0.65 + river_moisture))

        # 2. Elevation Tiers & 2.5D Cliff Drops
        for r in range(self.rows):
            for c in range(self.cols):
                e = self.elevation[r][c]
                if e >= 0.72:
                    tier = 4  # Glacial Crags & High Alpine Peaks
                elif e >= 0.56:
                    tier = 3  # Highland Terraces & Rocky Bluffs
                elif e >= 0.32:
                    tier = 2  # Central Steppe Plains & Savanna Basin
                elif e >= 0.12:
                    tier = 1  # Floodplains & Riparian Shrubland
                else:
                    tier = 0  # River Channel & Deep Water
                self.elevation_tier[r][c] = tier

        # Compute cliff drops where adjacent tiers drop steeply
        for r in range(self.rows):
            for c in range(self.cols):
                cur_t = self.elevation_tier[r][c]
                # South drop
                if r < self.rows - 1:
                    s_t = self.elevation_tier[r + 1][c]
                    if cur_t > s_t and s_t >= 1:
                        self.cliff_south[r][c] = cur_t - s_t
                # East drop
                if c < self.cols - 1:
                    e_t = self.elevation_tier[r][c + 1]
                    if cur_t > e_t and e_t >= 1:
                        self.cliff_east[r][c] = cur_t - e_t
                # West drop
                if c > 0:
                    w_t = self.elevation_tier[r][c - 1]
                    if cur_t > w_t and w_t >= 1:
                        self.cliff_west[r][c] = cur_t - w_t

        # 3. Ground Material Horizons
        self.water_tiles.clear()
        self.solid_tiles.clear()

        for r in range(self.rows):
            rc = self.get_river_center_float(r)
            hw = self.get_river_half_width_float(r)
            left_b = rc - hw
            right_b = rc + hw

            for c in range(self.cols):
                cm = c + 0.5
                e = self.elevation[r][c]
                m = self.moisture[r][c]
                tier = self.elevation_tier[r][c]

                # River Channel
                if left_b - 0.15 <= cm <= right_b + 0.15 or tier == 0:
                    self.terrain[r][c] = "water"
                    self.water_tiles.add((c, r))
                    self.solid_tiles.add((c, r))

                # Talus Scree (High Alpine Crags & Dry Ridges)
                elif tier >= 4 or (tier == 3 and m < 0.38):
                    self.terrain[r][c] = "scree_talus"

                # Primeval Forest Humus (High moisture midlands & East Forest)
                elif m >= 0.62 and (c >= 54 or (c <= 22 and r >= 35)):
                    self.terrain[r][c] = "forest_humus"

                # Riparian Mud (Riverbanks and Southern Delta Swamp)
                elif r >= 64 or (abs(cm - rc) <= hw + 4.2 and tier <= 1):
                    self.terrain[r][c] = "riparian_mud"

                # Steppe Meadow (Central rolling savanna grasslands)
                else:
                    self.terrain[r][c] = "steppe_meadow"

        # 4. Stepping Stone Ford at Row 36
        rc_36 = self.get_river_center_float(36)
        hw_36 = self.get_river_half_width_float(36)
        for c in range(self.cols):
            if rc_36 - hw_36 - 0.25 <= c + 0.5 <= rc_36 + hw_36 + 0.25:
                self.terrain[36][c] = "bridge_ford"
                self.water_tiles.discard((c, 36))
                self.solid_tiles.discard((c, 36))

        # 5. Populate Ecological Vegetation & Natural Formations
        self._populate_flora_and_geology()

    def _can_place_obstacle(self, c: int, r: int) -> bool:
        if not (0 <= c < self.cols and 0 <= r < self.rows):
            return False
        if (c, r) in self.water_tiles:
            return False
        if (c, r) in self.obstacles:
            return False
        return True

    def _populate_flora_and_geology(self):
        """Places trees, shrubs, boulders, and flora in natural ecological groupings."""
        random.seed(self.seed)
        self.obstacles.clear()

        def place_cluster(obs_type, center_col, center_row, count, spread=2):
            placed = 0
            candidates = []
            for dc in range(-spread, spread + 1):
                for dr in range(-spread, spread + 1):
                    c, r = center_col + dc, center_row + dr
                    if self._can_place_obstacle(c, r):
                        candidates.append((c, r))
            random.shuffle(candidates)
            for c, r in candidates:
                if placed >= count:
                    break
                self.obstacles[(c, r)] = Obstacle(obs_type, c, r, health=1)
                placed += 1

        # A. River Shore Reeds & Pebbles on Point Bar
        for r in range(10, 72, 3):
            rc = int(self.get_river_center_float(r))
            hw = int(self.get_river_half_width_float(r))
            l_reed = rc - hw - 1
            if self._can_place_obstacle(l_reed, r):
                self.obstacles[(l_reed, r)] = Obstacle("weeds", l_reed, r, health=1, variant=1)
            r_reed = rc + hw + 1
            if self._can_place_obstacle(r_reed, r):
                self.obstacles[(r_reed, r)] = Obstacle("weeds", r_reed, r, health=1, variant=2)

        # Smooth river pebbles on the great sandy point bar (inner bend)
        place_cluster("pebble", 45, 33, 6, spread=2)
        place_cluster("pebble", 46, 42, 7, spread=2)
        place_cluster("pebble", 47, 50, 6, spread=2)
        place_cluster("log", 46, 36, 2, spread=1)
        place_cluster("clay_patch", 47, 45, 3, spread=1)

        # B. Savanna Steppe Oaks & Wild Berry Groves
        place_cluster("tree_steppe", 34, 48, 3, spread=2)
        place_cluster("tree_steppe", 42, 52, 2, spread=2)
        place_cluster("tree_steppe", 38, 36, 2, spread=2)
        place_cluster("wild_bush", 33, 49, 4, spread=1)
        place_cluster("wild_bush", 44, 49, 4, spread=1)
        place_cluster("wild_bush", 36, 38, 4, spread=1)
        place_cluster("branch", 35, 47, 3, spread=1)
        place_cluster("branch", 41, 51, 3, spread=1)

        # C. Northern Glacial Tundra (Tundra Spruces & Granite Boulders)
        tundra_tiles = [
            (c, r) for c in range(4, self.cols - 4) for r in range(4, 22)
            if self._can_place_obstacle(c, r)
        ]
        random.shuffle(tundra_tiles)
        for _ in range(28):
            if tundra_tiles:
                c, r = tundra_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("tree_tundra", c, r, health=4, max_health=4)
        for _ in range(22):
            if tundra_tiles:
                c, r = tundra_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("boulder", c, r, health=3, max_health=3)

        # D. Western Megalithic Highlands (Flint Boulders & Copper Rocks)
        highland_tiles = [
            (c, r) for c in range(2, 22) for r in range(20, 60)
            if self._can_place_obstacle(c, r)
        ]
        random.shuffle(highland_tiles)
        for _ in range(36):
            if highland_tiles:
                c, r = highland_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("boulder", c, r, health=3, max_health=3)
        for _ in range(22):
            if highland_tiles:
                c, r = highland_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("copper_rock", c, r, health=3, max_health=3)
        for _ in range(26):
            if highland_tiles:
                c, r = highland_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("rock_small", c, r, health=1)

        # E. Dense Eastern Primeval Forest (Ancient Fern Cycads & Fallen Hollow Logs)
        forest_tiles = [
            (c, r) for c in range(54, self.cols - 2) for r in range(20, 60)
            if self._can_place_obstacle(c, r)
        ]
        random.shuffle(forest_tiles)
        for _ in range(50):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("tree_forest", c, r, health=4, max_health=4)
        for _ in range(24):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("tree_stump", c, r, health=2, max_health=2)
        for _ in range(24):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("log", c, r, health=2, max_health=2)
        for _ in range(26):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("wild_bush", c, r, health=1)
        for _ in range(22):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("prop_mushroom", c, r, health=1)

        # F. Southern Mangrove Swamp & Delta
        swamp_tiles = [
            (c, r) for c in range(4, self.cols - 4) for r in range(62, self.rows - 2)
            if self._can_place_obstacle(c, r)
        ]
        random.shuffle(swamp_tiles)
        for _ in range(32):
            if swamp_tiles:
                c, r = swamp_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("tree_swamp", c, r, health=4, max_health=4)
        for _ in range(26):
            if swamp_tiles:
                c, r = swamp_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("clay_patch", c, r, health=1)
        for _ in range(26):
            if swamp_tiles:
                c, r = swamp_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("weeds", c, r, health=1)

    def check_collision(self, rect: pygame.Rect) -> bool:
        """World boundary and water collisions."""
        if rect.left < 20 or rect.right > WORLD_WIDTH - 20 or rect.top < 20 or rect.bottom > WORLD_HEIGHT - 20:
            return True
        ts = TILE_SIZE
        start_col = max(0, rect.left // ts)
        end_col = min(self.cols - 1, rect.right // ts)
        start_row = max(0, rect.top // ts)
        end_row = min(self.rows - 1, rect.bottom // ts)
        for r in range(start_row, end_row + 1):
            for c in range(start_col, end_col + 1):
                if (c, r) in self.solid_tiles:
                    tile_rect = pygame.Rect(c * ts + 4, r * ts + 4, ts - 8, ts - 8)
                    if rect.colliderect(tile_rect):
                        return True
                if (c, r) in self.obstacles:
                    obs = self.obstacles[(c, r)]
                    if not obs.is_ground_pickup:
                        obs_rect = pygame.Rect(c * ts + 8, r * ts + 8, ts - 16, ts - 16)
                        if rect.colliderect(obs_rect):
                            return True
        return False

    def is_water(self, col: int, row: int) -> bool:
        return (col, row) in self.water_tiles

    def update(self, dt: float):
        """Water caustics animation & obstacle ticks."""
        self.water_anim_timer += dt
        if self.water_anim_timer >= 0.28:
            self.water_anim_timer = 0.0
            self.water_frame = (self.water_frame + 1) % 4
        for obs in self.obstacles.values():
            obs.update(dt)
