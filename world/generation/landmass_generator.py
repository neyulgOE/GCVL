"""
world/generation/landmass_generator.py
Tạo hình lục địa Primeval Reach bằng Tectonic Skeleton + Multi-Scale Domain Warping,
loại bỏ hoàn toàn hiện tượng "cục tròn Gaussian", tạo bán đảo, vịnh hẹp (fjord) và vịnh nội địa.
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

    @staticmethod
    def _segment_influence(
        px: np.ndarray, py: np.ndarray, x1: float, y1: float, x2: float, y2: float, r1: float, r2: float
    ) -> np.ndarray:
        """Tính trường khoảng cách có bán kính biến thiên dọc theo đoạn xương sống lục địa."""
        dx, dy = x2 - x1, y2 - y1
        l2 = max(1e-6, dx * dx + dy * dy)
        t = np.clip(((px - x1) * dx + (py - y1) * dy) / l2, 0.0, 1.0)
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        rad = r1 + t * (r2 - r1)
        dist = np.hypot((px - proj_x) * 1.35, py - proj_y)
        return np.clip(1.0 - (dist / rad) ** 1.65, 0.0, 1.0)

    def generate(self) -> LandmassResult:
        h, w = self.cfg.height, self.cfg.width
        ny, nx = np.meshgrid(
            np.linspace(0.0, 1.0, h, dtype=np.float32),
            np.linspace(0.0, 1.0, w, dtype=np.float32),
            indexing="ij",
        )

        # 1. Two-Stage Domain Warping (Uốn cong mạnh không gian để bờ biển gồ ghề tự nhiên)
        q_x = (self.warp1.fbm_grid(nx * 1.5, ny, octaves=4, base_scale=2.2) - 0.5) * 0.24
        q_y = (self.warp1.fbm_grid(nx * 1.5 + 4.2, ny + 1.8, octaves=4, base_scale=2.2) - 0.5) * 0.24
        r_x = (self.warp2.fbm_grid(nx * 1.5 + q_x, ny + q_y, octaves=5, base_scale=4.5) - 0.5) * 0.14
        r_y = (self.warp2.fbm_grid(nx * 1.5 + q_y + 2.1, ny + q_x + 3.4, octaves=5, base_scale=4.5) - 0.5) * 0.14

        wx = nx + q_x + r_x
        wy = ny + q_y + r_y

        # 2. Khung xương kiến tạo bất đối xứng của đại lục Primeval Reach (7 vùng địa lý):
        # - Trục Bắc Cao & Tây Bắc (Windward Fjord Range)
        seg_north_alpine = self._segment_influence(wx, wy, 0.26, 0.18, 0.58, 0.22, 0.22, 0.25)
        seg_nw_peninsula = self._segment_influence(wx, wy, 0.28, 0.20, 0.16, 0.42, 0.19, 0.11)
        # - Sống lưng Trung Tâm & Bồn địa Khuất mưa Tây Nam (Rain Shadow Plateau)
        seg_central_spine = self._segment_influence(wx, wy, 0.42, 0.22, 0.38, 0.72, 0.26, 0.24)
        seg_sw_desert_lobe = self._segment_influence(wx, wy, 0.38, 0.56, 0.22, 0.78, 0.23, 0.16)
        # - Đồng bằng Đông Bắc & Vòng cung ôm Vịnh Nội Địa Đông Nam (Inland Sea Hook)
        seg_ne_plains = self._segment_influence(wx, wy, 0.55, 0.24, 0.76, 0.44, 0.24, 0.19)
        seg_se_peninsula = self._segment_influence(wx, wy, 0.75, 0.44, 0.78, 0.76, 0.16, 0.10)
        seg_south_delta = self._segment_influence(wx, wy, 0.38, 0.70, 0.56, 0.84, 0.21, 0.14)

        # - Quần đảo phụ ngoài khơi Tây Bắc & Đông Nam (Archipelago Arcs)
        island_arc_nw = self._segment_influence(wx, wy, 0.11, 0.16, 0.08, 0.28, 0.065, 0.045) * 0.78
        island_arc_se = self._segment_influence(wx, wy, 0.84, 0.68, 0.89, 0.82, 0.070, 0.050) * 0.76

        macro_continent = np.maximum.reduce([
            seg_north_alpine,
            seg_nw_peninsula,
            seg_central_spine,
            seg_sw_desert_lobe,
            seg_ne_plains,
            seg_se_peninsula,
            seg_south_delta,
            island_arc_nw,
            island_arc_se,
        ])

        # 3. Khoét Vịnh Nội Địa Đông Nam (Inland Sea/Bay) ăn sâu vào giữa Đông Bắc và Nam
        bay_core = self._segment_influence(wx, wy, 0.56, 0.50, 0.68, 0.68, 0.18, 0.16)
        bay_strait = self._segment_influence(wx, wy, 0.66, 0.66, 0.68, 0.90, 0.13, 0.18)
        inland_bay_carve = np.maximum(bay_core, bay_strait)

        # Khoét các vịnh hẹp Fjord ở bờ biển Tây Bắc
        fjord_noise = np.abs(self.detail_noise.noise_grid(nx * 18.0, ny * 18.0))
        nw_fjord_carve = np.where((nx < 0.32) & (ny < 0.42), (1.0 - np.clip(fjord_noise * 4.5, 0.0, 1.0)) * 0.28, 0.0)

        # 4. Kết hợp nhiễu đa tần số tạo đường bờ biển sắc nét
        coast_roughness = self.coast_noise.fbm_grid(nx * 1.5, ny, octaves=6, persistence=0.56, base_scale=4.8)
        micro_coast = self.detail_noise.fbm_grid(nx * 1.5, ny, octaves=5, persistence=0.52, base_scale=14.0)

        # Đảm bảo đại dương bao bọc toàn bộ mép khung ảnh
        border_dist = np.minimum.reduce([nx / 0.06, (1.0 - nx) / 0.06, ny / 0.06, (1.0 - ny) / 0.07])
        border_mask = np.clip(border_dist, 0.0, 1.0) ** 0.75

        raw_elev = (
            macro_continent * 0.72
            + coast_roughness * 0.26
            + micro_coast * 0.12
            - inland_bay_carve * 0.58
            - nw_fjord_carve
        ) * border_mask

        # 5. Chuẩn hóa mực nước biển để diện tích đất nổi đạt chuẩn 35% (nằm giữa [30%, 38%])
        target_land_ratio = 0.355
        q_thresh = float(np.quantile(raw_elev, 1.0 - target_land_ratio))
        base_elevation = np.clip(raw_elev - q_thresh + self.cfg.sea_level, 0.0, 1.0)
        landmask = base_elevation >= self.cfg.sea_level

        # 6. Tính độ sâu đáy biển (Bathymetry) có rãnh đại dương & thềm lục địa nông
        sea_span = max(1e-5, self.cfg.sea_level)
        raw_depth = np.clip((self.cfg.sea_level - base_elevation) / sea_span, 0.0, 1.0)
        bathymetry = np.where(landmask, 0.0, raw_depth ** 0.82).astype(np.float32)

        coastal_shelf = np.where((~landmask) & (bathymetry <= 0.32), 1.0 - (bathymetry / 0.32), 0.0).astype(np.float32)
        inland_bay_mask = (~landmask) & (inland_bay_carve > 0.22)

        return LandmassResult(
            base_elevation=base_elevation.astype(np.float32),
            landmask=landmask,
            bathymetry=bathymetry,
            coastal_shelf=coastal_shelf,
            inland_bay_mask=inland_bay_mask,
        )
