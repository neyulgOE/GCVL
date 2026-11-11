"""
tools/run_phase1_to_5.py
Thực thi liên hoàn Phase 1 -> Phase 5 và xuất bộ ảnh nghiệm thu Phase 5:
- soil.png (Bản đồ 7 loại thổ nhưỡng pha trộn mềm + bóng đổ địa hình)
- biome.png (Bản đồ 11 quần xã sinh vật chuyển tiếp mềm + mạng lưới sông hồ)
- validation_report_phase5.json
"""

import json
import os
import numpy as np
from PIL import Image

from world.config.world_config import WorldConfig
from world.generation.landmass_generator import LandmassGenerator
from world.generation.geology_generator import GeologyGenerator
from world.generation.terrain_generator import TerrainGenerator
from world.generation.climate_generator import ClimateGenerator
from world.generation.hydrology_generator import HydrologyGenerator
from world.generation.soil_generator import SoilGenerator, SOIL_PALETTE_RGB
from world.generation.biome_generator import BiomeGenerator
from world.data.world_validator import WorldValidator


def save_soil_png(landmass, terrain, hydrology, soil, path: str) -> None:
    """Kết xuất bản đồ 7 lớp đất (soil.png) với nội suy trọng số mềm và bóng đổ sườn dốc."""
    h, w = landmass.landmask.shape
    palette = np.zeros((8, 3), dtype=np.float32)
    for s_code, col in SOIL_PALETTE_RGB.items():
        palette[s_code] = col

    rgb = np.tensordot(soil.soil_weights, palette, axes=([-1], [0]))

    # Phủ nhẹ Hillshading để nhìn rõ mối liên hệ giữa Địa hình và Loại đất
    shade = (0.68 + 0.42 * terrain.shaded_relief)[:, :, None]
    rgb = np.where(landmass.landmask[:, :, None], rgb * shade, rgb)

    # Hiển thị đại dương & sông hồ
    sea = ~landmass.landmask
    d = landmass.bathymetry
    rgb[:, :, 0] = np.where(sea, 88.0 * (1.0 - d) + 18.0 * d, rgb[:, :, 0])
    rgb[:, :, 1] = np.where(sea, 160.0 * (1.0 - d) + 56.0 * d, rgb[:, :, 1])
    rgb[:, :, 2] = np.where(sea, 188.0 * (1.0 - d) + 96.0 * d, rgb[:, :, 2])

    rgb[hydrology.river_mask] = (42, 118, 172)
    rgb[hydrology.lake_mask] = (54, 136, 188)

    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB").save(path, "PNG")


def save_biome_png(landmass, terrain, hydrology, biome, path: str) -> None:
    """Kết xuất bản đồ 11 Quần xã chuyển tiếp mềm (biome.png) trên nền Shaded Relief."""
    rgb = biome.blended_biome_rgb.astype(np.float32)

    # Tích hợp ánh sáng nổi khối 3D (Relief Shading)
    shade = (0.62 + 0.52 * terrain.shaded_relief)[:, :, None]
    rgb = np.where(landmass.landmask[:, :, None], rgb * shade, rgb)

    # Đại dương theo độ sâu Bathymetry
    sea = ~landmass.landmask
    d = landmass.bathymetry
    rgb[:, :, 0] = np.where(sea, 102.0 * (1.0 - d) + 16.0 * d, rgb[:, :, 0])
    rgb[:, :, 1] = np.where(sea, 178.0 * (1.0 - d) + 60.0 * d, rgb[:, :, 1])
    rgb[:, :, 2] = np.where(sea, 204.0 * (1.0 - d) + 102.0 * d, rgb[:, :, 2])

    # Sông ngòi & Hồ nước ngọt / Hồ nội lưu
    rgb[hydrology.river_mask] = (38, 114, 176)
    rgb[hydrology.lake_mask & (~hydrology.endorheic_lake_mask)] = (48, 134, 194)
    rgb[hydrology.endorheic_lake_mask] = (68, 158, 166)

    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB").save(path, "PNG")


def run_phase1_to_5(output_dir: str = "debug_outputs/phase5") -> None:
    os.makedirs(output_dir, exist_ok=True)
    cfg = WorldConfig(seed=2026)

    # Thực thi chuỗi nhân quả Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5
    landmass = LandmassGenerator(cfg).generate()
    geology = GeologyGenerator(cfg).generate(landmass)
    terrain = TerrainGenerator(cfg).generate(landmass, geology)
    climate = ClimateGenerator(cfg).generate(landmass, geology, terrain)
    hydrology = HydrologyGenerator(cfg).generate(landmass, geology, terrain, climate)
    soil = SoilGenerator(cfg).generate(landmass, geology, terrain, climate, hydrology)
    biome = BiomeGenerator(cfg).generate(landmass, geology, terrain, climate, hydrology, soil)

    # Xuất ảnh nghiệm thu Phase 5
    save_soil_png(landmass, terrain, hydrology, soil, os.path.join(output_dir, "soil.png"))
    save_biome_png(landmass, terrain, hydrology, biome, os.path.join(output_dir, "biome.png"))

    # Kiểm định tự động
    validator = WorldValidator(cfg)
    rep_5 = validator.validate_phase5(landmass, soil, biome)

    with open(os.path.join(output_dir, "validation_report_phase5.json"), "w", encoding="utf-8") as f:
        json.dump(rep_5, f, indent=2, ensure_ascii=False)

    print(f"[HOÀN TẤT PHASE 5] Đã xuất soil.png & biome.png tại: {output_dir}")
    print(
        f" - Số loại đất hiện diện: {rep_5['present_soil_types']} / 7\n"
        f" - Số quần xã (Biomes) hiện diện: {rep_5['present_biomes']} / 11\n"
        f" - Tỷ lệ vùng chuyển tiếp mềm (Ecotone Transition): {rep_5['ecotone_transition_ratio']*100:.1f}%\n"
        f" - Kết quả Cổng Nghiệm thu Phase 5: {'ĐẠT (PASSED)' if rep_5['passed_gate'] else 'CẦN CÂN CHỈNH'}"
    )


if __name__ == "__main__":
    run_phase1_to_5()
