"""Deterministic vegetation layer for the canonical Primeval Reach map.

This module deliberately stays data-first: it derives a cool Paleolithic climate
baseline and vegetation layers from the canonical elevation/biome/water masks,
then places reproducible sprite instances for the 3D spectator renderer.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Sequence

import cv2
import numpy as np


BIOME_DEEP_OCEAN = 0
BIOME_REEF = 1
BIOME_RIVER = 2
BIOME_FOREST = 3
BIOME_STEPPE = 4
BIOME_TERRACOTTA = 5
BIOME_GLACIAL = 6
BIOME_SANCTUARY = 7


VEGETATION_LAYERS = (
    "emergent",
    "canopy",
    "understory",
    "shrub",
    "herb_ground",
    "litter_soil",
)

VEGETATION_LAYER_IDS = {name: index + 1 for index, name in enumerate(VEGETATION_LAYERS)}
VEGETATION_LAYER_LEGEND = {str(value): key for key, value in VEGETATION_LAYER_IDS.items()}

# `kind` is the renderer asset family. `species` is the worldbuilding label and
# remains useful to gameplay/data tools even when several species share a sprite
# family until a dedicated sprite sheet is added.
FLORA_KIND_IDS = {
    "tree_tundra": 1,
    "tree_steppe": 2,
    "tree_forest": 3,
    "tree_swamp": 4,
    "berry_bush": 5,
    "reed": 6,
    "mushroom": 7,
    "tuber": 8,
    "branch": 9,
    "soil_litter": 10,
    "copper_ore": 11,
}
FLORA_KIND_LEGEND = {str(value): key for key, value in FLORA_KIND_IDS.items()}


def _surface_slope(elevation: np.ndarray) -> np.ndarray:
    """Return a stable, normalized slope estimate for placement rules."""
    gy, gx = np.gradient(elevation.astype(np.float32))
    return np.clip(np.sqrt(gx * gx + gy * gy) * 4.5, 0.0, 1.0).astype(np.float32)


def build_ecology_maps(
    elevation: np.ndarray,
    biome_id: np.ndarray,
    river_mask: np.ndarray,
    land_mask: np.ndarray,
) -> Dict[str, np.ndarray]:
    """Build normalized temperature, moisture and vegetation-cover layers.

    The climate is intentionally cooler than a modern generic fantasy baseline,
    but not globally frozen: latitude, altitude, water proximity and biome keep
    southern wetlands/forest productive while the north remains tundra/taiga.
    """
    land_mask = np.asarray(land_mask).astype(bool)
    river_mask = np.asarray(river_mask).astype(bool)
    rows, cols = elevation.shape
    yy = np.linspace(0.0, 1.0, rows, dtype=np.float32)[:, None]
    elev_above_sea = np.clip((elevation - 0.35) / 0.65, 0.0, 1.0)

    # Cool Late-Paleolithic baseline: south is milder, altitude and northern
    # latitude cool the surface. Values are relative, not degrees Celsius.
    temperature = np.clip(
        0.14 + 0.58 * (yy ** 0.88) - 0.17 * elev_above_sea,
        0.02,
        0.86,
    )
    temperature = np.broadcast_to(temperature, elevation.shape).astype(np.float32).copy()
    temperature[biome_id == BIOME_GLACIAL] *= 0.72

    water_mask = (biome_id <= BIOME_RIVER) | river_mask.astype(bool)
    distance_to_water = cv2.distanceTransform(
        (~water_mask).astype(np.uint8), cv2.DIST_L2, 5
    )
    water_proximity = np.exp(-distance_to_water / 15.0).astype(np.float32)

    moisture_base = np.zeros_like(elevation, dtype=np.float32)
    moisture_base[biome_id == BIOME_FOREST] = 0.72
    moisture_base[biome_id == BIOME_STEPPE] = 0.43
    moisture_base[biome_id == BIOME_TERRACOTTA] = 0.16
    moisture_base[biome_id == BIOME_GLACIAL] = 0.34
    moisture_base[biome_id == BIOME_SANCTUARY] = 0.68
    moisture = np.clip(
        moisture_base + water_proximity * 0.22 + (temperature < 0.28) * 0.04,
        0.0,
        1.0,
    ).astype(np.float32)
    moisture[~land_mask] = 0.0

    # Stable low-frequency variation keeps vegetation clustered, not tiled.
    grid_y, grid_x = np.mgrid[0:rows, 0:cols]
    patch_noise = (
        0.5
        + 0.5
        * np.sin(grid_x * 0.117 + np.sin(grid_y * 0.031) * 2.4 + 1.7)
        * np.cos(grid_y * 0.083 - grid_x * 0.019)
    ).astype(np.float32)

    forest_weight = np.zeros_like(elevation, dtype=np.float32)
    forest_weight[biome_id == BIOME_FOREST] = 1.0
    forest_weight[biome_id == BIOME_SANCTUARY] = 0.78
    forest_weight[biome_id == BIOME_STEPPE] = 0.30
    forest_weight[biome_id == BIOME_GLACIAL] = 0.24

    canopy_cover = np.clip(
        forest_weight
        * (0.48 + 0.52 * patch_noise)
        * (0.42 + 0.58 * moisture)
        * (1.0 - 0.55 * elev_above_sea * (biome_id == BIOME_GLACIAL)),
        0.0,
        1.0,
    ) * land_mask
    shrub_cover = np.clip(
        (0.34 * forest_weight + 0.48 * (biome_id == BIOME_STEPPE) + 0.34 * (biome_id == BIOME_SANCTUARY))
        * (0.42 + 0.58 * patch_noise)
        * (0.35 + 0.65 * moisture),
        0.0,
        1.0,
    ) * land_mask
    ground_cover = np.clip(
        (0.52 * forest_weight + 0.74 * (biome_id == BIOME_STEPPE) + 0.82 * water_proximity)
        * (0.45 + 0.55 * moisture),
        0.0,
        1.0,
    ) * land_mask
    vegetation_density = np.clip(
        canopy_cover * 0.52 + shrub_cover * 0.28 + ground_cover * 0.20,
        0.0,
        1.0,
    ).astype(np.float32)
    slope = _surface_slope(elevation)

    return {
        "elevation": elevation.astype(np.float32),
        "temperature": temperature,
        "moisture": moisture,
        "water_proximity": water_proximity,
        "canopy_cover": canopy_cover.astype(np.float32),
        "shrub_cover": shrub_cover.astype(np.float32),
        "ground_cover": ground_cover.astype(np.float32),
        "vegetation_density": vegetation_density,
        "slope": slope,
    }


def _poisson_place(
    *,
    eligible: np.ndarray,
    score: np.ndarray,
    occupancy: np.ndarray,
    radius: int,
    rng: np.random.Generator,
    probability: float,
    limit: int,
    make_instance,
    stride: int,
) -> int:
    """Place candidates with a cheap grid Poisson/occupancy constraint."""
    rows, cols = eligible.shape
    points = np.argwhere(eligible[::stride, ::stride])
    if len(points) == 0:
        return 0
    rng.shuffle(points)
    placed = 0
    for coarse_row, coarse_col in points:
        row = int(coarse_row * stride + stride // 2)
        col = int(coarse_col * stride + stride // 2)
        if row < 2 or row >= rows - 2 or col < 2 or col >= cols - 2:
            continue
        if not eligible[row, col] or rng.random() > min(1.0, probability * float(score[row, col])):
            continue
        y0, y1 = max(0, row - radius), min(rows, row + radius + 1)
        x0, x1 = max(0, col - radius), min(cols, col + radius + 1)
        if occupancy[y0:y1, x0:x1].any():
            continue
        occupancy[y0:y1, x0:x1] = True
        make_instance(row, col)
        placed += 1
        if placed >= limit:
            break
    return placed


def _append_instance(
    instances: List[Dict[str, float | int | str]],
    *,
    row: int,
    col: int,
    layer: str,
    species: str,
    kind: str,
    scale: float,
    rng: np.random.Generator,
) -> None:
    instances.append({
        "col": int(col),
        "row": int(row),
        "layer": layer,
        "layer_id": int(VEGETATION_LAYER_IDS[layer]),
        "species": species,
        "kind": kind,
        "scale": round(float(scale), 3),
        "rotation_deg": round(float(rng.uniform(-12.0, 12.0)), 2),
        "growth_stage": int(rng.integers(0, 3)),
    })


def spawn_vegetation_instances(
    biome_id: np.ndarray,
    land_mask: np.ndarray,
    ecology: Dict[str, np.ndarray],
    river_mask: np.ndarray,
    seed: int = 2026,
    stride: int = 4,
    max_instances: int = 1800,
) -> List[Dict[str, float | int | str]]:
    """Place a deterministic six-layer Paleolithic vegetation hierarchy.

    The map silhouette and ecological fields are inputs only. Placement is
    hierarchical: mature trees reserve space first, then understory, shrubs,
    herbs and litter fill the remaining habitat with progressively smaller
    occupancy radii. Open steppe remains intentionally available as a
    megafauna corridor.
    """
    rows, cols = biome_id.shape
    elevation = ecology.get("elevation", np.zeros_like(biome_id, dtype=np.float32))
    temperature = ecology["temperature"]
    moisture = ecology["moisture"]
    water_proximity = ecology["water_proximity"]
    canopy = ecology["canopy_cover"]
    shrub = ecology["shrub_cover"]
    ground = ecology["ground_cover"]
    slope = ecology.get("slope", _surface_slope(elevation))
    rng = np.random.default_rng(seed)
    instances: List[Dict[str, float | int | str]] = []

    land_mask = np.asarray(land_mask).astype(bool)
    river_mask = np.asarray(river_mask).astype(bool)
    b = biome_id.astype(np.int16)
    deep_forest = (b == BIOME_FOREST) & (canopy > 0.72) & (slope < 0.18)
    forest_or_sanctuary = np.isin(b, (BIOME_FOREST, BIOME_SANCTUARY))
    water_edge = water_proximity > 0.43
    # The broad low-cover steppe is intentionally left open for megafauna.
    megafauna_corridor = (b == BIOME_STEPPE) & (canopy < 0.18) & (slope < 0.22)
    protected_surface = land_mask & ~np.isin(b, (BIOME_REEF, BIOME_RIVER))
    occupied_canopy = np.zeros((rows, cols), dtype=bool)
    occupied_understory = np.zeros((rows, cols), dtype=bool)
    occupied_shrub = np.zeros((rows, cols), dtype=bool)
    occupied_ground = np.zeros((rows, cols), dtype=bool)
    occupied_litter = np.zeros((rows, cols), dtype=bool)

    def add(row: int, col: int, layer: str, species: str, kind: str, low: float, high: float) -> None:
        _append_instance(
            instances,
            row=row,
            col=col,
            layer=layer,
            species=species,
            kind=kind,
            scale=float(rng.uniform(low, high)),
            rng=rng,
        )

    # 1. Emergent trees: only the deepest forest/sanctuary pockets, spaced wide.
    emergent_eligible = (
        protected_surface & deep_forest & ~water_edge & (b != BIOME_GLACIAL)
    ) | (
        protected_surface & (b == BIOME_SANCTUARY) & (canopy > 0.70) & (slope < 0.14)
    )
    _poisson_place(
        eligible=emergent_eligible,
        score=np.clip(canopy * (1.0 - slope), 0.0, 1.0),
        occupancy=occupied_canopy,
        radius=max(4, stride + 1),
        rng=rng,
        probability=0.82,
        limit=max_instances // 15,
        stride=max(2, stride),
        make_instance=lambda row, col: add(
            row, col, "emergent", "ancient_giant_hardwood", "tree_forest", 1.12, 1.42
        ),
    )

    # 2. Canopy: respect the glacial altitude ceiling and desert/oasis rule.
    glacial_tree = (b == BIOME_GLACIAL) & (elevation <= 0.65) & (temperature < 0.48)
    forest_tree = (b == BIOME_FOREST) & (canopy > 0.47) & (slope < 0.30)
    # Only the higher-cover pockets become groves; the rest stays open for
    # mammoth/bison movement and long sight lines.
    steppe_grove = (b == BIOME_STEPPE) & (canopy > 0.18) & ~megafauna_corridor
    sanctuary_tree = (b == BIOME_SANCTUARY) & (canopy > 0.42)
    terracotta_oasis = (b == BIOME_TERRACOTTA) & water_edge & (moisture > 0.34) & (slope < 0.22)
    canopy_eligible = protected_surface & (glacial_tree | forest_tree | steppe_grove | sanctuary_tree | terracotta_oasis)
    canopy_score = np.clip(0.30 + canopy * 0.85 - slope * 0.35, 0.0, 1.0)
    # Keep a sparse but visible snow-pine belt in the low glacial foothills;
    # steep/high cells remain excluded by the elevation rule above.
    canopy_score[glacial_tree] = np.clip(0.52 + canopy[glacial_tree] * 0.40, 0.0, 1.0)

    def add_canopy(row: int, col: int) -> None:
        biome = int(b[row, col])
        near_water = float(water_proximity[row, col])
        if biome == BIOME_GLACIAL:
            species, kind = "boreal_snow_pine", "tree_tundra"
        elif biome == BIOME_STEPPE:
            species, kind = "autumn_golden_birch", "tree_steppe"
        elif biome == BIOME_SANCTUARY and near_water > 0.54:
            species, kind = "nipa_palm_wetland", "tree_swamp"
        elif biome == BIOME_TERRACOTTA:
            species, kind = "oasis_ancient_palm", "tree_steppe"
        elif float(temperature[row, col]) < 0.36:
            species, kind = "cold_cycad_relict", "tree_tundra"
        else:
            species, kind = "primeval_fern_cycad", "tree_forest"
        add(row, col, "canopy", species, kind, 0.82, 1.18)

    _poisson_place(
        eligible=canopy_eligible,
        score=canopy_score,
        occupancy=occupied_canopy,
        radius=max(2, stride // 2 + 1),
        rng=rng,
        probability=0.72,
        limit=(max_instances * 3) // 10,
        stride=max(2, stride // 2),
        make_instance=add_canopy,
    )
    # The glacial foothill biome is a narrow, irregular band in the canonical
    # raster; a one-cell pass prevents the coarse candidate lattice from
    # accidentally erasing its lowland snow-pine ecology.
    _poisson_place(
        eligible=glacial_tree & ~occupied_canopy,
        score=canopy_score,
        occupancy=occupied_canopy,
        radius=2,
        rng=rng,
        probability=0.86,
        limit=max(6, max_instances // 80),
        stride=1,
        make_instance=add_canopy,
    )

    # Mature-tree shadow/canopy neighborhoods become valid habitat for the
    # lower layers; this keeps understory spatially subordinate to the canopy.
    canopy_shadow = cv2.dilate(occupied_canopy.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    understory_eligible = protected_surface & (forest_or_sanctuary | (b == BIOME_STEPPE)) & (canopy_shadow | water_edge)
    _poisson_place(
        eligible=understory_eligible,
        score=np.clip(0.25 + moisture * 0.80 + water_proximity * 0.18, 0.0, 1.0),
        occupancy=occupied_understory,
        radius=2,
        rng=rng,
        probability=0.58,
        limit=(max_instances * 7) // 40,
        stride=max(2, stride - 1),
        make_instance=lambda row, col: add(
            row, col,
            "understory",
            "wild_berry_understory" if float(temperature[row, col]) > 0.30 else "dwarf_boreal_shrub",
            "berry_bush" if float(water_proximity[row, col]) < 0.68 else "reed",
            0.58,
            0.92,
        ),
    )

    # 4. Shrubs concentrate at forest edges and occur in offset growth stages.
    forest_mask = (b == BIOME_FOREST) | (b == BIOME_SANCTUARY)
    forest_edge = cv2.morphologyEx(forest_mask.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8)) > 0
    shrub_eligible = protected_surface & (forest_edge | ((b == BIOME_STEPPE) & ~megafauna_corridor)) & (shrub > 0.24)
    _poisson_place(
        eligible=shrub_eligible,
        score=np.clip(shrub * (0.60 + 0.45 * moisture), 0.0, 1.0),
        occupancy=occupied_shrub,
        radius=1,
        rng=rng,
        probability=0.68,
        limit=(max_instances * 2) // 15,
        stride=max(2, stride - 1),
        make_instance=lambda row, col: add(
            row, col, "shrub", "wild_berry_bush", "berry_bush", 0.68, 1.02
        ),
    )

    # 5. Herbs/ground flora favor damp shade, stream banks and cold forest floor.
    ground_eligible = protected_surface & (ground > 0.22) & (
        (moisture > 0.48) | water_edge | (forest_or_sanctuary & canopy_shadow)
    )

    def add_ground(row: int, col: int) -> None:
        near_water = float(water_proximity[row, col])
        if near_water > 0.62:
            species, kind = "river_reed_grass", "reed"
        elif float(moisture[row, col]) > 0.66:
            species, kind = "wet_moss_mushroom_patch", "mushroom"
        else:
            species, kind = "wild_tuber_herb", "tuber"
        add(row, col, "herb_ground", species, kind, 0.45, 0.78)

    _poisson_place(
        eligible=ground_eligible,
        score=np.clip(0.30 + ground * 0.78 + moisture * 0.20, 0.0, 1.0),
        occupancy=occupied_ground,
        radius=1,
        rng=rng,
        probability=0.48,
        limit=(max_instances * 13) // 60,
        stride=max(2, stride - 1),
        make_instance=add_ground,
    )

    # 6. Litter/soil is data-first. Only the branch family is currently drawn
    # by the 3D renderer; clay/ore remain queryable gameplay instances.
    litter_eligible = protected_surface & (canopy_shadow | water_edge | (slope > 0.30))

    def add_litter(row: int, col: int) -> None:
        if float(slope[row, col]) > 0.48 and int(b[row, col]) in (BIOME_FOREST, BIOME_TERRACOTTA):
            species, kind = "exposed_copper_ore", "copper_ore"
        elif float(water_proximity[row, col]) > 0.66:
            species, kind = "stream_clay_deposit", "soil_litter"
        else:
            species, kind = "fallen_dry_branch", "branch"
        add(row, col, "litter_soil", species, kind, 0.42, 0.84)

    _poisson_place(
        eligible=litter_eligible,
        score=np.clip(0.25 + moisture * 0.55 + canopy_shadow * 0.28, 0.0, 1.0),
        occupancy=occupied_litter,
        radius=1,
        rng=rng,
        probability=0.34,
        limit=(max_instances * 13) // 120,
        stride=max(2, stride - 1),
        make_instance=add_litter,
    )

    # Keep output deterministic and bounded regardless of future layer tuning.
    instances.sort(key=lambda item: (int(item["row"]), int(item["col"]), int(item["layer_id"])))
    return instances[:max_instances]


def flora_instances_to_arrays(instances: Sequence[Mapping[str, float | int | str]]) -> Dict[str, np.ndarray]:
    """Convert JSON-friendly flora records into compact WorldData arrays."""
    count = len(instances)
    xy = np.zeros((count, 2), dtype=np.int32)
    elevation = np.zeros(count, dtype=np.float32)
    layer_id = np.zeros(count, dtype=np.uint8)
    species = np.zeros(count, dtype=np.uint16)
    kind_id = np.zeros(count, dtype=np.uint8)
    scale = np.ones(count, dtype=np.float32)
    rotation = np.zeros(count, dtype=np.float32)
    growth_stage = np.zeros(count, dtype=np.int8)
    species_names: Dict[str, int] = {}
    for index, item in enumerate(instances):
        layer = str(item["layer"])
        species_name = str(item["species"])
        if species_name not in species_names:
            species_names[species_name] = len(species_names) + 1
        xy[index] = (int(item["col"]), int(item["row"]))
        layer_id[index] = int(item.get("layer_id", VEGETATION_LAYER_IDS[layer]))
        species[index] = species_names[species_name]
        kind_id[index] = FLORA_KIND_IDS.get(str(item["kind"]), 0)
        scale[index] = float(item.get("scale", 1.0))
        rotation[index] = float(item.get("rotation_deg", 0.0))
        growth_stage[index] = int(item.get("growth_stage", 0))
    return {
        "flora_xy": xy,
        "flora_layer_id": layer_id,
        "flora_species_id": species,
        "flora_kind_id": kind_id,
        "flora_scale": scale,
        "flora_rotation_deg": rotation,
        "flora_growth_stage": growth_stage,
        "flora_species_names": np.array(list(species_names.keys()), dtype="U64"),
    }


def flora_instances_from_arrays(world_data: Mapping[str, np.ndarray]) -> List[Dict[str, float | int | str]]:
    """Rehydrate persisted WorldData flora arrays for the 3D renderer."""
    required = ("flora_xy", "flora_layer_id", "flora_kind_id", "flora_scale")
    if not all(key in world_data for key in required):
        return []
    xy = np.asarray(world_data["flora_xy"])
    layer_ids = np.asarray(world_data["flora_layer_id"])
    kind_ids = np.asarray(world_data["flora_kind_id"])
    scales = np.asarray(world_data["flora_scale"])
    rotations = np.asarray(world_data.get("flora_rotation_deg", np.zeros(len(xy))))
    stages = np.asarray(world_data.get("flora_growth_stage", np.zeros(len(xy))))
    species_ids = np.asarray(world_data.get("flora_species_id", np.zeros(len(xy))))
    species_names = [str(value) for value in np.asarray(world_data.get("flora_species_names", []))]
    records = []
    for index, (col, row) in enumerate(xy):
        layer_id = int(layer_ids[index])
        kind_id = int(kind_ids[index])
        species_id = int(species_ids[index]) if index < len(species_ids) else 0
        species_name = species_names[species_id - 1] if 0 < species_id <= len(species_names) else "flora_instance"
        records.append({
            "col": int(col),
            "row": int(row),
            "layer_id": layer_id,
            "layer": VEGETATION_LAYER_LEGEND.get(str(layer_id), "litter_soil"),
            "species": species_name,
            "kind": FLORA_KIND_LEGEND.get(str(kind_id), ""),
            "scale": float(scales[index]),
            "rotation_deg": float(rotations[index]),
            "growth_stage": int(stages[index]),
        })
    return records
