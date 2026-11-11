"""
world/generation/terrain_generator.py
Kết hợp Địa hình Đa tầng với Multi-Directional Hillshading (Bóng đổ đa hướng 3D)
giúp các dãy núi, thung lũng và cao nguyên nổi khối rõ rệt ngay cả ở kích thước thumbnail.
"""

import math
from dataclasses import dataclass
import numpy as np

try:
    from scipy.ndimage import distance_transform_edt
except ImportError:
    def distance_transform_edt(a: np.ndarray) -> np.ndarray:
        """Pure-NumPy Euclidean Distance Transform fallback when scipy is not available."""
        h, w = a.shape
        inf = 1e8
        g = np.full((h, w), inf, dtype=np.float32)
        cur = np.full(w, inf, dtype=np.float32)
        for r in range(h):
            cur = np.where(~a[r], 0.0, cur + 1.0)
            g[r] = cur
        cur = np.full(w, inf, dtype=np.float32)
        for r in range(h - 1, -1, -1):
            cur = np.where(~a[r], 0.0, cur + 1.0)
            g[r] = np.minimum(g[r], cur)
        g = g ** 2
        dt2 = np.full((h, w), inf, dtype=np.float32)
        for dc in range(-50, 51):
            sq = float(dc * dc)
            if dc < 0:
                shifted = np.pad(g[:, :dc], ((0, 0), (-dc, 0)), constant_values=inf)
            elif dc > 0:
                shifted = np.pad(g[:, dc:], ((0, 0), (0, dc)), constant_values=inf)
            else:
                shifted = g
            dt2 = np.minimum(dt2, shifted + sq)
        return np.sqrt(dt2).astype(np.float32)

from world.config.world_config import WorldConfig
from world.generation.landmass_generator import FastNoise2D, LandmassResult
from world.generation.geology_generator import GeologyResult


@dataclass
class TerrainResult:
    final_heightmap: np.ndarray
    erosion_field: np.ndarray
    slope: np.ndarray
    aspect: np.ndarray
    curvature: np.ndarray
    shaded_relief: np.ndarray


class TerrainGenerator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config
        self.detail_noise = FastNoise2D(seed=config.seed + 911)
        self.gully_noise = FastNoise2D(seed=config.seed + 1103)

    def generate(self, landmass: LandmassResult, geology: GeologyResult) -> TerrainResult:
        h, w = self.cfg.height, self.cfg.width
        ny, nx = np.meshgrid(
            np.linspace(0.0, 1.0, h, dtype=np.float32),
            np.linspace(0.0, 1.0, w, dtype=np.float32),
            indexing="ij",
        )
        land = landmass.landmask

        # Khoảng cách từ bờ biển vào sâu trong lục địa (giúp bờ biển thoai thoải tự nhiên, không bị dựng vách giả)
        dist_inland = distance_transform_edt(land).astype(np.float32)
        coastal_taper = np.clip(dist_inland / 22.0, 0.0, 1.0) ** 0.75

        # 1. Nhiễu khe xói mòn sườn núi (Branching Gullies)
        gully_val = 1.0 - np.abs(self.gully_noise.noise_grid(nx * 24.0, ny * 24.0))
        erosion_gullies = -np.clip((gully_val ** 3.0) * geology.tectonic_uplift * 0.14, 0.0, 0.14)

        detail = (self.detail_noise.fbm_grid(nx * 1.5, ny, octaves=6, base_scale=10.0) - 0.5) * 2.0

        # 2. Tổng hợp Độ cao theo đúng công thức kiến tạo
        continent_relief = (
            geology.tectonic_uplift * self.cfg.weight_tectonic_uplift
            + (geology.ridge_field ** 1.15) * self.cfg.weight_ridge_field
            - geology.basin_field * self.cfg.weight_basin_field
            - geology.fault_lines * 0.09
            + erosion_gullies
            + detail * self.cfg.weight_detail_noise
        ) * coastal_taper

        final_heightmap = np.where(
            land,
            np.clip(self.cfg.sea_level + 0.005 + continent_relief * 0.92 + (landmass.base_elevation - self.cfg.sea_level) * 0.35, self.cfg.sea_level + 0.002, 1.0),
            landmass.base_elevation,
        ).astype(np.float32)

        # 3. Tính đạo hàm hình học: Slope, Aspect, Curvature
        dz_dy, dz_dx = np.gradient(final_heightmap)
        slope_raw = np.hypot(dz_dx, dz_dy)
        slope = np.clip(slope_raw * 22.0, 0.0, 1.0).astype(np.float32)
        aspect = np.arctan2(dz_dy, -dz_dx).astype(np.float32)

        laplacian = (
            np.roll(final_heightmap, 1, axis=0)
            + np.roll(final_heightmap, -1, axis=0)
            + np.roll(final_heightmap, 1, axis=1)
            + np.roll(final_heightmap, -1, axis=1)
            - 4.0 * final_heightmap
        )
        curvature = np.clip(laplacian * 32.0, -1.0, 1.0).astype(np.float32)

        # 4. Multi-Directional Hillshading (Chiếu sáng 3 góc kết hợp: Tây-Bắc chính + Bắc-Đông phụ + Tây-Nam dịu)
        shaded_relief = self._compute_multidirectional_hillshade(dz_dx, dz_dy, slope_raw)

        return TerrainResult(
            final_heightmap=final_heightmap,
            erosion_field=erosion_gullies.astype(np.float32),
            slope=slope,
            aspect=aspect,
            curvature=curvature,
            shaded_relief=shaded_relief,
        )

    def _compute_multidirectional_hillshade(
        self, dz_dx: np.ndarray, dz_dy: np.ndarray, slope_raw: np.ndarray
    ) -> np.ndarray:
        """Kỹ thuật chiếu sáng bản đồ địa chất USGS (3 nguồn sáng lệch góc) giúp sườn núi mọi hướng đều nổi khối 3D."""
        slope_rad = np.arctan(slope_raw * self.cfg.vertical_exaggeration * 55.0)
        aspect_rad = np.arctan2(dz_dy, -dz_dx)

        lights = [
            (315.0, 38.0, 0.62),  # Ánh sáng chính từ Tây-Bắc
            (270.0, 42.0, 0.23),  # Ánh sáng phụ từ hướng Tây
            (355.0, 48.0, 0.15),  # Ánh sáng ven từ hướng Bắc
        ]
        combined = np.zeros_like(slope_raw, dtype=np.float32)
        for az_deg, alt_deg, weight in lights:
            az = math.radians(az_deg)
            zenith = math.pi / 2.0 - math.radians(alt_deg)
            sh = np.cos(zenith) * np.cos(slope_rad) + np.sin(zenith) * np.sin(slope_rad) * np.cos(az - aspect_rad)
            combined += np.clip(sh, 0.0, 1.0) * weight

        return np.clip(combined, 0.0, 1.0).astype(np.float32)
