"""Procedural Stone Age World Generator — Rich Hydrology (Lakes & Tributaries), Biome Stitching & 6-Tier Terraces.

Upgrades the 200x200 Stone Age RTS map generator with:
1. Rich Multi-Basin Hydrology Network:
   - Main Primal River + Braided Southern Delta
   - 4 Major Organic Lakes (Northern Glacial Lake, Central Crescent Oasis Lake near Spawn,
     Great Eastern Primeval Lagoon, and Western Highland Canyon Tarn)
   - 4 Winding Tributary Rivers & Feeder Streams connecting all lakes and highlands
   - Natural Oxbow Ponds & Swamp Watering Holes in high-moisture lowland depressions
   - Strategic Shallow Stepping-Stone Fords (Tier 1 walkable crossings) across all rivers
2. Domain-Warped Tectonic Macro-Geography & Cellular Automata Biome Smoothing
3. 5 Ecotone Transition Belts (Pebble Shoreline, Woodland Savanna, Rocky Foothills,
   Taiga Frost Edge, Wetland Marsh Fringe)
4. Discrete 6-Tier Terraced Elevation System (Levels 0..5) with 2.5D Cliff Walls & Ramps
5. Clustered Blue-Noise Flora, Reed-Lined Shores, Fish Shoals & Wildlife Distribution
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import os
import random
from typing import Any, Dict, List, Optional, Set, Tuple

from PIL import Image, ImageDraw


# Biome constants
BIOME_TUNDRA = "Tundra"
BIOME_PRIMEVAL_FOREST = "Primeval Forest"
BIOME_STEPPE_GRASSLAND = "Steppe Grassland"
BIOME_MEGALITHIC_HIGHLANDS = "Megalithic Highlands"
BIOME_ANCIENT_SWAMP = "Ancient Swamp / Mangrove"
BIOME_COASTAL_WATERS = "Coastal Waters / River Delta"

# Ecotone transition belt types
ECOTONE_NONE = "core_biome"
ECOTONE_PEBBLE_SHORELINE = "pebble_shoreline"
ECOTONE_ROCKY_FOOTHILLS = "rocky_foothills_talus"
ECOTONE_TAIGA_FROST_EDGE = "taiga_frost_edge"
ECOTONE_WOODLAND_SAVANNA = "woodland_savanna_border"
ECOTONE_WETLAND_MARSH = "wetland_marsh_fringe"

# Fog-of-War visibility states
FOW_UNEXPLORED_SHROUD = 0
FOW_EXPLORED_MEMORY = 1
FOW_VISIBLE_LOS = 2

GROWTH_STAGES = ("unripe_sprout", "ripe_harvestable", "depleted_foraged")
GROWTH_STAGE_WEIGHTS = (0.22, 0.68, 0.10)

PREDATOR_SPAWNERS = {
    "sabertooth_tiger",
    "cave_bear",
    "dire_wolf",
    "marsh_crocodilian",
}

BASE_BIOME_MOVE_COST: Dict[str, float] = {
    BIOME_STEPPE_GRASSLAND: 1.0,
    BIOME_TUNDRA: 1.40,
    BIOME_PRIMEVAL_FOREST: 1.95,
    BIOME_MEGALITHIC_HIGHLANDS: 2.40,
    BIOME_ANCIENT_SWAMP: 2.85,
    BIOME_COASTAL_WATERS: 4.20,
}

BIOME_PALETTE_RGB: Dict[str, Tuple[int, int, int]] = {
    BIOME_TUNDRA: (224, 236, 244),
    BIOME_PRIMEVAL_FOREST: (48, 98, 46),
    BIOME_STEPPE_GRASSLAND: (148, 172, 76),
    BIOME_MEGALITHIC_HIGHLANDS: (128, 114, 98),
    BIOME_ANCIENT_SWAMP: (64, 92, 68),
    BIOME_COASTAL_WATERS: (38, 108, 145),
}

ECOTONE_PALETTE_RGB: Dict[str, Tuple[int, int, int]] = {
    ECOTONE_PEBBLE_SHORELINE: (198, 182, 140),
    ECOTONE_ROCKY_FOOTHILLS: (142, 134, 102),
    ECOTONE_TAIGA_FROST_EDGE: (176, 196, 168),
    ECOTONE_WOODLAND_SAVANNA: (102, 138, 62),
    ECOTONE_WETLAND_MARSH: (96, 126, 78),
}

TERRACE_NAMES: Dict[int, str] = {
    0: "Tier 0: Deep Abyssal Water & Lake Center",
    1: "Tier 1: Shallow Shoal / River Ford / Lake Rim",
    2: "Tier 2: Lowland River Basin & Swamp",
    3: "Tier 3: Main Steppe & Forest Terrace",
    4: "Tier 4: Highland Mesa & Tundra Plateau",
    5: "Tier 5: Megalithic Summit & Glacial Crag",
}


@dataclass
class WorldTile:
    """Represents a single grid tile with hydrology, biome stitching, elevation terrace, and flora data."""

    tile_x: int
    tile_y: int
    biome_type: str
    ecotone_type: str
    water_body_type: Optional[str]  # None, 'main_river', 'tributary_stream', 'inland_lake', 'oxbow_pond', 'ocean_delta'
    elevation: float
    elevation_tier: int
    is_cliff_edge: bool
    is_natural_ramp: bool
    cliff_drop_south: int
    moisture: float
    temperature: float
    walkable: bool
    resource_node: Optional[str] = None
    flora_species: Optional[str] = None
    growth_stage: Optional[str] = None
    foraging_yield: int = 0
    regrowth_ticks: int = 0
    wildlife_spawner: Optional[str] = None
    special_feature: Optional[str] = None
    warmth_radius_active: bool = False
    autotile_mask_4bit: int = 0
    fow_state: int = FOW_UNEXPLORED_SHROUD
    trail_type: Optional[str] = None
    waypoint_marker: Optional[str] = None
    movement_cost: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultiOctaveNoise2D:
    """Self-contained 2D smooth Perlin-style gradient noise with Domain Warping."""

    def __init__(self, seed: int = 42) -> None:
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
        x2 = self._lerp(
            self._grad(ab, xf, yf - 1.0), self._grad(bb, xf - 1.0, yf - 1.0), u
        )
        return self._lerp(x1, x2, v)

    def fbm(
        self,
        x: float,
        y: float,
        octaves: int = 4,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
        base_scale: float = 0.022,
    ) -> float:
        total = 0.0
        amplitude = 1.0
        frequency = base_scale
        max_value = 0.0

        for _ in range(octaves):
            total += self.noise2d(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity

        normalized = 0.5 + (total / max_value) * 0.85
        return max(0.0, min(1.0, normalized))

    def warped_fbm(
        self,
        x: float,
        y: float,
        warp_strength: float = 18.0,
        base_scale: float = 0.018,
    ) -> float:
        qx = self.fbm(x + 13.5, y + 29.1, octaves=3, base_scale=base_scale) - 0.5
        qy = self.fbm(x + 71.2, y + 47.8, octaves=3, base_scale=base_scale) - 0.5
        wx = x + qx * warp_strength
        wy = y + qy * warp_strength
        return self.fbm(wx, wy, octaves=5, persistence=0.52, base_scale=base_scale)


class ProceduralStoneAgeWorldGenerator:
    """Generates a 200x200 Stone Age world with rich lakes, tributaries, 6 elevation tiers, and clustered flora."""

    def __init__(
        self,
        width: int = 200,
        height: int = 200,
        seed: int = 2026,
        safe_buffer_radius: int = 25,
        campfire_warmth_radius: int = 6,
    ) -> None:
        self.width = width
        self.height = height
        self.seed = seed
        self.safe_buffer_radius = safe_buffer_radius
        self.campfire_warmth_radius = campfire_warmth_radius

        self.rng = random.Random(seed)
        self.elev_noise = MultiOctaveNoise2D(seed=seed)
        self.moist_noise = MultiOctaveNoise2D(seed=seed + 1337)
        self.temp_noise = MultiOctaveNoise2D(seed=seed + 7919)
        self.grove_noise = MultiOctaveNoise2D(seed=seed + 4099)

        self.center_x = width // 2
        self.center_y = height // 2
        self.grid: List[List[WorldTile]] = []
        self.spawn_metadata: Dict[str, Any] = {}
        self.hydrology_metadata: Dict[str, Any] = {}

    def generate_world(self) -> List[List[Dict[str, Any]]]:
        """Executes the 7-stage tectonic, multi-lake hydrology, biome-stitching, and clustering pipeline."""
        self._build_initial_macro_continent()
        self._carve_hydrology_network_lakes_and_tributaries()
        self._smooth_biome_regions(iterations=2)
        self._compute_terraced_elevation_and_ramps()
        self._stitch_ecotone_transitions_and_bitmasks()
        self._populate_clustered_resources_and_wildlife()
        self._apply_starting_basin_guarantees()
        return [[tile.to_dict() for tile in row] for row in self.grid]

    def _build_initial_macro_continent(self) -> None:
        self.grid = []
        cx, cy = self.center_x, self.center_y

        for y in range(self.height):
            row: List[WorldTile] = []
            lat = y / max(1, self.height - 1)

            for x in range(self.width):
                lon = x / max(1, self.width - 1)

                w_elev = self.elev_noise.warped_fbm(
                    x, y, warp_strength=22.0, base_scale=0.017
                )
                w_moist = self.moist_noise.warped_fbm(
                    x, y, warp_strength=18.0, base_scale=0.019
                )
                w_temp = self.temp_noise.fbm(x, y, octaves=3, base_scale=0.016)

                dist_center = math.hypot((x - cx) / self.width, (y - cy) / self.height)
                center_basin_flatten = math.exp(-((dist_center / 0.24) ** 2))

                west_orogeny = max(0.0, (0.36 - lon) / 0.36) ** 1.35 * 0.34
                north_glacier = max(0.0, (0.32 - lat) / 0.32) ** 1.30 * 0.28
                east_basin_dip = max(0.0, (lon - 0.58) / 0.42) * 0.10
                east_humidity = max(0.0, (lon - 0.48) / 0.52) ** 1.15 * 0.38

                coast_wave = math.sin(lon * math.pi * 3.0) * 0.04
                south_ocean_shelf = (
                    max(0.0, (lat - (0.78 + coast_wave)) / 0.22) ** 1.25 * 0.68
                )

                elev = (
                    w_elev * 0.72
                    + 0.14
                    + west_orogeny
                    + north_glacier
                    - east_basin_dip
                    - south_ocean_shelf
                )
                elev = elev * (1.0 - 0.55 * center_basin_flatten) + 0.48 * (
                    0.55 * center_basin_flatten
                )
                elev = max(0.0, min(1.0, elev))

                moist = (
                    w_moist * 0.68
                    + 0.14
                    + east_humidity
                    - west_orogeny * 0.70
                    + south_ocean_shelf * 0.35
                )
                moist = max(0.0, min(1.0, moist))

                temp = max(
                    0.0,
                    min(
                        1.0,
                        0.76 * lat
                        + 0.24 * w_temp
                        - north_glacier * 0.45
                        - max(0.0, elev - 0.65) * 0.35,
                    ),
                )

                biome = self._classify_biome(elev, moist, temp, lon, lat)
                tier = self._elevation_to_tier(elev)
                wb_type = "ocean_delta" if biome == BIOME_COASTAL_WATERS else None

                row.append(
                    WorldTile(
                        tile_x=x,
                        tile_y=y,
                        biome_type=biome,
                        ecotone_type=ECOTONE_NONE,
                        water_body_type=wb_type,
                        elevation=round(elev, 4),
                        elevation_tier=tier,
                        is_cliff_edge=False,
                        is_natural_ramp=False,
                        cliff_drop_south=0,
                        moisture=round(moist, 4),
                        temperature=round(temp, 4),
                        walkable=(tier >= 1),
                    )
                )
            self.grid.append(row)

    @staticmethod
    def _classify_biome(
        elevation: float,
        moisture: float,
        temperature: float,
        lon: float,
        lat: float,
    ) -> str:
        if elevation < 0.26:
            return BIOME_COASTAL_WATERS
        if temperature < 0.31 and elevation >= 0.42:
            return BIOME_TUNDRA
        if elevation >= 0.63 and (moisture < 0.52 or lon < 0.42):
            return BIOME_MEGALITHIC_HIGHLANDS
        if elevation >= 0.72:
            return BIOME_TUNDRA if lat < 0.45 else BIOME_MEGALITHIC_HIGHLANDS
        if elevation < 0.44 and moisture >= 0.58 and lat > 0.25:
            return BIOME_ANCIENT_SWAMP
        if moisture >= 0.52 and lon > 0.42:
            return BIOME_PRIMEVAL_FOREST
        if moisture >= 0.60:
            return BIOME_PRIMEVAL_FOREST
        return BIOME_STEPPE_GRASSLAND

    @staticmethod
    def _elevation_to_tier(elevation: float) -> int:
        if elevation < 0.20:
            return 0
        if elevation < 0.26:
            return 1
        if elevation < 0.42:
            return 2
        if elevation < 0.62:
            return 3
        if elevation < 0.77:
            return 4
        return 5

    def _carve_organic_lake(
        self,
        center_x: int,
        center_y: int,
        radius_x: float,
        radius_y: float,
        lake_name: str,
        valley_rim_width: float = 5.0,
    ) -> int:
        """Carves an organically warped multi-tier lake with a deep center (T0), shallow rim (T1),
        and depressed fertile valley shoreline (T2)."""
        water_tiles = 0
        min_y = max(2, int(center_y - radius_y - valley_rim_width - 4))
        max_y = min(self.height - 3, int(center_y + radius_y + valley_rim_width + 4))
        min_x = max(2, int(center_x - radius_x - valley_rim_width - 4))
        max_x = min(self.width - 3, int(center_x + radius_x + valley_rim_width + 4))

        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                # Normalized elliptical distance warped by smooth 2D noise
                dx = (x - center_x) / max(1.0, radius_x)
                dy = (y - center_y) / max(1.0, radius_y)
                base_dist = math.hypot(dx, dy)
                warp = (
                    self.grove_noise.fbm(x * 1.4, y * 1.4, octaves=3, base_scale=0.055)
                    - 0.5
                ) * 0.42
                eff_dist = base_dist + warp

                tile = self.grid[y][x]
                if eff_dist <= 0.72:
                    # Deep lake core (Tier 0)
                    tile.biome_type = BIOME_COASTAL_WATERS
                    tile.water_body_type = "inland_lake"
                    tile.elevation = round(0.11 + eff_dist * 0.09, 4)
                    tile.elevation_tier = 0
                    tile.moisture = 1.0
                    tile.walkable = False
                    water_tiles += 1
                elif eff_dist <= 1.0:
                    # Shallow wading lake rim (Tier 1)
                    tile.biome_type = BIOME_COASTAL_WATERS
                    tile.water_body_type = "inland_lake"
                    tile.elevation = 0.23
                    tile.elevation_tier = 1
                    tile.moisture = 1.0
                    tile.walkable = True
                    water_tiles += 1
                elif eff_dist <= 1.0 + (valley_rim_width / max(radius_x, radius_y)):
                    # Depress surrounding lake shore into a gentle Tier 2 / Tier 3 basin
                    if tile.biome_type != BIOME_COASTAL_WATERS:
                        rim_ratio = (eff_dist - 1.0) / (
                            valley_rim_width / max(radius_x, radius_y)
                        )
                        target_elev = 0.36 + rim_ratio * 0.14
                        tile.elevation = round(min(tile.elevation, target_elev), 4)
                        tile.moisture = round(min(1.0, tile.moisture + 0.28), 4)

        return water_tiles

    def _carve_winding_stream(
        self,
        start_pt: Tuple[int, int],
        end_pt: Tuple[int, int],
        half_width: float = 1.2,
        meander_amp: float = 5.5,
        stream_type: str = "tributary_stream",
        phase_offset: float = 0.0,
    ) -> int:
        """Carves a winding river or tributary stream between two points with periodic shallow fords."""
        sx, sy = start_pt
        ex, ey = end_pt
        total_len = max(1, int(math.hypot(ex - sx, ey - sy) * 1.6))
        carved = 0

        # Unit perpendicular vector for lateral meandering
        length_vec = max(1.0, math.hypot(ex - sx, ey - sy))
        nx_perp = -(ey - sy) / length_vec
        ny_perp = (ex - sx) / length_vec

        for step in range(total_len + 1):
            t = step / total_len
            bx = sx + (ex - sx) * t
            by = sy + (ey - sy) * t

            # Smooth sinusoidal + noise meander that tapers to 0 at exact endpoints
            endpoint_envelope = math.sin(t * math.pi)
            wave = (
                math.sin(t * math.pi * 3.5 + phase_offset) * meander_amp
                + math.cos(t * math.pi * 7.0 - phase_offset) * (meander_amp * 0.35)
            ) * endpoint_envelope

            cx = bx + nx_perp * wave
            cy = by + ny_perp * wave

            # Create shallow walkable stepping-stone fords every ~26 steps
            is_ford = (step % 28 in (12, 13, 14)) or (
                math.hypot(cx - self.center_x, cy - self.center_y) <= 13.0
                and abs(cy - self.center_y) <= 3.5
            )

            ir = int(math.ceil(half_width + 3))
            icx, icy = int(round(cx)), int(round(cy))

            for dy in range(-ir, ir + 1):
                for dx in range(-ir, ir + 1):
                    px, py = icx + dx, icy + dy
                    if not (1 <= px < self.width - 1 and 1 <= py < self.height - 1):
                        continue
                    dist = math.hypot(px - cx, py - cy)
                    tile = self.grid[py][px]

                    if dist <= half_width:
                        tile.biome_type = BIOME_COASTAL_WATERS
                        if tile.water_body_type != "inland_lake":
                            tile.water_body_type = stream_type
                        tile.moisture = 1.0
                        if is_ford or dist >= half_width - 0.55:
                            tile.elevation = 0.23
                            tile.elevation_tier = 1
                            tile.walkable = True
                        else:
                            tile.elevation = 0.15
                            tile.elevation_tier = 0
                            tile.walkable = False
                        carved += 1
                    elif dist <= half_width + 3.0 and (
                        tile.biome_type != BIOME_COASTAL_WATERS
                    ):
                        # Carve gentle riverbank valley depression
                        bank_t = (dist - half_width) / 3.0
                        max_bank_elev = 0.36 + bank_t * 0.14
                        tile.elevation = round(
                            min(tile.elevation, max_bank_elev), 4
                        )
                        tile.moisture = round(min(1.0, tile.moisture + 0.22), 4)

        return carved

    def _carve_hydrology_network_lakes_and_tributaries(self) -> None:
        """Builds a complete prehistoric hydrology network:
        - 5 Major Lakes (Northern Glacial Lake, Central Oasis Lake, Great Eastern Lagoon,
          Western Canyon Tarn, and Northwestern Alpine Tarn)
        - Main North-South Primal River + 3-Branch Southern River Delta
        - 5 Winding Tributary Streams connecting lakes, highlands, and main river
        - 8 Natural Oxbow Ponds / Watering Holes across Steppe, Forest, and Swamp
        """
        lakes_spec = [
            # (cx, cy, rx, ry, name)
            (64, 34, 13.5, 10.5, "Northern Glacial Crater Lake"),
            (119, 92, 10.5, 9.0, "Central Crescent Oasis Lake"),
            (158, 118, 15.0, 12.5, "Great Eastern Primeval Lagoon"),
            (48, 126, 10.5, 8.5, "Western Highland Canyon Tarn"),
            (148, 44, 10.0, 8.0, "Northeastern Boreal Lake"),
        ]
        lake_summary = []
        for lx, ly, rx, ry, lname in lakes_spec:
            cnt = self._carve_organic_lake(lx, ly, rx, ry, lname)
            lake_summary.append(
                {"name": lname, "center": [lx, ly], "water_tiles": cnt}
            )

        # Carve Main Primal River from North Glacier (104, 2) through Central Lake edge (108, 96) to Deltahead (106, 150)
        self._carve_winding_stream(
            start_pt=(104, 2),
            end_pt=(108, 96),
            half_width=2.1,
            meander_amp=6.0,
            stream_type="main_river",
            phase_offset=0.4,
        )
        self._carve_winding_stream(
            start_pt=(108, 96),
            end_pt=(106, 150),
            half_width=2.3,
            meander_amp=5.5,
            stream_type="main_river",
            phase_offset=1.8,
        )

        # Carve 3 Southern Delta Distributary Branches into the Southern Ocean
        delta_branches = [
            ((106, 150), (74, 192), 1.6, 3.5, 0.5),
            ((106, 150), (108, 194), 2.1, 3.0, 1.2),
            ((106, 150), (142, 190), 1.6, 4.0, 2.4),
        ]
        for d_start, d_end, dw, damp, dphase in delta_branches:
            self._carve_winding_stream(
                start_pt=d_start,
                end_pt=d_end,
                half_width=dw,
                meander_amp=damp,
                stream_type="ocean_delta",
                phase_offset=dphase,
            )

        # Carve 5 Winding Tributary Streams connecting the 5 Lakes to the Main River & Coast
        tributaries_spec = [
            # 1) NW Glacial Tributary: Northern Glacial Lake (64, 34) -> Main River (105, 62)
            ((64, 34), (105, 62), 1.35, 4.5, 0.7, "NW Glacial Meltwater Tributary"),
            # 2) NE Boreal Tributary: NE Boreal Lake (148, 44) -> Central Crescent Lake (119, 92)
            ((148, 44), (119, 92), 1.30, 5.0, 1.5, "NE Primeval Forest Tributary"),
            # 3) Western Canyon Stream: Western Highland Tarn (48, 126) -> Main River (106, 138)
            ((48, 126), (106, 138), 1.35, 5.5, 2.1, "SW Canyon Flint Stream"),
            # 4) West-Central Steppe Creek: Western Foothills (52, 78) -> Main River (106, 86)
            ((52, 78), (106, 86), 1.15, 4.0, 0.9, "West Steppe Feeder Creek"),
            # 5) Eastern Lagoon Channel: Central Lake (122, 95) -> Great Eastern Lagoon (158, 118) -> Southern Sea (166, 184)
            ((122, 95), (158, 118), 1.40, 4.2, 1.1, "Eastern Lagoon Upper Channel"),
            ((158, 118), (166, 184), 1.55, 4.8, 2.6, "Eastern Swamp Estuary"),
        ]
        trib_summary = []
        for t_start, t_end, tw, tamp, tphase, tname in tributaries_spec:
            self._carve_winding_stream(
                start_pt=t_start,
                end_pt=t_end,
                half_width=tw,
                meander_amp=tamp,
                stream_type="tributary_stream",
                phase_offset=tphase,
            )
            trib_summary.append(
                {"name": tname, "from": list(t_start), "to": list(t_end)}
            )

        # Carve 7 smaller Natural Oxbow Ponds & Oasis Watering Holes across the biomes
        oxbow_ponds = [
            (82, 112, 4.5, 3.8, "Steppe Grazing Watering Hole"),
            (76, 62, 4.2, 3.5, "North Steppe Oxbow Pond"),
            (136, 72, 4.8, 4.0, "Primeval Forest Glade Pool"),
            (134, 146, 5.2, 4.2, "Southern Marsh Oxbow Pool"),
            (178, 84, 5.0, 4.2, "Deep Jungle Emerald Pool"),
            (34, 56, 4.2, 3.5, "Highland Ice Tarn"),
            (66, 158, 4.8, 3.8, "Southwest Coastal Lagoon"),
        ]
        for px, py, prx, pry, pname in oxbow_ponds:
            self._carve_organic_lake(
                px, py, prx, pry, pname, valley_rim_width=3.0
            )

        self.hydrology_metadata = {
            "major_lakes": lake_summary,
            "tributary_streams": trib_summary,
            "oxbow_watering_holes_count": len(oxbow_ponds),
        }

    def _smooth_biome_regions(self, iterations: int = 2) -> None:
        """Applies cellular automata majority filtering to remove isolated single-tile biome speckles."""
        for _ in range(iterations):
            new_biomes = [[t.biome_type for t in row] for row in self.grid]
            for y in range(1, self.height - 1):
                for x in range(1, self.width - 1):
                    curr = self.grid[y][x].biome_type
                    if curr == BIOME_COASTAL_WATERS:
                        continue

                    counts: Dict[str, int] = {}
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            nb = self.grid[y + dy][x + dx].biome_type
                            if nb != BIOME_COASTAL_WATERS:
                                counts[nb] = counts.get(nb, 0) + 1

                    if counts.get(curr, 0) <= 2 and counts:
                        best_biome = max(counts.items(), key=lambda kv: kv[1])[0]
                        new_biomes[y][x] = best_biome

            for y in range(1, self.height - 1):
                for x in range(1, self.width - 1):
                    self.grid[y][x].biome_type = new_biomes[y][x]

    def _compute_terraced_elevation_and_ramps(self) -> None:
        """Smooths elevation tiers, marks impassable cliff edges, and carves natural slope ramps."""
        for y in range(self.height):
            for x in range(self.width):
                t = self.grid[y][x]
                if t.biome_type != BIOME_COASTAL_WATERS:
                    t.elevation_tier = max(2, self._elevation_to_tier(t.elevation))

        for _ in range(2):
            next_tiers = [[t.elevation_tier for t in row] for row in self.grid]
            for y in range(1, self.height - 1):
                for x in range(1, self.width - 1):
                    if self.grid[y][x].biome_type == BIOME_COASTAL_WATERS:
                        continue
                    t_counts: Dict[int, int] = {}
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            nt = self.grid[y + dy][x + dx].elevation_tier
                            if nt >= 2:
                                t_counts[nt] = t_counts.get(nt, 0) + 1
                    cur_t = self.grid[y][x].elevation_tier
                    if t_counts.get(cur_t, 0) <= 3 and t_counts:
                        next_tiers[y][x] = max(
                            t_counts.items(), key=lambda kv: kv[1]
                        )[0]
            for y in range(1, self.height - 1):
                for x in range(1, self.width - 1):
                    self.grid[y][x].elevation_tier = next_tiers[y][x]

        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                t = self.grid[y][x]
                if t.biome_type == BIOME_COASTAL_WATERS:
                    continue

                my_tier = t.elevation_tier
                min_nb_tier = min(
                    self.grid[y - 1][x].elevation_tier,
                    self.grid[y + 1][x].elevation_tier,
                    self.grid[y][x - 1].elevation_tier,
                    self.grid[y][x + 1].elevation_tier,
                )
                south_tier = self.grid[y + 1][x].elevation_tier
                t.cliff_drop_south = (
                    max(0, my_tier - south_tier) if south_tier >= 2 else 0
                )

                if my_tier > min_nb_tier and min_nb_tier >= 2:
                    spatial_hash = (x * 3 + y * 5) % 22
                    if spatial_hash in (0, 1, 2) and (my_tier - min_nb_tier == 1):
                        t.is_natural_ramp = True
                        t.is_cliff_edge = False
                        t.walkable = True
                    else:
                        t.is_cliff_edge = True
                        t.walkable = False if my_tier >= 4 else True

    def _stitch_ecotone_transitions_and_bitmasks(self) -> None:
        """Assigns seamless Ecotone Transition Belts where distinct biomes and lakes/rivers meet."""
        for y in range(self.height):
            for x in range(self.width):
                tile = self.grid[y][x]
                b = tile.biome_type

                mask4 = 0
                if y > 0 and self.grid[y - 1][x].biome_type == b:
                    mask4 |= 1
                if x < self.width - 1 and self.grid[y][x + 1].biome_type == b:
                    mask4 |= 2
                if y < self.height - 1 and self.grid[y + 1][x].biome_type == b:
                    mask4 |= 4
                if x > 0 and self.grid[y][x - 1].biome_type == b:
                    mask4 |= 8
                tile.autotile_mask_4bit = mask4

                nb_biomes: Set[str] = set()
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < self.height and 0 <= nx < self.width:
                            nb_biomes.add(self.grid[ny][nx].biome_type)

                ecotone = ECOTONE_NONE
                if b != BIOME_COASTAL_WATERS and BIOME_COASTAL_WATERS in nb_biomes:
                    ecotone = (
                        ECOTONE_WETLAND_MARSH
                        if b == BIOME_ANCIENT_SWAMP
                        else ECOTONE_PEBBLE_SHORELINE
                    )
                elif b == BIOME_STEPPE_GRASSLAND:
                    if BIOME_MEGALITHIC_HIGHLANDS in nb_biomes or tile.is_cliff_edge:
                        ecotone = ECOTONE_ROCKY_FOOTHILLS
                    elif BIOME_TUNDRA in nb_biomes:
                        ecotone = ECOTONE_TAIGA_FROST_EDGE
                    elif BIOME_PRIMEVAL_FOREST in nb_biomes:
                        ecotone = ECOTONE_WOODLAND_SAVANNA
                    elif BIOME_ANCIENT_SWAMP in nb_biomes:
                        ecotone = ECOTONE_WETLAND_MARSH
                elif b == BIOME_PRIMEVAL_FOREST and BIOME_STEPPE_GRASSLAND in nb_biomes:
                    ecotone = ECOTONE_WOODLAND_SAVANNA
                elif b == BIOME_TUNDRA and (
                    BIOME_STEPPE_GRASSLAND in nb_biomes
                    or BIOME_PRIMEVAL_FOREST in nb_biomes
                ):
                    ecotone = ECOTONE_TAIGA_FROST_EDGE
                elif b == BIOME_MEGALITHIC_HIGHLANDS and BIOME_STEPPE_GRASSLAND in nb_biomes:
                    ecotone = ECOTONE_ROCKY_FOOTHILLS

                tile.ecotone_type = ecotone

    def _populate_clustered_resources_and_wildlife(self) -> None:
        placed_spawners: List[Tuple[int, int]] = []
        min_spawner_dist = 11.0

        for y in range(self.height):
            for x in range(self.width):
                tile = self.grid[y][x]
                b = tile.biome_type
                eco = tile.ecotone_type
                dist_center = math.hypot(x - self.center_x, y - self.center_y)
                in_safe_zone = dist_center <= self.safe_buffer_radius

                if b == BIOME_COASTAL_WATERS:
                    tile.resource_node = "water"
                    if tile.elevation_tier == 1 and self.rng.random() < 0.14:
                        self._set_tile_flora(
                            tile, ("delta_cattail_reeds", "fiber_plant", 20, 65)
                        )
                    elif self._can_place_spawner(x, y, placed_spawners, 8.5) and (
                        self.rng.random() < 0.22
                    ):
                        tile.wildlife_spawner = "fish_shoal"
                        placed_spawners.append((x, y))
                    continue

                if not tile.walkable or tile.is_natural_ramp:
                    continue

                grove_val = self.grove_noise.fbm(
                    x, y, octaves=3, persistence=0.55, base_scale=0.065
                )
                roll = self.rng.random()

                near_cliff = tile.cliff_drop_south > 0 or eco == ECOTONE_ROCKY_FOOTHILLS
                if near_cliff or b == BIOME_MEGALITHIC_HIGHLANDS:
                    if grove_val > 0.56 and roll < 0.24:
                        tile.resource_node = "flint"
                        tile.movement_cost = round(
                            BASE_BIOME_MOVE_COST[b] + 0.65, 2
                        )
                        continue
                    elif grove_val < 0.36 and roll < 0.14:
                        tile.resource_node = "bone_deposit"
                        continue

                if b == BIOME_PRIMEVAL_FOREST:
                    if grove_val > 0.44 and roll < 0.58:
                        species = self.rng.choice(
                            [
                                ("giant_tree_fern", "tree", 35, 180),
                                ("araucaria_monkey_pine", "tree", 45, 220),
                                ("ancient_gnarled_oak", "tree", 50, 240),
                            ]
                        )
                        self._set_tile_flora(tile, species)
                        tile.movement_cost = round(
                            BASE_BIOME_MOVE_COST[b] + 1.20, 2
                        )
                        continue
                elif eco == ECOTONE_WOODLAND_SAVANNA:
                    if grove_val > 0.52 and roll < 0.30:
                        self._set_tile_flora(
                            tile, ("steppe_ginkgo_tree", "tree", 30, 190)
                        )
                        continue
                elif b == BIOME_TUNDRA or eco == ECOTONE_TAIGA_FROST_EDGE:
                    if grove_val > 0.58 and roll < 0.22:
                        self._set_tile_flora(
                            tile, ("krummholz_dwarf_pine", "tree", 20, 240)
                        )
                        continue
                elif b == BIOME_ANCIENT_SWAMP:
                    if grove_val > 0.50 and roll < 0.32:
                        self._set_tile_flora(
                            tile, ("aerial_root_mangrove", "tree", 35, 175)
                        )
                        continue

                if eco in (ECOTONE_PEBBLE_SHORELINE, ECOTONE_WETLAND_MARSH):
                    if roll < 0.26:
                        self._set_tile_flora(
                            tile, ("riverbank_cattail_reeds", "fiber_plant", 24, 70)
                        )
                        continue
                elif eco == ECOTONE_WOODLAND_SAVANNA:
                    if roll < 0.16:
                        self._set_tile_flora(
                            tile, ("crimson_bramble_berries", "berries", 18, 85)
                        )
                        continue
                elif b == BIOME_STEPPE_GRASSLAND and grove_val < 0.48:
                    if roll < 0.055:
                        self._set_tile_flora(
                            tile, ("einkorn_wild_grain", "wild_grain", 22, 100)
                        )
                        continue
                    elif roll < 0.095:
                        self._set_tile_flora(
                            tile, ("burdock_starchy_roots", "roots_tubers", 18, 95)
                        )
                        continue
                    elif roll < 0.125:
                        self._set_tile_flora(
                            tile, ("wild_flax_fiber_plant", "fiber_plant", 15, 80)
                        )
                        continue
                elif b == BIOME_PRIMEVAL_FOREST:
                    if roll < 0.08:
                        self._set_tile_flora(
                            tile, ("king_spotted_mushrooms", "mushrooms", 14, 75)
                        )
                        continue
                    elif roll < 0.13:
                        self._set_tile_flora(
                            tile, ("healing_red_herb", "medicinal_herb", 10, 120)
                        )
                        continue
                    elif roll < 0.17:
                        self._set_tile_flora(
                            tile, ("wild_taro_tubers", "roots_tubers", 16, 110)
                        )
                        continue
                elif b == BIOME_TUNDRA:
                    if roll < 0.06:
                        self._set_tile_flora(
                            tile, ("golden_arctic_cloudberries", "berries", 14, 115)
                        )
                        continue
                    elif roll < 0.09:
                        self._set_tile_flora(
                            tile, ("arctic_reindeer_moss", "medicinal_herb", 10, 100)
                        )
                        continue

                if self._can_place_spawner(x, y, placed_spawners, min_spawner_dist):
                    mob_roll = self.rng.random()
                    spawner: Optional[str] = None
                    if b == BIOME_STEPPE_GRASSLAND and mob_roll < 0.18:
                        spawner = "ancient_bison"
                    elif b == BIOME_TUNDRA:
                        if mob_roll < 0.16:
                            spawner = "woolly_mammoth"
                        elif not in_safe_zone and mob_roll < 0.25:
                            spawner = "dire_wolf"
                    elif b == BIOME_PRIMEVAL_FOREST:
                        if mob_roll < 0.16:
                            spawner = "wild_boar"
                        elif not in_safe_zone and mob_roll < 0.24:
                            spawner = "sabertooth_tiger"
                    elif b == BIOME_MEGALITHIC_HIGHLANDS and not in_safe_zone:
                        if mob_roll < 0.20:
                            spawner = "sabertooth_tiger"
                        elif mob_roll < 0.30:
                            spawner = "cave_bear"
                    elif b == BIOME_ANCIENT_SWAMP and not in_safe_zone:
                        if mob_roll < 0.18:
                            spawner = "marsh_crocodilian"

                    if spawner:
                        tile.wildlife_spawner = spawner
                        placed_spawners.append((x, y))

    @staticmethod
    def _can_place_spawner(
        x: int,
        y: int,
        existing: List[Tuple[int, int]],
        min_dist: float,
    ) -> bool:
        for ex, ey in existing:
            if math.hypot(x - ex, y - ey) < min_dist:
                return False
        return True

    def _set_tile_flora(
        self,
        tile: WorldTile,
        entry: Tuple[str, str, int, int],
        force_ripe: bool = False,
    ) -> None:
        species_id, category, base_yield, regrowth = entry
        stage = (
            "ripe_harvestable"
            if force_ripe
            else self.rng.choices(GROWTH_STAGES, weights=GROWTH_STAGE_WEIGHTS, k=1)[0]
        )
        tile.resource_node = category
        tile.flora_species = species_id
        tile.growth_stage = stage
        tile.foraging_yield = (
            base_yield
            if stage == "ripe_harvestable"
            else (max(1, int(base_yield * 0.35)) if stage == "unripe_sprout" else 0)
        )
        tile.regrowth_ticks = regrowth

    def _apply_starting_basin_guarantees(self) -> None:
        cx, cy = self.center_x, self.center_y
        basin_radius = 9

        for y in range(
            max(0, cy - self.safe_buffer_radius - 1),
            min(self.height, cy + self.safe_buffer_radius + 2),
        ):
            for x in range(
                max(0, cx - self.safe_buffer_radius - 1),
                min(self.width, cx + self.safe_buffer_radius + 2),
            ):
                dist = math.hypot(x - cx, y - cy)
                tile = self.grid[y][x]
                if dist <= self.safe_buffer_radius and (
                    tile.wildlife_spawner in PREDATOR_SPAWNERS
                ):
                    tile.wildlife_spawner = None

                if dist <= basin_radius and tile.biome_type != BIOME_COASTAL_WATERS:
                    tile.biome_type = BIOME_STEPPE_GRASSLAND
                    tile.ecotone_type = ECOTONE_NONE
                    tile.elevation = 0.48
                    tile.elevation_tier = 3
                    tile.is_cliff_edge = False
                    tile.cliff_drop_south = 0
                    tile.walkable = True
                    tile.movement_cost = 1.0

        shelter_pos = (cx, cy - 2)
        shelter_tile = self.grid[shelter_pos[1]][shelter_pos[0]]
        shelter_tile.special_feature = "Ancestral Rock Shelter (Hang Đá Cội Nguồn)"
        shelter_tile.resource_node = None
        shelter_tile.flora_species = None
        shelter_tile.walkable = True

        campfire_pos = (cx, cy)
        campfire_tile = self.grid[campfire_pos[1]][campfire_pos[0]]
        campfire_tile.special_feature = "Active Campfire Hearth"
        campfire_tile.resource_node = None
        campfire_tile.flora_species = None
        campfire_tile.walkable = True

        warm_tiles_count = 0
        for y in range(
            max(0, cy - self.campfire_warmth_radius),
            min(self.height, cy + self.campfire_warmth_radius + 1),
        ):
            for x in range(
                max(0, cx - self.campfire_warmth_radius),
                min(self.width, cx + self.campfire_warmth_radius + 1),
            ):
                if math.hypot(x - cx, y - cy) <= self.campfire_warmth_radius:
                    self.grid[y][x].warmth_radius_active = True
                    warm_tiles_count += 1

        berry_offsets = [(-4, -1), (-3, 2), (-5, 1), (2, -3)]
        grain_offsets = [(-2, 3), (-1, 4), (1, 3)]
        tuber_offsets = [(-5, -2), (-3, -3)]
        fiber_offsets = [(3, 1), (3, -1)]
        herb_offsets = [(-2, -1), (1, -2)]
        mushroom_offsets = [(-6, 0), (-5, 4)]
        flint_offsets = [(-4, -4), (3, -4), (-2, -5)]
        tree_offsets = [(-6, -2), (-6, 3), (2, 5)]

        for ox, oy in berry_offsets:
            self._set_tile_flora(
                self.grid[cy + oy][cx + ox],
                ("crimson_bramble_berries", "berries", 18, 85),
                force_ripe=True,
            )
        for ox, oy in grain_offsets:
            self._set_tile_flora(
                self.grid[cy + oy][cx + ox],
                ("einkorn_wild_grain", "wild_grain", 22, 100),
                force_ripe=True,
            )
        for ox, oy in tuber_offsets:
            self._set_tile_flora(
                self.grid[cy + oy][cx + ox],
                ("burdock_starchy_roots", "roots_tubers", 18, 95),
                force_ripe=True,
            )
        for ox, oy in fiber_offsets:
            self._set_tile_flora(
                self.grid[cy + oy][cx + ox],
                ("riverbank_cattail_reeds", "fiber_plant", 24, 70),
                force_ripe=True,
            )
        for ox, oy in herb_offsets:
            self._set_tile_flora(
                self.grid[cy + oy][cx + ox],
                ("healing_red_herb", "medicinal_herb", 10, 120),
                force_ripe=True,
            )
        for ox, oy in mushroom_offsets:
            self._set_tile_flora(
                self.grid[cy + oy][cx + ox],
                ("king_spotted_mushrooms", "mushrooms", 14, 75),
                force_ripe=True,
            )
        for ox, oy in tree_offsets:
            self._set_tile_flora(
                self.grid[cy + oy][cx + ox],
                ("ancient_gnarled_oak", "tree", 50, 240),
                force_ripe=True,
            )

        for fx, fy in flint_offsets:
            t = self.grid[cy + fy][cx + fx]
            t.resource_node = "flint"
            t.flora_species = None
            t.walkable = True

        self.grid[cy + 5][cx - 4].wildlife_spawner = "ancient_bison"

        self.spawn_metadata = {
            "ancestral_rock_shelter": {"x": shelter_pos[0], "y": shelter_pos[1]},
            "active_campfire": {
                "x": campfire_pos[0],
                "y": campfire_pos[1],
                "warmth_radius": self.campfire_warmth_radius,
                "warm_tiles_count": warm_tiles_count,
            },
            "safe_buffer_radius": self.safe_buffer_radius,
        }

    def get_summary_statistics(self) -> Dict[str, Any]:
        biome_counts: Dict[str, int] = {}
        water_body_counts: Dict[str, int] = {}
        ecotone_counts: Dict[str, int] = {}
        tier_counts: Dict[str, int] = {}
        resource_counts: Dict[str, int] = {}
        wildlife_counts: Dict[str, int] = {}
        cliff_edges = 0
        natural_ramps = 0
        predators_in_safe_zone = 0

        for row in self.grid:
            for tile in row:
                biome_counts[tile.biome_type] = (
                    biome_counts.get(tile.biome_type, 0) + 1
                )
                if tile.water_body_type:
                    water_body_counts[tile.water_body_type] = (
                        water_body_counts.get(tile.water_body_type, 0) + 1
                    )
                ecotone_counts[tile.ecotone_type] = (
                    ecotone_counts.get(tile.ecotone_type, 0) + 1
                )
                tier_label = TERRACE_NAMES.get(
                    tile.elevation_tier, f"Tier {tile.elevation_tier}"
                )
                tier_counts[tier_label] = tier_counts.get(tier_label, 0) + 1
                if tile.is_cliff_edge:
                    cliff_edges += 1
                if tile.is_natural_ramp:
                    natural_ramps += 1
                if tile.resource_node:
                    resource_counts[tile.resource_node] = (
                        resource_counts.get(tile.resource_node, 0) + 1
                    )
                if tile.wildlife_spawner:
                    wildlife_counts[tile.wildlife_spawner] = (
                        wildlife_counts.get(tile.wildlife_spawner, 0) + 1
                    )
                    if tile.wildlife_spawner in PREDATOR_SPAWNERS:
                        dist = math.hypot(
                            tile.tile_x - self.center_x, tile.tile_y - self.center_y
                        )
                        if dist <= self.safe_buffer_radius:
                            predators_in_safe_zone += 1

        return {
            "map_dimensions": {"width": self.width, "height": self.height},
            "biome_distribution": biome_counts,
            "water_body_breakdown": water_body_counts,
            "hydrology_network": self.hydrology_metadata,
            "ecotone_transition_counts": ecotone_counts,
            "elevation_terrace_counts": tier_counts,
            "cliff_edge_tiles": cliff_edges,
            "natural_slope_ramps": natural_ramps,
            "resource_node_counts": resource_counts,
            "wildlife_spawner_counts": wildlife_counts,
            "predators_within_25_tile_safe_zone": predators_in_safe_zone,
        }


class StoneAgeGraphicsRenderer:
    """Renders a 2.5D Terraced RTS Overworld Preview with rich lakes, tributaries, cliff walls, and ecotones."""

    def __init__(self, generator: ProceduralStoneAgeWorldGenerator) -> None:
        self.gen = generator
        if not self.gen.grid:
            self.gen.generate_world()

    def render_25d_terraced_preview(
        self, tile_scale: int = 5, apply_fog_of_war: bool = True
    ) -> Image.Image:
        w, h = self.gen.width, self.gen.height
        canvas = Image.new("RGB", (w * tile_scale, h * tile_scale))
        draw = ImageDraw.Draw(canvas)

        cx, cy = self.gen.center_x, self.gen.center_y
        max_dist = math.hypot(cx, cy)

        base_colors: List[List[Tuple[int, int, int]]] = [
            [(0, 0, 0) for _ in range(w)] for _ in range(h)
        ]

        for y in range(h):
            for x in range(w):
                tile = self.gen.grid[y][x]
                if tile.biome_type == BIOME_COASTAL_WATERS:
                    if tile.elevation_tier == 1:
                        # Shallow ford / lake rim turquoise
                        r, g, b = (76, 166, 194)
                    else:
                        # Deep lake / river bathymetry gradient
                        depth_f = max(0.0, min(1.0, tile.elevation / 0.20))
                        r = int(20 + depth_f * 26)
                        g = int(74 + depth_f * 42)
                        b = int(114 + depth_f * 44)
                else:
                    core_rgb = BIOME_PALETTE_RGB[tile.biome_type]
                    if tile.ecotone_type != ECOTONE_NONE:
                        eco_rgb = ECOTONE_PALETTE_RGB.get(tile.ecotone_type, core_rgb)
                        r = int(core_rgb[0] * 0.40 + eco_rgb[0] * 0.60)
                        g = int(core_rgb[1] * 0.40 + eco_rgb[1] * 0.60)
                        b = int(core_rgb[2] * 0.40 + eco_rgb[2] * 0.60)
                    else:
                        r, g, b = core_rgb

                    tier_light = (tile.elevation_tier - 3) * 11
                    elev_nw = (
                        self.gen.grid[y - 1][x - 1].elevation
                        if (x > 0 and y > 0)
                        else tile.elevation
                    )
                    slope_shade = int(
                        max(-26.0, min(26.0, (tile.elevation - elev_nw) * 165.0))
                    )
                    dither = ((x * 17 + y * 31) % 7) - 3
                    delta = tier_light + slope_shade + dither
                    r = max(0, min(255, r + delta))
                    g = max(0, min(255, g + delta))
                    b = max(0, min(255, b + delta))

                if tile.warmth_radius_active:
                    dist_c = math.hypot(x - cx, y - cy)
                    glow = max(
                        0.0,
                        1.0 - (dist_c / (self.gen.campfire_warmth_radius + 1.5)),
                    )
                    r = min(255, int(r + 88 * glow))
                    g = min(255, int(g + 42 * glow))
                    b = max(0, int(b - 18 * glow))

                base_colors[y][x] = (r, g, b)

        s = tile_scale
        for y in range(h):
            for x in range(w):
                tile = self.gen.grid[y][x]
                r, g, b = base_colors[y][x]
                px0, py0 = x * s, y * s
                px1, py1 = px0 + s - 1, py0 + s - 1

                draw.rectangle([px0, py0, px1, py1], fill=(r, g, b))

                # Sparkling water foam highlight along lake/river shores
                if (
                    tile.biome_type == BIOME_COASTAL_WATERS
                    and tile.autotile_mask_4bit != 15
                ):
                    draw.rectangle(
                        [px0, py0, px1, py0 + 1], fill=(186, 230, 244)
                    )

                if tile.is_natural_ramp:
                    draw.rectangle(
                        [px0, py0, px1, py1], fill=(168, 148, 106)
                    )
                    draw.line(
                        [px0 + 1, py0 + 1, px1 - 1, py0 + 1], fill=(208, 190, 145)
                    )
                elif tile.is_cliff_edge or tile.cliff_drop_south > 0:
                    draw.line(
                        [px0, py0, px1, py0],
                        fill=(
                            min(255, r + 38),
                            min(255, g + 36),
                            min(255, b + 32),
                        ),
                    )
                    if tile.cliff_drop_south > 0:
                        wall_h = min(s, 2 + tile.cliff_drop_south)
                        draw.rectangle(
                            [px0, py1 - wall_h + 1, px1, py1],
                            fill=(54, 48, 44),
                        )

                rn = tile.resource_node
                if rn == "tree":
                    canopy_col = (
                        (182, 212, 218)
                        if tile.biome_type == BIOME_TUNDRA
                        else ((32, 74, 34) if (x + y) % 2 == 0 else (40, 88, 38))
                    )
                    hi_col = (
                        (230, 244, 248)
                        if tile.biome_type == BIOME_TUNDRA
                        else (68, 128, 56)
                    )
                    draw.rectangle(
                        [px0 + 1, py0 + 1, px1 - 1, py1 - 1], fill=canopy_col
                    )
                    draw.point((px0 + 1, py0 + 1), fill=hi_col)
                elif rn == "berries":
                    draw.rectangle(
                        [px0 + 1, py0 + 1, px1 - 1, py1 - 1], fill=(46, 108, 44)
                    )
                    draw.point((px0 + s // 2, py0 + s // 2), fill=(228, 42, 64))
                    draw.point((px0 + 1, py1 - 1), fill=(244, 68, 84))
                elif rn == "wild_grain":
                    draw.rectangle(
                        [px0 + 1, py0 + 1, px1 - 1, py1 - 1], fill=(234, 184, 36)
                    )
                elif rn == "fiber_plant":
                    draw.rectangle(
                        [px0 + 1, py0 + 1, px1 - 1, py1 - 1], fill=(56, 142, 82)
                    )
                    draw.point((px0 + s // 2, py0 + 1), fill=(138, 92, 48))
                elif rn == "flint":
                    draw.rectangle(
                        [px0 + 1, py0 + 1, px1 - 1, py1 - 1], fill=(74, 80, 92)
                    )
                    draw.point((px0 + 1, py0 + 1), fill=(156, 166, 182))
                elif rn == "bone_deposit":
                    draw.rectangle(
                        [px0 + 1, py0 + 1, px1 - 1, py1 - 1], fill=(238, 228, 204)
                    )

                if tile.special_feature:
                    if "Shelter" in tile.special_feature:
                        draw.rectangle(
                            [px0 - s, py0 - s, px1 + s, py1 + s],
                            fill=(214, 192, 142),
                            outline=(78, 64, 52),
                        )
                    elif "Campfire" in tile.special_feature:
                        draw.rectangle(
                            [px0 - 2, py0 - 2, px1 + 2, py1 + 2],
                            fill=(255, 94, 20),
                            outline=(254, 240, 138),
                        )

                if apply_fog_of_war:
                    dist_edge = math.hypot(x - cx, y - cy) / max_dist
                    if dist_edge > 0.80:
                        fog = min(0.84, (dist_edge - 0.80) / 0.20 * 0.84)
                        fr = int(r * (1.0 - fog) + 18 * fog)
                        fg = int(g * (1.0 - fog) + 16 * fog)
                        fb = int(b * (1.0 - fog) + 22 * fog)
                        draw.rectangle([px0, py0, px1, py1], fill=(fr, fg, fb))

        return canvas

    def render_biome_stitching_and_terrace_atlas(self, output_path: str) -> str:
        """Renders a 4-panel visual showcase of the Multi-Lake & Tributary Hydrology,
        6-Tier Elevation Terraces, Ecotone Stitching Belts, and Central Oasis Lake Zoom."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
        import numpy as np

        preview_25d = self.render_25d_terraced_preview(
            tile_scale=5, apply_fog_of_war=True
        )

        fig, axes = plt.subplots(2, 2, figsize=(16, 15.5), dpi=150)
        fig.patch.set_facecolor("#1c1917")

        title_style = {
            "color": "#f5f5f4",
            "fontsize": 13,
            "fontweight": "bold",
            "pad": 10,
        }
        label_color = "#d6d3d1"

        # Panel 1: 2.5D Terraced Overworld Preview Map with Lakes & Tributaries
        ax1 = axes[0, 0]
        ax1.imshow(
            preview_25d,
            extent=[0, self.gen.width, self.gen.height, 0],
            interpolation="bilinear",
        )
        # Annotate the 5 Major Lakes on the Overworld Map
        for lk in self.gen.hydrology_metadata.get("major_lakes", []):
            lx, ly = lk["center"]
            short_n = lk["name"].replace("Northern ", "N. ").replace("Northeastern ", "NE ").replace("Western ", "W. ").replace("Great Eastern ", "E. ").replace("Central ", "")
            ax1.text(
                lx,
                ly,
                short_n,
                color="#e0f2fe",
                fontsize=7.5,
                fontweight="bold",
                ha="center",
                va="center",
                bbox=dict(
                    boxstyle="round,pad=0.2",
                    facecolor="#0c4a6e",
                    edgecolor="#38bdf8",
                    alpha=0.78,
                ),
            )

        ax1.set_title(
            "1. 2.5D Overworld Preview (5 Major Lakes, 6 Tributaries & 7 Oxbow Ponds)",
            **title_style,
        )
        ax1.tick_params(colors=label_color)
        legend_patches = [
            mpatches.Patch(color=tuple(c / 255.0 for c in rgb), label=b_name)
            for b_name, rgb in BIOME_PALETTE_RGB.items()
        ]
        ax1.legend(
            handles=legend_patches,
            loc="lower left",
            fontsize=8,
            facecolor="#292524",
            edgecolor="#78716c",
            labelcolor="#f5f5f4",
        )

        # Panel 2: Discrete 6-Tier Terraced Elevation & Hydrology Bathymetry
        ax2 = axes[0, 1]
        tier_arr = np.array(
            [[t.elevation_tier for t in row] for row in self.gen.grid], dtype=float
        )
        cmap_tiers = matplotlib.colors.ListedColormap(
            [
                "#164e63",  # Tier 0: Deep Lake & River Core
                "#38bdf8",  # Tier 1: Shallow Wading Rim & River Fords
                "#5c8252",  # Tier 2: Lowland River/Lake Basin & Swamp
                "#94ac4c",  # Tier 3: Main Steppe & Forest Terrace
                "#8c7e6a",  # Tier 4: Highland Mesa & Tundra Plateau
                "#e2ecf4",  # Tier 5: Megalithic Summit & Glacier Crag
            ]
        )
        im2 = ax2.imshow(
            tier_arr,
            cmap=cmap_tiers,
            vmin=-0.5,
            vmax=5.5,
            interpolation="nearest",
        )
        cliff_pts = [
            (t.tile_x, t.tile_y)
            for row in self.gen.grid
            for t in row
            if t.is_cliff_edge
        ]
        ramp_pts = [
            (t.tile_x, t.tile_y)
            for row in self.gen.grid
            for t in row
            if t.is_natural_ramp
        ]
        if cliff_pts:
            cp = np.array(cliff_pts)
            ax2.scatter(
                cp[:, 0],
                cp[:, 1],
                c="#1c1917",
                s=1.8,
                alpha=0.85,
                label=f"Impassable Cliff Ledges ({len(cliff_pts)})",
            )
        if ramp_pts:
            rp = np.array(ramp_pts)
            ax2.scatter(
                rp[:, 0],
                rp[:, 1],
                c="#facc15",
                s=8.0,
                marker="s",
                label=f"Natural Passable Slope Ramps ({len(ramp_pts)})",
            )
        ax2.set_title(
            "2. 6-Tier Terraces, Deep Lake Bathymetry (T0) & Shallow Fords (T1)",
            **title_style,
        )
        ax2.tick_params(colors=label_color)
        ax2.legend(
            loc="lower left",
            fontsize=8.5,
            facecolor="#292524",
            edgecolor="#78716c",
            labelcolor="#f5f5f4",
        )
        cbar2 = fig.colorbar(
            im2, ax=ax2, ticks=[0, 1, 2, 3, 4, 5], fraction=0.046, pad=0.04
        )
        cbar2.ax.set_yticklabels(
            ["T0 Deep", "T1 Shoal/Ford", "T2 Basin", "T3 Steppe", "T4 Mesa", "T5 Peak"],
            color=label_color,
            fontsize=8,
        )

        # Panel 3: Biome Stitching & Expanded Pebble Shoreline / Marsh Belts
        ax3 = axes[1, 0]
        eco_map_order = [
            ECOTONE_NONE,
            ECOTONE_PEBBLE_SHORELINE,
            ECOTONE_WOODLAND_SAVANNA,
            ECOTONE_ROCKY_FOOTHILLS,
            ECOTONE_TAIGA_FROST_EDGE,
            ECOTONE_WETLAND_MARSH,
        ]
        eco_idx_map = {k: i for i, k in enumerate(eco_map_order)}
        eco_arr = np.array(
            [
                [
                    -1
                    if t.biome_type == BIOME_COASTAL_WATERS
                    else eco_idx_map.get(t.ecotone_type, 0)
                    for t in row
                ]
                for row in self.gen.grid
            ],
            dtype=float,
        )
        cmap_eco = matplotlib.colors.ListedColormap(
            [
                "#0284c7",  # Water Network (Rivers, Tributaries & Lakes)
                "#292524",  # Core Land Biome Interior
                "#fbbf24",  # Pebble Shoreline (Water <-> Land)
                "#4ade80",  # Woodland Border (Forest <-> Steppe)
                "#f97316",  # Rocky Foothills Talus
                "#38bdf8",  # Taiga Frost Edge
                "#a855f7",  # Wetland Marsh Fringe
            ]
        )
        ax3.imshow(
            eco_arr, cmap=cmap_eco, vmin=-1.5, vmax=5.5, interpolation="nearest"
        )
        eco_patches = [
            mpatches.Patch(
                color="#0284c7", label="Rivers, Tributaries & Lakes Network"
            ),
            mpatches.Patch(
                color="#fbbf24", label="Pebble Shoreline Belt (Water <-> Land)"
            ),
            mpatches.Patch(
                color="#a855f7", label="Wetland Marsh Fringe (Swamp <-> Water)"
            ),
            mpatches.Patch(
                color="#4ade80", label="Woodland Border (Forest <-> Steppe)"
            ),
            mpatches.Patch(
                color="#f97316", label="Rocky Foothills (Highland <-> Steppe)"
            ),
            mpatches.Patch(
                color="#38bdf8", label="Taiga Frost Edge (Tundra <-> Steppe)"
            ),
        ]
        ax3.set_title(
            "3. Hydrology Network & Stitched Shoreline / Ecotone Belts",
            **title_style,
        )
        ax3.tick_params(colors=label_color)
        ax3.legend(
            handles=eco_patches,
            loc="lower left",
            fontsize=8,
            facecolor="#1c1917",
            edgecolor="#78716c",
            labelcolor="#f5f5f4",
        )

        # Panel 4: Close-Up Zoom (50..145, 55..140) showing Central Oasis Lake, Tributary Confluences & Spawn
        ax4 = axes[1, 1]
        zx0, zy0, zx1, zy1 = 50, 55, 145, 140
        s = 5
        crop_25d = preview_25d.crop((zx0 * s, zy0 * s, zx1 * s, zy1 * s))
        ax4.imshow(
            crop_25d,
            extent=[zx0, zx1, zy1, zy0],
            interpolation="nearest",
        )
        for y in range(zy0, zy1):
            for x in range(zx0, zx1):
                t = self.gen.grid[y][x]
                if t.special_feature and "Shelter" in t.special_feature:
                    ax4.scatter(
                        x,
                        y,
                        c="#fde047",
                        s=160,
                        marker="^",
                        edgecolors="black",
                        zorder=6,
                    )
                elif t.wildlife_spawner == "fish_shoal":
                    ax4.scatter(
                        x,
                        y,
                        c="#38bdf8",
                        s=38,
                        marker="d",
                        edgecolors="white",
                        zorder=5,
                    )

        ax4.set_title(
            "4. Close-Up: Central Oasis Lake, Tributary Confluences & Stepping-Stone Fords",
            **title_style,
        )
        ax4.tick_params(colors=label_color)

        plt.suptitle(
            "PREHISTORIC STONE AGE RTS — EXPANDED HYDROLOGY (5 LAKES, 6 TRIBUTARIES & 7 PONDS) & 6-TIER TERRACES",
            color="#fafaf9",
            fontsize=14.5,
            fontweight="bold",
            y=0.98,
        )
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path, dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
        return output_path


