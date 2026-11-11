"""
world/data/world_validator.py
Cập nhật: Tích hợp kiểm định Phase 1, Phase 2, Phase 3 (Climate & Rain Shadow),
Phase 4 (Watershed & River Monotonic Downhill Check) và Phase 5 (Soil & Biome Distribution).
"""

from collections import deque
from typing import Dict, Any, Tuple
import numpy as np

from world.config.world_config import WorldConfig
from world.generation.landmass_generator import LandmassResult
from world.generation.terrain_generator import TerrainResult
from world.generation.climate_generator import ClimateResult
from world.generation.hydrology_generator import HydrologyResult
from world.generation.soil_generator import SoilResult
from world.generation.biome_generator import BiomeResult


class WorldValidator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config

    def _find_connected_landmasses(self, landmask: np.ndarray) -> Tuple[int, int, int]:
        h, w = landmask.shape
        visited = np.zeros_like(landmask, dtype=bool)
        component_sizes = []

        for r in range(h):
            for c in range(w):
                if landmask[r, c] and not visited[r, c]:
                    size = 0
                    queue = deque([(r, c)])
                    visited[r, c] = True
                    while queue:
                        cr, cc = queue.popleft()
                        size += 1
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < h and 0 <= nc < w and landmask[nr, nc] and not visited[nr, nc]:
                                visited[nr, nc] = True
                                queue.append((nr, nc))
                    component_sizes.append(size)

        if not component_sizes:
            return 0, 0, 0
        component_sizes.sort(reverse=True)
        largest = component_sizes[0]
        minor_islands = sum(1 for s in component_sizes[1:] if s >= 25)
        return len(component_sizes), largest, minor_islands

    def validate_phase1_and_phase2(
        self, landmass: LandmassResult, terrain: TerrainResult
    ) -> Dict[str, Any]:
        total_cells = landmass.landmask.size
        land_cells = int(np.sum(landmass.landmask))
        land_ratio = land_cells / max(1, total_cells)

        num_comp, largest_comp, minor_islands = self._find_connected_landmasses(landmass.landmask)
        main_continent_share = largest_comp / max(1, land_cells)

        land_heights = terrain.final_heightmap[landmass.landmask]
        max_elev = float(np.max(land_heights)) if land_heights.size > 0 else 0.0
        std_elev = float(np.std(land_heights)) if land_heights.size > 0 else 0.0

        passed = (
            self.cfg.target_land_ratio_min <= land_ratio <= self.cfg.target_land_ratio_max
            and main_continent_share >= self.cfg.min_main_continent_share
            and std_elev >= 0.08
        )

        return {
            "seed": self.cfg.seed,
            "resolution": f"{self.cfg.width}x{self.cfg.height}",
            "land_ratio": round(land_ratio, 4),
            "main_continent_share": round(main_continent_share, 4),
            "minor_islands_count": minor_islands,
            "inland_bay_cells": int(np.sum(landmass.inland_bay_mask)),
            "max_elevation": round(max_elev, 4),
            "elevation_std": round(std_elev, 4),
            "passed_gate": bool(passed),
        }

    def validate_phase3_and_phase4(
        self,
        landmass: LandmassResult,
        climate: ClimateResult,
        hydrology: HydrologyResult,
    ) -> Dict[str, Any]:
        land = landmass.landmask
        h, w = land.shape

        # 1. Kiểm tra tương phản lượng mưa giữa Sườn đón gió Tây Bắc và Vùng khuất mưa Tây Nam
        nw_mask = land & (np.arange(h)[:, None] < int(h * 0.45)) & (np.arange(w)[None, :] < int(w * 0.45))
        sw_mask = land & (np.arange(h)[:, None] >= int(h * 0.52)) & (np.arange(w)[None, :] < int(w * 0.45))

        nw_precip = float(np.mean(climate.precipitation[nw_mask])) if np.any(nw_mask) else 0.0
        sw_precip = float(np.mean(climate.precipitation[sw_mask])) if np.any(sw_mask) else 0.0
        rain_shadow_contrast = nw_precip - sw_precip

        # 2. Kiểm tra 0% sông chảy ngược dốc (Monotonic Downhill Validation)
        uphill_violations = 0
        total_segments = 0
        for feat in hydrology.river_features:
            elevs = feat["properties"]["elevations"]
            for i in range(len(elevs) - 1):
                total_segments += 1
                if elevs[i + 1] > elevs[i] + 1e-4:
                    uphill_violations += 1

        river_cells = int(np.sum(hydrology.river_mask))
        lake_cells = int(np.sum(hydrology.lake_mask))
        endorheic_cells = int(np.sum(hydrology.endorheic_lake_mask))

        passed = (
            rain_shadow_contrast >= 0.12
            and uphill_violations == 0
            and len(hydrology.river_features) >= 15
            and endorheic_cells > 0
        )

        return {
            "seed": self.cfg.seed,
            "nw_windward_precip_avg": round(nw_precip, 4),
            "sw_rain_shadow_precip_avg": round(sw_precip, 4),
            "rain_shadow_contrast": round(rain_shadow_contrast, 4),
            "river_branches_count": len(hydrology.river_features),
            "river_cells": river_cells,
            "lake_cells": lake_cells,
            "endorheic_lake_cells": endorheic_cells,
            "uphill_river_violations": uphill_violations,
            "total_river_segments_checked": total_segments,
            "passed_gate": bool(passed),
        }

    def validate_phase5(
        self,
        landmass: LandmassResult,
        soil: SoilResult,
        biome: BiomeResult,
    ) -> Dict[str, Any]:
        """Kiểm định Phase 5: Đảm bảo đủ 7 loại đất và 11 quần xã sinh vật với dải chuyển tiếp mềm."""
        land = landmass.landmask
        land_total = max(1, int(np.sum(land)))

        soil_counts: Dict[str, float] = {}
        present_soils = 0
        for s_id in range(1, 8):
            cnt = int(np.sum((soil.soil_id == s_id) & land))
            share = round(cnt / land_total, 4)
            soil_counts[f"soil_{s_id}"] = share
            if cnt >= 40:
                present_soils += 1

        biome_counts: Dict[str, float] = {}
        present_biomes = 0
        for b_id in range(1, 12):
            cnt = int(np.sum((biome.primary_biome_id == b_id) & land))
            share = round(cnt / land_total, 4)
            biome_counts[f"biome_{b_id}"] = share
            if cnt >= 40:
                present_biomes += 1

        ecotone_ratio = float(np.mean(biome.ecotone_factor[land] > 0.25))

        passed = (present_soils == 7) and (present_biomes >= 10) and (ecotone_ratio >= 0.15)

        return {
            "seed": self.cfg.seed,
            "present_soil_types": present_soils,
            "target_soil_types": 7,
            "present_biomes": present_biomes,
            "target_biomes": 11,
            "ecotone_transition_ratio": round(ecotone_ratio, 4),
            "soil_distribution": soil_counts,
            "biome_distribution": biome_counts,
            "passed_gate": bool(passed),
        }
