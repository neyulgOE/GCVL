"""
world/generation/climate_generator.py
Phase 3: Mô phỏng Nhiệt độ, Gió thịnh hành, Mưa địa hình (Orographic Precipitation)
và Hiệu ứng Khuất mưa (Rain Shadow) cho thế giới đa lục địa 100% Procedural:
- Đới lạnh băng tuyết & mưa đón gió ở Lục địa Băng Bắc (Tây Bắc)
- Vùng Khuất mưa bán khô hạn & hoang mạc ở Lục địa Sa mạc Tây Nam
- Vùng rừng mưa trù phú ở Đại lục Rừng Thiêng Trung Tâm & Đông Nam
- Vùng cao nguyên ôn đới Đông Bắc
"""

from dataclasses import dataclass
from typing import Tuple
import numpy as np
from world.config.world_config import WorldConfig
from world.generation.landmass_generator import FastNoise2D, LandmassResult
from world.generation.geology_generator import GeologyResult
from world.generation.terrain_generator import TerrainResult


# Mã phân đới khí hậu (Climate Zones)
CLIMATE_POLAR_ALPINE = 0       # Hàn đới / Núi tuyết cao phía Bắc
CLIMATE_BOREAL_HUMID = 1       # Cận cực ẩm (Tây Bắc & Bắc)
CLIMATE_TEMPERATE_HUMID = 2    # Ôn đới ẩm (Đông Bắc & Trung tâm)
CLIMATE_WARM_WET_BAY = 3       # Cận nhiệt đới ẩm quanh Đại lục Rừng Thiêng
CLIMATE_SEMI_ARID_STEPPE = 4   # Thảo nguyên bán khô hạn
CLIMATE_ARID_RAIN_SHADOW = 5   # Khô hạn khuất mưa Sa mạc Tây Nam


@dataclass
class ClimateResult:
    temperature: np.ndarray        # Nhiệt độ chuẩn hóa [0..1] (0 = băng giá, 1 = nóng)
    wind_u: np.ndarray             # Thành phần gió Đông-Tây
    wind_v: np.ndarray             # Thành phần gió Bắc-Nam
    orographic_lift: np.ndarray    # Độ nâng địa hình đón gió gây mưa [0..1]
    rain_shadow: np.ndarray        # Cường độ khuất mưa sau sống núi [0..1]
    precipitation: np.ndarray      # Lượng mưa tổng hợp [0..1]
    aridity_index: np.ndarray      # Chỉ số khô hạn [0..1] (cao ở Tây Nam)
    climate_zones: np.ndarray      # Phân đới khí hậu (uint8, 0..5)


