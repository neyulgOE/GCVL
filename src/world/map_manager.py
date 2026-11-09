"""
Map Manager and Multi-Zone Grid World for Green Valley Tales.
Handles:
1. Farm Zone (50x40): Authentic river & pond, cozy farmhouse, fields, obstacles, coop, shipping bin, storage.
2. Town Zone (50x40): Cobblestone plaza, central fountain, shops (Cô Mai, Bác Bảy, Cụ Ba Tri), teleport waypoints.
3. Seamless transitions (walking through borders) & Fast Travel Teleportation.
4. Rare excavation drops when tilling farmable soil.
"""

import pygame
import random
import json
import os
import math
from src.settings import (
    TILE_SIZE, MAP_COLS, MAP_ROWS, WORLD_WIDTH, WORLD_HEIGHT,
    TOOL_HOE, TOOL_WATER_CAN, TOOL_AXE, TOOL_PICKAXE, TOOL_SCYTHE, TOOL_FISHING_ROD
)
from src.entities.obstacles import Obstacle
from src.entities.crops import Crop
from src.entities.npc import NPC

ZONE_FARM = "farm"
ZONE_TOWN = "town"

class MapManager:
    def __init__(self):
        self.cols = MAP_COLS
        self.rows = MAP_ROWS
        self.current_zone = ZONE_FARM
        
        # --- Farm Zone Data ---
        self.farm_terrain = [["grass" for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_obstacles = {}
        self.farm_crops = {}
        self.farm_water_tiles = set()
        self.farm_solid_tiles = set()
        self.farmable_tiles = set()
        
        # Farm / Prehistoric Tribal Sanctuary Key Locations (Centered around 40, 38)
        self.campfire_pos = (40, 38)        # Campfire gathering hearth (Tier 2 Basin)
        self.shelter_pos = (38, 30)         # Ancestral Rock Shelter (Tier 3 Hillside Terrace)
        self.bed_pos = (38, 32)             # Inside rock shelter sleeping area
        self.house_door_pos = (38, 32)      # Cave shelter entrance
        self.shipping_bin_pos = (43, 38)    # Tribal Resource Cache (Kho Bộ Tộc)
        self.farm_waypoint = (40, 42)       # Inukshuk Stone Cairn Waypoint
        self.coop_pos = (36, 33)            # Fowl pen / Pelt Tipi
        self.barn_col = 36
        self.barn_row = 33
        self.house_col = 38
        self.house_row = 30
        self.workshop_pos = (37, 40)        # Flintknapping & Tool Workshop (Tier 2 Basin)
        self.smoker_pos = (42, 35)          # Meat Smoker & Drying Rack (Natural River Breeze)
        self.shrine_pos = (35, 42)          # Megalithic Totem Shrine
        self.palisade_gate_pos = (45, 40)   # Stake & Mammoth Bone Beast Barrier
        self.merchant_pos = (43, 42)        # Tribal Trader
        self.farm_road_exit = (79, 38)      # Trail leading east to boundary

        # Discrete 5-Tier Elevation System (Levels 0..4) & Topography
        self.farm_elevation = [[2 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_cliff_south = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_cliff_east = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_cliff_west = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_ramps = set()

        # --- Town Zone Data ---
        self.town_terrain = [["grass" for _ in range(self.cols)] for _ in range(self.rows)]
        self.town_obstacles = {}
        self.town_water_tiles = set()
        self.town_solid_tiles = set()
        self.town_waypoint = (25, 24)       # Fast Travel Waypoint in town plaza
        self.town_road_exit = (0, 20)       # Road westward to farm
        
        # Town NPCs (Stone Tribe Leaders)
        self.npcs = {
            "co_mai": NPC("thay_mo_kraa", "Thầy Mo Kraa", "Giữ Lửa & Dược Thảo", col=14, row=15, personality="friendly"),
            "bac_bay": NPC("tho_san_boomer", "Thợ Săn Boomer", "Chế Tác Vũ Khí & Quặng", col=35, row=15, personality="gruff"),
            "cu_ba_tri": NPC("toc_truong_ogg", "Tộc Trưởng Ogg", "Đại Thủ Lĩnh Bộ Tộc", col=25, row=9, personality="wise")
        }

        # Active Pointers (point to current zone's collections)
        self.terrain = self.farm_terrain
        self.obstacles = self.farm_obstacles
        self.crops = self.farm_crops
        self.water_tiles = self.farm_water_tiles
        self.solid_tiles = self.farm_solid_tiles

        # Animation
        self.water_anim_timer = 0.0
        self.water_frame = 0

        self._load_farm_map_data()
        self._build_farm_world()
        self._build_town_world()

    @staticmethod
    def get_river_center_float(r: float) -> float:
        """
        Continuous mathematical spline for natural meandering river.
        Creates an expressive S-curve cutting through the 80x80 continent:
        - Swings East in Northern Mountains
        - Sweeps West in Central Basin (creating a massive Point Bar on inner bank)
        - Deflects East at the Stepping Stone Ford (r=36)
        - Spreads into delta marshes in the South
        """
        return 49.0 + 8.5 * math.sin(r * 0.08) + 4.2 * math.cos(r * 0.16)

    @staticmethod
    def get_river_half_width_float(r: float) -> float:
        """
        Continuous river half-width in grid tile units:
        - Narrow rushing canyon gorge in Northern mountains (~1.6 tiles)
        - Broad shallow wading ford at row 36 (~3.4 tiles)
        - Wide braided estuary in Southern mangrove delta (~3.8 tiles)
        """
        ford_broaden = 1.3 * math.exp(-((r - 36.0) ** 2) / 6.0)
        if r >= 62:
            return 2.8 + 0.8 * math.sin(r * 0.12)
        elif r <= 22:
            return 1.5 + 0.3 * math.sin(r * 0.2)
        return 2.1 + 0.4 * math.sin(r * 0.14) + ford_broaden

    # -------------------------------------------------------------
    # PREHISTORIC STONE AGE CONTINENT (80x80 RTS MAP)
    # -------------------------------------------------------------
    def _load_farm_map_data(self):
        """
        Generates an expansive 80x80 Prehistoric continent with:
        - Discrete 5-Tier Elevation Topography (Levels 0..4) with 2.5D Cliff Facings & Natural Ramps
        - 5 Distinct Ground Horizons (Dry Talus Scree, Lush Steppe Meadow, Forest Humus, Riparian Mud, River Sand/Pebble)
        - S-Curve Meandering Hydrology & Massive Point Bar Deposit
        - Ecological Settlement Loam with 80-120px River Buffer Zone
        """
        # 1. Discrete 5-Tier Elevation Topography (Levels 0..4)
        # Default Tier 2 (Central Valley Basin & Plains)
        for r in range(self.rows):
            for c in range(self.cols):
                self.farm_elevation[r][c] = 2

        # Tier 4: Northern Highland Crags & Mountain Ridge backing the cave
        for r in range(27):
            for c in range(self.cols):
                self.farm_elevation[r][c] = 4
        # North ridge behind the cave
        for r in range(27, 30):
            for c in range(32, 46):
                self.farm_elevation[r][c] = 4
        # Western Megalithic Highlands
        for r in range(27, 35):
            for c in range(21):
                self.farm_elevation[r][c] = 4

        # Tier 3: Cave Terrace Hillside (Ancestral Rock Shelter perched high on elevated terrace)
        for r in range(30, 35):
            for c in range(34, 44):
                self.farm_elevation[r][c] = 3

        # Natural Ramps (Smooth walkable slopes connecting tiers)
        self.farm_ramps.clear()
        # Ramp 1: From Tier 3 Cave Terrace down to Tier 2 Fireplace Basin (Wide ceremonial access)
        for r in (34, 35):
            for c in (37, 38, 39, 40):
                self.farm_ramps.add((c, r))
                self.farm_elevation[r][c] = 2
        # Ramp 2: Western Highland Pass
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
        self.farm_water_tiles.clear()
        self.farm_solid_tiles.clear()

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
                    self.farm_terrain[r][c] = "water"
                    self.farm_water_tiles.add((c, r))
                    self.farm_solid_tiles.add((c, r))

                # B. Dry Talus Scree & Stony Crags (Tier 4 Mountain Crags & Cave Shelf)
                elif elev >= 4 or (elev == 3 and r <= 32):
                    self.farm_terrain[r][c] = "scree_talus"

                # C. Moist Forest Humus (Dense Eastern Primeval Forest)
                elif c >= 56:
                    self.farm_terrain[r][c] = "forest_humus"

                # D. Alluvial Riparian Mud (Floodplain depression & South Swamp)
                elif r >= 62 or (r >= 52 and abs(cm - rc) <= hw + 4.8):
                    self.farm_terrain[r][c] = "riparian_mud"

                # E. Lush Steppe Meadow (Central Basin Plain & River Bank)
                else:
                    self.farm_terrain[r][c] = "steppe_meadow"

        # 3. River Crossings: Stepping Stone Ford (r=36) & Fallen Log Bridge (r=48)
        rc_36 = self.get_river_center_float(36)
        hw_36 = self.get_river_half_width_float(36)
        for c in range(self.cols):
            if rc_36 - hw_36 - 0.2 <= c + 0.5 <= rc_36 + hw_36 + 0.2:
                self.farm_terrain[36][c] = "bridge_ford"
                self.farm_water_tiles.discard((c, 36))
                self.farm_solid_tiles.discard((c, 36))

        rc_48 = self.get_river_center_float(48)
        hw_48 = self.get_river_half_width_float(48)
        for c in range(self.cols):
            if rc_48 - hw_48 - 0.2 <= c + 0.5 <= rc_48 + hw_48 + 0.2:
                self.farm_terrain[48][c] = "bridge_log"
                self.farm_water_tiles.discard((c, 48))
                self.farm_solid_tiles.discard((c, 48))

        # 4. Human Settlement Trampled Loam Apron & Footpaths
        # Maintains 80-120px (cols 44..48) Ecological Buffer from the river
        # Tight natural footprints leave the central valley open as a lush grazing meadow
        camp_activity_centers = [
            (40, 38, 1.4),  # Central campfire hearth footprint
            (38, 33, 1.6),  # Ancestral Rock Cave apron (Tier 3 Terrace)
            (37, 40, 1.2),  # Flintknapping workshop footprint
            (42, 35, 1.2),  # Meat smoker & drying rack footprint
            (35, 42, 1.1),  # Megalithic shrine base
            (45, 40, 1.2),  # Beast barrier threshold
            (35, 36, 1.0),  # Grass tent footprint
            (37, 38, 1.0),  # Grass tent footprint
            (42, 36, 1.0),  # Pelt tipi footprint
            (43, 38, 1.0),  # Pelt tipi footprint
        ]
        for r in range(28, 48):
            for c in range(30, 46):
                if 0 <= c < self.cols and 0 <= r < self.rows:
                    if self.farm_terrain[r][c] not in ["water", "bridge_ford", "bridge_log"]:
                        for cx, cy, rad in camp_activity_centers:
                            if math.hypot(c - cx, r - cy) <= rad:
                                self.farm_terrain[r][c] = "settlement_loam"
                                self.farm_solid_tiles.discard((c, r))
                                break

        # Organic Beaten Footpaths connecting camp hubs
        settlement_tracks = [
            # Cave Terrace to Ramp down to Campfire
            (38, 34), (39, 35), (39, 36), (40, 37),
            # Campfire to Flintknapping Workshop
            (39, 39), (38, 39), (37, 40),
            # Campfire to Smoker
            (40, 37), (41, 36), (42, 35),
            # Campfire to Beast Barrier & River Buffer
            (41, 38), (42, 39), (43, 39), (44, 40), (45, 40),
            # Beast Barrier eastward through buffer to Stepping Stone Ford
            (45, 39), (46, 38), (47, 37), (48, 36),
            # Campfire to Megalithic Shrine
            (39, 39), (38, 40), (37, 41), (36, 42),
        ]
        for c, r in settlement_tracks:
            if 0 <= c < self.cols and 0 <= r < self.rows:
                if self.farm_terrain[r][c] not in ["water", "bridge_ford", "bridge_log"]:
                    self.farm_terrain[r][c] = "trail_dirt"
                    self.farm_solid_tiles.discard((c, r))

        # 5. Farmable Clearing Garden (cols 36..43, rows 40..45)
        self.farmable_tiles.clear()
        for r in range(40, 46):
            for c in range(36, 44):
                if (c, r) not in self.farm_water_tiles and (c, r) not in self.farm_solid_tiles:
                    self.farmable_tiles.add((c, r))

        # Clear sanctuary centers
        sanctuary_cleared = [
            self.campfire_pos, self.shelter_pos, self.bed_pos, self.shipping_bin_pos,
            self.farm_waypoint, self.workshop_pos, self.smoker_pos, self.shrine_pos,
            self.palisade_gate_pos, (39, 38), (41, 38), (40, 37), (40, 39),
            (39, 35), (40, 35)  # Ramp
        ]
        for pt in sanctuary_cleared:
            self.farm_solid_tiles.discard(pt)

        self.water_tiles = self.farm_water_tiles
        self.solid_tiles = self.farm_solid_tiles

    def _build_farm_world(self):
        """
        Populate authentic ecological vegetation clusters:
        1. Riparian Wetland & Reeds Cluster along riverbanks and point bar
        2. Savanna Steppe Oak & Berry Grove Grazing Meadow in central plain
        3. Highland Talus, Dwarf Spruces & Flint Boulders around cave terrace
        4. Primeval Dense Forest Canopy with Fallen Logs across the river
        """
        random.seed(42)
        self.farm_obstacles.clear()

        def place_cluster(obs_type, center_col, center_row, count, spread=2):
            placed = 0
            candidates = []
            for dc in range(-spread, spread + 1):
                for dr in range(-spread, spread + 1):
                    c, r = center_col + dc, center_row + dr
                    if 0 <= c < self.cols and 0 <= r < self.rows:
                        if self._can_place_obstacle(c, r) and (c, r) not in self.farm_obstacles:
                            candidates.append((c, r))
            random.shuffle(candidates)
            for c, r in candidates:
                if placed >= count:
                    break
                self.farm_obstacles[(c, r)] = Obstacle(obs_type, c, r, health=1)
                placed += 1

        # ---------------------------------------------------------
        # 1. RIPARIAN WETLAND & POINT BAR CLUSTER (Ven Sông & Bãi Bồi)
        # ---------------------------------------------------------
        # Reeds & cattails ribbon along the water margin
        for r in range(12, 70, 3):
            rc = int(self.get_river_center_float(r))
            hw = int(self.get_river_half_width_float(r))
            # Left bank reeds
            l_reed = rc - hw - 1
            if self._can_place_obstacle(l_reed, r):
                self.farm_obstacles[(l_reed, r)] = Obstacle("weeds", l_reed, r, health=1, variant=1)
            # Right bank reeds
            r_reed = rc + hw + 1
            if self._can_place_obstacle(r_reed, r):
                self.farm_obstacles[(r_reed, r)] = Obstacle("weeds", r_reed, r, health=1, variant=2)

        # Smooth river pebbles & flint chips on the Point Bar (rows 28..50)
        place_cluster("pebble", 45, 33, 4, spread=2)
        place_cluster("pebble", 46, 42, 5, spread=2)
        place_cluster("pebble", 47, 49, 4, spread=2)

        # River driftwood & water-worn logs near buffer
        place_cluster("log", 46, 35, 2, spread=1)
        place_cluster("clay_patch", 47, 45, 3, spread=1)

        # ---------------------------------------------------------
        # 2. SAVANNA OAKS & GRAZING MEADOW CLUSTER (Đồng Bằng Trung Tâm)
        # ---------------------------------------------------------
        # South plain (cols 30..46, rows 46..56): Pasture for grazing deer and bison
        # Two majestic ancient oaks providing shade
        if self._can_place_obstacle(34, 48):
            self.farm_obstacles[(34, 48)] = Obstacle("tree_steppe", 34, 48, health=4, max_health=4)
        if self._can_place_obstacle(42, 50):
            self.farm_obstacles[(42, 50)] = Obstacle("tree_steppe", 42, 50, health=4, max_health=4)

        # Berry groves forming natural hedgerows around the grazing pasture
        place_cluster("wild_bush", 33, 49, 4, spread=1)
        place_cluster("wild_bush", 44, 49, 4, spread=1)
        place_cluster("wild_bush", 35, 36, 3, spread=1)  # Northwest camp berry grove

        # Fallen branches under oak trees
        place_cluster("branch", 35, 47, 3, spread=1)
        place_cluster("branch", 41, 51, 3, spread=1)

        # ---------------------------------------------------------
        # 3. HIGHLAND TALUS & CAVE LEDGES CLUSTER (Chân Núi & Hang Đá)
        # ---------------------------------------------------------
        # Dwarf spruces on rock ledges backing the cave
        for c, r in [(33, 29), (36, 28), (42, 28), (45, 29), (32, 33), (45, 33)]:
            if self._can_place_obstacle(c, r):
                self.farm_obstacles[(c, r)] = Obstacle("tree_tundra", c, r, health=4, max_health=4)

        # Massive granite boulders flanking the cave terrace
        place_cluster("boulder", 35, 31, 3, spread=1)
        place_cluster("boulder", 43, 31, 3, spread=1)

        # Flint nodes & rock rubble along the base of the cliff
        place_cluster("rock_small", 37, 32, 3, spread=1)
        place_cluster("rock_small", 43, 33, 3, spread=1)

        # Blue glow rock mushrooms in shaded cave crevice
        place_cluster("prop_mushroom", 36, 33, 3, spread=1)

        # ---------------------------------------------------------
        # 4. CONTINENT-WIDE BIOME RESOURCE DISTRIBUTIONS
        # ---------------------------------------------------------
        # A. Northern Tundra (rows 0..22)
        tundra_tiles = [
            (c, r) for c in range(4, self.cols - 4) for r in range(4, 22)
            if self._can_place_obstacle(c, r)
        ]
        random.shuffle(tundra_tiles)
        for _ in range(25):
            if tundra_tiles:
                c, r = tundra_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("prop_bone", c, r, health=1)
        for _ in range(20):
            if tundra_tiles:
                c, r = tundra_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("tree_tundra", c, r, health=4, max_health=4)
        for _ in range(16):
            if tundra_tiles:
                c, r = tundra_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("boulder", c, r, health=3, max_health=3)

        # B. Megalithic Highlands (cols 0..22, rows 20..60)
        highland_tiles = [
            (c, r) for c in range(2, 22) for r in range(20, 60)
            if self._can_place_obstacle(c, r)
        ]
        random.shuffle(highland_tiles)
        for _ in range(35):
            if highland_tiles:
                c, r = highland_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("boulder", c, r, health=3, max_health=3)
        for _ in range(20):
            if highland_tiles:
                c, r = highland_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("copper_rock", c, r, health=3, max_health=3)
        for _ in range(25):
            if highland_tiles:
                c, r = highland_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("rock_small", c, r, health=1)

        # C. Dense Primeval Forest (cols 56..80, rows 20..60)
        forest_tiles = [
            (c, r) for c in range(56, self.cols - 2) for r in range(20, 60)
            if self._can_place_obstacle(c, r)
        ]
        random.shuffle(forest_tiles)
        for _ in range(45):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("tree_forest", c, r, health=4, max_health=4)
        for _ in range(20):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("tree_stump", c, r, health=2, max_health=2)
        for _ in range(20):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("log", c, r, health=2, max_health=2)
        for _ in range(20):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("wild_bush", c, r, health=1)
        for _ in range(18):
            if forest_tiles:
                c, r = forest_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("prop_mushroom", c, r, health=1)

        # D. Ancient Swamp & Mangrove Delta (rows 62..80)
        swamp_tiles = [
            (c, r) for c in range(4, self.cols - 4) for r in range(62, self.rows - 2)
            if self._can_place_obstacle(c, r)
        ]
        random.shuffle(swamp_tiles)
        for _ in range(30):
            if swamp_tiles:
                c, r = swamp_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("tree_swamp", c, r, health=4, max_health=4)
        for _ in range(25):
            if swamp_tiles:
                c, r = swamp_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("clay_patch", c, r, health=1)
        for _ in range(25):
            if swamp_tiles:
                c, r = swamp_tiles.pop()
                self.farm_obstacles[(c, r)] = Obstacle("weeds", c, r, health=1)

        self.obstacles = self.farm_obstacles

    # -------------------------------------------------------------
    # TOWN ZONE BUILDER
    # -------------------------------------------------------------
    def _build_town_world(self):
        """Constructs the Town Zone layout (Plaza, Shops, Fountain, Waypoint)."""
        # 1. Base terrain: Grass border with large cobblestone central plaza
        for r in range(self.rows):
            for c in range(self.cols):
                self.town_terrain[r][c] = "grass"

        # Paved central square / plaza (cols 14..36, rows 12..28)
        for r in range(12, 29):
            for c in range(14, 37):
                self.town_terrain[r][c] = "cobble"

        # Road leading west to Farm (cols 0..14, rows 19..21)
        for r in range(19, 22):
            for c in range(0, 15):
                self.town_terrain[r][c] = "stone_road"

        # Road heading North to shops (cols 24..26, rows 6..12)
        for r in range(6, 13):
            for c in range(24, 27):
                self.town_terrain[r][c] = "cobble"

        # 2. Central Fountain (cols 24..26, rows 19..21)
        for r in range(19, 22):
            for c in range(24, 27):
                self.town_water_tiles.add((c, r))
                self.town_solid_tiles.add((c, r))
                self.town_terrain[r][c] = "water"

        # 3. Buildings & Shop Counters (Marked as solid tiles)
        # Shop 1: Tiệm Nông Sản Cô Mai (cols 10..18, rows 9..14)
        for r in range(9, 15):
            for c in range(10, 19):
                self.town_solid_tiles.add((c, r))
        # Clear counter entrance for interaction
        self.town_solid_tiles.discard((14, 15))

        # Shop 2: Lò Rèn Bác Bảy (cols 32..40, rows 9..14)
        for r in range(9, 15):
            for c in range(32, 41):
                self.town_solid_tiles.add((c, r))
        self.town_solid_tiles.discard((35, 15))

        # Shop 3: Tòa Thị Chính & Tạp Hóa Cụ Ba Tri (cols 20..30, rows 3..8)
        for r in range(3, 9):
            for c in range(20, 31):
                self.town_solid_tiles.add((c, r))
        self.town_solid_tiles.discard((25, 9))

        # 4. Outer Boundary Cliffs (Town walls)
        # North wall
        for c in range(self.cols):
            for r in range(0, 5):
                self.town_solid_tiles.add((c, r))
        # South wall
        for c in range(self.cols):
            for r in range(35, self.rows):
                self.town_solid_tiles.add((c, r))
        # East wall
        for r in range(self.rows):
            for c in range(46, self.cols):
                self.town_solid_tiles.add((c, r))
        # West wall (except road cols 0..2, rows 19..21)
        for r in range(self.rows):
            if not (19 <= r <= 21):
                for c in range(0, 3):
                    self.town_solid_tiles.add((c, r))

    # -------------------------------------------------------------
    # ZONE SWITCHING & TELEPORTATION
    # -------------------------------------------------------------
    def switch_zone(self, new_zone, player=None, spawn_tile=None):
        """Switches active zone between 'farm' and 'town'."""
        if new_zone not in [ZONE_FARM, ZONE_TOWN]:
            return False

        if new_zone == self.current_zone:
            if player and spawn_tile:
                player.x = spawn_tile[0] * TILE_SIZE
                player.y = spawn_tile[1] * TILE_SIZE
                player.move_target = None
            return True

        self.current_zone = new_zone

        if new_zone == ZONE_FARM:
            self.terrain = self.farm_terrain
            self.obstacles = self.farm_obstacles
            self.crops = self.farm_crops
            self.water_tiles = self.farm_water_tiles
            self.solid_tiles = self.farm_solid_tiles
            target_tile = spawn_tile if spawn_tile else self.farm_waypoint
        else:  # ZONE_TOWN
            self.terrain = self.town_terrain
            self.obstacles = self.town_obstacles
            self.crops = {}  # No crops in town plaza
            self.water_tiles = self.town_water_tiles
            self.solid_tiles = self.town_solid_tiles
            target_tile = spawn_tile if spawn_tile else self.town_waypoint

        if player:
            player.x = target_tile[0] * TILE_SIZE
            player.y = target_tile[1] * TILE_SIZE
            player.move_target = None

        return True

    def check_border_transition(self, player):
        """Checks if player walked past boundary roads to transition between zones."""
        px = player.x
        py = player.y
        col = int(px // TILE_SIZE)
        row = int(py // TILE_SIZE)

        # Farm -> Town transition (walked off east road)
        if self.current_zone == ZONE_FARM:
            if col >= self.cols - 1 and 18 <= row <= 22:
                # Arrive at Town West entrance
                self.switch_zone(ZONE_TOWN, player, spawn_tile=(3, 20))
                return "Đã bước vào Thị Trấn Hương Đồng!"

        # Town -> Farm transition (walked off west road)
        elif self.current_zone == ZONE_TOWN:
            if col <= 1 and 18 <= row <= 22:
                # Arrive at Farm East road
                self.switch_zone(ZONE_FARM, player, spawn_tile=(self.cols - 3, 20))
                return "Đã trở về Nông Trại Hương Đồng!"

        return None

    def _can_place_obstacle(self, col, row):
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return False
        if (col, row) in self.water_tiles or (col, row) in self.solid_tiles:
            return False
        if (col, row) in [self.house_door_pos, self.bed_pos, self.shipping_bin_pos, 
                          self.coop_pos, self.merchant_pos, self.farm_waypoint]:
            return False
        if (col, row) in self.obstacles:
            return False
        return True

    def check_collision(self, rect):
        """Check if rect collides with solid world boundaries, cliffs, fences, or obstacles."""
        if rect.left < 20 or rect.right > WORLD_WIDTH - 20 or rect.top < 20 or rect.bottom > WORLD_HEIGHT - 20:
            return True

        ts = TILE_SIZE
        start_col = max(0, rect.left // ts)
        end_col = min(self.cols - 1, rect.right // ts)
        start_row = max(0, rect.top // ts)
        end_row = min(self.rows - 1, rect.bottom // ts)

        for r in range(start_row, end_row + 1):
            for c in range(start_col, end_col + 1):
                # 1. Solid map tiles
                if (c, r) in self.solid_tiles:
                    tile_rect = pygame.Rect(c * ts + 4, r * ts + 4, ts - 8, ts - 8)
                    if rect.colliderect(tile_rect):
                        return True

                # 2. Water tiles are impassable
                if (c, r) in self.water_tiles:
                    tile_rect = pygame.Rect(c * ts + 2, r * ts + 2, ts - 4, ts - 4)
                    if rect.colliderect(tile_rect):
                        return True

                # 3. Obstacles (except ground pickups)
                if (c, r) in self.obstacles:
                    obs = self.obstacles[(c, r)]
                    if not obs.is_ground_pickup:
                        obs_rect = pygame.Rect(c * ts + 8, r * ts + 8, ts - 16, ts - 16)
                        if rect.colliderect(obs_rect):
                            return True

        # Tribal Sanctuary collisions
        if self.current_zone == ZONE_FARM:
            bin_rect = pygame.Rect(self.shipping_bin_pos[0] * ts + 4, self.shipping_bin_pos[1] * ts + 4, ts - 8, ts - 8)
            if rect.colliderect(bin_rect):
                return True

        return False

    def is_water(self, col, row):
        return (col, row) in self.water_tiles

    def is_near_water(self, col, row):
        """Check if tile or adjacent is water for refilling watering can."""
        for dc, dr in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]:
            if self.is_water(col + dc, row + dr):
                return True
        return False

    def is_farmable(self, col, row):
        """Only farmable when on Farm Zone."""
        if self.current_zone != ZONE_FARM:
            return False
        if self.farmable_tiles:
            return (col, row) in self.farmable_tiles
        return 37 <= col <= 45 and 39 <= row <= 46

    def update(self, dt):
        # Water ripple animation
        self.water_anim_timer += dt
        if self.water_anim_timer >= 0.28:
            self.water_anim_timer = 0.0
            self.water_frame = (self.water_frame + 1) % 4

        # Obstacle hit shakes
        for obs in self.obstacles.values():
            obs.update(dt)

        # Update NPCs
        if self.current_zone == ZONE_TOWN:
            for npc in self.npcs.values():
                npc.update(dt)

    def advance_day(self, current_season_id, is_raining=False):
        """Called overnight when player sleeps."""
        # Reset NPC daily patience
        for npc in self.npcs.values():
            npc.reset_daily_patience()

        # Advance farm crops
        for (col, row), crop in list(self.farm_crops.items()):
            crop.next_day(current_season_id, is_raining)

        # Farm Soil moisture update
        for r in range(self.rows):
            for c in range(self.cols):
                if self.farm_terrain[r][c] == "dirt_watered":
                    self.farm_terrain[r][c] = "dirt_tilled" if not is_raining else "dirt_watered"
                elif self.farm_terrain[r][c] == "dirt_tilled" and is_raining:
                    self.farm_terrain[r][c] = "dirt_watered"

    def handle_tool_action(self, tool_id, col, row, player, inventory):
        """Executes tool interaction or foraging at target tile."""
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return None, None

        if self.current_zone != ZONE_FARM:
            return "Không thể canh tác hay khai hoang trong khu vực Bản Doanh Bộ Lạc!", None

        current_terrain = self.terrain[row][col]

        # 0. GROUND PICKUPS & FORAGING (Can gather with bare hands or ANY tool!)
        if (col, row) in self.obstacles:
            obs = self.obstacles[(col, row)]
            if obs.is_ground_pickup:
                drops, success = obs.hit(tool_id or "hands")
                if success:
                    player.consume_stamina(0.5)
                    if drops:
                        for d in drops:
                            inventory.add_item(d, d.get("qty", 1))
                        if obs.obs_type == "wild_bush":
                            obs.growth_stage = "depleted"
                            obs.regrow_timer = 120.0
                        else:
                            del self.obstacles[(col, row)]
                        return f"Thu lượm {drops[0]['name']}!", "success"
                    return None, "success"

        # 1. HOE & DIGGING STICK
        is_hoe = tool_id in [TOOL_HOE, "digging_stick", "stone_hoe", "bronze_hoe"]
        if is_hoe:
            if (col, row) in self.obstacles and self.obstacles[(col, row)].obs_type == "clay_patch":
                obs = self.obstacles[(col, row)]
                drops, success = obs.hit(tool_id)
                if success and drops:
                    for d in drops:
                        inventory.add_item(d, d.get("qty", 1))
                    del self.obstacles[(col, row)]
                    player.consume_stamina(player.get_tool_stamina_cost(tool_id))
                    return f"Đã đào {drops[0]['name']}!", "dig"

            if self.is_farmable(col, row) and (col, row) not in self.obstacles:
                if current_terrain not in ["dirt_tilled", "dirt_watered"]:
                    self.terrain[row][col] = "dirt_tilled"
                    player.consume_stamina(player.get_tool_stamina_cost(tool_id))

                    # 8% chance to unearth an ancient relic
                    if random.random() < 0.08:
                        relic = random.choice([
                            {"id": "ancient_coin", "type": "rare", "name": "Đồng Tiền Triều Đại Cổ", "price": 220, "qty": 1, "is_rare": True},
                            {"id": "clay_relic", "type": "rare", "name": "Cổ Vật Gốm Tiền Sử", "price": 380, "qty": 1, "is_rare": True},
                            {"id": "flint", "type": "material", "name": "Đá Lửa Ngầm", "price": 8, "qty": 2}
                        ])
                        inventory.add_item(relic, relic.get("qty", 1))
                        return f"Đã xới đất và đào được {relic['name']}!", "success"

                    return "Đã xới đất tơi xốp!", "dig"
            else:
                return "Khu vực này không thích hợp để xới đất!", None

        # 2. WATERING CAN & CLAY JUG
        is_water_tool = tool_id in [TOOL_WATER_CAN, "clay_jug"]
        if is_water_tool:
            active_item = inventory.active_item
            if self.is_near_water(col, row):
                active_item["water"] = active_item.get("max_water", 35)
                return "Đã múc đầy nước mát vào bình!", "water"

            if current_terrain == "dirt_tilled":
                if active_item.get("water", 0) > 0:
                    active_item["water"] -= 1
                    self.terrain[row][col] = "dirt_watered"
                    if (col, row) in self.crops:
                        self.crops[(col, row)].water()
                    player.consume_stamina(player.get_tool_stamina_cost(tool_id))
                    return "Đã tưới nước ẩm luống đất!", "water"
                else:
                    return "Bình gốm đã cạn nước! Hãy ra bờ suối múc thêm.", None

        # 3. AXE (Primitive Axe, Polished Axe, Bronze Axe)
        is_axe = tool_id in [TOOL_AXE, "primitive_axe", "polished_axe", "bronze_axe"]
        if is_axe:
            if (col, row) in self.obstacles:
                obs = self.obstacles[(col, row)]
                drops, success = obs.hit(tool_id)
                if success:
                    player.consume_stamina(player.get_tool_stamina_cost(tool_id))
                    if drops:
                        for d in drops:
                            inventory.add_item(d, d.get("qty", 1))
                        if obs.obs_type.startswith("tree") and obs.obs_type != "tree_stump":
                            # Woodcut progression: Felled tree transforms into mossy stump!
                            self.obstacles[(col, row)] = Obstacle("tree_stump", col, row, health=2, max_health=2)
                        else:
                            del self.obstacles[(col, row)]
                        return f"Thu hoạch {drops[0]['name']}!", "chop"
                    return None, "chop"

        # 4. PICKAXE (Stone Pick, Bronze Pick)
        is_pick = tool_id in [TOOL_PICKAXE, "stone_pick", "bronze_pick"]
        if is_pick:
            if (col, row) in self.obstacles:
                obs = self.obstacles[(col, row)]
                drops, success = obs.hit(tool_id)
                if success:
                    player.consume_stamina(player.get_tool_stamina_cost(tool_id))
                    if drops:
                        for d in drops:
                            inventory.add_item(d, d.get("qty", 1))
                        del self.obstacles[(col, row)]
                        return f"Thu hoạch {drops[0]['name']}!", "clink"
                    return None, "clink"
            elif current_terrain in ["dirt_tilled", "dirt_watered"] and (col, row) not in self.crops:
                self.terrain[row][col] = "grass"
                player.consume_stamina(1.0)
                return "Đã lấp đất hoàn thổ.", "dig"

        # 5. SCYTHE (Bone Scythe)
        is_scythe = tool_id in [TOOL_SCYTHE, "bone_scythe"]
        if is_scythe:
            if (col, row) in self.obstacles:
                obs = self.obstacles[(col, row)]
                drops, success = obs.hit(tool_id)
                if success:
                    player.consume_stamina(player.get_tool_stamina_cost(tool_id))
                    if drops:
                        for d in drops:
                            inventory.add_item(d, d.get("qty", 1))
                        del self.obstacles[(col, row)]
                        return f"Thu hoạch {drops[0]['name']}!", "swish"
                    return None, "swish"
            if (col, row) in self.crops and self.crops[(col, row)].is_dead:
                del self.crops[(col, row)]
                return "Đã dọn sạch cây khô héo.", "swish"

        return None, None

    def plant_seed(self, crop_id, col, row, inventory):
        """Plants a seed from active inventory slot into tilled/watered soil."""
        if self.current_zone != ZONE_FARM:
            return False, "Chỉ có thể gieo hạt trong khu vực Nông Trại!"

        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return False, "Ngoài phạm vi nông trại!"

        if self.terrain[row][col] not in ["dirt_tilled", "dirt_watered"]:
            return False, "Cần dùng Cuốc xới đất trước khi gieo hạt!"

        if (col, row) in self.crops:
            return False, "Ô đất này đã có cây trồng!"

        if (col, row) in self.obstacles:
            return False, "Ô đất bị vướng chướng ngại vật!"

        is_watered = (self.terrain[row][col] == "dirt_watered")
        crop = Crop(crop_id, col, row, days_grown=0, watered_today=is_watered)
        self.crops[(col, row)] = crop
        inventory.remove_active_item(1)
        return True, "Đã gieo hạt giống xuống luống đất!"

    def harvest_crop(self, col, row, inventory):
        """Attempts to harvest crop at (col, row)."""
        if self.current_zone != ZONE_FARM:
            return False, None

        if (col, row) not in self.crops:
            return False, None

        crop = self.crops[(col, row)]
        if not crop.is_mature:
            return False, f"Cây đang lớn ({crop.days_grown}/{crop.data['grow_days']} ngày)!"

        produce, keep_plant = crop.harvest()
        if produce:
            if inventory.add_item(produce, 1):
                if not keep_plant:
                    del self.crops[(col, row)]
                return True, f"Thu hoạch {produce['name']} (+{produce['price']}G)!"
            else:
                return False, "Túi đồ đã đầy!"

        return False, None

    def to_dict(self):
        return {
            "current_zone": self.current_zone,
            "farm_terrain": self.farm_terrain,
            "farm_obstacles": [obs.to_dict() for obs in self.farm_obstacles.values()],
            "farm_crops": [c.to_dict() for c in self.farm_crops.values()],
            "npc_moods": {nid: {"patience": npc.patience, "friendship": npc.friendship} for nid, npc in self.npcs.items()}
        }

    def from_dict(self, data):
        self.current_zone = data.get("current_zone", ZONE_FARM)
        self.farm_terrain = data.get("farm_terrain", self.farm_terrain)
        self.farm_obstacles = {}
        for o_data in data.get("farm_obstacles", []):
            obs = Obstacle.from_dict(o_data)
            self.farm_obstacles[(obs.col, obs.row)] = obs

        self.farm_crops = {}
        for c_data in data.get("farm_crops", []):
            crop = Crop.from_dict(c_data)
            self.farm_crops[(crop.col, crop.row)] = crop

        npc_moods = data.get("npc_moods", {})
        for nid, m in npc_moods.items():
            if nid in self.npcs:
                self.npcs[nid].patience = m.get("patience", 100)
                self.npcs[nid].friendship = m.get("friendship", 10)

        # Set active zone
        self.switch_zone(self.current_zone)
