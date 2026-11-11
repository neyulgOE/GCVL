"""
world/generation/soil_generator.py
Phase 5A: Phân bổ 7 loại đất tự nhiên (Soil Types) và các chỉ số vật lý của đất
từ dữ liệu Địa chất, Địa hình, Khí hậu và Thủy văn.
"""

from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np

try:
    from scipy.ndimage import distance_transform_edt
except ImportError:
    def distance_transform_edt(a: np.ndarray) -> np.ndarray:
        """
        Pure-NumPy Euclidean Distance Transform fallback when scipy is not available.
        Calculates distance from non-zero elements to the closest zero element.
        """
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
from world.generation.terrain_generator import TerrainResult
from world.generation.climate_generator import ClimateResult
from world.generation.hydrology_generator import HydrologyResult


# Mã định danh 7 loại đất chuẩn trên đất liền (0 dành cho Đáy biển / Mặt nước)
SOIL_WATER_BED = 0
SOIL_ROCKY = 1        # Đất đá / Đá vụn sườn dốc (Lithosol / Talus Scree)
SOIL_PERMAFROST = 2   # Đất đóng băng vĩnh cửu cận cực (Cryosol / Permafrost)
SOIL_SANDY = 3        # Đất cát bờ biển & hoang mạc khuất mưa (Arenosol)
SOIL_CLAY = 4         # Đất sét bồn trũng nội địa (Vertisol / Clay Basin)
SOIL_PEAT = 5         # Than bùn đầm lầy ngập nước (Histosol / Peat Bog)
SOIL_ALLUVIAL = 6     # Đất phù sa bãi bồi sông & châu thổ (Fluvisol / Alluvium)
SOIL_HUMUS = 7        # Đất mùn giàu hữu cơ dưới tán rừng & đồng cỏ ẩm (Humus / Mollisol)

SOIL_NAMES: Dict[int, str] = {
    SOIL_WATER_BED: "Water / Seabed",
    SOIL_ROCKY: "Rocky / Talus Soil",
    SOIL_PERMAFROST: "Permafrost Soil",
    SOIL_SANDY: "Sandy Soil",
    SOIL_CLAY: "Clay Basin Soil",
    SOIL_PEAT: "Peat / Wetland Soil",
    SOIL_ALLUVIAL: "Alluvial Floodplain Soil",
    SOIL_HUMUS: "Forest Humus / Loam",
}

SOIL_PALETTE_RGB: Dict[int, Tuple[int, int, int]] = {
    SOIL_WATER_BED: (28, 72, 108),
    SOIL_ROCKY: (132, 128, 124),       # Xám đá sườn núi
    SOIL_PERMAFROST: (178, 196, 210),  # Xám xanh băng giá
    SOIL_SANDY: (218, 184, 114),       # Vàng cát / đất son khô
    SOIL_CLAY: (168, 112, 78),         # Nâu đỏ đất sét bồn địa
    SOIL_PEAT: (72, 62, 52),           # Nâu đen than bùn đầm lầy
    SOIL_ALLUVIAL: (154, 142, 96),     # Nâu vàng phù sa ven sông
    SOIL_HUMUS: (84, 108, 64),         # Nâu xanh đất mùn rừng
}


@dataclass
class SoilResult:
    soil_id: np.ndarray            # Mã loại đất chính tại mỗi ô (uint8, 0..7)
    soil_weights: np.ndarray       # Xác suất pha trộn 8 lớp đất (H, W, 8) tạo ranh giới mềm
    soil_moisture: np.ndarray      # Độ ẩm đất thực tế [0..1]
    soil_fertility: np.ndarray     # Độ phì nhiêu hữu cơ [0..1]
    drainage_capacity: np.ndarray  # Khả năng thoát nước [0..1] (Cát/Đá cao, Sét/Than bùn thấp)
    distance_to_water: np.ndarray  # Khoảng cách Euclid tới sông/hồ/vịnh gần nhất [px]


