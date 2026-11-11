"""
world/generation/biome_generator.py
Phase 5B: Tổng hợp Khí hậu + Độ cao + Thổ nhưỡng + Thủy văn thành 11 Quần xã (Biomes)
với dải chuyển tiếp sinh thái mềm (Soft Ecotone Transition Bands).
"""

from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np

from world.config.world_config import WorldConfig
from world.generation.landmass_generator import FastNoise2D, LandmassResult
from world.generation.geology_generator import GeologyResult
from world.generation.terrain_generator import TerrainResult
from world.generation.climate_generator import ClimateResult
from world.generation.hydrology_generator import HydrologyResult
from world.generation.soil_generator import (
    SoilResult,
    SOIL_ROCKY,
    SOIL_PERMAFROST,
    SOIL_SANDY,
    SOIL_CLAY,
    SOIL_PEAT,
    SOIL_ALLUVIAL,
    SOIL_HUMUS,
)


# Mã định danh Đại dương / Mặt nước (0) và 11 Quần xã Trên cạn (1..11)
BIOME_WATER = 0
BIOME_ALPINE_ICE_SNOW = 1       # 1. Băng tuyết & Đỉnh đá cao (Northern Alpine Ice & Snow)
BIOME_TUNDRA = 2                # 2. Đài nguyên cận cực (Subpolar Tundra)
BIOME_BOREAL_TAIGA = 3          # 3. Rừng lá kim phương Bắc & Sườn đón gió Tây Bắc (Boreal Conifer Forest)
BIOME_MIXED_FOREST = 4          # 4. Rừng hỗn hợp (Mixed Conifer-Broadleaf Forest)
BIOME_TEMPERATE_DECIDUOUS = 5   # 5. Rừng ôn đới lá rộng (Temperate Deciduous Forest)
BIOME_MOIST_BAY_FOREST = 6      # 6. Rừng ẩm cận nhiệt đới quanh Vịnh Nội Địa (Warm Moist Forest)
BIOME_RIPARIAN_FOREST = 7       # 7. Rừng hành lang ven sông & bãi bồi (Riparian Gallery Forest)
BIOME_WETLAND_SWAMP = 8         # 8. Đầm lầy & Châu thổ ngập nước (Wetland / Marsh / Fen)
BIOME_TEMPERATE_MEADOW = 9      # 9. Đồng cỏ ôn đới mở (Open Steppe Meadow / Grassland)
BIOME_DRY_SAVANNA_STEPPE = 10   # 10. Thảo nguyên khô vàng nhạt (Dry Rain-Shadow Steppe)
BIOME_SEMI_ARID_DESERT = 11     # 11. Bán hoang mạc & Hoang mạc đất son Tây Nam (Arid Badlands & Dunes)

BIOME_NAMES: Dict[int, str] = {
    BIOME_WATER: "Ocean / River / Lake",
    BIOME_ALPINE_ICE_SNOW: "1. Alpine Ice & Snow",
    BIOME_TUNDRA: "2. Subpolar Tundra",
    BIOME_BOREAL_TAIGA: "3. Boreal Conifer Forest",
    BIOME_MIXED_FOREST: "4. Mixed Forest",
    BIOME_TEMPERATE_DECIDUOUS: "5. Temperate Deciduous Forest",
    BIOME_MOIST_BAY_FOREST: "6. Warm Moist Forest",
    BIOME_RIPARIAN_FOREST: "7. Riparian Corridor Forest",
    BIOME_WETLAND_SWAMP: "8. Wetland & Delta Marsh",
    BIOME_TEMPERATE_MEADOW: "9. Open Temperate Meadow",
    BIOME_DRY_SAVANNA_STEPPE: "10. Dry Steppe",
    BIOME_SEMI_ARID_DESERT: "11. Semi-Arid / Red Desert",
}

