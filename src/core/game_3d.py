"""
Bộ Điều Phối & Kết Xuất Phối Cảnh 3D (3D Perspective Spectator Engine)
cho Thế Giới Hoang Dã Tiền Sử Primeval Reach (GCVL).

- Hoàn toàn độc lập, sử dụng Pygame (tích hợp sẵn trong libs/) và NumPy.
- Tải bản đồ thế giới đa lục địa chuẩn Single Source of Truth từ debug_outputs/primeval_world_data.npz.
- Chiếu phối cảnh 3D thời gian thực (Perspective Camera, Depth Sorting, Lambertian Hillshading).
- Tích hợp động vật cổ đại (Voi ma mút, Bò rừng, Hổ răng kiếm, Gấu hang, Hươu khổng lồ) di chuyển trên bề mặt 3D.
- Hỗ trợ đầy đủ chế độ đồ họa cửa sổ và chế độ kiểm thử tự động không đầu (Headless mode).
"""

import os
import sys
import math
import json
import time
import random
from pathlib import Path
import numpy as np

# Đảm bảo đường dẫn thư viện
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
libs_dir = os.path.join(root_dir, "libs")
if os.path.exists(libs_dir) and libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)

import pygame

from src.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TITLE, FPS, TILE_SIZE,
    MAP_COLS, MAP_ROWS,
)
from src.world.map_manager import MapManager
from src.world.wildlife_manager import WildlifeManager
from src.world.canonical_ecology import build_ecology_maps, spawn_vegetation_instances


# Bảng màu 8 Quần xã chuẩn cho mô hình 3D
BIOME_COLORS = {
    0: (11, 44, 76),       # 0: Deep Ocean
    1: (28, 182, 196),     # 1: Coastal Reef Halo
    2: (42, 118, 158),     # 2: Meandering River & Lake
    3: (42, 94, 46),       # 3: Primeval Forest Valley
    4: (204, 134, 48),     # 4: Autumn Steppes Plateau
    5: (212, 114, 68),     # 5: Terracotta Dunes & Crater
    6: (240, 245, 250),    # 6: Glacial Alpine Massif
    7: (34, 102, 54),      # 7: Sanctuary Archipelago
}

BIOME_NAMES = {
    0: "Đại dương sâu (Deep Ocean)",
    1: "Vành đai san hô ngọc lam (Coastal Reef Halo)",
    2: "Sông uốn khúc & Hồ nội địa (River & Lake)",
    3: "Thung lũng rừng nguyên sinh (Primeval Forest)",
    4: "Cao nguyên thảo nguyên mùa thu (Autumn Steppes)",
    5: "Hoang mạc cát đỏ đồi đá (Terracotta Dunes)",
    6: "Dãy núi tuyết băng giá (Glacial Alpine)",
    7: "Quần đảo bảo tồn (Sanctuary Isle)",
}

BEAST_COLORS = {
    "mammoth": (85, 60, 42),
    "ancient_bison": (115, 68, 32),
    "sabertooth": (205, 145, 52),
    "dire_wolf": (92, 96, 102),
    "giant_deer": (148, 96, 56),
    "cave_bear": (76, 48, 30),
    "wild_boar": (102, 72, 50),
}


