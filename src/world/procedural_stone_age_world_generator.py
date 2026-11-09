"""
Prehistoric Island Archipelago World Generator (Palworld & AAA-Style Topographic Overworld).
Creates an organic island continent surrounded by deep ocean with:
1. Four High-Contrast Prehistoric Biomes:
   - Northwest: Glacial Alpine Peaks & Knife-Edge Snow Crags (Astral Peaks)
   - Southwest: Terracotta Badlands & Golden Desert Dunes (Dunes of the Desiccated)
   - Central & East: Emerald Primeval Forest & Winding River Valleys (Verdant Wilds)
   - Northeast: Autumn Highlands & Amber Plateau (Golden Steppes)
   - Southeast: Offshore Sanctuary Island & Coastal Archipelagos
2. Realistic Topographic Shaded Relief (Directional NW Hillshading with Ridged Multifractal Normals).
3. Glowing Turquoise Coastal Shelf / Coral Sandbar Halo hugging jagged fractal fjords.
4. Dendritic River Hydrology cutting through mountain gorges into coastal bays.
5. Faint Navigation Coordinate Grid & Prehistoric Alpha Boss / Fauna Map Pins.
"""

from __future__ import annotations
import math
import os
import random
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from tools.build_palworld_masterpiece import generate_palworld_overworld, FastFbmNoise


class FastVectorNoise2D(FastFbmNoise):
    pass