# Bảng màu Tự nhiên chuẩn cho 11 Quần xã
BIOME_PALETTE_RGB: Dict[int, Tuple[int, int, int]] = {
    BIOME_WATER: (42, 92, 136),
    BIOME_ALPINE_ICE_SNOW: (248, 252, 255),     # Trắng băng tuyết sáng
    BIOME_TUNDRA: (165, 175, 155),              # Xám rêu đài nguyên lạnh
    BIOME_BOREAL_TAIGA: (42, 88, 56),           # Xanh thông đậm vùng Tây Bắc & Bắc
    BIOME_MIXED_FOREST: (64, 122, 52),          # Xanh rừng hỗn hợp Đông Bắc
    BIOME_TEMPERATE_DECIDUOUS: (88, 142, 58),   # Xanh lá rộng ôn đới
    BIOME_MOIST_BAY_FOREST: (28, 82, 24),       # Xanh ngọc lục bảo Dathic Jungle
    BIOME_RIPARIAN_FOREST: (56, 132, 68),       # Xanh tươi hành lang ven sông
    BIOME_WETLAND_SWAMP: (74, 108, 82),         # Xanh nâu rêu đầm lầy
    BIOME_TEMPERATE_MEADOW: (138, 178, 72),     # Xanh ô-liu sáng đồng cỏ mở
    BIOME_DRY_SAVANNA_STEPPE: (208, 188, 116),  # Vàng cỏ khô thảo nguyên khuất mưa
    BIOME_SEMI_ARID_DESERT: (240, 212, 132),    # Vàng cát rực rỡ Pontic & Samark Desert
}


@dataclass
class BiomeResult:
    primary_biome_id: np.ndarray     # Quần xã chính (uint8, 0..11)
    secondary_biome_id: np.ndarray   # Quần xã thứ cấp tại dải chuyển tiếp (uint8, 0..11)
    biome_weights: np.ndarray        # Trọng số pha trộn mềm (H, W, 12)
    ecotone_factor: np.ndarray       # Độ mạnh của dải chuyển tiếp [0..1] (cao ở ranh giới giữa 2 biome)
    blended_biome_rgb: np.ndarray    # Ảnh màu RGB đã nội suy mềm qua dải chuyển tiếp (H, W, 3)


