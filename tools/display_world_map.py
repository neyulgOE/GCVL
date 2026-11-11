"""Display and capture the canonical Primeval Reach map and 3D runtime view.

Renders:
1. Canonical atlas and 3D deliverables.
2. Headless 3D runtime preview.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
libs_dir = ROOT / "libs"
if libs_dir.exists() and str(libs_dir) not in sys.path:
    sys.path.insert(0, str(libs_dir))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
from PIL import Image

from tools.run_canonical_pipeline import run_canonical_pipeline
from src.core.game_3d import Game3D

OUT_DIR = ROOT / "debug_outputs" / "runtime_previews"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("1. Building canonical Primeval Reach map and 3D deliverables...")
    run_canonical_pipeline()
    out_atlas = ROOT / "assets" / "sprites" / "primeval_reach_canonical_atlas.png"

    # Save artifact copy
    img = Image.open(out_atlas)
    artifact_macro = OUT_DIR / "preview_complete_world_map.png"
    img.save(artifact_macro)
    print(f"Saved complete world map artifact to: {artifact_macro}")

    print("2. Initializing canonical 3D runtime preview...")
    pygame.init()
    game = Game3D(headless=True)

    # Simulate 5 frames for rendering
    for _ in range(5):
        game.update(1.0 / 60.0)
        game.render()

    artifact_atlas = OUT_DIR / "preview_ingame_3d.png"
    pygame.image.save(game.screen, str(artifact_atlas))
    print(f"Saved 3D runtime preview to: {artifact_atlas}")

    pygame.quit()
    print("All world displays generated successfully!")


if __name__ == "__main__":
    main()
