"""
world/generation/climate_generator.py
Phase 3: Mô phỏng Nhiệt độ, Gió thịnh hành, Mưa địa hình (Orographic Precipitation)
và Hiệu ứng Khuất mưa (Rain Shadow) tạo vùng bán khô hạn Pontic Desert & Samark Desert,
vùng mưa nhiệt đới Dathic Jungle và đới lạnh Bắc Băng Dương (Frozen Ocean).
"""

import os
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
CLIMATE_WARM_WET_BAY = 3       # Cận nhiệt đới ẩm quanh Dathic Jungle & Vịnh Nội Địa
CLIMATE_SEMI_ARID_STEPPE = 4   # Thảo nguyên bán khô hạn
CLIMATE_ARID_RAIN_SHADOW = 5   # Khô hạn khuất mưa Pontic Desert & Samark Desert


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
        """
        Mô phỏng vận chuyển hơi ẩm từ đại dương vào lục địa theo 2 luồng gió chính:
        1. Luồng Tây-Bắc -> Đông-Nam ở nửa Bắc (đón ẩm từ Gran Ocean, trút mưa lên sườn núi).
        2. Luồng Đông -> Tây ở nửa Nam (mang ẩm từ Biển Nội Địa vào Dathic Jungle, bị chặn bởi
           sống núi trung tâm khiến vùng Tây Nam rơi vào vùng Khuất mưa - Rain Shadow Pontic Desert).
        """
        h, w = self.cfg.height, self.cfg.width
        elev = terrain.final_heightmap
        land = landmass.landmask

        orographic_rain = np.zeros((h, w), dtype=np.float32)
        shadow_accum = np.zeros((h, w), dtype=np.float32)
        moisture_field = np.zeros((h, w), dtype=np.float32)

        # --- Luồng 1: Gió Tây -> Đông (Quét từ Gran Ocean sang, mạnh ở Tây Bắc) ---
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

        # --- Luồng 2: Gió Tín phong Đông -> Tây (Từ Biển Nội Địa thổi sang Tây) ---
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

            # Sống núi Trung tâm (Continental Spine) chặn hơi ẩm
            is_high_ridge = (elev[:, c] > 0.56) | (geology.tectonic_uplift[:, c] > 0.46)
            shadow_tracker = np.where(
                is_high_ridge & land[:, c],
                np.minimum(1.0, shadow_tracker + 0.035),
                np.maximum(0.0, shadow_tracker - 0.003),
            )

            east_weight = np.clip(0.35 + ny[:, c] * 0.85, 0.3, 1.0)
            moisture_field[:, c] += m_east * east_weight * (1.0 - shadow_tracker * 0.65)
            orographic_rain[:, c] += lift * east_weight
            shadow_accum[:, c] = shadow_tracker * np.clip((ny[:, c] - 0.36) * 1.8, 0.0, 1.0) * land[:, c]

            m_east = np.clip(m_east - lift * 0.40 - is_high_ridge * 0.024, 0.05, 1.0)
            prev_elev = elev[:, c]

        # Cường điệu hóa vùng Khuất mưa Pontic Desert & Samark Desert
        sw_focus = np.exp(-(((nx - 0.28) / 0.16) ** 2 + ((ny - 0.64) / 0.16) ** 2)) * land
        se_focus = np.exp(-(((nx - 0.64) / 0.12) ** 2 + ((ny - 0.74) / 0.12) ** 2)) * land
        shadow_accum = np.clip(shadow_accum * 0.55 + (sw_focus + se_focus * 0.75) * 0.65, 0.0, 1.0)

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

        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "demo_world_template.npz"
        )
        if os.path.exists(template_path):
            tmpl = np.load(template_path)
            is_desert = tmpl["is_desert"]
            is_jungle = tmpl["is_jungle"]
        else:
            is_desert = np.zeros((h, w), dtype=bool)
            is_jungle = np.zeros((h, w), dtype=bool)

        # 1. Tính Nhiệt độ: Băng giá ở cực Bắc (ny < 0.18), ấm áp ở xích đạo/miền Nam
        lat_temp = np.clip(0.08 + (ny ** 0.88) * 0.90, 0.0, 1.0)
        elev_above_sea = np.maximum(0.0, terrain.final_heightmap - self.cfg.sea_level) / (1.0 - self.cfg.sea_level)
        lapse_cooling = (elev_above_sea ** 1.25) * 0.68
        temp_noise = (self.clim_noise.fbm_grid(nx, ny, octaves=3, base_scale=3.0) - 0.5) * 0.08

        temperature = np.clip(lat_temp - lapse_cooling + temp_noise, 0.0, 1.0).astype(np.float32)

        # 2. Vector Gió thịnh hành
        wind_u = np.cos(ny * np.pi * 1.1).astype(np.float32)
        wind_v = (0.25 * np.sin(nx * np.pi)).astype(np.float32)

        # 3. Mô phỏng Hơi ẩm, Mưa địa hình & Hiệu ứng Khuất mưa
        raw_moist, orographic_lift, rain_shadow = self._simulate_moisture_advection(
            landmass, geology, terrain, ny, nx
        )

        precip_noise = self.clim_noise.fbm_grid(nx + 4.1, ny + 2.3, octaves=4, base_scale=4.0)
        nw_windward_boost = 0.38 * np.exp(-(((nx - 0.20) / 0.16) ** 2 + ((ny - 0.28) / 0.16) ** 2))
        dathic_rain_boost = 0.42 * np.exp(-(((nx - 0.49) / 0.12) ** 2 + ((ny - 0.60) / 0.12) ** 2))

        raw_precip = (
            raw_moist * 0.40
            + orographic_lift * 0.25
            + precip_noise * 0.15
            + nw_windward_boost
            + dathic_rain_boost
        ) * (1.0 - rain_shadow * 0.75)

        precipitation = np.clip(raw_precip, 0.03, 1.0).astype(np.float32)
        # Bồn địa hoang mạc Pontic & Samark chịu khô hạn cực độ
        precipitation[is_desert] = np.clip(precipitation[is_desert] * 0.32, 0.04, 0.22)
        # Rừng nhiệt đới Dathic Jungle nhận mưa trù phú
        precipitation[is_jungle] = np.maximum(precipitation[is_jungle], 0.72)

        # 4. Chỉ số Khô hạn (Aridity Index)
        aridity_index = np.clip(
            (temperature * 0.65 + (1.0 - precipitation) * 0.75) - 0.35, 0.0, 1.0
        ).astype(np.float32)
        aridity_index[is_desert] = np.maximum(aridity_index[is_desert], 0.85)
        aridity_index[is_jungle] = np.minimum(aridity_index[is_jungle], 0.18)

        # 5. Phân loại Đới Khí hậu
        zones = np.full((h, w), CLIMATE_TEMPERATE_HUMID, dtype=np.uint8)
        zones = np.where(temperature < 0.24, CLIMATE_POLAR_ALPINE, zones)
        zones = np.where((temperature >= 0.24) & (temperature < 0.42), CLIMATE_BOREAL_HUMID, zones)
        zones = np.where(
            (temperature >= 0.42) & (precipitation >= 0.60) & (ny > 0.45), CLIMATE_WARM_WET_BAY, zones
        )
        zones = np.where((temperature >= 0.38) & (precipitation < 0.36), CLIMATE_SEMI_ARID_STEPPE, zones)
        zones = np.where((rain_shadow > 0.38) & (precipitation < 0.26), CLIMATE_ARID_RAIN_SHADOW, zones)

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
