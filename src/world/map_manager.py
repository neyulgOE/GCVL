"""
Wilderness Map Manager for Prehistoric Natural World.
Mô hình hóa 7 lớp dữ liệu tự nhiên có quan hệ nhân quả:
1. Terrain Layer: Heightmap liên tục (0.0..1.0), Slope, Aspect, Curvature, Roughness.
2. Hydrology Layer: D8 Flow Direction, Flow Accumulation, Suối phụ lưu (Tributary),
   Sông chính uốn khúc (Meandering River), Ghềnh đá thượng nguồn & Đầm lầy hạ lưu.
3. Soil & Splat Layer: Rock/Talus, River Sand/Pebble (Point Bar), Mud/Silt, Humus, Loam.
4. Multi-Canopy Vegetation: Rừng 6 tầng tán (Vượt tán -> Tán chính -> Dưới tán -> Bụi -> Cỏ -> Mặt đất).
5. Spatial Landmarks: Khối đá vách núi hai bên sườn thung lũng, Hóa thạch ngà khổng lồ ven sông.
(Hoàn toàn không có con người, nhà cửa hay công trình nhân tạo).
"""

import pygame
import random
import math
from src.settings import TILE_SIZE, MAP_COLS, MAP_ROWS, WORLD_WIDTH, WORLD_HEIGHT
from src.entities.obstacles import Obstacle

# Giữ hằng số tương thích nếu code bên ngoài có import
ZONE_FARM = "wilderness"
ZONE_TOWN = "wilderness"


