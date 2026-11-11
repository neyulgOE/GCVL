"""
world/atlas/atlas_renderer.py
Kết xuất Bản đồ Thế giới Vật lý Nổi khối (Physical Relief Atlas 1600x1040 px)
với sông ngòi làm mượt Chaikin Spline khử răng cưa, bóng đổ địa chất đa hướng
và dải màu độ sâu đại dương chuẩn Cartographic.
"""

import math
from typing import List, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

try:
    from scipy.ndimage import gaussian_filter
except ImportError:
    def gaussian_filter(arr: np.ndarray, sigma: float = 0.85) -> np.ndarray:
        """Pure-NumPy 1D separable Gaussian blur fallback when scipy is not available."""
        radius = int(math.ceil(2.5 * sigma))
        x = np.arange(-radius, radius + 1, dtype=np.float32)
        kernel = np.exp(-0.5 * (x / sigma) ** 2)
        kernel /= kernel.sum()
        pad_h = np.pad(arr, ((0, 0), (radius, radius)), mode="reflect")
        blurred_h = np.zeros_like(arr, dtype=np.float32)
        for i, k in enumerate(kernel):
            blurred_h += k * pad_h[:, i : i + arr.shape[1]]
        pad_v = np.pad(blurred_h, ((radius, radius), (0, 0)), mode="reflect")
        out = np.zeros_like(arr, dtype=np.float32)
        for j, k in enumerate(kernel):
            out += k * pad_v[j : j + arr.shape[0], :]
        return out

from world.config.world_config import WorldConfig
from world.generation.landmass_generator import LandmassResult
from world.generation.terrain_generator import TerrainResult
from world.generation.climate_generator import ClimateResult
from world.generation.hydrology_generator import HydrologyResult
from world.generation.soil_generator import SoilResult
from world.generation.biome_generator import BiomeResult
from world.generation.ecology_generator import EcologyResult


