"""Display and capture the complete grand prehistoric world map and in-game atlas views.

Renders:
1. High-resolution Grand Continental Overworld Map ("ĐẠI LỤC NGUYÊN SINH").
2. In-game Full-Screen Atlas View (Simulating pressing 'M' in-game with Spectator Tracking).
3. Panoramic in-game observation views across the primeval world.
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

from tools.build_multi_continent_world import generate_multi_continent_overworld
from src.core.game import Game

OUT_DIR = Path("/home/huyen1905/.gemini/antigravity/brain/fed854e2-3b10-4d89-9cc2-ce9ec962f36a")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("1. Generating Grand Multi-Continent Overworld Map (1024x1024)...")
    out_macro = ROOT / "assets" / "sprites" / "world_overview_macro.png"
    generate_multi_continent_overworld(out_path=out_macro, size_px=1024)

    # Save artifact copy
    img = Image.open(out_macro)
    artifact_macro = OUT_DIR / "preview_complete_world_map.png"
    img.save(artifact_macro)
    print(f"Saved complete world map artifact to: {artifact_macro}")

    print("2. Initializing Game and capturing Full-Screen Atlas View...")
    pygame.init()
    game = Game()

    # Move free camera to valley center and toggle full map
    game.free_cam.target.set_pos(42.0 * 64.0, 36.0 * 64.0)
    game.camera.snap_to(game.free_cam.target.rect)
    game.minimap.viewing_zone = "macro"
    game.minimap.show_full_map = True
    game.minimap._modal_alpha = 1.0

    # Simulate 5 frames for rendering
    for _ in range(5):
        game.update(1.0 / 60.0)
        game.render()

    artifact_atlas = OUT_DIR / "preview_ingame_atlas.png"
    pygame.image.save(game.screen, str(artifact_atlas))
    print(f"Saved in-game atlas preview to: {artifact_atlas}")

    print("3. Capturing In-Game Natural World Views...")
    # View A: Natural Valley View with Spectator Camera HUD & Minimap
    game.minimap.show_full_map = False
    game.minimap._modal_alpha = 0.0
    for _ in range(30):
        game.update(1.0 / 60.0)
        game.render()

    artifact_ingame = OUT_DIR / "preview_ingame_world.png"
    pygame.image.save(game.screen, str(artifact_ingame))
    print(f"Saved in-game world view to: {artifact_ingame}")

    pygame.quit()
    print("All world displays generated successfully!")


if __name__ == "__main__":
    main()

