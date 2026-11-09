"""
Map Manager for Stone Age Nature Observation Simulator.
Generates an expansive 80x80 Prehistoric Continent featuring:
- 5-tier natural elevation topography (Mountains, Terraces, Basins, Floodplains, River channel)
- 5 organic soil horizons (Talus Scree, Forest Humus, Steppe Meadow, Riparian Mud, River Sand/Pebbles)
- Continuous S-curve meandering hydrology with natural stepping stone ford
- Diverse prehistoric flora and geological formations across distinct biomes (Tundra, Highlands, Forest, Swamp)
"""

import pygame
import random
import math
from src.settings import (
    TILE_SIZE, MAP_COLS, MAP_ROWS, WORLD_WIDTH, WORLD_HEIGHT
)
from src.entities.obstacles import Obstacle

ZONE_FARM = "farm"
ZONE_TOWN = "town"


class MapManager:
    def __init__(self):
        self.cols = MAP_COLS
        self.rows = MAP_ROWS
        self.current_zone = ZONE_FARM

        # 2D Grids
        self.terrain = [["grass" for _ in range(self.cols)] for _ in range(self.rows)]
        self.obstacles = {}
        self.water_tiles = set()
        self.solid_tiles = set()

        # Elevation & Cliff Facings (Levels 0..4)
        self.farm_elevation = [[2 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_cliff_south = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_cliff_east = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_cliff_west = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_ramps = set()

        # Aliases for backwards compatibility
        self.farm_terrain = self.terrain
        self.farm_obstacles = self.obstacles
        self.farm_crops = {}
        self.farm_water_tiles = self.water_tiles
        self.farm_solid_tiles = self.solid_tiles

        # Animation
        self.water_anim_timer = 0.0
        self.water_frame = 0

        self._load_farm_map_data()
        self._build_farm_world()

    @staticmethod
    def get_river_center_float(r: float) -> float:
        """
        Continuous mathematical spline for natural meandering river.
        Creates an expressive S-curve cutting through the 80x80 continent.
        """
        return 49.0 + 8.5 * math.sin(r * 0.08) + 4.2 * math.cos(r * 0.16)

    @staticmethod
    def get_river_half_width_float(r: float) -> float:
        """
        Continuous river half-width in grid tile units.
        Narrow gorge in the North, broad ford at row 36, wide estuary in the South.
        """
        ford_broaden = 1.3 * math.exp(-((r - 36.0) ** 2) / 6.0)
        if r >= 62:
            return 2.8 + 0.8 * math.sin(r * 0.12)
        elif r <= 22:
            return 1.5 + 0.3 * math.sin(r * 0.2)
        return 2.3 + 0.6 * math.sin(r * 0.18 + 0.5) + ford_broaden

    def _load_farm_map_data(self):
        """Generates the 5-Tier Elevation Topography and 5 Ground Material Horizons."""
        # 1. Discrete 5-Tier Elevation Topography (Levels 0..4)
        # Tier 2: Central Valley Basin & Plains
        for r in range(self.rows):
            for c in range(self.cols):
                self.farm_elevation[r][c] = 2

        # Tier 4: Northern Highland Crags & Mountain Ridge
        for r in range(27):
            for c in range(self.cols):
                self.farm_elevation[r][c] = 4
        for r in range(27, 30):
            for c in range(32, 46):
                self.farm_elevation[r][c] = 4
        # Western Megalithic Highlands
        for r in range(27, 35):
            for c in range(21):
                self.farm_elevation[r][c] = 4

        # Tier 3: Elevated Hillside Terraces
        for r in range(30, 35):
            for c in range(34, 44):
                self.farm_elevation[r][c] = 3

        # Natural Ramps (Smooth walkable slopes connecting tiers)
        self.farm_ramps.clear()
        for r in (34, 35):
            for c in (37, 38, 39, 40):
                self.farm_ramps.add((c, r))
                self.farm_elevation[r][c] = 2
        for r in (36, 37, 38):
            for c in (22, 23, 24):
                self.farm_ramps.add((c, r))
                self.farm_elevation[r][c] = 2

        # Tier 1: River Floodplain Depression & Southern Mangrove Delta
        for r in range(self.rows):
            rc = self.get_river_center_float(r)
            hw = self.get_river_half_width_float(r)
            for c in range(self.cols):
                if r >= 62 or abs(c + 0.5 - rc) <= hw + 3.8:
                    if self.farm_elevation[r][c] == 2:
                        self.farm_elevation[r][c] = 1

        # Tier 0: Deep River Water Channel
        for r in range(self.rows):
            rc = self.get_river_center_float(r)
            hw = self.get_river_half_width_float(r)
            for c in range(self.cols):
                if abs(c + 0.5 - rc) <= hw + 0.15:
                    self.farm_elevation[r][c] = 0

        # Compute 2.5D Cliff Drops (South, East, West)
        for r in range(self.rows):
            for c in range(self.cols):
                self.farm_cliff_south[r][c] = 0
                self.farm_cliff_east[r][c] = 0
                self.farm_cliff_west[r][c] = 0
                if (c, r) in self.farm_ramps:
                    continue
                cur_elev = self.farm_elevation[r][c]
                if r < self.rows - 1 and (c, r + 1) not in self.farm_ramps:
                    s_elev = self.farm_elevation[r + 1][c]
                    if cur_elev > s_elev and s_elev >= 1:
                        self.farm_cliff_south[r][c] = cur_elev - s_elev
                if c < self.cols - 1 and (c + 1, r) not in self.farm_ramps:
                    e_elev = self.farm_elevation[r][c + 1]
                    if cur_elev > e_elev and e_elev >= 1:
                        self.farm_cliff_east[r][c] = cur_elev - e_elev
                if c > 0 and (c - 1, r) not in self.farm_ramps:
                    w_elev = self.farm_elevation[r][c - 1]
                    if cur_elev > w_elev and w_elev >= 1:
                        self.farm_cliff_west[r][c] = cur_elev - w_elev

        # 2. Ground Material Horizons & Biome Assignment
        self.water_tiles.clear()
        self.solid_tiles.clear()

        for r in range(self.rows):
            rc = self.get_river_center_float(r)
            hw = self.get_river_half_width_float(r)
            left_b = rc - hw
            right_b = rc + hw

            for c in range(self.cols):
                cm = c + 0.5
                elev = self.farm_elevation[r][c]

                # A. Deep River Channel
                if left_b - 0.15 <= cm <= right_b + 0.15:
                    self.terrain[r][c] = "water"
                    self.water_tiles.add((c, r))
                    self.solid_tiles.add((c, r))

                # B. Dry Talus Scree & Stony Crags (Highland Mountain Ridges)
                elif elev >= 4 or (elev == 3 and r <= 32):
                    self.terrain[r][c] = "scree_talus"

                # C. Moist Forest Humus (Dense Eastern Primeval Forest)
                elif c >= 56:
                    self.terrain[r][c] = "forest_humus"

                # D. Alluvial Riparian Mud (Floodplain depression & South Swamp)
                elif r >= 62 or (r >= 52 and abs(cm - rc) <= hw + 4.8):
                    self.terrain[r][c] = "riparian_mud"

                # E. Lush Steppe Meadow (Central Basin Plain & River Bank)
                else:
                    self.terrain[r][c] = "steppe_meadow"

        # 3. River Crossing: Stepping Stone Ford at r=36
        rc_36 = self.get_river_center_float(36)
        hw_36 = self.get_river_half_width_float(36)
        for c in range(self.cols):
            if rc_36 - hw_36 - 0.2 <= c + 0.5 <= rc_36 + hw_36 + 0.2:
                self.terrain[36][c] = "bridge_ford"
                self.water_tiles.discard((c, 36))
                self.solid_tiles.discard((c, 36))

    def _build_farm_world(self):
        """Populates authentic, lush prehistoric vegetation clusters and natural formations."""
        random.seed(42)
        self.obstacles.clear()

        def place_cluster(obs_type, center_col, center_row, count, spread=2):
            placed = 0
            candidates = []
            for dc in range(-spread, spread + 1):
                for dr in range(-spread, spread + 1):
                    c, r = center_col + dc, center_row + dr
                    if 0 <= c < self.cols and 0 <= r < self.rows:
                        if self._can_place_obstacle(c, r) and (c, r) not in self.obstacles:
                            candidates.append((c, r))
            random.shuffle(candidates)
            for c, r in candidates:
                if placed >= count:
                    break
                self.obstacles[(c, r)] = Obstacle(obs_type, c, r, health=1)
                placed += 1

        # 1. RIPARIAN WETLAND & REEDS CLUSTER (Ven Sông & Bãi Bồi)
        for r in range(12, 70, 3):
            rc = int(self.get_river_center_float(r))
            hw = int(self.get_river_half_width_float(r))
            l_reed = rc - hw - 1
            if self._can_place_obstacle(l_reed, r):
                self.obstacles[(l_reed, r)] = Obstacle("weeds", l_reed, r, health=1, variant=1)
            r_reed = rc + hw + 1
            if self._can_place_obstacle(r_reed, r):
                self.obstacles[(r_reed, r)] = Obstacle("weeds", r_reed, r, health=1, variant=2)

        # Smooth river pebbles & flint chips on the Point Bar (rows 28..50)
        place_cluster("pebble", 45, 33, 5, spread=2)
        place_cluster("pebble", 46, 42, 6, spread=2)
        place_cluster("pebble", 47, 49, 5, spread=2)

        # River driftwood & clay patches near riverbanks
        place_cluster("log", 46, 35, 2, spread=1)
        place_cluster("clay_patch", 47, 45, 3, spread=1)

        # 2. SAVANNA OAKS & GRAZING MEADOW CLUSTER (Đồng Bằng Trung Tâm)
        if self._can_place_obstacle(34, 48):
            self.obstacles[(34, 48)] = Obstacle("tree_steppe", 34, 48, health=4, max_health=4)
        if self._can_place_obstacle(42, 50):
            self.obstacles[(42, 50)] = Obstacle("tree_steppe", 42, 50, health=4, max_health=4)
        if self._can_place_obstacle(38, 36):
            self.obstacles[(38, 36)] = Obstacle("tree_steppe", 38, 36, health=4, max_health=4)

        # Wild berry groves in the open savanna
        place_cluster("wild_bush", 33, 49, 4, spread=1)
        place_cluster("wild_bush", 44, 49, 4, spread=1)
        place_cluster("wild_bush", 35, 36, 4, spread=1)

        # Fallen branches under oak trees
        place_cluster("branch", 35, 47, 3, spread=1)
        place_cluster("branch", 41, 51, 3, spread=1)

        # 3. HIGHLAND TALUS & ROCK LEDGES (Chân Núi & Vách Đá)
        for c, r in [(33, 29), (36, 28), (42, 28), (45, 29), (32, 33), (45, 33)]:
            if self._can_place_obstacle(c, r):
                self.obstacles[(c, r)] = Obstacle("tree_tundra", c, r, health=4, max_health=4)

        place_cluster("boulder", 35, 31, 3, spread=1)
        place_cluster("boulder", 43, 31, 3, spread=1)
        place_cluster("rock_small", 37, 32, 3, spread=1)
        place_cluster("rock_small", 43, 33, 3, spread=1)
        place_cluster("prop_mushroom", 36, 33, 3, spread=1)

        # 4. CONTINENT-WIDE BIOME DISTRIBUTIONS
        # A. Northern Tundra (rows 4..22)
        tundra_tiles = [
            (c, r) for c in range(4, self.cols - 4) for r in range(4, 22)
            if self._can_place_obstacle(c, r)
        ]
        random.shuffle(tundra_tiles)
        for _ in range(25):
            if tundra_tiles:
                c, r = tundra_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("tree_tundra", c, r, health=4, max_health=4)
        for _ in range(20):
            if tundra_tiles:
                c, r = tundra_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("boulder", c, r, health=3, max_health=3)

        # B. Megalithic Highlands (cols 2..22, rows 20..60)
        highland_tiles = [
            (c, r) for c in range(2, 22) for r in range(20, 60)
            if self._can_place_obstacle(c, r)
        ]
        random.shuffle(highland_tiles)
        for _ in range(35):
            if highland_tiles:
                c, r = highland_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("boulder", c, r, health=3, max_health=3)
        for _ in range(22):
            if highland_tiles:
                c, r = highland_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("copper_rock", c, r, health=3, max_health=3)
        for _ in range(25):
            if highland_tiles:
                c, r = highland_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("rock_small", c, r, health=1)

        # C. Primeval Forest (cols 56..78, rows 20..60)
        forest_tiles = [
            (c, r) for c in range(56, self.cols - 2) for r in range(20, 60)
            if self._can_place_obstacle(c, r)
        ]
        random.shuffle(forest_tiles)
        for _ in range(48):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("tree_forest", c, r, health=4, max_health=4)
        for _ in range(22):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("tree_stump", c, r, health=2, max_health=2)
        for _ in range(22):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("log", c, r, health=2, max_health=2)
        for _ in range(24):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("wild_bush", c, r, health=1)
        for _ in range(20):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("prop_mushroom", c, r, health=1)

        # D. Ancient Swamp & Mangrove Delta (rows 62..78)
        swamp_tiles = [
            (c, r) for c in range(4, self.cols - 4) for r in range(62, self.rows - 2)
            if self._can_place_obstacle(c, r)
        ]
        random.shuffle(swamp_tiles)
        for _ in range(32):
            if swamp_tiles:
                c, r = swamp_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("tree_swamp", c, r, health=4, max_health=4)
        for _ in range(25):
            if swamp_tiles:
                c, r = swamp_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("clay_patch", c, r, health=1)
        for _ in range(25):
            if swamp_tiles:
                c, r = swamp_tiles.pop()
                self.obstacles[(c, r)] = Obstacle("weeds", c, r, health=1)

    def _can_place_obstacle(self, col, row):
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return False
        if (col, row) in self.water_tiles:
            return False
        if (col, row) in self.obstacles:
            return False
        return True

    def check_collision(self, rect):
        """Check if rect collides with solid boundaries or water."""
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

    def is_water(self, col, row):
        return (col, row) in self.water_tiles

    def is_near_water(self, col, row):
        for dc, dr in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]:
            if self.is_water(col + dc, row + dr):
                return True
        return False

    def update(self, dt):
        """Water caustics animation & obstacle shake ticks."""
        self.water_anim_timer += dt
        if self.water_anim_timer >= 0.28:
            self.water_anim_timer = 0.0
            self.water_frame = (self.water_frame + 1) % 4
        for obs in self.obstacles.values():
            obs.update(dt)
