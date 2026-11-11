"""
EXPERIMENTAL procedural validation pipeline.

This file is retained for debugging the old procedural `world/` package. It
is not the canonical map build and must not overwrite the current atlas.

Thực thi toàn bộ 7 Phase của kiến trúc Primeval Reach (Phase 1 -> Phase 7):
Xuất đầy đủ các tạo phẩm nghiệm thu Phase 6 & Phase 7:
- habitat.png (Bản đồ sinh cảnh & 18 loài động vật hoang dã)
- vegetation_density.png (Bản đồ mật độ 24 loài thực vật 6 tầng tán)
- world_atlas.png (Bản đồ thế giới vật lý nổi khối Physical Relief 1024x1024)
- local_patch_sample.json (Dữ liệu đồng bộ trực tiếp sang Local Map 80x80)
"""

import json
import os
import numpy as np

from world.config.world_config import WorldConfig
from world.generation.landmass_generator import LandmassGenerator
from world.generation.geology_generator import GeologyGenerator
from world.generation.terrain_generator import TerrainGenerator
from world.generation.climate_generator import ClimateGenerator
from world.generation.hydrology_generator import HydrologyGenerator
from world.generation.soil_generator import SoilGenerator
from world.generation.biome_generator import BiomeGenerator
from world.generation.ecology_generator import EcologyGenerator, FLORA_CATALOG, FAUNA_CATALOG
from world.atlas.atlas_renderer import PhysicalAtlasRenderer
from world.data.local_map_bridge import LocalMapBridge
from world.data.world_validator import WorldValidator


def run_all_phases(output_dir: str = "debug_outputs/experimental_phase6_7") -> None:
    os.makedirs(output_dir, exist_ok=True)
    cfg = WorldConfig(seed=2026)

    # 1. Chạy liên hoàn 6 tầng sinh thế giới (Phase 1 -> Phase 6)
    landmass = LandmassGenerator(cfg).generate()
    geology = GeologyGenerator(cfg).generate(landmass)
    terrain = TerrainGenerator(cfg).generate(landmass, geology)
    climate = ClimateGenerator(cfg).generate(landmass, geology, terrain)
    hydrology = HydrologyGenerator(cfg).generate(landmass, geology, terrain, climate)
    soil = SoilGenerator(cfg).generate(landmass, geology, terrain, climate, hydrology)
    biome = BiomeGenerator(cfg).generate(landmass, geology, terrain, climate, hydrology, soil)
    ecology = EcologyGenerator(cfg).generate(landmass, terrain, climate, hydrology, soil, biome)

    # 2. Kết xuất bộ ảnh nghiệm thu Phase 6 & Phase 7
    renderer = PhysicalAtlasRenderer(cfg)
    renderer.render_vegetation_density_png(
        landmass, hydrology, ecology, os.path.join(output_dir, "vegetation_density.png")
    )
    renderer.render_habitat_png(
        landmass, terrain, hydrology, biome, ecology, os.path.join(output_dir, "habitat.png")
    )
    atlas_out = os.path.join(output_dir, "world_atlas.png")
    renderer.render_world_atlas_png(
        landmass,
        terrain,
        climate,
        hydrology,
        soil,
        biome,
        ecology,
        atlas_out,
        upscale_factor=2,
    )
    # 3. Kiểm thử Cầu nối Local Map Bridge (Phase 7B) tại trung tâm lưu vực sông chính
    bridge = LocalMapBridge(cfg, landmass, terrain, climate, hydrology, soil, biome, ecology)
    local_patch = bridge.extract_local_patch(center_world_col=236, center_world_row=248)

    patch_summary = {
        "world_id": cfg.world_id,
        "seed": cfg.seed,
        "center_world_coord": [local_patch.center_world_col, local_patch.center_world_row],
        "world_bbox": list(local_patch.world_bbox),
        "local_resolution": [local_patch.local_cols, local_patch.local_rows],
        "water_tiles_count": len(local_patch.water_tiles),
        "flora_instances_spawned": len(local_patch.flora_instances),
        "fauna_herds_in_region": len(local_patch.fauna_spawns),
        "sample_flora": local_patch.flora_instances[:10],
        "sample_fauna": local_patch.fauna_spawns,
    }
    with open(os.path.join(output_dir, "local_patch_sample.json"), "w", encoding="utf-8") as f:
        json.dump(patch_summary, f, indent=2, ensure_ascii=False)

    # 4. Tổng hợp báo cáo kiểm định toàn trình (Phase 1 -> Phase 7)
    validator = WorldValidator(cfg)
    rep_1_2 = validator.validate_phase1_and_phase2(landmass, terrain)
    rep_3_4 = validator.validate_phase3_and_phase4(landmass, climate, hydrology)
    rep_5 = validator.validate_phase5(landmass, soil, biome)

    active_flora = sum(
        1 for spec in FLORA_CATALOG if float(np.max(ecology.flora_suitability[spec.species_id])) >= 0.25
    )
    active_fauna = len({h["species_id"] for h in ecology.spawned_wildlife_herds})
    total_animals = sum(h["count"] for h in ecology.spawned_wildlife_herds)

    rep_6_7 = {
        "total_flora_species_configured": len(FLORA_CATALOG),
        "active_flora_species_on_continent": active_flora,
        "total_fauna_species_configured": len(FAUNA_CATALOG),
        "active_fauna_species_spawned": active_fauna,
        "total_wildlife_herds": len(ecology.spawned_wildlife_herds),
        "total_individual_animals": total_animals,
        "local_bridge_flora_instances": len(local_patch.flora_instances),
        "local_bridge_water_tiles": len(local_patch.water_tiles),
        "passed_gate": bool(active_flora >= 22 and active_fauna >= 16 and len(local_patch.flora_instances) > 100),
    }

    master_report = {
        "phase_1_2": rep_1_2,
        "phase_3_4": rep_3_4,
        "phase_5": rep_5,
        "phase_6_7": rep_6_7,
    }
    with open(os.path.join(output_dir, "validation_report_full_pipeline.json"), "w", encoding="utf-8") as f:
        json.dump(master_report, f, indent=2, ensure_ascii=False)

    print(f"[HOÀN TẤT TOÀN BỘ 7 PHASE PRIMEVAL REACH] Tạo phẩm xuất tại: {output_dir}")
    print(
        f" - Đa dạng Thực vật: {active_flora}/{len(FLORA_CATALOG)} loài hoạt động (6 tầng tán)\n"
        f" - Đa dạng Động vật: {active_fauna}/{len(FAUNA_CATALOG)} loài ({len(ecology.spawned_wildlife_herds)} bầy đàn, {total_animals} cá thể)\n"
        f" - Đồng bộ Local Map (80x80): {len(local_patch.flora_instances)} cây/thảo mộc, {len(local_patch.fauna_spawns)} đàn thú trong vùng chọn\n"
        f" - Cổng Nghiệm thu Cuối cùng (Phase 6 & 7): {'ĐẠT (PASSED)' if rep_6_7['passed_gate'] else 'CẦN CÂN CHỈNH'}"
    )


if __name__ == "__main__":
    run_all_phases()
