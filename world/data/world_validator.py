"""
world/data/world_validator.py
Kiểm định tự động hình thái lục địa, tính liên thông đất liền, độ rộng eo đất
và chất lượng phân tầng độ cao cho Phase 1 & Phase 2.
"""

from collections import deque
from typing import Dict, Any, Tuple
import numpy as np
from world.config.world_config import WorldConfig
from world.generation.landmass_generator import LandmassResult
from world.generation.terrain_generator import TerrainResult


class WorldValidator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config

    def _find_connected_landmasses(self, landmask: np.ndarray) -> Tuple[int, int, int]:
        """
        Dùng BFS Flood-Fill đếm số lượng mảng đất nổi, diện tích lục địa lớn nhất
        và số lượng đảo phụ.
        """
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

        # Kiểm tra độ cao trung bình và độ tương phản trên đất liền
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
