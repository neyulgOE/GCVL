#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Công cụ kết xuất phối cảnh 3D và xuất mô hình 3D (Wavefront OBJ/MTL)
cho bản đồ thế giới đa lục địa Primeval Reach (GCVL).

- Kết xuất 4 góc nhìn phối cảnh 3D độ phân giải cao: debug_outputs/primeval_world_3d_preview.png
- Xuất tệp mô hình 3D chuẩn: debug_outputs/primeval_world.obj & debug_outputs/primeval_world.mtl
"""

import json
import math
import os
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont


# Bảng màu chuẩn cho 8 quần xã Primeval Reach
BIOME_COLORS = {
    0: (11, 44, 76),       # 0: Đại dương sâu (Deep Ocean)
    1: (28, 182, 196),     # 1: Vành đai san hô ngọc lam (Coastal Reef Halo)
    2: (42, 118, 158),     # 2: Sông ngòi & Hồ nội địa (Meandering River & Lake)
    3: (42, 94, 46),       # 3: Thung lũng rừng nguyên sinh (Primeval Forest Valley)
    4: (204, 134, 48),     # 4: Cao nguyên thảo nguyên mùa thu (Autumn Steppes Plateau)
    5: (212, 114, 68),     # 5: Hoang mạc cát đỏ đồi đá (Terracotta Dunes & Crater)
    6: (240, 245, 250),    # 6: Dãy núi tuyết băng giá (Glacial Alpine Massif)
    7: (34, 102, 54),      # 7: Quần đảo thiêng bảo tồn (Sanctuary Archipelago)
}

BIOME_NAMES = {
    0: "Deep Ocean",
    1: "Coastal Reef Halo",
    2: "River & Lake System",
    3: "Primeval Forest Valley",
    4: "Autumn Steppes Plateau",
    5: "Terracotta Basin & Dunes",
    6: "Glacial Alpine Massif",
    7: "Sanctuary Archipelago",
}


def load_world_data(json_path: str = "stone_age_world_200x200.json"):
    """Tải dữ liệu lưới thế giới 200x200."""
    if not os.path.exists(json_path):
        from tools.generate_primeval_world import generate_primeval_world
        print(f"[3D] Không tìm thấy {json_path}, đang tự động sinh...")
        generate_primeval_world()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    elevation = np.array(data["elevation"], dtype=np.float32)
    biome_id = np.array(data["biome_id"], dtype=np.int32)
    river_mask = np.array(data["river_mask"], dtype=np.bool_)
    return elevation, biome_id, river_mask


# ==============================================================================
# 1. BỘ TÍNH TOÁN BÓNG ĐỔ ĐỊA HÌNH 3D (LAMBERTIAN HILLSHADING)
# ==============================================================================
def compute_normals_and_shading(elevation: np.ndarray, light_dir=( -0.45, 0.75, -0.48 ), height_scale=22.0):
    rows, cols = elevation.shape
    scaled_h = elevation * height_scale

    # Tính gradient dH/dx và dH/dy
    gy, gx = np.gradient(scaled_h)

    # Pháp tuyến bề mặt N = (-gx, 1.0, -gy)
    nx = -gx
    ny = np.ones_like(gx)
    nz = -gy

    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx /= norm
    ny /= norm
    nz /= norm

    # Vector ánh sáng chuẩn hóa
    lx, ly, lz = light_dir
    l_len = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / l_len, ly / l_len, lz / l_len

    # Tích vô hướng N . L
    dot = nx * lx + ny * ly + nz * lz
    ambient = 0.38
    diffuse = 0.62 * np.clip(dot, 0.0, 1.0)
    shading = ambient + diffuse
    return nx, ny, nz, shading


# ==============================================================================
# 2. BỘ KẾT XUẤT PHỐI CẢNH 3D (PERSPECTIVE 3D RENDERER)
# ==============================================================================
def render_3d_view(
    elevation: np.ndarray,
    biome_id: np.ndarray,
    shading: np.ndarray,
    cam_pos=(100.0, 75.0, 240.0),
    look_at=(100.0, 10.0, 100.0),
    fov_deg=55.0,
    out_width=800,
    out_height=500,
    grid_stride=1,
    height_scale=24.0,
    subsample_range=None,
    sky_gradient=((16, 28, 48), (70, 95, 125)),
):
    """
    Kết xuất phối cảnh 3D góc nhìn máy ảnh tùy biến trên lưới địa hình.
    """
    rows, cols = elevation.shape
    r_start, r_end = 0, rows
    c_start, c_end = 0, cols
    if subsample_range is not None:
        r_start, r_end, c_start, c_end = subsample_range

    r_idx = np.arange(r_start, r_end, grid_stride)
    c_idx = np.arange(c_start, c_end, grid_stride)
    sub_elev = elevation[np.ix_(r_idx, c_idx)]
    sub_biome = biome_id[np.ix_(r_idx, c_idx)]
    sub_shade = shading[np.ix_(r_idx, c_idx)]

    sub_rows, sub_cols = sub_elev.shape

    # Tọa độ thế giới X, Y, Z
    C_grid, R_grid = np.meshgrid(c_idx, r_idx)
    X_world = C_grid.astype(np.float32)
    Z_world = R_grid.astype(np.float32)
    # Nâng độ cao cho đất nổi mượt mà từ bờ biển, mặt nước phẳng ở đáy
    Y_world = np.where(sub_elev < 0.35, 0.03, (sub_elev - 0.33) * 1.35) * height_scale

    # Tính hệ tọa độ máy ảnh (Camera Basis)
    cx, cy, cz = cam_pos
    lx, ly, lz = look_at
    forward = np.array([lx - cx, ly - cy, lz - cz], dtype=np.float32)
    f_len = np.linalg.norm(forward)
    forward /= (f_len + 1e-8)

    up_hint = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    right = np.cross(forward, up_hint)
    r_len = np.linalg.norm(right)
    if r_len < 1e-6:
        right = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    else:
        right /= r_len
    up = np.cross(right, forward)

    # Chuyển đổi đỉnh sang Camera Space
    dx = X_world - cx
    dy = Y_world - cy
    dz = Z_world - cz

    cam_x = dx * right[0] + dy * right[1] + dz * right[2]
    cam_y = dx * up[0] + dy * up[1] + dz * up[2]
    cam_z = dx * forward[0] + dy * forward[1] + dz * forward[2]

    # Chiếu phối cảnh Perspective
    fov_rad = math.radians(fov_deg)
    f_scale = (out_width * 0.5) / math.tan(fov_rad * 0.5)

    valid_mask = cam_z > 2.0
    safe_z = np.where(valid_mask, cam_z, 2.0)

    screen_x = out_width * 0.5 + (cam_x * f_scale / safe_z)
    screen_y = out_height * 0.5 - (cam_y * f_scale / safe_z)

    # Khởi tạo Canvas với bầu trời gradient
    img = Image.new("RGB", (out_width, out_height))
    draw = ImageDraw.Draw(img)

    sky_top, sky_bot = sky_gradient
    for y in range(out_height):
        t = y / float(out_height)
        r = int(sky_top[0] * (1.0 - t) + sky_bot[0] * t)
        g = int(sky_top[1] * (1.0 - t) + sky_bot[1] * t)
        b = int(sky_top[2] * (1.0 - t) + sky_bot[2] * t)
        draw.line([(0, y), (out_width, y)], fill=(r, g, b))

    # Chuẩn bị danh sách polygon (quads) và sắp xếp chiều sâu Painter's Algorithm (Xa -> Gần)
    quads = []
    for r in range(sub_rows - 1):
        for c in range(sub_cols - 1):
            z0 = cam_z[r, c]
            z1 = cam_z[r, c + 1]
            z2 = cam_z[r + 1, c + 1]
            z3 = cam_z[r + 1, c]

            if z0 <= 2.0 and z1 <= 2.0 and z2 <= 2.0 and z3 <= 2.0:
                continue

            center_depth = (z0 + z1 + z2 + z3) * 0.25

            pts = [
                (float(screen_x[r, c]), float(screen_y[r, c])),
                (float(screen_x[r, c + 1]), float(screen_y[r, c + 1])),
                (float(screen_x[r + 1, c + 1]), float(screen_y[r + 1, c + 1])),
                (float(screen_x[r + 1, c]), float(screen_y[r + 1, c])),
            ]

            b_id = int(sub_biome[r, c])
            base_col = BIOME_COLORS.get(b_id, (50, 80, 50))
            shade_val = float(sub_shade[r, c])

            # Tính sương mù khoảng cách (Atmospheric Fog)
            fog_factor = np.clip((center_depth - 40.0) / 220.0, 0.0, 0.72)
            fog_col = sky_bot

            lit_r = int(np.clip(base_col[0] * shade_val, 0, 255))
            lit_g = int(np.clip(base_col[1] * shade_val, 0, 255))
            lit_b = int(np.clip(base_col[2] * shade_val, 0, 255))

            final_r = int(lit_r * (1.0 - fog_factor) + fog_col[0] * fog_factor)
            final_g = int(lit_g * (1.0 - fog_factor) + fog_col[1] * fog_factor)
            final_b = int(lit_b * (1.0 - fog_factor) + fog_col[2] * fog_factor)

            quads.append((center_depth, pts, (final_r, final_g, final_b)))

    # Sắp xếp từ xa đến gần
    quads.sort(key=lambda item: item[0], reverse=True)

    # Vẽ quads
    for _, pts, col in quads:
        draw.polygon(pts, fill=col, outline=col)

    return img


# ==============================================================================
# 3. TẠO TỔNG HỢP 4 GÓC NHÌN 3D (COMPOSITE 4-PANEL PREVIEW)
# ==============================================================================
def generate_3d_preview(elevation: np.ndarray, biome_id: np.ndarray, river_mask: np.ndarray, output_path: str):
    """Tạo bảng xem trước phối cảnh 3D gồm 4 góc nhìn tráng lệ."""
    _, _, _, shading = compute_normals_and_shading(elevation, height_scale=22.0)

    print("[3D] Đang kết xuất Góc nhìn 1: Toàn cảnh phối cảnh đại lục Primeval Reach...")
    view1 = render_3d_view(
        elevation, biome_id, shading,
        cam_pos=(100.0, 115.0, 260.0),
        look_at=(100.0, 10.0, 95.0),
        fov_deg=52.0,
        out_width=860,
        out_height=520,
        height_scale=25.0,
    )

    print("[3D] Đang kết xuất Góc nhìn 2: Dãy núi tuyết băng giá Tây-Bắc...")
    view2 = render_3d_view(
        elevation, biome_id, shading,
        cam_pos=(55.0, 52.0, 115.0),
        look_at=(55.0, 14.0, 45.0),
        fov_deg=58.0,
        out_width=860,
        out_height=520,
        height_scale=28.0,
        subsample_range=(0, 110, 0, 110),
    )

    print("[3D] Đang kết xuất Góc nhìn 3: Hoang mạc cát đỏ & Vành đai đá sừng sững Tây-Nam...")
    view3 = render_3d_view(
        elevation, biome_id, shading,
        cam_pos=(48.0, 48.0, 195.0),
        look_at=(52.0, 8.0, 135.0),
        fov_deg=56.0,
        out_width=860,
        out_height=520,
        height_scale=26.0,
        subsample_range=(90, 200, 0, 110),
    )

    print("[3D] Đang kết xuất Góc nhìn 4: Đại châu thổ hạ lưu sông mẹ & Rừng cổ sinh Đông Nam...")
    view4 = render_3d_view(
        elevation, biome_id, shading,
        cam_pos=(125.0, 46.0, 220.0),
        look_at=(135.0, 6.0, 150.0),
        fov_deg=55.0,
        out_width=860,
        out_height=520,
        height_scale=24.0,
        subsample_range=(80, 200, 80, 200),
    )

    # Ghép 4 tấm thành bảng điều khiển phối cảnh 2x2 (1760 x 1120)
    canvas_w = 860 * 2 + 30
    canvas_h = 520 * 2 + 80
    composite = Image.new("RGB", (canvas_w, canvas_h), (12, 16, 24))
    draw = ImageDraw.Draw(composite)

    # Tiêu đề chính
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    try:
        title_font = ImageFont.truetype(font_path, 20)
        sub_font = ImageFont.truetype(font_path, 13)
        label_font = ImageFont.truetype(font_path, 14)
    except Exception:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()
        label_font = ImageFont.load_default()

    title_text = "PRIMEVAL REACH - BỘ KẾT XUẤT ĐỊA HÌNH 3D PHỐI CẢNH (3D PERSPECTIVE ATLAS)"
    draw.text((30, 18), title_text, fill=(240, 215, 140), font=title_font)
    sub_title = "Single Source of Truth 200x200 Grid | 100% Procedural | Lambertian Shading & Perspective Frustum"
    draw.text((30, 46), sub_title, fill=(160, 180, 200), font=sub_font)

    # Dán 4 góc nhìn
    panels = [
        (view1, 15, 75, "1. TOÀN CẢNH ĐẠI LỤC (GLOBAL PERSPECTIVE PANORAMA)"),
        (view2, 875 + 15, 75, "2. LỤC ĐỊA BĂNG GIÁ TÂY-BẮC (GLACIAL ALPINE MASSIF & FJORDS)"),
        (view3, 15, 605, "3. HOANG MẠC CÁT ĐỎ TÂY-NAM (TERRACOTTA DUNES & LAGOON)"),
        (view4, 875 + 15, 605, "4. ĐẠI CHÂU THỔ & RỪNG CỔ SINH (SOUTHERN DELTA & RAINFOREST)"),
    ]

    for img_p, px, py, label in panels:
        composite.paste(img_p, (px, py))
        draw.rectangle([(px, py), (px + 860, py + 520)], outline=(60, 90, 130), width=2)
        # Nhãn góc nhìn
        draw.rectangle([(px + 10, py + 10), (px + 640, py + 38)], fill=(10, 14, 20, 220))
        draw.text((px + 18, py + 14), label, fill=(230, 240, 255), font=label_font)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    composite.save(output_path, "PNG")
    print(f"[3D] Đã lưu ảnh phối cảnh 3D tại: {output_path}")


# ==============================================================================
# 4. XUẤT MÔ HÌNH 3D CHUẨN WAVEFRONT (.OBJ & .MTL)
# ==============================================================================
def export_wavefront_obj(elevation: np.ndarray, biome_id: np.ndarray, obj_path: str, height_scale=22.0):
    """
    Xuất mô hình lưới 3D (.obj) cùng tệp vật liệu (.mtl) để nhập vào Blender/Unity/Godot.
    """
    rows, cols = elevation.shape
    mtl_path = os.path.splitext(obj_path)[0] + ".mtl"
    mtl_filename = os.path.basename(mtl_path)

    # 1. Ghi tệp MTL (Vật liệu theo 8 Quần xã)
    print(f"[3D] Đang xuất tệp vật liệu MTL: {mtl_path}...")
    with open(mtl_path, "w", encoding="utf-8") as fmtl:
        fmtl.write("# Materials for Primeval Reach World\n\n")
        for b_id, color in BIOME_COLORS.items():
            name = BIOME_NAMES.get(b_id, f"biome_{b_id}").replace(" ", "_").replace("&", "and")
            r, g, b = [c / 255.0 for c in color]
            fmtl.write(f"newmtl mtl_{name}\n")
            fmtl.write(f"Kd {r:.4f} {g:.4f} {b:.4f}\n")
            fmtl.write(f"Ka {r*0.4:.4f} {g*0.4:.4f} {b*0.4:.4f}\n")
            fmtl.write("Ks 0.1000 0.1000 0.1000\n")
            fmtl.write("Ns 10.0\n")
            fmtl.write("d 1.0\n")
            fmtl.write("illum 2\n\n")

    # 2. Ghi tệp OBJ (Vertices, UVs, Normals, Faces nhóm theo Quần xã)
    print(f"[3D] Đang xuất tệp mô hình 3D OBJ: {obj_path}...")
    nx, ny, nz, _ = compute_normals_and_shading(elevation, height_scale=height_scale)

    with open(obj_path, "w", encoding="utf-8") as fobj:
        fobj.write("# Wavefront OBJ export for Primeval Reach (GCVL)\n")
        fobj.write(f"mtllib {mtl_filename}\n\n")

        # Ghi các đỉnh (Vertices: v x y z)
        # Tọa độ chuẩn hóa về tâm [-(cols/2) .. (cols/2)]
        half_w = cols * 0.5
        half_h = rows * 0.5

        for r in range(rows):
            for c in range(cols):
                vx = c - half_w
                # Nâng cao độ đất nổi mượt mà từ bờ biển, mặt nước phẳng
                h = max(0.01, float(elevation[r, c]) - 0.33) if float(elevation[r, c]) >= 0.35 else 0.01
                vy = h * 1.35 * height_scale
                vz = r - half_h
                fobj.write(f"v {vx:.2f} {vy:.2f} {vz:.2f}\n")

        # Ghi UV Coordinates (vt u v)
        for r in range(rows):
            for c in range(cols):
                u = c / float(cols - 1)
                v = 1.0 - (r / float(rows - 1))
                fobj.write(f"vt {u:.4f} {v:.4f}\n")

        # Ghi Pháp tuyến (vn nx ny nz)
        for r in range(rows):
            for c in range(cols):
                fobj.write(f"vn {nx[r, c]:.3f} {ny[r, c]:.3f} {nz[r, c]:.3f}\n")

        # Gom nhóm Faces theo vật liệu Biome
        # Đỉnh trong OBJ bắt đầu từ chỉ mục 1
        faces_by_biome = {}
        for r in range(rows - 1):
            for c in range(cols - 1):
                b_id = int(biome_id[r, c])
                if b_id not in faces_by_biome:
                    faces_by_biome[b_id] = []

                # 4 chỉ mục đỉnh của ô (1-based index)
                idx0 = r * cols + c + 1
                idx1 = r * cols + (c + 1) + 1
                idx2 = (r + 1) * cols + (c + 1) + 1
                idx3 = (r + 1) * cols + c + 1

                # 2 tam giác cho mỗi ô lưới
                faces_by_biome[b_id].append((idx0, idx1, idx2))
                faces_by_biome[b_id].append((idx0, idx2, idx3))

        # Ghi Faces theo từng nhóm Biome
        for b_id in sorted(faces_by_biome.keys()):
            name = BIOME_NAMES.get(b_id, f"biome_{b_id}").replace(" ", "_").replace("&", "and")
            fobj.write(f"\ng biome_{name}\n")
            fobj.write(f"usemtl mtl_{name}\n")
            for v0, v1, v2 in faces_by_biome[b_id]:
                # f v/vt/vn v/vt/vn v/vt/vn
                fobj.write(f"f {v0}/{v0}/{v0} {v1}/{v1}/{v1} {v2}/{v2}/{v2}\n")

    print(f"[3D] Hoàn tất xuất OBJ ({rows*cols} đỉnh, {(rows-1)*(cols-1)*2} mặt tam giác)!")


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
def main():
    json_file = "stone_age_world_200x200.json"
    elevation, biome_id, river_mask = load_world_data(json_file)

    out_preview = "debug_outputs/primeval_world_3d_preview.png"
    out_obj = "debug_outputs/primeval_world.obj"

    print(f"=== KHỞI ĐỘNG XUẤT 3D THẾ GIỚI PRIMEVAL REACH ({elevation.shape[1]}x{elevation.shape[0]}) ===")
    generate_3d_preview(elevation, biome_id, river_mask, out_preview)
    export_wavefront_obj(elevation, biome_id, out_obj, height_scale=22.0)
    print("=== HOÀN TẤT KẾT XUẤT 3D TOÀN DIỆN! ===")


if __name__ == "__main__":
    main()