if __name__ == "__main__":
    generator = ProceduralStoneAgeWorldGenerator(width=200, height=200, seed=2026)
    world_matrix = generator.generate_world()
    stats = generator.get_summary_statistics()
    print("=== EXPANDED HYDROLOGY, BIOME STITCHING & TERRACES SUMMARY ===")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

    output_dir = os.path.dirname(os.path.abspath(__file__))
    renderer = StoneAgeGraphicsRenderer(generator)

    standalone_preview_path = os.path.join(
        output_dir, "stone_age_25d_terraced_map_preview.png"
    )
    preview_img = renderer.render_25d_terraced_preview(
        tile_scale=5, apply_fog_of_war=True
    )
    preview_img.save(standalone_preview_path, format="PNG")

    terrace_atlas_path = os.path.join(
        output_dir, "stone_age_biome_stitching_terrace_atlas.png"
    )
    renderer.render_biome_stitching_and_terrace_atlas(terrace_atlas_path)
    print(f"\nSaved standalone 2.5D preview to: {standalone_preview_path}")
    print(f"Saved 4-panel hydrology & terrace atlas to: {terrace_atlas_path}")


# ==============================================================================
# PHASE 3: ENVIRONMENTAL PHYSICS, SUBSURFACE GROUNDWATER, 4-SEASON WEATHER
#          & NATURAL DISASTERS ENGINE
# ==============================================================================

