"""
world/config/world_config.py
Cấu hình chuẩn tỷ lệ 16:10 (800x520 raster -> 1600x1040 px Atlas) theo đúng tài liệu PDF.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class WorldConfig:
    world_id: str = "primeval_reach_v2"
    seed: int = 2026
    version: str = "2.0.0"

    # Tỷ lệ chuẩn 16:10 như ảnh mẫu trong PDF (800x520 x2 = 1600x1040 px)
    width: int = 800
    height: int = 520

    # Độ phân giải Local Map trong Runtime
    local_cols: int = 80
    local_rows: int = 80

    # Ngưỡng kiểm định hình thái lục địa (30% - 38% diện tích đất nổi)
    sea_level: float = 0.38
    target_land_ratio_min: float = 0.30
    target_land_ratio_max: float = 0.38
    min_main_continent_share: float = 0.85
    min_isthmus_width_px: int = 12

    # Trọng số tổng hợp địa hình đa tầng (Tăng độ nổi sống núi & thung lũng)
    weight_base_elevation: float = 0.38
    weight_tectonic_uplift: float = 0.28
    weight_ridge_field: float = 0.28
    weight_basin_field: float = 0.18
    weight_erosion_field: float = 0.12
    weight_detail_noise: float = 0.08

    # Thông số chiếu sáng đa hướng (Multi-directional Relief Shading)
    sun_azimuth_deg: float = 315.0
    sun_altitude_deg: float = 38.0
    vertical_exaggeration: float = 7.5

    candidate_seeds: Tuple[int, int, int] = (2026, 4093, 7719)
