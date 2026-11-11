"""
world/config/world_config.py
Cấu hình thế giới đa lục địa hoàn chỉnh (Multi-Continent Primeval Reach)
với tỷ lệ chuẩn 16:10 (800x520 raster -> 1600x1040 px Atlas).
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class WorldConfig:
    world_id: str = "primeval_reach_v3"
    seed: int = 2026
    version: str = "3.0.0"

    # Lưới World Raster 512x512 (khi upscale x2 = 1024x1024 px chuẩn 1:1 square)
    width: int = 512
    height: int = 512

    # Độ phân giải Local Map trong Runtime
    local_cols: int = 80
    local_rows: int = 80

    # Ngưỡng kiểm định hình thái đa lục địa (Multi-continent: 40% - 52% đất nổi, nhiều lục địa lớn)
    sea_level: float = 0.38
    target_land_ratio_min: float = 0.40
    target_land_ratio_max: float = 0.52
    min_main_continent_share: float = 0.42
    min_isthmus_width_px: int = 6

    # Trọng số tổng hợp địa hình đa tầng
    weight_base_elevation: float = 0.36
    weight_tectonic_uplift: float = 0.34
    weight_ridge_field: float = 0.32
    weight_basin_field: float = 0.16
    weight_erosion_field: float = 0.10
    weight_detail_noise: float = 0.08

    # Thông số chiếu sáng đa hướng (Multi-directional Relief Shading)
    sun_azimuth_deg: float = 315.0
    sun_altitude_deg: float = 42.0
    vertical_exaggeration: float = 6.5

    candidate_seeds: Tuple[int, int, int] = (2026, 4093, 7719)
