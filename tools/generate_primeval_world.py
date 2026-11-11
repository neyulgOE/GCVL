#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bộ sinh bản đồ thế giới đa lục địa nguyên sinh (100% Procedural) chuẩn cho dự án GCVL.
- Xuất ảnh bản đồ địa hình 3D Hillshaded: debug_outputs/primeval_world_atlas.png
- Đồng bộ vào tài nguyên game: assets/sprites/world_atlas.png & world_overview_macro.png
- Xuất dữ liệu lưới thế giới (200x200): stone_age_world_200x200.json
"""

import json
import math
import os
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps


# ==============================================================================
# 1. HÀM NHIỄU PHÂN TẦNG (MULTI-OCTAVE VALUE/PERLIN NOISE THUẦN NUMPY)
# ==============================================================================
def _hash2d(ix: np.ndarray, iy: np.ndarray, seed: int) -> np.ndarray:
    n = ix * 374761393 + iy * 668265263 + seed * 1442695041
    n = (n ^ (n >> 13)) * 1274126177
    n = n ^ (n >> 16)
    return (n & 0x7FFFFFFF).astype(np.float32) / float(0x7FFFFFFF)


def value_noise_2d(x: np.ndarray, y: np.ndarray, seed: int = 42) -> np.ndarray:
    ix = np.floor(x).astype(np.int64)
    iy = np.floor(y).astype(np.int64)
    fx = x - ix
    fy = y - iy

    # Đường cong làm mượt Quintic (6t^5 - 15t^4 + 10t^3)
    ux = fx * fx * fx * (fx * (fx * 6.0 - 15.0) + 10.0)
    uy = fy * fy * fy * (fy * (fy * 6.0 - 15.0) + 10.0)

    v00 = _hash2d(ix, iy, seed)
    v10 = _hash2d(ix + 1, iy, seed)
    v01 = _hash2d(ix, iy + 1, seed)
    v11 = _hash2d(ix + 1, iy + 1, seed)

    v0 = v00 + ux * (v10 - v00)
    v1 = v01 + ux * (v11 - v01)
    return v0 + uy * (v1 - v0)


def fbm_2d(
    x: np.ndarray,
    y: np.ndarray,
    octaves: int = 6,
    lacunarity: float = 2.05,
    gain: float = 0.5,
    seed: int = 101,
) -> np.ndarray:
    total = np.zeros_like(x, dtype=np.float32)
    amplitude = 1.0
    frequency = 1.0
    max_amp = 0.0

    for i in range(octaves):
        total += amplitude * value_noise_2d(x * frequency, y * frequency, seed + i * 31)
        max_amp += amplitude
        amplitude *= gain
        frequency *= lacunarity

    return total / max_amp


def ridged_fbm_2d(
    x: np.ndarray, y: np.ndarray, octaves: int = 5, seed: int = 303
) -> np.ndarray:
    """Nhiễu tạo sống núi sắc nét cho dãy núi tuyết và vành đai đá sa mạc."""
    total = np.zeros_like(x, dtype=np.float32)
    amplitude = 0.5
    frequency = 1.0
    weight = np.ones_like(x, dtype=np.float32)

    for i in range(octaves):
        n = value_noise_2d(x * frequency, y * frequency, seed + i * 47)
        signal = 1.0 - np.abs(2.0 * n - 1.0)
        signal = signal * signal * weight
        weight = np.clip(signal * 2.0, 0.0, 1.0)
        total += signal * amplitude
        frequency *= 2.1
        amplitude *= 0.5

    return np.clip(total * 1.35, 0.0, 1.0)


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0 + 1e-8), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ==============================================================================
# 2. KIẾN TẠO ĐỊA HÌNH ĐA LỤC ĐỊA, QUẦN XÃ SINH VẬT & THỦY VĂN
# ==============================================================================
def generate_primeval_world(width: int = 1440, height: int = 810, seed: int = 2026):
    u = np.linspace(0.0, 1.0, width, dtype=np.float32)
    v = np.linspace(0.0, 1.0, height, dtype=np.float32)
    U, V = np.meshgrid(u, v)

    # Biến dạng miền (Domain Warping)
    warp_x = (fbm_2d(U * 4.5, V * 4.5, octaves=4, seed=seed + 1) - 0.5) * 0.08
    warp_y = (fbm_2d(U * 4.5, V * 4.5, octaves=4, seed=seed + 2) - 0.5) * 0.08
    Uw = U + warp_x
    Vw = V + warp_y

    coast_detail = (fbm_2d(U * 16.0, V * 16.0, octaves=5, seed=seed + 3) - 0.5) * 0.12

    # --------------------------------------------------------------------------
    # A. ĐỊNH HÌNH 4 ĐẠI LỤC & QUẦN ĐẢO TÁCH BIỆT
    # --------------------------------------------------------------------------
    # 1. Lục địa Tây-Bắc (Glacial Alpine Massif, Rừng thông & Chuỗi đảo Fjord)
    dist_nw_main = np.sqrt(((Uw - 0.31) / 0.17) ** 2 + ((Vw - 0.22) / 0.20) ** 2)
    mask_nw = 1.0 - smoothstep(0.66, 1.06, dist_nw_main + coast_detail)

    # Chuỗi đảo fjord Tây-Bắc
    fjord_chain = fbm_2d(U * 22.0, V * 22.0, octaves=4, seed=seed + 15)
    in_nw_arch = (
        smoothstep(0.05, 0.12, U) * smoothstep(0.18, 0.10, U)
        * smoothstep(0.04, 0.14, V) * smoothstep(0.38, 0.26, V)
    )
    islets_nw = (1.0 - smoothstep(0.50, 0.68, fjord_chain)) * in_nw_arch * 1.3
    mask_nw = np.maximum(mask_nw, islets_nw)

    # Hồ băng Đông-Bắc trên lục địa Tây-Bắc
    lake_nw = 1.0 - smoothstep(0.024, 0.048, np.sqrt(((Uw - 0.36) * 1.4) ** 2 + (Vw - 0.19) ** 2))
    mask_nw = np.clip(mask_nw - lake_nw * 0.90, 0.0, 1.0)

    # Vịnh tròn Đông-Nam khoét sâu có rừng ôm quanh
    bay_nw_circle = 1.0 - smoothstep(0.038, 0.072, np.sqrt(((Uw - 0.35) * 1.2) ** 2 + (Vw - 0.33) ** 2))
    mask_nw = np.clip(mask_nw - bay_nw_circle * 0.92, 0.0, 1.0)

    # 2. Lục địa Tây-Nam (Hoang mạc đất đỏ Terracotta Dunes & Vành đai đá)
    dist_sw_main = np.sqrt(((Uw - 0.23) / 0.16) ** 2 + ((Vw - 0.67) / 0.19) ** 2)
    mask_sw = 1.0 - smoothstep(0.68, 1.05, dist_sw_main + coast_detail * 0.9)

    # Vịnh đầm phá và ốc đảo phía Đông lục địa Tây-Nam
    lagoon_east_dist = np.sqrt(((Uw - 0.33) / 0.04) ** 2 + ((Vw - 0.58) / 0.035) ** 2)
    lagoon_cut = 1.0 - smoothstep(0.60, 1.05, lagoon_east_dist)
    oasis_islet = 1.0 - smoothstep(0.008, 0.016, np.sqrt(((Uw - 0.33) * 1.3) ** 2 + (Vw - 0.58) ** 2))
    mask_sw = np.clip(mask_sw - lagoon_cut * 0.90 + oasis_islet * 0.95, 0.0, 1.0)

    # Eo biển Tây ngăn cách Tây-Bắc và Tây-Nam
    strait_west = np.exp(-((Vw - 0.46) / 0.032) ** 2) * smoothstep(0.44, 0.28, U)
    mask_nw *= 1.0 - strait_west * 0.95
    mask_sw *= 1.0 - strait_west * 0.95

    # 3. Đại lục Đông (Cao nguyên mùa thu phía Bắc + Rừng thiêng & Vịnh Trăng Khuyết)
    dist_east_north = np.sqrt(((Uw - 0.73) / 0.18) ** 2 + ((Vw - 0.28) / 0.22) ** 2)
    dist_east_south = np.sqrt(((Uw - 0.64) / 0.21) ** 2 + ((Vw - 0.65) / 0.25) ** 2)
    peninsula_se = np.exp(-((Uw - 0.77) / 0.038) ** 2) * smoothstep(0.50, 0.62, Vw) * smoothstep(0.85, 0.72, Vw)

    dist_east = np.minimum(np.minimum(dist_east_north, dist_east_south), 1.0 - peninsula_se * 0.5)
    mask_east = 1.0 - smoothstep(0.70, 1.06, dist_east + coast_detail * 1.05)

    # Vịnh Trăng Khuyết (Crescent Bay) khoét sâu vào Đại lục Đông
    crescent_bay_center = np.sqrt(((Uw - 0.67) / 0.082) ** 2 + ((Vw - 0.60) / 0.095) ** 2)
    crescent_bay_channel = np.exp(-((Uw - 0.72) / 0.026) ** 2) * smoothstep(0.56, 0.72, Vw)
    bay_cut = (1.0 - smoothstep(0.65, 1.02, crescent_bay_center)) + crescent_bay_channel * 0.85
    mask_east = np.clip(mask_east - bay_cut * 0.95, 0.0, 1.0)

    # Eo đất (Isthmus) phía Nam nối Tây-Nam sang Đại lục Đông
    isthmus_sw_east = np.exp(-((Vw - 0.78) / 0.026) ** 2) * smoothstep(0.32, 0.38, Uw) * smoothstep(0.48, 0.42, Uw)
    mask_east = np.clip(mask_east + isthmus_sw_east * 0.85, 0.0, 1.0)

    # Eo biển trung tâm ngăn cách Tây và Đông
    strait_center = np.exp(-((Uw - 0.44 + (Vw - 0.50) * 0.16) / 0.052) ** 2)
    mask_east *= 1.0 - strait_center * 0.88

    # 4. Quần đảo Thánh tích Đông-Nam (Sanctuary Archipelago)
    dist_se_center = np.sqrt(((Uw - 0.90) / 0.048) ** 2 + ((Vw - 0.85) / 0.065) ** 2)
    island_center = 1.0 - smoothstep(0.60, 1.05, dist_se_center)
    ring_noise = fbm_2d(U * 36.0, V * 36.0, octaves=4, seed=seed + 99)
    ring_band = np.exp(-((dist_se_center - 1.25) / 0.22) ** 2) * (ring_noise > 0.42)
    mask_se = np.clip(island_center + ring_band * 0.85, 0.0, 1.0)

    # Gộp toàn bộ đất nổi và đóng viền biển
    land_raw = np.maximum(np.maximum(mask_nw, mask_sw), np.maximum(mask_east, mask_se))
    border_fade = (
        smoothstep(0.015, 0.045, U)
        * smoothstep(0.985, 0.955, U)
        * smoothstep(0.015, 0.045, V)
        * smoothstep(0.985, 0.955, V)
    )
    land_mask = land_raw * border_fade

    # --------------------------------------------------------------------------
    # B. PHÂN BỔ ĐỘ CAO (ELEVATION & RELIEF)
    # --------------------------------------------------------------------------
    base_plains = fbm_2d(U * 6.0, V * 6.0, octaves=4, seed=seed + 10) * 0.16 + 0.06
    ridges = ridged_fbm_2d(U * 8.0, V * 8.0, octaves=5, seed=seed + 11)

    # Đỉnh núi tuyết Tây-Bắc
    alpine_zone = (
        mask_nw
        * smoothstep(0.36, 0.06, Vw)
        * np.exp(-((Uw - 0.25) / 0.075) ** 2)
        * 1.15
    )
    # Vành đai miệng đá bao quanh hoang mạc Tây-Nam
    sw_basin_dist = np.sqrt(((Uw - 0.22) / 0.10) ** 2 + ((Vw - 0.67) / 0.11) ** 2)
    sw_crater_rim = mask_sw * np.exp(-((sw_basin_dist - 0.88) / 0.32) ** 2) * 0.70

    # Cao nguyên thoải Đông-Bắc
    autumn_plateau = (
        mask_east
        * smoothstep(0.44, 0.10, Vw)
        * (0.35 + 0.30 * np.exp(-((Vw - 0.12) / 0.06) ** 2) * ridges)
    )

    # Sống rừng rậm ôm quanh Vịnh Trăng Khuyết
    crescent_ridge = (
        mask_east
        * np.exp(-((crescent_bay_center - 1.05) / 0.25) ** 2)
        * (0.28 + 0.32 * ridges)
    )

    mountain_height = (
        alpine_zone * (0.60 + 0.40 * ridges)
        + sw_crater_rim * (0.45 + 0.35 * ridges)
        + autumn_plateau
        + crescent_ridge
    )

    elevation = np.where(
        land_mask > 0.35,
        0.35 + (land_mask - 0.35) * 0.40 * base_plains + mountain_height,
        land_mask,
    )

    # --------------------------------------------------------------------------
    # C. THỦY VĂN: SÔNG UỐN KHÚC, HỒ NÚI CAO & CHÂU THỔ ĐA NHÁNH
    # --------------------------------------------------------------------------
    river_mask = np.zeros_like(U, dtype=np.float32)

    # Hồ trung tâm Cao nguyên mùa thu
    lake_autumn_dist = np.sqrt(((Uw - 0.70) / 0.052) ** 2 + ((Vw - 0.30) / 0.035) ** 2)
    lake_autumn = 1.0 - smoothstep(0.70, 1.05, lake_autumn_dist)

    # Hồ nội địa Tây-Bắc
    lake_nw_mask = 1.0 - smoothstep(0.70, 1.05, np.sqrt(((Uw - 0.36) / 0.040) ** 2 + ((Vw - 0.19) / 0.028) ** 2))

    # Sông chính uốn khúc nối từ hồ Cao nguyên mùa thu
    meander_wave = 0.038 * np.sin(V * 28.0 + fbm_2d(U * 6.0, V * 6.0, seed=77) * 4.5)
    river_main_x = 0.62 + (0.70 - 0.62) * smoothstep(0.75, 0.30, V) + meander_wave
    dist_river_main = np.abs(U - river_main_x)
    in_main_reach = smoothstep(0.24, 0.30, V) * smoothstep(0.85, 0.72, V) * (mask_east > 0.36)
    river_main = (1.0 - smoothstep(0.0022, 0.0068, dist_river_main)) * in_main_reach

    # Châu thổ khổng lồ phía Nam Đại lục Đông (Braided Delta)
    delta_branches = np.zeros_like(U, dtype=np.float32)
    delta_offsets = [-0.10, -0.06, -0.02, 0.02, 0.06, 0.10]
    for idx, off in enumerate(delta_offsets):
        d_x = 0.53 + (V - 0.73) * off * 2.8 + 0.010 * np.sin(V * 50.0 + idx * 15)
        in_delta = smoothstep(0.71, 0.76, V) * smoothstep(0.92, 0.85, V) * (mask_east > 0.28)
        branch = (1.0 - smoothstep(0.0016, 0.0048, np.abs(U - d_x))) * in_delta
        delta_branches = np.maximum(delta_branches, branch)

    # Châu thổ phía Nam lục địa Tây-Bắc
    nw_delta = np.zeros_like(U, dtype=np.float32)
    for nw_off in [-0.05, 0.0, 0.05]:
        nw_dx = 0.28 + (V - 0.40) * nw_off * 3.0 + 0.008 * np.sin(V * 40.0)
        in_nw_delta = smoothstep(0.38, 0.42, V) * smoothstep(0.48, 0.44, V) * (mask_nw > 0.30)
        nw_branch = (1.0 - smoothstep(0.0015, 0.0045, np.abs(U - nw_dx))) * in_nw_delta
        nw_delta = np.maximum(nw_delta, nw_branch)

    # Phụ lưu hội tụ về hồ mùa thu và sông chính
    tributaries = np.zeros_like(U, dtype=np.float32)
    trib_coords = [
        (0.63, 0.15, 0.70, 0.30),
        (0.78, 0.16, 0.70, 0.30),
        (0.84, 0.24, 0.70, 0.30),
        (0.55, 0.42, 0.64, 0.50),
        (0.28, 0.15, 0.36, 0.19),
        (0.36, 0.19, 0.40, 0.25),
        (0.57, 0.62, 0.60, 0.70),
        (0.64, 0.70, 0.54, 0.76),
    ]
    for tx_start, ty_start, tx_end, ty_end in trib_coords:
        l2 = (tx_end - tx_start) ** 2 + (ty_end - ty_start) ** 2 + 1e-8
        t_param = np.clip(((U - tx_start) * (tx_end - tx_start) + (V - ty_start) * (ty_end - ty_start)) / l2, 0.0, 1.0)
        proj_x = tx_start + t_param * (tx_end - tx_start) + 0.009 * np.sin(t_param * 16.0)
        proj_y = ty_start + t_param * (ty_end - ty_start) + 0.009 * np.cos(t_param * 16.0)
        d_trib = np.sqrt((U - proj_x) ** 2 + (V - proj_y) ** 2)
        trib = (1.0 - smoothstep(0.0012, 0.0042, d_trib)) * (land_mask > 0.38)
        tributaries = np.maximum(tributaries, trib)

    river_mask = np.maximum.reduce([river_main, delta_branches, nw_delta, tributaries, lake_autumn, lake_nw_mask])
    elevation = np.where(river_mask > 0.5, 0.34, elevation - river_mask * 0.06)

    # --------------------------------------------------------------------------
    # D. PHÂN VÙNG QUẦN XÃ SINH VẬT (BIOME IDS)
    # --------------------------------------------------------------------------
    # 0=Đại dương sâu, 1=Thềm san hô, 2=Sông/Hồ, 3=Rừng nguyên sinh/Đồng cỏ,
    # 4=Cao nguyên mùa thu, 5=Hoang mạc đất đỏ, 6=Núi tuyết & Băng hà, 7=Đảo bảo tồn
    biome_id = np.zeros((height, width), dtype=np.uint8)
    biome_id[land_mask > 0.16] = 1
    biome_id[land_mask > 0.35] = 3

    is_autumn = (mask_east > 0.35) & (Vw + (fbm_2d(U * 8.0, V * 8.0, seed=55) - 0.5) * 0.10 < 0.44)
    biome_id[is_autumn] = 4

    is_desert = (mask_sw > 0.35) & (sw_basin_dist < 0.78)
    biome_id[is_desert] = 5

    is_glacial = (mask_nw > 0.35) & (elevation > 0.60) & (Vw < 0.32)
    biome_id[is_glacial] = 6

    biome_id[mask_se > 0.35] = 7
    biome_id[river_mask > 0.40] = 2

    return {
        "U": U,
        "V": V,
        "land_mask": land_mask,
        "elevation": elevation,
        "river_mask": river_mask,
        "delta_branches": delta_branches,
        "nw_delta": nw_delta,
        "biome_id": biome_id,
        "mask_nw": mask_nw,
        "mask_sw": mask_sw,
        "mask_east": mask_east,
        "mask_se": mask_se,
        "sw_basin_dist": sw_basin_dist,
        "crescent_bay_center": crescent_bay_center,
    }


# ==============================================================================
# 3. KẾT XUẤT BẢN ĐỒ ĐỊA HÌNH 3D (AAA TOPOGRAPHIC OVERWORLD ATLAS)
# ==============================================================================
def render_topographic_atlas(world_data: dict, output_path: str):
    U = world_data["U"]
    V = world_data["V"]
    land_mask = world_data["land_mask"]
    elev = world_data["elevation"]
    river_mask = world_data["river_mask"]
    delta_branches = world_data["delta_branches"]
    nw_delta = world_data["nw_delta"]
    mask_sw = world_data["mask_sw"]
    mask_east = world_data["mask_east"]
    mask_se = world_data["mask_se"]
    mask_nw = world_data["mask_nw"]
    sw_basin_dist = world_data["sw_basin_dist"]
    crescent_bay_center = world_data["crescent_bay_center"]

    h, w = elev.shape
    rgb = np.zeros((h, w, 3), dtype=np.float32)

    # 1. ĐẠI DƯƠNG SÂU & THỀM SAN HÔ NGỌC LAM (COASTAL REEF HALO)
    deep_ocean = np.array([8.0, 52.0, 78.0], dtype=np.float32)
    mid_ocean  = np.array([14.0, 96.0, 130.0], dtype=np.float32)
    mid_reef   = np.array([28.0, 172.0, 185.0], dtype=np.float32)
    shallow_reef = np.array([68.0, 224.0, 222.0], dtype=np.float32)

    bathymetry_lines = np.sin(fbm_2d(U * 18.0, V * 18.0, octaves=3, seed=512) * 22.0) * 0.08
    t_sea = np.clip(land_mask + bathymetry_lines, 0.0, 1.0)

    reef_t1 = smoothstep(0.12, 0.22, t_sea)[..., None]
    reef_t2 = smoothstep(0.22, 0.32, t_sea)[..., None]
    reef_t3 = smoothstep(0.32, 0.348, t_sea)[..., None]

    ocean_color = deep_ocean * (1.0 - reef_t1) + mid_ocean * reef_t1
    ocean_color = ocean_color * (1.0 - reef_t2) + mid_reef * reef_t2
    ocean_color = ocean_color * (1.0 - reef_t3) + shallow_reef * reef_t3

    # 2. ĐẤT LIỀN CƠ SỞ (THUNG LŨNG THẢO NGUYÊN & RỪNG NGUYÊN SINH)
    grass_valley = np.array([120.0, 156.0, 84.0], dtype=np.float32)
    lush_meadow  = np.array([92.0, 134.0, 62.0], dtype=np.float32)
    primeval_forest = np.array([32.0, 72.0, 32.0], dtype=np.float32)

    tex_noise = fbm_2d(U * 28.0, V * 28.0, octaves=5, seed=888)[..., None]
    land_color = grass_valley * (1.0 - tex_noise) + lush_meadow * tex_noise

    canopy_noise = fbm_2d(U * 14.0, V * 14.0, octaves=5, seed=999)
    is_crescent_forest = (
        (mask_east > 0.36)
        & (crescent_bay_center < 1.45)
        & (crescent_bay_center > 0.75)
        & (V > 0.44)
    )
    is_nw_forest = (mask_nw > 0.36) & (V > 0.22) & (V < 0.44) & (canopy_noise > 0.44)
    is_se_forest = (mask_se > 0.36)

    forest_mask = (is_crescent_forest | is_nw_forest | is_se_forest)[..., None]
    land_color = land_color * (1.0 - forest_mask * 0.90) + primeval_forest * (forest_mask * 0.90)

    # 3. CAO NGUYÊN MÙA THU (AUTUMN STEPPES PLATEAU)
    autumn_gold = np.array([232.0, 154.0, 64.0], dtype=np.float32)
    autumn_amber = np.array([220.0, 118.0, 36.0], dtype=np.float32)
    autumn_mix = autumn_gold * (1.0 - tex_noise) + autumn_amber * tex_noise

    autumn_weight = (
        smoothstep(0.35, 0.44, mask_east)
        * smoothstep(0.48, 0.28, V + (tex_noise[..., 0] - 0.5) * 0.08)
    )[..., None]
    land_color = land_color * (1.0 - autumn_weight) + autumn_mix * autumn_weight

    # 4. HOANG MẠC ĐẤT ĐỎ (TERRACOTTA DUNES)
    sand_tan = np.array([218.0, 180.0, 122.0], dtype=np.float32)
    terracotta_red = np.array([238.0, 128.0, 82.0], dtype=np.float32)
    dune_d = np.exp(-((sw_basin_dist / 0.55) ** 2))[..., None]
    desert_color = sand_tan * (1.0 - dune_d) + terracotta_red * dune_d

    sw_weight = smoothstep(0.34, 0.40, mask_sw)[..., None]
    land_color = land_color * (1.0 - sw_weight) + desert_color * sw_weight

    # 5. SƯỜN NÚI ĐÁ & ĐỈNH TUYẾT VĨNH CỬU
    rock_slate = np.array([96.0, 92.0, 84.0], dtype=np.float32)
    glacial_snow = np.array([252.0, 254.0, 255.0], dtype=np.float32)

    rock_weight = smoothstep(0.52, 0.66, elev)[..., None]
    snow_weight = (smoothstep(0.66, 0.78, elev) * smoothstep(0.38, 0.16, V) * smoothstep(0.16, 0.24, U))[..., None]

    land_color = land_color * (1.0 - rock_weight) + rock_slate * rock_weight
    land_color = land_color * (1.0 - snow_weight) + glacial_snow * snow_weight

    # 6. SÔNG NGÒI, HỒ NƯỚC & CHÂU THỔ ĐA NHÁNH
    river_azure = np.array([28.0, 128.0, 162.0], dtype=np.float32)
    delta_turquoise = np.array([58.0, 208.0, 206.0], dtype=np.float32)

    r_weight = smoothstep(0.24, 0.65, river_mask)[..., None]
    d_weight = smoothstep(0.22, 0.60, np.maximum(delta_branches, nw_delta))[..., None]

    land_color = land_color * (1.0 - r_weight) + river_azure * r_weight
    land_color = land_color * (1.0 - d_weight) + delta_turquoise * d_weight

    # 7. ĐỔ BÓNG NỔI 3D (AZIMUTHAL HILLSHADING TƯƠNG PHẢN CAO)
    dy, dx = np.gradient(elev * 92.0)
    micro_bump = fbm_2d(U * 85.0, V * 85.0, octaves=3, seed=777) * 0.75
    b_dy, b_dx = np.gradient(micro_bump)
    dx += b_dx * 0.40
    dy += b_dy * 0.40

    normal_z = np.ones_like(elev)
    norm_len = np.sqrt(dx * dx + dy * dy + normal_z * normal_z)
    nx, ny, nz = -dx / norm_len, -dy / norm_len, normal_z / norm_len

    # Nguồn sáng Mặt Trời hướng Tây-Bắc: 315 độ, độ cao 42 độ
    lx, ly, lz = -0.52, -0.52, 0.68
    shade = np.clip(nx * lx + ny * ly + nz * lz, 0.0, 1.0)
    hillshade = (0.55 + 0.65 * shade)[..., None]
    snow_highlight = np.clip((shade - 0.50) * 1.5, 0.0, 0.45)[..., None] * snow_weight

    hillshade = np.where(r_weight > 0.5, 0.95, hillshade)
    shaded_land = np.clip(land_color * hillshade + snow_highlight * 255.0, 0.0, 255.0)

    # 8. KẾT HỢP ĐẠI DƯƠNG VÀ ĐẤT LIỀN
    coast_blend = smoothstep(0.34, 0.362, land_mask)[..., None]
    rgb = ocean_color * (1.0 - coast_blend) + shaded_land * coast_blend

    # 9. KHUNG VIỀN CỔ ĐIỂN
    img = Image.fromarray(rgb.astype(np.uint8), mode="RGB")
    img_bordered = ImageOps.expand(img, border=3, fill=(38, 44, 48))
    img_bordered = ImageOps.expand(img_bordered, border=15, fill=(238, 230, 212))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img_bordered.save(output_path, quality=96)
    print(f"[GCVL] Đã lưu bản đồ thế giới đa lục địa tại: {output_path}")

    # Tự động đồng bộ sang tài nguyên game
    for target_asset in ["assets/sprites/world_atlas.png", "assets/sprites/world_overview_macro.png"]:
        try:
            Path(target_asset).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(output_path, target_asset)
            print(f"[GCVL] Đã đồng bộ sang tài nguyên: {target_asset}")
        except Exception as e:
            print(f"[GCVL] Không thể sao chép sang {target_asset}: {e}")

    return img_bordered


# ==============================================================================
# 4. XUẤT TỆP DỮ LIỆU THẾ GIỚI 200x200 CHO ENGINE 3D/2D (main.py)
# ==============================================================================
def export_world_json(output_json_path: str = "stone_age_world_200x200.json"):
    grid_data = generate_primeval_world(width=200, height=200, seed=2026)

    biome_names = {
        0: "deep_ocean",
        1: "coastal_reef_halo",
        2: "meandering_river",
        3: "primeval_forest_valley",
        4: "autumn_steppes_plateau",
        5: "terracotta_dunes",
        6: "glacial_alpine_massif",
        7: "sanctuary_island",
    }

    payload = {
        "world_name": "Primeval Reach - Multi-Continent Archipelago",
        "grid_size": [200, 200],
        "biome_legend": biome_names,
        "elevation": np.round(grid_data["elevation"], 4).tolist(),
        "biome_id": grid_data["biome_id"].tolist(),
        "river_mask": (grid_data["river_mask"] > 0.40).astype(int).tolist(),
    }

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"[GCVL] Đã xuất dữ liệu lưới 200x200 tại: {output_json_path}")


if __name__ == "__main__":
    world = generate_primeval_world(width=1440, height=810, seed=2026)
    render_topographic_atlas(world, "debug_outputs/primeval_world_atlas.png")
    export_world_json("stone_age_world_200x200.json")
