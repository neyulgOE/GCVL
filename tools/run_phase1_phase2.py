"""
tools/run_phase1_phase2.py
Thực thi Cổng Nghiệm thu Phase 1 (Landmass & Bathymetry) & Phase 2 (Geology & Terrain).
Xuất 3 phương án silhouette lục địa từ 3 seed độc lập và bộ ảnh debug đầy đủ.
"""

import json
import os
import numpy as np
from PIL import Image

from world.config.world_config import WorldConfig
from world.generation.landmass_generator import LandmassGenerator
from world.generation.geology_generator import GeologyGenerator
from world.generation.terrain_generator import TerrainGenerator
from world.data.world_validator import WorldValidator


def save_grayscale_png(arr: np.ndarray, path: str) -> None:
    norm = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(norm, mode="L").save(path, "PNG")


def save_bathymetry_png(landmass, path: str) -> None:
    """Kết xuất dải màu độ sâu đại dương (Bathymetric Bands) và thềm lục địa."""
    h, w = landmass.landmask.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)

    # Đất nổi màu kem nhạt để nổi bật đường bờ biển và vịnh nội địa
    rgb[landmass.landmask] = (218, 212, 192)

    # Đại dương phân dải theo độ sâu bathymetry
    sea = ~landmass.landmask
    depth = landmass.bathymetry
    rgb[sea & (depth <= 0.18)] = (128, 198, 212)  # Thềm lục địa nông (Shallow Shelf)
    rgb[sea & (depth > 0.18) & (depth <= 0.45)] = (72, 152, 184)
    rgb[sea & (depth > 0.45) & (depth <= 0.72)] = (38, 108, 148)
    rgb[sea & (depth > 0.72)] = (18, 68, 108)     # Vực biển sâu (Abyssal Deep)

    Image.fromarray(rgb, mode="RGB").save(path, "PNG")


def save_shaded_relief_preview(landmass, terrain, path: str) -> None:
    """Kết xuất bản đồ nổi khối vật lý (Physical Shaded Relief Preview) cho Phase 2."""
    h, w = landmass.landmask.shape
    rgb = np.zeros((h, w, 3), dtype=np.float32)

    elev = terrain.final_heightmap
    shade = terrain.shaded_relief

    # Màu địa hình cơ sở theo độ cao (Hypsometric Tints)
    for r_idx, g_idx, b_idx, low, high, col_low, col_high in [
        (0, 1, 2, 0.38, 0.52, (96, 148, 78), (154, 178, 94)),    # Đồng bằng & Sườn thấp
        (0, 1, 2, 0.52, 0.70, (154, 178, 94), (172, 142, 98)),   # Cao nguyên & Đồi núi vừa
        (0, 1, 2, 0.70, 0.84, (172, 142, 98), (138, 132, 128)),  # Núi đá cao (Alpine Crags)
        (0, 1, 2, 0.84, 1.01, (138, 132, 128), (238, 242, 246)), # Đỉnh tuyết vĩnh cửu
    ]:
        mask = landmass.landmask & (elev >= low) & (elev < high)
        t = np.clip((elev - low) / max(1e-5, high - low), 0.0, 1.0)
        for ch in range(3):
            rgb[:, :, ch] = np.where(
                mask,
                col_low[ch] * (1.0 - t) + col_high[ch] * t,
                rgb[:, :, ch],
            )

    # Áp dụng ánh sáng nổi khối 3D (Hillshade Multiply + Highlight)
    lighting = 0.55 + 0.70 * shade
    for ch in range(3):
        rgb[:, :, ch] = np.where(landmass.landmask, rgb[:, :, ch] * lighting, rgb[:, :, ch])

    # Màu đại dương phân tầng độ sâu
    sea = ~landmass.landmask
    d = landmass.bathymetry
    rgb[:, :, 0] = np.where(sea, 110.0 * (1.0 - d) + 16.0 * d, rgb[:, :, 0])
    rgb[:, :, 1] = np.where(sea, 185.0 * (1.0 - d) + 64.0 * d, rgb[:, :, 1])
    rgb[:, :, 2] = np.where(sea, 205.0 * (1.0 - d) + 104.0 * d, rgb[:, :, 2])

    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB").save(path, "PNG")


def run_pipeline(output_root: str = "debug_outputs/experimental_phase1_2") -> None:
    os.makedirs(output_root, exist_ok=True)
    base_cfg = WorldConfig()
    reports = []

    for idx, candidate_seed in enumerate(base_cfg.candidate_seeds, start=1):
        cfg = WorldConfig(seed=candidate_seed)
        seed_dir = os.path.join(output_root, f"candidate_{idx}_seed_{candidate_seed}")
        os.makedirs(seed_dir, exist_ok=True)

        # Phase 1: Landmass & Bathymetry
        land_gen = LandmassGenerator(cfg)
        landmass = land_gen.generate()

        # Phase 2: Geology & Multi-layer Terrain
        geo_gen = GeologyGenerator(cfg)
        geology = geo_gen.generate(landmass)

        ter_gen = TerrainGenerator(cfg)
        terrain = ter_gen.generate(landmass, geology)

        # Kiểm định tự động
        validator = WorldValidator(cfg)
        report = validator.validate_phase1_and_phase2(landmass, terrain)
        reports.append(report)

        # Xuất bộ ảnh nghiệm thu Phase 1 & Phase 2
        save_grayscale_png(landmass.landmask.astype(np.float32), os.path.join(seed_dir, "landmask.png"))
        save_bathymetry_png(landmass, os.path.join(seed_dir, "bathymetry.png"))
        save_grayscale_png(terrain.final_heightmap, os.path.join(seed_dir, "heightmap.png"))
        save_grayscale_png(terrain.slope, os.path.join(seed_dir, "slope.png"))
        save_shaded_relief_preview(landmass, terrain, os.path.join(seed_dir, "shaded_relief.png"))

        # Copy ứng viên số 1 (seed mặc định 2026) ra thư mục gốc debug để tiện kiểm tra nhanh
        if idx == 1:
            save_grayscale_png(landmass.landmask.astype(np.float32), os.path.join(output_root, "landmask.png"))
            save_bathymetry_png(landmass, os.path.join(output_root, "bathymetry.png"))
            save_grayscale_png(terrain.final_heightmap, os.path.join(output_root, "heightmap.png"))
            save_grayscale_png(terrain.slope, os.path.join(output_root, "slope.png"))
            save_shaded_relief_preview(landmass, terrain, os.path.join(output_root, "shaded_relief.png"))

    report_path = os.path.join(output_root, "validation_report_phase1_2.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)

    print(f"[HOÀN TẤT PHASE 1 & 2] Đã xuất 3 phương án lục địa và báo cáo kiểm định tại: {output_root}")
    for r in reports:
        print(f" - Seed {r['seed']}: Land={r['land_ratio']*100:.1f}%, MainContinent={r['main_continent_share']*100:.1f}%, Pass={r['passed_gate']}")


if __name__ == "__main__":
    run_pipeline()