class Game3D:
    """Bộ mô phỏng thế giới tiền sử với máy ảnh phối cảnh 3D tự do."""

    # Tỷ lệ thế giới 3D
    TILE_SIZE_3D = 3.5
    HEIGHT_SCALE_3D = 22.0
    WATER_Y = 0.05 * HEIGHT_SCALE_3D

    # Các điểm mốc nhảy nhanh (Quick camera presets)
    CAMERA_PRESETS = {
        pygame.K_1: {
            "name": "1. Lục địa Băng giá Tây-Bắc (Glacial Alpine Massif)",
            "pos": (62.0, 36.0, 88.0),
            "yaw": 0.0,
            "pitch": -0.32,
        },
        pygame.K_2: {
            "name": "2. Hoang mạc Cát đỏ Tây-Nam (Terracotta Basin)",
            "pos": (50.0, 32.0, 175.0),
            "yaw": 0.0,
            "pitch": -0.35,
        },
        pygame.K_3: {
            "name": "3. Cao nguyên Thảo nguyên Mùa thu Đông-Bắc (Autumn Steppes)",
            "pos": (140.0, 38.0, 85.0),
            "yaw": 0.0,
            "pitch": -0.36,
        },
        pygame.K_4: {
            "name": "4. Đại Châu thổ & Rừng nguyên sinh Đông-Nam (Southern Delta)",
            "pos": (120.0, 34.0, 185.0),
            "yaw": 0.0,
            "pitch": -0.32,
        },
    }

    def __init__(self, width=SCREEN_WIDTH, height=SCREEN_HEIGHT, headless=False):
        self.width = width
        self.height = height
        self.headless = headless or (os.environ.get("GCVL_HEADLESS") == "1") or (os.environ.get("SDL_VIDEODRIVER") == "dummy")

        if self.headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"

        pygame.init()
        pygame.display.set_caption(f"{TITLE} - Phối Cảnh 3D Đa Lục Địa")

        if self.headless:
            self.screen = pygame.display.set_mode((width, height))
        else:
            try:
                self.screen = pygame.display.set_mode((width, height), pygame.DOUBLEBUF)
            except Exception:
                self.screen = pygame.display.set_mode((width, height))

        self.clock = pygame.time.Clock()
        self.running = True
        self.game_time = 0.0

        # Khởi tạo phông chữ
        pygame.font.init()
        font_name = pygame.font.match_font("dejavusans", "arial")
        self.font = pygame.font.Font(font_name, 14)
        self.font_bold = pygame.font.Font(font_name, 16)
        self.font_small = pygame.font.Font(font_name, 12)

        # 1. Tải WorldData canonical giữ đúng tỉ lệ bản đồ
        self._load_world_grid()

        # 2. Quản lý động vật hoang dã
        self.map_mgr = MapManager()
        self.wildlife_mgr = WildlifeManager(self.map_mgr)
        self._spawn_world_megafauna()

        # 3. Tải tài nguyên bản đồ mini (Minimap Texture)
        self._load_minimap_atlas()
        self._load_vegetation_assets()

        # 4. Thiết lập Camera 3D
        # Vị trí quan sát ban đầu: Nhìn bao quát toàn bộ lục địa từ phía Nam
        self.cam_x = self.grid_cols * 0.5 * self.TILE_SIZE_3D
        self.cam_y = 82.0
        # Đứng trên phần đất phía Nam để khung mặc định không chỉ thấy mặt biển.
        self.cam_z = self.grid_rows * 0.86 * self.TILE_SIZE_3D
        self.yaw = 0.0          # 0: nhìn về hướng Bắc (-Z)
        self.pitch = -0.48      # Nghiêng nhìn xuống ~28 độ
        self.fov = 56.0
        self.speed = 45.0

        # Trạng thái chuột & tương tác
        self.mouse_drag = False
        self.last_mouse_pos = (0, 0)
        self.show_hud = True
        self.show_minimap = True
        self.current_preset_name = "Toàn cảnh lục địa Primeval Reach"

    def _load_world_grid(self):
        """Tải WorldData canonical từ gói nén duy nhất của pipeline."""
        world_data_path = os.path.join(root_dir, "debug_outputs", "primeval_world_data.npz")
        if not os.path.exists(world_data_path):
            from tools.generate_primeval_world import export_all
            export_all()

        world_data = np.load(world_data_path)
        self.elevation = np.array(world_data["elevation"], dtype=np.float32)
        self.biome_id = np.array(world_data["biome_id"], dtype=np.int32)
        self.river_mask = np.array(world_data["river_mask"], dtype=np.bool_)
        self.land_mask = np.array(world_data["land_mask"], dtype=np.bool_)
        self.grid_rows, self.grid_cols = self.elevation.shape
        self.grid_scale_x = self.grid_cols / 200.0
        self.grid_scale_z = self.grid_rows / 200.0

        ecology_keys = (
            "temperature", "moisture", "water_proximity", "canopy_cover",
            "shrub_cover", "ground_cover", "vegetation_density",
        )
        if all(key in world_data.files for key in ecology_keys):
            self.ecology = {key: np.array(world_data[key], dtype=np.float32) for key in ecology_keys}
        else:
            self.ecology = build_ecology_maps(
                self.elevation, self.biome_id, self.river_mask, self.land_mask
            )
        self.vegetation_instances = spawn_vegetation_instances(
            self.biome_id,
            self.land_mask,
            self.ecology,
            self.river_mask,
        )

        # Tính trước độ cao thực tế trong không gian 3D
        # Đất nổi (elevation >= 0.35) vươn lên từ mặt biển, biển phẳng ở y = WATER_Y
        self.world_heights = np.where(
            self.elevation < 0.35,
            0.03,
            (self.elevation - 0.33) * 1.35
        ) * self.HEIGHT_SCALE_3D

        # Tính trước bóng đổ địa hình 3D (Hillshading)
        gy, gx = np.gradient(self.world_heights)
        nx = -gx
        ny = np.ones_like(gx) * self.TILE_SIZE_3D
        nz = -gy
        norm = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
        nx /= norm
        ny /= norm
        nz /= norm

        # Hướng Mặt Trời Tây-Bắc
        lx, ly, lz = -0.50, 0.72, -0.48
        l_len = math.sqrt(lx * lx + ly * ly + lz * lz)
        lx, ly, lz = lx / l_len, ly / l_len, lz / l_len

        dot = nx * lx + ny * ly + nz * lz
        self.shading = 0.40 + 0.60 * np.clip(dot, 0.0, 1.0)

        # Tải kết cấu bề mặt thực từ bản đồ chuẩn
        tex_path = os.path.join(root_dir, "debug_outputs", "primeval_world_texture.png")
        if os.path.exists(tex_path):
            from PIL import Image
            import cv2
            tex_img = Image.open(tex_path).convert("RGB")
            self.terrain_texture = cv2.resize(np.array(tex_img), (self.grid_cols, self.grid_rows), interpolation=cv2.INTER_AREA)
        else:
            self.terrain_texture = None

    def _spawn_world_megafauna(self):
        """Phân bổ các đàn thú cổ đại trên các lục địa tương ứng với sinh cảnh."""
        # Danh sách các bầy thú trên bản đồ thế giới 200x200
        # (type, grid_c, grid_r)
        spawns = [
            # 1. Voi ma mút (Mammoths) ở Thảo nguyên mùa thu & Chân núi băng Tây-Bắc
            ("mammoth", 52, 45), ("mammoth", 56, 48), ("mammoth", 60, 42),
            ("mammoth", 135, 45), ("mammoth", 140, 50), ("mammoth", 145, 42),
            # 2. Bò rừng cổ đại (Ancient Bison) ở Bình nguyên trung tâm
            ("ancient_bison", 120, 95), ("ancient_bison", 125, 98), ("ancient_bison", 115, 105),
            ("ancient_bison", 130, 102), ("ancient_bison", 122, 110),
            # 3. Hươu sừng lớn (Giant Deer) ở bìa Rừng nguyên sinh
            ("giant_deer", 108, 118), ("giant_deer", 112, 122), ("giant_deer", 105, 125),
            ("giant_deer", 68, 62), ("giant_deer", 72, 65),
            # 4. Hổ răng kiếm (Sabertooth) săn mồi ven sông và vũng nước
            ("sabertooth", 128, 75), ("sabertooth", 132, 78), ("sabertooth", 85, 145),
            # 5. Gấu hang khổng lồ (Cave Bear) ở sườn núi đá
            ("cave_bear", 48, 38), ("cave_bear", 42, 125), ("cave_bear", 152, 60),
            # 6. Sói tiền sử (Dire Wolf)
            ("dire_wolf", 115, 82), ("dire_wolf", 118, 85), ("dire_wolf", 122, 80),
        ]

        self.world_beasts = []
        for beast_type, gc, gr in spawns:
            self.world_beasts.append({
                "type": beast_type,
                "x": gc * self.grid_scale_x * self.TILE_SIZE_3D,
                "z": gr * self.grid_scale_z * self.TILE_SIZE_3D,
                "vx": random.uniform(-1.2, 1.2),
                "vz": random.uniform(-1.2, 1.2),
                "state": "graze",
                "timer": random.uniform(2.0, 6.0),
                "heading": random.uniform(0, math.pi * 2),
            })

    def _load_minimap_atlas(self):
        """Tải bản đồ thu nhỏ cho góc màn hình."""
        atlas_path = os.path.join(root_dir, "debug_outputs", "primeval_world_atlas.png")
        if not os.path.exists(atlas_path):
            atlas_path = os.path.join(root_dir, "assets", "sprites", "world_atlas.png")

        self.minimap_surf = None
        if os.path.exists(atlas_path):
            try:
                raw_surf = pygame.image.load(atlas_path).convert()
                # Thu nhỏ về kích thước HUD 200 x 112
                self.minimap_surf = pygame.transform.smoothscale(raw_surf, (200, 112))
            except Exception:
                self.minimap_surf = None

    def _load_vegetation_assets(self):
        """Nạp đúng bộ cây/thực vật tiền sử trong assets/stone_age."""
        asset_root = os.path.join(root_dir, "assets", "stone_age")
        specs = {
            "tree_tundra": ("04_prehistoric_trees_and_wood/tree_tundra_spruce_birch_{:02d}.png", 10, 10.5),
            "tree_steppe": ("04_prehistoric_trees_and_wood/tree_steppe_oak_pine_{:02d}.png", 10, 10.0),
            "tree_forest": ("04_prehistoric_trees_and_wood/tree_primeval_fern_cycad_{:02d}.png", 10, 9.0),
            "tree_swamp": ("04_prehistoric_trees_and_wood/tree_swamp_mangrove_{:02d}.png", 2, 8.4),
            "berry_bush": ("05_forageable_flora_3stages/flora_berry_bush_stage_{:02d}.png", 9, 3.2),
            "reed": ("05_forageable_flora_3stages/flora_grain_fiber_reed_stage_{:02d}.png", 9, 3.1),
            "mushroom": ("05_forageable_flora_3stages/flora_mushroom_herb_stage_{:02d}.png", 9, 2.2),
        }
        self.vegetation_sprites = {}
        self.vegetation_sprite_heights = {}
        for kind, (pattern, count, world_height) in specs.items():
            sprites = []
            for index in range(1, count + 1):
                path = os.path.join(asset_root, pattern.format(index))
                if os.path.exists(path):
                    try:
                        sprites.append(pygame.image.load(path).convert_alpha())
                    except pygame.error:
                        pass
            if sprites:
                self.vegetation_sprites[kind] = sprites
                self.vegetation_sprite_heights[kind] = world_height
        self._vegetation_scale_cache = {}

    def _draw_3d_vegetation(self):
        """Vẽ các tầng cây/bụi/cỏ theo WorldData và khí hậu Paleolithic mát."""
        if not self.vegetation_instances:
            return

        s = self.TILE_SIZE_3D
        cx, cy, cz = self.cam_x, self.cam_y, self.cam_z
        f_x = math.sin(self.yaw) * math.cos(self.pitch)
        f_y = math.sin(self.pitch)
        f_z = -math.cos(self.yaw) * math.cos(self.pitch)
        forward = np.array([f_x, f_y, f_z], dtype=np.float32)
        up_hint = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        right = np.cross(forward, up_hint)
        right /= np.linalg.norm(right) + 1e-6
        up = np.cross(right, forward)
        fov_rad = math.radians(self.fov)
        f_scale = (self.width * 0.5) / math.tan(fov_rad * 0.5)
        half_w = self.width * 0.5
        half_h = self.height * 0.5
        grid_c = int(cx / s)
        grid_r = int(cz / s)
        view_radius = max(42, int(self.grid_rows * 0.34)) + 8
        draw_queue = []

        for plant in self.vegetation_instances:
            col, row = int(plant["col"]), int(plant["row"])
            if abs(col - grid_c) > view_radius or abs(row - grid_r) > view_radius:
                continue
            kind = str(plant["kind"])
            sprites = self.vegetation_sprites.get(kind)
            if not sprites:
                continue

            wx, wz = col * s, row * s
            wy = float(self.world_heights[row, col])
            dx, dy, dz = wx - cx, wy - cy, wz - cz
            depth = dx * forward[0] + dy * forward[1] + dz * forward[2]
            if depth <= 2.0 or depth > 260.0:
                continue

            screen_u = dx * right[0] + dy * right[1] + dz * right[2]
            screen_v_base = dx * up[0] + dy * up[1] + dz * up[2]
            height_world = self.vegetation_sprite_heights.get(kind, 3.0) * float(plant.get("scale", 1.0))
            top_dx, top_dy, top_dz = dx, dy + height_world, dz
            screen_v_top = top_dx * up[0] + top_dy * up[1] + top_dz * up[2]
            sx = half_w + (screen_u * f_scale / depth)
            sy_base = half_h - (screen_v_base * f_scale / depth)
            sy_top = half_h - (screen_v_top * f_scale / depth)
            pixel_h = int(max(4.0, min(260.0, abs(sy_base - sy_top))))
            if sx < -180 or sx > self.width + 180 or sy_base < -80 or sy_top > self.height + 100:
                continue

            variant = (col * 17 + row * 31) % len(sprites)
            cache_key = (kind, variant, pixel_h)
            scaled = self._vegetation_scale_cache.get(cache_key)
            if scaled is None:
                source = sprites[variant]
                pixel_w = max(3, int(source.get_width() * pixel_h / max(1, source.get_height())))
                scaled = pygame.transform.smoothscale(source, (pixel_w, pixel_h))
                self._vegetation_scale_cache[cache_key] = scaled
            draw_queue.append((depth, scaled, int(sx - scaled.get_width() * 0.5), int(sy_top)))

        for depth, sprite, x, y in sorted(draw_queue, key=lambda item: item[0], reverse=True):
            self.screen.blit(sprite, (x, y))

    # --------------------------------------------------------------------------
    # ĐIỀU KHIỂN & SỰ KIỆN (INPUT HANDLING)
    # --------------------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return
                elif event.key == pygame.K_m:
                    self.show_minimap = not self.show_minimap
                elif event.key in (pygame.K_F1, pygame.K_h):
                    self.show_hud = not self.show_hud

                # Phím nhảy nhanh đến các địa danh lớn
                elif event.key in self.CAMERA_PRESETS:
                    preset = self.CAMERA_PRESETS[event.key]
                    self.cam_x = preset["pos"][0] * self.grid_scale_x * self.TILE_SIZE_3D
                    self.cam_y = preset["pos"][1]
                    self.cam_z = preset["pos"][2] * self.grid_scale_z * self.TILE_SIZE_3D
                    self.yaw = preset["yaw"]
                    self.pitch = preset["pitch"]
                    self.current_preset_name = preset["name"]

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:  # Chuột phải
                    self.mouse_drag = True
                    self.last_mouse_pos = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3:
                    self.mouse_drag = False

            elif event.type == pygame.MOUSEMOTION:
                if self.mouse_drag:
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    self.last_mouse_pos = event.pos
                    self.yaw += dx * 0.005
                    self.pitch = max(-math.radians(82), min(math.radians(20), self.pitch - dy * 0.004))

    # --------------------------------------------------------------------------
    # CẬP NHẬT VẬT LÝ & ĐỘNG VẬT (UPDATE)
    # --------------------------------------------------------------------------
    def update(self, dt: float):
        self.game_time += dt

        # Đọc trạng thái bàn phím để di chuyển Camera
        keys = pygame.key.get_pressed()
        move_speed = self.speed * dt
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            move_speed *= 2.6  # Tăng tốc bay nhanh

        # Vector hướng nhìn
        forward_x = math.sin(self.yaw) * math.cos(self.pitch)
        forward_y = math.sin(self.pitch)
        forward_z = -math.cos(self.yaw) * math.cos(self.pitch)

        # Vector ngang (Right)
        right_x = math.cos(self.yaw)
        right_z = math.sin(self.yaw)

        # Di chuyển tiến/lùi (W/S)
        if keys[pygame.K_w]:
            self.cam_x += forward_x * move_speed
            self.cam_y += forward_y * move_speed
            self.cam_z += forward_z * move_speed
        if keys[pygame.K_s]:
            self.cam_x -= forward_x * move_speed
            self.cam_y -= forward_y * move_speed
            self.cam_z -= forward_z * move_speed

        # Di chuyển ngang (A/D)
        if keys[pygame.K_a]:
            self.cam_x -= right_x * move_speed
            self.cam_z -= right_z * move_speed
        if keys[pygame.K_d]:
            self.cam_x += right_x * move_speed
            self.cam_z += right_z * move_speed

        # Nâng hạ độ cao máy ảnh (Q/E)
        if keys[pygame.K_q]:
            self.cam_y += move_speed * 0.9
        if keys[pygame.K_e]:
            self.cam_y -= move_speed * 0.9

        # Xoay bằng phím mũi tên (hỗ trợ khi không dùng chuột)
        rot_speed = 1.4 * dt
        if keys[pygame.K_LEFT]:
            self.yaw -= rot_speed
        if keys[pygame.K_RIGHT]:
            self.yaw += rot_speed
        if keys[pygame.K_UP]:
            self.pitch = min(math.radians(20), self.pitch + rot_speed * 0.8)
        if keys[pygame.K_DOWN]:
            self.pitch = max(-math.radians(82), self.pitch - rot_speed * 0.8)

        # Giới hạn độ cao máy ảnh không chìm xuống dưới mặt nước
        world_max_x = self.grid_cols * self.TILE_SIZE_3D
        world_max_z = self.grid_rows * self.TILE_SIZE_3D
        self.cam_x = max(-50.0, min(world_max_x + 50.0, self.cam_x))
        self.cam_z = max(-50.0, min(world_max_z + 50.0, self.cam_z))
        self.cam_y = max(self.WATER_Y + 1.5, min(140.0, self.cam_y))

        # Cập nhật hành vi bầy thú hoang dã
        self._update_wildlife(dt)

    def _update_wildlife(self, dt: float):
        """Cập nhật vị trí và dáng đi của động vật trên bề mặt 3D."""
        world_max_x = (self.grid_cols - 2) * self.TILE_SIZE_3D
        world_max_z = (self.grid_rows - 2) * self.TILE_SIZE_3D

        for b in self.world_beasts:
            b["timer"] -= dt
            if b["timer"] <= 0:
                b["timer"] = random.uniform(3.0, 8.0)
                if random.random() < 0.65:
                    b["state"] = "wander"
                    angle = random.uniform(0, math.pi * 2)
                    spd = random.uniform(0.6, 1.8)
                    b["vx"] = math.cos(angle) * spd
                    b["vz"] = math.sin(angle) * spd
                else:
                    b["state"] = "graze"
                    b["vx"] = 0.0
                    b["vz"] = 0.0

            if b["state"] == "wander":
                b["x"] += b["vx"] * dt
                b["z"] += b["vz"] * dt
                b["x"] = max(5.0, min(world_max_x, b["x"]))
                b["z"] = max(5.0, min(world_max_z, b["z"]))

    def _get_terrain_height_at(self, wx: float, wz: float) -> float:
        """Lấy độ cao bề mặt 3D tại tọa độ thế giới (wx, wz)."""
        s = self.TILE_SIZE_3D
        half_w = self.grid_cols * 0.5 * s
        gc = (wx - half_w) / s + self.grid_cols * 0.5
        gr = wz / s
        c0 = max(0, min(self.grid_cols - 1, int(math.floor(gc))))
        r0 = max(0, min(self.grid_rows - 1, int(math.floor(gr))))
        return float(self.world_heights[r0, c0])

    # --------------------------------------------------------------------------
    # KẾT XUẤT 3D (RENDER PIPELINE)
    # --------------------------------------------------------------------------
    def render(self):
        # 1. Vẽ nền trời gradient (Sky dome)
        self._draw_sky_gradient()

        # 2. Chiếu & Vẽ địa hình 3D (Terrain Mesh Quads)
        self._draw_3d_terrain()

        # 3. Vẽ thảm thực vật canonical theo các tầng sinh thái
        self._draw_3d_vegetation()

        # 4. Vẽ động vật cổ đại (Beast Billboards/Cubes)
        self._draw_3d_wildlife()

        # 5. Giao diện HUD & Bản đồ mini
        if self.show_hud:
            self._draw_hud()

        if not self.headless:
            pygame.display.flip()

    def _draw_sky_gradient(self):
        """Vẽ bầu trời tiền sử chuyển màu tự nhiên."""
        sky_top = (16, 28, 48)
        sky_horizon = (64, 88, 118)
        h = self.height
        step = 4
        for y in range(0, h, step):
            t = y / float(h)
            r = int(sky_top[0] * (1.0 - t) + sky_horizon[0] * t)
            g = int(sky_top[1] * (1.0 - t) + sky_horizon[1] * t)
            b = int(sky_top[2] * (1.0 - t) + sky_horizon[2] * t)
            pygame.draw.rect(self.screen, (r, g, b), (0, y, self.width, step))

    def _draw_3d_terrain(self):
        """
        Chiếu phối cảnh và kết xuất lưới địa hình 3D.
        Tối ưu hóa: Giới hạn tầm nhìn quanh vị trí máy ảnh (Frustum/Range culling).
        """
        s = self.TILE_SIZE_3D
        cx, cy, cz = self.cam_x, self.cam_y, self.cam_z

        # Tính toán Camera Basis
        f_x = math.sin(self.yaw) * math.cos(self.pitch)
        f_y = math.sin(self.pitch)
        f_z = -math.cos(self.yaw) * math.cos(self.pitch)
        forward = np.array([f_x, f_y, f_z], dtype=np.float32)

        up_hint = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        right = np.cross(forward, up_hint)
        r_norm = np.linalg.norm(right)
        if r_norm < 1e-6:
            right = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        else:
            right /= r_norm
        up = np.cross(right, forward)

        # Tiêu cự Perspective
        fov_rad = math.radians(self.fov)
        f_scale = (self.width * 0.5) / math.tan(fov_rad * 0.5)
        half_w = self.width * 0.5
        half_h = self.height * 0.5

        # Xác định phạm vi ô lưới hiển thị; tăng nhẹ theo lưới canonical mới.
        center_c = int(cx / s)
        center_r = int(cz / s)
        view_radius = max(42, int(self.grid_rows * 0.34))

        c_min = max(0, center_c - view_radius)
        c_max = min(self.grid_cols - 1, center_c + view_radius)
        r_min = max(0, center_r - view_radius)
        r_max = min(self.grid_rows - 1, center_r + view_radius)

        if c_max <= c_min or r_max <= r_min:
            return

        c_range = np.arange(c_min, c_max + 1)
        r_range = np.arange(r_min, r_max + 1)
        C_grid, R_grid = np.meshgrid(c_range, r_range)

        # WorldData đã giữ tỉ lệ vùng bản đồ canonical; hai trục dùng cùng đơn vị.
        aspect_ratio = 1.0
        half_w = self.grid_cols * 0.5 * s
        X_world = (C_grid.astype(np.float32) * s - half_w) * aspect_ratio + half_w
        Z_world = R_grid.astype(np.float32) * s
        Y_world = self.world_heights[r_min:r_max + 1, c_min:c_max + 1]

        # Chuyển đổi sang Camera Space
        dx = X_world - cx
        dy = Y_world - cy
        dz = Z_world - cz

        cam_x = dx * right[0] + dy * right[1] + dz * right[2]
        cam_y = dx * up[0] + dy * up[1] + dz * up[2]
        cam_z = dx * forward[0] + dy * forward[1] + dz * forward[2]

        # Tọa độ màn hình 2D
        safe_z = np.where(cam_z > 1.2, cam_z, 1.2)
        screen_x = half_w + (cam_x * f_scale / safe_z)
        screen_y = half_h - (cam_y * f_scale / safe_z)

        # Thu thập các ô quads để sắp xếp theo chiều sâu
        sub_rows = len(r_range)
        sub_cols = len(c_range)
        quads = []

        sub_biomes = self.biome_id[r_min:r_max, c_min:c_max]
        sub_shading = self.shading[r_min:r_max, c_min:c_max]

        # Hiệu ứng gợn sóng nước
        wave_shimmer = math.sin(self.game_time * 2.5) * 0.05

        for r in range(sub_rows - 1):
            for c in range(sub_cols - 1):
                z0 = cam_z[r, c]
                z1 = cam_z[r, c + 1]
                z2 = cam_z[r + 1, c + 1]
                z3 = cam_z[r + 1, c]

                # Bỏ qua nếu toàn bộ ô ở sau máy ảnh
                if z0 <= 1.5 and z1 <= 1.5 and z2 <= 1.5 and z3 <= 1.5:
                    continue

                avg_depth = (z0 + z1 + z2 + z3) * 0.25
                if avg_depth > 260.0:
                    continue

                # Tọa độ 4 đỉnh trên màn hình
                p0 = (float(screen_x[r, c]), float(screen_y[r, c]))
                p1 = (float(screen_x[r, c + 1]), float(screen_y[r, c + 1]))
                p2 = (float(screen_x[r + 1, c + 1]), float(screen_y[r + 1, c + 1]))
                p3 = (float(screen_x[r + 1, c]), float(screen_y[r + 1, c]))

                # Kiểm tra thô Frustum (nằm ngoài màn hình quá xa)
                min_px = min(p0[0], p1[0], p2[0], p3[0])
                max_px = max(p0[0], p1[0], p2[0], p3[0])
                min_py = min(p0[1], p1[1], p2[1], p3[1])
                max_py = max(p0[1], p1[1], p2[1], p3[1])

                if max_px < -60 or min_px > self.width + 60 or max_py < -60 or min_py > self.height + 60:
                    continue

                if self.terrain_texture is not None:
                    tex_c = sub_cols - 1
                    base_col = self.terrain_texture[r_min + r, c_min + c]
                else:
                    b_id = int(sub_biomes[r, c])
                    base_col = BIOME_COLORS.get(b_id, (50, 80, 50))

                # Sương mù khí quyển xa (Distance Fog)
                fog = np.clip((avg_depth - 45.0) / 220.0, 0.0, 0.65)
                fog_col = (64, 88, 118)

                r_col = int(base_col[0] * (1.0 - fog) + fog_col[0] * fog)
                g_col = int(base_col[1] * (1.0 - fog) + fog_col[1] * fog)
                b_col = int(base_col[2] * (1.0 - fog) + fog_col[2] * fog)

                quads.append((avg_depth, [p0, p1, p2, p3], (r_col, g_col, b_col)))

        # Sắp xếp từ xa đến gần (Painter's Algorithm)
        quads.sort(key=lambda q: q[0], reverse=True)

        for _, pts, col in quads:
            pygame.draw.polygon(self.screen, col, pts)

    def _draw_3d_wildlife(self):
        """Vẽ các bầy thú tiền sử dưới dạng mô hình 3D thu nhỏ trên bề mặt đất."""
        cx, cy, cz = self.cam_x, self.cam_y, self.cam_z
        f_x = math.sin(self.yaw) * math.cos(self.pitch)
        f_y = math.sin(self.pitch)
        f_z = -math.cos(self.yaw) * math.cos(self.pitch)
        forward = np.array([f_x, f_y, f_z], dtype=np.float32)

        up_hint = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        right = np.cross(forward, up_hint)
        r_norm = np.linalg.norm(right)
        right = right / (r_norm + 1e-6)
        up = np.cross(right, forward)

        fov_rad = math.radians(self.fov)
        f_scale = (self.width * 0.5) / math.tan(fov_rad * 0.5)
        half_w = self.width * 0.5
        half_h = self.height * 0.5

        for beast in self.world_beasts:
            bx, bz = beast["x"], beast["z"]
            by = self._get_terrain_height_at(bx, bz)

            # Chỉ vẽ thú khi chúng ở trên mặt đất
            if by < self.WATER_Y - 0.2:
                continue

            dx = bx - cx
            dy = by - cy
            dz = bz - cz

            cam_depth = dx * forward[0] + dy * forward[1] + dz * forward[2]
            if cam_depth <= 2.0 or cam_depth > 180.0:
                continue

            cam_u = dx * right[0] + dy * right[1] + dz * right[2]
            cam_v = dx * up[0] + dy * up[1] + dz * up[2]

            sx = half_w + (cam_u * f_scale / cam_depth)
            sy = half_h - (cam_v * f_scale / cam_depth)

            if sx < -30 or sx > self.width + 30 or sy < -30 or sy > self.height + 30:
                continue

            b_type = beast["type"]
            base_color = BEAST_COLORS.get(b_type, (90, 60, 40))

            # Kích thước theo loài và khoảng cách
            size_map = {"mammoth": 3.6, "ancient_bison": 2.4, "cave_bear": 2.2, "sabertooth": 1.9, "giant_deer": 2.1, "dire_wolf": 1.6}
            scale = size_map.get(b_type, 1.8)
            screen_size = max(3.0, (scale * f_scale / cam_depth))

            w = screen_size
            h = screen_size * 0.75
            body_rect = pygame.Rect(int(sx - w * 0.5), int(sy - h), int(w), int(h))

            # Vẽ bóng đổ dưới đất
            shadow_rect = pygame.Rect(int(sx - w * 0.55), int(sy - h * 0.2), int(w * 1.1), int(h * 0.35))
            pygame.draw.ellipse(self.screen, (10, 15, 20), shadow_rect)

            # Vẽ thân thú (Thân + Đầu)
            pygame.draw.rect(self.screen, base_color, body_rect, border_radius=2)
            head_rect = pygame.Rect(int(sx + w * 0.15), int(sy - h * 1.15), int(w * 0.45), int(h * 0.55))
            pygame.draw.rect(self.screen, tuple(min(255, int(c * 1.15)) for c in base_color), head_rect, border_radius=2)

            # Voi ma mút: Thêm ngà cong trắng ngà đặc trưng
            if b_type == "mammoth" and screen_size > 8.0:
                tusk_end = (int(sx + w * 0.75), int(sy - h * 0.95))
                pygame.draw.line(self.screen, (240, 235, 215), (int(sx + w * 0.45), int(sy - h * 0.8)), tusk_end, 2)

    # --------------------------------------------------------------------------
    # GIAO DIỆN HUD & BẢN ĐỒ THU NHỎ (OVERLAY)
    # --------------------------------------------------------------------------
    def _draw_hud(self):
        """Vẽ bảng thông tin đo đạc trắc địa, tọa độ máy ảnh và bản đồ thu nhỏ."""
        # Tọa độ lưới hiện tại dưới chân máy ảnh
        grid_c = max(0, min(self.grid_cols - 1, int(self.cam_x / self.TILE_SIZE_3D)))
        grid_r = max(0, min(self.grid_rows - 1, int(self.cam_z / self.TILE_SIZE_3D)))
        current_biome_id = int(self.biome_id[grid_r, grid_c])
        biome_name = BIOME_NAMES.get(current_biome_id, "Vùng chưa thám hiểm")
        current_elev = float(self.world_heights[grid_r, grid_c])

        # Hộp thông tin trên cùng bên trái
        hud_bg = pygame.Surface((380, 115), pygame.SRCALPHA)
        hud_bg.fill((12, 16, 24, 210))
        self.screen.blit(hud_bg, (14, 14))
        pygame.draw.rect(self.screen, (60, 95, 130), (14, 14, 380, 115), width=1)

        title_surf = self.font_bold.render("STONE AGE 3D: PRIMEVAL REACH", True, (240, 215, 140))
        self.screen.blit(title_surf, (24, 20))

        fps = self.clock.get_fps()
        telemetry = f"FPS: {fps:.0f} | Máy ảnh: X={self.cam_x/self.TILE_SIZE_3D:.1f}, Y={self.cam_y:.1f}, Z={self.cam_z/self.TILE_SIZE_3D:.1f}"
        self.screen.blit(self.font_small.render(telemetry, True, (200, 220, 240)), (24, 44))

        biome_str = f"Quần xã: {biome_name} | Cao độ: {current_elev:.1f}m"
        self.screen.blit(self.font_small.render(biome_str, True, (160, 225, 175)), (24, 66))

        preset_str = f"Địa danh: {self.current_preset_name}"
        self.screen.blit(self.font_small.render(preset_str, True, (235, 185, 130)), (24, 88))

        # Bản đồ thu nhỏ ở góc dưới bên phải
        if self.show_minimap and self.minimap_surf:
            mm_w, mm_h = self.minimap_surf.get_size()
            mm_x = self.width - mm_w - 18
            mm_y = self.height - mm_h - 42

            # Khung bản đồ thu nhỏ
            self.screen.blit(self.minimap_surf, (mm_x, mm_y))
            pygame.draw.rect(self.screen, (180, 160, 120), (mm_x - 1, mm_y - 1, mm_w + 2, mm_h + 2), width=2)

            # Chấm định vị vị trí máy ảnh và hình nón tầm nhìn
            norm_cx = (self.cam_x / (self.grid_cols * self.TILE_SIZE_3D))
            norm_cz = (self.cam_z / (self.grid_rows * self.TILE_SIZE_3D))
            pin_x = int(mm_x + np.clip(norm_cx, 0.0, 1.0) * mm_w)
            pin_y = int(mm_y + np.clip(norm_cz, 0.0, 1.0) * mm_h)

            # Vẽ tia hướng nhìn
            cone_len = 14
            cone_lx = pin_x + int(math.sin(self.yaw - 0.35) * cone_len)
            cone_ly = pin_y - int(math.cos(self.yaw - 0.35) * cone_len)
            cone_rx = pin_x + int(math.sin(self.yaw + 0.35) * cone_len)
            cone_ry = pin_y - int(math.cos(self.yaw + 0.35) * cone_len)
            pygame.draw.line(self.screen, (255, 230, 80), (pin_x, pin_y), (cone_lx, cone_ly), 1)
            pygame.draw.line(self.screen, (255, 230, 80), (pin_x, pin_y), (cone_rx, cone_ry), 1)
            pygame.draw.circle(self.screen, (255, 60, 40), (pin_x, pin_y), 4)

        # Thanh hướng dẫn điều khiển dưới đáy
        bar_bg = pygame.Surface((self.width, 28), pygame.SRCALPHA)
        bar_bg.fill((8, 12, 18, 220))
        self.screen.blit(bar_bg, (0, self.height - 28))
        help_text = "WASD di chuyển | Q/E lên xuống | Chuột phải/Mũi tên xoay | Shift bay nhanh | 1-4 Nhảy địa danh | M Bản đồ | ESC thoát"
        self.screen.blit(self.font_small.render(help_text, True, (210, 225, 240)), (18, self.height - 22))

    # --------------------------------------------------------------------------
    # VÒNG LẶP CHÍNH (MAIN LOOP)
    # --------------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(0.1, dt)
            self.handle_events()
            self.update(dt)
            self.render()
        pygame.quit()


if __name__ == "__main__":
    game = Game3D()
    game.run()