class ClimateGenerator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config
        self.clim_noise = FastNoise2D(seed=config.seed + 1409)

    def _simulate_moisture_advection(
        self,
        landmass: LandmassResult,
        geology: GeologyResult,
        terrain: TerrainResult,
        ny: np.ndarray,
        nx: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        h, w = self.cfg.height, self.cfg.width
        elev = terrain.final_heightmap
        land = landmass.landmask

        orographic_rain = np.zeros((h, w), dtype=np.float32)
        shadow_accum = np.zeros((h, w), dtype=np.float32)
        moisture_field = np.zeros((h, w), dtype=np.float32)

        # 1. Luồng Gió Tây-Bắc -> Đông-Nam (đón ẩm đại dương, trút mưa lên sườn Tây Bắc)
        m_west = np.ones(h, dtype=np.float32) * 0.94
        prev_elev = elev[:, 0].copy()
        for c in range(w):
            is_sea = ~land[:, c]
            m_west = np.where(is_sea, np.minimum(1.0, m_west + 0.04), m_west)

            dz = np.maximum(0.0, elev[:, c] - prev_elev)
            lift = np.clip(dz * 9.5, 0.0, 0.45) * land[:, c]
            rain_drop = m_west * (0.006 + lift)

            west_weight = np.clip(1.20 - ny[:, c] * 1.05, 0.20, 1.0)
            moisture_field[:, c] += m_west * west_weight
            orographic_rain[:, c] += lift * west_weight

            barrier_loss = np.clip((elev[:, c] - 0.54) * 0.05, 0.0, 0.04) * land[:, c]
            m_west = np.clip(m_west - rain_drop * 0.35 - barrier_loss, 0.08, 1.0)
            prev_elev = elev[:, c]

        # 2. Luồng Gió Đông mang ẩm từ biển Đông vào Đại lục Rừng Thiêng
        m_east = np.ones(h, dtype=np.float32) * 0.95
        shadow_tracker = np.zeros(h, dtype=np.float32)
        prev_elev = elev[:, -1].copy()

        for c in range(w - 1, -1, -1):
            is_sea = ~land[:, c]
            is_bay = landmass.inland_bay_mask[:, c]
            m_east = np.where(is_sea | is_bay, np.minimum(1.0, m_east + 0.06), m_east)
            shadow_tracker = np.where(is_sea, shadow_tracker * 0.5, shadow_tracker)

            dz = np.maximum(0.0, elev[:, c] - prev_elev)
            lift = np.clip(dz * 10.0, 0.0, 0.50) * land[:, c]

            is_high_ridge = (elev[:, c] > 0.55) | (geology.tectonic_uplift[:, c] > 0.45)
            shadow_tracker = np.where(
                is_high_ridge & land[:, c],
                np.minimum(1.0, shadow_tracker + 0.038),
                np.maximum(0.0, shadow_tracker - 0.003),
            )

            east_weight = np.clip(0.35 + ny[:, c] * 0.85, 0.3, 1.0)
            moisture_field[:, c] += m_east * east_weight * (1.0 - shadow_tracker * 0.65)
            orographic_rain[:, c] += lift * east_weight
            shadow_accum[:, c] = shadow_tracker * np.clip((ny[:, c] - 0.36) * 1.8, 0.0, 1.0) * land[:, c]

            m_east = np.clip(m_east - lift * 0.40 - is_high_ridge * 0.024, 0.05, 1.0)
            prev_elev = elev[:, c]

        # Vùng khuất mưa và bồn địa khô hạn Tây Nam
        sw_focus = np.exp(-(((nx - 0.25) / 0.16) ** 2 + ((ny - 0.72) / 0.16) ** 2)) * land
        shadow_accum = np.clip(shadow_accum * 0.50 + sw_focus * 0.75, 0.0, 1.0)

        return moisture_field, np.clip(orographic_rain, 0.0, 1.0), shadow_accum

    def generate(
        self,
        landmass: LandmassResult,
        geology: GeologyResult,
        terrain: TerrainResult,
    ) -> ClimateResult:
        h, w = self.cfg.height, self.cfg.width
        ny, nx = np.meshgrid(
            np.linspace(0.0, 1.0, h, dtype=np.float32),
            np.linspace(0.0, 1.0, w, dtype=np.float32),
            indexing="ij",
        )
        land = landmass.landmask

        # 1. Tính Nhiệt độ: Bắc băng hà (ny < 0.22), ấm áp ở xích đạo/miền Nam
        lat_temp = np.clip(0.06 + (ny ** 0.85) * 0.92, 0.0, 1.0)
        elev_above_sea = np.maximum(0.0, terrain.final_heightmap - self.cfg.sea_level) / (1.0 - self.cfg.sea_level)
        lapse_cooling = (elev_above_sea ** 1.25) * 0.70
        temp_noise = (self.clim_noise.fbm_grid(nx, ny, octaves=3, base_scale=3.0) - 0.5) * 0.06

        temperature = np.clip(lat_temp - lapse_cooling + temp_noise, 0.0, 1.0).astype(np.float32)

        # 2. Vector Gió thịnh hành
        wind_u = np.cos(ny * np.pi * 1.1).astype(np.float32)
        wind_v = (0.25 * np.sin(nx * np.pi)).astype(np.float32)

        # 3. Mô phỏng Hơi ẩm, Mưa địa hình & Hiệu ứng Khuất mưa
        raw_moist, orographic_lift, rain_shadow = self._simulate_moisture_advection(
            landmass, geology, terrain, ny, nx
        )

        precip_noise = self.clim_noise.fbm_grid(nx + 4.1, ny + 2.3, octaves=4, base_scale=4.0)
        nw_windward_boost = 0.42 * np.exp(-(((nx - 0.24) / 0.16) ** 2 + ((ny - 0.26) / 0.16) ** 2)) * land
        verdant_rain_boost = 0.44 * np.exp(-(((nx - 0.62) / 0.20) ** 2 + ((ny - 0.58) / 0.22) ** 2)) * land

        raw_precip = (
            raw_moist * 0.38
            + orographic_lift * 0.26
            + precip_noise * 0.14
            + nw_windward_boost
            + verdant_rain_boost
        ) * (1.0 - rain_shadow * 0.78)

        precipitation = np.clip(raw_precip, 0.03, 1.0).astype(np.float32)

        # 4. Chỉ số Khô hạn (Aridity Index)
        aridity_index = np.clip(
            (temperature * 0.65 + (1.0 - precipitation) * 0.75) - 0.32, 0.0, 1.0
        ).astype(np.float32)

        # 5. Phân loại Đới Khí hậu
        zones = np.full((h, w), CLIMATE_TEMPERATE_HUMID, dtype=np.uint8)
        zones = np.where(temperature < 0.22, CLIMATE_POLAR_ALPINE, zones)
        zones = np.where((temperature >= 0.22) & (temperature < 0.40), CLIMATE_BOREAL_HUMID, zones)
        zones = np.where(
            (temperature >= 0.40) & (precipitation >= 0.55) & (ny > 0.40), CLIMATE_WARM_WET_BAY, zones
        )
        zones = np.where((temperature >= 0.38) & (precipitation < 0.34), CLIMATE_SEMI_ARID_STEPPE, zones)
        zones = np.where((rain_shadow > 0.36) & (precipitation < 0.25), CLIMATE_ARID_RAIN_SHADOW, zones)

        return ClimateResult(
            temperature=temperature,
            wind_u=wind_u,
            wind_v=wind_v,
            orographic_lift=orographic_lift.astype(np.float32),
            rain_shadow=rain_shadow.astype(np.float32),
            precipitation=precipitation,
            aridity_index=aridity_index,
            climate_zones=zones,
        )
