"""
world/atlas/atlas_renderer.py
Kết xuất Bản đồ Thế giới Vật lý Nổi khối (Physical Relief Atlas 1024x1024 px)
chuẩn mỹ thuật đa lục địa (Multi-Continent Primeval World):
- Nhiều lục địa tách biệt rõ rệt (Tây Bắc, Tây Nam, Trung Tâm-Đông Nam, Đông Bắc, Quần đảo)
- Phân biệt rõ nét 11 Quần xã sinh thái (Băng tuyết, Vách núi đá, Rừng, Đồng cỏ, Sa mạc vàng, v.v.)
- Thềm lục địa phát sáng xanh ngọc (Turquoise Reef Halo) ôm trọn mọi bờ biển
- Khung chú giải HUD "ĐẠI LỤC NGUYÊN SINH" góc dưới bên trái
- Lưới tọa độ chiến thuật A-L (cột) và 1-12 (hàng)
- La bàn định hướng Bắc ("B") góc trên bên phải
"""

import math
from pathlib import Path
from typing import List, Tuple, Dict
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from scipy.ndimage import gaussian_filter
except ImportError:
    def gaussian_filter(arr: np.ndarray, sigma: float = 0.85) -> np.ndarray:
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
        """Làm mượt gấp khúc D8 thành đường cong sông uốn khúc tự nhiên."""
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
        rgb[~landmass.landmask] = (18, 54, 88)
        rgb[hydrology.river_mask | hydrology.lake_mask] = (44, 142, 204)
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
        shade = (0.60 + 0.55 * terrain.shaded_relief)[:, :, None]
        rgb = np.where(landmass.landmask[:, :, None], rgb * shade, rgb)
        rgb[~landmass.landmask] = (20, 58, 96)
        rgb[hydrology.river_mask | hydrology.lake_mask] = (44, 142, 204)

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

    def _render_hud_elements(self, img: Image.Image, w: int, h: int) -> None:
        """Kết xuất Lưới tọa độ 12x12, La bàn Bắc 'B' và Khung chú giải 'ĐẠI LỤC NGUYÊN SINH'."""
        draw = ImageDraw.Draw(img)

        def _font(sz: int, bold: bool = False):
            font_candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "assets/fonts/DejaVuSans-Bold.ttf" if bold else "assets/fonts/DejaVuSans.ttf",
            ]
            for p in font_candidates:
                if Path(p).exists():
                    return ImageFont.truetype(p, sz)
            return ImageFont.load_default()

        f_grid = _font(12)
        f_compass = _font(15, bold=True)
        f_legend_title = _font(13, bold=True)
        f_legend_item = _font(10, bold=True)
        f_cartouche = _font(11, bold=True)

        # 1. Lưới tọa độ chiến thuật (12x12 Graticule Grid)
        step = w / 12.0
        grid_line_col = (180, 230, 255, 30)
        grid_text_col = (210, 240, 255, 215)

        for k in range(1, 12):
            pos = int(round(k * step))
            draw.line([(pos, 0), (pos, h)], fill=grid_line_col[:3], width=1)
            draw.line([(0, pos), (w, pos)], fill=grid_line_col[:3], width=1)

        for k in range(12):
            draw.text((int(round(k * step + step * 0.45)), 6), chr(ord("A") + k), fill=grid_text_col[:3], font=f_grid)
            draw.text((6, int(round(k * step + step * 0.42))), str(k + 1), fill=grid_text_col[:3], font=f_grid)

        # 2. La bàn hướng Bắc ("B") tại góc trên bên phải
        cx, cy, cr = w - 58, 68, 30
        draw.polygon([(cx, cy - cr), (cx - 7, cy), (cx, cy - 5)], fill=(245, 242, 230))
        draw.polygon([(cx, cy - cr), (cx + 7, cy), (cx, cy - 5)], fill=(125, 130, 140))
        draw.polygon([(cx, cy + cr * 0.7), (cx - 6, cy), (cx, cy + 4)], fill=(160, 165, 175))
        draw.polygon([(cx, cy + cr * 0.7), (cx + 6, cy), (cx, cy + 4)], fill=(85, 90, 100))
        draw.text((cx - 5, cy - cr - 18), "B", fill=(245, 242, 230), font=f_compass)

        # 3. Khung Chú Giải HUD "ĐẠI LỤC NGUYÊN SINH" tại góc dưới bên trái
        leg_x = 18
        leg_y = h - 248
        leg_w = 210
        leg_h = 230

        leg_bg = Image.new("RGBA", (leg_w, leg_h), (18, 28, 42, 238))
        leg_draw = ImageDraw.Draw(leg_bg)
        leg_draw.rounded_rectangle([(0, 0), (leg_w - 1, leg_h - 1)], radius=8, outline=(195, 175, 130, 220), width=2)
        leg_draw.text((14, 12), "ĐẠI LỤC NGUYÊN SINH", fill=(245, 230, 175), font=f_legend_title)

        legend_items = [
            ("Đỉnh băng tuyết", (252, 254, 255)),
            ("Vách núi đá", (56, 66, 80)),
            ("Đài nguyên", (146, 158, 118)),
            ("Rừng lá kim", (46, 88, 62)),
            ("Rừng ôn đới", (48, 112, 42)),
            ("Rừng nguyên sinh", (22, 82, 30)),
            ("Đồng cỏ", (110, 182, 60)),
            ("Thảo nguyên", (222, 152, 46)),
            ("Hoang mạc cát", (246, 192, 88)),
            ("Đầm lầy cửa sông", (68, 122, 96)),
            ("Bờ cát", (246, 230, 180)),
        ]

        item_y = 36
        box_sz = 10
        for name, col in legend_items:
            leg_draw.rectangle([(14, item_y + 2), (14 + box_sz, item_y + 2 + box_sz)], fill=col, outline=(30, 30, 30))
            leg_draw.text((32, item_y), name, fill=(235, 240, 245), font=f_legend_item)
            item_y += 17

        img.paste(leg_bg, (leg_x, leg_y), leg_bg)

        # 4. Thẻ định danh địa lý các đại lục (Continent Cartouches)
        cartouches = [
            ("LỤC ĐỊA BĂNG BẮC (ARCTICA)", int(w * 0.24), int(h * 0.08), (200, 235, 255)),
            ("LỤC ĐỊA CAO NGUYÊN (ORIENTIS)", int(w * 0.65), int(h * 0.12), (230, 245, 215)),
            ("LỤC ĐỊA SA MẠC (GONDWANA)", int(w * 0.25), int(h * 0.55), (255, 215, 145)),
            ("ĐẠI LỤC RỪNG THIÊNG (VERDANTIA)", int(w * 0.65), int(h * 0.44), (180, 245, 190)),
        ]
        for c_title, tx, ty, tcol in cartouches:
            bbox = f_cartouche.getbbox(c_title)
            tw = bbox[2] - bbox[0]
            draw.rounded_rectangle(
                [(tx - tw // 2 - 8, ty - 3), (tx + tw // 2 + 8, ty + 18)],
                radius=4,
                fill=(12, 22, 34, 210),
                outline=(195, 175, 130, 180),
                width=1,
            )
            draw.text((tx - tw // 2, ty), c_title, fill=tcol, font=f_cartouche)

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
        h, w = landmass.landmask.shape
        land = landmass.landmask
        elev = terrain.final_heightmap
        slope = terrain.slope
        shade = terrain.shaded_relief

        # 1. BẢNG MÀU QUẦN XÃ TƯƠNG PHẢN CAO (HIGH-CONTRAST PALETTE)
        # Bắt đầu từ dải màu blend sinh thái chuẩn
        base_rgb = biome.blended_biome_rgb.astype(np.float32)

        # A. Cồn cát vàng rực rỡ và hẻm núi đất son vùng Sa mạc Tây Nam
        arid_mask = np.clip((climate.aridity_index - 0.28) * 2.2, 0.0, 1.0) * land
        golden_sand = np.array([246.0, 192.0, 88.0], dtype=np.float32)
        base_rgb = base_rgb * (1.0 - arid_mask[:, :, None] * 0.55) + golden_sand * (arid_mask[:, :, None] * 0.55)

        # Hẻm núi đỏ trên sườn dốc sa mạc
        red_canyon = (slope > 0.26) & (climate.aridity_index > 0.38) & land
        base_rgb[red_canyon] = np.array([194.0, 72.0, 38.0], dtype=np.float32)

        # B. Vách đá xám sừng sững trên sườn dốc lớn và sườn núi tuyết
        rock_cliff = (slope > 0.28) & (elev > 0.44) & (~red_canyon) & land
        base_rgb[rock_cliff] = np.array([56.0, 66.0, 80.0], dtype=np.float32)

        # C. Băng tuyết trắng muốt vĩnh cửu trên các đỉnh núi cao
        snow_cap = (elev > 0.62) & (climate.temperature < 0.32) & (~rock_cliff) & land
        extreme_snow = (elev > 0.72) & (climate.temperature < 0.26) & land
        base_rgb[snow_cap] = np.array([245.0, 248.0, 252.0], dtype=np.float32)
        base_rgb[extreme_snow] = np.array([254.0, 255.0, 255.0], dtype=np.float32)

        # D. Tán rừng nguyên sinh ngọc lục bảo đậm đà
        canopy = ecology.canopy_cover
        deep_rainforest = (canopy > 0.52) & (climate.precipitation > 0.48) & land
        base_rgb[deep_rainforest] = np.array([22.0, 82.0, 30.0], dtype=np.float32)

        # E. Đồng cỏ tươi sáng
        is_meadow = (biome.primary_biome_id == 9) & land
        base_rgb[is_meadow] = np.array([110.0, 182.0, 60.0], dtype=np.float32)

        # F. Bờ cát vàng óng sát mép biển
        is_shore = land & (soil.distance_to_water <= 2.2) & (elev < 0.42)
        base_rgb[is_shore] = np.array([246.0, 230.0, 180.0], dtype=np.float32)

        # 2. BÓNG ĐỔ ĐỊA HÌNH 3D (3D RELIEF SHADING + AO + CREST RIM)
        valley_ao = np.clip(1.0 + np.minimum(0.0, terrain.curvature) * 0.35, 0.65, 1.0)
        crest_rim = np.maximum(0.0, terrain.curvature) * 28.0 * (0.4 + 0.6 * shade)
        illumination = (0.50 + 0.75 * (shade ** 1.1)) * valley_ao

        lit_rgb = base_rgb * illumination[:, :, None] + crest_rim[:, :, None]

        # 3. THỀM LỤC ĐỊA PHÁT SÁNG XANH NGỌC & ĐẠI DƯƠNG SÂU (SIGNATURE REEF HALO)
        sea = ~land
        d = landmass.bathymetry
        shelf = landmass.coastal_shelf

        # Thềm san hô xanh ngọc lam phát sáng rực rỡ ôm trọn đường bờ biển
        reef_glow = shelf ** 1.15
        ocean_r = 12.0 * (1.0 - reef_glow) + 48.0 * reef_glow
        ocean_g = 36.0 * (1.0 - reef_glow) + 228.0 * reef_glow
        ocean_b = 78.0 * (1.0 - reef_glow) + 242.0 * reef_glow

        # Độ sâu đại dương chuyển tiếp mềm
        ocean_r = ocean_r * (1.0 - d * 0.45)
        ocean_g = ocean_g * (1.0 - d * 0.35)
        ocean_b = ocean_b * (1.0 - d * 0.25)

        lit_rgb[:, :, 0] = np.where(sea, ocean_r, lit_rgb[:, :, 0])
        lit_rgb[:, :, 1] = np.where(sea, ocean_g, lit_rgb[:, :, 1])
        lit_rgb[:, :, 2] = np.where(sea, ocean_b, lit_rgb[:, :, 2])

        # Hồ nước ngọt và hồ băng
        lit_rgb[hydrology.lake_mask & (~hydrology.endorheic_lake_mask)] = (36, 142, 210)
        lit_rgb[hydrology.endorheic_lake_mask] = (42, 160, 168)

        # 4. PHÓNG LÊN ĐỘ PHÂN GIẢI 1024x1024 PX & VẼ SÔNG NGÒI VECTOR CHAIKIN
        target_w, target_h = w * upscale_factor, h * upscale_factor
        atlas_img = Image.fromarray(np.clip(lit_rgb, 0, 255).astype(np.uint8), mode="RGB")
        resample_filter = getattr(Image, "Resampling", Image).LANCZOS
        atlas_img = atlas_img.resize((target_w, target_h), resample=resample_filter)

        draw = ImageDraw.Draw(atlas_img)

        # Vẽ mạng lưới sông ngòi mượt mà khử răng cưa
        for feat in hydrology.river_features:
            raw_coords = feat["geometry"]["coordinates"]
            s_order = int(feat["properties"]["stream_order"])
            smooth_pts = self._chaikin_smooth_coords(raw_coords, iterations=2)
            scaled_pts = [(x * upscale_factor, y * upscale_factor) for x, y in smooth_pts]

            if len(scaled_pts) >= 2:
                n_pts = len(scaled_pts)
                for i in range(n_pts - 1):
                    prog = i / max(1, n_pts - 1)
                    width_px = max(1, int(round((0.8 + 0.5 * s_order) * (0.65 + 0.50 * prog))))
                    # Viền bóng sông
                    if s_order >= 3:
                        draw.line([scaled_pts[i], scaled_pts[i + 1]], fill=(22, 60, 72), width=width_px + 2)
                    river_col = (52, 175, 228) if s_order <= 2 else (36, 142, 204)
                    draw.line([scaled_pts[i], scaled_pts[i + 1]], fill=river_col, width=width_px)

        # 5. ĐƯỜNG MÒN THỜI TIỀN SỬ (ANCIENT EXPEDITION TRAILS)
        trail_points = [
            [(int(target_w * 0.62), int(target_h * 0.76)), (int(target_w * 0.60), int(target_h * 0.66)), (int(target_w * 0.56), int(target_h * 0.56)), (int(target_w * 0.52), int(target_h * 0.46))],
            [(int(target_w * 0.62), int(target_h * 0.76)), (int(target_w * 0.70), int(target_h * 0.70)), (int(target_w * 0.73), int(target_h * 0.60)), (int(target_w * 0.65), int(target_h * 0.44))],
            [(int(target_w * 0.52), int(target_h * 0.46)), (int(target_w * 0.58), int(target_h * 0.38)), (int(target_w * 0.62), int(target_h * 0.30)), (int(target_w * 0.66), int(target_h * 0.25))],
            [(int(target_w * 0.22), int(target_h * 0.76)), (int(target_w * 0.26), int(target_h * 0.71)), (int(target_w * 0.32), int(target_h * 0.66))],
        ]
        for path_pts in trail_points:
            for i in range(len(path_pts) - 1):
                p1, p2 = path_pts[i], path_pts[i + 1]
                draw.line([p1, p2], fill=(138, 118, 80), width=4)
                draw.line([p1, p2], fill=(225, 208, 168), width=2)

        # 6. KẾT XUẤT CÁC PHẦN TỬ HUD ATLAS
        self._render_hud_elements(atlas_img, target_w, target_h)

        atlas_img = atlas_img.filter(ImageFilter.UnsharpMask(radius=1.1, percent=45, threshold=2))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        atlas_img.save(path, "PNG")
        return atlas_img
