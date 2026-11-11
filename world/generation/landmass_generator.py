"""
world/generation/landmass_generator.py
Sinh khung hình học tần số thấp cho đại lục Primeval Reach, Vịnh Nội Địa (Inland Bay),
các bán đảo bất đối xứng và độ sâu đáy biển (Bathymetry).
"""

import math
import random
from dataclasses import dataclass
import numpy as np
from world.config.world_config import WorldConfig


class FastNoise2D:
    """Bộ sinh nhiễu Perlin 2D vector hóa trên NumPy tốc độ cao cho lưới 512x512 / 1024x1024."""

    def __init__(self, seed: int = 2026) -> None:
        rng = random.Random(seed)
        perm = list(range(256))
        rng.shuffle(perm)
        self.perm = np.array(perm + perm, dtype=np.int32)
        angles = np.linspace(0, 2.0 * np.pi, 16, endpoint=False)
        self.grad_x = np.cos(angles)
        self.grad_y = np.sin(angles)

    @staticmethod
    def _fade(t: np.ndarray) -> np.ndarray:
        return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

    def _grad(self, hash_idx: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        h = hash_idx & 15
        return self.grad_x[h] * x + self.grad_y[h] * y

    def noise_grid(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        xi = np.floor(x).astype(np.int32) & 255
        yi = np.floor(y).astype(np.int32) & 255
        xf = x - np.floor(x)
        yf = y - np.floor(y)

        u = self._fade(xf)
        v = self._fade(yf)

        aa = self.perm[self.perm[xi] + yi]
        ab = self.perm[self.perm[xi] + yi + 1]
        ba = self.perm[self.perm[xi + 1] + yi]
        bb = self.perm[self.perm[xi + 1] + yi + 1]

        x1 = self._grad(aa, xf, yf) * (1.0 - u) + self._grad(ba, xf - 1.0, yf) * u
        x2 = self._grad(ab, xf, yf - 1.0) * (1.0 - u) + self._grad(bb, xf - 1.0, yf - 1.0) * u
        return x1 * (1.0 - v) + x2 * v

    def fbm_grid(
        self,
        x: np.ndarray,
        y: np.ndarray,
        octaves: int = 5,
        persistence: float = 0.52,
        lacunarity: float = 2.05,
        base_scale: float = 3.0,
    ) -> np.ndarray:
        total = np.zeros_like(x, dtype=np.float32)
        amplitude = 1.0
        frequency = base_scale
        max_val = 0.0
        for _ in range(octaves):
            total += self.noise_grid(x * frequency, y * frequency) * amplitude
            max_val += amplitude
            amplitude *= persistence
            frequency *= lacunarity
        norm = total / max(1e-6, max_val)
        return np.clip(0.5 + norm * 0.82, 0.0, 1.0)


@dataclass
class LandmassResult:
    base_elevation: np.ndarray   # Độ cao cơ sở [0..1]
    landmask: np.ndarray         # Boolean mask (True = Đất nổi, False = Biển)
    bathymetry: np.ndarray       # Độ sâu đáy biển [0..1] (0 = mặt biển, 1 = vực biển sâu)
    coastal_shelf: np.ndarray    # Thềm lục địa nông [0..1]
    inland_bay_mask: np.ndarray  # Vùng vịnh nội địa Đông Nam


class LandmassGenerator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config
        self.macro_noise = FastNoise2D(seed=config.seed + 11)
        self.warp_noise = FastNoise2D(seed=config.seed + 37)
        self.coast_noise = FastNoise2D(seed=config.seed + 89)

    def generate(self) -> LandmassResult:
        h, w = self.cfg.height, self.cfg.width
        ny, nx = np.meshgrid(
            np.linspace(0.0, 1.0, h, dtype=np.float32),
            np.linspace(0.0, 1.0, w, dtype=np.float32),
            indexing="ij",
        )

        # 1. Domain Warping tạo đường bờ biển tự nhiên, bất đối xứng
        warp_x = (self.warp_noise.fbm_grid(nx, ny, octaves=3, base_scale=2.2) - 0.5) * 0.16
        warp_y = (self.warp_noise.fbm_grid(nx + 3.7, ny + 1.9, octaves=3, base_scale=2.2) - 0.5) * 0.16
        wx = nx + warp_x
        wy = ny + warp_y

        # 2. Khung hình học tần số thấp của đại lục Primeval Reach:
        #    - Khối lục địa chính trải từ Bắc Cao xuống Nam Ven Biển
        #    - Mở rộng về phía Tây Bắc (Windward) và Đông Bắc (Temperate Plains)
        core_continent = np.exp(-(((wx - 0.44) / 0.31) ** 2 + ((wy - 0.46) / 0.36) ** 2))
        northern_alpine_lobe = 0.78 * np.exp(-(((wx - 0.46) / 0.28) ** 2 + ((wy - 0.20) / 0.16) ** 2))
        nw_windward_peninsula = 0.62 * np.exp(-(((wx - 0.24) / 0.15) ** 2 + ((wy - 0.32) / 0.18) ** 2))
        ne_temperate_lobe = 0.68 * np.exp(-(((wx - 0.68) / 0.18) ** 2 + ((wy - 0.34) / 0.20) ** 2))
        sw_arid_plateau = 0.72 * np.exp(-(((wx - 0.32) / 0.20) ** 2 + ((wy - 0.68) / 0.20) ** 2))
        se_coastal_hook = 0.54 * np.exp(-(((wx - 0.74) / 0.13) ** 2 + ((wy - 0.72) / 0.16) ** 2))

        # 3. Đảo phụ nhỏ tách biệt ngoài khơi Tây Bắc & Đông Nam
        island_nw = 0.48 * np.exp(-(((wx - 0.12) / 0.055) ** 2 + ((wy - 0.18) / 0.045) ** 2))
        island_se = 0.46 * np.exp(-(((wx - 0.85) / 0.050) ** 2 + ((wy - 0.82) / 0.050) ** 2))

        macro_shape = np.maximum.reduce([
            core_continent,
            northern_alpine_lobe,
            nw_windward_peninsula,
            ne_temperate_lobe,
            sw_arid_plateau,
            se_coastal_hook,
            island_nw,
            island_se,
        ])

        # 4. Khoét Vịnh Nội Địa lớn (Inland Sea / Bay) ở Đông Nam ăn sâu vào lục địa
        #    nhưng giữ lại eo đất phía Bắc & Tây để không cắt rời lục địa.
        inland_bay_cavity = 0.68 * np.exp(-(((wx - 0.62) / 0.13) ** 2 + ((wy - 0.62) / 0.14) ** 2))
        bay_mouth_channel = 0.55 * np.exp(-(((wx - 0.68) / 0.08) ** 2 + ((wy - 0.78) / 0.12) ** 2))
        inland_bay_total = np.maximum(inland_bay_cavity, bay_mouth_channel)

        # 5. Cộng nhiễu bờ biển đa tần số (Multi-frequency coastal detail)
        coast_fbm = self.coast_noise.fbm_grid(nx, ny, octaves=6, persistence=0.54, base_scale=4.2)
        edge_falloff = np.clip(
            np.minimum.reduce([nx / 0.07, (1.0 - nx) / 0.07, ny / 0.06, (1.0 - ny) / 0.08]),
            0.0,
            1.0,
        )

        raw_elev = (macro_shape * 0.76 + coast_fbm * 0.34 - inland_bay_total * 0.65) * edge_falloff

        # 6. Tự động cân chỉnh ngưỡng Sea Level để tỷ lệ đất nổi luôn nằm trong [30%, 38%]
        target_ratio = 0.34  # Mục tiêu trung tâm 34% diện tích là đất nổi
        quantile_threshold = float(np.quantile(raw_elev, 1.0 - target_ratio))
        base_elevation = np.clip(raw_elev - quantile_threshold + self.cfg.sea_level, 0.0, 1.0)

        landmask = base_elevation >= self.cfg.sea_level

        # 7. Tính độ sâu đáy biển (Bathymetry) và thềm lục địa nông (Continental Shelf)
        sea_span = max(1e-5, self.cfg.sea_level)
        bathymetry = np.where(
            landmask,
            0.0,
            np.clip((self.cfg.sea_level - base_elevation) / sea_span, 0.0, 1.0),
        )
        coastal_shelf = np.where((~landmask) & (bathymetry <= 0.28), 1.0 - (bathymetry / 0.28), 0.0)
        inland_bay_mask = (~landmask) & (inland_bay_total > 0.25)

        return LandmassResult(
            base_elevation=base_elevation.astype(np.float32),
            landmask=landmask,
            bathymetry=bathymetry.astype(np.float32),
            coastal_shelf=coastal_shelf.astype(np.float32),
            inland_bay_mask=inland_bay_mask,
        )
