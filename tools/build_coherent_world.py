"""LEGACY: coherent procedural overworld generator.

This is deliberately data-first: the same continuous elevation field drives
coastline, watersheds, climate and biome selection before any pixels are
painted.  The PNG is only a cartographic view of that field.
"""

from __future__ import annotations

import math
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    from tools.build_palworld_masterpiece import FastFbmNoise
except ModuleNotFoundError:  # Running this file through the tools directory.
    from build_palworld_masterpiece import FastFbmNoise


def _smoothstep(edge0, edge1, value):
    t = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _normalise(values):
    lo = np.percentile(values, 3.0)
    hi = np.percentile(values, 97.0)
    return np.clip((values - lo) / max(1e-6, hi - lo), 0.0, 1.0)


def _curve_mask(u, v, x_curve, v0, v1, width):
    active = (v >= v0) & (v <= v1)
    return active & (np.abs(u - x_curve) <= width)


def generate_coherent_overworld(
    width=1024,
    height=1024,
    seed=2026,
    output_path="debug_outputs/legacy_coherent_world.png",
):
    """Compatibility wrapper that mirrors the canonical atlas without rebuilding it."""
    try:
        from tools.generate_primeval_world import load_canonical_atlas
    except ModuleNotFoundError:
        from generate_primeval_world import load_canonical_atlas

    image = load_canonical_atlas().convert("RGB")
    target_size = (int(width), int(height))
    if image.size != target_size:
        image = image.resize(target_size, Image.Resampling.LANCZOS)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, "PNG")
    return image


