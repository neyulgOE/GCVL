"""
Captures panoramic in-game screenshots of key natural Stone Age environments:
1. Colossal Mammoth Rib Fossils on Sandy Point Bar (Image 2)
2. Upstream Boulder Cascade & Rapids (Image 1 & 3)
3. Stepping Stone River Crossing (Image 1)
4. Temperate Valley Wildlife & Open Meadow (Ancient Bison, Giant Deer, Wolves)
"""

import os
import sys

sys.path.insert(0, os.path.abspath("libs"))
sys.path.insert(0, os.path.abspath("."))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()
screen = pygame.display.set_mode((1024, 640))

from src.core.game import Game
from tools.generate_primeval_world import load_canonical_atlas

views = [
    ("colossal_rib_fossils", 44 * 64, 40 * 64),
    ("upstream_cascade", 53 * 64, 12 * 64),
    ("stepping_stone_ford", 41 * 64, 36 * 64),
    ("meadow_wildlife", 29 * 64, 36 * 64),
]

out_dir = "debug_outputs/runtime_previews"
os.makedirs(out_dir, exist_ok=True)

for name, wx, wy in views:
    game = Game()
    game.free_cam.target.set_pos(wx, wy)
    game.camera.snap_to(game.free_cam.target.rect)

    for _ in range(60):
        game.update(1.0 / 60.0)
        game.render()

    out_file = os.path.join(out_dir, f"preview_{name}.png")
    pygame.image.save(game.screen, out_file)
    print(f"Captured {name} to {out_file}")

macro_file = os.path.join(out_dir, "preview_macro_watershed.png")
load_canonical_atlas().convert("RGB").save(macro_file, "PNG")
print(f"Captured macro watershed map to {macro_file}")

pygame.quit()