SEASON_SPRING_THAW = "Spring Thaw (Xuân Băng Tan)"
SEASON_SUMMER_MONSOON = "Summer Monsoon & Drought (Hạ Mưa Dông & Nắng Hạn)"
SEASON_AUTUMN_GALE = "Autumn Gale & Frost (Thu Gió Chướng & Sương Giá)"
SEASON_WINTER_ICE_AGE = "Deep Ice Age Winter (Đông Đại Hàn Kỷ Băng Hà)"

# Soil hydraulic conductivity K (Darcy permeability coefficient by biome)
SOIL_PERMEABILITY_K: Dict[str, float] = {
    BIOME_STEPPE_GRASSLAND: 0.78,      # Porous sandy-loam savanna soil
    BIOME_PRIMEVAL_FOREST: 0.64,       # Humus-rich forest floor
    BIOME_TUNDRA: 0.22,                # Permafrost restricts deep infiltration
    BIOME_ANCIENT_SWAMP: 0.18,         # Saturated clay/peat aquitard (holds surface water)
    BIOME_MEGALITHIC_HIGHLANDS: 0.12,  # Fractured granite bedrock (forms confined aquifers)
    BIOME_COASTAL_WATERS: 1.00,        # Open water body
}


class StoneAgePhysicsWeatherAndDisasterEngine:
    """Simulates Darcy groundwater aquifers, D8 surface hydraulics, thermodynamics,
    4-season Paleolithic weather cycles, and physics-driven natural disasters."""

    def __init__(self, generator: ProceduralStoneAgeWorldGenerator) -> None:
        self.gen = generator
        if not self.gen.grid:
            self.gen.generate_world()
        self.w = self.gen.width
        self.h = self.gen.height
        self.rng = random.Random(self.gen.seed + 9001)

        # Physics fields (200x200 matrices)
        self.permeability_k: List[List[float]] = [
            [0.5 for _ in range(self.w)] for _ in range(self.h)
        ]
        self.groundwater_head: List[List[float]] = [
            [0.0 for _ in range(self.w)] for _ in range(self.h)
        ]
        self.water_table_depth: List[List[float]] = [
            [0.0 for _ in range(self.w)] for _ in range(self.h)
        ]
        self.darcy_flux_uv: List[List[Tuple[float, float]]] = [
            [(0.0, 0.0) for _ in range(self.w)] for _ in range(self.h)
        ]
        self.surface_flow_uv: List[List[Tuple[float, float]]] = [
            [(0.0, 0.0) for _ in range(self.w)] for _ in range(self.h)
        ]
        self.flow_discharge: List[List[float]] = [
            [0.0 for _ in range(self.w)] for _ in range(self.h)
        ]
        self.alluvial_fertility: List[List[float]] = [
            [0.0 for _ in range(self.w)] for _ in range(self.h)
        ]
        self.orographic_rain_factor: List[List[float]] = [
            [1.0 for _ in range(self.w)] for _ in range(self.h)
        ]
        self.temp_celsius: List[List[float]] = [
            [15.0 for _ in range(self.w)] for _ in range(self.h)
        ]

        # Dynamic features & disaster logs
        self.artesian_springs: List[Tuple[int, int]] = []
        self.geothermal_hot_springs: List[Tuple[int, int]] = []
        self.seasonal_metrics: Dict[str, Dict[str, Any]] = {}
        self.disaster_events_log: Dict[str, Any] = {}

    def run_full_physics_and_seasonal_simulation(self) -> Dict[str, Any]:
        """Executes the complete multi-layer physics, groundwater, 4-season, and disaster pipeline."""
        self._compute_subsurface_groundwater_and_springs()
        self._compute_surface_hydraulics_and_alluvial_fertility()
        self._compute_orographic_wind_and_rain_shadow(wind_vec=(-0.75, -0.65))
        self._simulate_four_seasons_cycle()
        self._simulate_natural_disasters()

        return {
            "groundwater_summary": {
                "artesian_freshwater_springs_count": len(self.artesian_springs),
                "geothermal_hot_springs_count": len(self.geothermal_hot_springs),
                "artesian_spring_coords": [list(p) for p in self.artesian_springs[:10]],
                "geothermal_hot_spring_coords": [
                    list(p) for p in self.geothermal_hot_springs
                ],
            },
            "seasonal_cycle_metrics": self.seasonal_metrics,
            "natural_disasters_summary": self.disaster_events_log,
        }

    def _compute_subsurface_groundwater_and_springs(self) -> None:
        """Applies Darcy's Law (q = -K * grad(h)) to model subsurface aquifers, water table depth,
        artesian oasis springs at foothill faults, and geothermal hot springs in cold highlands."""
        for y in range(self.h):
            for x in range(self.w):
                t = self.gen.grid[y][x]
                self.permeability_k[y][x] = SOIL_PERMEABILITY_K.get(
                    t.biome_type, 0.5
                )
                # Initial hydraulic head h = elevation * 0.75 + moisture * 0.35
                if t.biome_type == BIOME_COASTAL_WATERS:
                    self.groundwater_head[y][x] = t.elevation + 0.12
                else:
                    self.groundwater_head[y][x] = (
                        t.elevation * 0.78 + t.moisture * 0.32
                    )

        # Iterative Laplace/Darcy relaxation (6 passes) to simulate subsurface lateral seepage
        for _ in range(6):
            next_head = [row[:] for row in self.groundwater_head]
            for y in range(1, self.h - 1):
                for x in range(1, self.w - 1):
                    if self.gen.grid[y][x].biome_type == BIOME_COASTAL_WATERS:
                        continue
                    k_local = self.permeability_k[y][x]
                    avg_nb = 0.25 * (
                        self.groundwater_head[y - 1][x]
                        + self.groundwater_head[y + 1][x]
                        + self.groundwater_head[y][x - 1]
                        + self.groundwater_head[y][x + 1]
                    )
                    next_head[y][x] = (
                        1.0 - 0.45 * k_local
                    ) * self.groundwater_head[y][x] + (0.45 * k_local) * avg_nb
            self.groundwater_head = next_head

        # Compute Darcy velocity flux q = -K * grad(h) and identify Artesian & Geothermal Springs
        self.artesian_springs = []
        self.geothermal_hot_springs = []

        for y in range(2, self.h - 2):
            for x in range(2, self.w - 2):
                t = self.gen.grid[y][x]
                dh_dx = (
                    self.groundwater_head[y][x + 1]
                    - self.groundwater_head[y][x - 1]
                ) * 0.5
                dh_dy = (
                    self.groundwater_head[y + 1][x]
                    - self.groundwater_head[y - 1][x]
                ) * 0.5
                k_val = self.permeability_k[y][x]
                qx = -k_val * dh_dx
                qy = -k_val * dh_dy
                self.darcy_flux_uv[y][x] = (round(qx, 4), round(qy, 4))

                # Depth to water table (0.0 = saturated at surface / spring, 1.0 = deep dry rock)
                wt_depth = max(
                    0.0,
                    min(1.0, (t.elevation - self.groundwater_head[y][x] * 0.72) * 2.2),
                )
                if t.biome_type == BIOME_COASTAL_WATERS:
                    wt_depth = 0.0
                self.water_table_depth[y][x] = round(wt_depth, 4)

                # 1) Artesian Freshwater Springs: emerge at foothill faults where groundwater head surges
                if (
                    t.ecotone_type == ECOTONE_ROCKY_FOOTHILLS
                    and wt_depth < 0.16
                    and t.walkable
                ):
                    if all(
                        math.hypot(x - sx, y - sy) > 18.0
                        for sx, sy in self.artesian_springs
                    ):
                        self.artesian_springs.append((x, y))
                        t.special_feature = "Artesian Freshwater Spring"
                        t.moisture = 1.0

                # 2) Geothermal Hot Springs: emerge along tectonic crags in Tundra & Megalithic Highlands
                if (
                    t.biome_type in (BIOME_TUNDRA, BIOME_MEGALITHIC_HIGHLANDS)
                    and t.elevation_tier in (3, 4)
                    and t.is_natural_ramp
                ):
                    if (
                        len(self.geothermal_hot_springs) < 6
                        and all(
                            math.hypot(x - gx, y - gy) > 28.0
                            for gx, gy in self.geothermal_hot_springs
                        )
                    ):
                        self.geothermal_hot_springs.append((x, y))
                        t.special_feature = "Geothermal Hot Spring Geyser"
                        t.walkable = True

    def _compute_surface_hydraulics_and_alluvial_fertility(self) -> None:
        """Computes gravity-driven surface flow vectors v = -g * grad(z), D8 flow accumulation,
        and alluvial silt fertility along floodplains and deltas."""
        # Sort all tiles from highest elevation to lowest to propagate D8 runoff downstream
        all_coords = [
            (self.gen.grid[y][x].elevation, x, y)
            for y in range(self.h)
            for x in range(self.w)
        ]
        all_coords.sort(reverse=True)

        accum = [[1.0 for _ in range(self.w)] for _ in range(self.h)]

        for _, x, y in all_coords:
            my_elev = self.gen.grid[y][x].elevation
            best_drop = 0.0
            best_nb: Optional[Tuple[int, int]] = None

            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h:
                        drop = (my_elev - self.gen.grid[ny][nx].elevation) / math.hypot(
                            dx, dy
                        )
                        if drop > best_drop:
                            best_drop = drop
                            best_nb = (nx, ny)

            if best_nb is not None:
                accum[best_nb[1]][best_nb[0]] += accum[y][x] * 0.88

        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                t = self.gen.grid[y][x]
                dz_dx = (
                    self.gen.grid[y][x + 1].elevation
                    - self.gen.grid[y][x - 1].elevation
                ) * 0.5
                dz_dy = (
                    self.gen.grid[y + 1][x].elevation
                    - self.gen.grid[y - 1][x].elevation
                ) * 0.5

                # River channels have a strong southward + downstream hydraulic flow
                if t.biome_type == BIOME_COASTAL_WATERS:
                    vx = -dz_dx * 18.0
                    vy = max(0.35, -dz_dy * 18.0 + 0.45)
                    discharge = min(100.0, accum[y][x] * 1.8 + 12.0)
                else:
                    vx = -dz_dx * 12.0
                    vy = -dz_dy * 12.0
                    discharge = min(100.0, accum[y][x])

                self.surface_flow_uv[y][x] = (round(vx, 3), round(vy, 3))
                self.flow_discharge[y][x] = round(discharge, 2)

                # Alluvial Silt Fertility: high where moisture/groundwater is rich and slope is gentle
                slope_mag = math.hypot(dz_dx, dz_dy)
                silt = (
                    t.moisture * 0.55
                    + (1.0 - self.water_table_depth[y][x]) * 0.35
                    + max(0.0, 0.15 - slope_mag * 2.0)
                )
                if t.ecotone_type in (
                    ECOTONE_PEBBLE_SHORELINE,
                    ECOTONE_WETLAND_MARSH,
                ):
                    silt += 0.22
                self.alluvial_fertility[y][x] = round(max(0.0, min(1.0, silt)), 3)

    def _compute_orographic_wind_and_rain_shadow(
        self, wind_vec: Tuple[float, float] = (-0.75, -0.65)
    ) -> None:
        """Models Orographic Lift (windward condensation rain) and Foehn Rain Shadow (leeward dryness)."""
        wx, wy = wind_vec
        w_norm = max(1e-5, math.hypot(wx, wy))
        ux, uy = wx / w_norm, wy / w_norm

        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                dz_dx = (
                    self.gen.grid[y][x + 1].elevation
                    - self.gen.grid[y][x - 1].elevation
                ) * 0.5
                dz_dy = (
                    self.gen.grid[y + 1][x].elevation
                    - self.gen.grid[y - 1][x].elevation
                ) * 0.5
                # Dot product between wind vector and terrain upward gradient:
                # Positive = wind blowing uphill (Orographic lift -> heavy rain)
                # Negative = wind descending leeward slope (Foehn effect -> dry rain shadow)
                uphill_dot = ux * dz_dx + uy * dz_dy
                oro_factor = max(0.45, min(1.65, 1.0 + uphill_dot * 14.0))
                self.orographic_rain_factor[y][x] = round(oro_factor, 3)

    def evaluate_temperature_field_celsius(
        self,
        season_base_c: float,
        wind_vec: Tuple[float, float] = (0.0, 1.0),
    ) -> List[List[float]]:
        """Computes physical temperature in Celsius (°C) across all 40,000 tiles:
        T(x,y) = T_season + Latitude_Insolation - Adiabatic_Lapse_Rate(Tier)
                 + Water_Thermal_Inertia + Wind_Advected_Campfire_&_Geothermal_Heat.
        """
        temp_c = [[0.0 for _ in range(self.w)] for _ in range(self.h)]
        cx, cy = self.gen.center_x, self.gen.center_y
        wx, wy = wind_vec

        for y in range(self.h):
            lat = y / max(1, self.h - 1)  # 0.0 North (-14°C colder) -> 1.0 South (+10°C warmer)
            lat_offset_c = (lat - 0.45) * 24.0

            for x in range(self.w):
                t = self.gen.grid[y][x]
                # Adiabatic lapse rate: -4.8°C per elevation tier above Tier 2
                lapse_c = -max(0, t.elevation_tier - 2) * 4.8

                # Water bodies have high specific heat capacity (moderate extremes)
                water_buffer_c = 0.0
                if t.biome_type == BIOME_COASTAL_WATERS:
                    water_buffer_c = 3.5 if season_base_c < 5.0 else -2.5

                val_c = season_base_c + lat_offset_c + lapse_c + water_buffer_c

                # Wind-advected Campfire Hearth heat plume (+16°C at core, shifted downwind)
                eff_cx = cx + wx * 1.6
                eff_cy = cy + wy * 1.6
                dist_camp = math.hypot(x - eff_cx, y - eff_cy)
                if dist_camp <= self.gen.campfire_warmth_radius + 1.5:
                    val_c += 16.0 * max(
                        0.0, 1.0 - dist_camp / (self.gen.campfire_warmth_radius + 1.5)
                    )

                # Geothermal Hot Springs provide an 8-tile permanent +18°C thermal sanctuary
                for gx, gy in self.geothermal_hot_springs:
                    dist_geo = math.hypot(x - (gx + wx * 1.2), y - (gy + wy * 1.2))
                    if dist_geo <= 8.0:
                        val_c += 18.0 * (1.0 - dist_geo / 8.0)

                temp_c[y][x] = round(val_c, 2)

        return temp_c

    def _simulate_four_seasons_cycle(self) -> None:
        """Simulates all 4 Paleolithic seasons and computes hydrological, thermal, and ecological shifts."""
        seasons_config = [
            (
                SEASON_SPRING_THAW,
                11.0,
                (0.4, 0.8),
                1.65,
                1.35,
                "Glacial snowmelt surges rivers (+65% discharge); rich alluvial mud boosts sprouting.",
            ),
            (
                SEASON_SUMMER_MONSOON,
                24.0,
                (-0.8, -0.5),
                0.85,
                1.50,
                "Monsoon rains drench Eastern Jungle while Western Steppe experiences Foehn heat & wildfire risk.",
            ),
            (
                SEASON_AUTUMN_GALE,
                8.0,
                (-0.6, 0.7),
                1.05,
                0.90,
                "Cold northeast gales bring dense marsh fog (-35% LoS) and peak tuber/nut harvest before frost.",
            ),
            (
                SEASON_WINTER_ICE_AGE,
                -9.5,
                (0.2, 1.2),
                0.45,
                0.15,
                "Sub-zero Ice Age freeze locks shallow rivers/lakes into walkable ice bridges; blizzards threaten survival.",
            ),
        ]

        self.seasonal_metrics = {}
        for (
            s_name,
            base_c,
            wind_v,
            discharge_mult,
            growth_mult,
            desc,
        ) in seasons_config:
            t_field = self.evaluate_temperature_field_celsius(base_c, wind_vec=wind_v)
            flat_temps = [val for row in t_field for val in row]
            mean_temp = sum(flat_temps) / len(flat_temps)

            # Count frozen walkable water tiles (T <= -2.0°C on Tier 1 shallow water / fords / lake rims)
            frozen_walkable_tiles = 0
            drought_fire_risk_tiles = 0
            for y in range(self.h):
                for x in range(self.w):
                    tile = self.gen.grid[y][x]
                    tc = t_field[y][x]
                    if (
                        tile.biome_type == BIOME_COASTAL_WATERS
                        and tile.elevation_tier == 1
                        and tc <= -2.0
                    ):
                        frozen_walkable_tiles += 1
                    if (
                        tile.biome_type
                        in (BIOME_STEPPE_GRASSLAND, BIOME_PRIMEVAL_FOREST)
                        and tc >= 21.0
                        and self.water_table_depth[y][x] > 0.42
                    ):
                        drought_fire_risk_tiles += 1

            self.seasonal_metrics[s_name] = {
                "mean_temperature_celsius": round(mean_temp, 1),
                "min_temperature_celsius": round(min(flat_temps), 1),
                "max_temperature_celsius": round(max(flat_temps), 1),
                "prevailing_wind_vector": list(wind_v),
                "river_discharge_multiplier": discharge_mult,
                "flora_growth_rate_multiplier": growth_mult,
                "frozen_walkable_ice_bridge_tiles": frozen_walkable_tiles,
                "high_wildfire_risk_tiles": drought_fire_risk_tiles,
                "gameplay_effect": desc,
            }
            if s_name == SEASON_WINTER_ICE_AGE:
                self.temp_celsius = t_field

    def _simulate_natural_disasters(self) -> None:
        """Simulates 4 physics-driven natural disasters on the map:
        1) Spring/Monsoon Flash Flood (riverbank inundation + alluvial silt deposition)
        2) Summer Wind-Driven Wildfire (cellular automata fire spread along wind vector + ash fertility)
        3) Deep Winter Blizzard Whiteout (frozen river ice bridges + hypothermia zone)
        4) Highland Cliff Rockslide (collapses steep cliff ledges & exposes new flint boulders)
        """
        # 1. Flash Flood Simulation: Low-lying Tier 2 riverbanks within 2 tiles of Main River / Tributaries flood
        flooded_tiles: List[Tuple[int, int]] = []
        for y in range(2, self.h - 2):
            for x in range(2, self.w - 2):
                t = self.gen.grid[y][x]
                if (
                    t.biome_type != BIOME_COASTAL_WATERS
                    and t.elevation_tier == 2
                    and t.elevation < 0.34
                    and t.ecotone_type
                    in (ECOTONE_PEBBLE_SHORELINE, ECOTONE_WETLAND_MARSH)
                ):
                    flooded_tiles.append((x, y))
                    # Post-flood bonus: enriches alluvial fertility by +0.25
                    self.alluvial_fertility[y][x] = min(
                        1.0, round(self.alluvial_fertility[y][x] + 0.25, 3)
                    )

        # 2. Wind-Driven Wildfire Cellular Automata (ignited by lightning at dry forest-steppe border)
        ignition_pt = (132, 82)
        wind_dir = (0.85, 0.45)  # Blowing East-Southeast
        burned_tiles: Set[Tuple[int, int]] = {ignition_pt}
        frontier: List[Tuple[int, int]] = [ignition_pt]

        for _ in range(14):  # 14 propagation waves
            next_frontier: List[Tuple[int, int]] = []
            for fx, fy in frontier:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = fx + dx, fy + dy
                        if not (1 <= nx < self.w - 1 and 1 <= ny < self.h - 1):
                            continue
                        if (nx, ny) in burned_tiles:
                            continue
                        ntile = self.gen.grid[ny][nx]
                        # Water bodies, swamps, and sheer cliffs act as natural firebreaks!
                        if ntile.biome_type in (
                            BIOME_COASTAL_WATERS,
                            BIOME_ANCIENT_SWAMP,
                            BIOME_TUNDRA,
                        ):
                            continue
                        if ntile.is_cliff_edge:
                            continue

                        # Dot product with wind vector boosts downwind spread probability
                        step_len = math.hypot(dx, dy)
                        wind_align = (dx * wind_dir[0] + dy * wind_dir[1]) / step_len
                        fuel_bonus = (
                            0.32
                            if ntile.resource_node
                            in ("tree", "wild_grain", "fiber_plant")
                            else 0.12
                        )
                        spread_prob = (
                            0.28 + max(-0.15, wind_align * 0.34) + fuel_bonus
                        )
                        if self.rng.random() < spread_prob and len(burned_tiles) < 240:
                            burned_tiles.add((nx, ny))
                            next_frontier.append((nx, ny))
                            # Leave behind fertile charcoal ash
                            self.alluvial_fertility[ny][nx] = min(
                                1.0,
                                round(self.alluvial_fertility[ny][nx] + 0.30, 3),
                            )
            frontier = next_frontier
            if not frontier:
                break

        # 3. Cliff Rockslide / Avalanche on steep Tier 4/5 Megalithic Highland ledges
        rockslide_tiles: List[Tuple[int, int]] = []
        for y in range(10, self.h - 10):
            for x in range(5, 65):
                t = self.gen.grid[y][x]
                if t.is_cliff_edge and t.cliff_drop_south >= 1:
                    if self.rng.random() < 0.065:
                        rockslide_tiles.append((x, y))
                        # Deposit fresh harvestable flint boulder at the base of the cliff
                        if y + 1 < self.h:
                            base_t = self.gen.grid[y + 1][x]
                            if base_t.biome_type != BIOME_COASTAL_WATERS:
                                base_t.resource_node = "flint"

        # 4. Winter Frozen Ice Bridges across shallow rivers & lake rims
        winter_temp = self.evaluate_temperature_field_celsius(
            -9.5, wind_vec=(0.2, 1.2)
        )
        frozen_ice_tiles = [
            (x, y)
            for y in range(self.h)
            for x in range(self.w)
            if self.gen.grid[y][x].biome_type == BIOME_COASTAL_WATERS
            and self.gen.grid[y][x].elevation_tier == 1
            and winter_temp[y][x] <= -2.0
        ]

        self.disaster_events_log = {
            "flash_flood": {
                "inundated_riverbank_tiles": len(flooded_tiles),
                "post_flood_alluvial_fertility_bonus": "+0.25",
            },
            "wind_driven_wildfire": {
                "ignition_origin": list(ignition_pt),
                "wind_vector": list(wind_dir),
                "burned_canopy_and_steppe_tiles": len(burned_tiles),
                "post_fire_ash_fertility_bonus": "+0.30",
            },
            "cliff_rockslides": {
                "collapsed_cliff_tiles": len(rockslide_tiles),
                "new_flint_deposits_exposed": len(rockslide_tiles),
            },
            "winter_blizzard_freeze": {
                "walkable_frozen_ice_bridge_tiles": len(frozen_ice_tiles),
                "geothermal_refuge_zones": len(self.geothermal_hot_springs),
            },
            "_coords": {
                "flooded": flooded_tiles,
                "burned": list(burned_tiles),
                "rockslides": rockslide_tiles,
                "frozen_ice": frozen_ice_tiles,
            },
        }

    def render_physics_weather_and_disasters_atlas(
        self, renderer: StoneAgeGraphicsRenderer, output_path: str
    ) -> str:
        """Renders a 6-panel Master Visual Atlas of Groundwater, Hydraulics, Thermodynamics,
        Seasonal Weather, and Dynamic Natural Disasters."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
        import numpy as np

        preview_25d = renderer.render_25d_terraced_preview(
            tile_scale=4, apply_fog_of_war=False
        )

        fig, axes = plt.subplots(2, 3, figsize=(21, 13.5), dpi=150)
        fig.patch.set_facecolor("#1c1917")

        title_style = {
            "color": "#f5f5f4",
            "fontsize": 12,
            "fontweight": "bold",
            "pad": 9,
        }
        label_color = "#d6d3d1"

        # Panel 1: Subsurface Groundwater Table, Darcy Flux & Artesian/Geothermal Springs
        ax1 = axes[0, 0]
        gw_arr = np.array(
            [[1.0 - self.water_table_depth[y][x] for x in range(self.w)] for y in range(self.h)],
            dtype=float,
        )
        im1 = ax1.imshow(gw_arr, cmap="GnBu", vmin=0.0, vmax=1.0)
        # Quiver plot of Darcy subsurface groundwater flux every 10 tiles
        step_q = 10
        Y_q, X_q = np.mgrid[5 : self.h - 5 : step_q, 5 : self.w - 5 : step_q]
        U_q = np.array(
            [
                [self.darcy_flux_uv[y][x][0] for x in range(5, self.w - 5, step_q)]
                for y in range(5, self.h - 5, step_q)
            ]
        )
        V_q = np.array(
            [
                [self.darcy_flux_uv[y][x][1] for x in range(5, self.w - 5, step_q)]
                for y in range(5, self.h - 5, step_q)
            ]
        )
        mag_q = np.hypot(U_q, V_q) + 1e-6
        U_qn = (U_q / mag_q) * np.minimum(mag_q, 0.018)
        V_qn = (V_q / mag_q) * np.minimum(mag_q, 0.018)
        ax1.quiver(
            X_q,
            Y_q,
            U_qn,
            V_qn,
            color="#0f172a",
            alpha=0.72,
            scale=0.22,
            width=0.0032,
        )
        if self.artesian_springs:
            ap = np.array(self.artesian_springs)
            ax1.scatter(
                ap[:, 0],
                ap[:, 1],
                c="#22d3ee",
                s=75,
                marker="o",
                edgecolors="black",
                linewidths=1.2,
                label=f"Artesian Freshwater Springs ({len(self.artesian_springs)})",
                zorder=5,
            )
        if self.geothermal_hot_springs:
            gp = np.array(self.geothermal_hot_springs)
            ax1.scatter(
                gp[:, 0],
                gp[:, 1],
                c="#f97316",
                s=110,
                marker="^",
                edgecolors="white",
                linewidths=1.2,
                label=f"Geothermal Hot Springs ({len(self.geothermal_hot_springs)})",
                zorder=6,
            )
        ax1.set_title(
            "1. Subsurface Groundwater Saturation, Darcy Flux & Springs",
            **title_style,
        )
        ax1.tick_params(colors=label_color)
        ax1.legend(
            loc="lower left",
            fontsize=8,
            facecolor="#292524",
            edgecolor="#78716c",
            labelcolor="#f5f5f4",
        )
        cbar1 = fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
        cbar1.ax.yaxis.set_tick_params(color=label_color, labelcolor=label_color)

        # Panel 2: Surface Hydraulics, Flow Velocity Vectors & Alluvial Silt Fertility
        ax2 = axes[0, 1]
        fert_arr = np.array(self.alluvial_fertility, dtype=float)
        im2 = ax2.imshow(fert_arr, cmap="YlGn", vmin=0.1, vmax=1.0)
        U_s = np.array(
            [
                [self.surface_flow_uv[y][x][0] for x in range(5, self.w - 5, step_q)]
                for y in range(5, self.h - 5, step_q)
            ]
        )
        V_s = np.array(
            [
                [self.surface_flow_uv[y][x][1] for x in range(5, self.w - 5, step_q)]
                for y in range(5, self.h - 5, step_q)
            ]
        )
        mag_s = np.hypot(U_s, V_s) + 1e-6
        U_sn = (U_s / mag_s) * np.minimum(mag_s, 0.65)
        V_sn = (V_s / mag_s) * np.minimum(mag_s, 0.65)
        ax2.quiver(
            X_q,
            Y_q,
            U_sn,
            V_sn,
            color="#0284c7",
            alpha=0.85,
            scale=8.5,
            width=0.0035,
            label="Surface Runoff & River Velocity Vector",
        )
        ax2.set_title(
            "2. Surface Hydraulics (Flow Vectors) & Alluvial Soil Fertility",
            **title_style,
        )
        ax2.tick_params(colors=label_color)
        ax2.legend(
            loc="lower left",
            fontsize=8,
            facecolor="#292524",
            edgecolor="#78716c",
            labelcolor="#f5f5f4",
        )
        cbar2 = fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
        cbar2.ax.yaxis.set_tick_params(color=label_color, labelcolor=label_color)

        # Panel 3: Winter Thermodynamics (Adiabatic Lapse Rate, Campfire & Geothermal Heat Plumes)
        ax3 = axes[0, 2]
        temp_arr = np.array(self.temp_celsius, dtype=float)
        im3 = ax3.imshow(temp_arr, cmap="coolwarm", vmin=-24.0, vmax=16.0)
        ax3.contour(
            temp_arr,
            levels=[-10.0, 0.0, 5.0],
            colors=["#38bdf8", "#ffffff", "#fb923c"],
            linewidths=1.1,
            alpha=0.8,
        )
        ax3.set_title(
            "3. Winter Thermodynamics (°C), 0°C Freeze Line & Geothermal Plumes",
            **title_style,
        )
        ax3.tick_params(colors=label_color)
        cbar3 = fig.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04)
        cbar3.ax.yaxis.set_tick_params(color=label_color, labelcolor=label_color)

        # Panel 4: Orographic Rain Shadow & Prevailing Monsoon Wind Physics
        ax4 = axes[1, 0]
        oro_arr = np.array(self.orographic_rain_factor, dtype=float)
        im4 = ax4.imshow(oro_arr, cmap="BrBG", vmin=0.5, vmax=1.5)
        ax4.set_title(
            "4. Orographic Lift (Windward Rain) vs. Foehn Rain Shadow",
            **title_style,
        )
        ax4.tick_params(colors=label_color)
        cbar4 = fig.colorbar(im4, ax=ax4, fraction=0.046, pad=0.04)
        cbar4.ax.yaxis.set_tick_params(color=label_color, labelcolor=label_color)

        # Panel 5: Dynamic Natural Disasters Map (Flash Floods, Wind-Driven Wildfire, Ice Bridges, Rockslides)
        ax5 = axes[1, 1]
        ax5.imshow(
            preview_25d,
            extent=[0, self.w, self.h, 0],
            interpolation="bilinear",
            alpha=0.82,
        )
        coords = self.disaster_events_log["_coords"]
        if coords["frozen_ice"]:
            fi = np.array(coords["frozen_ice"])
            ax5.scatter(
                fi[:, 0],
                fi[:, 1],
                c="#a5f3fc",
                s=3.5,
                alpha=0.85,
                label=f"Winter Frozen Ice Bridges ({len(fi)} tiles)",
            )
        if coords["flooded"]:
            fl = np.array(coords["flooded"])
            ax5.scatter(
                fl[:, 0],
                fl[:, 1],
                c="#3b82f6",
                s=6.0,
                alpha=0.85,
                label=f"Spring Flash-Flood Inundation ({len(fl)} tiles)",
            )
        if coords["burned"]:
            bu = np.array(coords["burned"])
            ax5.scatter(
                bu[:, 0],
                bu[:, 1],
                c="#ef4444",
                s=10.0,
                alpha=0.9,
                label=f"Summer Wind-Driven Wildfire ({len(bu)} tiles)",
            )
        if coords["rockslides"]:
            rk = np.array(coords["rockslides"])
            ax5.scatter(
                rk[:, 0],
                rk[:, 1],
                c="#facc15",
                s=28.0,
                marker="^",
                edgecolors="black",
                label=f"Cliff Rockslides / New Flint ({len(rk)} sites)",
                zorder=6,
            )
        ax5.set_title(
            "5. Natural Disasters Simulation (Flood, Wildfire, Ice & Rockslide)",
            **title_style,
        )
        ax5.tick_params(colors=label_color)
        ax5.legend(
            loc="lower left",
            fontsize=8,
            facecolor="#292524",
            edgecolor="#78716c",
            labelcolor="#f5f5f4",
        )

        # Panel 6: 4-Season Paleolithic Telemetry Comparison Chart
        ax6 = axes[1, 2]
        ax6.set_facecolor("#292524")
        s_labels = ["Spring\nThaw", "Summer\nMonsoon", "Autumn\nGale", "Winter\nIce Age"]
        s_keys = [
            SEASON_SPRING_THAW,
            SEASON_SUMMER_MONSOON,
            SEASON_AUTUMN_GALE,
            SEASON_WINTER_ICE_AGE,
        ]
        temps_mean = [
            self.seasonal_metrics[k]["mean_temperature_celsius"] for k in s_keys
        ]
        discharge_pct = [
            self.seasonal_metrics[k]["river_discharge_multiplier"] * 100.0
            for k in s_keys
        ]
        growth_pct = [
            self.seasonal_metrics[k]["flora_growth_rate_multiplier"] * 100.0
            for k in s_keys
        ]

        x_idx = np.arange(len(s_labels))
        w_bar = 0.28
        b_dis = ax6.bar(
            x_idx - w_bar / 2,
            discharge_pct,
            width=w_bar,
            color="#38bdf8",
            label="River Flow Discharge (%)",
        )
        b_gro = ax6.bar(
            x_idx + w_bar / 2,
            growth_pct,
            width=w_bar,
            color="#4ade80",
            label="Botanical Growth Rate (%)",
        )
        ax6.set_xticks(x_idx)
        ax6.set_xticklabels(s_labels, color=label_color, fontsize=9)
        ax6.set_ylabel("Index (% of Baseline)", color=label_color, fontsize=9.5)
        ax6.tick_params(colors=label_color)

        ax6_twin = ax6.twinx()
        ax6_twin.plot(
            x_idx,
            temps_mean,
            color="#f97316",
            marker="o",
            linewidth=2.5,
            label="Mean Continent Temp (°C)",
        )
        ax6_twin.set_ylabel("Mean Temperature (°C)", color="#fb923c", fontsize=9.5)
        ax6_twin.tick_params(colors="#fb923c")
        for xi, tv in zip(x_idx, temps_mean):
            ax6_twin.text(
                xi,
                tv + 1.4,
                f"{tv:+.1f}°C",
                color="#fed7aa",
                fontsize=8.5,
                fontweight="bold",
                ha="center",
            )

        ax6.set_title(
            "6. 4-Season Paleolithic Climate, Hydrology & Growth Telemetry",
            **title_style,
        )
        ax6.legend(
            loc="upper left",
            fontsize=8,
            facecolor="#1c1917",
            edgecolor="#78716c",
            labelcolor="#f5f5f4",
        )

        plt.suptitle(
            "PREHISTORIC STONE AGE RTS — SUBSURFACE GROUNDWATER, FLUID/THERMAL PHYSICS, 4-SEASON WEATHER & DISASTERS ATLAS",
            color="#fafaf9",
            fontsize=15,
            fontweight="bold",
            y=0.98,
        )
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path, dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
        return output_path


if __name__ == "__main__":
    phys_engine = StoneAgePhysicsWeatherAndDisasterEngine(generator)
    phys_summary = phys_engine.run_full_physics_and_seasonal_simulation()
    # Strip raw coordinate lists for clean console output
    clean_summary = {
        "groundwater_summary": phys_summary["groundwater_summary"],
        "seasonal_cycle_metrics": phys_summary["seasonal_cycle_metrics"],
        "natural_disasters_summary": {
            k: v
            for k, v in phys_summary["natural_disasters_summary"].items()
            if k != "_coords"
        },
    }
    print("\n=== PHYSICS, GROUNDWATER, 4-SEASON WEATHER & DISASTERS SUMMARY ===")
    print(json.dumps(clean_summary, indent=2, ensure_ascii=False))

    phys_atlas_path = os.path.join(
        output_dir, "stone_age_physics_weather_disasters_atlas.png"
    )
    phys_engine.render_physics_weather_and_disasters_atlas(
        renderer, phys_atlas_path
    )
    print(f"Saved 6-panel physics, weather & disasters atlas to: {phys_atlas_path}")