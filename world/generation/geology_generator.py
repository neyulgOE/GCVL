"""
world/generation/geology_generator.py
Sinh hệ thống Dãy núi phân thủy sắc nét (Warped Ridged Multifractal),
nhánh núi xương cá (Secondary Spur Ridges), Cao nguyên bậc thang và Bồn địa.
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

    def _warped_ridged_multifractal(self, nx: np.ndarray, ny: np.ndarray, octaves: int = 6, base_scale: float = 4.2) -> np.ndarray:
        """Sinh các sống núi nhọn phân nhánh như xương cá bằng Domain-Warped Ridged Noise."""
        wx = nx + (self.warp_noise.fbm_grid(nx, ny, octaves=3, base_scale=3.0) - 0.5) * 0.18
        wy = ny + (self.warp_noise.fbm_grid(nx + 3.1, ny + 1.7, octaves=3, base_scale=3.0) - 0.5) * 0.18

        total = np.zeros_like(nx, dtype=np.float32)
        amplitude = 1.0
        frequency = base_scale
        weight = np.ones_like(nx, dtype=np.float32)
        max_val = 0.0

        for _ in range(octaves):
            n_val = self.ridge_noise.noise_grid(wx * frequency * 1.4, wy * frequency)
            signal = 1.0 - np.abs(n_val)
            signal = (signal ** 2.2) * weight
            weight = np.clip(signal * 2.1, 0.0, 1.0)
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

        # 1. Dãy núi Xương sống Trung tâm (Continental Spine) uốn lượn Bắc - Nam
        wiggle = (self.warp_noise.fbm_grid(nx, ny, octaves=3, base_scale=2.5) - 0.5) * 0.12
        spine_x = 0.42 + 0.05 * np.sin(ny * np.pi * 2.2 - 0.4) + wiggle
        dist_spine = np.abs(nx - spine_x)
        central_spine = np.exp(-((dist_spine / 0.085) ** 2)) * np.clip(1.32 - ny * 1.15, 0.0, 1.0)

        # 2. Vòng cung Núi Băng Phía Bắc (Northern Alpine Arc) & Dãy Đón Gió Tây Bắc
        alpine_north = np.exp(-(((nx - 0.44) / 0.25) ** 2 + ((ny - 0.20 + wiggle * 0.4) / 0.095) ** 2))
        nw_windward_range = np.exp(-(((nx - 0.24 - wiggle * 0.3) / 0.08) ** 2 + ((ny - 0.32) / 0.15) ** 2)) * 0.85
        east_highland_spur = np.exp(-(((nx - 0.66) / 0.09) ** 2 + ((ny - 0.28) / 0.11) ** 2)) * 0.68

        macro_belts = np.maximum.reduce([central_spine, alpine_north, nw_windward_range, east_highland_spur])
        uplift_fbm = self.spur_noise.fbm_grid(nx * 1.4, ny, octaves=4, base_scale=3.0)
        tectonic_uplift = np.clip((macro_belts * 0.82 + uplift_fbm * 0.24) * land, 0.0, 1.0)

        # 3. Trường Sống núi sắc nét (Ridge Field)
        ridged_detail = self._warped_ridged_multifractal(nx, ny, octaves=6, base_scale=4.5)
        ridge_field = np.clip(ridged_detail * (0.28 + 0.85 * (tectonic_uplift ** 0.8)) * land, 0.0, 1.0)

        # 4. Bồn địa trũng (Tây Nam nội lưu & Đồng bằng Đông Bắc)
        sw_basin = 0.82 * np.exp(-(((nx - 0.28) / 0.11) ** 2 + ((ny - 0.65) / 0.11) ** 2))
        ne_basin = 0.68 * np.exp(-(((nx - 0.62) / 0.12) ** 2 + ((ny - 0.38) / 0.11) ** 2))
        se_bay_lowland = 0.60 * np.exp(-(((nx - 0.56) / 0.12) ** 2 + ((ny - 0.58) / 0.12) ** 2))
        basin_field = np.clip(np.maximum.reduce([sw_basin, ne_basin, se_bay_lowland]) * land, 0.0, 1.0)

        # 5. Đứt gãy hẻm vực (Tectonic Canyons)
        fault_raw = np.abs(self.spur_noise.noise_grid(nx * 9.0 + ny * 3.0, ny * 9.0 - nx * 3.0))
        fault_lines = np.clip((1.0 - np.clip(fault_raw * 14.0, 0.0, 1.0)) * tectonic_uplift, 0.0, 1.0)

        return GeologyResult(
            tectonic_uplift=tectonic_uplift.astype(np.float32),
            ridge_field=ridge_field.astype(np.float32),
            basin_field=basin_field.astype(np.float32),
            fault_lines=fault_lines.astype(np.float32),
        )
