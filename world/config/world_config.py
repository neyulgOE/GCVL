"""
world/config/world_config.py
Cấu hình trung tâm (Single Source of Truth) cho hệ thống sinh thế giới Primeval Reach.
"""

from dataclasses import dataclass, field
from typing import Tuple, List


@dataclass(frozen=True)
class WorldConfig:
    world_id: str = "primeval_reach_v1"
    seed: int = 2026
    version: str = "1.0.0"

    # Độ phân giải World Raster (mặc định 512x512, có thể mở rộng lên 1024x1024)
    width: int = 512
    height: int = 512

    # Độ phân giải Local Map khi zoom vào từng ô/vùng trong Runtime
    local_cols: int = 80
    local_rows: int = 80

    # Ngưỡng kiểm định hình thái lục địa (Landmass & Bathymetry)
    sea_level: float = 0.38
    target_land_ratio_min: float = 0.30
    target_land_ratio_max: float = 0.38
    min_main_continent_share: float = 0.85  # Lục địa chính chiếm tối thiểu 85% tổng diện tích đất nổi
    min_isthmus_width_px: int = 10          # Độ rộng tối thiểu của eo đất nối quanh vịnh nội địa

    # Trọng số tổng hợp địa hình (Terrain Composition Weights)
    weight_base_elevation: float = 0.44
    weight_tectonic_uplift: float = 0.24
    weight_ridge_field: float = 0.22
    weight_basin_field: float = 0.16
    weight_erosion_field: float = 0.08
    weight_detail_noise: float = 0.06

    # Thông số ánh sáng kết xuất bản đồ nổi khối (Relief Hillshading)
    sun_azimuth_deg: float = 315.0  # Hướng Tây-Bắc (NW)
    sun_altitude_deg: float = 42.0
    vertical_exaggeration: float = 4.5

    # Danh sách 3 seed ứng viên để xuất 3 phương án hình dáng lục địa ở Phase 1
    candidate_seeds: Tuple[int, int, int] = (2026, 4093, 7719)
