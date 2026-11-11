"""
tools/run_phase1_to_4.py
Chạy liên hoàn từ Phase 1 -> Phase 4 và xuất bộ ảnh nghiệm thu:
- Phase 3: temperature.png, precipitation.png, climate.png
- Phase 4: watershed.png, water_map.png, rivers.geojson, kèm bản đồ tổng hợp relief + sông hồ.
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
from world.data.world_validator import WorldValidator


def save_temperature_png(landmass, climate, path: str) -> None:
    """Bản đồ nhiệt độ: Xanh băng (Bắc Cao) -> Xanh lục (Ôn đới) -> Vàng cam/Đỏ ấm (Phương Nam)."""
    h, w = climate.temperature.shape
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    t = climate.temperature

    # Gradient nhiệt độ trực quan
    rgb[:, :, 0] = np.clip(t * 1.45, 0.0, 1.0) * 245.0
    rgb[:, :, 1] = np.clip(1.0 - np.abs(t - 0.52) * 2.1, 0.15, 1.0) * 225.0
    rgb[:, :, 2] = np.clip((1.0 - t) * 1.35, 0.0, 1.0) * 245.0

    # Làm tối nhẹ vùng biển để nổi bật lục địa
    sea = ~landmass.landmask
    for ch in range(3):
        rgb[:, :, ch] = np.where(sea, rgb[:, :, ch] * 0.42, rgb[:, :, ch])

    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB").save(path, "PNG")


def save_precipitation_png(landmass, climate, path: str) -> None:
    """Bản đồ lượng mưa & Khuất mưa: Vàng đất khô hạn (Tây Nam) -> Xanh ngọc -> Xanh lam đậm (Mưa lớn)."""
    h, w = climate.precipitation.shape
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    p = climate.precipitation

    # Khô hạn (Nâu cam nhạt) -> Ẩm ướt (Xanh lam đậm)
    rgb[:, :, 0] = (1.0 - p) * 218.0 + p * 24.0
    rgb[:, :, 1] = (1.0 - p) * 172.0 + p * 118.0
    rgb[:, :, 2] = (1.0 - p) * 96.0 + p * 220.0

    sea = ~landmass.landmask
    rgb[sea] = (24, 52, 78)
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB").save(path, "PNG")


def save_climate_zones_png(landmass, climate, path: str) -> None:
    """Bản đồ 6 đới khí hậu của Primeval Reach."""
    palette = {
        0: (225, 236, 245),  # Hàn đới / Núi băng Bắc Cao
        1: (88, 148, 138),   # Cận cực ẩm (Tây Bắc)
        2: (112, 176, 92),   # Ôn đới ẩm (Đông Bắc & Trung tâm)
        3: (46, 128, 74),    # Cận nhiệt đới mưa ẩm quanh Vịnh Nội Địa
        4: (198, 182, 98),   # Thảo nguyên bán khô hạn
        5: (214, 134, 78),   # Vùng Khuất mưa Khô hạn Tây Nam (Rain Shadow Basin)
    }
    h, w = climate.climate_zones.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    for code, col in palette.items():
        rgb[climate.climate_zones == code] = col
    rgb[~landmass.landmask] = (28, 72, 108)
    Image.fromarray(rgb, mode="RGB").save(path, "PNG")


def save_watershed_png(landmass, hydrology, path: str) -> None:
    """Bản đồ phân định các Lưu vực sông (Watershed Basins) kèm mạng lưới dòng chảy."""
    h, w = hydrology.watershed_id.shape
    ws = hydrology.watershed_id
    rgb = np.zeros((h, w, 3), dtype=np.uint8)

    # Tô màu phân biệt từng lưu vực bằng hàm băm màu cố định
    r_col = ((ws * 73) % 155 + 75).astype(np.uint8)
    g_col = ((ws * 151) % 155 + 75).astype(np.uint8)
    b_col = ((ws * 211) % 155 + 75).astype(np.uint8)

    rgb[:, :, 0] = np.where(landmass.landmask, r_col, 22)
    rgb[:, :, 1] = np.where(landmass.landmask, g_col, 58)
    rgb[:, :, 2] = np.where(landmass.landmask, b_col, 92)

    # Vẽ đè sông và hồ lên trên lưu vực
    rgb[hydrology.river_mask] = (18, 52, 115)
    rgb[hydrology.lake_mask] = (48, 138, 204)
    rgb[hydrology.endorheic_lake_mask] = (92, 168, 178)

    Image.fromarray(rgb, mode="RGB").save(path, "PNG")


def save_water_map_png(landmass, terrain, hydrology, path: str) -> None:
    """
    Bản đồ Thủy văn tổng hợp (Water Map) trên nền địa hình nổi khối:
    Hiển thị rõ Hồ băng thượng nguồn, Sông phân cấp mở rộng về hạ lưu,
    Hồ Nội Lưu vùng khô hạn Tây Nam và Châu thổ cửa biển.
    """
    h, w = landmass.landmask.shape
    rgb = np.zeros((h, w, 3), dtype=np.float32)

    # Nền địa hình Shaded Relief trầm để tôn bật hệ thống thủy văn
    shade = 0.45 + 0.55 * terrain.shaded_relief
    elev = terrain.final_heightmap
    rgb[:, :, 0] = np.where(landmass.landmask, (118.0 + elev * 85.0) * shade, 24.0)
    rgb[:, :, 1] = np.where(landmass.landmask, (136.0 + elev * 65.0) * shade, 68.0)
    rgb[:, :, 2] = np.where(landmass.landmask, (104.0 + elev * 60.0) * shade, 108.0)

    # Đại dương theo dải độ sâu
    sea = ~landmass.landmask
    d = landmass.bathymetry
    rgb[:, :, 0] = np.where(sea, 96.0 * (1.0 - d) + 16.0 * d, rgb[:, :, 0])
    rgb[:, :, 1] = np.where(sea, 172.0 * (1.0 - d) + 58.0 * d, rgb[:, :, 1])
    rgb[:, :, 2] = np.where(sea, 198.0 * (1.0 - d) + 98.0 * d, rgb[:, :, 2])

    # Châu thổ cửa sông (Delta)
    rgb[hydrology.delta_mask] = (138, 178, 142)

    # Sông suối phân cấp (Suối nhỏ xanh sáng -> Sông cái xanh đậm)
    rgb[hydrology.stream_order == 1] = (112, 188, 224)
    rgb[hydrology.stream_order == 2] = (78, 162, 214)
    rgb[hydrology.stream_order == 3] = (48, 134, 196)
    rgb[hydrology.river_mask & (hydrology.stream_order >= 4)] = (26, 102, 172)

    # Hồ nước ngọt thoát nước (Exorheic Lakes) vs. Hồ Nội Lưu mặn/lợ Tây Nam (Endorheic Lake)
    rgb[hydrology.lake_mask & (~hydrology.endorheic_lake_mask)] = (42, 128, 192)
    rgb[hydrology.endorheic_lake_mask] = (64, 158, 164)

    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB").save(path, "PNG")


def run_phase1_to_4(output_dir: str = "debug_outputs/phase3_4") -> None:
    os.makedirs(output_dir, exist_ok=True)
    cfg = WorldConfig(seed=2026)

    # 1. Chạy nối tiếp Phase 1 -> Phase 2 -> Phase 3 -> Phase 4
    landmass = LandmassGenerator(cfg).generate()
    geology = GeologyGenerator(cfg).generate(landmass)
    terrain = TerrainGenerator(cfg).generate(landmass, geology)
    climate = ClimateGenerator(cfg).generate(landmass, geology, terrain)
    hydrology = HydrologyGenerator(cfg).generate(landmass, geology, terrain, climate)

    # 2. Xuất bộ ảnh nghiệm thu Phase 3
    save_temperature_png(landmass, climate, os.path.join(output_dir, "temperature.png"))
    save_precipitation_png(landmass, climate, os.path.join(output_dir, "precipitation.png"))
    save_climate_zones_png(landmass, climate, os.path.join(output_dir, "climate.png"))

    # 3. Xuất bộ ảnh nghiệm thu Phase 4 & tệp rivers.geojson
    save_watershed_png(landmass, hydrology, os.path.join(output_dir, "watershed.png"))
    save_water_map_png(landmass, terrain, hydrology, os.path.join(output_dir, "water_map.png"))

    geojson_path = os.path.join(output_dir, "rivers.geojson")
    geojson_payload = {
        "type": "FeatureCollection",
        "metadata": {
            "world_id": cfg.world_id,
            "seed": cfg.seed,
            "resolution": [cfg.width, cfg.height],
        },
        "features": hydrology.river_features,
    }
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson_payload, f, indent=2)

    # 4. Chạy bộ kiểm định tự động cho cả 4 Phase
    validator = WorldValidator(cfg)
    rep_1_2 = validator.validate_phase1_and_phase2(landmass, terrain)
    rep_3_4 = validator.validate_phase3_and_phase4(landmass, climate, hydrology)

    full_report = {"phase_1_2": rep_1_2, "phase_3_4": rep_3_4}
    with open(os.path.join(output_dir, "validation_report_phase1_to_4.json"), "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2, ensure_ascii=False)

    print(f"[HOÀN TẤT PHASE 3 & 4] Dữ liệu đã được xuất tại: {output_dir}")
    print(
        f" - Độ tương phản Khuất mưa (Tây Bắc vs Tây Nam): {rep_3_4['rain_shadow_contrast']:.3f}\n"
        f" - Số nhánh sông trích xuất: {rep_3_4['river_branches_count']} nhánh\n"
        f" - Số đoạn sông chảy ngược dốc (Vi phạm): {rep_3_4['uphill_river_violations']} / {rep_3_4['total_river_segments_checked']}\n"
        f" - Kết quả Cổng Nghiệm thu Phase 3 & 4: {'ĐẠT (PASSED)' if rep_3_4['passed_gate'] else 'CẦN CÂN CHỈNH'}"
    )


if __name__ == "__main__":
    run_phase1_to_4()