class MultiOctaveNoise2D:
    """Bộ sinh nhiễu Perlin 2D đa tầng (FBM) & Domain Warping tạo địa hình tự nhiên."""

    def __init__(self, seed: int = 2026) -> None:
        self.seed = seed
        rng = random.Random(seed)
        self.perm = list(range(256))
        rng.shuffle(self.perm)
        self.perm += self.perm
        self.gradients = [
            (math.cos(2.0 * math.pi * i / 12.0), math.sin(2.0 * math.pi * i / 12.0))
            for i in range(12)
        ]

    @staticmethod
    def _fade(t: float) -> float:
        return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + t * (b - a)

    def _grad(self, hash_val: int, x: float, y: float) -> float:
        gx, gy = self.gradients[hash_val % 12]
        return gx * x + gy * y

    def noise2d(self, x: float, y: float) -> float:
        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        u = self._fade(xf)
        v = self._fade(yf)

        aa = self.perm[self.perm[xi] + yi]
        ab = self.perm[self.perm[xi] + yi + 1]
        ba = self.perm[self.perm[xi + 1] + yi]
        bb = self.perm[self.perm[xi + 1] + yi + 1]

        x1 = self._lerp(self._grad(aa, xf, yf), self._grad(ba, xf - 1.0, yf), u)
        x2 = self._lerp(self._grad(ab, xf, yf - 1.0), self._grad(bb, xf - 1.0, yf - 1.0), u)
        return self._lerp(x1, x2, v)

    def fbm(self, x: float, y: float, octaves: int = 4, persistence: float = 0.52,
            lacunarity: float = 2.0, base_scale: float = 0.04) -> float:
        total = 0.0
        amplitude = 1.0
        frequency = base_scale
        max_value = 0.0
        for _ in range(octaves):
            total += self.noise2d(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity
        return max(0.0, min(1.0, 0.5 + (total / max_value) * 0.85))


class MapManager:
    def __init__(self, seed: int = 2026):
        self.cols = MAP_COLS
        self.rows = MAP_ROWS
        self.seed = seed
        self.current_zone = ZONE_FARM

        # Bộ sinh nhiễu địa chất, độ ẩm và thực vật
        self.elev_noise = MultiOctaveNoise2D(seed=seed)
        self.warp_noise = MultiOctaveNoise2D(seed=seed + 101)
        self.moist_noise = MultiOctaveNoise2D(seed=seed + 303)
        self.flora_noise = MultiOctaveNoise2D(seed=seed + 707)

        # --- Lớp 1: Địa hình (Terrain & Topography) ---
        self.heightmap = [[0.5 for _ in range(self.cols)] for _ in range(self.rows)]
        self.slope_map = [[0.0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.aspect_map = [[0.0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.curvature_map = [[0.0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_elevation = [[2 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_cliff_south = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_cliff_east = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_cliff_west = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.farm_ramps = set()

        # --- Lớp 2: Thủy văn (Hydrology) ---
        self.flow_dir = [[(0, 0) for _ in range(self.cols)] for _ in range(self.rows)]
        self.flow_accum = [[1.0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.river_spine = []         # Trục sông chính [(col_float, row)]
        self.tributary_tiles = set()  # Nhánh suối phụ lưu từ khe núi
        self.water_depth = [[0.0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.water_level_offset = 0.0 # Biến động mực nước theo lượng mưa

        # --- Lớp 3: Đất đai & Bề mặt (Soil & Splat Map) ---
        self.farm_terrain = [["steppe_meadow" for _ in range(self.cols)] for _ in range(self.rows)]
        self.soil_type = [["loam" for _ in range(self.cols)] for _ in range(self.rows)]
        self.soil_moisture = [[0.4 for _ in range(self.cols)] for _ in range(self.rows)]
        self.surface_wetness = [[0.0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.biome_map = [["steppe_meadow" for _ in range(self.cols)] for _ in range(self.rows)]

        # --- Lớp 4 & 5: Thực vật đa tầng, Chướng ngại vật & Điểm mốc ---
        self.farm_obstacles = {}
        self.farm_water_tiles = set()
        self.farm_solid_tiles = set()
        self.natural_landmarks = []  # Hóa thạch xương khổng lồ, tảng đá rêu, ghềnh thác
        self.npcs = {}               # Trống hoàn toàn (không có con người)

        # Con trỏ tương thích ngược
        self.terrain = self.farm_terrain
        self.obstacles = self.farm_obstacles
        self.crops = {}
        self.water_tiles = self.farm_water_tiles
        self.solid_tiles = self.farm_solid_tiles
        self.world = self
        self.cliff_south = self.farm_cliff_south
        self.cliff_east = self.farm_cliff_east
        self.cliff_west = self.farm_cliff_west
        self.elevation_tier = self.farm_elevation

        # Animation mặt nước
        self.water_anim_timer = 0.0
        self.water_frame = 0

        self._generate_natural_valley()
        self._build_multi_canopy_ecosystem()

    # -------------------------------------------------------------------------
    # LỚP 1 & 2: ĐỊA HÌNH THUNG LŨNG & THỦY VĂN SÔNG SUỐI TỰ NHIÊN
    # -------------------------------------------------------------------------
    def get_river_center_float(self, r: float) -> float:
        """
        Trục sông uốn khúc bất đối xứng (Domain-Warped Meandering Spine)
        chảy từ hẻm núi Đông-Bắc cắt chéo qua thung lũng xuống châu thổ Tây-Nam.
        """
        r_clamped = max(0.0, min(float(self.rows - 1), float(r)))
        t = r_clamped / max(1.0, self.rows - 1.0)
        # Hướng chảy chéo tự nhiên từ vùng cao (Đông Bắc) về vùng thấp (Tây Nam)
        base_col = self.cols * (0.66 - 0.30 * t)
        # Khúc uốn lớn (Meander) kết hợp nhiễu địa hình để không bị lặp lại như hàm sin thuần
        meander_large = 9.5 * math.sin(t * math.pi * 2.3 - 0.4)
        noise_warp = (self.warp_noise.fbm(r_clamped * 0.7, 10.0, octaves=3, base_scale=0.06) - 0.5) * 11.0
        return max(8.0, min(self.cols - 9.0, base_col + meander_large + noise_warp))

    def get_river_half_width_float(self, r: float) -> float:
        """
        Bề rộng sông biến thiên theo độ dốc địa hình:
        - Thượng nguồn núi đá (r < 18): Suối hẹp chảy xiết qua khe đá (1.2 - 1.6 ô)
        - Trung lưu thung lũng (18 <= r <= 58): Uốn khúc, phình rộng ở ghềnh đá cạn (2.2 - 3.4 ô)
        - Hạ lưu đầm lầy (r > 58): Cửa sông phân nhánh rộng (3.5 - 4.6 ô) + co giãn theo mưa
        """
        t = r / max(1.0, self.rows - 1.0)
        noise_w = (self.warp_noise.noise2d(r * 0.15, 42.0)) * 0.45
        shallows_broaden = 1.15 * math.exp(-((r - 36.0) ** 2) / 9.0)
        if r < 18:
            base_w = 1.35 + 0.35 * t
        elif r > 58:
            base_w = 2.9 + (r - 58) * 0.08
        else:
            base_w = 2.05 + 0.55 * t + shallows_broaden
        return max(1.1, base_w + noise_w + self.water_level_offset)

    def get_river_curvature(self, r: float) -> float:
        """
        Tính đạo hàm bậc 2 (độ cong khúc cua) của tim sông tại hàng r:
        - Giá trị > 0: Sông đang cua sang phải -> Bờ trái là Bờ Lõm (vách đá xói mòn), Bờ phải là Bờ Lồi (bãi bồi cát sỏi).
        - Giá trị < 0: Sông đang cua sang trái -> Bờ phải là Bờ Lõm (vách đá), Bờ trái là Bờ Lồi (bãi bồi).
        """
        r0 = max(1.0, min(self.rows - 2.0, float(r)))
        c_prev = self.get_river_center_float(r0 - 1.5)
        c_curr = self.get_river_center_float(r0)
        c_next = self.get_river_center_float(r0 + 1.5)
        return (c_next - 2.0 * c_curr + c_prev)

    def _generate_natural_valley(self):
        """
        Khởi tạo cấu trúc không gian Thung lũng Phân tầng (Layered Valley Topology):
        - Sườn núi đá (Rock Cliffs) bao bọc 2 bên Tây-Bắc và Đông-Nam (như ảnh 1)
        - Dòng sông chính + 2 suối phụ lưu chảy từ khe núi xuống hợp lưu
        - Bờ lõm dựng đứng (Cut-bank cliff) vs Bờ lồi bãi bồi cát sỏi (Point bar)
        """
        self.farm_water_tiles.clear()
        self.farm_solid_tiles.clear()
        self.tributary_tiles.clear()
        self.natural_landmarks.clear()

        # 1. Tạo Heightmap liên tục với hình thái Thung lũng chữ V / U
        for r in range(self.rows):
            ny = r / max(1.0, self.rows - 1.0)
            rc = self.get_river_center_float(r)
            hw = self.get_river_half_width_float(r)
            curv = self.get_river_curvature(r)

            for c in range(self.cols):
                nx = c / max(1.0, self.cols - 1.0)

                # Nhiễu địa chất Domain Warping tạo sườn đá tự nhiên
                wx = c + (self.warp_noise.noise2d(c * 0.05, r * 0.05) * 6.5)
                wy = r + (self.warp_noise.noise2d(c * 0.05 + 50, r * 0.05 + 50) * 6.5)
                raw_fbm = self.elev_noise.fbm(wx, wy, octaves=5, persistence=0.55, base_scale=0.035)

                # Độ cao tăng dần về 2 bên sườn thung lũng (Tây-Bắc và Đông-Nam như ảnh 1)
                dist_to_river = abs((c + 0.5) - rc)
                valley_wall_left = max(0.0, (18.0 - c) / 18.0) ** 1.6 * 0.48
                valley_wall_right = max(0.0, (c - (self.cols - 19.0)) / 18.0) ** 1.6 * 0.45
                north_highland = max(0.0, (0.32 - ny) * 0.65)
                south_basin_drop = max(0.0, (ny - 0.72) * 0.55)

                elev = (
                    0.34
                    + raw_fbm * 0.36
                    + valley_wall_left
                    + valley_wall_right
                    + north_highland
                    - south_basin_drop
                )

                # Mặt cắt ngang bất đối xứng quanh lòng sông (Cut-bank vs Point-bar)
                signed_offset = (c + 0.5) - rc  # Âm: bờ trái, Dương: bờ phải
                if dist_to_river <= hw:
                    # Lòng sông trũng sâu
                    depth_ratio = 1.0 - (dist_to_river / max(0.5, hw)) ** 2
                    elev = 0.12 - 0.06 * depth_ratio
                    self.water_depth[r][c] = round(0.4 + 0.6 * depth_ratio, 3)
                elif dist_to_river <= hw + 7.5:
                    bank_dist = dist_to_river - hw
                    # Kiểm tra bờ lõm (xói mòn tạo vách đá cao) hay bờ lồi (bãi bồi cát sỏi thoai thoải)
                    is_cut_bank = (signed_offset < 0 and curv > 0.12) or (signed_offset > 0 and curv < -0.12)
                    if is_cut_bank:
                        # Bờ vách đá dựng đứng sát mép nước (như bờ trái ảnh 2)
                        cliff_boost = 0.26 * math.exp(-bank_dist * 0.35)
                        elev = max(elev, 0.58 + cliff_boost)
                    else:
                        # Bãi bồi cát vàng & sỏi cuội thoải dần từ mép nước lên đồng cỏ (như ảnh 1)
                        point_bar_slope = (bank_dist / 7.5) ** 1.35
                        elev = 0.21 + (elev - 0.21) * point_bar_slope

                self.heightmap[r][c] = max(0.02, min(0.99, elev))

        # 2. Tính D8 Flow Direction & Flow Accumulation để khắc các nhánh Suối Phụ Lưu (Tributaries)
        self._compute_d8_hydrology_and_tributaries()

        # 3. Tính Slope (Độ dốc), Aspect (Hướng sườn), Curvature (Độ cong) & Bậc độ cao 2.5D
        for r in range(self.rows):
            for c in range(self.cols):
                z = self.heightmap[r][c]
                z_w = self.heightmap[r][max(0, c - 1)]
                z_e = self.heightmap[r][min(self.cols - 1, c + 1)]
                z_n = self.heightmap[max(0, r - 1)][c]
                z_s = self.heightmap[min(self.rows - 1, r + 1)][c]

                dz_dx = (z_e - z_w) * 0.5
                dz_dy = (z_s - z_n) * 0.5
                slope = math.hypot(dz_dx, dz_dy)
                aspect = math.atan2(dz_dy, -dz_dx)
                curvature = (z_w + z_e + z_n + z_s - 4.0 * z)

                self.slope_map[r][c] = round(slope, 4)
                self.aspect_map[r][c] = round(aspect, 4)
                self.curvature_map[r][c] = round(curvature, 4)

                # Quy đổi ra 5 tầng độ cao hiển thị vách đá 2.5D
                if z < 0.19:
                    self.farm_elevation[r][c] = 0
                elif z < 0.29:
                    self.farm_elevation[r][c] = 1
                elif z < 0.52:
                    self.farm_elevation[r][c] = 2
                elif z < 0.68:
                    self.farm_elevation[r][c] = 3
                else:
                    self.farm_elevation[r][c] = 4

        # Tính mặt vách đá 2.5D (Cliff Drops)
        for r in range(self.rows):
            for c in range(self.cols):
                cur_e = self.farm_elevation[r][c]
                self.farm_cliff_south[r][c] = max(0, cur_e - self.farm_elevation[min(self.rows - 1, r + 1)][c]) if cur_e >= 2 else 0
                self.farm_cliff_east[r][c] = max(0, cur_e - self.farm_elevation[r][min(self.cols - 1, c + 1)]) if cur_e >= 2 else 0
                self.farm_cliff_west[r][c] = max(0, cur_e - self.farm_elevation[r][max(0, c - 1)]) if cur_e >= 2 else 0

        # 4. Phân bổ Lớp Đất (Soil), Độ ẩm (Moisture) & Sinh cảnh (Biome Splat Map)
        for r in range(self.rows):
            rc = self.get_river_center_float(r)
            hw = self.get_river_half_width_float(r)
            curv = self.get_river_curvature(r)

            for c in range(self.cols):
                z = self.heightmap[r][c]
                slope = self.slope_map[r][c]
                dist_river = abs((c + 0.5) - rc)
                raw_m = self.moist_noise.fbm(c, r, octaves=4, base_scale=0.045)

                # Độ ẩm phụ thuộc khoảng cách tới sông/suối và độ trũng địa hình
                river_moist_boost = max(0.0, 1.0 - (dist_river / 16.0)) * 0.45
                moist = max(0.05, min(1.0, raw_m * 0.65 + river_moist_boost - max(0.0, z - 0.55) * 0.5))
                self.soil_moisture[r][c] = round(moist, 3)

                # A. Lòng sông chính & Suối phụ lưu
                if z < 0.19 or (c, r) in self.tributary_tiles:
                    # Ghềnh đá cạn tự nhiên ở vùng chuyển tiếp (r=35..37 hoặc thượng nguồn r=12..14)
                    if (35 <= r <= 37 or 12 <= r <= 13) and dist_river <= hw + 0.4:
                        self.farm_terrain[r][c] = "bridge_ford"  # Ghềnh đá lội qua tự nhiên
                        self.soil_type[r][c] = "gravel_rock"
                        self.biome_map[r][c] = "riparian_corridor"
                    else:
                        self.farm_terrain[r][c] = "water"
                        self.soil_type[r][c] = "sand"
                        self.biome_map[r][c] = "river_water"
                        self.farm_water_tiles.add((c, r))
                        self.farm_solid_tiles.add((c, r))

                # B. Đồi đá & Vách núi dựng đứng (18% diện tích - 4 góc & sườn thung lũng như ảnh 1 & 2)
                elif z >= 0.64 or slope >= 0.11:
                    self.farm_terrain[r][c] = "scree_talus"
                    self.soil_type[r][c] = "gravel_rock"
                    self.biome_map[r][c] = "rock_cliff"
                    if z >= 0.78 or slope >= 0.18:
                        self.farm_solid_tiles.add((c, r))  # Vách đá cao không thể leo trực diện

                # C. Đầm lầy & Vùng ngập nước góc thấp (8% diện tích - Hạ lưu phía Nam)
                elif r >= int(self.rows * 0.76) and z <= 0.34 and moist >= 0.62:
                    self.farm_terrain[r][c] = "riparian_mud"
                    self.soil_type[r][c] = "mud_silt"
                    self.biome_map[r][c] = "wetland_marsh"

                # D. Hành lang ven sông & Bãi bồi cát vàng/sỏi cuội (16% diện tích - Point Bar như ảnh 1)
                elif dist_river <= hw + 5.2 and z < 0.36:
                    # Bên bờ lồi tạo bãi cát vàng rộng (sand_point_bar), sát mép bùn là riparian_mud
                    signed_offset = (c + 0.5) - rc
                    is_point_bar = (signed_offset > 0 and curv > 0.05) or (signed_offset < 0 and curv < -0.05)
                    if is_point_bar or dist_river <= hw + 2.6:
                        self.farm_terrain[r][c] = "settlement_loam"  # Tái sử dụng mã màu cát vàng ấm của bãi bồi
                        self.soil_type[r][c] = "sand"
                    else:
                        self.farm_terrain[r][c] = "riparian_mud"
                        self.soil_type[r][c] = "mud_silt"
                    self.biome_map[r][c] = "riparian_corridor"

                # E. Rừng hỗn hợp đa tầng (32% diện tích - Bao quanh sườn đồi & rìa map)
                elif moist >= 0.52 or c <= 18 or c >= self.cols - 19 or z >= 0.46:
                    self.farm_terrain[r][c] = "forest_humus"
                    self.soil_type[r][c] = "humus"
                    self.biome_map[r][c] = "mixed_forest"

                # F. Đồng cỏ mở trung tâm thung lũng (22% diện tích - Open Meadow)
                else:
                    self.farm_terrain[r][c] = "steppe_meadow"
                    self.soil_type[r][c] = "loam"
                    self.biome_map[r][c] = "open_meadow"

        # 5. Đặt các Điểm mốc Tự nhiên (Natural Landmarks như ảnh 2 & ảnh 3)
        rc_mid = int(self.get_river_center_float(42))
        hw_mid = int(self.get_river_half_width_float(42))
        self.natural_landmarks = [
            # Hàng xương sườn / ngà voi hóa thạch khổng lồ cắm dọc bãi bồi bờ sông (như ảnh 2)
            {"type": "colossal_rib_fossils", "col": rc_mid + hw_mid + 2, "row": 40},
            # Ghềnh đá thác đổ ở thượng nguồn (như ảnh 3)
            {"type": "upstream_boulder_cascade", "col": int(self.get_river_center_float(12)), "row": 12},
            # Tảng đá bàn thạch phủ rêu bên bờ suối (như ảnh 3)
            {"type": "mossy_monolith", "col": int(self.get_river_center_float(28)) - 4, "row": 28},
        ]

    def _compute_d8_hydrology_and_tributaries(self):
        """
        Tính hướng dòng chảy D8 (8 hướng lân cận) và tích lũy dòng chảy (Flow Accumulation),
        từ đó khắc 2 nhánh suối phụ lưu chảy từ vách núi Tây-Bắc và Đông-Bắc hợp lưu vào sông chính.
        """
        d8_offsets = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
        cells_by_elev = []

        for r in range(self.rows):
            for c in range(self.cols):
                cells_by_elev.append((self.heightmap[r][c], c, r))
                best_drop = 0.0
                best_dir = (0, 0)
                z = self.heightmap[r][c]
                for dc, dr in d8_offsets:
                    nc, nr = c + dc, r + dr
                    if 0 <= nc < self.cols and 0 <= nr < self.rows:
                        dist = math.hypot(dc, dr)
                        drop = (z - self.heightmap[nr][nc]) / dist
                        if drop > best_drop:
                            best_drop = drop
                            best_dir = (dc, dr)
                self.flow_dir[r][c] = best_dir

        # Cộng dồn lượng nước từ đỉnh núi cao xuống vùng thấp
        cells_by_elev.sort(reverse=True, key=lambda x: x[0])
        for _, c, r in cells_by_elev:
            dc, dr = self.flow_dir[r][c]
            if dc != 0 or dr != 0:
                nc, nr = c + dc, r + dr
                if 0 <= nc < self.cols and 0 <= nr < self.rows:
                    self.flow_accum[nr][nc] += self.flow_accum[r][c]

        # Khắc 2 dòng suối phụ lưu (Tributary Streams) từ khe núi đổ vào sông chính (Confluence)
        stream_sources = [(12, 16), (self.cols - 12, 24)]
        for sc, sr in stream_sources:
            curr_c, curr_r = float(sc), float(sr)
            for _ in range(60):
                ic, ir = int(round(curr_c)), int(round(curr_r))
                if not (1 <= ic < self.cols - 1 and 1 <= ir < self.rows - 1):
                    break
                rc_target = self.get_river_center_float(ir)
                if abs(curr_c - rc_target) <= self.get_river_half_width_float(ir):
                    break  # Đã hợp lưu vào sông chính

                self.tributary_tiles.add((ic, ir))
                self.heightmap[ir][ic] = min(self.heightmap[ir][ic], 0.17)
                # Chảy hướng về phía sông chính và xuôi xuống hạ lưu
                step_c = 1.0 if rc_target > curr_c else -1.0
                noise_defl = self.warp_noise.noise2d(curr_c * 0.2, curr_r * 0.2) * 0.6
                curr_c += step_c * 0.75 + noise_defl
                curr_r += 0.45

    # -------------------------------------------------------------------------
    # LỚP 4: RỪNG ĐA TẦNG TÁN & PHÂN BỐ THỰC VẬT THEO CỤM SINH THÁI
    # -------------------------------------------------------------------------
    def _build_multi_canopy_ecosystem(self):
        """
        Rải thực vật và đá tự nhiên theo cấu trúc 6 tầng tán (Multi-Canopy Clustering):
        - Tuyệt đối không rải đều như lưới; dùng nhiễu cụm (Cluster Noise) và điều kiện đất/độ dốc.
        - Bãi bồi ven sông có sỏi cuội (pebble), đá tảng (boulder), gỗ lũa (log) và lau sậy (weeds).
        - Rừng có cây cổ thụ vượt tán, cây non dưới tán, bụi quả mọng, dương xỉ, nấm và cành khô.
        """
        rng = random.Random(self.seed)
        self.farm_obstacles.clear()

        for r in range(2, self.rows - 2):
            rc = self.get_river_center_float(r)
            hw = self.get_river_half_width_float(r)

            for c in range(2, self.cols - 2):
                if not self._can_place_obstacle(c, r):
                    continue

                biome = self.biome_map[r][c]
                z = self.heightmap[r][c]
                slope = self.slope_map[r][c]
                moist = self.soil_moisture[r][c]
                dist_river = abs((c + 0.5) - rc)
                cluster_val = self.flora_noise.fbm(c, r, octaves=3, base_scale=0.11)
                roll = rng.random()

                # 1. SINH CẢNH ĐỒI ĐÁ & CHÂN VÁCH NÚI (Rock Cliffs & Talus Scree)
                if biome == "rock_cliff":
                    if slope >= 0.09 and roll < 0.28:
                        self.farm_obstacles[(c, r)] = Obstacle("boulder", c, r, health=3, max_health=3)
                    elif roll < 0.42:
                        self.farm_obstacles[(c, r)] = Obstacle("rock_small", c, r, health=1)
                    elif z >= 0.66 and roll < 0.50:
                        # Thông núi cao (Conifer) mọc bám trên vách đá (như ảnh 2 & 3)
                        self.farm_obstacles[(c, r)] = Obstacle("tree_tundra", c, r, health=4, max_health=4)

                # 2. HÀNH LANG VEN SÔNG & BÃI BỒI CÁT SỎI (Riparian & Point Bar - như ảnh 1)
                elif biome == "riparian_corridor":
                    # Sát mép nước: Lau sậy, cói và đá cuội lòng suối
                    if dist_river <= hw + 1.6:
                        if roll < 0.32:
                            self.farm_obstacles[(c, r)] = Obstacle("weeds", c, r, health=1, variant=(c + r) % 2 + 1)
                        elif roll < 0.52:
                            self.farm_obstacles[(c, r)] = Obstacle("pebble", c, r, health=1)
                    # Trên bãi bồi cát vàng: Đá tảng rải rác, sỏi cuội, gỗ lũa trôi dạt và bụi cây thấp
                    else:
                        if roll < 0.18:
                            self.farm_obstacles[(c, r)] = Obstacle("pebble", c, r, health=1)
                        elif roll < 0.24:
                            self.farm_obstacles[(c, r)] = Obstacle("boulder", c, r, health=3, max_health=3)
                        elif roll < 0.28:
                            self.farm_obstacles[(c, r)] = Obstacle("log", c, r, health=2, max_health=2)
                        elif cluster_val > 0.58 and roll < 0.36:
                            self.farm_obstacles[(c, r)] = Obstacle("wild_bush", c, r, health=1)

                # 3. RỪNG HỖN HỢP ĐA TẦNG TÁN (Mixed Primeval Forest - 6 Canopy Layers)
                elif biome == "mixed_forest":
                    # Tầng vượt tán & Tán chính (Tập trung ở lõi cụm có cluster_val > 0.52)
                    if cluster_val > 0.55 and roll < 0.38:
                        tree_type = "tree_tundra" if z > 0.54 else "tree_forest"
                        self.farm_obstacles[(c, r)] = Obstacle(tree_type, c, r, health=4, max_health=4)
                    # Tầng dưới tán & Cây bụi ở rìa cụm rừng (Ecotone)
                    elif 0.42 <= cluster_val <= 0.55 and roll < 0.26:
                        self.farm_obstacles[(c, r)] = Obstacle("wild_bush", c, r, health=1)
                    # Tầng mặt đất: Cây mục đổ, gốc cây rêu, nấm ẩm và cành khô rụng
                    elif roll < 0.06:
                        self.farm_obstacles[(c, r)] = Obstacle("log", c, r, health=2, max_health=2)
                    elif roll < 0.11 and moist > 0.58:
                        self.farm_obstacles[(c, r)] = Obstacle("prop_mushroom", c, r, health=1)
                    elif roll < 0.16:
                        self.farm_obstacles[(c, r)] = Obstacle("branch", c, r, health=1)
                    elif roll < 0.20:
                        self.farm_obstacles[(c, r)] = Obstacle("boulder", c, r, health=3, max_health=3)

                # 4. ĐỒNG CỎ MỞ TRUNG TÂM (Open Steppe Meadow)
                elif biome == "open_meadow":
                    # Giữ không gian thoáng đãng để tạo chiều sâu thị giác, chỉ điểm xuyết cụm cây tán rộng & bụi hoa quả
                    if cluster_val > 0.68 and roll < 0.14:
                        self.farm_obstacles[(c, r)] = Obstacle("tree_steppe", c, r, health=4, max_health=4)
                    elif cluster_val > 0.62 and roll < 0.22:
                        self.farm_obstacles[(c, r)] = Obstacle("wild_bush", c, r, health=1)
                    elif roll < 0.03:
                        self.farm_obstacles[(c, r)] = Obstacle("rock_small", c, r, health=1)

                # 5. ĐẦM LẦY HẠ LƯU (Wetland Marsh)
                elif biome == "wetland_marsh":
                    if roll < 0.22:
                        self.farm_obstacles[(c, r)] = Obstacle("tree_swamp", c, r, health=4, max_health=4)
                    elif roll < 0.45:
                        self.farm_obstacles[(c, r)] = Obstacle("weeds", c, r, health=1)
                    elif roll < 0.55:
                        self.farm_obstacles[(c, r)] = Obstacle("clay_patch", c, r, health=1)

        self.obstacles = self.farm_obstacles

    # -------------------------------------------------------------------------
    # PHẢN ỨNG MÔI TRƯỜNG ĐỘNG THEO THỜI TIẾT & MÙA (CAUSAL ENVIRONMENT UPDATE)
    # -------------------------------------------------------------------------
    def apply_weather_response(self, dt: float, weather: str, rain_intensity: float = 0.0):
        """
        Cập nhật độ ẩm mặt đất (Surface Wetness) và mực nước sông (Water Response) theo thời tiết:
        - Khi mưa: Đất sét/bùn và đất thịt sẫm màu nhanh; mực nước suối dâng cao làm ngập bãi sỏi thấp.
        - Khi nắng: Cát và đá khô nhanh nhất; bùn đầm lầy giữ ẩm lâu nhất.
        """
        is_wet_weather = weather in ("rain", "storm") or rain_intensity > 0.1
        target_offset = 0.45 if weather == "storm" else (0.25 if weather == "rain" else 0.0)
        self.water_level_offset += (target_offset - self.water_level_offset) * min(1.0, dt * 0.5)

        for r in range(self.rows):
            for c in range(self.cols):
                st = self.soil_type[r][c]
                cur_w = self.surface_wetness[r][c]
                if is_wet_weather:
                    absorb_rate = 0.35 if st in ("mud_silt", "loam") else 0.20
                    self.surface_wetness[r][c] = min(1.0, cur_w + dt * absorb_rate)
                else:
                    # Tốc độ khô phụ thuộc loại đất (Cát/đá khô nhanh, bùn giữ nước lâu)
                    dry_rate = 0.18 if st in ("sand", "gravel_rock") else (0.04 if st == "mud_silt" else 0.09)
                    self.surface_wetness[r][c] = max(0.0, cur_w - dt * dry_rate)

    def _can_place_obstacle(self, col: int, row: int) -> bool:
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return False
        if (col, row) in self.farm_water_tiles or (col, row) in self.farm_solid_tiles:
            return False
        if self.farm_terrain[row][col] == "bridge_ford":
            return False
        if (col, row) in self.farm_obstacles:
            return False
        return True

    def check_collision(self, rect: pygame.Rect) -> bool:
        """Kiểm tra va chạm với rìa bản đồ, vách đá dựng đứng, sông sâu và cây/đá lớn."""
        if rect.left < 20 or rect.right > WORLD_WIDTH - 20 or rect.top < 20 or rect.bottom > WORLD_HEIGHT - 20:
            return True

        ts = TILE_SIZE
        start_col = max(0, rect.left // ts)
        end_col = min(self.cols - 1, rect.right // ts)
        start_row = max(0, rect.top // ts)
        end_row = min(self.rows - 1, rect.bottom // ts)

        for r in range(start_row, end_row + 1):
            for c in range(start_col, end_col + 1):
                if (c, r) in self.solid_tiles or (c, r) in self.water_tiles:
                    tile_rect = pygame.Rect(c * ts + 4, r * ts + 4, ts - 8, ts - 8)
                    if rect.colliderect(tile_rect):
                        return True
                if (c, r) in self.obstacles:
                    obs = self.obstacles[(c, r)]
                    if not obs.is_ground_pickup:
                        obs_rect = pygame.Rect(c * ts + 8, r * ts + 8, ts - 16, ts - 16)
                        if rect.colliderect(obs_rect):
                            return True
        return False

    def is_water(self, col: int, row: int) -> bool:
        return (col, row) in self.water_tiles

    def is_near_water(self, col: int, row: int) -> bool:
        for dc, dr in [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]:
            if self.is_water(col + dc, row + dr):
                return True
        return False

    def update(self, dt: float):
        self.water_anim_timer += dt
        if self.water_anim_timer >= 0.24:
            self.water_anim_timer = 0.0
            self.water_frame = (self.water_frame + 1) % 4

        for obs in self.obstacles.values():
            obs.update(dt)

    def advance_day(self, current_season_id: str, is_raining: bool = False):
        """Vòng đời tự nhiên qua ngày mới (không có NPC hay ruộng lúa nhân tạo)."""
        if is_raining:
            self.apply_weather_response(10.0, "rain", 1.0)
        else:
            self.apply_weather_response(10.0, "sunny", 0.0)

    def switch_zone(self, new_zone, player=None, spawn_tile=None):
        return True

    def check_border_transition(self, player):
        return None

    def to_dict(self):
        return {
            "seed": self.seed,
            "farm_terrain": self.farm_terrain,
            "farm_obstacles": [obs.to_dict() for obs in self.farm_obstacles.values()],
        }

    def from_dict(self, data):
        self.seed = data.get("seed", self.seed)
        self.farm_terrain = data.get("farm_terrain", self.farm_terrain)
        self.farm_obstacles = {}
        for o_data in data.get("farm_obstacles", []):
            obs = Obstacle.from_dict(o_data)
            self.farm_obstacles[(obs.col, obs.row)] = obs
        self.terrain = self.farm_terrain
        self.obstacles = self.farm_obstacles