class SoilGenerator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config
        self.soil_noise = FastNoise2D(seed=config.seed + 2029)

    def generate(
        self,
        landmass: LandmassResult,
        geology: GeologyResult,
        terrain: TerrainResult,
        climate: ClimateResult,
        hydrology: HydrologyResult,
    ) -> SoilResult:
        h, w = self.cfg.height, self.cfg.width
        land = landmass.landmask
        elev = terrain.final_heightmap
        slope = terrain.slope
        temp = climate.temperature
        precip = climate.precipitation

        ny, nx = np.meshgrid(
            np.linspace(0.0, 1.0, h, dtype=np.float32),
            np.linspace(0.0, 1.0, w, dtype=np.float32),
            indexing="ij",
        )
        micro_var = (self.soil_noise.fbm_grid(nx, ny, octaves=4, base_scale=6.5) - 0.5) * 0.16

        # 1. Tính khoảng cách tới mặt nước ngọt (Sông, Hồ) và tới Bờ biển
        freshwater_mask = hydrology.river_mask | hydrology.lake_mask
        dist_to_freshwater = distance_transform_edt(~freshwater_mask).astype(np.float32)
        dist_to_sea = distance_transform_edt(land).astype(np.float32)
        dist_to_any_water = np.minimum(dist_to_freshwater, dist_to_sea)

        # 2. Độ ẩm đất tổng hợp (Soil Moisture) = Lượng mưa + Thấm nước ngầm ven sông - Thoát nước sườn dốc
        riparian_seepage = np.exp(-dist_to_freshwater / 9.5) * 0.48
        basin_retention = geology.basin_field * 0.22
        slope_runoff_loss = slope * 0.35

        soil_moisture = np.clip(
            (precip * 0.65 + riparian_seepage + basin_retention - slope_runoff_loss + micro_var * 0.5) * land,
            0.02,
            1.0,
        ).astype(np.float32)

        # 3. Tính điểm phù hợp (Suitability Scores) cho từng loại trong 7 loại đất
        scores = np.zeros((h, w, 8), dtype=np.float32)

        # (1) Đất đóng băng (Permafrost): Vùng Bắc Cao & đỉnh núi lạnh (temperature < 0.26)
        scores[:, :, SOIL_PERMAFROST] = (
            np.clip((0.28 - temp) * 4.2, 0.0, 1.0)
            * (0.65 + 0.35 * (1.0 - slope))
            + micro_var * 0.4
        )

        # (2) Đất đá (Rocky / Talus): Sườn dốc lớn, sống núi cao và vách đứt gãy
        scores[:, :, SOIL_ROCKY] = (
            slope * 1.45
            + geology.ridge_field * 0.65
            + np.clip((elev - 0.64) * 2.5, 0.0, 0.8)
            + micro_var * 0.3
        )

        # (3) Đất phù sa (Alluvial): Bãi bồi dọc sông lớn, hợp lưu và châu thổ cửa biển
        river_corridor = np.exp(-dist_to_freshwater / 3.5) * np.clip(hydrology.flow_accumulation / 35.0, 0.4, 2.0)
        scores[:, :, SOIL_ALLUVIAL] = (
            river_corridor * (1.0 - slope * 0.8) * 1.65
            + hydrology.delta_mask.astype(np.float32) * 1.65
            + micro_var * 0.3
        )

        # (4) Than bùn (Peat): Vùng trũng ẩm ướt quanh Vịnh Nội Địa Đông Nam, đầm lầy cửa sông & ven hồ lạnh
        low_flat = np.clip(1.0 - (elev - self.cfg.sea_level) * 4.5, 0.0, 1.0) * (1.0 - slope)
        scores[:, :, SOIL_PEAT] = (
            (soil_moisture ** 1.4) * low_flat * 1.15
            + np.exp(-dist_to_freshwater / 6.0) * (precip > 0.62) * 0.45
            + micro_var * 0.3
        )

        # (5) Đất cát (Sandy): Bãi biển ven đại dương + Hoang mạc khuất mưa Tây Nam (Rain Shadow)
        coastal_sand = np.exp(-dist_to_sea / 3.2) * (1.0 - slope) * 0.88
        arid_desert_sand = climate.aridity_index * (0.65 + 0.35 * climate.rain_shadow) * 1.15
        scores[:, :, SOIL_SANDY] = np.maximum(coastal_sand, arid_desert_sand) + micro_var * 0.35

        # (6) Đất sét (Clay): Bồn địa trũng nội lục, thung lũng bán khô hạn & rìa hồ nội lưu
        scores[:, :, SOIL_CLAY] = (
            geology.basin_field * 0.95
            + (1.0 - slope) * np.clip(1.0 - np.abs(soil_moisture - 0.45) * 2.5, 0.0, 0.6)
            + np.exp(-distance_transform_edt(~hydrology.endorheic_lake_mask) / 10.0) * 0.55
            + micro_var * 0.35
        )

        # (7) Đất mùn (Humus): Rừng ôn đới, rừng hỗn hợp và sườn đồi ẩm thoát nước tốt
        moderate_temp = np.clip(1.0 - np.abs(temp - 0.54) * 2.2, 0.0, 1.0)
        scores[:, :, SOIL_HUMUS] = (
            soil_moisture * moderate_temp * (1.0 - slope * 0.55) * 1.25
            + (precip * 0.55)
            + micro_var * 0.35
        )

        # Xóa điểm trên vùng mặt nước (Biển, Sông, Hồ)
        water_surface = (~land) | hydrology.river_mask | hydrology.lake_mask
        for s_idx in range(1, 8):
            scores[:, :, s_idx] = np.where(water_surface, 0.0, np.maximum(0.01, scores[:, :, s_idx]))
        scores[:, :, SOIL_WATER_BED] = np.where(water_surface, 1.0, 0.0)

        # Chuẩn hóa thành trọng số pha trộn mềm (Soft Blending Weights)
        exp_scores = np.exp(scores * 4.5)
        exp_scores[:, :, SOIL_WATER_BED] = np.where(water_surface, 100.0, 0.0)
        for s_idx in range(1, 8):
            exp_scores[:, :, s_idx] = np.where(water_surface, 0.0, exp_scores[:, :, s_idx])

        sum_weights = np.maximum(1e-6, np.sum(exp_scores, axis=-1, keepdims=True))
        soil_weights = (exp_scores / sum_weights).astype(np.float32)

        # Loại đất chiếm ưu thế tại mỗi ô
        soil_id = np.argmax(soil_weights, axis=-1).astype(np.uint8)
        soil_id = np.where(water_surface, SOIL_WATER_BED, soil_id)

        # 4. Tính Độ phì nhiêu (Fertility) & Khả năng thoát nước (Drainage)
        fertility = np.clip(
            soil_weights[:, :, SOIL_ALLUVIAL] * 0.95
            + soil_weights[:, :, SOIL_HUMUS] * 0.90
            + soil_weights[:, :, SOIL_PEAT] * 0.65
            + soil_weights[:, :, SOIL_CLAY] * 0.55
            + soil_weights[:, :, SOIL_SANDY] * 0.18
            + soil_weights[:, :, SOIL_ROCKY] * 0.10
            + soil_weights[:, :, SOIL_PERMAFROST] * 0.08,
            0.0,
            1.0,
        ).astype(np.float32)

        drainage = np.clip(
            soil_weights[:, :, SOIL_SANDY] * 0.95
            + soil_weights[:, :, SOIL_ROCKY] * 0.90
            + soil_weights[:, :, SOIL_HUMUS] * 0.65
            + soil_weights[:, :, SOIL_ALLUVIAL] * 0.55
            + soil_weights[:, :, SOIL_CLAY] * 0.22
            + soil_weights[:, :, SOIL_PEAT] * 0.12
            + soil_weights[:, :, SOIL_PERMAFROST] * 0.05,
            0.0,
            1.0,
        ).astype(np.float32)

        return SoilResult(
            soil_id=soil_id,
            soil_weights=soil_weights,
            soil_moisture=soil_moisture,
            soil_fertility=fertility,
            drainage_capacity=drainage,
            distance_to_water=dist_to_any_water,
        )
