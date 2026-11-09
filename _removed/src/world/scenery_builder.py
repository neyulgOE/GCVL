"""
Natural Scenery & Spatial Relief Builder.
Chuyên trách hiển thị cấu trúc không gian thung lũng tự nhiên (100% không có công trình con người):
- Bảng màu tự nhiên theo đúng tài liệu thiết kế (Xanh ô-liu đồng cỏ, Xanh lá trầm rừng già,
  Vàng cát bãi bồi, Nâu sẫm bùn ướt, Xám lạnh/Nâu đá vách núi, Xanh lục lam trầm lòng sông).
- Vẽ Vách núi đá xếp lớp góc cạnh (Layered Faceted Rock Cliffs) kèm bóng đổ hướng nắng.
- Vẽ Sông uốn khúc có độ sâu, ghềnh đá bọt trắng thượng nguồn và bãi bồi cát sỏi bất đối xứng.
- Vẽ Điểm mốc tự nhiên (Hóa thạch xương sườn/ngà khổng lồ bên bờ sông như ảnh tham chiếu số 2).
"""

import pygame
import os
import math
import random
from src.settings import TILE_SIZE, MAP_COLS, MAP_ROWS

# Bảng màu Tự nhiên chuẩn theo Tài liệu Thiết kế Môi trường Thời kỳ Đồ Đá
PALETTE_NATURAL = {
    "meadow_olive": (132, 162, 74),      # Đồng cỏ xanh ô-liu
    "meadow_gold": (168, 176, 88),       # Cỏ vàng nắng ấm
    "forest_humus": (62, 92, 52),        # Nền rừng xanh lá trầm
    "forest_moss": (78, 114, 62),        # Rêu xanh ẩm dưới tán rừng
    "sand_dry": (212, 174, 106),         # Cát vàng bãi bồi (Point Bar - Ảnh 1)
    "sand_wet": (168, 132, 78),          # Cát ướt sát mép nước
    "mud_silt": (96, 76, 56),            # Đất bùn / phù sa mịn ven sông & đầm lầy
    "rock_light": (146, 150, 154),       # Mặt đá đón nắng
    "rock_mid": (104, 108, 114),         # Đá xám trung gian
    "rock_dark": (58, 62, 68),           # Khe nứt & mặt vách đá khuất bóng
    "water_deep": (38, 108, 128),        # Lòng sông sâu xanh lục lam trầm
    "water_mid": (64, 148, 162),         # Nước sông trung lưu
    "water_shallow": (118, 188, 184),    # Nước nông ánh cát ven bãi bồi
    "foam_white": (232, 244, 248),       # Bọt nước trắng ở ghềnh thác
    "fossil_ivory": (228, 220, 202),     # Màu ngà/xương hóa thạch cổ đại (Ảnh 2)
    "fossil_shadow": (148, 138, 122),
}


