"""
world/atlas/atlas_renderer.py
Phase 7A: Kết xuất Bản đồ Thế giới Vật lý Nổi khối (Physical World Atlas Renderer)
cùng các bản đồ Sinh cảnh (habitat.png) và Mật độ Thực vật (vegetation_density.png).
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

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

    def render_vegetation_density_png(
        self, landmass: LandmassResult, hydrology: HydrologyResult, ecology: EcologyResult, path: str
    ) -> None:
        """Xuất vegetation_density.png: Vàng cát (0.0) -> Xanh non -> Xanh rừng nguyên sinh thẫm (1.0)."""
        h, w = ecology.vegetation_density.shape
        v = ecology.vegetation_density
        rgb = np.zeros((h, w, 3), dtype=np.float32)

        rgb[:, :, 0] = (1.0 - v) * 214.0 + v * 22.0
        rgb[:, :, 1] = (1.0 - v) * 192.0 + v * 98.0
        rgb[:, :, 2] = (1.0 - v) * 138.0 + v * 36.0

        rgb[~landmass.landmask] = (24, 62, 96)
        rgb[hydrology.river_mask | hydrology.lake_mask] = (46, 126, 182)
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
        """
        Xuất habitat.png: Bản đồ Sinh cảnh Động Thực vật & Hành lang Di cư (Wildlife Corridors)
        kèm vị trí các đàn thú lớn (Megafauna Herds).
        """
        rgb = biome.blended_biome_rgb.astype(np.float32)
        shade = (0.65 + 0.45 * terrain.shaded_relief)[:, :, None]
        rgb = np.where(landmass.landmask[:, :, None], rgb * shade, rgb)

        # Tô nổi bật nhẹ Hành lang Di cư tự nhiên
        corridor = ecology.wildlife_corridor_score
        rgb[:, :, 0] = np.where(landmass.landmask, rgb[:, :, 0] + corridor * 22.0, rgb[:, :, 0])
        rgb[:, :, 1] = np.where(landmass.landmask, rgb[:, :, 1] + corridor * 28.0, rgb[:, :, 1])

        rgb[~landmass.landmask] = (28, 74, 112)
        rgb[hydrology.river_mask | hydrology.lake_mask] = (44, 128, 188)

        img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")
        draw = ImageDraw.Draw(img)

        # Đánh dấu màu sinh thái cho từng nhóm đàn động vật (Guild Markers)
        guild_colors = {
            "megafauna_herbivore": (255, 215, 64),  # Vàng hổ phách (Voi ma mút, Bò rừng, Tê giác lông mượt)
            "medium_herbivore": (132, 238, 118),    # Xanh lá sáng (Hươu khổng lồ, Tuần lộc, Ngựa hoang)
            "omnivore": (232, 148, 72),             # Cam đất (Lợn rừng)
            "apex_predator": (238, 68, 68),         # Đỏ tươi (Hổ răng kiếm, Gấu hang, Sư tử hang)
            "pack_predator": (212, 92, 224),        # Tím hồng (Sói Dire)
            "aquatic_semi": (72, 224, 238),         # Xanh ngọc (Cá sấu đầm lầy, Hải ly, Cá hồi)
        }
        for herd in ecology.spawned_wildlife_herds:
            cx, cy = herd["world_col"], herd["world_row"]
            col = guild_colors.get(herd["guild"], (255, 255, 255))
            r_dot = 3 if herd["guild"] in ("megafauna_herbivore", "apex_predator") else 2
            draw.ellipse([cx - r_dot, cy - r_dot, cx + r_dot, cy + r_dot], fill=col, outline=(20, 20, 20))

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
        Kết xuất Bản đồ Thế giới Hoàn chỉnh (world_atlas.png) theo phong cách Physical Relief:
        - Nền 11 Quần xã pha trộn mềm với lớp Thổ nhưỡng & Độ cao.
        - Bóng đổ địa hình 3D sắc nét (Multi-directional Hillshading + Ambient Occlusion ở hẻm vực).
        - Hạt tán cây rừng 3D (Canopy Crown Texturing) nổi khối ở vùng rừng già và ven sông.
        - Đại dương phân tầng độ sâu Bathymetry với viền thềm lục địa ngọc lam (Coastal Reef Halo).
        """
        h, w = landmass.landmask.shape
        land = landmass.landmask
        elev = terrain.final_heightmap
        shade = terrain.shaded_relief
        curv = terrain.curvature

        # 1. Pha trộn Màu Quần xã Mềm (75%) + Sắc thái Thổ nhưỡng & Đá núi cao (25%)
        base_rgb = biome.blended_biome_rgb.astype(np.float32)

        # Tăng độ tương phản đá xám và băng tuyết trên các sống núi cao (Alpine Ridge Enhancement)
        rock_exposure = np.clip((terrain.slope - 0.18) * 2.2 + np.maximum(0.0, elev - 0.68) * 2.5, 0.0, 0.85) * land
        snow_cap = np.clip((elev - 0.76) * 5.0 + (0.20 - climate.temperature) * 2.8, 0.0, 1.0) * land

        rock_color = np.array([128.0, 124.0, 120.0], dtype=np.float32)
        snow_color = np.array([242.0, 246.0, 252.0], dtype=np.float32)

        base_rgb = base_rgb * (1.0 - rock_exposure[:, :, None]) + rock_color * rock_exposure[:, :, None]
        base_rgb = base_rgb * (1.0 - snow_cap[:, :, None]) + snow_color * snow_cap[:, :, None]

        # 2. Kết cấu Tán rừng Nổi khối (3D Canopy Micro-Texturing)
        canopy = ecology.canopy_cover
        canopy_grain = np.sin(np.arange(h)[:, None] * 1.7) * np.cos(np.arange(w)[None, :] * 1.7)
        canopy_delta = (canopy * canopy_grain * 18.0)[:, :, None]
        forest_darken = (1.0 - canopy * 0.18)[:, :, None]
        base_rgb = np.where(land[:, :, None], base_rgb * forest_darken + canopy_delta, base_rgb)

        # 3. Ánh sáng Nổi khối 3D (Shaded Relief + Valley Ambient Occlusion + Ridge Specular)
        valley_ao = np.clip(1.0 + np.minimum(0.0, curv) * 0.25, 0.72, 1.0)
        ridge_highlight = np.maximum(0.0, curv) * 18.0
        light_factor = (0.52 + 0.68 * shade) * valley_ao

        lit_rgb = base_rgb * light_factor[:, :, None] + ridge_highlight[:, :, None]

        # 4. Kết xuất Đại dương Phân tầng Độ sâu (Bathymetric Bands & Coastal Shelf Halo)
        sea = ~land
        d = landmass.bathymetry
        shelf = landmass.coastal_shelf

        ocean_r = 98.0 * shelf + 38.0 * (1.0 - d) * (1.0 - shelf) + 12.0 * d
        ocean_g = 192.0 * shelf + 118.0 * (1.0 - d) * (1.0 - shelf) + 46.0 * d
        ocean_b = 208.0 * shelf + 158.0 * (1.0 - d) * (1.0 - shelf) + 84.0 * d

        # Tạo hiệu ứng gợn địa hình đáy biển nhẹ (Submarine Bathymetric Relief)
        sea_shade = 0.88 + 0.24 * shade
        lit_rgb[:, :, 0] = np.where(sea, ocean_r * sea_shade, lit_rgb[:, :, 0])
        lit_rgb[:, :, 1] = np.where(sea, ocean_g * sea_shade, lit_rgb[:, :, 1])
        lit_rgb[:, :, 2] = np.where(sea, ocean_b * sea_shade, lit_rgb[:, :, 2])

        # Viền bờ biển cát sáng / bọt sóng mỏng (Shoreline Rim)
        shore_rim = land & (soil.distance_to_water <= 1.5) & (elev < self.cfg.sea_level + 0.035)
        lit_rgb[shore_rim] = lit_rgb[shore_rim] * 0.55 + np.array([216.0, 198.0, 152.0]) * 0.45

        # 5. Vẽ Mạng lưới Sông ngòi Phân cấp, Hồ Nước Ngọt & Hồ Nội Lưu
        lit_rgb[hydrology.stream_order == 1] = (92, 168, 206)
        lit_rgb[hydrology.stream_order == 2] = (64, 146, 194)
        lit_rgb[hydrology.stream_order == 3] = (44, 126, 182)
        lit_rgb[hydrology.river_mask & (hydrology.stream_order >= 4)] = (28, 102, 164)

        lit_rgb[hydrology.lake_mask & (~hydrology.endorheic_lake_mask)] = (36, 118, 178)
        lit_rgb[hydrology.endorheic_lake_mask] = (58, 148, 156)

        atlas_img = Image.fromarray(np.clip(lit_rgb, 0, 255).astype(np.uint8), mode="RGB")
        if upscale_factor > 1:
            resample_filter = getattr(Image, "Resampling", Image).LANCZOS
            atlas_img = atlas_img.resize(
                (w * upscale_factor, h * upscale_factor), resample=resample_filter
            )
            atlas_img = atlas_img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=65, threshold=2))

        atlas_img.save(path, "PNG")
        return atlas_img
