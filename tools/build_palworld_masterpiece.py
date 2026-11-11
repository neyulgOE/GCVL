"""
LEGACY compatibility module for the former Palworld-style overworld generator.

The public compatibility entry point now mirrors the canonical atlas and no
longer invokes the historical multi-continent builder.
Refined to achieve identical aesthetic fidelity to Palworld (Image 3):
- True archipelago continent surrounded by open deep ocean
- Signature glowing neon-turquoise shallow coral reef halo hugging all coastlines
- High-contrast 4 vibrant biomes:
  1. Astral Peaks (NW): Dazzling white snow massif with dark slate granite crags and glacial melt lakes
  2. Dunes of the Desiccated (SW): Golden amber dune waves & deep red terracotta canyons
  3. Verdant Primeval Wilds (East/Center): Lush lime & emerald grasslands with canopy grove clumping
  4. Golden Steppes (NE): Amber, russet, and golden larch autumn plateau
  5. Isle of the Ancients (SE): Isolated circular sanctuary island
- Natural narrow dendritic river ribbons (2-3px wide)
- Directional 3D NW hillshading with specular highlights
- Winding ancient dirt roads & wildlife trails
- 12x12 tactical coordinate grid & 45+ Alpha Boss & Fast-Travel Waypoint Pins
"""

import os
import math
import random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


