"""
world/generation/ecology_generator.py
Phase 6: Mô phỏng Hệ sinh thái Đa tầng (24 loài Thực vật & 18 loài Động vật tiền sử),
tính toán Habitat Suitability Map, mật độ 6 tầng tán rừng và hành lang di cư tự nhiên.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any
import random
import numpy as np

from world.config.world_config import WorldConfig
from world.generation.landmass_generator import FastNoise2D, LandmassResult
from world.generation.terrain_generator import TerrainResult
from world.generation.climate_generator import ClimateResult
from world.generation.hydrology_generator import HydrologyResult
from world.generation.soil_generator import (
    SoilResult,
    SOIL_ROCKY,
    SOIL_PERMAFROST,
    SOIL_SANDY,
    SOIL_CLAY,
    SOIL_PEAT,
    SOIL_ALLUVIAL,
    SOIL_HUMUS,
)
from world.generation.biome_generator import (
    BiomeResult,
    BIOME_WATER,
    BIOME_ALPINE_ICE_SNOW,
    BIOME_TUNDRA,
    BIOME_BOREAL_TAIGA,
    BIOME_MIXED_FOREST,
    BIOME_TEMPERATE_DECIDUOUS,
    BIOME_MOIST_BAY_FOREST,
    BIOME_RIPARIAN_FOREST,
    BIOME_WETLAND_SWAMP,
    BIOME_TEMPERATE_MEADOW,
    BIOME_DRY_SAVANNA_STEPPE,
    BIOME_SEMI_ARID_DESERT,
)


@dataclass(frozen=True)
class FloraSpeciesSpec:
    species_id: str
    layer: str  # emergent | canopy | understory | shrub | herb | ground
    preferred_biomes: Tuple[int, ...]
    preferred_soils: Tuple[int, ...]
    temp_range: Tuple[float, float]
    moist_range: Tuple[float, float]
    cluster_strength: float = 0.65


@dataclass(frozen=True)
class FaunaSpeciesSpec:
    species_id: str
    guild: str  # megafauna_herbivore | medium_herbivore | omnivore | apex_predator | pack_predator | aquatic_semi | avian_ambient
    preferred_biomes: Tuple[int, ...]
    herd_size_range: Tuple[int, int]
    water_dependency: float  # [0..1] mức độ cần bám sát sông/hồ
    max_slope: float = 0.45


# =============================================================================
# DANH MỤC 24 LOÀI THỰC VẬT NGUYÊN SINH (12 loài từ assets/flora/* + 12 loài mở rộng)
# =============================================================================
FLORA_CATALOG: Tuple[FloraSpeciesSpec, ...] = (
    # --- Tầng Vượt tán & Tán chính (Emergent & Main Canopy Trees) ---
    FloraSpeciesSpec("giant_redwood_primeval", "emergent", (BIOME_MOIST_BAY_FOREST, BIOME_MIXED_FOREST), (SOIL_HUMUS, SOIL_ALLUVIAL), (0.38, 0.78), (0.55, 1.0), 0.80),
    FloraSpeciesSpec("boreal_spruce_pine", "canopy", (BIOME_BOREAL_TAIGA, BIOME_MIXED_FOREST, BIOME_TUNDRA), (SOIL_HUMUS, SOIL_ROCKY, SOIL_PERMAFROST), (0.15, 0.52), (0.35, 0.90), 0.75),
    FloraSpeciesSpec("ancient_broadleaf_oak", "canopy", (BIOME_TEMPERATE_DECIDUOUS, BIOME_MIXED_FOREST), (SOIL_HUMUS, SOIL_CLAY), (0.42, 0.78), (0.45, 0.88), 0.72),
    FloraSpeciesSpec("silver_birch_grove", "canopy", (BIOME_MIXED_FOREST, BIOME_BOREAL_TAIGA, BIOME_RIPARIAN_FOREST), (SOIL_HUMUS, SOIL_ALLUVIAL), (0.28, 0.65), (0.45, 0.90), 0.68),
    FloraSpeciesSpec("weeping_riparian_willow", "canopy", (BIOME_RIPARIAN_FOREST, BIOME_WETLAND_SWAMP), (SOIL_ALLUVIAL, SOIL_PEAT), (0.32, 0.85), (0.68, 1.0), 0.70),
    FloraSpeciesSpec("swamp_bald_cypress", "canopy", (BIOME_WETLAND_SWAMP, BIOME_MOIST_BAY_FOREST), (SOIL_PEAT, SOIL_ALLUVIAL), (0.48, 0.92), (0.75, 1.0), 0.78),
    FloraSpeciesSpec("steppe_acacia_thorn", "canopy", (BIOME_DRY_SAVANNA_STEPPE, BIOME_TEMPERATE_MEADOW), (SOIL_CLAY, SOIL_SANDY), (0.50, 0.95), (0.15, 0.48), 0.55),
    # --- Tầng Dưới tán & Cổ thực vật (Understory) ---
    FloraSpeciesSpec("tree_fern_cycad", "understory", (BIOME_MOIST_BAY_FOREST, BIOME_RIPARIAN_FOREST, BIOME_WETLAND_SWAMP), (SOIL_HUMUS, SOIL_ALLUVIAL, SOIL_PEAT), (0.50, 0.95), (0.62, 1.0), 0.74),
    FloraSpeciesSpec("dwarf_subpolar_juniper", "understory", (BIOME_TUNDRA, BIOME_ALPINE_ICE_SNOW, BIOME_BOREAL_TAIGA), (SOIL_PERMAFROST, SOIL_ROCKY), (0.08, 0.36), (0.20, 0.75), 0.62),
    FloraSpeciesSpec("arid_joshua_yucca", "understory", (BIOME_SEMI_ARID_DESERT, BIOME_DRY_SAVANNA_STEPPE), (SOIL_SANDY, SOIL_ROCKY), (0.55, 1.0), (0.02, 0.30), 0.52),
    # --- Tầng Cây bụi & Quả mọng (Shrub Layer - Tích hợp assets/flora/*) ---
    FloraSpeciesSpec("elderberry", "shrub", (BIOME_TEMPERATE_DECIDUOUS, BIOME_MIXED_FOREST, BIOME_RIPARIAN_FOREST), (SOIL_HUMUS, SOIL_ALLUVIAL), (0.38, 0.76), (0.48, 0.88), 0.66),
    FloraSpeciesSpec("bramble", "shrub", (BIOME_TEMPERATE_MEADOW, BIOME_MIXED_FOREST, BIOME_DRY_SAVANNA_STEPPE), (SOIL_HUMUS, SOIL_CLAY, SOIL_ROCKY), (0.34, 0.82), (0.30, 0.75), 0.64),
    FloraSpeciesSpec("cloudberry", "shrub", (BIOME_TUNDRA, BIOME_BOREAL_TAIGA, BIOME_WETLAND_SWAMP), (SOIL_PERMAFROST, SOIL_PEAT), (0.12, 0.44), (0.50, 0.98), 0.68),
    FloraSpeciesSpec("arid_sagebrush_scrub", "shrub", (BIOME_SEMI_ARID_DESERT, BIOME_DRY_SAVANNA_STEPPE), (SOIL_SANDY, SOIL_CLAY, SOIL_ROCKY), (0.45, 0.98), (0.04, 0.35), 0.60),
    # --- Tầng Thảm cỏ & Thảo mộc (Herb Layer - Tích hợp assets/flora/*) ---
    FloraSpeciesSpec("cattail", "herb", (BIOME_WETLAND_SWAMP, BIOME_RIPARIAN_FOREST), (SOIL_PEAT, SOIL_ALLUVIAL), (0.28, 0.90), (0.78, 1.0), 0.82),
    FloraSpeciesSpec("taro", "herb", (BIOME_MOIST_BAY_FOREST, BIOME_RIPARIAN_FOREST, BIOME_WETLAND_SWAMP), (SOIL_ALLUVIAL, SOIL_PEAT, SOIL_HUMUS), (0.52, 0.95), (0.68, 1.0), 0.72),
    FloraSpeciesSpec("einkorn", "herb", (BIOME_TEMPERATE_MEADOW, BIOME_DRY_SAVANNA_STEPPE), (SOIL_HUMUS, SOIL_CLAY, SOIL_ALLUVIAL), (0.38, 0.82), (0.28, 0.65), 0.76),
    FloraSpeciesSpec("flax", "herb", (BIOME_TEMPERATE_MEADOW, BIOME_RIPARIAN_FOREST), (SOIL_HUMUS, SOIL_ALLUVIAL, SOIL_CLAY), (0.36, 0.78), (0.40, 0.78), 0.70),
    FloraSpeciesSpec("burdock", "herb", (BIOME_MIXED_FOREST, BIOME_TEMPERATE_DECIDUOUS, BIOME_TEMPERATE_MEADOW), (SOIL_HUMUS, SOIL_CLAY), (0.35, 0.75), (0.42, 0.80), 0.60),
    FloraSpeciesSpec("garlic", "herb", (BIOME_TEMPERATE_DECIDUOUS, BIOME_MIXED_FOREST, BIOME_DRY_SAVANNA_STEPPE), (SOIL_HUMUS, SOIL_ROCKY, SOIL_CLAY), (0.35, 0.78), (0.32, 0.72), 0.62),
    FloraSpeciesSpec("herb", "herb", (BIOME_TEMPERATE_MEADOW, BIOME_MIXED_FOREST, BIOME_BOREAL_TAIGA), (SOIL_HUMUS, SOIL_ALLUVIAL), (0.28, 0.78), (0.38, 0.82), 0.65),
    # --- Tầng Mặt đất, Nấm & Địa y (Ground / Moss / Fungi Layer) ---
    FloraSpeciesSpec("mushroom", "ground", (BIOME_MIXED_FOREST, BIOME_TEMPERATE_DECIDUOUS, BIOME_MOIST_BAY_FOREST, BIOME_BOREAL_TAIGA), (SOIL_HUMUS, SOIL_PEAT), (0.25, 0.82), (0.58, 0.98), 0.70),
    FloraSpeciesSpec("cavefungi", "ground", (BIOME_ALPINE_ICE_SNOW, BIOME_TUNDRA, BIOME_BOREAL_TAIGA), (SOIL_ROCKY, SOIL_PEAT), (0.05, 0.48), (0.45, 0.95), 0.75),
    FloraSpeciesSpec("arctic_reindeer_lichen", "ground", (BIOME_TUNDRA, BIOME_ALPINE_ICE_SNOW), (SOIL_PERMAFROST, SOIL_ROCKY), (0.02, 0.32), (0.15, 0.85), 0.72),
)


# =============================================================================
# DANH MỤC 18 LOÀI ĐỘNG VẬT HOANG DÃ TIỀN SỬ (MEGAFAUNA & AMBIENT FAUNA)
# =============================================================================
FAUNA_CATALOG: Tuple[FaunaSpeciesSpec, ...] = (
    # --- Thú ăn cỏ Khổng lồ & Đi theo đàn lớn (Megafauna & Herd Herbivores) ---
    FaunaSpeciesSpec("woolly_mammoth", "megafauna_herbivore", (BIOME_TUNDRA, BIOME_ALPINE_ICE_SNOW, BIOME_BOREAL_TAIGA), (4, 8), 0.45, 0.35),
    FaunaSpeciesSpec("woolly_rhino", "megafauna_herbivore", (BIOME_TUNDRA, BIOME_DRY_SAVANNA_STEPPE, BIOME_TEMPERATE_MEADOW), (2, 4), 0.40, 0.32),
    FaunaSpeciesSpec("ancient_bison", "megafauna_herbivore", (BIOME_TEMPERATE_MEADOW, BIOME_DRY_SAVANNA_STEPPE), (6, 14), 0.65, 0.38),
    FaunaSpeciesSpec("megaloceros_elk", "medium_herbivore", (BIOME_TEMPERATE_MEADOW, BIOME_MIXED_FOREST, BIOME_RIPARIAN_FOREST), (5, 10), 0.60, 0.42),
    FaunaSpeciesSpec("reindeer_caribou", "medium_herbivore", (BIOME_TUNDRA, BIOME_BOREAL_TAIGA), (7, 15), 0.40, 0.48),
    FaunaSpeciesSpec("wild_steppe_horse", "medium_herbivore", (BIOME_TEMPERATE_MEADOW, BIOME_DRY_SAVANNA_STEPPE), (5, 12), 0.55, 0.36),
    FaunaSpeciesSpec("musk_ox", "medium_herbivore", (BIOME_TUNDRA, BIOME_ALPINE_ICE_SNOW), (4, 9), 0.30, 0.50),
    FaunaSpeciesSpec("steppe_saiga_antelope", "medium_herbivore", (BIOME_DRY_SAVANNA_STEPPE, BIOME_SEMI_ARID_DESERT), (6, 14), 0.25, 0.38),
    FaunaSpeciesSpec("giant_ground_sloth", "megafauna_herbivore", (BIOME_MOIST_BAY_FOREST, BIOME_TEMPERATE_DECIDUOUS, BIOME_RIPARIAN_FOREST), (2, 4), 0.55, 0.35),
    # --- Động vật Ăn tạp & Cỡ nhỏ (Omnivores & Small Herbivores) ---
    FaunaSpeciesSpec("wild_boar", "omnivore", (BIOME_TEMPERATE_DECIDUOUS, BIOME_MIXED_FOREST, BIOME_RIPARIAN_FOREST), (4, 9), 0.65, 0.45),
    FaunaSpeciesSpec("arctic_mountain_hare", "medium_herbivore", (BIOME_TUNDRA, BIOME_BOREAL_TAIGA, BIOME_TEMPERATE_MEADOW), (5, 12), 0.25, 0.55),
    # --- Thú Săn Mồi Đỉnh Chóp & Theo Đàn (Apex & Pack Predators) ---
    FaunaSpeciesSpec("sabertooth_smilodon", "apex_predator", (BIOME_TEMPERATE_MEADOW, BIOME_DRY_SAVANNA_STEPPE, BIOME_MOIST_BAY_FOREST), (2, 4), 0.50, 0.52),
    FaunaSpeciesSpec("dire_wolf", "pack_predator", (BIOME_BOREAL_TAIGA, BIOME_MIXED_FOREST, BIOME_TEMPERATE_MEADOW, BIOME_TUNDRA), (4, 9), 0.50, 0.55),
    FaunaSpeciesSpec("cave_bear", "apex_predator", (BIOME_BOREAL_TAIGA, BIOME_ALPINE_ICE_SNOW, BIOME_MIXED_FOREST), (1, 3), 0.45, 0.62),
    FaunaSpeciesSpec("steppe_cave_lion", "apex_predator", (BIOME_DRY_SAVANNA_STEPPE, BIOME_SEMI_ARID_DESERT, BIOME_TEMPERATE_MEADOW), (2, 5), 0.45, 0.45),
    # --- Thủy sinh, Bán thủy sinh & Chim săn mồi (Aquatic, Semi-Aquatic & Avian) ---
    FaunaSpeciesSpec("marsh_crocodile", "aquatic_semi", (BIOME_WETLAND_SWAMP, BIOME_RIPARIAN_FOREST, BIOME_MOIST_BAY_FOREST), (3, 7), 0.95, 0.20),
    FaunaSpeciesSpec("giant_river_beaver", "aquatic_semi", (BIOME_RIPARIAN_FOREST, BIOME_WETLAND_SWAMP, BIOME_MIXED_FOREST), (4, 8), 0.92, 0.28),
    FaunaSpeciesSpec("prehistoric_salmon_shoal", "aquatic_semi", (BIOME_WATER, BIOME_RIPARIAN_FOREST), (8, 20), 1.00, 0.25),
)


@dataclass
class EcologyResult:
    vegetation_density: np.ndarray           # Mật độ thảm thực vật tổng hợp [0..1]
    canopy_cover: np.ndarray                 # Độ che phủ tầng cây gỗ lớn [0..1]
    shrub_cover: np.ndarray                  # Độ che phủ tầng cây bụi & quả mọng [0..1]
    herb_ground_cover: np.ndarray            # Độ che phủ tầng thảo mộc, rêu & nấm [0..1]
    dominant_flora_idx: np.ndarray           # Chỉ số loài thực vật chiếm ưu thế tại mỗi ô (int16)
    flora_suitability: Dict[str, np.ndarray] # Bản đồ phù hợp sinh cảnh cho 24 loài cây
    fauna_suitability: Dict[str, np.ndarray] # Bản đồ phù hợp sinh cảnh cho 18 loài thú
    wildlife_corridor_score: np.ndarray      # Hành lang di cư tự nhiên của thú lớn [0..1]
    spawned_wildlife_herds: List[Dict[str, Any]] = field(default_factory=list)


class EcologyGenerator:
    def __init__(self, config: WorldConfig) -> None:
        self.cfg = config
        self.patch_noise = FastNoise2D(seed=config.seed + 4111)
        self.canopy_noise = FastNoise2D(seed=config.seed + 5227)

    def generate(
        self,
        landmass: LandmassResult,
        terrain: TerrainResult,
        climate: ClimateResult,
        hydrology: HydrologyResult,
        soil: SoilResult,
        biome: BiomeResult,
    ) -> EcologyResult:
        h, w = self.cfg.height, self.cfg.width
        land = landmass.landmask
        water_surface = (~land) | hydrology.river_mask | hydrology.lake_mask

        ny, nx = np.meshgrid(
            np.linspace(0.0, 1.0, h, dtype=np.float32),
            np.linspace(0.0, 1.0, w, dtype=np.float32),
            indexing="ij",
        )
        patch_fbm = self.patch_noise.fbm_grid(nx, ny, octaves=5, base_scale=8.5)
        canopy_fbm = self.canopy_noise.fbm_grid(nx + 2.3, ny + 5.1, octaves=4, base_scale=11.0)

        # 1. Tính toán Mật độ 3 Tầng Thực vật (Canopy, Shrub, Herb/Ground)
        bw = biome.biome_weights
        forest_weight = (
            bw[:, :, BIOME_BOREAL_TAIGA]
            + bw[:, :, BIOME_MIXED_FOREST]
            + bw[:, :, BIOME_TEMPERATE_DECIDUOUS]
            + bw[:, :, BIOME_MOIST_BAY_FOREST]
            + bw[:, :, BIOME_RIPARIAN_FOREST] * 0.90
            + bw[:, :, BIOME_WETLAND_SWAMP] * 0.55
        )
        open_weight = (
            bw[:, :, BIOME_TEMPERATE_MEADOW]
            + bw[:, :, BIOME_DRY_SAVANNA_STEPPE] * 0.75
            + bw[:, :, BIOME_TUNDRA] * 0.50
        )

        canopy_cover = np.clip(
            forest_weight * (0.55 + 0.65 * canopy_fbm) * soil.soil_fertility * (1.0 - terrain.slope * 0.7),
            0.0,
            1.0,
        ) * (~water_surface)

        shrub_cover = np.clip(
            (forest_weight * 0.45 + open_weight * 0.65 + biome.ecotone_factor * 0.35)
            * (0.45 + 0.55 * patch_fbm)
            * soil.soil_moisture,
            0.0,
            1.0,
        ) * (~water_surface)

        herb_ground_cover = np.clip(
            (open_weight * 0.85 + forest_weight * 0.50 + bw[:, :, BIOME_WETLAND_SWAMP] * 0.90)
            * (0.50 + 0.50 * patch_fbm)
            * (0.35 + 0.65 * soil.soil_moisture),
            0.0,
            1.0,
        ) * (~water_surface)

        vegetation_density = np.clip(
            canopy_cover * 0.52 + shrub_cover * 0.28 + herb_ground_cover * 0.20,
            0.0,
            1.0,
        ).astype(np.float32)

        # 2. Tính Habitat Suitability Map cho toàn bộ 24 loài thực vật
        flora_suitability: Dict[str, np.ndarray] = {}
        flora_stack = np.zeros((h, w, len(FLORA_CATALOG)), dtype=np.float32)

        for idx, spec in enumerate(FLORA_CATALOG):
            b_match = np.zeros((h, w), dtype=np.float32)
            for b_id in spec.preferred_biomes:
                b_match += bw[:, :, b_id]

            s_match = np.zeros((h, w), dtype=np.float32)
            for s_id in spec.preferred_soils:
                s_match += soil.soil_weights[:, :, s_id]

            t_min, t_max = spec.temp_range
            t_mid = 0.5 * (t_min + t_max)
            t_span = max(0.05, 0.5 * (t_max - t_min))
            t_score = np.clip(1.0 - np.abs(climate.temperature - t_mid) / t_span, 0.0, 1.0)

            m_min, m_max = spec.moist_range
            m_mid = 0.5 * (m_min + m_max)
            m_span = max(0.05, 0.5 * (m_max - m_min))
            m_score = np.clip(1.0 - np.abs(soil.soil_moisture - m_mid) / m_span, 0.0, 1.0)

            suit = (
                b_match * 0.45
                + s_match * 0.25
                + t_score * 0.15
                + m_score * 0.15
            ) * (0.65 + 0.35 * patch_fbm) * (~water_surface)

            suit_clipped = np.clip(suit, 0.0, 1.0).astype(np.float32)
            flora_suitability[spec.species_id] = suit_clipped
            flora_stack[:, :, idx] = suit_clipped

        dominant_flora_idx = np.where(
            ~water_surface,
            np.argmax(flora_stack, axis=-1),
            -1,
        ).astype(np.int16)

        # 3. Tính Hành lang Di cư Động vật (Wildlife Migration Corridor)
        #    Thú lớn ưu tiên di chuyển dọc theo thung lũng độ dốc thấp, gần nguồn nước ngọt và đồng cỏ/rìa rừng
        water_prox = np.exp(-soil.distance_to_water / 18.0)
        gentle_slope = np.clip(1.0 - terrain.slope * 1.8, 0.0, 1.0)
        corridor_score = np.clip(
            gentle_slope * (0.45 * water_prox + 0.35 * open_weight + 0.20 * biome.ecotone_factor) * (~water_surface),
            0.0,
            1.0,
        ).astype(np.float32)

        # 4. Tính Habitat Suitability & Khởi tạo các Đàn Động vật (18 loài, ~95 bầy đàn, >650 cá thể)
        fauna_suitability: Dict[str, np.ndarray] = {}
        spawned_herds: List[Dict[str, Any]] = []
        rng = random.Random(self.cfg.seed + 8803)

        for spec in FAUNA_CATALOG:
            b_match = np.zeros((h, w), dtype=np.float32)
            for b_id in spec.preferred_biomes:
                if b_id == BIOME_WATER:
                    b_match += hydrology.river_mask.astype(np.float32) + hydrology.lake_mask.astype(np.float32)
                else:
                    b_match += bw[:, :, b_id]

            slope_ok = np.clip((spec.max_slope - terrain.slope) / max(0.05, spec.max_slope), 0.0, 1.0)
            w_factor = (1.0 - spec.water_dependency) + spec.water_dependency * np.exp(-soil.distance_to_water / 14.0)

            valid_mask = (hydrology.river_mask | hydrology.lake_mask) if spec.species_id == "prehistoric_salmon_shoal" else (~water_surface)
            f_suit = np.clip(b_match * slope_ok * w_factor * valid_mask, 0.0, 1.0).astype(np.float32)
            fauna_suitability[spec.species_id] = f_suit

            # Lấy mẫu các tọa độ có mức độ phù hợp cao để sinh bầy đàn (6 - 8 đàn mỗi loài)
            high_cells = np.argwhere(f_suit >= 0.32)
            if high_cells.size == 0:
                high_cells = np.argwhere(f_suit >= 0.15)
            if len(high_cells) > 0:
                target_herds = 6 if spec.guild in ("megafauna_herbivore", "medium_herbivore") else 5
                chosen_indices = [rng.randrange(len(high_cells)) for _ in range(min(target_herds, len(high_cells)))]
                for h_idx in chosen_indices:
                    r_pos, c_pos = int(high_cells[h_idx, 0]), int(high_cells[h_idx, 1])
                    herd_count = rng.randint(spec.herd_size_range[0], spec.herd_size_range[1])
                    spawned_herds.append({
                        "species_id": spec.species_id,
                        "guild": spec.guild,
                        "world_col": c_pos,
                        "world_row": r_pos,
                        "count": herd_count,
                        "suitability": round(float(f_suit[r_pos, c_pos]), 3),
                        "biome_id": int(biome.primary_biome_id[r_pos, c_pos]),
                    })

        return EcologyResult(
            vegetation_density=vegetation_density,
            canopy_cover=canopy_cover.astype(np.float32),
            shrub_cover=shrub_cover.astype(np.float32),
            herb_ground_cover=herb_ground_cover.astype(np.float32),
            dominant_flora_idx=dominant_flora_idx,
            flora_suitability=flora_suitability,
            fauna_suitability=fauna_suitability,
            wildlife_corridor_score=corridor_score,
            spawned_wildlife_herds=spawned_herds,
        )
