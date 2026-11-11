"""
world/generation/landmass_generator.py
Tạo hình thế giới đa lục địa hoàn chỉnh (Multi-Continent Primeval Reach)
bằng Khung xương Kiến tạo Tectonic Skeleton + Domain Warping đa tầng 100% Procedural.
Bao gồm:
- Lục địa Băng Bắc (Arctica) ở Tây Bắc
- Lục địa Cao nguyên Đông Bắc (Orientis)
- Đại lục Rừng Thiêng Trung Tâm & Đông Nam (Verdantia)
- Lục địa Sa mạc Cát Vàng Tây Nam (Gondwana)
- Quần đảo nhiệt đới ngoại vi và các eo biển tự nhiên
"""

import random
from dataclasses import dataclass
import numpy as np
from world.config.world_config import WorldConfig


class FastNoise2D:
    """Bộ sinh nhiễu Perlin & Ridged FBM vector hóa trên NumPy."""

    def __init__(self, seed: int = 2026) -> None:
        rng = random.Random(seed)
        perm = list(range(256))
        rng.shuffle(perm)
        self.perm = np.array(perm + perm, dtype=np.int32)
        angles = np.linspace(0, 2.0 * np.pi, 16, endpoint=False)
        self.grad_x = np.cos(angles).astype(np.float32)
        self.grad_y = np.sin(angles).astype(np.float32)

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
        return np.clip(0.5 + (total / max(1e-6, max_val)) * 0.88, 0.0, 1.0)


@dataclass
class LandmassResult:
    base_elevation: np.ndarray
    landmask: np.ndarray
    bathymetry: np.ndarray
    coastal_shelf: np.ndarray
    inland_bay_mask: np.ndarray