def _legacy_generate_coherent_overworld(
    width=1024,
    height=1024,
    seed=2026,
    output_path="debug_outputs/legacy_coherent_world.png",
):
    """Legacy elliptical generator kept only for reference."""
    W, H = int(width), int(height)
    noise = FastFbmNoise(seed)
    y_px, x_px = np.mgrid[0:H, 0:W]
    u = x_px / float(max(1, W - 1))
    v = y_px / float(max(1, H - 1))

    # One primary continental body with a gently indented coast. Two small
    # offshore islands are kept separate instead of making every biome an island.
    body = 1.0 - (((u - 0.50) / 0.43) ** 2 + ((v - 0.51) / 0.46) ** 2)
    body += (noise.fbm(W, H, 0.006, octaves=4, seed_offset=11) - 0.5) * 0.18
    body += (noise.fbm(W, H, 0.025, octaves=3, seed_offset=12) - 0.5) * 0.055
    body -= 0.14 * np.maximum(0.0, u - 0.72) * np.maximum(0.0, v - 0.42)
    main_land = body > 0.0

    island_north = (((u - 0.18) / 0.065) ** 2 + ((v - 0.14) / 0.055) ** 2) < 1.0
    island_south = (((u - 0.82) / 0.085) ** 2 + ((v - 0.84) / 0.065) ** 2) < 1.0
    is_land = main_land | island_north | island_south

    # Continuous elevation: a northern mountain spine feeds a central basin,
    # while the south/east coast falls away gradually.
    ridge_x = 0.34 + 0.22 * v + 0.035 * np.sin(v * math.pi * 5.0)
    ridge_distance = np.abs(u - ridge_x)
    north_ridge = np.exp(-((ridge_distance / 0.075) ** 2)) * np.exp(-((v - 0.30) / 0.34) ** 2)
    western_ridge = np.exp(-(((u - 0.20) / 0.11) ** 2 + ((v - 0.42) / 0.33) ** 2)) * 0.45
    rolling = noise.fbm(W, H, 0.018, octaves=5, persistence=0.55, seed_offset=30)
    fine = noise.fbm(W, H, 0.055, octaves=3, persistence=0.45, seed_offset=31)
    coast_falloff = np.clip(body, 0.0, 1.0)
    elevation = (
        0.08
        + 0.12 * (1.0 - v)
        + 0.54 * north_ridge
        + 0.22 * western_ridge
        + 0.15 * rolling
        + 0.05 * fine
        + 0.10 * coast_falloff
    )
    # The small islands have low coastal shelves and one central rise.
    island_height = np.maximum(0.0, 1.0 - np.minimum(
        ((u - 0.18) / 0.065) ** 2 + ((v - 0.14) / 0.055) ** 2,
        ((u - 0.82) / 0.085) ** 2 + ((v - 0.84) / 0.065) ** 2,
    ))
    elevation = np.maximum(elevation, 0.10 + 0.28 * island_height)
    elevation = np.clip(elevation, 0.0, 1.0)

    # Rivers follow descending corridors from the mountain spine to the coast.
    main_x = 0.50 + 0.075 * np.sin(v * math.pi * 3.0 + 0.5) - 0.10 * (v - 0.25)
    river_main = _curve_mask(u, v, main_x, 0.16, 0.96, 0.008 + 0.008 * v)

    west_t = np.clip((v - 0.16) / 0.40, 0.0, 1.0)
    west_x = 0.28 + (main_x - 0.28) * west_t + 0.018 * np.sin(v * 17.0)
    river_west = _curve_mask(u, v, west_x, 0.16, 0.56, 0.0045 + 0.004 * west_t)

    east_t = np.clip((v - 0.22) / 0.34, 0.0, 1.0)
    east_x = 0.70 + (main_x - 0.70) * east_t + 0.015 * np.sin(v * 15.0 + 1.7)
    river_east = _curve_mask(u, v, east_x, 0.22, 0.56, 0.004 + 0.003 * east_t)

    # The southern lowlands split into several distributaries. They remain
    # connected to the main watershed instead of reading as decorative lines.
    delta_t = np.clip((v - 0.67) / 0.29, 0.0, 1.0)
    delta_west_x = main_x - 0.16 * delta_t + 0.025 * np.sin(v * 13.0)
    delta_east_x = main_x + 0.14 * delta_t + 0.022 * np.sin(v * 15.0 + 2.1)
    delta_south_x = main_x + 0.035 * np.sin(v * 18.0 + 0.3)
    river_delta_west = _curve_mask(u, v, delta_west_x, 0.67, 0.96, 0.004 + 0.004 * delta_t)
    river_delta_east = _curve_mask(u, v, delta_east_x, 0.67, 0.96, 0.004 + 0.004 * delta_t)
    river_delta_south = _curve_mask(u, v, delta_south_x, 0.67, 0.98, 0.003 + 0.003 * delta_t)

    river_mask = (
        river_main | river_west | river_east |
        river_delta_west | river_delta_east | river_delta_south
    ) & is_land
    # Carve channels into the same field used for hillshade and 3D elevation.
    # The channel floor itself is monotonic downstream; this prevents a river
    # from visually climbing over a noisy ridge just because the spline does.
    main_t = np.clip((v - 0.16) / 0.80, 0.0, 1.0)
    main_profile = 0.055 + 0.39 * (1.0 - main_t) ** 1.15
    west_t = np.clip((v - 0.16) / 0.40, 0.0, 1.0)
    west_profile = 0.18 + 0.22 * (1.0 - west_t) ** 1.1
    east_t = np.clip((v - 0.22) / 0.34, 0.0, 1.0)
    east_profile = 0.19 + 0.18 * (1.0 - east_t) ** 1.1
    main_channel = river_main & is_land
    west_channel = river_west & is_land
    east_channel = river_east & is_land
    delta_channel = (river_delta_west | river_delta_east | river_delta_south) & is_land
    main_corridor = is_land & (v >= 0.145) & (v <= 0.97) & (np.abs(u - main_x) < 0.014)
    river_mask |= main_corridor
    elevation[main_channel] = main_profile[main_channel]
    elevation[west_channel] = west_profile[west_channel]
    elevation[east_channel] = east_profile[east_channel]
    elevation[delta_channel] = (0.065 + 0.025 * (1.0 - delta_t))[delta_channel]
    elevation[main_corridor] = main_profile[main_corridor]
    slope_y, slope_x = np.gradient(elevation)
    slope = np.hypot(slope_x, slope_y)

    # Macro regions are semantic geography, not arbitrary color quadrants.
    # Each region owns a climate target and an ecosystem. The noise only
    # breaks up its edges and surface; it cannot turn the whole continent into
    # one generic green biome.
    region_centers = np.array([
        [0.31, 0.20],  # northern glacial headwaters
        [0.20, 0.56],  # western dry steppe
        [0.49, 0.49],  # central river valley
        [0.72, 0.46],  # eastern primeval forest
        [0.70, 0.20],  # northeastern cool uplands
        [0.57, 0.78],  # southern wetland delta
    ], dtype=np.float32)
    region_scales = np.array([0.38, 0.34, 0.38, 0.32, 0.29, 0.34], dtype=np.float32)
    region_warp = noise.fbm(W, H, 0.012, octaves=4, persistence=0.55, seed_offset=44)
    region_scores = []
    for index, ((cx, cy), scale) in enumerate(zip(region_centers, region_scales)):
        distance = np.sqrt(((u - cx) / scale) ** 2 + ((v - cy) / scale) ** 2)
        local_warp = noise.fbm(W, H, 0.022, octaves=3, persistence=0.50, seed_offset=45 + index)
        score = -distance + (region_warp - 0.5) * 0.16 + (local_warp - 0.5) * 0.08
        region_scores.append(score)
    region_scores = np.stack(region_scores, axis=0)
    region = np.argmax(region_scores, axis=0).astype(np.uint8) + 1

    # Geography constrains the macro regions so the intended climate belts are
    # legible even where the coast/noise makes a narrow peninsula.
    region[is_land & (v < 0.235) & (u < 0.56)] = 1
    dry_edge = 0.34 + 0.045 * np.sin(v * math.pi * 3.4) + 0.025 * (v - 0.5)
    forest_edge = 0.61 - 0.045 * np.sin(v * math.pi * 2.7 + 0.6)
    delta_edge = 0.70 + 0.035 * np.sin(u * math.pi * 3.0 + 0.4) - 0.025 * np.maximum(0.0, u - 0.55)
    region[is_land & (u < dry_edge) & (v > 0.38)] = 2
    region[is_land & (u > forest_edge) & (v > 0.31) & (v < 0.69)] = 4
    region[is_land & (v > delta_edge)] = 6
    region[~is_land] = 0

    # Blur only the categorical base before applying local terrain detail.
    # This creates natural transition bands instead of hard Voronoi seams.
    region_base_values = np.array([0.0, 0.62, 0.18, 0.12, 0.23, 0.38, 0.08], dtype=np.float32)
    region_base = region_base_values[region]
    region_base = np.asarray(
        Image.fromarray(np.clip(region_base * 255.0, 0, 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(13.0)
        ),
        dtype=np.float32,
    ) / 255.0
    region_base = np.clip(region_base, 0.0, 1.0)

    # Climate follows latitude, height, region and hydrology. These targets
    # are deliberately explicit: glacier, dry steppe, valley, forest, cool
    # upland and delta must remain distinguishable in both data and pixels.
    river_distance = np.minimum.reduce([
        np.abs(u - main_x), np.abs(u - west_x), np.abs(u - east_x),
        np.abs(u - delta_west_x), np.abs(u - delta_east_x), np.abs(u - delta_south_x),
    ])
    humidity_noise = noise.fbm(W, H, 0.020, octaves=4, seed_offset=50)
    region_moisture = np.array([0.0, 0.46, 0.18, 0.62, 0.82, 0.54, 0.96], dtype=np.float32)[region]
    region_temperature = np.array([0.0, 0.14, 0.57, 0.56, 0.48, 0.32, 0.72], dtype=np.float32)[region]
    moisture = np.clip(
        0.45 * region_moisture
        + 0.18 * np.exp(-river_distance / 0.055)
        + 0.10 * np.maximum(0.0, v - 0.56)
        + 0.12 * humidity_noise
        - 0.09 * np.maximum(0.0, u - 0.65),
        0.0,
        1.0,
    )
    temperature = np.clip(
        0.48 * region_temperature
        + 0.22 * v
        + 0.12 * noise.fbm(W, H, 0.014, seed_offset=60)
        - 0.19 * elevation,
        0.0,
        1.0,
    )

    # 0 ocean, then six named regional ecosystems.
    biome = region.copy()
    biome[~is_land] = 0
    biome[river_mask] = 0

    # Bring the regional base back into the elevation field. The values are
    # smooth, so a dry plateau does not look like a pasted flat polygon.
    elevation = np.clip(
        0.62 * elevation + 0.24 * region_base + 0.08 * rolling,
        0.0,
        1.0,
    )
    elevation[main_channel] = main_profile[main_channel]
    elevation[west_channel] = west_profile[west_channel]
    elevation[east_channel] = east_profile[east_channel]
    elevation[delta_channel] = (0.065 + 0.025 * (1.0 - delta_t))[delta_channel]
    elevation[main_corridor] = main_profile[main_corridor]
    slope_y, slope_x = np.gradient(elevation)
    slope = np.hypot(slope_x, slope_y)

    # Cartographic rendering with restrained natural colors and continuous
    # hillshade. The labels/grid remain, but they describe natural features.
    land_img = Image.fromarray((is_land * 255).astype(np.uint8))
    shore_blur = np.asarray(land_img.filter(ImageFilter.GaussianBlur(5.0)), dtype=np.float32) / 255.0
    ocean_noise = noise.fbm(W, H, 0.045, octaves=3, seed_offset=70)
    rgb = np.zeros((H, W, 3), dtype=np.float32)
    rgb[:, :, 0] = 9.0 + ocean_noise * 6.0
    rgb[:, :, 1] = 26.0 + ocean_noise * 15.0
    rgb[:, :, 2] = 58.0 + ocean_noise * 22.0

    # Muted coastal shelf, without a neon reef ring.
    shelf = (~is_land) & (shore_blur > 0.035)
    shelf_t = shore_blur[shelf]
    rgb[shelf, 0] = 12.0 + 28.0 * shelf_t
    rgb[shelf, 1] = 58.0 + 78.0 * shelf_t
    rgb[shelf, 2] = 98.0 + 86.0 * shelf_t

    light_x, light_y, light_z = -0.45, -0.70, 0.56
    normal_x = -slope_x * 42.0
    normal_y = -slope_y * 42.0
    normal_z = np.ones_like(elevation)
    normal_len = np.sqrt(normal_x ** 2 + normal_y ** 2 + normal_z ** 2)
    hillshade = np.clip(
        0.76 + 0.34 * ((normal_x * light_x + normal_y * light_y + normal_z * light_z) / normal_len),
        0.52,
        1.12,
    )

    palette = {
        1: np.array([190.0, 201.0, 192.0]),  # glacial headwaters
        2: np.array([164.0, 139.0, 74.0]),   # dry western steppe
        3: np.array([112.0, 151.0, 76.0]),   # central river valley
        4: np.array([48.0, 101.0, 57.0]),    # eastern primeval forest
        5: np.array([112.0, 127.0, 93.0]),   # cool uplands
        6: np.array([53.0, 128.0, 107.0]),   # southern wetland delta
    }
    # Blend adjacent ecosystem colors over a narrow natural transition band.
    # The semantic region array remains categorical for gameplay, while the
    # atlas avoids the pasted-polygon look of hard Voronoi fills.
    soft_regions = []
    for kind in range(1, 7):
        region_mask = (biome == kind).astype(np.uint8) * 255
        blurred = np.asarray(
            Image.fromarray(region_mask).filter(ImageFilter.GaussianBlur(16.0)),
            dtype=np.float32,
        ) / 255.0
        soft_regions.append(blurred)
    soft_regions = np.stack(soft_regions, axis=0)
    soft_regions *= is_land[None, :, :]
    weight_total = np.sum(soft_regions, axis=0, keepdims=True)
    soft_regions = np.divide(
        soft_regions,
        np.maximum(weight_total, 1e-5),
        out=np.zeros_like(soft_regions),
        where=weight_total > 1e-5,
    )
    color_field = np.zeros((H, W, 3), dtype=np.float32)
    for kind, color in palette.items():
        color_field += soft_regions[kind - 1, :, :, None] * color[None, None, :]

    broad_texture = noise.fbm(W, H, 0.010, octaves=3, persistence=0.55, seed_offset=80)
    snow_texture = noise.fbm(W, H, 0.028, octaves=3, seed_offset=91)
    variation = (fine - 0.5) * 10.0 + (broad_texture - 0.5) * 22.0
    # Local ecosystem signatures: ochre steppe bands, dark forest canopy,
    # and a wetland mosaic of reeds, shallow water and mud.
    variation += soft_regions[1] * 14.0 * np.sin(v * math.pi * 19.0)
    variation -= soft_regions[3] * 20.0 * np.maximum(0.0, broad_texture - 0.50)
    variation += soft_regions[5] * 18.0 * (humidity_noise - 0.5)
    variation += soft_regions[0] * (snow_texture > 0.60) * 18.0
    for channel in range(3):
        rgb[:, :, channel][is_land] = np.clip(
            (color_field[:, :, channel][is_land] + variation[is_land]) * hillshade[is_land],
            0.0,
            255.0,
        )

    # Visible ecosystem structure: canopy clusters, glacial rock, dry grass
    # variation, and shallow pools in the delta. These are field-derived, not
    # arbitrary symbols pasted over the map.
    forest_noise = noise.fbm(W, H, 0.032, octaves=3, persistence=0.55, seed_offset=101)
    forest_dark = (biome == 4) & (forest_noise > 0.57)
    rgb[forest_dark] *= 0.77
    glacial_rock = (biome == 1) & (snow_texture < 0.44)
    rgb[glacial_rock] *= np.array([0.82, 0.86, 0.85])
    dry_grass = (biome == 2) & (broad_texture > 0.58)
    rgb[dry_grass] *= np.array([1.05, 0.96, 0.78])
    wetland_noise = noise.fbm(W, H, 0.026, octaves=3, persistence=0.55, seed_offset=103)
    wetland_pools = (biome == 6) & (elevation < 0.22) & (wetland_noise > 0.62) & (humidity_noise > 0.52)
    rgb[wetland_pools] = np.array([31.0, 105.0, 111.0]) * (0.85 + 0.12 * hillshade[wetland_pools, None])

    rgb[river_mask] = np.array([34.0, 112.0, 154.0]) * (0.88 + 0.10 * hillshade[river_mask, None])
    # Sandy, low-gradient river margins.
    river_img = Image.fromarray((river_mask * 255).astype(np.uint8))
    river_blur = np.asarray(river_img.filter(ImageFilter.GaussianBlur(9.0)), dtype=np.float32) / 255.0
    shore = is_land & (~river_mask) & (river_blur > 0.055) & (elevation < 0.36)
    shore_strength = np.clip((river_blur - 0.055) / 0.16, 0.0, 0.42)
    shore_strength *= shore
    shore_color = np.array([176.0, 157.0, 112.0]) * hillshade[:, :, None]
    rgb = rgb * (1.0 - shore_strength[:, :, None]) + shore_color * shore_strength[:, :, None]
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    # Region boundaries are subtle enough to feel geographic, but visible
    # enough that the atlas communicates where one ecosystem ends.
    boundary = np.zeros((H, W), dtype=bool)
    boundary[:-1, :] |= (region[:-1, :] != region[1:, :]) & is_land[:-1, :] & is_land[1:, :]
    boundary[:, :-1] |= (region[:, :-1] != region[:, 1:]) & is_land[:, :-1] & is_land[:, 1:]
    boundary_img = Image.fromarray((boundary * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    boundary_soft = np.asarray(boundary_img, dtype=np.float32) / 255.0
    boundary_color = np.array([52.0, 73.0, 61.0])
    rgb = np.asarray(image, dtype=np.float32)
    rgb = rgb * (1.0 - 0.22 * boundary_soft[:, :, None]) + boundary_color * (0.22 * boundary_soft[:, :, None])
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(image)

    grid_step = max(64, int(round(W / 12.0)))
    for gx in range(grid_step, W, grid_step):
        draw.line([(gx, 0), (gx, H)], fill=(82, 143, 171), width=1)
        draw.text((gx + 4, 6), str(round(gx / W * 120)), fill=(174, 211, 224), font=font)
    for gy in range(grid_step, H, grid_step):
        draw.line([(0, gy), (W, gy)], fill=(82, 143, 171), width=1)
        draw.text((6, gy + 4), str(round(gy / H * 120)), fill=(174, 211, 224), font=font)

    labels = [
        (190, 190, "GLACIAL HEADWATERS", "snowfields • alpine conifers"),
        (155, 560, "WESTERN DRY STEPPE", "grassland • scrub • exposed rock"),
        (430, 500, "CENTRAL RIVER VALLEY", "floodplain • willow • meadow"),
        (700, 450, "PRIMEVAL EASTERN FOREST", "dense canopy • fern • moss"),
        (690, 180, "COOL NORTHERN UPLANDS", "taiga • heath • rocky ridges"),
        (565, 805, "SOUTHERN WETLAND DELTA", "reed beds • marsh • mudflats"),
    ]
    for px, py, label, subtitle in labels:
        draw.text((px + 2, py + 2), label, fill=(20, 34, 34), font=font)
        draw.text((px, py), label, fill=(235, 240, 204), font=font)
        draw.text((px, py + 14), subtitle, fill=(190, 220, 194), font=font)

    draw.rectangle((25, 25, 430, 112), fill=(10, 22, 38), outline=(48, 165, 225), width=2)
    draw.text((36, 32), "THE PRIMEVAL CONTINENT", fill=(235, 225, 170), font=font)
    draw.text((36, 50), "REGIONAL CLIMATE / ECOSYSTEM ATLAS", fill=(170, 220, 230), font=font)
    draw.text((36, 68), "ELEVATION • WATERSHEDS • BIOMES", fill=(150, 195, 210), font=font)
    draw.text((36, 86), "6 natural regions / continuous terrain field", fill=(145, 190, 170), font=font)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    image.save(output_path, "PNG")
    field_path = os.path.splitext(output_path)[0] + "_field.npz"
    np.savez_compressed(
        field_path,
        elevation=elevation.astype(np.float32),
        moisture=moisture.astype(np.float32),
        temperature=temperature.astype(np.float32),
        biome=biome,
        region=region,
        river_mask=river_mask,
        is_land=is_land,
        slope=slope.astype(np.float32),
        world_width=W,
        world_height=H,
        seed=seed,
    )
    manifest_path = os.path.splitext(output_path)[0] + "_regions.json"
    with open(manifest_path, "w", encoding="utf-8") as manifest_file:
        json.dump({
            "world": "The Primeval Continent",
            "seed": int(seed),
            "regions": [
                {"id": 1, "name": "Glacial Headwaters", "climate": "cold alpine", "ecosystem": "snowfields, alpine conifers, exposed granite"},
                {"id": 2, "name": "Western Dry Steppe", "climate": "semi-arid temperate", "ecosystem": "grassland, scrub, badlands"},
                {"id": 3, "name": "Central River Valley", "climate": "temperate river basin", "ecosystem": "floodplain meadow, willow, reed banks"},
                {"id": 4, "name": "Primeval Eastern Forest", "climate": "humid temperate", "ecosystem": "dense canopy, fern, moss, forest pools"},
                {"id": 5, "name": "Cool Northern Uplands", "climate": "cool subalpine", "ecosystem": "taiga, heath, rocky ridges"},
                {"id": 6, "name": "Southern Wetland Delta", "climate": "warm humid lowland", "ecosystem": "reed beds, marsh, mudflats, delta channels"},
            ],
        }, manifest_file, ensure_ascii=False, indent=2)
    return image


if __name__ == "__main__":
    generate_coherent_overworld()
