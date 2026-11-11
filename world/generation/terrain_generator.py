"""
world/generation/terrain_generator.py
Kết hợp các trường địa chất thành Heightmap hoàn chỉnh, mô phỏng xói mòn sườn dốc
và tính toán các đạo hàm hình học: Slope (Độ dốc), Aspect (Hướng sườn), Curvature (Độ cong).
"""

import math
from dataclasses import dataclass
import numpy as np
from world.config.world_config import WorldConfig
from world.generation.landmass_generator import FastNoise2D, LandmassResult
from world.generation.geology_generator import GeologyResult


@dataclass
class TerrainResult:
    final_heightmap: np.ndarray  # Độ cao chuẩn hóa [0..1]
    erosion_field: np.ndarray    # Trường xói mòn nhiệt & thủy lực vùng sườn núi
    slope: np.ndarray            # Độ dốc bề mặt [0..1]
    aspect: np.ndarray           # Hướng sườn dốc (radian [-pi..pi])
    curvature: np.ndarray        # Độ cong Laplacian (Dương: Đỉnh lồi, Âm: Khe lõm)
    shaded_relief: np.ndarray    # Bản đồ bóng đổ sườn núi (Hillshading [0..1])


class TerrainGenerator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config
        self.detail_noise = FastNoise2D(seed=config.seed + 911)

    def generate(self, landmass: LandmassResult, geology: GeologyResult) -> TerrainResult:
        h, w = self.cfg.height, self.cfg.width
        ny, nx = np.meshgrid(
            np.linspace(0.0, 1.0, h, dtype=np.float32),
            np.linspace(0.0, 1.0, w, dtype=np.float32),
            indexing="ij",
        )

        # 1. Nhiễu chi tiết vi mô (Micro Detail Noise)
        detail = (self.detail_noise.fbm_grid(nx, ny, octaves=6, base_scale=9.5) - 0.5) * 2.0

        # 2. Kết hợp sơ bộ trước xói mòn
        raw_height = (
            landmass.base_elevation * self.cfg.weight_base_elevation
            + geology.tectonic_uplift * self.cfg.weight_tectonic_uplift
            + geology.ridge_field * self.cfg.weight_ridge_field
            - geology.basin_field * self.cfg.weight_basin_field
            - geology.fault_lines * 0.07
            + detail * self.cfg.weight_detail_noise
        )

        # Đảm bảo vùng đất nổi luôn cao hơn mực nước biển (sea_level)
        land_elev = np.where(
            landmass.landmask,
            np.maximum(self.cfg.sea_level + 0.008, raw_height + 0.22),
            landmass.base_elevation,
        )

        # 3. Mô phỏng Xói mòn Địa mạo (Thermal & Valley Carving Erosion Approximation)
        #    Làm mượt các thung lũng chữ U nhưng giữ nguyên độ sắc nét của sống núi
        neighbor_avg = (
            np.roll(land_elev, 1, axis=0)
            + np.roll(land_elev, -1, axis=0)
            + np.roll(land_elev, 1, axis=1)
            + np.roll(land_elev, -1, axis=1)
        ) * 0.25
        erosion_field = (neighbor_avg - land_elev) * (1.0 - geology.ridge_field * 0.75) * landmass.landmask

        final_heightmap = np.clip(
            land_elev + erosion_field * self.cfg.weight_erosion_field,
            0.0,
            1.0,
        ).astype(np.float32)

        # 4. Tính Đạo hàm Bề mặt: Slope, Aspect, Curvature
        dz_dy, dz_dx = np.gradient(final_heightmap)
        slope_raw = np.hypot(dz_dx, dz_dy)
        slope = np.clip(slope_raw * 18.0, 0.0, 1.0).astype(np.float32)

        aspect = np.arctan2(dz_dy, -dz_dx).astype(np.float32)

        laplacian = (
            np.roll(final_heightmap, 1, axis=0)
            + np.roll(final_heightmap, -1, axis=0)
            + np.roll(final_heightmap, 1, axis=1)
            + np.roll(final_heightmap, -1, axis=1)
            - 4.0 * final_heightmap
        )
        curvature = np.clip(laplacian * 25.0, -1.0, 1.0).astype(np.float32)

        # 5. Tính Hillshading (Shaded Relief) chuẩn quang học
        azimuth_rad = math.radians(self.cfg.sun_azimuth_deg)
        altitude_rad = math.radians(self.cfg.sun_altitude_deg)
        zenith_rad = math.pi / 2.0 - altitude_rad

        slope_rad = np.arctan(slope_raw * self.cfg.vertical_exaggeration * 45.0)
        aspect_math = np.arctan2(dz_dy, -dz_dx)

        shaded = (
            np.cos(zenith_rad) * np.cos(slope_rad)
            + np.sin(zenith_rad) * np.sin(slope_rad) * np.cos(azimuth_rad - aspect_math)
        )
        shaded_relief = np.clip(shaded, 0.0, 1.0).astype(np.float32)

        return TerrainResult(
            final_heightmap=final_heightmap,
            erosion_field=erosion_field.astype(np.float32),
            slope=slope,
            aspect=aspect,
            curvature=curvature,
            shaded_relief=shaded_relief,
        )
