#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bộ xử lý & Sinh dữ liệu bản đồ thế giới Primeval Reach (GCVL).

Nguồn dữ liệu chuẩn (Single Source of Truth) là bản đồ tham chiếu canonical.
Lưới thế giới chính giữ gần đúng tỉ lệ vùng bản đồ gốc, còn JSON 200x200 chỉ
được giữ lại như một gói tương thích cho các công cụ cũ.
"""

import json
import math
import os
import shutil
import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.world.canonical_ecology import build_ecology_maps


CANONICAL_IMG_PATH = PROJECT_ROOT / "assets" / "sprites" / "primeval_reach_canonical_atlas.png"
CANONICAL_GRID_SIZE = (400, 218)  # Giữ tỉ lệ vùng bản đồ gốc ~982:536.
LEGACY_GRID_SIZE = (200, 200)
WORLD_DATA_PATH = PROJECT_ROOT / "debug_outputs" / "primeval_world_data.npz"
WORLD_MANIFEST_PATH = PROJECT_ROOT / "debug_outputs" / "primeval_world_manifest.json"


def load_canonical_atlas():
    """Tải ảnh bản đồ thế giới chuẩn."""
    if CANONICAL_IMG_PATH.exists():
        return Image.open(CANONICAL_IMG_PATH)
    raise FileNotFoundError(
        "Không tìm thấy bản đồ canonical tại "
        f"{CANONICAL_IMG_PATH}. Hãy đặt ảnh chuẩn vào đúng đường dẫn trước khi build."
    )


def extract_world_data(target_size=CANONICAL_GRID_SIZE):
    """
    Trích xuất bản đồ độ cao (Elevation), quần xã (Biomes), sông hồ (Rivers)
    và bản đồ bề mặt (Texture) trực tiếp từ bản đồ tham chiếu.
    """
    img = load_canonical_atlas()
    full_arr = np.array(img.convert("RGB"))

    # Tọa độ khung nội dung bản đồ bên trong viền giấy cổ
    # Bờ viền đen: y trong khoảng 18..554, x trong khoảng 21..1003
    y0, y1 = 18, 554
    x0, x1 = 21, 1003
    inner_texture = full_arr[y0:y1, x0:x1]
    h, w, _ = inner_texture.shape

    r = inner_texture[..., 0].astype(np.float32)
    g = inner_texture[..., 1].astype(np.float32)
    b = inner_texture[..., 2].astype(np.float32)
    brightness = (r + g + b) / 3.0
    saturation = np.max(inner_texture, axis=-1) - np.min(inner_texture, axis=-1)

    # 1. Phân tách Vùng nước (Đại dương sâu, San hô, Sông ngòi & Hồ)
    is_deep_ocean = (b > r + 30) & (b > 60) & (g < 110) & (r < 50)
    is_reef = (g > 130) & (b > 150) & (r < 90)
    is_river = (b > r + 15) & (b > 75) & (r < 105) & (~is_deep_ocean) & (~is_reef)
    is_water = is_deep_ocean | is_reef | is_river
    is_land = ~is_water

    # 2. Xây dựng bản đồ độ cao thực tế (Elevation [0.0 .. 1.25])
    # Khoảng cách từ bờ biển vào đất liền (Distance transform)
    dist_land = cv2.distanceTransform(is_land.astype(np.uint8), cv2.DIST_L2, 5)
    dist_norm = np.clip(dist_land / 38.0, 0.0, 1.0)

    yy, xx = np.mgrid[0:h, 0:w]

    # Đỉnh núi tuyết băng giá Tây-Bắc (Glacial Alpine Massif)
    is_nw_alpine = is_land & (xx < 440) & (yy < 250) & (r > 150) & (g > 150) & (b > 150)
    alpine_relief = cv2.GaussianBlur(is_nw_alpine.astype(np.float32), (31, 31), 0) * 0.75

    # Vành đai miệng núi đá Sa mạc Tây-Nam (Terracotta Crater Rim)
    is_sw_crater = is_land & (xx < 450) & (yy > 230) & (r > 120) & (g > 90) & (b < 120)
    sw_relief = cv2.GaussianBlur(is_sw_crater.astype(np.float32), (31, 31), 0) * 0.45

    # Cao nguyên Thảo nguyên Mùa thu Đông-Bắc (Autumn Steppes Plateau)
    is_autumn_plat = is_land & (xx > 500) & (yy < 280) & (r > 140) & (g > 90)
    autumn_relief = cv2.GaussianBlur(is_autumn_plat.astype(np.float32), (31, 31), 0) * 0.35

    # Sống núi Rừng nguyên sinh ôm Vịnh Trăng Khuyết
    is_crescent_ridge = is_land & (xx > 480) & (yy > 220) & (yy < 450) & (g > 60) & (b < 75)
    crescent_relief = cv2.GaussianBlur(is_crescent_ridge.astype(np.float32), (25, 25), 0) * 0.25

    # Tổng hợp độ cao
    elev = np.zeros((h, w), dtype=np.float32)
    # Mặt đất nổi bắt đầu từ 0.35 và vươn lên
    elev[is_land] = (
        0.35
        + dist_norm[is_land] * 0.22
        + alpine_relief[is_land]
        + sw_relief[is_land]
        + autumn_relief[is_land]
        + crescent_relief[is_land]
    )
    # Lòng sông và hồ hạ thấp về mực nước
    elev[is_river] = 0.34
    # Biển sâu phẳng ở 0.0
    elev[is_deep_ocean | is_reef] = 0.0

    # 3. Phân loại 8 Quần xã chuẩn (Biomes 0..7)
    biome_map = np.zeros((h, w), dtype=np.uint8)
    biome_map[is_deep_ocean] = 0     # 0: Đại dương sâu
    biome_map[is_reef] = 1           # 1: Vành đai san hô
    biome_map[is_river] = 2          # 2: Sông ngòi & Hồ

    # Đất liền
    # 6: Dãy núi tuyết băng giá
    is_snow = is_land & (brightness > 165) & (saturation < 45) & (xx < 460) & (yy < 260)
    biome_map[is_snow] = 6

    # 5: Hoang mạc cát đỏ Tây-Nam
    is_terracotta = is_land & (r > 130) & (r > g + 20) & (b < 140) & (yy > 220) & (xx < 460)
    biome_map[is_terracotta] = 5

    # 4: Thảo nguyên mùa thu Đông-Bắc
    is_autumn = is_land & (r > 140) & (g > 90) & (b < 120) & (yy < 280) & (xx > 500)
    biome_map[is_autumn] = 4

    # 7: Quần đảo bảo tồn Đông-Nam
    is_sanctuary = is_land & (yy > 370) & (xx > 800)
    biome_map[is_sanctuary] = 7

    # 3: Thung lũng rừng nguyên sinh (phần đất còn lại)
    is_forest = is_land & (biome_map == 0)
    biome_map[is_forest] = 3

    # 4. Giảm mẫu về lưới mục tiêu nhưng giữ nguyên tỉ lệ vùng bản đồ.
    tw, th = target_size
    elev_grid = cv2.resize(elev, (tw, th), interpolation=cv2.INTER_AREA)
    biome_grid = cv2.resize(biome_map, (tw, th), interpolation=cv2.INTER_NEAREST)
    river_grid = cv2.resize(is_river.astype(np.uint8), (tw, th), interpolation=cv2.INTER_NEAREST)
    texture_grid = cv2.resize(inner_texture, (tw, th), interpolation=cv2.INTER_AREA)

    return {
        "full_img": img,
        "inner_texture": inner_texture,
        "elevation_full": elev,
        "biome_full": biome_map,
        "elevation_grid": elev_grid,
        "biome_grid": biome_grid,
        "river_grid": river_grid,
        "land_grid": cv2.resize(is_land.astype(np.uint8), (tw, th), interpolation=cv2.INTER_NEAREST),
        "texture_grid": texture_grid,
    }


def export_all():
    """Xuất toàn bộ tệp dữ liệu, hình ảnh và tài nguyên chuẩn."""
    print("[GCVL] Đang trích xuất dữ liệu bản đồ từ ảnh chuẩn...")
    data = extract_world_data(target_size=CANONICAL_GRID_SIZE)

    debug_dir = PROJECT_ROOT / "debug_outputs"
    debug_dir.mkdir(parents=True, exist_ok=True)
    sprites_dir = PROJECT_ROOT / "assets" / "sprites"
    sprites_dir.mkdir(parents=True, exist_ok=True)

    # 1. Lưu bản đồ đầy đủ chuẩn (có viền)
    atlas_dest = debug_dir / "primeval_world_atlas.png"
    data["full_img"].save(atlas_dest, "PNG")
    print(f"[GCVL] Đã lưu bản đồ chuẩn tại: {atlas_dest}")

    # Đồng bộ sang các tài nguyên game
    for target in [sprites_dir / "world_atlas.png", sprites_dir / "world_overview_macro.png"]:
        shutil.copy(atlas_dest, target)
        print(f"[GCVL] Đã đồng bộ sang: {target}")

    # 2. Lưu kết cấu mặt đất 3D (Inner Texture)
    tex_path = debug_dir / "primeval_world_texture.png"
    Image.fromarray(data["inner_texture"]).save(tex_path, "PNG")
    print(f"[GCVL] Đã lưu kết cấu 3D tại: {tex_path}")

    # 3. Lưu ảnh bản đồ độ cao cùng kích thước với WorldData canonical.
    h_norm = np.clip(data["elevation_grid"] / 1.30 * 255.0, 0, 255).astype(np.uint8)
    h_path = debug_dir / "primeval_world_heightmap.png"
    Image.fromarray(h_norm).save(h_path, "PNG")
    print(f"[GCVL] Đã lưu bản đồ độ cao tại: {h_path}")

    # 4. WorldData binary canonical: một gói dữ liệu duy nhất cho runtime/renderer.
    biome_legend = {
        0: "deep_ocean",
        1: "coastal_reef_halo",
        2: "meandering_river",
        3: "primeval_forest_valley",
        4: "autumn_steppes_plateau",
        5: "terracotta_dunes",
        6: "glacial_alpine_massif",
        7: "sanctuary_island",
    }

    ecology = build_ecology_maps(
        data["elevation_grid"],
        data["biome_grid"],
        data["river_grid"],
        data["land_grid"],
    )

    # 4a. Ảnh kiểm định các lớp sinh thái, dùng để tuning mà không đụng silhouette.
    vegetation_path = debug_dir / "primeval_world_vegetation_density.png"
    vegetation_img = np.clip(ecology["vegetation_density"] * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(vegetation_img).save(vegetation_path, "PNG")
    temperature_path = debug_dir / "primeval_world_temperature.png"
    temperature_img = np.clip(ecology["temperature"] * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(temperature_img).save(temperature_path, "PNG")
    print(f"[GCVL] Đã lưu bản đồ mật độ thực vật tại: {vegetation_path}")
    print(f"[GCVL] Đã lưu bản đồ nhiệt độ tương đối tại: {temperature_path}")

    # 4b. WorldData binary canonical: một gói dữ liệu duy nhất cho runtime/renderer.
    np.savez_compressed(
        WORLD_DATA_PATH,
        elevation=data["elevation_grid"].astype(np.float32),
        biome_id=data["biome_grid"].astype(np.uint8),
        river_mask=data["river_grid"].astype(np.uint8),
        land_mask=data["land_grid"].astype(np.uint8),
        temperature=ecology["temperature"].astype(np.float32),
        moisture=ecology["moisture"].astype(np.float32),
        water_proximity=ecology["water_proximity"].astype(np.float32),
        canopy_cover=ecology["canopy_cover"].astype(np.float32),
        shrub_cover=ecology["shrub_cover"].astype(np.float32),
        ground_cover=ecology["ground_cover"].astype(np.float32),
        vegetation_density=ecology["vegetation_density"].astype(np.float32),
    )
    manifest = {
        "world_name": "Primeval Reach - Canonical Multi-Continent Archipelago",
        "source_atlas": str(CANONICAL_IMG_PATH.relative_to(PROJECT_ROOT)),
        "source_size": [int(data["full_img"].width), int(data["full_img"].height)],
        "inner_bounds_xyxy": [21, 18, 1003, 554],
        "grid_size": [CANONICAL_GRID_SIZE[0], CANONICAL_GRID_SIZE[1]],
        "axis": {"x": "west_to_east", "z": "north_to_south"},
        "elevation_range": [0.0, 1.30],
        "sea_level": 0.35,
        "climate_baseline": "cool_late_paleolithic_relative_temperature",
        "vegetation_layers": ["canopy", "shrub", "ground"],
        "biome_legend": biome_legend,
        "data_file": WORLD_DATA_PATH.name,
    }
    with open(WORLD_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[GCVL] Đã xuất WorldData canonical tại: {WORLD_DATA_PATH}")

    # 5. Xuất JSON 200x200 tương thích ngược, không còn là nguồn chuẩn.
    legacy_elev = cv2.resize(data["elevation_grid"], LEGACY_GRID_SIZE, interpolation=cv2.INTER_AREA)
    legacy_biome = cv2.resize(data["biome_grid"], LEGACY_GRID_SIZE, interpolation=cv2.INTER_NEAREST)
    legacy_river = cv2.resize(data["river_grid"], LEGACY_GRID_SIZE, interpolation=cv2.INTER_NEAREST)

    payload = {
        "world_name": "Primeval Reach - Canonical Multi-Continent Archipelago",
        "grid_size": [LEGACY_GRID_SIZE[0], LEGACY_GRID_SIZE[1]],
        "source": "debug_outputs/primeval_world_data.npz",
        "compatibility_only": True,
        "biome_legend": biome_legend,
        "elevation": np.round(legacy_elev, 4).tolist(),
        "biome_id": legacy_biome.tolist(),
        "river_mask": legacy_river.tolist(),
    }

    json_path = PROJECT_ROOT / "stone_age_world_200x200.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"[GCVL] Đã xuất tệp tương thích 200x200 tại: {json_path}")


if __name__ == "__main__":
    export_all()