class BiomeGenerator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config
        self.ecotone_noise = FastNoise2D(seed=config.seed + 3301)

    def generate(
        self,
        landmass: LandmassResult,
        geology: GeologyResult,
        terrain: TerrainResult,
        climate: ClimateResult,
        hydrology: HydrologyResult,
        soil: SoilResult,
    ) -> BiomeResult:
        h, w = self.cfg.height, self.cfg.width
        land = landmass.landmask
        elev = terrain.final_heightmap
        slope = terrain.slope
        temp = climate.temperature
        precip = climate.precipitation
        aridity = climate.aridity_index
        shadow = climate.rain_shadow
        moist = soil.soil_moisture
        sw = soil.soil_weights

        ny, nx = np.meshgrid(
            np.linspace(0.0, 1.0, h, dtype=np.float32),
            np.linspace(0.0, 1.0, w, dtype=np.float32),
            indexing="ij",
        )
        # Nhiễu làm răng cưa mềm ranh giới chuyển tiếp (Dithered Ecotone Warping)
        dither = (self.ecotone_noise.fbm_grid(nx, ny, octaves=4, base_scale=7.5) - 0.5) * 0.14

        affinities = np.zeros((h, w, 12), dtype=np.float32)

        # 1. Băng tuyết & Đỉnh núi cao (Alpine Ice & Snow)
        affinities[:, :, BIOME_ALPINE_ICE_SNOW] = (
            np.clip((0.22 - temp) * 5.0, 0.0, 1.2)
            + np.clip((elev - 0.72) * 3.8, 0.0, 1.0)
            + dither * 0.4
        )

        # 2. Đài nguyên cận cực (Tundra)
        tundra_temp = np.exp(-(((temp - 0.25) / 0.09) ** 2))
        affinities[:, :, BIOME_TUNDRA] = (
            tundra_temp * 0.95
            + sw[:, :, SOIL_PERMAFROST] * 0.55
            + sw[:, :, SOIL_ROCKY] * (temp < 0.34) * 0.35
            + dither * 0.45
        )

        # 3. Rừng lá kim (Boreal Conifer / Taiga) - Mạnh ở Tây Bắc đón gió & sườn núi Bắc
        taiga_temp = np.exp(-(((temp - 0.38) / 0.12) ** 2))
        affinities[:, :, BIOME_BOREAL_TAIGA] = (
            taiga_temp * np.clip(precip * 1.45, 0.2, 1.1)
            + (nx < 0.45) * (ny < 0.50) * precip * 0.35
            + dither * 0.45
        )

        # 4. Rừng hỗn hợp (Mixed Forest) - Đông Bắc & Sườn trung bình
        mixed_temp = np.exp(-(((temp - 0.50) / 0.13) ** 2))
        affinities[:, :, BIOME_MIXED_FOREST] = (
            mixed_temp * np.clip(moist * 1.35, 0.2, 1.0)
            + sw[:, :, SOIL_HUMUS] * 0.38
            + (nx >= 0.48) * (ny < 0.52) * 0.22
            + dither * 0.45
        )

        # 5. Rừng ôn đới lá rộng (Temperate Deciduous Forest)
        decid_temp = np.exp(-(((temp - 0.60) / 0.13) ** 2))
        affinities[:, :, BIOME_TEMPERATE_DECIDUOUS] = (
            decid_temp * np.clip(precip * 1.35, 0.0, 1.0) * (1.0 - shadow * 0.6)
            + sw[:, :, SOIL_HUMUS] * 0.42
            + dither * 0.45
        )

        # 6. Rừng ẩm quanh Vịnh Nội Địa Đông Nam (Warm Moist Forest)
        warm_humid = np.clip((temp - 0.46) * 2.6, 0.0, 1.0) * np.clip((precip - 0.40) * 2.6, 0.0, 1.1)
        affinities[:, :, BIOME_MOIST_BAY_FOREST] = (
            warm_humid * 1.35
            + (nx > 0.48) * (ny > 0.48) * moist * 0.65
            + dither * 0.45
        )

        # 7. Rừng hành lang ven sông (Riparian Forest)
        affinities[:, :, BIOME_RIPARIAN_FOREST] = (
            sw[:, :, SOIL_ALLUVIAL] * 1.10
            + np.exp(-soil.distance_to_water / 5.0) * (temp > 0.28) * (1.0 - slope) * 0.65
            + dither * 0.35
        )

        # 8. Đầm lầy ngập nước & Châu thổ (Wetland / Swamp)
        affinities[:, :, BIOME_WETLAND_SWAMP] = (
            sw[:, :, SOIL_PEAT] * 1.25
            + hydrology.delta_mask.astype(np.float32) * 0.90
            + (moist > 0.74) * (slope < 0.08) * (elev < self.cfg.sea_level + 0.07) * 0.65
            + dither * 0.35
        )

        # 9. Đồng cỏ ôn đới mở (Temperate Meadow)
        meadow_moist = np.exp(-(((moist - 0.48) / 0.16) ** 2))
        affinities[:, :, BIOME_TEMPERATE_MEADOW] = (
            meadow_moist * np.clip((temp - 0.32) * 1.8, 0.0, 1.0) * (1.0 - slope * 0.5) * 0.96
            + dither * 0.45
        )

        # 10. Thảo nguyên khô vàng nhạt (Dry Savanna / Steppe) - Chuyển tiếp vào vùng Khuất mưa
        dry_steppe_moist = np.exp(-(((moist - 0.28) / 0.13) ** 2))
        affinities[:, :, BIOME_DRY_SAVANNA_STEPPE] = (
            dry_steppe_moist * (0.5 + 0.6 * shadow + 0.4 * aridity)
            + sw[:, :, SOIL_CLAY] * (precip < 0.45) * 0.48
            + dither * 0.45
        )

        # 11. Bán hoang mạc & Hoang mạc cát vàng Tây Nam (Pontic & Samark Desert)
        affinities[:, :, BIOME_SEMI_ARID_DESERT] = (
            aridity * 1.15
            + shadow * (precip < 0.32) * 0.85
            + sw[:, :, SOIL_SANDY] * (temp > 0.48) * 0.55
            + dither * 0.4
        )

        import os
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "demo_world_template.npz"
        )
        if os.path.exists(template_path):
            tmpl = np.load(template_path)
            affinities[:, :, BIOME_SEMI_ARID_DESERT] += tmpl["is_desert"] * 2.2
            affinities[:, :, BIOME_MOIST_BAY_FOREST] += tmpl["is_jungle"] * 2.2
            affinities[:, :, BIOME_ALPINE_ICE_SNOW] += tmpl["is_snow"] * 2.2

        # Áp mặt nạ Mặt nước (Ocean / River / Lake)
        water_surface = (~land) | hydrology.river_mask | hydrology.lake_mask
        for b_idx in range(1, 12):
            affinities[:, :, b_idx] = np.where(water_surface, 0.0, np.maximum(0.01, affinities[:, :, b_idx]))
        affinities[:, :, BIOME_WATER] = np.where(water_surface, 1.0, 0.0)

        # Tính Softmax nhiệt độ thấp vừa phải để tạo dải chuyển tiếp mềm (Transition Bands)
        exp_aff = np.exp(affinities * 5.2)
        exp_aff[:, :, BIOME_WATER] = np.where(water_surface, 100.0, 0.0)
        for b_idx in range(1, 12):
            exp_aff[:, :, b_idx] = np.where(water_surface, 0.0, exp_aff[:, :, b_idx])

        biome_weights = (exp_aff / np.maximum(1e-6, np.sum(exp_aff, axis=-1, keepdims=True))).astype(np.float32)

        # Xác định Quần xã chính (Primary) và Quần xã thứ cấp (Secondary) tại ranh giới chuyển tiếp
        sorted_indices = np.argsort(biome_weights, axis=-1)
        primary_id = sorted_indices[:, :, -1].astype(np.uint8)
        secondary_id = sorted_indices[:, :, -2].astype(np.uint8)

        primary_w = np.take_along_axis(biome_weights, primary_id[:, :, None], axis=-1)[:, :, 0]
        secondary_w = np.take_along_axis(biome_weights, secondary_id[:, :, None], axis=-1)[:, :, 0]

        # Hệ số chuyển tiếp Ecotone: Đạt cực đại (=1.0) khi 2 quần xã ngang điểm nhau ở biên giới
        ecotone_factor = np.where(
            water_surface,
            0.0,
            np.clip((secondary_w / np.maximum(1e-5, primary_w)), 0.0, 1.0),
        ).astype(np.float32)

        # Kết xuất mảng màu RGB pha trộn mềm qua dải chuyển tiếp (Soft Ecotone Color Blending)
        palette_arr = np.zeros((12, 3), dtype=np.float32)
        for b_code, rgb_tuple in BIOME_PALETTE_RGB.items():
            palette_arr[b_code] = rgb_tuple

        blended_rgb = np.tensordot(biome_weights, palette_arr, axes=([-1], [0]))
        blended_rgb = np.clip(blended_rgb, 0.0, 255.0).astype(np.uint8)

        return BiomeResult(
            primary_biome_id=primary_id,
            secondary_biome_id=secondary_id,
            biome_weights=biome_weights,
            ecotone_factor=ecotone_factor,
            blended_biome_rgb=blended_rgb,
        )
