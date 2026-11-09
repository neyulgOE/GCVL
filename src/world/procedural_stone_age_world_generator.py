"""
Prehistoric Island Archipelago World Generator (Palworld & AAA-Style Topographic Overworld).
Creates an organic island continent surrounded by deep ocean with:
1. Four High-Contrast Prehistoric Biomes:
   - Northwest: Glacial Alpine Peaks & Knife-Edge Snow Crags (Astral Peaks)
   - Southwest: Terracotta Badlands & Amber Desert Dunes (Dunes of the Desiccated)
   - Central & East: Emerald Primeval Forest & Winding River Valleys (Verdant Wilds)
   - Northeast: Autumn Highlands & Amber Plateau (Amber Steppes)
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
from PIL import Image
from tools.build_palworld_masterpiece import generate_palworld_overworld, FastFbmNoise


class FastVectorNoise2D(FastFbmNoise):
    pass


class ProceduralStoneAgeWorldGenerator:
    """
    Overworld Generator creating an iconic island archipelago map on par with AAA adventure maps (Palworld style).
    """
    def __init__(self, width: int = 200, height: int = 200, world_key: int = 2026):
        self.width = width
        self.height = height
        self.world_key = world_key
        self.noise = FastFbmNoise(world_key)
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
        - 4 High-contrast biomes (Snow Massif, Amber Sand Dunes, Lush Emerald Forest, Autumn Plateau)
        - 3D Ridged mountain topography with directional northwest hillshading
        - Glowing aquamarine reef shelves hugging the jagged coastline
        - Delicate navigation grid and 40+ Prehistoric Alpha Boss / Fauna Pins
        """
        img = generate_palworld_overworld(
            render_resolution,
            render_resolution,
            self.world_key,
            output_path
        )
        self.master_map_image = img
        return img