class LandmassGenerator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config
        self.warp1 = FastNoise2D(seed=config.seed + 17)
        self.warp2 = FastNoise2D(seed=config.seed + 53)
        self.coast_noise = FastNoise2D(seed=config.seed + 109)
        self.detail_noise = FastNoise2D(seed=config.seed + 223)

    def generate(self) -> LandmassResult:
        h, w = self.cfg.height, self.cfg.width
        ny, nx = np.meshgrid(
            np.linspace(0.0, 1.0, h, dtype=np.float32),
            np.linspace(0.0, 1.0, w, dtype=np.float32),
            indexing="ij",
        )

        # 1. Multi-scale Domain Warping
        wx_coarse = (self.warp1.fbm_grid(nx * 1.8, ny * 1.8, octaves=4, base_scale=2.2) - 0.5) * 0.14
        wy_coarse = (self.warp1.fbm_grid(nx * 1.8 + 3.1, ny * 1.8 + 2.1, octaves=4, base_scale=2.2) - 0.5) * 0.14
        wx_fine = (self.warp2.fbm_grid(nx * 4.0, ny * 4.0, octaves=3, base_scale=5.0) - 0.5) * 0.04
        wy_fine = (self.warp2.fbm_grid(nx * 4.0 + 1.7, ny * 4.0 + 2.8, octaves=3, base_scale=5.0) - 0.5) * 0.04

        nx_w = nx + wx_coarse + wx_fine
        ny_w = ny + wy_coarse + wy_fine

        # 2. Khung xương Đa Lục Địa (Multi-Continent Tectonic Skeleton)
        continent_lobes = [
            # A. Lục địa Băng Bắc (NW Glacial Continent)
            (0.24, 0.28, 0.14, 0.17, 1.08),
            (0.15, 0.17, 0.08, 0.10, 0.98),
            (0.29, 0.18, 0.09, 0.11, 0.96),

            # B. Lục địa Cao nguyên Đông Bắc (NE Highland Continent)
            (0.60, 0.24, 0.16, 0.13, 1.02),
            (0.70, 0.22, 0.11, 0.10, 0.94),

            # C. Đại lục Rừng Thiêng Trung Tâm & Đông Nam (Verdant Mainland)
            (0.62, 0.56, 0.21, 0.23, 1.10),
            (0.50, 0.46, 0.14, 0.15, 1.04),
            (0.72, 0.48, 0.14, 0.16, 1.02),
            (0.66, 0.70, 0.16, 0.16, 1.02),
            (0.76, 0.65, 0.10, 0.12, 0.95),

            # D. Lục địa Sa mạc Cát Vàng Tây Nam (SW Desert Continent)
            (0.25, 0.72, 0.17, 0.16, 1.08),
            (0.18, 0.65, 0.11, 0.12, 0.98),
            (0.32, 0.81, 0.12, 0.11, 0.96),

            # E. Đảo Hải hành Phía Nam
            (0.48, 0.82, 0.12, 0.09, 0.95),

            # F. Quần đảo Nhiệt đới Đông Nam & Ngoại vi
            (0.88, 0.88, 0.065, 0.075, 0.92),
            (0.79, 0.92, 0.040, 0.045, 0.88),
            (0.78, 0.40, 0.045, 0.055, 0.88),
            (0.38, 0.08, 0.035, 0.040, 0.86),
        ]

        land_base = np.zeros((h, w), dtype=np.float32)
        for cx, cy, rx, ry, w_val in continent_lobes:
            d = np.sqrt(((nx_w - cx) / rx) ** 2 + ((ny_w - cy) / ry) ** 2)
            v = np.maximum(0.0, 1.0 - d) * w_val
            land_base = np.maximum(land_base, v)

        # 3. Độ nhám bờ biển Fractal
        coast_n1 = self.coast_noise.fbm_grid(nx * 2.8, ny * 2.8, octaves=5, base_scale=4.5)
        coast_n2 = self.detail_noise.fbm_grid(nx * 5.5, ny * 5.5, octaves=4, base_scale=9.0)
        coast_fractal = (coast_n1 - 0.5) * 0.22 + (coast_n2 - 0.5) * 0.11

        # 4. Khoét eo biển trung tâm và vịnh sâu chia tách các lục địa
        strait_cut = (np.abs(nx_w - 0.40) < 0.065) & (ny_w > 0.25) & (ny_w < 0.72)
        bay_cut_1 = (np.hypot((nx_w - 0.54) * 1.5, ny_w - 0.64) < 0.09)
        bay_cut_2 = (np.hypot((nx_w - 0.38) * 1.4, ny_w - 0.48) < 0.08)

        land_field = land_base + coast_fractal
        land_field[strait_cut] -= 0.26
        land_field[bay_cut_1] -= 0.22
        land_field[bay_cut_2] -= 0.22

        # Đại dương bao bọc hoàn toàn 4 mép bản đồ
        border_dist = np.minimum.reduce([nx / 0.04, (1.0 - nx) / 0.04, ny / 0.04, (1.0 - ny) / 0.04])
        border_mask = np.clip(border_dist, 0.0, 1.0) ** 0.65
        land_field *= border_mask

        # Chuẩn hóa tỷ lệ đất nổi chuẩn 46%
        target_land_ratio = 0.46
        q_thresh = float(np.quantile(land_field, 1.0 - target_land_ratio))
        base_elevation = np.clip(land_field - q_thresh + self.cfg.sea_level, 0.0, 1.0)
        landmask = base_elevation >= self.cfg.sea_level

        # 5. Độ sâu đáy biển (Bathymetry) & Thềm lục địa phát sáng (Coastal Shelf)
        sea_span = max(1e-5, self.cfg.sea_level)
        raw_depth = np.clip((self.cfg.sea_level - base_elevation) / sea_span, 0.0, 1.0)
        bathymetry = np.where(landmask, 0.0, raw_depth ** 0.80).astype(np.float32)

        coastal_shelf = np.where(
            (~landmask) & (bathymetry <= 0.38), 1.0 - (bathymetry / 0.38), 0.0
        ).astype(np.float32)

        inland_bay_mask = (~landmask) & (bay_cut_1 | bay_cut_2 | strait_cut)

        return LandmassResult(
            base_elevation=base_elevation.astype(np.float32),
            landmask=landmask,
            bathymetry=bathymetry,
            coastal_shelf=coastal_shelf,
            inland_bay_mask=inland_bay_mask,
        )
