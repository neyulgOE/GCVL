"""
world/data/local_map_bridge.py
Phase 7B: Cầu nối đồng bộ Single Source of Truth từ World Raster (512x512)
sang Local Runtime Map (80x80) cho map_manager.py và wildlife_manager.py.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import math
import random
import numpy as np

from world.config.world_config import WorldConfig
from world.generation.landmass_generator import LandmassResult
from world.generation.terrain_generator import TerrainResult
from world.generation.climate_generator import ClimateResult
from world.generation.hydrology_generator import HydrologyResult
from world.generation.soil_generator import SoilResult, SOIL_NAMES
from world.generation.biome_generator import BiomeResult, BIOME_NAMES
from world.generation.ecology_generator import EcologyResult, FLORA_CATALOG, FAUNA_CATALOG


@dataclass
class LocalRegionPatch:
    center_world_col: int
    center_world_row: int
    world_bbox: Tuple[int, int, int, int]  # (c0, r0, c1, r1) trên lưới 512x512
    local_cols: int
    local_rows: int
    heightmap: List[List[float]]
    slope_map: List[List[float]]
    aspect_map: List[List[float]]
    soil_moisture: List[List[float]]
    terrain_tags: List[List[str]]
    biome_tags: List[List[str]]
    water_tiles: List[Tuple[int, int]]
    flora_instances: List[Dict[str, Any]]
    fauna_spawns: List[Dict[str, Any]]


class LocalMapBridge:
    """
    Trích xuất một cửa sổ trên đại lục Primeval Reach (mặc định vùng 32x32 trên lưới 512x512)
    và nội suy mượt lên lưới Local Map (80x80 tiles) để hiển thị trong Pygame / OpenGL 3D.
    """

    def __init__(
        self,
        config: WorldConfig,
        landmass: LandmassResult,
        terrain: TerrainResult,
        climate: ClimateResult,
        hydrology: HydrologyResult,
        soil: SoilResult,
        biome: BiomeResult,
        ecology: EcologyResult,
    ) -> None:
        self.cfg = config
        self.landmass = landmass
        self.terrain = terrain
        self.climate = climate
        self.hydrology = hydrology
        self.soil = soil
        self.biome = biome
        self.ecology = ecology

    @staticmethod
    def _bilinear_sample(grid: np.ndarray, wy: float, wx: float) -> float:
        h, w = grid.shape
        wy = max(0.0, min(float(h - 1), wy))
        wx = max(0.0, min(float(w - 1), wx))
        r0, c0 = int(math.floor(wy)), int(math.floor(wx))
        r1, c1 = min(h - 1, r0 + 1), min(w - 1, c0 + 1)
        fy, fx = wy - r0, wx - c0
        top = grid[r0, c0] * (1.0 - fx) + grid[r0, c1] * fx
        bot = grid[r1, c0] * (1.0 - fx) + grid[r1, c1] * fx
        return float(top * (1.0 - fy) + bot * fy)

    def extract_local_patch(
        self,
        center_world_col: int = 236,
        center_world_row: int = 248,
        world_window_size: int = 32,
    ) -> LocalRegionPatch:
        half = world_window_size // 2
        c0 = max(0, min(self.cfg.width - world_window_size, center_world_col - half))
        r0 = max(0, min(self.cfg.height - world_window_size, center_world_row - half))
        c1 = c0 + world_window_size
        r1 = r0 + world_window_size

        l_cols, l_rows = self.cfg.local_cols, self.cfg.local_rows
        heightmap = [[0.0 for _ in range(l_cols)] for _ in range(l_rows)]
        slope_map = [[0.0 for _ in range(l_cols)] for _ in range(l_rows)]
        aspect_map = [[0.0 for _ in range(l_cols)] for _ in range(l_rows)]
        soil_moisture = [[0.0 for _ in range(l_cols)] for _ in range(l_rows)]
        terrain_tags = [["steppe_meadow" for _ in range(l_cols)] for _ in range(l_rows)]
        biome_tags = [["open_meadow" for _ in range(l_cols)] for _ in range(l_rows)]
        water_tiles: List[Tuple[int, int]] = []
        flora_instances: List[Dict[str, Any]] = []

        rng = random.Random(self.cfg.seed + center_world_col * 31 + center_world_row)

        for lr in range(l_rows):
            wy = r0 + (lr / max(1, l_rows - 1)) * (world_window_size - 1)
            wi_r = int(round(wy))
            for lc in range(l_cols):
                wx = c0 + (lc / max(1, l_cols - 1)) * (world_window_size - 1)
                wi_c = int(round(wx))

                elev = self._bilinear_sample(self.terrain.final_heightmap, wy, wx)
                slope = self._bilinear_sample(self.terrain.slope, wy, wx)
                aspect = self._bilinear_sample(self.terrain.aspect, wy, wx)
                moist = self._bilinear_sample(self.soil.soil_moisture, wy, wx)

                heightmap[lr][lc] = round(elev, 4)
                slope_map[lr][lc] = round(slope, 4)
                aspect_map[lr][lc] = round(aspect, 4)
                soil_moisture[lr][lc] = round(moist, 4)

                is_sea = not bool(self.landmass.landmask[wi_r, wi_c])
                is_river = bool(self.hydrology.river_mask[wi_r, wi_c])
                is_lake = bool(self.hydrology.lake_mask[wi_r, wi_c])
                b_id = int(self.biome.primary_biome_id[wi_r, wi_c])

                if is_sea or is_river or is_lake or elev < self.cfg.sea_level:
                    terrain_tags[lr][lc] = "water"
                    biome_tags[lr][lc] = "river_water"
                    water_tiles.append((lc, lr))
                elif slope > 0.35 or b_id in (1, 2):
                    terrain_tags[lr][lc] = "scree_talus"
                    biome_tags[lr][lc] = "rock_cliff"
                elif b_id == 8:
                    terrain_tags[lr][lc] = "riparian_mud"
                    biome_tags[lr][lc] = "wetland_marsh"
                elif b_id == 7:
                    terrain_tags[lr][lc] = "settlement_loam"
                    biome_tags[lr][lc] = "riparian_corridor"
                elif b_id in (3, 4, 5, 6):
                    terrain_tags[lr][lc] = "forest_humus"
                    biome_tags[lr][lc] = "mixed_forest"
                else:
                    terrain_tags[lr][lc] = "steppe_meadow"
                    biome_tags[lr][lc] = "open_meadow"

                # Sinh thực vật đa tầng theo đúng loài chiếm ưu thế của World Map
                if terrain_tags[lr][lc] != "water":
                    veg_dens = self._bilinear_sample(self.ecology.vegetation_density, wy, wx)
                    dom_idx = int(self.ecology.dominant_flora_idx[wi_r, wi_c])
                    if dom_idx >= 0 and rng.random() < (veg_dens * 0.68):
                        spec = FLORA_CATALOG[dom_idx]
                        flora_instances.append({
                            "col": lc,
                            "row": lr,
                            "species_id": spec.species_id,
                            "layer": spec.layer,
                            "growth_stage": rng.choice(["sprout", "mature", "prime"]),
                        })

        # Ánh xạ các đàn thú hoang dã nằm trong hoặc lân cận vùng Local Map
        fauna_spawns: List[Dict[str, Any]] = []
        for herd in self.ecology.spawned_wildlife_herds:
            hc, hr = herd["world_col"], herd["world_row"]
            if (c0 - 16) <= hc <= (c1 + 16) and (r0 - 16) <= hr <= (r1 + 16):
                norm_c = max(0.05, min(0.95, (hc - c0) / max(1.0, float(world_window_size))))
                norm_r = max(0.05, min(0.95, (hr - r0) / max(1.0, float(world_window_size))))
                fauna_spawns.append({
                    "species_id": herd["species_id"],
                    "guild": herd["guild"],
                    "local_col": int(norm_c * (l_cols - 1)),
                    "local_row": int(norm_r * (l_rows - 1)),
                    "count": herd["count"],
                })

        return LocalRegionPatch(
            center_world_col=center_world_col,
            center_world_row=center_world_row,
            world_bbox=(c0, r0, c1, r1),
            local_cols=l_cols,
            local_rows=l_rows,
            heightmap=heightmap,
            slope_map=slope_map,
            aspect_map=aspect_map,
            soil_moisture=soil_moisture,
            terrain_tags=terrain_tags,
            biome_tags=biome_tags,
            water_tiles=water_tiles,
            flora_instances=flora_instances,
            fauna_spawns=fauna_spawns,
        )

    def sync_into_runtime_map_manager(
        self, map_mgr: Any, center_world_col: int = 236, center_world_row: int = 248
    ) -> LocalRegionPatch:
        """Đồng bộ trực tiếp dữ liệu địa lý vào đối tượng MapManager đang chạy trong game."""
        patch = self.extract_local_patch(center_world_col, center_world_row)
        map_mgr.heightmap = patch.heightmap
        map_mgr.slope_map = patch.slope_map
        map_mgr.aspect_map = patch.aspect_map
        map_mgr.soil_moisture = patch.soil_moisture
        map_mgr.farm_terrain = patch.terrain_tags
        map_mgr.terrain = patch.terrain_tags
        map_mgr.biome_map = patch.biome_tags
        map_mgr.farm_water_tiles = set(patch.water_tiles)
        map_mgr.water_tiles = map_mgr.farm_water_tiles
        map_mgr.synced_world_patch = patch
        return patch