class ProceduralStoneAgeWorldGenerator:
    """
    Overworld Generator creating an iconic island archipelago map on par with AAA adventure maps (Palworld style).
    """
    def __init__(self, width: int = 200, height: int = 200, seed: int = 2026):
        self.width = width
        self.height = height
        self.seed = seed
        self.noise = FastFbmNoise(seed)
        self.grid: List[List[Any]] = []
        self.master_map_image: Optional[Image.Image] = None

    def generate_world(self):
        """Generates standard tile representation for compatibility."""
        self.grid = [[None for _ in range(self.width)] for _ in range(self.height)]
        return self.grid

    def render_natural_overworld_map(
        self,
        tile_scale: int = 4,
        output_path: str = "assets/sprites/world_overview_macro.png",
        render_resolution: int = 1024
    ) -> Image.Image:
        """
        Renders a stunning 1024x1024 Palworld-style Prehistoric Overworld Map with:
        - Organic island continent surrounded by open deep ocean
        - 4 High-contrast biomes (Snow Massif, Golden Sand Dunes, Lush Emerald Forest, Autumn Plateau)
        - 3D Ridged mountain topography with directional northwest hillshading
        - Glowing aquamarine reef shelves hugging the jagged coastline
        - Delicate navigation grid and 40+ Prehistoric Alpha Boss / Fauna Pins
        """
        img = generate_palworld_overworld(
            width=render_resolution,
            height=render_resolution,
            seed=self.seed,
            output_path=output_path
        )
        self.master_map_image = img
        return img

        W = render_resolution
        H = render_resolution

        # 1. Grids & Domain Warping
        y_coords, x_coords = np.mgrid[0:H, 0:W]
        nx = x_coords / float(W)
        ny = y_coords / float(H)

        warp_x = (self.noise.fbm(W, H, 0.0032, octaves=4, seed_offset=101) - 0.5) * 0.18
        warp_y = (self.noise.fbm(W, H, 0.0032, octaves=4, seed_offset=202) - 0.5) * 0.18
        nx_w = nx + warp_x
        ny_w = ny + warp_y

        # 2. Island Silhouette (Continental Archipelago)
        lobes = [
            (0.56, 0.52, 0.32, 0.34, 1.00),   # Central/East primeval forest mass
            (0.32, 0.34, 0.22, 0.25, 1.06),  # Northwest snow mountain
            (0.12, 0.16, 0.09, 0.10, 0.95),  # Northwest peninsula horn
            (0.20, 0.25, 0.12, 0.13, 0.92),  # Connecting NW neck
            (0.34, 0.74, 0.25, 0.21, 1.00),  # Southwest desert lobe
            (0.62, 0.28, 0.20, 0.18, 0.98),  # Northeast autumn plateau
            (0.74, 0.68, 0.17, 0.19, 0.96),  # Southeast coastal lobe
            (0.89, 0.88, 0.08, 0.09, 0.90),  # Sanctuary island bottom-right
            (0.86, 0.05, 0.03, 0.04, 0.85),  # Top-right islet
            (0.31, 0.06, 0.03, 0.04, 0.85),  # North islet
        ]

        island_base = np.zeros((H, W), dtype=np.float32)
        for cx, cy, rx, ry, w_val in lobes:
            d = np.sqrt(((nx_w - cx) / rx) ** 2 + ((ny_w - cy) / ry) ** 2)
            lobe_val = np.maximum(0.0, (1.0 - d)) * w_val
            island_base = np.maximum(island_base, lobe_val)

        coast_noise = self.noise.fbm(W, H, 0.016, octaves=5, seed_offset=555)
        island_mask = island_base + (coast_noise - 0.5) * 0.26
        is_land = island_mask > 0.38

        # 3. Topography & Elevation
        dist_snow = np.sqrt(((nx_w - 0.32) / 0.22) ** 2 + ((ny_w - 0.34) / 0.24) ** 2)
        snow_dome = np.maximum(0.0, 1.0 - dist_snow) ** 1.35

        n_med = self.noise.fbm(W, H, 0.012, octaves=4, seed_offset=333)
        n_fine = self.noise.fbm(W, H, 0.028, octaves=4, seed_offset=444)
        ridge1 = (1.0 - np.abs(2.0 * (n_med - 0.5))) ** 2.2
        ridge2 = (1.0 - np.abs(2.0 * (n_fine - 0.5))) ** 1.8
        snow_crags = snow_dome * (0.45 + 0.60 * ridge1 + 0.35 * ridge2)

        dist_desert = np.sqrt(((nx_w - 0.34) / 0.25) ** 2 + ((ny_w - 0.74) / 0.21) ** 2)
        desert_dome = np.maximum(0.0, 1.0 - dist_desert)
        dune_waves = np.sin((nx_w * 48.0 + ny_w * 28.0) + n_med * 6.5) * 0.08
        desert_relief = desert_dome * (0.35 + 0.45 * self.noise.fbm(W, H, 0.008, seed_offset=666) + dune_waves)

        dist_forest = np.sqrt(((nx_w - 0.58) / 0.30) ** 2 + ((ny_w - 0.50) / 0.32) ** 2)
        forest_dome = np.maximum(0.0, 1.0 - dist_forest)
        forest_relief = forest_dome * (0.30 + 0.50 * self.noise.fbm(W, H, 0.009, seed_offset=888) + 0.25 * ridge2)

        dist_autumn = np.sqrt(((nx_w - 0.62) / 0.20) ** 2 + ((ny_w - 0.28) / 0.18) ** 2)
        autumn_dome = np.maximum(0.0, 1.0 - dist_autumn)
        autumn_relief = autumn_dome * (0.40 + 0.45 * self.noise.fbm(W, H, 0.010, seed_offset=999))

        elevation = np.zeros((H, W), dtype=np.float32)
        elevation += snow_crags * 0.98
        elevation += desert_relief * 0.45
        elevation += forest_relief * 0.55
        elevation += autumn_relief * 0.60
        elevation = np.clip(elevation, 0.0, 1.0)

        # Rivers & Gorges
        river_noise = self.noise.fbm(W, H, 0.006, octaves=4, seed_offset=1212)
        river_branches = self.noise.fbm(W, H, 0.015, octaves=4, seed_offset=1313)
        river_mask = (np.abs(river_noise - 0.5) < 0.020) & (is_land) & (elevation < 0.72)
        river_mask |= (np.abs(river_branches - 0.5) < 0.016) & (is_land) & (elevation < 0.42) & (nx_w > 0.42)
        elevation[river_mask] = np.maximum(0.04, elevation[river_mask] - 0.26)
        is_surface_land = is_land & (~river_mask)

        # 4. Hillshading (NW Sun Lighting)
        dz_dy, dz_dx = np.gradient(elevation)
        scale = 36.0
        nx_norm = -dz_dx * scale
        ny_norm = -dz_dy * scale
        nz_norm = np.ones_like(elevation)
        length = np.sqrt(nx_norm**2 + ny_norm**2 + nz_norm**2)
        nx_norm /= length
        ny_norm /= length
        nz_norm /= length

        # Light from Northwest (315 deg azimuth, 45 deg altitude)
        lx, ly, lz = -0.577, -0.577, 0.577
        dot = nx_norm * lx + ny_norm * ly + nz_norm * lz
        hillshade = np.clip(0.32 + 0.80 * dot, 0.22, 1.50)

        # 5. Coastal Reef / Shallow Shelf
        land_img = Image.fromarray((is_surface_land * 255).astype(np.uint8))
        blur_3 = np.array(land_img.filter(ImageFilter.GaussianBlur(3)), dtype=np.float32) / 255.0
        blur_8 = np.array(land_img.filter(ImageFilter.GaussianBlur(8)), dtype=np.float32) / 255.0
        blur_20 = np.array(land_img.filter(ImageFilter.GaussianBlur(20)), dtype=np.float32) / 255.0
        blur_45 = np.array(land_img.filter(ImageFilter.GaussianBlur(45)), dtype=np.float32) / 255.0

        is_beach = is_surface_land & (blur_8 < 0.88) & (elevation < 0.45)

        # 6. Colors Construction (RGB channels)
        R = np.zeros((H, W), dtype=np.float32)
        G = np.zeros((H, W), dtype=np.float32)
        B = np.zeros((H, W), dtype=np.float32)

        # Deep Ocean
        ocean_noise = self.noise.fbm(W, H, 0.04, octaves=3, seed_offset=808) * 12.0
        R[:] = 12.0 + ocean_noise
        G[:] = 48.0 + ocean_noise
        B[:] = 95.0 + ocean_noise

        # Shelf transitions
        m45 = (~is_surface_land) & (blur_45 > 0.01)
        t45 = blur_45[m45]
        R[m45] = R[m45] * (1.0 - t45) + 16.0 * t45
        G[m45] = G[m45] * (1.0 - t45) + 75.0 * t45
        B[m45] = B[m45] * (1.0 - t45) + 135.0 * t45

        m20 = (~is_surface_land) & (blur_20 > 0.02)
        t20 = blur_20[m20]
        R[m20] = R[m20] * (1.0 - t20) + 24.0 * t20
        G[m20] = G[m20] * (1.0 - t20) + 120.0 * t20
        B[m20] = B[m20] * (1.0 - t20) + 175.0 * t20

        m8 = (~is_surface_land) & (blur_8 > 0.05)
        t8 = blur_8[m8]
        R[m8] = R[m8] * (1.0 - t8) + 36.0 * t8
        G[m8] = G[m8] * (1.0 - t8) + 175.0 * t8
        B[m8] = B[m8] * (1.0 - t8) + 210.0 * t8

        # Glowing turquoise reef shelf immediately around coastline
        m3 = (~is_surface_land) & (blur_3 > 0.12)
        t3 = blur_3[m3]
        R[m3] = R[m3] * (1.0 - t3) + 52.0 * t3
        G[m3] = G[m3] * (1.0 - t3) + 218.0 * t3
        B[m3] = B[m3] * (1.0 - t3) + 228.0 * t3

        # Rivers
        R[river_mask] = 34.0
        G[river_mask] = 165.0
        B[river_mask] = 205.0

        # Bathymetric contours in ocean
        bath_contour = (np.abs(blur_20 - 0.25) < 0.015) | (np.abs(blur_45 - 0.20) < 0.015)
        m_bath = (~is_surface_land) & bath_contour
        R[m_bath] = np.clip(R[m_bath] + 25.0, 0, 255)
        G[m_bath] = np.clip(G[m_bath] + 45.0, 0, 255)
        B[m_bath] = np.clip(B[m_bath] + 55.0, 0, 255)

        # 7. Land Biome Weights
        w_snow = np.clip(1.0 - dist_snow * 3.4, 0.0, 1.0) * np.clip((elevation - 0.32) * 3.5, 0.0, 1.0)
        w_desert = np.clip(1.0 - dist_desert * 3.0, 0.0, 1.0) * (1.0 - w_snow)
        w_autumn = np.clip(1.0 - dist_autumn * 3.2, 0.0, 1.0) * (1.0 - w_snow) * (1.0 - w_desert)
        w_forest = np.clip(1.0 - w_snow - w_desert - w_autumn, 0.0, 1.0)

        # Snow Biome
        snow_rock_mask = (ridge1 > 0.52) & (elevation < 0.85)
        snow_r = np.where(snow_rock_mask, 115.0, 246.0)
        snow_g = np.where(snow_rock_mask, 126.0, 250.0)
        snow_b = np.where(snow_rock_mask, 142.0, 255.0)

        # Desert Biome
        d_dune = self.noise.fbm(W, H, 0.015, seed_offset=616)
        desert_r = 238.0 + (d_dune - 0.5) * 35.0
        desert_g = 175.0 + (d_dune - 0.5) * 45.0
        desert_b = 98.0 + (d_dune - 0.5) * 30.0
        red_bluff = elevation > 0.35
        desert_r = np.where(red_bluff, 212.0, desert_r)
        desert_g = np.where(red_bluff, 115.0, desert_g)
        desert_b = np.where(red_bluff, 62.0, desert_b)

        # Autumn Biome
        autumn_r = 224.0 + (n_fine - 0.5) * 25.0
        autumn_g = 162.0 + (n_fine - 0.5) * 30.0
        autumn_b = 45.0 + (n_fine - 0.5) * 20.0

        # Forest Biome
        forest_canopy = self.noise.fbm(W, H, 0.035, seed_offset=717)
        forest_r = np.where(forest_canopy > 0.52, 26.0, 68.0)
        forest_g = np.where(forest_canopy > 0.52, 96.0, 145.0)
        forest_b = np.where(forest_canopy > 0.52, 40.0, 56.0)

        land_r = w_snow * snow_r + w_desert * desert_r + w_autumn * autumn_r + w_forest * forest_r
        land_g = w_snow * snow_g + w_desert * desert_g + w_autumn * autumn_g + w_forest * forest_g
        land_b = w_snow * snow_b + w_desert * desert_b + w_autumn * autumn_b + w_forest * forest_b

        # Sand beaches
        land_r[is_beach] = 235.0
        land_g[is_beach] = 220.0
        land_b[is_beach] = 172.0

        # Apply Hillshading to land
        land_r = np.clip(land_r * hillshade, 0.0, 255.0)
        land_g = np.clip(land_g * hillshade, 0.0, 255.0)
        land_b = np.clip(land_b * hillshade, 0.0, 255.0)

        R[is_surface_land] = land_r[is_surface_land]
        G[is_surface_land] = land_g[is_surface_land]
        B[is_surface_land] = land_b[is_surface_land]

        # Assemble final RGB image
        rgb = np.stack([R, G, B], axis=-1).astype(np.uint8)
        img = Image.fromarray(rgb)
        draw = ImageDraw.Draw(img)

        # 8. Navigation Coordinate Grid Overlay
        grid_step = 85  # 12x12 grid
        for gx in range(grid_step, W, grid_step):
            draw.line([(gx, 0), (gx, H)], fill=(200, 235, 250, 40), width=1)
        for gy in range(grid_step, H, grid_step):
            draw.line([(0, gy), (W, gy)], fill=(200, 235, 250, 40), width=1)

        # Coordinate ticks
        for idx, gx in enumerate(range(grid_step, W, grid_step)):
            draw.text((gx + 4, 8), f"{gx // 10}", fill=(180, 225, 245))
        for idx, gy in enumerate(range(grid_step, H, grid_step)):
            draw.text((8, gy + 4), f"{gy // 10}", fill=(180, 225, 245))

        # 9. Prehistoric Palworld-style Pins (Alpha Bosses, Beasts, Waypoints)
        beast_defs = [
            (320, 310, "Frost Mammoth (Alpha)", "alpha"),
            (270, 360, "Dire Blizzard Wolf", "beast"),
            (230, 290, "Ice Peak Wyvern", "alpha"),
            (180, 230, "Glacial Raptor", "beast"),
            (380, 280, "Snow Leopard Stalker", "beast"),
            (350, 210, "Frozen Lake Leviathan", "alpha"),
            (140, 170, "Astral Horn Guardian", "fast_travel"),
            (290, 420, "Glacial Pass Totem", "fast_travel"),
            (410, 340, "Frostveil Spire", "fast_travel"),

            (310, 720, "Dune Behemoth (Alpha)", "alpha"),
            (380, 770, "Terracotta Saber", "beast"),
            (250, 810, "Desert Drake", "beast"),
            (210, 730, "Scorched Scorpio (Alpha)", "alpha"),
            (430, 750, "Canyon Sandworm", "beast"),
            (330, 850, "Southern Dune Oasis", "fast_travel"),
            (260, 680, "Red Canyon Arch", "fast_travel"),
            (440, 820, "Sunken Ruins Totem", "fast_travel"),
            (170, 770, "Sunset Cape Totem", "fast_travel"),

            (630, 260, "Golden Gryphon (Alpha)", "alpha"),
            (690, 310, "Highland Drake", "beast"),
            (570, 220, "Amber Stag Lord", "beast"),
            (730, 260, "Crimson Raptor", "beast"),
            (660, 180, "Autumn Ridge Beacon", "fast_travel"),
            (540, 270, "Highland Gateway", "fast_travel"),

            (590, 490, "Forest Titan (Alpha)", "alpha"),
            (650, 430, "Great Primeval Elk", "beast"),
            (540, 560, "Cave Bear Patriarch (Alpha)", "alpha"),
            (710, 620, "Primal Boar Herd", "beast"),
            (490, 430, "River Valley Bison", "beast"),
            (520, 360, "Verdant Glade Totem", "fast_travel"),
            (610, 570, "Ancient Oak Spire", "fast_travel"),
            (680, 490, "Emerald Creek Beacon", "fast_travel"),
            (770, 580, "Eastern Shore Outpost", "fast_travel"),
            (470, 530, "Confluence Ford Totem", "fast_travel"),
            (430, 610, "Central Steppe Watch", "fast_travel"),
            (780, 680, "Southeast Cliffs Totem", "fast_travel"),
            (710, 740, "Verdant Cape Beacon", "fast_travel"),

            (890, 880, "Sanctuary Leviathan (Alpha)", "alpha"),
            (910, 860, "Sanctuary Waypoint", "fast_travel"),
            (860, 50, "North Sea Serpent", "alpha"),
            (310, 60, "Arctic Islet Totem", "fast_travel"),
        ]

        for bx, by, bname, pin_type in beast_defs:
            if pin_type == "alpha":
                draw.ellipse([bx - 16, by - 16, bx + 16, by + 16], fill=(18, 42, 78), outline=(245, 195, 45), width=2)
                draw.ellipse([bx - 11, by - 11, bx + 11, by + 11], fill=(28, 140, 220))
                draw.polygon([(bx, by - 9), (bx + 7, by - 2), (bx + 5, by + 6), (bx - 5, by + 6), (bx - 7, by - 2)], fill=(255, 250, 230))
                draw.text((bx + 18, by - 7), bname, fill=(255, 235, 140))
            elif pin_type == "fast_travel":
                draw.polygon([(bx, by - 12), (bx + 10, by), (bx, by + 12), (bx - 10, by)], fill=(12, 65, 115), outline=(65, 235, 255), width=2)
                draw.polygon([(bx, by - 6), (bx + 5, by), (bx, by + 6), (bx - 5, by)], fill=(220, 252, 255))
                draw.text((bx + 16, by - 6), bname, fill=(180, 240, 255))
            else:
                draw.ellipse([bx - 13, by - 13, bx + 13, by + 13], fill=(16, 48, 88), outline=(68, 215, 245), width=2)
                draw.ellipse([bx - 8, by - 8, bx + 8, by + 8], fill=(32, 145, 210))
                draw.polygon([(bx, by - 6), (bx + 5, by + 4), (bx - 5, by + 4)], fill=(240, 252, 255))
                draw.text((bx + 16, by - 6), bname, fill=(225, 242, 255))

        # 10. Map HUD: Zoom controls & Title Header
        draw.rectangle([W - 65, H - 95, W - 25, H - 35], fill=(18, 32, 52), outline=(55, 115, 165), width=2)
        draw.line([(W - 55, H - 75), (W - 35, H - 75)], fill=(200, 240, 255), width=3)
        draw.line([(W - 45, H - 85), (W - 45, H - 65)], fill=(200, 240, 255), width=3)
        draw.line([(W - 55, H - 52), (W - 35, H - 52)], fill=(200, 240, 255), width=3)
        draw.line([(W - 65, H - 65), (W - 25, H - 65)], fill=(55, 115, 165), width=1)

        draw.rectangle([25, 25, 320, 80], fill=(12, 24, 40), outline=(50, 160, 220), width=1)
        draw.text((36, 32), "THE PRIMEVAL CONTINENT", fill=(255, 235, 160))
        draw.text((36, 52), "STONE AGE OVERWORLD EXPEDITION", fill=(140, 215, 245))

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, "PNG")
        self.master_map_image = img
        return img
