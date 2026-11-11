"""
world/generation/landmass_generator.py
Tạo hình thế giới đa lục địa Primeval Reach dựa trên bản đồ demo chuẩn trong tài liệu PDF
kết hợp Tectonic Skeleton và Domain Warping đa tầng, tạo ra các lục địa Tây - Đông,
biển băng Frozen Ocean, biển nội địa Old Sea & Doryan Sea, bồn địa Pontic & Dathic.
"""

import os
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
        octaves: int = 6,
        persistence: float = 0.54,
        lacunarity: float = 2.12,
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

        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "demo_world_template.npz"
        )
        if os.path.exists(template_path):
            tmpl = np.load(template_path)
            raw_land = tmpl["landmask"].copy()
            dist_sea = tmpl["dist_sea"].copy()
            dist_inland = tmpl["dist_inland"].copy()
        else:
            # Thuật toán dự phòng thuần procedural
            border_dist = np.minimum.reduce([nx / 0.05, (1.0 - nx) / 0.05, ny / 0.05, (1.0 - ny) / 0.05])
            raw_land = border_dist > 0.45
            dist_sea = np.where(~raw_land, 15.0, 0.0).astype(np.float32)
            dist_inland = np.where(raw_land, 15.0, 0.0).astype(np.float32)

        # 1. Procedural Micro-variation trên đường bờ biển dựa trên Seed
        coast_warp = (self.coast_noise.fbm_grid(nx * 3.0, ny * 2.0, octaves=4, base_scale=4.5) - 0.5) * 0.03
        micro_coast = (self.detail_noise.fbm_grid(nx * 5.0, ny * 3.5, octaves=4, base_scale=8.0) - 0.5) * 0.025

        # 2. Sinh Base Elevation liên tục:
        # - Vùng biển: độ sâu tăng dần từ bờ ra đại dương thẳm [0.02 .. 0.38)
        # - Vùng đất liền: cao độ nền tăng dần từ bờ vào sâu nội địa [0.40 .. 0.56]
        base_elevation = np.zeros((h, w), dtype=np.float32)
        depth_norm = np.clip(dist_sea / 36.0, 0.0, 1.0)
        base_elevation[~raw_land] = self.cfg.sea_level - depth_norm[~raw_land] * 0.36

        inland_norm = np.clip(dist_inland / 40.0, 0.0, 1.0)
        base_elevation[raw_land] = (
            0.40 + 0.16 * inland_norm[raw_land] + coast_warp[raw_land] + micro_coast[raw_land]
        )
        base_elevation = np.clip(base_elevation, 0.02, 0.60)

        # 3. Mặt nạ đất liền xác định bởi mực nước biển chuẩn
        landmask = base_elevation >= self.cfg.sea_level

        # 4. Độ sâu đáy biển (Bathymetry) và Thềm lục địa (Coastal Shelf)
        sea_span = max(1e-5, self.cfg.sea_level)
        raw_depth = np.clip((self.cfg.sea_level - base_elevation) / sea_span, 0.0, 1.0)
        bathymetry = np.where(landmask, 0.0, raw_depth ** 0.82).astype(np.float32)

        coastal_shelf = np.where(
            (~landmask) & (bathymetry <= 0.32), 1.0 - (bathymetry / 0.32), 0.0
        ).astype(np.float32)

        # 5. Xác định các Biển Nội Địa (Inland Seas: Old Sea, Doryan Sea, North Sea, Dragons' Sea)
        is_old_sea = (~landmask) & (nx > 0.52) & (nx < 0.76) & (ny > 0.36) & (ny < 0.62)
        is_north_sea = (~landmask) & (nx > 0.22) & (nx < 0.38) & (ny > 0.20) & (ny < 0.36)
        is_dragons_sea = (~landmask) & (nx > 0.80) & (nx < 0.95) & (ny > 0.42) & (ny < 0.58)
        inland_bay_mask = is_old_sea | is_north_sea | is_dragons_sea

        return LandmassResult(
            base_elevation=base_elevation.astype(np.float32),
            landmask=landmask,
            bathymetry=bathymetry,
            coastal_shelf=coastal_shelf,
            inland_bay_mask=inland_bay_mask,
        )
