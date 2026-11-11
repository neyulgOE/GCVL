"""
world/generation/geology_generator.py
Mô phỏng kiến tạo mảng, sống núi phân thủy chính (Continental Spine),
các nhánh núi phụ (Secondary Ridges), bồn địa (Basins) và đứt gãy tuyến tính.
"""

from dataclasses import dataclass
import numpy as np
from world.config.world_config import WorldConfig
from world.generation.landmass_generator import FastNoise2D, LandmassResult


@dataclass
class GeologyResult:
    tectonic_uplift: np.ndarray  # Trường nâng kiến tạo vùng Bắc Cao & Trung Tâm [0..1]
    ridge_field: np.ndarray      # Sống núi sắc nét (Ridged Multifractal + Spine) [0..1]
    basin_field: np.ndarray      # Các bồn địa trũng (Tây Nam nội lưu & Đông Bắc) [0..1]
    fault_lines: np.ndarray      # Vết đứt gãy địa chất và hẻm vực [0..1]


class GeologyGenerator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config
        self.ridge_noise = FastNoise2D(seed=config.seed + 131)
        self.uplift_noise = FastNoise2D(seed=config.seed + 257)
        self.fault_noise = FastNoise2D(seed=config.seed + 509)

    def _ridged_multifractal(self, nx: np.ndarray, ny: np.ndarray, octaves: int = 5, base_scale: float = 3.5) -> np.ndarray:
        """Sinh nhiễu Ridged Multifractal tạo các đỉnh núi và sống núi nhọn tự nhiên."""
        total = np.zeros_like(nx, dtype=np.float32)
        amplitude = 1.0
        frequency = base_scale
        weight = np.ones_like(nx, dtype=np.float32)
        max_val = 0.0

        for _ in range(octaves):
            signal = 1.0 - np.abs(self.ridge_noise.noise_grid(nx * frequency, ny * frequency))
            signal = (signal * signal) * weight
            weight = np.clip(signal * 1.8, 0.0, 1.0)
            total += signal * amplitude
            max_val += amplitude
            amplitude *= 0.52
            frequency *= 2.1

        return np.clip(total / max(1e-6, max_val), 0.0, 1.0)

    def generate(self, landmass: LandmassResult) -> GeologyResult:
        h, w = self.cfg.height, self.cfg.width
        ny, nx = np.meshgrid(
            np.linspace(0.0, 1.0, h, dtype=np.float32),
            np.linspace(0.0, 1.0, w, dtype=np.float32),
            indexing="ij",
        )

        # 1. Đường cong Sống lưng Kiến tạo Chính (Continental Spine) chạy từ Bắc xuống Nam-Trung Tâm
        spine_center_x = (
            0.44
            + 0.06 * np.sin(ny * np.pi * 2.1 - 0.3)
            + (self.uplift_noise.noise_grid(nx * 2.5, ny * 2.5)) * 0.05
        )
        dist_to_spine = np.abs(nx - spine_center_x)
        spine_profile = np.exp(-((dist_to_spine / 0.095) ** 2)) * np.clip(1.25 - ny * 1.1, 0.0, 1.0)

        # 2. Nhánh núi phụ Tây-Bắc (Windward Range) và Dãy Bắc Cao (Northern Alpine Massif)
        nw_branch_dist = np.abs((nx - 0.28) + (ny - 0.26) * 0.85)
        nw_branch = 0.75 * np.exp(-((nw_branch_dist / 0.07) ** 2)) * np.exp(-(((ny - 0.28) / 0.16) ** 2))

        north_alpine_belt = 0.88 * np.exp(-(((nx - 0.46) / 0.24) ** 2 + ((ny - 0.18) / 0.11) ** 2))

        # 3. Trường nâng kiến tạo tổng hợp (Tectonic Uplift)
        uplift_fbm = self.uplift_noise.fbm_grid(nx, ny, octaves=4, base_scale=2.5)
        tectonic_uplift = np.clip(
            (np.maximum.reduce([spine_profile, nw_branch, north_alpine_belt]) * 0.78 + uplift_fbm * 0.22)
            * landmass.landmask,
            0.0,
            1.0,
        )

        # 4. Sống núi phân nhánh sắc nét (Ridge Field)
        raw_ridges = self._ridged_multifractal(nx, ny, octaves=5, base_scale=4.2)
        ridge_field = np.clip(raw_ridges * (0.35 + 0.65 * tectonic_uplift) * landmass.landmask, 0.0, 1.0)

        # 5. Bồn địa trũng (Basin Field):
        #    - Bồn địa nội lưu Tây Nam (SW Endorheic Rain-Shadow Basin)
        #    - Bồn địa hồ & đồng bằng Đông Bắc (NE Temperate Basin)
        sw_basin = 0.75 * np.exp(-(((nx - 0.29) / 0.11) ** 2 + ((ny - 0.64) / 0.11) ** 2))
        ne_basin = 0.60 * np.exp(-(((nx - 0.64) / 0.12) ** 2 + ((ny - 0.36) / 0.12) ** 2))
        basin_field = np.clip(np.maximum(sw_basin, ne_basin) * landmass.landmask, 0.0, 1.0)

        # 6. Vết đứt gãy địa chất tuyến tính (Fault Lines / Canyons)
        fault_signal = np.abs(self.fault_noise.noise_grid(nx * 5.5 + ny * 2.0, ny * 5.5 - nx * 2.0))
        fault_lines = np.clip((1.0 - np.clip(fault_signal * 12.0, 0.0, 1.0)) * tectonic_uplift, 0.0, 1.0)

        return GeologyResult(
            tectonic_uplift=tectonic_uplift.astype(np.float32),
            ridge_field=ridge_field.astype(np.float32),
            basin_field=basin_field.astype(np.float32),
            fault_lines=fault_lines.astype(np.float32),
        )