class PhysicalAtlasRenderer:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config

    @staticmethod
    def _chaikin_smooth_coords(coords: List[List[float]], iterations: int = 2) -> List[Tuple[float, float]]:
        """Làm mượt gấp khúc D8 thành đường cong sông uốn khúc tự nhiên (Chaikin's Corner Cutting)."""
        pts = [(float(p[0]), float(p[1])) for p in coords]
        if len(pts) < 3:
            return pts
        for _ in range(iterations):
            new_pts = [pts[0]]
            for i in range(len(pts) - 1):
                p0, p1 = pts[i], pts[i + 1]
                q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
                r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
                new_pts.extend([q, r])
            new_pts.append(pts[-1])
            pts = new_pts
        return pts

    def render_vegetation_density_png(
        self, landmass: LandmassResult, hydrology: HydrologyResult, ecology: EcologyResult, path: str
    ) -> None:
        v = ecology.vegetation_density
        h, w = v.shape
        rgb = np.zeros((h, w, 3), dtype=np.float32)
        rgb[:, :, 0] = (1.0 - v) * 218.0 + v * 20.0
        rgb[:, :, 1] = (1.0 - v) * 194.0 + v * 102.0
        rgb[:, :, 2] = (1.0 - v) * 136.0 + v * 34.0
        rgb[~landmass.landmask] = (22, 58, 92)
        rgb[hydrology.river_mask | hydrology.lake_mask] = (44, 126, 184)
        Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB").save(path, "PNG")

    def render_habitat_png(
        self,
        landmass: LandmassResult,
        terrain: TerrainResult,
        hydrology: HydrologyResult,
        biome: BiomeResult,
        ecology: EcologyResult,
        path: str,
    ) -> None:
        rgb = biome.blended_biome_rgb.astype(np.float32)
        shade = (0.58 + 0.56 * terrain.shaded_relief)[:, :, None]
        rgb = np.where(landmass.landmask[:, :, None], rgb * shade, rgb)
        rgb[~landmass.landmask] = (26, 70, 108)
        rgb[hydrology.river_mask | hydrology.lake_mask] = (44, 128, 188)

        img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")
        draw = ImageDraw.Draw(img)
        guild_colors = {
            "megafauna_herbivore": (255, 215, 64),
            "medium_herbivore": (132, 238, 118),
            "omnivore": (232, 148, 72),
            "apex_predator": (238, 68, 68),
            "pack_predator": (212, 92, 224),
            "aquatic_semi": (72, 224, 238),
        }
        for herd in ecology.spawned_wildlife_herds:
            cx, cy = herd["world_col"], herd["world_row"]
            col = guild_colors.get(herd["guild"], (255, 255, 255))
            r_dot = 3 if herd["guild"] in ("megafauna_herbivore", "apex_predator") else 2
            draw.ellipse([cx - r_dot, cy - r_dot, cx + r_dot, cy + r_dot], fill=col, outline=(18, 18, 18))
        img.save(path, "PNG")

    def render_world_atlas_png(
        self,
        landmass: LandmassResult,
        terrain: TerrainResult,
        climate: ClimateResult,
        hydrology: HydrologyResult,
        soil: SoilResult,
        biome: BiomeResult,
        ecology: EcologyResult,
        path: str,
        upscale_factor: int = 2,
    ) -> Image.Image:
        """
        Kết xuất Bản đồ Vật lý Đại lục (Physical World Atlas 1600x1040 px) chuẩn thẩm mỹ ảnh mẫu:
        - Nền Sinh thái + Địa chất đa tầng không vết gãy.
        - Bóng đổ 3D tương phản cao (Ambient Occlusion ở khe vực + Specular Highlight trên đỉnh núi đá/băng).
        - Đại dương phân 6 dải độ sâu (Bathymetric Contours) và thềm lục địa sáng màu.
        - Sông ngòi vẽ vector Chaikin Spline mượt mà ở độ phân giải cao.
        """
        h, w = landmass.landmask.shape
        land = landmass.landmask
        elev = terrain.final_heightmap
        shade = terrain.shaded_relief
        curv = terrain.curvature
        slope = terrain.slope

        # 1. Nền màu Quần xã kết hợp Độ cao Địa chất (Hypsometric + Ecological Tinting)
        base_rgb = biome.blended_biome_rgb.astype(np.float32)

        # Tăng sắc độ ấm cho thảo nguyên/hoang mạc Tây Nam và sắc xanh sâu cho rừng ẩm
        arid_warmth = np.clip(climate.aridity_index * 1.2, 0.0, 1.0) * land
        warm_terracotta = np.array([216.0, 152.0, 92.0], dtype=np.float32)
        base_rgb = base_rgb * (1.0 - arid_warmth[:, :, None] * 0.35) + warm_terracotta * (arid_warmth[:, :, None] * 0.35)

        # Vách đá xám lộ thiên trên sườn dốc lớn & sống núi cao
        rock_mask = np.clip((slope - 0.14) * 2.6 + np.maximum(0.0, elev - 0.62) * 2.2, 0.0, 0.92) * land
        rock_tone = np.where(
            (climate.aridity_index > 0.35)[:, :, None],
            np.array([156.0, 126.0, 104.0], dtype=np.float32),  # Đá sa thạch nâu đỏ vùng khô hạn
            np.array([134.0, 136.0, 140.0], dtype=np.float32),  # Đá granite xám lạnh vùng núi cao
        )
        base_rgb = base_rgb * (1.0 - rock_mask[:, :, None]) + rock_tone * rock_mask[:, :, None]

        # Tuyết trắng & Băng hà vĩnh cửu trên đỉnh núi Bắc Cao & Continental Spine
        snow_mask = np.clip((elev - 0.72) * 4.8 + (0.24 - climate.temperature) * 3.2 - slope * 0.35, 0.0, 1.0) * land
        snow_tone = np.array([244.0, 248.0, 254.0], dtype=np.float32)
        base_rgb = base_rgb * (1.0 - snow_mask[:, :, None]) + snow_tone * snow_mask[:, :, None]

        # 2. Tán rừng Nổi khối Tự nhiên (Organic Stochastic Canopy — Không dùng sin*cos kẻ caro)
        rng_tex = np.random.default_rng(self.cfg.seed + 77)
        fine_grain = gaussian_filter(rng_tex.standard_normal((h, w)).astype(np.float32), sigma=0.85)
        canopy = ecology.canopy_cover
        canopy_relief = np.clip(fine_grain * canopy * 26.0, -22.0, 24.0)

        forest_deep_tint = np.array([34.0, 82.0, 42.0], dtype=np.float32)
        base_rgb = base_rgb * (1.0 - canopy[:, :, None] * 0.38) + forest_deep_tint * (canopy[:, :, None] * 0.38)
        base_rgb[:, :, 0] += canopy_relief * 0.6
        base_rgb[:, :, 1] += canopy_relief * 1.1
        base_rgb[:, :, 2] += canopy_relief * 0.5

        # 3. Áp dụng Bóng đổ Địa hình 3D (High-Contrast Relief Shading + Valley AO + Ridge Rimlight)
        valley_ao = np.clip(1.0 + np.minimum(0.0, curv) * 0.38, 0.62, 1.0)
        ridge_rim = np.maximum(0.0, curv) * 26.0 * (0.4 + 0.6 * shade)
        illumination = (0.38 + 0.88 * (shade ** 1.08)) * valley_ao

        lit_rgb = base_rgb * illumination[:, :, None] + ridge_rim[:, :, None]

        # 4. Kết xuất Đại dương Phân dải Độ sâu (Bathymetric Bands & Coastal Reef Halo)
        sea = ~land
        d = landmass.bathymetry
        shelf = landmass.coastal_shelf

        # Phân bậc nhẹ (Terraced Bathymetric Steps) kết hợp chuyển sắc mượt như bản đồ Atlas mẫu
        d_stepped = 0.72 * d + 0.28 * (np.floor(d * 7.0) / 7.0)
        ocean_r = 108.0 * (shelf ** 1.3) + 36.0 * (1.0 - d_stepped) * (1.0 - shelf) + 11.0 * d_stepped
        ocean_g = 196.0 * (shelf ** 1.2) + 116.0 * (1.0 - d_stepped) * (1.0 - shelf) + 42.0 * d_stepped
        ocean_b = 212.0 * (shelf ** 1.1) + 158.0 * (1.0 - d_stepped) * (1.0 - shelf) + 82.0 * d_stepped

        sea_relief = 0.90 + 0.20 * shade
        lit_rgb[:, :, 0] = np.where(sea, ocean_r * sea_relief, lit_rgb[:, :, 0])
        lit_rgb[:, :, 1] = np.where(sea, ocean_g * sea_relief, lit_rgb[:, :, 1])
        lit_rgb[:, :, 2] = np.where(sea, ocean_b * sea_relief, lit_rgb[:, :, 2])

        # Viền bờ biển cát vàng / đá ven bờ sắc nét (Shoreline Contour)
        shoreline = land & (soil.distance_to_water <= 1.8)
        lit_rgb[shoreline] = lit_rgb[shoreline] * 0.62 + np.array([212.0, 194.0, 146.0]) * 0.38

        # Vẽ Hồ Nước Ngọt Thượng Nguồn & Hồ Nội Lưu Tây Nam trên lưới gốc
        lit_rgb[hydrology.lake_mask & (~hydrology.endorheic_lake_mask)] = (38, 122, 178)
        lit_rgb[hydrology.endorheic_lake_mask] = (58, 148, 158)

        # 5. Phóng lên độ phân giải chuẩn 1600x1040 px & Vẽ Mạng lưới Sông ngòi Khử răng cưa (Smooth Vector Rivers)
        atlas_img = Image.fromarray(np.clip(lit_rgb, 0, 255).astype(np.uint8), mode="RGB")
        target_w, target_h = w * upscale_factor, h * upscale_factor
        resample_filter = getattr(Image, "Resampling", Image).LANCZOS
        atlas_img = atlas_img.resize((target_w, target_h), resample=resample_filter)

        draw = ImageDraw.Draw(atlas_img)
        for feat in hydrology.river_features:
            raw_coords = feat["geometry"]["coordinates"]
            s_order = int(feat["properties"]["stream_order"])
            smooth_pts = self._chaikin_smooth_coords(raw_coords, iterations=2)
            scaled_pts = [(x * upscale_factor, y * upscale_factor) for x, y in smooth_pts]

            if len(scaled_pts) >= 2:
                # Bề rộng dòng chảy tăng dần từ thượng nguồn xuống cửa biển
                n_pts = len(scaled_pts)
                for i in range(n_pts - 1):
                    prog = i / max(1, n_pts - 1)
                    width_px = max(1, int(round((0.8 + 0.65 * s_order) * (0.55 + 0.75 * prog))))
                    # Vẽ viền thung lũng ẩm sát bờ sông
                    draw.line([scaled_pts[i], scaled_pts[i + 1]], fill=(38, 86, 82), width=width_px + 2)
                    # Vẽ lòng nước sông xanh lam trầm
                    river_col = (56, 142, 188) if s_order <= 2 else (32, 108, 164)
                    draw.line([scaled_pts[i], scaled_pts[i + 1]], fill=river_col, width=width_px)

        atlas_img = atlas_img.filter(ImageFilter.UnsharpMask(radius=1.1, percent=55, threshold=2))
        atlas_img.save(path, "PNG")
        return atlas_img