class SceneryBuilder:
    @staticmethod
    def build_storefront_sprites(ts, fonts):
        """Đã loại bỏ toàn bộ cửa hàng và nhà cửa nhân tạo."""
        return {}

    @staticmethod
    def build_farmhouse_exterior(ts):
        """Đã loại bỏ nền nhà/trại của con người; trả về surface trong suốt."""
        return pygame.Surface((ts, ts), pygame.SRCALPHA)

    @staticmethod
    def build_town_composite(ts, fonts):
        """Không còn Town Zone; trả về surface rỗng và danh sách đèn trống."""
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
        return surf, []

    @staticmethod
    def build_natural_valley_composite(map_mgr, ts=TILE_SIZE):
        """
        Kết xuất toàn bộ mặt đất, sông suối, bãi bồi, vách đá xếp lớp và điểm mốc tự nhiên
        dựa trực tiếp trên 7 lớp dữ liệu của MapManager.
        """
        w, h = map_mgr.cols * ts, map_mgr.rows * ts
        comp = pygame.Surface((w, h))
        rng = random.Random(map_mgr.seed)

        # 1. VẼ LỚP ĐẤT NỀN & ĐỔI SẮC ĐỘ THEO ĐỘ CAO + HƯỚNG SƯỜN DỐC (HILLSHADING)
        for r in range(map_mgr.rows):
            for c in range(map_mgr.cols):
                sx, sy = c * ts, r * ts
                biome = map_mgr.biome_map[r][c]
                t_type = map_mgr.farm_terrain[r][c]
                z = map_mgr.heightmap[r][c]
                aspect = map_mgr.aspect_map[r][c]
                slope = map_mgr.slope_map[r][c]
                wetness = map_mgr.surface_wetness[r][c]

                # Chọn màu vật liệu gốc
                if t_type == "water":
                    depth = map_mgr.water_depth[r][c]
                    base_col = PALETTE_NATURAL["water_deep"] if depth > 0.65 else PALETTE_NATURAL["water_mid"]
                elif t_type == "bridge_ford":
                    base_col = PALETTE_NATURAL["water_shallow"]
                elif biome == "rock_cliff":
                    base_col = PALETTE_NATURAL["rock_mid"]
                elif biome == "wetland_marsh":
                    base_col = PALETTE_NATURAL["mud_silt"]
                elif biome == "riparian_corridor":
                    base_col = PALETTE_NATURAL["sand_dry"] if t_type == "settlement_loam" else PALETTE_NATURAL["sand_wet"]
                elif biome == "mixed_forest":
                    base_col = PALETTE_NATURAL["forest_humus"]
                else:
                    base_col = PALETTE_NATURAL["meadow_olive"]

                # Tính ánh sáng sườn dốc (Directional NW Hillshading tạo khối 3D cho địa hình)
                sun_angle = -math.pi * 0.75  # Ánh nắng chiếu từ hướng Tây-Bắc
                hillshade = math.cos(aspect - sun_angle) * min(0.35, slope * 2.8)
                shade_delta = int(hillshade * 95)

                # Đất ướt sau mưa sẫm màu hơn
                wet_darken = int(wetness * 28)

                cr = max(0, min(255, base_col[0] + shade_delta - wet_darken))
                cg = max(0, min(255, base_col[1] + shade_delta - wet_darken))
                cb = max(0, min(255, base_col[2] + shade_delta - wet_darken))
                pygame.draw.rect(comp, (cr, cg, cb), (sx, sy, ts, ts))

                # Chi tiết vi mô trên bề mặt (Micro-texture)
                if biome == "open_meadow":
                    # Vạt cỏ vàng nắng và hoa dại tím/vàng như ảnh 3
                    for _ in range(4):
                        gx = sx + rng.randint(6, ts - 6)
                        gy = sy + rng.randint(6, ts - 6)
                        pygame.draw.line(comp, PALETTE_NATURAL["meadow_gold"], (gx, gy), (gx + 2, gy - 5), 2)
                    if rng.random() < 0.22:
                        fx = sx + rng.randint(10, ts - 10)
                        fy = sy + rng.randint(10, ts - 10)
                        f_col = (165, 115, 210) if rng.random() < 0.55 else (235, 195, 65)
                        pygame.draw.circle(comp, f_col, (fx, fy), 2)

                elif biome == "riparian_corridor" and t_type != "water":
                    # Hạt cát và sỏi cuội rải dọc bãi bồi (Point Bar - Ảnh 1)
                    for _ in range(6):
                        px = sx + rng.randint(4, ts - 6)
                        py = sy + rng.randint(4, ts - 6)
                        pr = rng.randint(2, 5)
                        p_col = (145, 130, 105) if rng.random() < 0.6 else (115, 110, 102)
                        pygame.draw.ellipse(comp, p_col, (px, py, pr * 2, pr))

        # 2. VẼ CHUYỂN TIẾP BỜ SÔNG, GHỀNH THÁC & VIỀN NƯỚC NÔNG (SHORELINE & RAPIDS)
        for r in range(1, map_mgr.rows - 1):
            for c in range(1, map_mgr.cols - 1):
                sx, sy = c * ts, r * ts
                t_type = map_mgr.farm_terrain[r][c]

                if t_type in ("water", "bridge_ford"):
                    # Kiểm tra ô sát bờ để vẽ viền nước nông trong vắt ánh cát
                    is_shore = any(
                        map_mgr.farm_terrain[r + dr][c + dc] not in ("water", "bridge_ford")
                        for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    )
                    if is_shore:
                        pygame.draw.rect(comp, PALETTE_NATURAL["water_shallow"], (sx, sy, ts, ts), 6)

                    # Ghềnh đá cạn & bọt sóng trắng (như ảnh 1 và thượng nguồn ảnh 3)
                    if t_type == "bridge_ford" or r < 18:
                        for _ in range(3):
                            rx = sx + rng.randint(10, ts - 14)
                            ry = sy + rng.randint(10, ts - 14)
                            pygame.draw.ellipse(comp, PALETTE_NATURAL["rock_mid"], (rx, ry, 14, 10))
                            pygame.draw.arc(comp, PALETTE_NATURAL["foam_white"], (rx - 3, ry - 2, 20, 14), 0, math.pi, 2)

        # 3. VẼ KHỐI VÁCH ĐÁ XẾP LỚP 3D & BÓNG ĐỔ SÂU (FACETED CLIFFS - NHƯ ẢNH 1 & 2)
        for r in range(1, map_mgr.rows - 1):
            for c in range(1, map_mgr.cols - 1):
                sx, sy = c * ts, r * ts
                drop_s = map_mgr.farm_cliff_south[r][c]
                drop_e = map_mgr.farm_cliff_east[r][c]
                drop_w = map_mgr.farm_cliff_west[r][c]

                if drop_s > 0 or drop_e > 0 or drop_w > 0:
                    cliff_h = min(ts, 18 * max(drop_s, drop_e, drop_w))
                    # Bóng đổ dài của vách đá xuống mặt sông / bãi cát bên dưới
                    shadow_surf = pygame.Surface((ts + 24, cliff_h + 20), pygame.SRCALPHA)
                    pygame.draw.ellipse(shadow_surf, (15, 22, 28, 95), (0, 6, ts + 20, cliff_h + 12))
                    comp.blit(shadow_surf, (sx - 4, sy + ts - 10))

                    # Vẽ các mảng đá đa giác góc cạnh (Faceted Rock Outcrop)
                    poly_top = [(sx, sy + ts - 14), (sx + ts // 2, sy + ts - 22), (sx + ts, sy + ts - 12),
                                (sx + ts, sy + ts + cliff_h - 8), (sx + ts // 2, sy + ts + cliff_h), (sx, sy + ts + cliff_h - 10)]
                    pygame.draw.polygon(comp, PALETTE_NATURAL["rock_dark"], poly_top)
                    # Mảng đá đón nắng bên trái
                    facet_light = [(sx, sy + ts - 14), (sx + ts // 2, sy + ts - 22),
                                   (sx + ts // 2 - 4, sy + ts + cliff_h // 2), (sx, sy + ts + cliff_h - 10)]
                    pygame.draw.polygon(comp, PALETTE_NATURAL["rock_light"], facet_light)
                    # Rêu xanh bám trên gờ vách đá ẩm
                    pygame.draw.line(comp, PALETTE_NATURAL["forest_moss"], (sx + 4, sy + ts - 14), (sx + ts - 4, sy + ts - 12), 4)

        # 4. VẼ CÁC ĐIỂM MỐC TỰ NHIÊN (NATURAL LANDMARKS - HÓA THẠCH NGÀ VOI & THÁC ĐÁ)
        for lm in getattr(map_mgr, "natural_landmarks", []):
            lx = lm["col"] * ts
            ly = lm["row"] * ts
            if lm["type"] == "colossal_rib_fossils":
                # Hàng xương sườn / ngà hóa thạch khổng lồ cắm nghiêng bên bờ sông (Tham chiếu Ảnh 2)
                for idx in range(5):
                    rib_x = lx + idx * 28
                    rib_y = ly + idx * 18
                    # Bóng đổ dài của xương hóa thạch trên bãi bồi
                    sh_surf = pygame.Surface((90, 36), pygame.SRCALPHA)
                    pygame.draw.ellipse(sh_surf, (15, 20, 25, 90), (0, 8, 86, 22))
                    comp.blit(sh_surf, (rib_x - 35, rib_y + 42))
                    # Chân xương sẫm màu cắm xuống đất
                    pygame.draw.polygon(comp, (65, 58, 50), [
                        (rib_x + 12, rib_y + 56), (rib_x + 28, rib_y + 56), (rib_x + 18, rib_y + 28)
                    ])
                    # Thân xương cong vút lên hướng về phía lòng sông
                    arc_rect = pygame.Rect(rib_x - 48, rib_y - 34, 76, 92)
                    pygame.draw.arc(comp, PALETTE_NATURAL["fossil_ivory"], arc_rect, 0.15, math.pi * 0.78, 8)
                    pygame.draw.arc(comp, PALETTE_NATURAL["fossil_shadow"], (arc_rect.x + 2, arc_rect.y + 3, 76, 92), 0.15, math.pi * 0.78, 3)

            elif lm["type"] == "upstream_boulder_cascade":
                # Bậc đá thác nước thượng nguồn (Tham chiếu Ảnh 3)
                for bx_off, by_off, bw, bh in [(-45, -10, 52, 34), (0, -4, 60, 38), (42, -12, 48, 32)]:
                    pygame.draw.ellipse(comp, PALETTE_NATURAL["rock_dark"], (lx + bx_off, ly + by_off + 6, bw, bh))
                    pygame.draw.ellipse(comp, PALETTE_NATURAL["rock_light"], (lx + bx_off, ly + by_off, bw, bh - 6))
                    # Dòng thác bọt trắng đổ qua khe đá
                    pygame.draw.line(comp, PALETTE_NATURAL["foam_white"],
                                     (lx + bx_off + bw // 2, ly + by_off + bh - 4),
                                     (lx + bx_off + bw // 2, ly + by_off + bh + 22), 5)

        return comp

    @staticmethod
    def enhance_farm_composite(base_comp, ts, fonts=None, map_mgr=None):
        """
        Ghi đè hàm cũ: Không còn vẽ trại, hàng rào hay cầu tàu.
        Nếu có map_mgr, kết xuất trực tiếp thung lũng tự nhiên có chiều sâu không gian.
        """
        if map_mgr is not None:
            return SceneryBuilder.build_natural_valley_composite(map_mgr, ts)
        return base_comp.copy()

    @staticmethod
    def load_environmental_props():
        """Chỉ tải các prop tự nhiên (hoa súng, đá dưới nước, hoa dại); bỏ cầu gỗ và hàng rào."""
        props = {}
        def safe_load(path):
            img = pygame.image.load(path)
            try:
                return img.convert_alpha()
            except Exception:
                return img

        wdec_path = "assets/pydew/environment/Water Decoration.png"
        if os.path.exists(wdec_path):
            sheet = safe_load(wdec_path)
            for i in range(4):
                props[f"water_dec_{i}"] = sheet.subsurface(pygame.Rect(i * 64, 0, 64, 64))

        plant_path = "assets/pydew/environment/Plant Decoration.png"
        if os.path.exists(plant_path):
            p_sheet = safe_load(plant_path)
            for r in range(2):
                for c in range(5):
                    sub = p_sheet.subsurface(pygame.Rect(c * 64, r * 64, 64, 64))
                    if pygame.mask.from_surface(sub).count() > 50:
                        props[f"plant_dec_{r * 5 + c}"] = sub

        return props
