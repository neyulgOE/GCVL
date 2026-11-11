"""
world/generation/geology_generator.py
Sinh hệ thống Dãy núi phân thủy sắc nét (Warped Ridged Multifractal),
Dãy núi Bắc Băng Dương, Sống lưng Trung tâm (Continental Spine),
và các bồn địa địa chất (Pontic Basin, Dathic Jungle Basin, Samark Plateau).
"""

import os
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

        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "demo_world_template.npz"
        )
        if os.path.exists(template_path):
            tmpl = np.load(template_path)
            roughness = tmpl["roughness"]
            is_snow = tmpl["is_snow"]
        else:
            roughness = np.zeros((h, w), dtype=np.float32)
            is_snow = np.zeros((h, w), dtype=bool)

        # 1. Trục Nâng Kiến Tạo Vĩ Mô (Tectonic Uplift Belts)
        # Sống lưng Trung tâm (Continental Spine) chạy dọc North-South
        wiggle = (self.warp_noise.fbm_grid(nx, ny, octaves=3, base_scale=2.5) - 0.5) * 0.08
        spine_x = 0.42 + 0.04 * np.sin(ny * np.pi * 2.2) + wiggle
        central_spine = np.exp(-(((nx - spine_x) / 0.075) ** 2)) * np.clip(1.35 - ny * 1.1, 0.0, 1.0)

        # Vòng cung Núi Băng Tuyết Phía Bắc (Northern Alpine Spine)
        north_spine = np.exp(-(((ny - 0.16 + wiggle * 0.4) / 0.085) ** 2)) * np.clip(
            1.0 - np.abs(nx - 0.52) / 0.46, 0.0, 1.0
        )

        # Dãy núi Đông Bắc & Bờ biển Đông
        ne_mountains = np.exp(-(((nx - 0.72) / 0.16) ** 2 + ((ny - 0.22) / 0.09) ** 2)) * 0.88

        # Vành đai núi đá quanh Hoang mạc Pontic & Samark
        macro_belts = np.maximum.reduce([central_spine, north_spine, ne_mountains])
        roughness_boost = np.clip(roughness * 3.4, 0.0, 0.88)
        roughness_boost[is_snow] = np.maximum(roughness_boost[is_snow], 0.95)

        tectonic_uplift = np.clip(
            (macro_belts * 0.42 + roughness_boost * 0.65) * land, 0.0, 1.0
        )

        # 2. Trường Sống núi sắc nhọn (Ridged Multifractal)
        ridged_detail = self._warped_ridged_multifractal(nx, ny, octaves=6, base_scale=4.5)
        ridge_field = np.clip(
            ridged_detail * (0.25 + 0.88 * (tectonic_uplift ** 0.8)) * land, 0.0, 1.0
        )

        # 3. Các Bồn địa Trũng (Sedimentary Basins)
        # Bồn địa hoang mạc Pontic Tây Nam
        pontic_basin = 0.85 * np.exp(-(((nx - 0.26) / 0.14) ** 2 + ((ny - 0.62) / 0.14) ** 2))
        # Bồn địa rừng nhiệt đới Dathic trung tâm
        dathic_basin = 0.75 * np.exp(-(((nx - 0.49) / 0.10) ** 2 + ((ny - 0.60) / 0.10) ** 2))
        # Cao nguyên bán khô hạn Samark Đông Nam
        samark_basin = 0.70 * np.exp(-(((nx - 0.64) / 0.11) ** 2 + ((ny - 0.74) / 0.11) ** 2))
        basin_field = np.clip(
            np.maximum.reduce([pontic_basin, dathic_basin, samark_basin]) * land, 0.0, 1.0
        )

        # 4. Các Đứt gãy Hẻm vực (Tectonic Gorges & Faults)
        fault_raw = np.abs(self.spur_noise.noise_grid(nx * 9.0 + ny * 3.0, ny * 9.0 - nx * 3.0))
        fault_lines = np.clip((1.0 - np.clip(fault_raw * 14.0, 0.0, 1.0)) * tectonic_uplift, 0.0, 1.0)

        return GeologyResult(
            tectonic_uplift=tectonic_uplift.astype(np.float32),
            ridge_field=ridge_field.astype(np.float32),
            basin_field=basin_field.astype(np.float32),
            fault_lines=fault_lines.astype(np.float32),
        )
