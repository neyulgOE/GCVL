"""Deterministic vegetation layer for the canonical Primeval Reach map.

This module deliberately stays data-first: it derives a cool Paleolithic climate
baseline and vegetation layers from the canonical elevation/biome/water masks,
then places reproducible sprite instances for the 3D spectator renderer.
"""

from __future__ import annotations

from typing import Dict, List

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

    return {
        "temperature": temperature,
        "moisture": moisture,
        "water_proximity": water_proximity,
        "canopy_cover": canopy_cover.astype(np.float32),
        "shrub_cover": shrub_cover.astype(np.float32),
        "ground_cover": ground_cover.astype(np.float32),
        "vegetation_density": vegetation_density,
    }


def spawn_vegetation_instances(
    biome_id: np.ndarray,
    land_mask: np.ndarray,
    ecology: Dict[str, np.ndarray],
    river_mask: np.ndarray,
    seed: int = 2026,
    stride: int = 4,
    max_instances: int = 1800,
) -> List[Dict[str, float | int | str]]:
    """Place deterministic canopy, shrub and ground sprite instances."""
    rows, cols = biome_id.shape
    temperature = ecology["temperature"]
    moisture = ecology["moisture"]
    water_proximity = ecology["water_proximity"]
    canopy = ecology["canopy_cover"]
    shrub = ecology["shrub_cover"]
    ground = ecology["ground_cover"]
    rng = np.random.default_rng(seed)
    instances: List[Dict[str, float | int | str]] = []

    for row in range(2, rows - 2, stride):
        for col in range(2, cols - 2, stride):
            if not land_mask[row, col] or biome_id[row, col] in (BIOME_REEF, BIOME_RIVER):
                continue

            b_id = int(biome_id[row, col])
            local_canopy = float(canopy[row, col])
            local_shrub = float(shrub[row, col])
            local_ground = float(ground[row, col])
            near_water = float(water_proximity[row, col])
            cold = float(temperature[row, col]) < 0.42

            tree_probability = {
                BIOME_FOREST: 0.42,
                BIOME_STEPPE: 0.16,
                BIOME_GLACIAL: 0.13,
                BIOME_SANCTUARY: 0.34,
                BIOME_TERRACOTTA: 0.015,
            }.get(b_id, 0.0) * local_canopy

            if rng.random() < tree_probability:
                if b_id == BIOME_GLACIAL or (b_id == BIOME_FOREST and cold):
                    kind = "tree_tundra"
                elif b_id == BIOME_SANCTUARY and near_water > 0.52:
                    kind = "tree_swamp"
                elif b_id == BIOME_STEPPE:
                    kind = "tree_steppe"
                else:
                    kind = "tree_forest"
                instances.append({
                    "col": col,
                    "row": row,
                    "kind": kind,
                    "layer": "canopy",
                    "scale": round(float(rng.uniform(0.82, 1.18)), 3),
                })
                continue

            # Understory is more common than canopy and survives in open cold
            # steppe as berry scrub rather than turning the whole map into forest.
            if rng.random() < 0.18 * local_shrub:
                instances.append({
                    "col": col,
                    "row": row,
                    "kind": "berry_bush",
                    "layer": "shrub",
                    "scale": round(float(rng.uniform(0.70, 1.00)), 3),
                })
            elif near_water > 0.62 and rng.random() < 0.20 * local_ground:
                instances.append({
                    "col": col,
                    "row": row,
                    "kind": "reed",
                    "layer": "ground",
                    "scale": round(float(rng.uniform(0.58, 0.86)), 3),
                })
            elif b_id in (BIOME_FOREST, BIOME_SANCTUARY) and float(moisture[row, col]) > 0.58 and rng.random() < 0.12:
                instances.append({
                    "col": col,
                    "row": row,
                    "kind": "mushroom",
                    "layer": "ground",
                    "scale": round(float(rng.uniform(0.48, 0.72)), 3),
                })

            if len(instances) >= max_instances:
                return instances

    return instances