class FastFbmNoise:
    """Fast vectorized multi-octave noise generator."""
    def __init__(self, seed: int = 2026):
        self.seed = seed

    def fbm(self, w: int, h: int, scale: float, octaves: int = 4,
            persistence: float = 0.5, lacunarity: float = 2.0, seed_offset: int = 0) -> np.ndarray:
        rng = np.random.RandomState(self.seed + seed_offset)
        total = np.zeros((h, w), dtype=np.float32)
        max_val = 0.0
        amp = 1.0
        freq = scale
        resample_filter = getattr(getattr(Image, "Resampling", None), "BILINEAR", getattr(Image, "BILINEAR", 2))

        for _ in range(octaves):
            gw = int(max(2, w * freq))
            gh = int(max(2, h * freq))
            grid = rng.rand(gh, gw).astype(np.float32)
            img = Image.fromarray(grid).resize((w, h), resample_filter)
            total += np.array(img, dtype=np.float32) * amp
            max_val += amp
            amp *= persistence
            freq *= lacunarity

        return total / max_val


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def generate_legacy_palworld_overworld(
    width: int = 1024,
    height: int = 1024,
    seed: int = 2026,
    output_path: str = "assets/sprites/world_overview_macro.png"
) -> Image.Image:
    W, H = width, height
    noise = FastFbmNoise(seed)

    # -------------------------------------------------------------
    # 1. DOMAIN WARPING & COORDINATES
    # -------------------------------------------------------------
    y_coords, x_coords = np.mgrid[0:H, 0:W]
    nx = x_coords / float(W)
    ny = y_coords / float(H)

    # Multi-scale domain warp for organic, non-geometric island borders
    warp_x_coarse = (noise.fbm(W, H, 0.003, octaves=4, seed_offset=11) - 0.5) * 0.16
    warp_y_coarse = (noise.fbm(W, H, 0.003, octaves=4, seed_offset=22) - 0.5) * 0.16
    warp_x_fine = (noise.fbm(W, H, 0.012, octaves=4, seed_offset=33) - 0.5) * 0.05
    warp_y_fine = (noise.fbm(W, H, 0.012, octaves=4, seed_offset=44) - 0.5) * 0.05

    nx_w = nx + warp_x_coarse + warp_x_fine
    ny_w = ny + warp_y_coarse + warp_y_fine

    # -------------------------------------------------------------
    # 2. CONTINENTAL ARCHIPELAGO SILHOUETTE (MATCHING PALWORLD)
    # -------------------------------------------------------------
    lobes = [
        # Northwest: Astral Peaks Snow Massif
        (0.28, 0.36, 0.20, 0.24, 1.06),
        # Northwest: Northern Horn Peninsula
        (0.13, 0.16, 0.08, 0.11, 0.96),
        (0.18, 0.25, 0.09, 0.12, 0.95),
        # Central mountain isthmus connecting Snow to East
        (0.38, 0.42, 0.12, 0.13, 0.98),
        # Southwest: Desert Crescent (Dunes of the Desiccated)
        (0.30, 0.76, 0.22, 0.19, 1.04),
        (0.40, 0.82, 0.18, 0.14, 1.00),
        (0.18, 0.70, 0.10, 0.12, 0.94),
        # Center & East: Verdant Primeval Wilds (Massive mainland)
        (0.56, 0.52, 0.28, 0.32, 1.06),
        (0.68, 0.44, 0.18, 0.22, 1.00),
        (0.70, 0.62, 0.19, 0.24, 0.98),
        # Northeast: Autumn Golden Plateau
        (0.60, 0.24, 0.17, 0.15, 0.98),
        # Southeast Coastal Peninsulas
        (0.78, 0.72, 0.12, 0.15, 0.95),
        # Offshore Sanctuary Island (Iconic round island at bottom-right)
        (0.88, 0.89, 0.075, 0.085, 0.92),
        # Northern & Eastern Satellite Islets
        (0.86, 0.06, 0.035, 0.045, 0.88),
        (0.30, 0.05, 0.030, 0.040, 0.88),
        (0.79, 0.14, 0.030, 0.035, 0.86),
    ]

    island_base = np.zeros((H, W), dtype=np.float32)
    for cx, cy, rx, ry, w_val in lobes:
        d = np.sqrt(((nx_w - cx) / rx) ** 2 + ((ny_w - cy) / ry) ** 2)
        v = np.maximum(0.0, 1.0 - d) * w_val
        island_base = np.maximum(island_base, v)

    # Detailed fractal coastline noise
    coast_n1 = noise.fbm(W, H, 0.015, octaves=5, seed_offset=101)
    coast_n2 = noise.fbm(W, H, 0.035, octaves=4, seed_offset=102)
    coast_fractal = (coast_n1 - 0.5) * 0.24 + (coast_n2 - 0.5) * 0.12

    # Coastal bays, fjords, and inlets
    deep_bay_mask = (noise.fbm(W, H, 0.008, octaves=3, seed_offset=203) < 0.24) & (nx_w > 0.65) & (ny_w > 0.45) & (ny_w < 0.60)
    island_mask = island_base + coast_fractal
    island_mask[deep_bay_mask] -= 0.18

    is_land = island_mask > 0.38

    # -------------------------------------------------------------
    # 3. TOPOGRAPHY & 3D RELIEF ELEVATION
    # -------------------------------------------------------------
    # A. Astral Peaks (Glacial Massif in Northwest)
    dist_snow = np.sqrt(((nx_w - 0.28) / 0.22) ** 2 + ((ny_w - 0.36) / 0.24) ** 2)
    snow_dome = np.maximum(0.0, 1.0 - dist_snow) ** 1.35

    n_ridge_med = noise.fbm(W, H, 0.012, octaves=5, seed_offset=301)
    n_ridge_fine = noise.fbm(W, H, 0.030, octaves=4, seed_offset=302)
    # Ridged multifractals for razor-sharp arêtes and cirques
    ridge_primary = (1.0 - np.abs(2.0 * (n_ridge_med - 0.5))) ** 2.4
    ridge_secondary = (1.0 - np.abs(2.0 * (n_ridge_fine - 0.5))) ** 2.0
    snow_elevation = snow_dome * (0.35 + 0.65 * ridge_primary + 0.35 * ridge_secondary)

    # Glacial cirque tarns (mountain meltwater lakes)
    lake_spot_1 = (np.sqrt(((nx_w - 0.26) / 0.03) ** 2 + ((ny_w - 0.33) / 0.025) ** 2) < 0.85)
    lake_spot_2 = (np.sqrt(((nx_w - 0.33) / 0.025) ** 2 + ((ny_w - 0.41) / 0.02) ** 2) < 0.85)
    glacial_lakes = (lake_spot_1 | lake_spot_2) & (snow_dome > 0.35)

    # B. Dunes of the Desiccated (Southwest Desert)
    dist_desert = np.sqrt(((nx_w - 0.30) / 0.24) ** 2 + ((ny_w - 0.76) / 0.20) ** 2)
    desert_dome = np.maximum(0.0, 1.0 - dist_desert)
    # Wind-swept dune ripples aligned southwest to northeast
    dune_angle = nx_w * 55.0 + ny_w * 32.0 + noise.fbm(W, H, 0.010, seed_offset=401) * 8.0
    dune_ripples = (np.sin(dune_angle) * 0.5 + 0.5) ** 2.0 * 0.12
    desert_canyons = (noise.fbm(W, H, 0.018, seed_offset=402) - 0.5) * 0.25
    desert_elevation = desert_dome * (0.28 + 0.35 * noise.fbm(W, H, 0.008, seed_offset=403) + dune_ripples + desert_canyons)

    # C. Autumn Golden Plateau (Northeast)
    dist_autumn = np.sqrt(((nx_w - 0.60) / 0.18) ** 2 + ((ny_w - 0.24) / 0.16) ** 2)
    autumn_dome = np.maximum(0.0, 1.0 - dist_autumn)
    # Mesa plateau: flat top with stepped cliff edges
    autumn_plateau = np.clip((autumn_dome - 0.2) * 1.8, 0.0, 0.75) + noise.fbm(W, H, 0.015, seed_offset=501) * 0.20

    # D. Verdant Primeval Forest (Central & East)
    dist_forest = np.sqrt(((nx_w - 0.58) / 0.28) ** 2 + ((ny_w - 0.54) / 0.32) ** 2)
    forest_dome = np.maximum(0.0, 1.0 - dist_forest)
    rolling_hills = noise.fbm(W, H, 0.010, octaves=4, seed_offset=601) * 0.40
    river_canyon_noise = noise.fbm(W, H, 0.022, octaves=4, seed_offset=602) * 0.20
    forest_elevation = forest_dome * (0.22 + rolling_hills + river_canyon_noise)

    # Combine into comprehensive heightmap
    elevation = np.zeros((H, W), dtype=np.float32)
    elevation += snow_elevation * 1.05
    elevation += desert_elevation * 0.60
    elevation += autumn_plateau * 0.68
    elevation += forest_elevation * 0.58
    elevation = np.clip(elevation, 0.0, 1.0)

    # -------------------------------------------------------------
    # 4. FLUVIAL NETWORK (ELEGANT NARROW RIVER RIBBONS & LAKES)
    # -------------------------------------------------------------
    river_n1 = noise.fbm(W, H, 0.007, octaves=4, seed_offset=701)
    river_n2 = noise.fbm(W, H, 0.016, octaves=4, seed_offset=702)
    # Narrow main river (2-3px) flowing from Central Highlands into Eastern Bay
    main_river = (np.abs(river_n1 - 0.5) < 0.0065) & (is_land) & (elevation < 0.68) & (nx_w > 0.38)
    # Narrow tributary rivers
    tributaries = (np.abs(river_n2 - 0.5) < 0.0050) & (is_land) & (elevation < 0.46) & (nx_w > 0.45) & (ny_w > 0.35)
    # Western mountain melt stream
    melt_stream = (np.abs(river_n2 - 0.5) < 0.0055) & (is_land) & (dist_snow < 0.26) & (elevation > 0.30) & (elevation < 0.72)

    river_mask = (main_river | tributaries | melt_stream | glacial_lakes) & is_land
    elevation[river_mask] = np.maximum(0.03, elevation[river_mask] - 0.18)
    is_surface_land = is_land & (~river_mask)

    # -------------------------------------------------------------
    # 5. HIGH-CONTRAST 3D TOPOGRAPHIC HILLSHADING
    # -------------------------------------------------------------
    dz_dy, dz_dx = np.gradient(elevation)
    scale = 38.0
    nx_norm = -dz_dx * scale
    ny_norm = -dz_dy * scale
    nz_norm = np.ones_like(elevation)
    length = np.sqrt(nx_norm**2 + ny_norm**2 + nz_norm**2)
    nx_norm /= length
    ny_norm /= length
    nz_norm /= length

    # Sun from Northwest: 315 degrees azimuth, 45 degrees elevation
    lx, ly, lz = -0.577, -0.577, 0.577
    dot = nx_norm * lx + ny_norm * ly + nz_norm * lz
    hillshade = np.clip(0.60 + 0.62 * dot, 0.52, 1.45)
    # Specular rim on razor-sharp mountain arêtes
    crest_highlight = np.clip((dot - 0.28) * 1.5, 0.0, 0.55) * (elevation > 0.55)

    # -------------------------------------------------------------
    # 6. SIGNATURE GLOWING REEF HALO (PALWORLD TURQUOISE SHELF)
    # -------------------------------------------------------------
    # Distances measured strictly from True Ocean
    ocean_img = Image.fromarray(((~is_land) * 255).astype(np.uint8))
    ocean_blur_3 = np.array(ocean_img.filter(ImageFilter.GaussianBlur(3.0)), dtype=np.float32) / 255.0

    # Sandy Beach is STRICTLY 2-4 pixels adjacent to TRUE OCEAN (not inland rivers)
    is_beach = is_surface_land & (ocean_blur_3 > 0.12) & (elevation < 0.40)

    # Land distance from ocean (for reef shelf gradients)
    land_img = Image.fromarray((is_land * 255).astype(np.uint8))
    land_blur_3 = np.array(land_img.filter(ImageFilter.GaussianBlur(3.0)), dtype=np.float32) / 255.0
    land_blur_7 = np.array(land_img.filter(ImageFilter.GaussianBlur(7.0)), dtype=np.float32) / 255.0
    land_blur_18 = np.array(land_img.filter(ImageFilter.GaussianBlur(18.0)), dtype=np.float32) / 255.0
    land_blur_45 = np.array(land_img.filter(ImageFilter.GaussianBlur(45.0)), dtype=np.float32) / 255.0

    # -------------------------------------------------------------
    # 7. COLOR FIELD ASSEMBLY (PALWORLD AAA PALETTE)
    # -------------------------------------------------------------
    R = np.zeros((H, W), dtype=np.float32)
    G = np.zeros((H, W), dtype=np.float32)
    B = np.zeros((H, W), dtype=np.float32)

    # A. Open Deep Ocean (Dark Royal Navy)
    ocean_noise = noise.fbm(W, H, 0.05, octaves=3, seed_offset=801) * 8.0
    R[:] = 10.0 + ocean_noise
    G[:] = 32.0 + ocean_noise
    B[:] = 74.0 + ocean_noise

    # Outer continental slope (18 - 45 px)
    m45 = (~is_surface_land) & (land_blur_45 > 0.015)
    t45 = land_blur_45[m45]
    R[m45] = R[m45] * (1.0 - t45) + 16.0 * t45
    G[m45] = G[m45] * (1.0 - t45) + 68.0 * t45
    B[m45] = B[m45] * (1.0 - t45) + 132.0 * t45

    # Mid lagoon shelf (7 - 18 px)
    m18 = (~is_surface_land) & (land_blur_18 > 0.03)
    t18 = land_blur_18[m18]
    R[m18] = R[m18] * (1.0 - t18) + 26.0 * t18
    G[m18] = G[m18] * (1.0 - t18) + 128.0 * t18
    B[m18] = B[m18] * (1.0 - t18) + 192.0 * t18

    # Shallow azure shelf (3 - 7 px)
    m7 = (~is_surface_land) & (land_blur_7 > 0.06)
    t7 = land_blur_7[m7]
    R[m7] = R[m7] * (1.0 - t7) + 36.0 * t7
    G[m7] = G[m7] * (1.0 - t7) + 185.0 * t7
    B[m7] = B[m7] * (1.0 - t7) + 220.0 * t7

    # Glowing Neon-Turquoise Coral Reef Shelf (0 - 3 px immediately hugging coast)
    m3 = (~is_surface_land) & (land_blur_3 > 0.10)
    t3 = land_blur_3[m3]
    R[m3] = R[m3] * (1.0 - t3) + 48.0 * t3
    G[m3] = G[m3] * (1.0 - t3) + 228.0 * t3
    B[m3] = B[m3] * (1.0 - t3) + 242.0 * t3

    # Subsurface depth contour lines in coastal ocean
    contour_line = (np.abs(land_blur_18 - 0.28) < 0.012) | (np.abs(land_blur_45 - 0.20) < 0.012)
    m_contour = (~is_surface_land) & contour_line
    R[m_contour] = np.clip(R[m_contour] + 24.0, 0, 255)
    G[m_contour] = np.clip(G[m_contour] + 45.0, 0, 255)
    B[m_contour] = np.clip(B[m_contour] + 58.0, 0, 255)

    # B. River and Lake Water Colors
    R[river_mask] = 34.0
    G[river_mask] = 168.0
    B[river_mask] = 210.0
    # Mountain glacial lakes are deep crystal sapphire
    R[glacial_lakes] = 20.0
    G[glacial_lakes] = 105.0
    B[glacial_lakes] = 175.0

    # C. Organic Biome Weight Partitioning (Domain-Warped Smoothstep)
    # Snow weight (Northwest Quadrant)
    w_snow_x = 1.0 - smoothstep(0.36, 0.44, nx_w)
    w_snow_y = 1.0 - smoothstep(0.48, 0.56, ny_w)
    w_snow = w_snow_x * w_snow_y

    # Desert weight (Southwest Quadrant)
    w_desert_x = 1.0 - smoothstep(0.40, 0.48, nx_w)
    w_desert_y = smoothstep(0.48, 0.56, ny_w)
    w_desert = w_desert_x * w_desert_y

    # Autumn weight (Northeast Plateau)
    w_autumn_x = smoothstep(0.42, 0.50, nx_w) * (1.0 - smoothstep(0.72, 0.78, nx_w))
    w_autumn_y = 1.0 - smoothstep(0.28, 0.36, ny_w)
    w_autumn = w_autumn_x * w_autumn_y

    # Forest weight (Central and East Mainland)
    w_forest = np.clip(1.0 - w_snow - w_desert - w_autumn, 0.0, 1.0)

    # Normalize weights so they sum to 1.0 everywhere
    w_total = np.maximum(1e-5, w_snow + w_desert + w_autumn + w_forest)
    w_snow /= w_total
    w_desert /= w_total
    w_autumn /= w_total
    w_forest /= w_total

    # D. Biome Specific Surface Colors
    # 1. Snow Biome: Pure White snow with sharp dark slate granite rock faces on steep slopes
    slope = np.sqrt(dz_dx**2 + dz_dy**2) * 45.0
    rock_face_mask = (slope > 0.34) & (elevation < 0.88)
    snow_surf_r = np.where(rock_face_mask, 52.0, 252.0)
    snow_surf_g = np.where(rock_face_mask, 62.0, 254.0)
    snow_surf_b = np.where(rock_face_mask, 76.0, 255.0)

    # 2. Desert Biome: Vibrant Golden Sand Dunes & Deep Terracotta Red Canyon Cliffs
    sand_dune_wave = (np.sin(dune_angle * 1.5) * 0.5 + 0.5)
    desert_sand_r = 248.0 + sand_dune_wave * 6.0
    desert_sand_g = 186.0 + sand_dune_wave * 20.0
    desert_sand_b = 82.0 + sand_dune_wave * 28.0
    # Red canyon cliffs on high ground / steep slopes
    is_red_canyon = (slope > 0.28) | (elevation > 0.42)
    desert_surf_r = np.where(is_red_canyon, 192.0, desert_sand_r)
    desert_surf_g = np.where(is_red_canyon, 68.0, desert_sand_g)
    desert_surf_b = np.where(is_red_canyon, 34.0, desert_sand_b)

    # 3. Autumn Biome: Warm Amber, Russet Orange & Golden Larch Foliage
    autumn_canopy = noise.fbm(W, H, 0.025, seed_offset=511)
    autumn_surf_r = 224.0 + (autumn_canopy - 0.5) * 30.0
    autumn_surf_g = 146.0 + (autumn_canopy - 0.5) * 40.0
    autumn_surf_b = 34.0 + (autumn_canopy - 0.5) * 20.0

    # 4. Forest Biome: Lush Vibrant Lime & Emerald Grasslands with Deep-Green Tree Canopies
    forest_canopy_noise = noise.fbm(W, H, 0.026, seed_offset=611)
    is_dense_canopy = forest_canopy_noise > 0.50
    # Grassland: Vibrant Spring/Meadow Green (Palworld Style)
    grass_r = 95.0 + (noise.fbm(W, H, 0.012, seed_offset=622) - 0.5) * 20.0
    grass_g = 175.0 + (noise.fbm(W, H, 0.012, seed_offset=622) - 0.5) * 25.0
    grass_b = 52.0 + (noise.fbm(W, H, 0.012, seed_offset=622) - 0.5) * 15.0
    # Tree canopy clumps: deep forest emerald
    canopy_r = 24.0
    canopy_g = 88.0
    canopy_b = 32.0
    forest_surf_r = np.where(is_dense_canopy, canopy_r, grass_r)
    forest_surf_g = np.where(is_dense_canopy, canopy_g, grass_g)
    forest_surf_b = np.where(is_dense_canopy, canopy_b, grass_b)

    # Blend land biomes
    land_r = w_snow * snow_surf_r + w_desert * desert_surf_r + w_autumn * autumn_surf_r + w_forest * forest_surf_r
    land_g = w_snow * snow_surf_g + w_desert * desert_surf_g + w_autumn * autumn_surf_g + w_forest * forest_surf_g
    land_b = w_snow * snow_surf_b + w_desert * desert_surf_b + w_autumn * autumn_surf_b + w_forest * forest_surf_b

    # Ivory-gold Sandy Beaches (Strictly along Ocean Edge)
    land_r[is_beach] = 246.0
    land_g[is_beach] = 232.0
    land_b[is_beach] = 186.0

    # Apply 3D Topographic Hillshading and Crest Highlights
    land_r = np.clip(land_r * hillshade + crest_highlight * 255.0, 0.0, 255.0)
    land_g = np.clip(land_g * hillshade + crest_highlight * 255.0, 0.0, 255.0)
    land_b = np.clip(land_b * hillshade + crest_highlight * 255.0, 0.0, 255.0)

    # Paint land over RGB
    R[is_surface_land] = land_r[is_surface_land]
    G[is_surface_land] = land_g[is_surface_land]
    B[is_surface_land] = land_b[is_surface_land]

    # Convert to PIL Image
    rgb = np.stack([R, G, B], axis=-1).astype(np.uint8)
    img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(img)

    # -------------------------------------------------------------
    # 8. WINDING PREHISTORIC GAME TRAILS & ANCIENT DIRT PATHS
    # -------------------------------------------------------------
    trail_points = [
        # Trail 1: Central Valley Highway connecting South to North
        [(560, 820), (530, 740), (510, 650), (490, 570), (480, 480), (450, 410), (420, 360), (370, 340), (320, 310)],
        # Trail 2: East Coast Scenic Trail
        [(560, 820), (640, 780), (710, 720), (740, 620), (700, 530), (660, 440), (620, 360), (640, 280), (660, 210)],
        # Trail 3: Desert Canyon Pass into Central Valley
        [(240, 800), (310, 760), (380, 710), (440, 660), (510, 650)],
        # Trail 4: Northern Snow Pass
        [(370, 340), (340, 260), (280, 230), (210, 220), (160, 180)],
    ]

    trail_color = (225, 208, 168)
    trail_shadow = (145, 125, 88)
    for path in trail_points:
        for i in range(len(path) - 1):
            p1, p2 = path[i], path[i + 1]
            draw.line([p1, p2], fill=trail_shadow, width=4)
            draw.line([p1, p2], fill=trail_color, width=2)

    # -------------------------------------------------------------
    # 9. TACTICAL COORDINATE GRID (PALWORLD 12x12 GRID OVERLAY)
    # -------------------------------------------------------------
    grid_step = 85
    grid_col = (180, 230, 255, 38)
    for gx in range(grid_step, W, grid_step):
        draw.line([(gx, 0), (gx, H)], fill=grid_col[:3], width=1)
    for gy in range(grid_step, H, grid_step):
        draw.line([(0, gy), (W, gy)], fill=grid_col[:3], width=1)

    # Coordinate Axis Numbers
    for idx, gx in enumerate(range(grid_step, W, grid_step)):
        coord_val = f"{(idx + 1) * 10}"
        draw.text((gx + 4, 6), coord_val, fill=(200, 240, 255))
        draw.text((gx + 4, H - 20), coord_val, fill=(200, 240, 255))
    for idx, gy in enumerate(range(grid_step, H, grid_step)):
        coord_val = f"{(idx + 1) * 10}"
        draw.text((6, gy + 4), coord_val, fill=(200, 240, 255))
        draw.text((W - 28, gy + 4), coord_val, fill=(200, 240, 255))

    # -------------------------------------------------------------
    # 10. PREHISTORIC ALPHA BOSSES & FAST-TRAVEL WAYPOINT PINS
    # -------------------------------------------------------------
    # Definitions: (x, y, name, type)
    pins = [
        # --- Astral Peaks (Snow Massif) ---
        (280, 330, "Frost Mammoth (Alpha Lv.45)", "alpha"),
        (210, 280, "Blizzard Wyvern (Alpha Lv.38)", "alpha"),
        (340, 270, "Dire Glacier Wolf", "beast"),
        (160, 180, "Astral Horn Guardian (Alpha Lv.50)", "alpha"),
        (240, 220, "Icebound Raptor Flock", "beast"),
        (330, 390, "Glacial Melt Lake Leviathan (Alpha)", "alpha"),
        (130, 160, "Astral Peak Spire", "waypoint"),
        (280, 410, "Frostveil Pass Totem", "waypoint"),
        (360, 320, "Northern Glacial Shrine", "waypoint"),

        # --- Dunes of the Desiccated (Desert Crescent) ---
        (300, 750, "Dune Tyrant (Alpha Lv.42)", "alpha"),
        (220, 720, "Scorched Scorpio (Alpha Lv.35)", "alpha"),
        (390, 790, "Terracotta Smilodon Pride", "beast"),
        (250, 830, "Canyon Sandworm (Alpha Lv.40)", "alpha"),
        (350, 830, "Red Dune Oasis", "waypoint"),
        (230, 680, "Sunken Canyon Arch", "waypoint"),
        (430, 810, "Desert Ruins Monolith", "waypoint"),
        (180, 750, "Sunset Shore Beacon", "waypoint"),

        # --- Golden Steppes (Autumn Plateau) ---
        (620, 240, "Golden Gryphon (Alpha Lv.36)", "alpha"),
        (690, 280, "Amber Stag Patriarch", "beast"),
        (560, 210, "Crimson Falcon", "beast"),
        (720, 230, "Autumn Ridge Beacon", "waypoint"),
        (550, 260, "Highland Gateway Totem", "waypoint"),

        # --- Verdant Primeval Wilds (Mainland Center/East) ---
        (580, 500, "Forest Colossus (Alpha Lv.35)", "alpha"),
        (510, 580, "Cave Bear Patriarch (Alpha Lv.32)", "alpha"),
        (640, 420, "Great Primeval Elk Herd", "beast"),
        (710, 610, "Primal Boar Matriarch", "beast"),
        (470, 460, "River Valley Ancient Bison", "beast"),
        (670, 520, "Emerald Creek Totem", "waypoint"),
        (520, 370, "Verdant Glade Monolith", "waypoint"),
        (600, 620, "Ancient Sacred Oak Spire", "waypoint"),
        (750, 550, "Eastern Estuary Totem", "waypoint"),
        (460, 560, "Confluence Ford Beacon", "waypoint"),
        (770, 690, "Southeast Cliffs Totem", "waypoint"),
        (680, 740, "Verdant Cape Monolith", "waypoint"),

        # --- Offshore Sanctuary Island (SE) ---
        (880, 890, "Sanctuary Chimera (Alpha Lv.50)", "alpha"),
        (900, 870, "Sanctuary Relic Spire", "waypoint"),

        # --- Northern & Remote Islets ---
        (860, 55, "North Sea Drake (Alpha Lv.48)", "alpha"),
        (300, 55, "Arctic Islet Monolith", "waypoint"),
    ]

    for px, py, pname, ptype in pins:
        if ptype == "alpha":
            # Golden Outer Ring with Deep Navy Center
            draw.ellipse([px - 15, py - 15, px + 15, py + 15], fill=(16, 36, 68), outline=(255, 205, 45), width=2)
            draw.ellipse([px - 10, py - 10, px + 10, py + 10], fill=(28, 145, 225))
            # Stylized crown / beast silhouette inside
            draw.polygon([(px, py - 7), (px + 6, py - 1), (px + 4, py + 5), (px - 4, py + 5), (px - 6, py - 1)], fill=(255, 252, 235))
            # Text label
            draw.text((px + 18, py - 7), pname, fill=(255, 235, 140))
        elif ptype == "waypoint":
            # Neon Cyan Diamond Totem (Fast-Travel)
            draw.polygon([(px, py - 12), (px + 9, py), (px, py + 12), (px - 9, py)], fill=(10, 52, 95), outline=(55, 235, 255), width=2)
            draw.polygon([(px, py - 6), (px + 4, py), (px, py + 6), (px - 4, py)], fill=(215, 252, 255))
            draw.text((px + 15, py - 6), pname, fill=(185, 242, 255))
        else:
            # Megafauna Herd Pin (Cyan Ring)
            draw.ellipse([px - 11, py - 11, px + 11, py + 11], fill=(14, 42, 75), outline=(65, 210, 245), width=2)
            draw.ellipse([px - 7, py - 7, px + 7, py + 7], fill=(30, 135, 205))
            draw.polygon([(px, py - 5), (px + 4, py + 3), (px - 4, py + 3)], fill=(235, 250, 255))
            draw.text((px + 15, py - 6), pname, fill=(215, 240, 255))

    # -------------------------------------------------------------
    # 11. MAP CARTOGRAPHIC HUD & TITLE CARTOUCHE
    # -------------------------------------------------------------
    # Zoom buttons (+ / -) in bottom-right corner
    draw.rectangle([W - 65, H - 95, W - 25, H - 35], fill=(15, 28, 48), outline=(50, 120, 175), width=2)
    draw.line([(W - 55, H - 75), (W - 35, H - 75)], fill=(200, 245, 255), width=3)
    draw.line([(W - 45, H - 85), (W - 45, H - 65)], fill=(200, 245, 255), width=3)
    draw.line([(W - 55, H - 52), (W - 35, H - 52)], fill=(200, 245, 255), width=3)
    draw.line([(W - 65, H - 65), (W - 25, H - 65)], fill=(50, 120, 175), width=1)

    # Title Cartouche
    draw.rectangle([25, 25, 360, 90], fill=(10, 22, 38), outline=(48, 165, 225), width=2)
    draw.text((36, 32), "THE PRIMEVAL CONTINENT", fill=(255, 235, 140))
    draw.text((36, 52), "ARCHIPELAGO OF THE STONE AGE (PALWORLD ATLAS)", fill=(140, 225, 255))
    draw.text((36, 72), "100% UNTOUCHED PRIMEVAL NATURE", fill=(110, 185, 215))

    # Save to disk
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG")
    print(f"Successfully generated Palworld Masterpiece Map at: {output_path} ({W}x{H})")
    return img


def generate_palworld_overworld(
    width: int = 1024,
    height: int = 1024,
    seed: int = 2026,
    output_path: str = "assets/sprites/world_overview_macro.png",
) -> Image.Image:
    """Return the canonical atlas for old callers without rebuilding the map."""
    try:
        from tools.generate_primeval_world import load_canonical_atlas
    except ModuleNotFoundError:  # Running this file directly from tools/.
        from generate_primeval_world import load_canonical_atlas

    image = load_canonical_atlas().convert("RGB")
    target_size = (int(width), int(height))
    if image.size != target_size:
        image = image.resize(target_size, Image.Resampling.LANCZOS)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, "PNG")
    return image


if __name__ == "__main__":
    generate_palworld_overworld()
