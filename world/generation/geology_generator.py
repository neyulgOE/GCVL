"""
world/generation/geology_generator.py
Sinh hệ thống Dãy núi phân thủy sắc nét (Warped Ridged Multifractal),
trục nâng kiến tạo đa lục địa (NW Arctic Spine, NE Plateau, Central-East Ridges, SW Canyon Rim)
và các bồn địa địa chất (SW Desert Basin, Central Floodplain, Eastern Bay).
"""

from dataclasses import dataclass
import numpy as np
from world.config.world_config import WorldConfig
from world.generation.landmass_generator import FastNoise2D, LandmassResult


@dataclass
class GeologyResult:
    tectonic_uplift: np.ndarray
    ridge_field: np.ndarray
    basin_field: np.ndarray
    fault_lines: np.ndarray


class GeologyGenerator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config
        self.ridge_noise = FastNoise2D(seed=config.seed + 151)
        self.spur_noise = FastNoise2D(seed=config.seed + 283)
        self.warp_noise = FastNoise2D(seed=config.seed + 419)

    def _warped_ridged_multifractal(
        self, nx: np.ndarray, ny: np.ndarray, octaves: int = 6, base_scale: float = 4.2
    ) -> np.ndarray:
        """Sinh các sống núi nhọn phân nhánh bằng Domain-Warped Ridged Noise."""
        wx = nx + (self.warp_noise.fbm_grid(nx, ny, octaves=3, base_scale=3.0) - 0.5) * 0.16
        wy = ny + (self.warp_noise.fbm_grid(nx + 3.1, ny + 1.7, octaves=3, base_scale=3.0) - 0.5) * 0.16

        total = np.zeros_like(nx, dtype=np.float32)
        amplitude = 1.0
        frequency = base_scale
        weight = np.ones_like(nx, dtype=np.float32)
        max_val = 0.0

        for _ in range(octaves):
            n_val = self.ridge_noise.noise_grid(wx * frequency * 1.3, wy * frequency)
            signal = 1.0 - np.abs(n_val)
            signal = (signal ** 2.2) * weight
            weight = np.clip(signal * 2.0, 0.0, 1.0)
            total += signal * amplitude
            max_val += amplitude
            amplitude *= 0.52
            frequency *= 2.15

        return np.clip(total / max(1e-6, max_val), 0.0, 1.0)

    def generate(self, landmass: LandmassResult) -> GeologyResult:
        h, w = self.cfg.height, self.cfg.width
        ny, nx = np.meshgrid(
            np.linspace(0.0, 1.0, h, dtype=np.float32),
            np.linspace(0.0, 1.0, w, dtype=np.float32),
            indexing="ij",
        )
        land = landmass.landmask

        # 1. Trục Nâng Kiến Tạo Đa Lục Địa (Tectonic Uplift Belts)
        # --- A. Khối núi Băng Bắc (NW Glacial Massif) ---
        dist_nw_spine = np.sqrt(((nx - 0.24) / 0.15) ** 2 + ((ny - 0.26) / 0.17) ** 2)
        nw_alpine_uplift = np.maximum(0.0, 1.0 - dist_nw_spine) ** 1.35 * 1.15

        # --- B. Sống núi Cao nguyên Đông Bắc (NE Highland Spine) ---
        dist_ne_spine = np.sqrt(((nx - 0.60) / 0.16) ** 2 + ((ny - 0.24) / 0.14) ** 2)
        ne_plateau_uplift = np.maximum(0.0, 1.0 - dist_ne_spine) ** 1.20 * 0.85

        # --- C. Vành đai Núi & Đồi Lục địa Rừng Thiêng (Central-East Ridges) ---
        dist_ce_spine = np.sqrt(((nx - 0.62) / 0.20) ** 2 + ((ny - 0.56) / 0.22) ** 2)
        ce_mountain_uplift = np.maximum(0.0, 1.0 - dist_ce_spine) ** 1.25 * 0.78

        # --- D. Vành đai Vách đá Hẻm núi Sa mạc Tây Nam (SW Canyon Rim) ---
        dist_sw_rim = np.sqrt(((nx - 0.25) / 0.17) ** 2 + ((ny - 0.72) / 0.16) ** 2)
        sw_canyon_uplift = np.maximum(0.0, 1.0 - dist_sw_rim) ** 1.30 * 0.80

        macro_uplift = np.maximum.reduce([
            nw_alpine_uplift,
            ne_plateau_uplift,
            ce_mountain_uplift,
            sw_canyon_uplift,
        ])

        tectonic_uplift = np.clip(macro_uplift * land, 0.0, 1.0)

        # 2. Trường Sống núi sắc nhọn (Ridged Multifractal)
        ridged_detail = self._warped_ridged_multifractal(nx, ny, octaves=6, base_scale=4.5)
        ridge_field = np.clip(ridged_detail * (0.35 + 0.65 * tectonic_uplift) * land, 0.0, 1.0)

        # 3. Bồn địa địa chất (Sedimentary Basins)
        # Bồn địa Sa mạc Tây Nam (Southwest Arid Basin)
        sw_basin = np.exp(-(((nx - 0.26) / 0.12) ** 2 + ((ny - 0.70) / 0.12) ** 2)) * 0.85
        # Bồn trũng thung lũng sông Trung Tâm (Central Floodplain Basin)
        ce_basin = np.exp(-(((nx - 0.56) / 0.14) ** 2 + ((ny - 0.52) / 0.15) ** 2)) * 0.75
        # Bồn trũng vịnh ven biển Đông
        east_bay_basin = np.exp(-(((nx - 0.72) / 0.10) ** 2 + ((ny - 0.62) / 0.12) ** 2)) * 0.70

        basin_field = np.clip(np.maximum.reduce([sw_basin, ce_basin, east_bay_basin]) * land, 0.0, 1.0)

        # 4. Đứt gãy kiến tạo (Fault Lines)
        fault_noise = self.spur_noise.fbm_grid(nx * 5.0, ny * 5.0, octaves=4, base_scale=6.0)
        fault_lines = np.clip((np.abs(fault_noise - 0.5) < 0.04).astype(np.float32) * tectonic_uplift * 0.18, 0.0, 1.0)

        return GeologyResult(
            tectonic_uplift=tectonic_uplift.astype(np.float32),
            ridge_field=ridge_field.astype(np.float32),
            basin_field=basin_field.astype(np.float32),
            fault_lines=fault_lines.astype(np.float32),
        )
