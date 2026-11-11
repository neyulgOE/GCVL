#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Công cụ kết xuất phối cảnh 3D và xuất mô hình 3D (Wavefront OBJ/MTL)
từ Bản đồ Thế giới Chuẩn Primeval Reach (GCVL).

- Kết xuất 4 góc nhìn phối cảnh 3D chân thực: debug_outputs/primeval_world_3d_preview.png
- Xuất tệp mô hình 3D chuẩn kèm kết cấu UV: debug_outputs/primeval_world.obj & primeval_world.mtl
"""

import json
import math
import os
import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEBUG_DIR = PROJECT_ROOT / "debug_outputs"
CANONICAL_IMG_PATH = PROJECT_ROOT / "assets" / "sprites" / "primeval_reach_canonical_atlas.png"
TEXTURE_PATH = DEBUG_DIR / "primeval_world_texture.png"


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

BIOME_COLORS = {
    0: (11, 44, 76),
    1: (28, 182, 196),
    2: (42, 118, 158),
    3: (42, 94, 46),
    4: (204, 134, 48),
    5: (212, 114, 68),
    6: (240, 245, 250),
    7: (34, 102, 54),
}


def load_canonical_data():
    """Tải dữ liệu độ cao và kết cấu bề mặt từ bản đồ chuẩn."""
    if not TEXTURE_PATH.exists() or not (PROJECT_ROOT / "stone_age_world_200x200.json").exists():
        from tools.generate_primeval_world import export_all
        export_all()

    tex_img = Image.open(TEXTURE_PATH).convert("RGB")
    texture_full = np.array(tex_img)
    th, tw, _ = texture_full.shape

    with open(PROJECT_ROOT / "stone_age_world_200x200.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    elev_grid = np.array(data["elevation"], dtype=np.float32)
    biome_grid = np.array(data["biome_id"], dtype=np.int32)
    tex_grid = cv2.resize(texture_full, (200, 200), interpolation=cv2.INTER_AREA)

    return elev_grid, biome_grid, tex_grid, texture_full


# ==============================================================================
# 1. KẾT XUẤT PHỐI CẢNH 3D (PERSPECTIVE 3D RENDERER)
# ==============================================================================
def render_3d_view(
    elevation: np.ndarray,
    texture: np.ndarray,
    cam_pos=(100.0, 95.0, 245.0),
    look_at=(100.0, 10.0, 95.0),
    fov_deg=52.0,
    out_width=860,
    out_height=520,
    height_scale=22.0,
    subsample_range=None,
    aspect_ratio_correction=1.83,
    sky_gradient=((14, 24, 42), (64, 88, 118)),
):
    rows, cols = elevation.shape
    r_start, r_end = 0, rows
    c_start, c_end = 0, cols
    if subsample_range is not None:
        r_start, r_end, c_start, c_end = subsample_range

    r_idx = np.arange(r_start, r_end)
    c_idx = np.arange(c_start, c_end)
    sub_elev = elevation[np.ix_(r_idx, c_idx)]
    sub_tex = texture[np.ix_(r_idx, c_idx)]

    sub_rows, sub_cols = sub_elev.shape

    # Tọa độ thế giới X, Y, Z (căn chỉnh theo tỷ lệ 16:9 của bản đồ thực tế)
    C_grid, R_grid = np.meshgrid(c_idx, r_idx)
    # Tọa độ X co giãn theo aspect_ratio_correction
    X_world = (C_grid.astype(np.float32) - cols * 0.5) * aspect_ratio_correction + (cols * 0.5)
    Z_world = R_grid.astype(np.float32)
    # Nâng cao độ đất nổi mượt mà
    Y_world = np.where(sub_elev < 0.35, 0.03, (sub_elev - 0.33) * 1.35) * height_scale

    # Tính toán Camera Basis
    cx, cy, cz = cam_pos
    lx, ly, lz = look_at
    forward = np.array([lx - cx, ly - cy, lz - cz], dtype=np.float32)
    forward /= (np.linalg.norm(forward) + 1e-8)

    up_hint = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    right = np.cross(forward, up_hint)
    right /= (np.linalg.norm(right) + 1e-8)
    up = np.cross(right, forward)

    # Chiếu sang Camera Space
    dx = X_world - cx
    dy = Y_world - cy
    dz = Z_world - cz

    cam_x = dx * right[0] + dy * right[1] + dz * right[2]
    cam_y = dx * up[0] + dy * up[1] + dz * up[2]
    cam_z = dx * forward[0] + dy * forward[1] + dz * forward[2]

    # Chiếu phối cảnh Perspective
    fov_rad = math.radians(fov_deg)
    f_scale = (out_width * 0.5) / math.tan(fov_rad * 0.5)

    safe_z = np.maximum(2.0, cam_z)
    screen_x = out_width * 0.5 + (cam_x * f_scale / safe_z)
    screen_y = out_height * 0.5 - (cam_y * f_scale / safe_z)

    # Nền bầu trời
    img = Image.new("RGB", (out_width, out_height))
    draw = ImageDraw.Draw(img)
    sky_top, sky_bot = sky_gradient
    for y in range(out_height):
        t = y / float(out_height)
        r = int(sky_top[0] * (1.0 - t) + sky_bot[0] * t)
        g = int(sky_top[1] * (1.0 - t) + sky_bot[1] * t)
        b = int(sky_top[2] * (1.0 - t) + sky_bot[2] * t)
        draw.line([(0, y), (out_width, y)], fill=(r, g, b))

    # Danh sách các quads
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

            tex_col = sub_tex[r, c]

            # Sương mù khí quyển xa (Distance Fog)
            fog = np.clip((center_depth - 45.0) / 220.0, 0.0, 0.65)
            fog_col = sky_bot

            final_r = int(tex_col[0] * (1.0 - fog) + fog_col[0] * fog)
            final_g = int(tex_col[1] * (1.0 - fog) + fog_col[1] * fog)
            final_b = int(tex_col[2] * (1.0 - fog) + fog_col[2] * fog)

            quads.append((center_depth, pts, (final_r, final_g, final_b)))

    # Sắp xếp từ xa đến gần
    quads.sort(key=lambda item: item[0], reverse=True)

    for _, pts, col in quads:
        draw.polygon(pts, fill=col, outline=col)

    return img


# ==============================================================================
# 2. BẢNG XEM TRƯỚC 4 GÓC NHÌN PHỐI CẢNH 3D (COMPOSITE PREVIEW)
# ==============================================================================
def generate_3d_preview(elevation: np.ndarray, texture: np.ndarray, output_path: str):
    print("[3D] Đang kết xuất Góc nhìn 1: Toàn cảnh phối cảnh đại lục Primeval Reach...")
    view1 = render_3d_view(
        elevation, texture,
        cam_pos=(100.0, 110.0, 255.0),
        look_at=(100.0, 8.0, 95.0),
        fov_deg=52.0,
        out_width=860,
        out_height=520,
        height_scale=22.0,
    )

    print("[3D] Đang kết xuất Góc nhìn 2: Dãy núi tuyết băng giá Tây-Bắc (Glacial Alpine)...")
    view2 = render_3d_view(
        elevation, texture,
        cam_pos=(45.0, 52.0, 112.0),
        look_at=(52.0, 12.0, 48.0),
        fov_deg=56.0,
        out_width=860,
        out_height=520,
        height_scale=26.0,
        subsample_range=(0, 110, 0, 110),
    )

    print("[3D] Đang kết xuất Góc nhìn 3: Hoang mạc cát đỏ & Vành đai đá sừng sững Tây-Nam...")
    view3 = render_3d_view(
        elevation, texture,
        cam_pos=(42.0, 48.0, 192.0),
        look_at=(50.0, 8.0, 136.0),
        fov_deg=55.0,
        out_width=860,
        out_height=520,
        height_scale=24.0,
        subsample_range=(90, 200, 0, 110),
    )

    print("[3D] Đang kết xuất Góc nhìn 4: Đại châu thổ hạ lưu sông mẹ & Rừng cổ sinh Đông Nam...")
    view4 = render_3d_view(
        elevation, texture,
        cam_pos=(122.0, 48.0, 218.0),
        look_at=(135.0, 8.0, 148.0),
        fov_deg=54.0,
        out_width=860,
        out_height=520,
        height_scale=22.0,
        subsample_range=(80, 200, 80, 200),
    )

    canvas_w = 860 * 2 + 30
    canvas_h = 520 * 2 + 80
    composite = Image.new("RGB", (canvas_w, canvas_h), (12, 16, 24))
    draw = ImageDraw.Draw(composite)

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
    sub_title = "Single Source of Truth Canonical Grid | 100% Faithful Relief | UV Texture Mapped & Perspective Frustum"
    draw.text((30, 46), sub_title, fill=(160, 180, 200), font=sub_font)

    panels = [
        (view1, 15, 75, "1. TOÀN CẢNH ĐẠI LỤC (GLOBAL PERSPECTIVE PANORAMA)"),
        (view2, 875 + 15, 75, "2. LỤC ĐỊA BĂNG GIÁ TÂY-BẮC (GLACIAL ALPINE MASSIF & FJORDS)"),
        (view3, 15, 605, "3. HOANG MẠC CÁT ĐỎ TÂY-NAM (TERRACOTTA DUNES & LAGOON)"),
        (view4, 875 + 15, 605, "4. ĐẠI CHÂU THỔ & RỪNG CỔ SINH (SOUTHERN DELTA & RAINFOREST)"),
    ]

    for img_p, px, py, label in panels:
        composite.paste(img_p, (px, py))
        draw.rectangle([(px, py), (px + 860, py + 520)], outline=(60, 90, 130), width=2)
        draw.rectangle([(px + 10, py + 10), (px + 640, py + 38)], fill=(10, 14, 20, 220))
        draw.text((px + 18, py + 14), label, fill=(230, 240, 255), font=label_font)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    composite.save(output_path, "PNG")
    print(f"[3D] Đã lưu ảnh phối cảnh 3D tại: {output_path}")


# ==============================================================================
# 3. XUẤT MÔ HÌNH 3D CHUẨN WAVEFRONT (.OBJ, .MTL & .PNG TEXTURE)
# ==============================================================================
def export_wavefront_obj(elevation: np.ndarray, biome_id: np.ndarray, obj_path: str, height_scale=22.0):
    rows, cols = elevation.shape
    mtl_path = os.path.splitext(obj_path)[0] + ".mtl"
    mtl_filename = os.path.basename(mtl_path)
    tex_filename = "primeval_world_texture.png"

    # 1. Ghi tệp MTL
    print(f"[3D] Đang xuất tệp vật liệu MTL: {mtl_path}...")
    with open(mtl_path, "w", encoding="utf-8") as fmtl:
        fmtl.write("# Materials for Primeval Reach Canonical World\n\n")
        # Vật liệu chính có gắn kết cấu UV texture
        fmtl.write("newmtl mtl_Primeval_World_Texture\n")
        fmtl.write("Kd 1.0000 1.0000 1.0000\n")
        fmtl.write("Ka 0.3500 0.3500 0.3500\n")
        fmtl.write("Ks 0.1000 0.1000 0.1000\n")
        fmtl.write("Ns 10.0\n")
        fmtl.write("d 1.0\n")
        fmtl.write(f"map_Kd {tex_filename}\n\n")

        # Các vật liệu màu dự phòng theo 8 quần xã
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

    # 2. Ghi tệp OBJ
    print(f"[3D] Đang xuất tệp mô hình 3D OBJ: {obj_path}...")
    aspect_scale = 1.83
    half_w = cols * 0.5
    half_h = rows * 0.5

    with open(obj_path, "w", encoding="utf-8") as fobj:
        fobj.write("# Wavefront OBJ export for Primeval Reach Canonical World\n")
        fobj.write(f"mtllib {mtl_filename}\n\n")

        # Vertices (v x y z)
        for r in range(rows):
            for c in range(cols):
                vx = (c - half_w) * aspect_scale
                h = max(0.01, float(elevation[r, c]) - 0.33) if float(elevation[r, c]) >= 0.35 else 0.01
                vy = h * 1.35 * height_scale
                vz = r - half_h
                fobj.write(f"v {vx:.2f} {vy:.2f} {vz:.2f}\n")

        # Texture Coordinates (vt u v)
        for r in range(rows):
            for c in range(cols):
                u = c / float(cols - 1)
                v = 1.0 - (r / float(rows - 1))
                fobj.write(f"vt {u:.4f} {v:.4f}\n")

        # Normals (vn nx ny nz)
        gy, gx = np.gradient(elevation * height_scale)
        nx = -gx
        ny = np.ones_like(gx)
        nz = -gy
        norm = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
        nx /= norm
        ny /= norm
        nz /= norm

        for r in range(rows):
            for c in range(cols):
                fobj.write(f"vn {nx[r, c]:.3f} {ny[r, c]:.3f} {nz[r, c]:.3f}\n")

        # Faces dùng chung mtl_Primeval_World_Texture
        fobj.write("\ng terrain_surface\n")
        fobj.write("usemtl mtl_Primeval_World_Texture\n")

        for r in range(rows - 1):
            for c in range(cols - 1):
                idx0 = r * cols + c + 1
                idx1 = r * cols + (c + 1) + 1
                idx2 = (r + 1) * cols + (c + 1) + 1
                idx3 = (r + 1) * cols + c + 1

                fobj.write(f"f {idx0}/{idx0}/{idx0} {idx1}/{idx1}/{idx1} {idx2}/{idx2}/{idx2}\n")
                fobj.write(f"f {idx0}/{idx0}/{idx0} {idx2}/{idx2}/{idx2} {idx3}/{idx3}/{idx3}\n")

    print(f"[3D] Hoàn tất xuất OBJ ({rows*cols} đỉnh, {(rows-1)*(cols-1)*2} mặt tam giác)!")


def main():
    elev_grid, biome_grid, tex_grid, texture_full = load_canonical_data()

    out_preview = str(DEBUG_DIR / "primeval_world_3d_preview.png")
    out_obj = str(DEBUG_DIR / "primeval_world.obj")

    print(f"=== KHỞI ĐỘNG XUẤT 3D CHUẨN THẾ GIỚI PRIMEVAL REACH ===")
    generate_3d_preview(elev_grid, tex_grid, out_preview)
    export_wavefront_obj(elev_grid, biome_grid, out_obj, height_scale=22.0)
    print("=== HOÀN TẤT KẾT XUẤT 3D CHUẨN THỰC THẾ! ===")


if __name__ == "__main__":
    main()
