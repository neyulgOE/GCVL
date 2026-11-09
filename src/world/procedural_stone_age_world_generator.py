"""Procedural Stone Age World Generator & 2D Graphics Renderer (200x200 RTS Map).

Generates a multi-biome prehistoric continent using multi-octave gradient/value
noise for elevation, moisture, and temperature, guarantees a balanced starting
settlement basin around the map center, computes 4-bit/8-bit auto-tile bitmasks
for seamless terrain tilesets, and renders high-resolution 2D pixel-art maps
and multi-layer tactical graphics atlases via Pillow & Matplotlib.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import os
import random
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter


# Biome constants
BIOME_TUNDRA = "Tundra"
BIOME_PRIMEVAL_FOREST = "Primeval Forest"
BIOME_STEPPE_GRASSLAND = "Steppe Grassland"
BIOME_MEGALITHIC_HIGHLANDS = "Megalithic Highlands"
BIOME_ANCIENT_SWAMP = "Ancient Swamp / Mangrove"
BIOME_COASTAL_WATERS = "Coastal Waters / River Delta"

# Predators restricted from spawning inside the 25-tile starting safe zone
PREDATOR_SPAWNERS = {
    "sabertooth_tiger",
    "cave_bear",
    "dire_wolf",
    "marsh_crocodilian",
}

# Prehistoric Earthy RGB Palette for 2D Pixel-Art Rendering
BIOME_PALETTE_RGB: Dict[str, Tuple[int, int, int]] = {
    BIOME_TUNDRA: (218, 230, 238),             # Glacial ice & snow white
    BIOME_PRIMEVAL_FOREST: (46, 94, 48),       # Deep primeval fern green
    BIOME_STEPPE_GRASSLAND: (146, 168, 78),    # Fertile savanna / ochre grass
    BIOME_MEGALITHIC_HIGHLANDS: (118, 108, 98),# Rough-hewn granite gray-brown
    BIOME_ANCIENT_SWAMP: (62, 88, 68),         # Misty mangrove mud-green
    BIOME_COASTAL_WATERS: (44, 114, 148),      # Deep river & coastal water
}

RESOURCE_COLOR_RGB: Dict[str, Tuple[int, int, int]] = {
    "tree": (24, 62, 28),          # Dark canopy pine/fern
    "berries": (212, 48, 62),      # Crimson wild berries
    "flint": (68, 72, 82),         # Sharp dark flintstone node
    "bone_deposit": (238, 228, 202), # Mammoth ivory / bone deposit
    "water": (78, 168, 204),       # Shallow ford / freshwater shimmer
}


@dataclass
class WorldTile:
    """Represents a single grid tile in the prehistoric Stone Age world."""

    tile_x: int
    tile_y: int
    biome_type: str
    elevation: float
    moisture: float
    temperature: float
    walkable: bool
    resource_node: Optional[str] = None
    wildlife_spawner: Optional[str] = None
    special_feature: Optional[str] = None
    warmth_radius_active: bool = False
    autotile_mask_4bit: int = 0
    flora_species: Optional[str] = None
    growth_stage: Optional[str] = None  # "unripe_sprout", "ripe_harvestable", "depleted_foraged"
    foraging_yield: int = 0
    regrowth_ticks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultiOctaveNoise2D:
    """Self-contained 2D smooth Perlin-style gradient noise generator."""

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
        """Evaluates 2D Perlin-style gradient noise in range [-1, 1]."""
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
        base_scale: float = 0.025,
    ) -> float:
        """Evaluates contrast-stretched multi-octave Fractal Brownian Motion in [0, 1]."""
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


class ProceduralStoneAgeWorldGenerator:
    """Generates a 200x200 multi-biome Stone Age world grid with guaranteed spawn balance."""

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

        self.center_x = width // 2
        self.center_y = height // 2
        self.grid: List[List[WorldTile]] = []
        self.spawn_metadata: Dict[str, Any] = {}

    def generate_world(self) -> List[List[Dict[str, Any]]]:
        """Generates the full 200x200 world matrix and returns a 2D list of tile dicts."""
        self.grid = []

        for y in range(self.height):
            row: List[WorldTile] = []
            lat_ratio = y / max(1, self.height - 1)  # 0.0 (North) -> 1.0 (South)

            for x in range(self.width):
                lon_ratio = x / max(1, self.width - 1)  # 0.0 (West) -> 1.0 (East)

                raw_elev = self.elev_noise.fbm(
                    x, y, octaves=5, persistence=0.54, base_scale=0.024
                )
                raw_moist = self.moist_noise.fbm(
                    x, y, octaves=4, persistence=0.52, base_scale=0.026
                )
                raw_temp = self.temp_noise.fbm(
                    x, y, octaves=3, persistence=0.48, base_scale=0.022
                )

                west_highland_boost = max(0.0, (0.38 - lon_ratio) * 0.48)
                north_ridge_boost = max(0.0, (0.28 - lat_ratio) * 0.35)
                south_delta_drop = max(0.0, (lat_ratio - 0.78) * 1.35)
                east_moisture_boost = max(0.0, (lon_ratio - 0.55) * 0.45)

                elevation = max(
                    0.0,
                    min(
                        1.0,
                        raw_elev
                        + west_highland_boost
                        + north_ridge_boost
                        - south_delta_drop,
                    ),
                )
                moisture = max(
                    0.0,
                    min(
                        1.0,
                        raw_moist
                        + east_moisture_boost
                        - west_highland_boost * 0.65
                        + south_delta_drop * 0.30,
                    ),
                )
                temperature = max(
                    0.0, min(1.0, 0.72 * lat_ratio + 0.28 * raw_temp)
                )

                biome = self._classify_biome(elevation, moisture, temperature)
                walkable = self._is_biome_walkable(biome, elevation)
                dist_from_center = math.hypot(x - self.center_x, y - self.center_y)
                (
                    resource_node,
                    wildlife_spawner,
                    flora_species,
                    growth_stage,
                    foraging_yield,
                    regrowth_ticks,
                ) = self._populate_tile_contents(biome, walkable, dist_from_center)

                tile = WorldTile(
                    tile_x=x,
                    tile_y=y,
                    biome_type=biome,
                    elevation=round(elevation, 4),
                    moisture=round(moisture, 4),
                    temperature=round(temperature, 4),
                    walkable=walkable,
                    resource_node=resource_node,
                    wildlife_spawner=wildlife_spawner,
                    flora_species=flora_species,
                    growth_stage=growth_stage,
                    foraging_yield=foraging_yield,
                    regrowth_ticks=regrowth_ticks,
                )
                row.append(tile)
            self.grid.append(row)

        self._carve_primal_river()
        self._apply_starting_basin_guarantees()
        self.compute_autotile_bitmasks()

        return [[tile.to_dict() for tile in row] for row in self.grid]

    @staticmethod
    def _classify_biome(
        elevation: float, moisture: float, temperature: float
    ) -> str:
        """Maps (elevation, moisture, temperature) into 6 prehistoric Stone Age biomes."""
        if elevation < 0.26:
            return BIOME_COASTAL_WATERS
        if elevation < 0.44 and moisture >= 0.62:
            return BIOME_ANCIENT_SWAMP
        if temperature < 0.34 and elevation >= 0.48:
            return BIOME_TUNDRA
        if elevation >= 0.64 and moisture < 0.52:
            return BIOME_MEGALITHIC_HIGHLANDS
        if elevation >= 0.72:
            return BIOME_TUNDRA if temperature < 0.50 else BIOME_MEGALITHIC_HIGHLANDS
        if moisture >= 0.54:
            return BIOME_PRIMEVAL_FOREST
        return BIOME_STEPPE_GRASSLAND

    @staticmethod
    def _is_biome_walkable(biome: str, elevation: float) -> bool:
        """Determines base walkability before resource boulder/cliff placement."""
        if biome == BIOME_COASTAL_WATERS:
            return elevation >= 0.22
        if biome == BIOME_MEGALITHIC_HIGHLANDS and elevation > 0.85:
            return False
        return True

    def _populate_tile_contents(
        self, biome: str, walkable: bool, dist_from_center: float
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], int, int]:
        """Assigns biome-specific resource nodes, botanical species, growth stages, and wildlife spawners."""
        resource_node: Optional[str] = None
        wildlife_spawner: Optional[str] = None
        flora_species: Optional[str] = None
        growth_stage: Optional[str] = None
        foraging_yield: int = 0
        regrowth_ticks: int = 0

        in_safe_zone = dist_from_center <= self.safe_buffer_radius
        roll_res = self.rng.random()
        roll_mob = self.rng.random()

        if biome == BIOME_TUNDRA:
            if walkable:
                if roll_res < 0.035:
                    resource_node = "flint"
                elif roll_res < 0.060:
                    resource_node = "bone_deposit"
                elif roll_res < 0.090:
                    resource_node = "tree"
                    flora_species = self.rng.choice(["tundra_spruce", "krummholz_dwarf_pine", "frost_white_birch"])
                elif roll_res < 0.115:
                    resource_node = "berries"
                    flora_species = "golden_arctic_cloudberries"
                elif roll_res < 0.135:
                    resource_node = "roots_tubers"
                    flora_species = "frost_hardy_root_tuber"
                elif roll_res < 0.150:
                    resource_node = "medicinal_herb"
                    flora_species = "arctic_reindeer_moss"

                if roll_mob < 0.014:
                    wildlife_spawner = "woolly_mammoth"
                elif not in_safe_zone and roll_mob < 0.022:
                    wildlife_spawner = "dire_wolf"

        elif biome == BIOME_PRIMEVAL_FOREST:
            if walkable:
                if roll_res < 0.200:
                    resource_node = "tree"
                    flora_species = self.rng.choice(["giant_tree_fern", "araucaria_monkey_pine", "cycad"])
                elif roll_res < 0.245:
                    resource_node = "berries"
                    flora_species = "crimson_bramble_berries"
                elif roll_res < 0.275:
                    resource_node = "mushrooms"
                    flora_species = "king_spotted_mushrooms"
                elif roll_res < 0.300:
                    resource_node = "medicinal_herb"
                    flora_species = "healing_red_herb"
                elif roll_res < 0.320:
                    resource_node = "roots_tubers"
                    flora_species = "wild_taro_tubers"

                if roll_mob < 0.018:
                    wildlife_spawner = "wild_boar"
                elif not in_safe_zone and roll_mob < 0.024:
                    wildlife_spawner = "sabertooth_tiger"

        elif biome == BIOME_STEPPE_GRASSLAND:
            if walkable:
                if roll_res < 0.038:
                    resource_node = "berries"
                    flora_species = "crimson_bramble_berries"
                elif roll_res < 0.070:
                    resource_node = "tree"
                    flora_species = self.rng.choice(["ancient_gnarled_oak", "steppe_ginkgo"])
                elif roll_res < 0.090:
                    resource_node = "wild_grain"
                    flora_species = "einkorn_wild_grain"
                elif roll_res < 0.110:
                    resource_node = "fiber_plant"
                    flora_species = "wild_flax_fiber_plant"
                elif roll_res < 0.130:
                    resource_node = "roots_tubers"
                    flora_species = "burdock_starchy_roots"
                elif roll_res < 0.145:
                    resource_node = "flint"

                if roll_mob < 0.020:
                    wildlife_spawner = "ancient_bison"

        elif biome == BIOME_MEGALITHIC_HIGHLANDS:
            if walkable:
                if roll_res < 0.080:
                    resource_node = "flint"
                elif roll_res < 0.125:
                    resource_node = "bone_deposit"
                elif roll_res < 0.155:
                    resource_node = "tree"
                    flora_species = "resin_pine"
                elif roll_res < 0.175:
                    resource_node = "roots_tubers"
                    flora_species = "burdock_starchy_roots"
                elif roll_res < 0.190:
                    resource_node = "mushrooms"
                    flora_species = "glowing_blue_cave_fungi"
                elif roll_res < 0.205:
                    resource_node = "medicinal_herb"
                    flora_species = "mountain_ephedra_herb"

                if not in_safe_zone and roll_mob < 0.022:
                    wildlife_spawner = "sabertooth_tiger"
                elif not in_safe_zone and roll_mob < 0.032:
                    wildlife_spawner = "cave_bear"

        elif biome == BIOME_ANCIENT_SWAMP:
            if roll_res < 0.100:
                resource_node = "water"
            elif roll_res < 0.150:
                resource_node = "tree"
                flora_species = self.rng.choice(["aerial_root_mangrove", "mossy_swamp_cypress"])
            elif roll_res < 0.185:
                resource_node = "berries"
                flora_species = "dark_swamp_elderberries"
            elif roll_res < 0.215:
                resource_node = "fiber_plant"
                flora_species = "riverbank_cattail_reeds"
            elif roll_res < 0.235:
                resource_node = "mushrooms"
                flora_species = "bioluminescent_marsh_fungi"
            elif roll_res < 0.250:
                resource_node = "medicinal_herb"
                flora_species = "willow_bark_pain_herb"

            if not in_safe_zone and roll_mob < 0.015:
                wildlife_spawner = "marsh_crocodilian"

        elif biome == BIOME_COASTAL_WATERS:
            resource_node = "water"
            if roll_res < 0.050:
                resource_node = "roots_tubers"
                flora_species = "tidal_edible_kelp"
            elif roll_res < 0.080:
                resource_node = "fiber_plant"
                flora_species = "delta_cattail_reeds"

            if roll_mob < 0.045:
                wildlife_spawner = "fish_shoal"

        # Botanical 3-stage lifecycle calculation
        if resource_node in ["tree", "berries", "roots_tubers", "fiber_plant", "medicinal_herb", "mushrooms", "wild_grain"]:
            roll_stage = self.rng.random()
            if roll_stage < 0.70:
                growth_stage = "ripe_harvestable"
                yield_mult = 1.0
                regrowth_ticks = 0
            elif roll_stage < 0.90:
                growth_stage = "unripe_sprout"
                yield_mult = 0.35
                regrowth_ticks = 25
            else:
                growth_stage = "depleted_foraged"
                yield_mult = 0.0
                regrowth_ticks = 80

            base_yield_map = {
                "tree": 50,
                "berries": 15,
                "roots_tubers": 20,
                "fiber_plant": 12,
                "medicinal_herb": 8,
                "mushrooms": 10,
                "wild_grain": 18
            }
            foraging_yield = int(base_yield_map.get(resource_node, 10) * yield_mult)

        return resource_node, wildlife_spawner, flora_species, growth_stage, foraging_yield, regrowth_ticks

    def _carve_primal_river(self) -> None:
        """Carves a winding freshwater river passing near the central settlement basin."""
        river_x = float(self.center_x + 7)
        for y in range(self.height):
            meander = math.sin(y * 0.09) * 4.5 + math.cos(y * 0.04) * 2.5
            cx = int(round(river_x + meander))
            for dx in (-1, 0, 1):
                rx = max(0, min(self.width - 1, cx + dx))
                tile = self.grid[y][rx]
                tile.biome_type = BIOME_COASTAL_WATERS
                tile.moisture = 1.0
                tile.resource_node = "water"
                if abs(y - self.center_y) <= 3 or dx != 0:
                    tile.elevation = 0.24
                    tile.walkable = True
                else:
                    tile.elevation = 0.18
                    tile.walkable = False
                if tile.wildlife_spawner in PREDATOR_SPAWNERS:
                    tile.wildlife_spawner = None

            # Seed riverbank cattail reeds along walkable river banks
            for bank_dx in (-2, 2):
                bx = max(0, min(self.width - 1, cx + bank_dx))
                btile = self.grid[y][bx]
                if btile.walkable and btile.biome_type != BIOME_COASTAL_WATERS:
                    if self.rng.random() < 0.40:
                        btile.resource_node = "fiber_plant"
                        btile.flora_species = "riverbank_cattail_reeds"
                        btile.growth_stage = "ripe_harvestable"
                        btile.foraging_yield = 12

    def _apply_starting_basin_guarantees(self) -> None:
        """Enforces all starting settlement rules around (center_x, center_y)."""
        cx, cy = self.center_x, self.center_y
        basin_radius = 10

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

                if dist <= self.safe_buffer_radius:
                    if tile.wildlife_spawner in PREDATOR_SPAWNERS:
                        tile.wildlife_spawner = None

                if dist <= basin_radius and tile.biome_type != BIOME_COASTAL_WATERS:
                    tile.biome_type = BIOME_STEPPE_GRASSLAND
                    tile.elevation = 0.48
                    tile.moisture = 0.50
                    tile.walkable = True

        shelter_pos = (cx, cy - 2)
        shelter_tile = self.grid[shelter_pos[1]][shelter_pos[0]]
        shelter_tile.special_feature = "Ancestral Rock Shelter (Hang Đá Cội Nguồn)"
        shelter_tile.resource_node = None
        shelter_tile.walkable = True

        campfire_pos = (cx, cy)
        campfire_tile = self.grid[campfire_pos[1]][campfire_pos[0]]
        campfire_tile.special_feature = "Active Campfire Hearth"
        campfire_tile.resource_node = None
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

        # Guaranteed starting botanical foraging garden around (cx, cy):
        # 1. 4 berry bushes (crimson_bramble_berries)
        berry_offsets = [(-4, -1), (-3, 2), (-5, 1), (2, -3)]
        for bx, by in berry_offsets:
            t = self.grid[cy + by][cx + bx]
            t.resource_node = "berries"
            t.flora_species = "crimson_bramble_berries"
            t.growth_stage = "ripe_harvestable"
            t.foraging_yield = 15
            t.walkable = True

        # 2. 3 wild grains (einkorn_wild_grain)
        grain_offsets = [(-3, -2), (-2, -3), (-1, -4)]
        for gx, gy in grain_offsets:
            t = self.grid[cy + gy][cx + gx]
            t.resource_node = "wild_grain"
            t.flora_species = "einkorn_wild_grain"
            t.growth_stage = "ripe_harvestable"
            t.foraging_yield = 18
            t.walkable = True

        # 3. 2 starchy roots/tubers (burdock_starchy_roots)
        tuber_offsets = [(1, 3), (2, 4)]
        for rx, ry in tuber_offsets:
            t = self.grid[cy + ry][cx + rx]
            t.resource_node = "roots_tubers"
            t.flora_species = "burdock_starchy_roots"
            t.growth_stage = "ripe_harvestable"
            t.foraging_yield = 20
            t.walkable = True

        # 4. 2 riverbank cattail reeds (riverbank_cattail_reeds)
        reed_offsets = [(5, -1), (6, 0)]
        for cax, cay in reed_offsets:
            t = self.grid[cy + cay][cx + cax]
            t.resource_node = "fiber_plant"
            t.flora_species = "riverbank_cattail_reeds"
            t.growth_stage = "ripe_harvestable"
            t.foraging_yield = 12
            t.walkable = True

        # 5. 2 healing herbs (healing_red_herb)
        herb_offsets = [(1, -2), (3, -1)]
        for hx, hy in herb_offsets:
            t = self.grid[cy + hy][cx + hx]
            t.resource_node = "medicinal_herb"
            t.flora_species = "healing_red_herb"
            t.growth_stage = "ripe_harvestable"
            t.foraging_yield = 8
            t.walkable = True

        # 6. 2 forest mushrooms (king_spotted_mushrooms)
        mush_offsets = [(-2, 3), (-4, 4)]
        for mx, my in mush_offsets:
            t = self.grid[cy + my][cx + mx]
            t.resource_node = "mushrooms"
            t.flora_species = "king_spotted_mushrooms"
            t.growth_stage = "ripe_harvestable"
            t.foraging_yield = 10
            t.walkable = True

        flint_offsets = [(-4, -4), (3, -4), (-2, -5)]
        pond_offsets = [(4, 2), (5, 2), (4, 3)]
        tree_offsets = [(-6, -2), (-6, 3), (2, 5)]

        for fx, fy in flint_offsets:
            t = self.grid[cy + fy][cx + fx]
            t.resource_node = "flint"
            t.walkable = True

        for px, py in pond_offsets:
            t = self.grid[cy + py][cx + px]
            t.resource_node = "water"
            t.moisture = 0.95
            t.walkable = True

        for tx, ty in tree_offsets:
            t = self.grid[cy + ty][cx + tx]
            t.resource_node = "tree"
            t.walkable = True

        bison_tile = self.grid[cy + 5][cx - 4]
        bison_tile.wildlife_spawner = "ancient_bison"

        self.spawn_metadata = {
            "ancestral_rock_shelter": {"x": shelter_pos[0], "y": shelter_pos[1]},
            "active_campfire": {
                "x": campfire_pos[0],
                "y": campfire_pos[1],
                "warmth_radius": self.campfire_warmth_radius,
                "warm_tiles_count": warm_tiles_count,
            },
            "safe_buffer_radius": self.safe_buffer_radius,
            "guaranteed_berry_nodes": len(berry_offsets),
            "guaranteed_flint_nodes": len(flint_offsets),
            "guaranteed_water_nodes": len(pond_offsets),
        }

    def compute_autotile_bitmasks(self) -> None:
        """Computes a 4-bit NESW auto-tile bitmask (0..15) per tile for seamless tileset rendering."""
        for y in range(self.height):
            for x in range(self.width):
                tile = self.grid[y][x]
                b = tile.biome_type
                mask = 0
                if y > 0 and self.grid[y - 1][x].biome_type == b:
                    mask |= 1
                if x < self.width - 1 and self.grid[y][x + 1].biome_type == b:
                    mask |= 2
                if y < self.height - 1 and self.grid[y + 1][x].biome_type == b:
                    mask |= 4
                if x > 0 and self.grid[y][x - 1].biome_type == b:
                    mask |= 8
                tile.autotile_mask_4bit = mask

    def render_ascii_preview(
        self, downsample_step: int = 4, show_spawn_zoom: bool = True
    ) -> str:
        """Generates a fast ASCII visualization of the 200x200 world and a 1:1 zoom of the starting basin."""
        biome_chars = {
            BIOME_TUNDRA: "^",
            BIOME_PRIMEVAL_FOREST: "T",
            BIOME_STEPPE_GRASSLAND: ".",
            BIOME_MEGALITHIC_HIGHLANDS: "M",
            BIOME_ANCIENT_SWAMP: "%",
            BIOME_COASTAL_WATERS: "~",
        }

        lines: List[str] = []
        lines.append(
            f"=== PREHISTORIC STONE AGE OVERWORLD MAP ({self.width}x{self.height}, Seed={self.seed}) ==="
        )
        lines.append(
            "Legend: [^] Tundra  [T] Primeval Forest  [.] Steppe Grassland  "
            "[M] Megalithic Highlands  [%] Ancient Swamp  [~] Water/Delta  [@] Spawn Basin"
        )
        lines.append("+" + "-" * (self.width // downsample_step) + "+")

        for y in range(0, self.height, downsample_step):
            row_chars: List[str] = []
            for x in range(0, self.width, downsample_step):
                if (
                    abs(x - self.center_x) < downsample_step
                    and abs(y - self.center_y) < downsample_step
                ):
                    row_chars.append("@")
                else:
                    tile = self.grid[y][x]
                    row_chars.append(biome_chars.get(tile.biome_type, "?"))
            lines.append("|" + "".join(row_chars) + "|")

        lines.append("+" + "-" * (self.width // downsample_step) + "+")

        if show_spawn_zoom:
            zoom_r = 10
            lines.append("")
            lines.append(
                f"=== STARTING SETTLEMENT BASIN (1:1 TILE ZOOM AROUND {self.center_x},{self.center_y}) ==="
            )
            lines.append(
                "Legend: [H] Ancestral Rock Shelter  [*] Campfire Hearth  [B] Berries  "
                "[F] Flint  [W] Freshwater  [t] Tree  [b] Bison  [.] Warm Steppe"
            )
            lines.append("+" + "-" * (zoom_r * 2 + 1) + "+")
            for y in range(self.center_y - zoom_r, self.center_y + zoom_r + 1):
                zoom_row: List[str] = []
                for x in range(self.center_x - zoom_r, self.center_x + zoom_r + 1):
                    t = self.grid[y][x]
                    if t.special_feature and "Shelter" in t.special_feature:
                        zoom_row.append("H")
                    elif t.special_feature and "Campfire" in t.special_feature:
                        zoom_row.append("*")
                    elif t.resource_node == "berries":
                        zoom_row.append("B")
                    elif t.resource_node == "flint":
                        zoom_row.append("F")
                    elif t.resource_node == "water":
                        zoom_row.append("W")
                    elif t.resource_node == "tree":
                        zoom_row.append("t")
                    elif t.wildlife_spawner == "ancient_bison":
                        zoom_row.append("b")
                    elif t.warmth_radius_active:
                        zoom_row.append(".")
                    else:
                        zoom_row.append(biome_chars.get(t.biome_type, " "))
                lines.append("|" + "".join(zoom_row) + "|")
            lines.append("+" + "-" * (zoom_r * 2 + 1) + "+")

        return "\n".join(lines)

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Computes biome distribution, resource counts, botanical flora, and safety verification metrics."""
        biome_counts: Dict[str, int] = {}
        resource_counts: Dict[str, int] = {}
        flora_counts: Dict[str, int] = {}
        stage_counts: Dict[str, int] = {}
        wildlife_counts: Dict[str, int] = {}
        predators_in_safe_zone = 0

        for row in self.grid:
            for tile in row:
                biome_counts[tile.biome_type] = (
                    biome_counts.get(tile.biome_type, 0) + 1
                )
                if tile.resource_node:
                    resource_counts[tile.resource_node] = (
                        resource_counts.get(tile.resource_node, 0) + 1
                    )
                if tile.flora_species:
                    flora_counts[tile.flora_species] = (
                        flora_counts.get(tile.flora_species, 0) + 1
                    )
                if tile.growth_stage:
                    stage_counts[tile.growth_stage] = (
                        stage_counts.get(tile.growth_stage, 0) + 1
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
            "total_tiles": self.width * self.height,
            "biome_distribution": biome_counts,
            "resource_node_counts": resource_counts,
            "flora_species_counts": flora_counts,
            "botanical_growth_stages": stage_counts,
            "wildlife_spawner_counts": wildlife_counts,
            "spawn_basin_metadata": self.spawn_metadata,
            "predators_within_25_tile_safe_zone": predators_in_safe_zone,
        }

    def export_to_json(self, filepath: str, include_full_grid: bool = True) -> None:
        """Exports the world metadata and optional 200x200 tile grid to a JSON file."""
        payload: Dict[str, Any] = {
            "metadata": self.get_summary_statistics(),
        }
        if include_full_grid:
            payload["grid"] = [
                [tile.to_dict() for tile in row] for row in self.grid
            ]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


class StoneAgeGraphicsRenderer:
    """Renders 2D pixel-art overworld maps, spawn basin zooms, and tactical atlases."""

    def __init__(self, generator: ProceduralStoneAgeWorldGenerator) -> None:
        self.gen = generator
        if not self.gen.grid:
            self.gen.generate_world()

    def render_pixel_art_overworld(
        self, tile_scale: int = 4, apply_fog_of_war: bool = True
    ) -> Image.Image:
        """Renders the 200x200 world into a crisp 2D pixel-art image with hillshading and campfire glow."""
        w, h = self.gen.width, self.gen.height
        base_img = Image.new("RGB", (w, h))
        pixels = base_img.load()

        cx, cy = self.gen.center_x, self.gen.center_y
        max_dist = math.hypot(cx, cy)

        for y in range(h):
            for x in range(w):
                tile = self.gen.grid[y][x]
                r, g, b = BIOME_PALETTE_RGB.get(tile.biome_type, (128, 128, 128))

                # Directional NW hillshading based on neighbor elevation slope
                elev_nw = (
                    self.gen.grid[y - 1][x - 1].elevation
                    if (x > 0 and y > 0)
                    else tile.elevation
                )
                slope = (tile.elevation - elev_nw) * 180.0
                shade = int(max(-35.0, min(35.0, slope)))

                # Auto-tile border darkening for cliff/shore transitions
                if tile.autotile_mask_4bit != 15:
                    if tile.biome_type == BIOME_COASTAL_WATERS:
                        shade += 22
                    elif tile.biome_type == BIOME_MEGALITHIC_HIGHLANDS:
                        shade -= 18

                r = max(0, min(255, r + shade))
                g = max(0, min(255, g + shade))
                b = max(0, min(255, b + shade))

                # Overlay resource nodes
                if tile.resource_node in RESOURCE_COLOR_RGB and (
                    tile.biome_type != BIOME_COASTAL_WATERS
                    or tile.resource_node != "water"
                ):
                    rr, rg, rb = RESOURCE_COLOR_RGB[tile.resource_node]
                    r = int(r * 0.35 + rr * 0.65)
                    g = int(g * 0.35 + rg * 0.65)
                    b = int(b * 0.35 + rb * 0.65)

                # Warm campfire amber glow inside 6-tile hearth radius
                if tile.warmth_radius_active:
                    dist_c = math.hypot(x - cx, y - cy)
                    glow = max(
                        0.0,
                        1.0 - (dist_c / (self.gen.campfire_warmth_radius + 1.0)),
                    )
                    r = min(255, int(r + 95 * glow))
                    g = min(255, int(g + 48 * glow))
                    b = max(0, int(b - 20 * glow))

                # Highlight Ancestral Rock Shelter & Campfire Hearth
                if tile.special_feature:
                    if "Shelter" in tile.special_feature:
                        r, g, b = (245, 220, 150)
                    elif "Campfire" in tile.special_feature:
                        r, g, b = (255, 92, 24)

                # Soft tribal fog-of-war near outer continent borders
                if apply_fog_of_war:
                    dist_edge = math.hypot(x - cx, y - cy) / max_dist
                    if dist_edge > 0.78:
                        fog = min(0.82, (dist_edge - 0.78) / 0.22 * 0.82)
                        r = int(r * (1.0 - fog) + 18 * fog)
                        g = int(g * (1.0 - fog) + 16 * fog)
                        b = int(b * (1.0 - fog) + 22 * fog)

                pixels[x, y] = (r, g, b)

        upscaled = base_img.resize(
            (w * tile_scale, h * tile_scale), resample=Image.Resampling.NEAREST
        )
        return upscaled

    def render_tactical_atlas(self, output_path: str) -> str:
        """Renders a 4-panel high-resolution graphic dashboard of the generated Stone Age world."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
        import numpy as np

        overworld_img = self.render_pixel_art_overworld(
            tile_scale=4, apply_fog_of_war=True
        )
        elev_arr = np.array(
            [[t.elevation for t in row] for row in self.gen.grid], dtype=float
        )
        moist_arr = np.array(
            [[t.moisture for t in row] for row in self.gen.grid], dtype=float
        )

        fig, axes = plt.subplots(2, 2, figsize=(16, 15), dpi=150)
        fig.patch.set_facecolor("#1c1917")

        title_style = {
            "color": "#f5f5f4",
            "fontsize": 13,
            "fontweight": "bold",
            "pad": 10,
        }
        label_color = "#d6d3d1"

        # Panel 1: 2D Pixel-Art Overworld Map + Safe Zone Ring
        ax1 = axes[0, 0]
        ax1.imshow(
            overworld_img,
            extent=[0, self.gen.width, self.gen.height, 0],
            interpolation="nearest",
        )
        safe_circle = plt.Circle(
            (self.gen.center_x, self.gen.center_y),
            self.gen.safe_buffer_radius,
            color="#facc15",
            fill=False,
            linestyle="--",
            linewidth=1.8,
            label="25-Tile Predator-Free Safe Zone",
        )
        warm_circle = plt.Circle(
            (self.gen.center_x, self.gen.center_y),
            self.gen.campfire_warmth_radius,
            color="#fb923c",
            fill=False,
            linestyle="-",
            linewidth=1.8,
            label="6-Tile Campfire Warmth Radius",
        )
        ax1.add_patch(safe_circle)
        ax1.add_patch(warm_circle)
        ax1.set_title(
            "1. Prehistoric Overworld Pixel-Art Map (200x200 Tiles)", **title_style
        )
        ax1.tick_params(colors=label_color)

        legend_patches = [
            mpatches.Patch(
                color=tuple(c / 255.0 for c in rgb), label=biome_name
            )
            for biome_name, rgb in BIOME_PALETTE_RGB.items()
        ]
        ax1.legend(
            handles=legend_patches,
            loc="lower left",
            fontsize=8,
            facecolor="#292524",
            edgecolor="#78716c",
            labelcolor="#f5f5f4",
        )

        # Panel 2: 1:1 Tactical Zoom of Starting Settlement Basin (Radius 16 around 100,100)
        ax2 = axes[0, 1]
        zoom_r = 16
        c_x, c_y = self.gen.center_x, self.gen.center_y
        scale = 4
        crop_box = (
            (c_x - zoom_r) * scale,
            (c_y - zoom_r) * scale,
            (c_x + zoom_r + 1) * scale,
            (c_y + zoom_r + 1) * scale,
        )
        zoom_img = overworld_img.crop(crop_box)
        ax2.imshow(
            zoom_img,
            extent=[
                c_x - zoom_r - 0.5,
                c_x + zoom_r + 0.5,
                c_y + zoom_r + 0.5,
                c_y - zoom_r - 0.5,
            ],
            interpolation="nearest",
        )

        # Annotate key starting features
        for y in range(c_y - zoom_r, c_y + zoom_r + 1):
            for x in range(c_x - zoom_r, c_x + zoom_r + 1):
                t = self.gen.grid[y][x]
                if t.special_feature and "Shelter" in t.special_feature:
                    ax2.scatter(
                        x, y, c="#fde047", s=140, marker="^", edgecolors="black", zorder=5
                    )
                    ax2.text(
                        x + 0.6,
                        y - 0.4,
                        "Rock Shelter",
                        color="#fef08a",
                        fontsize=8.5,
                        fontweight="bold",
                    )
                elif t.special_feature and "Campfire" in t.special_feature:
                    ax2.scatter(
                        x, y, c="#ef4444", s=130, marker="*", edgecolors="white", zorder=5
                    )
                    ax2.text(
                        x + 0.6,
                        y + 0.5,
                        "Campfire (R=6)",
                        color="#fed7aa",
                        fontsize=8.5,
                        fontweight="bold",
                    )
                elif t.resource_node == "berries":
                    ax2.scatter(
                        x, y, c="#f43f5e", s=45, marker="o", edgecolors="white", zorder=4
                    )
                elif t.resource_node == "flint":
                    ax2.scatter(
                        x, y, c="#94a3b8", s=50, marker="s", edgecolors="black", zorder=4
                    )
                elif t.wildlife_spawner == "ancient_bison":
                    ax2.scatter(
                        x, y, c="#d97706", s=70, marker="D", edgecolors="white", zorder=4
                    )

        warm_zoom = plt.Circle(
            (c_x, c_y),
            self.gen.campfire_warmth_radius,
            color="#fb923c",
            fill=False,
            linestyle="--",
            linewidth=2.0,
        )
        ax2.add_patch(warm_zoom)
        ax2.set_title(
            "2. Starting Settlement Basin (1:1 Tactical Zoom around 100,100)",
            **title_style,
        )
        ax2.tick_params(colors=label_color)

        # Panel 3: Topographic Elevation & Contour Relief Map
        ax3 = axes[1, 0]
        im3 = ax3.imshow(elev_arr, cmap="terrain", vmin=0.0, vmax=1.0)
        ax3.contour(
            elev_arr,
            levels=[0.26, 0.44, 0.64, 0.78],
            colors="black",
            alpha=0.35,
            linewidths=0.7,
        )
        ax3.set_title(
            "3. Multi-Octave FBM Elevation & Topographic Contours", **title_style
        )
        ax3.tick_params(colors=label_color)
        cbar3 = fig.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04)
        cbar3.ax.yaxis.set_tick_params(color=label_color, labelcolor=label_color)

        # Panel 4: Moisture & Predator Distribution Map
        ax4 = axes[1, 1]
        im4 = ax4.imshow(moist_arr, cmap="YlGnBu", vmin=0.0, vmax=1.0)
        pred_x, pred_y = [], []
        prey_x, prey_y = [], []
        for row in self.gen.grid:
            for t in row:
                if t.wildlife_spawner in PREDATOR_SPAWNERS:
                    pred_x.append(t.tile_x)
                    pred_y.append(t.tile_y)
                elif t.wildlife_spawner:
                    prey_x.append(t.tile_x)
                    prey_y.append(t.tile_y)

        ax4.scatter(
            prey_x,
            prey_y,
            c="#22c55e",
            s=8,
            alpha=0.75,
            label=f"Prey Spawners ({len(prey_x)})",
        )
        ax4.scatter(
            pred_x,
            pred_y,
            c="#ef4444",
            s=12,
            alpha=0.85,
            marker="x",
            label=f"Predator Spawners ({len(pred_x)})",
        )
        safe_circle_4 = plt.Circle(
            (c_x, c_y),
            self.gen.safe_buffer_radius,
            color="#ef4444",
            fill=False,
            linestyle="--",
            linewidth=2.0,
            label="25-Tile Safe Buffer (0 Predators)",
        )
        ax4.add_patch(safe_circle_4)
        ax4.set_title(
            "4. Hydrology Moisture Map & Wildlife / Predator Spawners",
            **title_style,
        )
        ax4.tick_params(colors=label_color)
        ax4.legend(
            loc="lower left",
            fontsize=8.5,
            facecolor="#292524",
            edgecolor="#78716c",
            labelcolor="#f5f5f4",
        )
        cbar4 = fig.colorbar(im4, ax=ax4, fraction=0.046, pad=0.04)
        cbar4.ax.yaxis.set_tick_params(color=label_color, labelcolor=label_color)

        plt.suptitle(
            "PREHISTORIC STONE AGE RTS — PROCEDURAL WORLD & GRAPHICS ATLAS (SEED 2026)",
            color="#fafaf9",
            fontsize=16,
            fontweight="bold",
            y=0.98,
        )

class StoneAgeMappingAndPathfinder:
    """
    Hệ thống Mapping, Sương Mù Chiến Tranh (Fog-of-War), Dò Đường Mù (Blind Pathfinding) & Mở Đường (Trailblazing).
    1. Sương mù 3 Trạng thái & Line-of-Sight Raycasting (cast_vision_los, reset_active_los_to_memory)
       - 0 = Unexplored Shroud (đen đặc)
       - 1 = Explored Memory Fog (xám lam bán trong suốt)
       - 2 = Visible LoS (nhìn thấy trực tiếp)
       - Tán rừng rậm ('tree') làm giảm 36% tầm nhìn mỗi ô (power *= 0.64).
       - Vách đá cao (elevation_diff > 0.16) chặn tia nhìn.
       - Đứng trên đồi cao (elevation >= 0.62) được cộng thêm +3 ô tầm nhìn.
    2. Dò đường mù & Cảm biến âm thanh (Blind Pathfinding)
       - blind_explore_to_target() & _optimistic_astar_on_known_map()
       - Trinh sát chỉ biết địa hình vùng đã mở (state 1, 2) và giả định vùng mù (state 0) có chi phí 1.15.
       - Mỗi bước tiến, Trinh sát chiếu nón tầm nhìn 55° half-angle.
       - Lắng nghe tiếng gầm thú dữ/dấu chân trong bán kính acoustic_sense_radius = 18 ô.
       - Tự động bẻ lái định tuyến lại (dynamic_replans) và dựng cột đá stone_cairn mỗi 14 bước.
    3. Chế độ Mở đường & Bắc cầu (Trailblazing Mode)
       - trailblaze_and_build_road()
       - Phát quang cây rừng thành đường mòn (cleared_forest_trail)
       - Lát gỗ qua đầm lầy (corduroy_log_causeway)
       - Bắc cầu gỗ qua sông (river_log_bridge)
       - Khắc mũi tên lên cây (blaze_tree_arrow)
       - Giảm chi phí di chuyển xuống 0.55/ô (tiết kiệm 38% - 48% thời gian hành quân).
    """

    def __init__(self, generator: ProceduralStoneAgeWorldGenerator) -> None:
        self.gen = generator
        if not self.gen.grid:
            self.gen.generate_world()
        self.width = self.gen.width
        self.height = self.gen.height
        # 0 = Unexplored, 1 = Explored Memory, 2 = Visible LoS
        self.fow_grid: List[List[int]] = [
            [0 for _ in range(self.width)] for _ in range(self.height)
        ]
        self.road_tiles: Dict[Tuple[int, int], str] = {}
        self.cairn_markers: Set[Tuple[int, int]] = set()

        # Reveal starting sanctuary basin permanently
        cx, cy = self.gen.center_x, self.gen.center_y
        self.cast_vision_los(cx, cy, max_radius=12)

    def reset_active_los_to_memory(self) -> None:
        """Degrades all currently Visible (2) tiles to Explored Memory Fog (1)."""
        for y in range(self.height):
            for x in range(self.width):
                if self.fow_grid[y][x] == 2:
                    self.fow_grid[y][x] = 1

    def cast_vision_los(
        self,
        center_x: int,
        center_y: int,
        max_radius: int = 10,
        facing_rad: Optional[float] = None,
        half_angle_rad: Optional[float] = None,
    ) -> Set[Tuple[int, int]]:
        """
        Casts line-of-sight rays from (center_x, center_y).
        - Forest canopy ('tree') attenuates vision by 36% per tile (factor 0.64).
        - High cliffs (elevation_diff > 0.16) block line-of-sight completely.
        - High hill (elevation >= 0.62) adds +3 bonus vision radius.
        - If facing_rad and half_angle_rad are provided, casts within directional vision cone.
        """
        origin_tile = self.gen.grid[center_y][center_x]
        effective_radius = max_radius + (3 if origin_tile.elevation >= 0.62 else 0)
        revealed_tiles: Set[Tuple[int, int]] = set()

        # Cast rays in circle perimeter
        ray_count = int(effective_radius * 8)
        for i in range(ray_count):
            angle = (2.0 * math.pi * i) / ray_count

            # Check vision cone angle restriction
            if facing_rad is not None and half_angle_rad is not None:
                diff = abs((angle - facing_rad + math.pi) % (2.0 * math.pi) - math.pi)
                if diff > half_angle_rad:
                    continue

            dx = math.cos(angle)
            dy = math.sin(angle)

            power = 1.0
            prev_elev = origin_tile.elevation

            for step in range(effective_radius + 1):
                cur_x = int(round(center_x + dx * step))
                cur_y = int(round(center_y + dy * step))

                if not (0 <= cur_x < self.width and 0 <= cur_y < self.height):
                    break

                target = self.gen.grid[cur_y][cur_x]

                # Steep cliff blockage
                if target.elevation - prev_elev > 0.16 and step > 1:
                    self.fow_grid[cur_y][cur_x] = max(self.fow_grid[cur_y][cur_x], 2)
                    revealed_tiles.add((cur_x, cur_y))
                    break

                # Mark visible
                self.fow_grid[cur_y][cur_x] = 2
                revealed_tiles.add((cur_x, cur_y))

                # Dense tree canopy attenuation (36% reduction)
                if target.resource_node == "tree":
                    power *= 0.64

                if power < 0.12:
                    break

                prev_elev = target.elevation

        return revealed_tiles

    def _optimistic_astar_on_known_map(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        known_threats: Set[Tuple[int, int]],
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Optimistic A* pathfinding.
        - Explored terrain uses real movement cost.
        - Unexplored shroud (state 0) is assumed to be walkable flat ground (cost 1.15).
        - Known threats (sabertooth, cliffs, deep water) are heavily penalized or blocked.
        """
        import heapq

        def get_cost(cx: int, cy: int) -> float:
            if (cx, cy) in known_threats:
                return 999.0

            state = self.fow_grid[cy][cx]
            if state == 0:
                # Unexplored assumption
                return 1.15

            tile = self.gen.grid[cy][cx]
            if not tile.walkable and (cx, cy) not in self.road_tiles:
                return 999.0

            # Trail / Road speedup
            if (cx, cy) in self.road_tiles:
                return 0.55

            if tile.biome_type == BIOME_ANCIENT_SWAMP:
                return 2.40
            elif tile.biome_type == BIOME_MEGALITHIC_HIGHLANDS:
                return 1.85
            elif tile.biome_type == BIOME_TUNDRA:
                return 1.45
            elif tile.biome_type == BIOME_PRIMEVAL_FOREST:
                return 1.35
            return 1.0

        open_set: List[Tuple[float, float, int, int, List[Tuple[int, int]]]] = []
        heapq.heappush(open_set, (math.hypot(goal[0] - start[0], goal[1] - start[1]), 0.0, start[0], start[1], [start]))
        visited: Dict[Tuple[int, int], float] = {start: 0.0}

        while open_set:
            f, g, cx, cy, path = heapq.heappop(open_set)

            if (cx, cy) == goal:
                return path

            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue

                step_cost = get_cost(nx, ny)
                if step_cost >= 900.0:
                    continue

                new_g = g + step_cost
                if (nx, ny) not in visited or new_g < visited[(nx, ny)]:
                    visited[(nx, ny)] = new_g
                    h = math.hypot(goal[0] - nx, goal[1] - ny)
                    heapq.heappush(open_set, (new_g + h, new_g, nx, ny, path + [(nx, ny)]))

        return None

    def blind_explore_to_target(
        self,
        start_pos: Tuple[int, int],
        goal_pos: Tuple[int, int],
        acoustic_sense_radius: int = 18,
    ) -> Dict[str, Any]:
        """
        Simulates dynamic blind pathfinding by an agile tribal scout.
        - Projects forward vision cone (55° half-angle).
        - Listens for predator roars and rustling tracks within acoustic_sense_radius.
        - Automatically executes dynamic replanning when encountering deep water, cliffs, or beasts.
        - Plants a stacked stone Inukshuk cairn every 14 steps.
        """
        scout_pos = start_pos
        actual_path: List[Tuple[int, int]] = [scout_pos]
        known_threats: Set[Tuple[int, int]] = set()
        dynamic_replans = 0
        acoustic_pings: List[Dict[str, Any]] = []

        half_angle = math.radians(55)

        for step_idx in range(500):
            if scout_pos == goal_pos:
                break

            # 1. Optimistic A* on known map
            planned_path = self._optimistic_astar_on_known_map(scout_pos, goal_pos, known_threats)
            if not planned_path or len(planned_path) < 2:
                break

            next_step = planned_path[1]
            facing = math.atan2(next_step[1] - scout_pos[1], next_step[0] - scout_pos[0])

            # 2. Advance and cast vision cone
            scout_pos = next_step
            actual_path.append(scout_pos)
            self.cast_vision_los(scout_pos[0], scout_pos[1], max_radius=9, facing_rad=facing, half_angle_rad=half_angle)

            # 3. Acoustic sensing for predators within 18 tiles
            threat_found_nearby = False
            for dy in range(-acoustic_sense_radius, acoustic_sense_radius + 1):
                for dx in range(-acoustic_sense_radius, acoustic_sense_radius + 1):
                    if dx * dx + dy * dy <= acoustic_sense_radius * acoustic_sense_radius:
                        sx = scout_pos[0] + dx
                        sy = scout_pos[1] + dy
                        if 0 <= sx < self.width and 0 <= sy < self.height:
                            tile = self.gen.grid[sy][sx]
                            if tile.wildlife_spawner in PREDATOR_SPAWNERS:
                                known_threats.add((sx, sy))
                                acoustic_pings.append({
                                    "pos": (sx, sy),
                                    "predator": tile.wildlife_spawner,
                                    "dist": round(math.hypot(dx, dy), 1),
                                })
                                threat_found_nearby = True
                            elif not tile.walkable and self.fow_grid[sy][sx] > 0:
                                known_threats.add((sx, sy))

            if threat_found_nearby:
                dynamic_replans += 1

            # 4. Plant Inukshuk Stone Cairn every 14 steps
            if len(actual_path) % 14 == 0:
                self.cairn_markers.add(scout_pos)

        return {
            "success": scout_pos == goal_pos,
            "path": actual_path,
            "steps_count": len(actual_path),
            "dynamic_replans": dynamic_replans,
            "cairns_planted": len(self.cairn_markers),
            "acoustic_pings": acoustic_pings,
        }

    def trailblaze_and_build_road(self, path: List[Tuple[int, int]]) -> Dict[str, Any]:
        """
        Pioneer Trailblazers clear and pave a route:
        - Forest -> cleared_forest_trail
        - Swamp -> corduroy_log_causeway
        - River -> river_log_bridge
        - Steppe -> trampled_footpath
        - Highlands -> gravel_trail
        Sets travel cost to 0.55/tile (38% to 48% speed boost).
        """
        built_bridges = 0
        built_causeways = 0
        cleared_trails = 0

        for x, y in path:
            tile = self.gen.grid[y][x]
            if tile.biome_type == BIOME_COASTAL_WATERS:
                self.road_tiles[(x, y)] = "river_log_bridge"
                tile.walkable = True
                built_bridges += 1
            elif tile.biome_type == BIOME_ANCIENT_SWAMP:
                self.road_tiles[(x, y)] = "corduroy_log_causeway"
                built_causeways += 1
            elif tile.resource_node == "tree":
                self.road_tiles[(x, y)] = "cleared_forest_trail"
                tile.resource_node = None
                cleared_trails += 1
            else:
                self.road_tiles[(x, y)] = "trampled_footpath"
                cleared_trails += 1

        return {
            "total_road_tiles": len(self.road_tiles),
            "built_bridges": built_bridges,
            "built_causeways": built_causeways,
            "cleared_trails": cleared_trails,
            "travel_cost_per_tile": 0.55,
        }

    def render_mapping_pathfinding_atlas(
        self, output_path: str = "assets/sprites/stone_age_mapping_pathfinding_atlas.png"
    ) -> str:
        """
        Renders a high-resolution 4-panel analytical atlas:
        1. Fog-of-War 3-State LoS from Rock Shelter and Scouts
        2. Blind Exploration Path with vision cone, acoustic pings, and cairns
        3. Trailblazing Road with corduroy causeways, log bridges, and carved arrows
        4. Travel Cost & March Time comparison chart
        """
        img_w, img_h = 1024, 960
        atlas = Image.new("RGB", (img_w, img_h), (20, 18, 16))
        draw = ImageDraw.Draw(atlas)

        # Panel coordinates
        panel_w = 480
        panel_h = 420
        margin_x = 24
        margin_y = 48
        gap = 16

        # Title banner
        draw.text(
            (margin_x, 14),
            "PREHISTORIC STONE AGE RTS -- MAPPING, FOW, BLIND PATHFINDING & TRAILBLAZING ATLAS",
            fill=(250, 245, 235),
        )

        cx, cy = self.gen.center_x, self.gen.center_y

        # Panel 1: Fog of War 3-State Line-of-Sight
        p1_x, p1_y = margin_x, margin_y
        draw.rectangle([p1_x, p1_y, p1_x + panel_w, p1_y + panel_h], fill=(30, 26, 24), outline=(80, 72, 64), width=2)
        draw.text((p1_x + 12, p1_y + 10), "1. Fog-of-War 3-State Line-of-Sight (LoS Raycasting)", fill=(255, 220, 140))

        # Render 200x200 downsampled into panel 1
        scale_x = panel_w / self.width
        scale_y = (panel_h - 40) / self.height
        for y in range(0, self.height, 2):
            for x in range(0, self.width, 2):
                st = self.fow_grid[y][x]
                if st == 0:
                    c = (12, 10, 8)  # Unexplored shroud
                elif st == 1:
                    c = (60, 68, 78)  # Memory fog
                else:
                    # Visible LoS with terrain tint
                    tile = self.gen.grid[y][x]
                    tr, tg, tb = BIOME_PALETTE_RGB.get(tile.biome_type, (140, 140, 140))
                    c = (int(tr * 0.9), int(tg * 0.9), int(tb * 0.9))

                px = int(p1_x + x * scale_x)
                py = int(p1_y + 36 + y * scale_y)
                draw.rectangle([px, py, px + 3, py + 3], fill=c)

        # Draw Campfire origin
        scx = int(p1_x + cx * scale_x)
        scy = int(p1_y + 36 + cy * scale_y)
        draw.ellipse([scx - 4, scy - 4, scx + 4, scy + 4], fill=(255, 120, 40), outline=(255, 255, 255))

        # Panel 2: Blind Pathfinding & Acoustic Sensing
        p2_x, p2_y = margin_x + panel_w + gap, margin_y
        draw.rectangle([p2_x, p2_y, p2_x + panel_w, p2_y + panel_h], fill=(30, 26, 24), outline=(80, 72, 64), width=2)
        draw.text((p2_x + 12, p2_y + 10), "2. Scout Blind Exploration & Acoustic Sensory Pings", fill=(255, 220, 140))

        # Background terrain
        for y in range(0, self.height, 2):
            for x in range(0, self.width, 2):
                tile = self.gen.grid[y][x]
                tr, tg, tb = BIOME_PALETTE_RGB.get(tile.biome_type, (100, 100, 100))
                px = int(p2_x + x * scale_x)
                py = int(p2_y + 36 + y * scale_y)
                draw.rectangle([px, py, px + 3, py + 3], fill=(int(tr * 0.5), int(tg * 0.5), int(tb * 0.5)))

        # Simulate a Scout exploration from camp to northeast mammoth / wolf territory
        target_explore = (cx + 45, cy - 40)
        res = self.blind_explore_to_target((cx, cy), target_explore)

        # Draw path
        for px, py in res["path"]:
            sx = int(p2_x + px * scale_x)
            sy = int(p2_y + 36 + py * scale_y)
            draw.rectangle([sx, sy, sx + 2, sy + 2], fill=(255, 230, 80))

        # Draw stone cairns
        for kx, ky in self.cairn_markers:
            sx = int(p2_x + kx * scale_x)
            sy = int(p2_y + 36 + ky * scale_y)
            draw.polygon([(sx, sy - 4), (sx + 3, sy + 3), (sx - 3, sy + 3)], fill=(220, 220, 220))

        # Draw acoustic predator pings
        for ping in res["acoustic_pings"][:15]:
            tx, ty = ping["pos"]
            sx = int(p2_x + tx * scale_x)
            sy = int(p2_y + 36 + ty * scale_y)
            draw.ellipse([sx - 6, sy - 6, sx + 6, sy + 6], outline=(255, 60, 60), width=1)

        # Panel 3: Trailblazing & River Crossings
        p3_x, p3_y = margin_x, margin_y + panel_h + gap
        draw.rectangle([p3_x, p3_y, p3_x + panel_w, p3_y + panel_h], fill=(30, 26, 24), outline=(80, 72, 64), width=2)
        draw.text((p3_x + 12, p3_y + 10), "3. Pioneer Trailblazing, Bridges & Log Causeways", fill=(255, 220, 140))

        # Pave the road
        road_res = self.trailblaze_and_build_road(res["path"])

        for y in range(0, self.height, 2):
            for x in range(0, self.width, 2):
                tile = self.gen.grid[y][x]
                tr, tg, tb = BIOME_PALETTE_RGB.get(tile.biome_type, (100, 100, 100))
                px = int(p3_x + x * scale_x)
                py = int(p3_y + 36 + y * scale_y)
                draw.rectangle([px, py, px + 3, py + 3], fill=(int(tr * 0.7), int(tg * 0.7), int(tb * 0.7)))

        # Draw paved roads
        for (rx, ry), rtype in self.road_tiles.items():
            sx = int(p3_x + rx * scale_x)
            sy = int(p3_y + 36 + ry * scale_y)
            if rtype == "river_log_bridge":
                draw.rectangle([sx - 1, sy - 1, sx + 4, sy + 4], fill=(220, 175, 110))
            elif rtype == "corduroy_log_causeway":
                draw.rectangle([sx - 1, sy - 1, sx + 3, sy + 3], fill=(160, 120, 70))
            else:
                draw.rectangle([sx, sy, sx + 2, sy + 2], fill=(240, 205, 140))

        # Panel 4: Movement Cost & March Time Analytics
        p4_x, p4_y = margin_x + panel_w + gap, margin_y + panel_h + gap
        draw.rectangle([p4_x, p4_y, p4_x + panel_w, p4_y + panel_h], fill=(30, 26, 24), outline=(80, 72, 64), width=2)
        draw.text((p4_x + 12, p4_y + 10), "4. Movement Cost & March Time Efficiency Comparison", fill=(255, 220, 140))

        # Comparison Bar Chart
        categories = [
            ("Steppe Grassland", 1.0, 0.55),
            ("Primeval Forest", 1.35, 0.55),
            ("Glacial Tundra", 1.45, 0.55),
            ("Highland Cliffs", 1.85, 0.55),
            ("Ancient Swamp", 2.40, 0.55),
            ("River Crossing", 3.00, 0.55),
        ]

        bar_start_y = p4_y + 60
        for idx, (cat_name, raw_cost, road_cost) in enumerate(categories):
            cy = bar_start_y + idx * 52
            draw.text((p4_x + 20, cy), cat_name, fill=(230, 225, 215))

            # Raw Cost bar (Red/Orange)
            w_raw = int(raw_cost * 80)
            draw.rectangle([p4_x + 170, cy + 2, p4_x + 170 + w_raw, cy + 14], fill=(225, 75, 65))
            draw.text((p4_x + 175 + w_raw, cy), f"{raw_cost:.2f}", fill=(240, 160, 150))

            # Road Cost bar (Green)
            w_road = int(road_cost * 80)
            draw.rectangle([p4_x + 170, cy + 18, p4_x + 170 + w_road, cy + 30], fill=(65, 195, 95))
            savings = int((1.0 - road_cost / raw_cost) * 100)
            draw.text((p4_x + 175 + w_road, cy + 16), f"{road_cost:.2f} (-{savings}%)", fill=(150, 230, 170))

        # Legend
        draw.rectangle([p4_x + 20, p4_y + panel_h - 35, p4_x + 35, p4_y + panel_h - 23], fill=(225, 75, 65))
        draw.text((p4_x + 42, p4_y + panel_h - 37), "Raw Wilderness Terrain Cost", fill=(220, 215, 205))
        draw.rectangle([p4_x + 240, p4_y + panel_h - 35, p4_x + 255, p4_y + panel_h - 23], fill=(65, 195, 95))
        draw.text((p4_x + 262, p4_y + panel_h - 37), "Trailblazed Road Cost (0.55/tile)", fill=(220, 215, 205))

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        atlas.save(output_path, "PNG")
        return output_path



if __name__ == "__main__":
    generator = ProceduralStoneAgeWorldGenerator(width=200, height=200, seed=2026)
    world_matrix = generator.generate_world()
    generator.export_to_json("stone_age_world_200x200.json", include_full_grid=True)
    print("Exported stone_age_world_200x200.json successfully!")
    print(generator.render_ascii_preview(downsample_step=4, show_spawn_zoom=True))

    output_dir = os.path.dirname(os.path.abspath(__file__))
    atlas_path = os.path.join(output_dir, "stone_age_world_tactical_atlas.png")
    renderer = StoneAgeGraphicsRenderer(generator)
    renderer.render_tactical_atlas(atlas_path)
    print(f"\nSaved 4-panel graphical tactical atlas to: {atlas_path}")
