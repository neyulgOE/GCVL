"""
Verification script for Prehistoric Stone Age RTS Overhaul.
Runs Pygame game instance headlessly for 120 frames, tests all rendering layers,
and exports in-game screenshots to assets/sprites/preview.png and artifact folder.
"""

import os
import sys

# Ensure local libs and workspace are in path
sys.path.insert(0, os.path.abspath("libs"))
sys.path.insert(0, os.path.abspath("."))

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
screen = pygame.display.set_mode((1024, 640))

from src.core.game import Game

print("Initializing Game instance...")
game = Game()
print("Game initialized successfully!")

# Advance simulation for 120 frames
print("Simulating 120 frames...")
for frame in range(120):
    game.update(1.0 / 60.0)
    game.render()
print("120 frames completed without exceptions!")

# Reveal settlement camp & river corridor in fog of war for clear tactical preview
game.fog_of_war.reveal_circle(41, 37, radius_tiles=25)
game.fog_of_war.reveal_circle(49, 36, radius_tiles=25)
game.fog_of_war.update_visibility([(41 * 64, 36 * 64, 25), (49 * 64, 36 * 64, 25)])

# Snap camera over central settlement camp and river bend
settlement_rect = pygame.Rect(41 * 64 - 200, 36 * 64 - 150, 400, 300)
game.camera.snap_to(settlement_rect)

# Draw and save in-game preview
game.render()
preview_path = "assets/sprites/preview.png"
pygame.image.save(game.screen, preview_path)
print(f"Saved in-game tactical preview to {preview_path}")

# Snap camera over S-Curve River, Point Bar and Stepping Stone Ford
river_rect = pygame.Rect(49 * 64 - 200, 36 * 64 - 150, 400, 300)
game.camera.snap_to(river_rect)
game.render()
preview_river_path = "assets/sprites/preview_river.png"
pygame.image.save(game.screen, preview_river_path)
print(f"Saved in-game river preview to {preview_river_path}")

# Now open Minimap Macro World Continent Tab and capture preview_macro_map.png
game.minimap.show_full_map = True
game.minimap._modal_alpha = 1.0
game.minimap.viewing_zone = "macro"
game.render()
macro_preview_path = "assets/sprites/preview_macro_map.png"
pygame.image.save(game.screen, macro_preview_path)
print(f"Saved macro continent preview to {macro_preview_path}")

# Now open Minimap Flora Ecology Atlas Tab and capture preview_flora_atlas.png
game.minimap.show_full_map = True
game.minimap._modal_alpha = 1.0
game.minimap.viewing_zone = "flora"
game.render()
flora_preview_path = "assets/sprites/preview_flora_atlas.png"
pygame.image.save(game.screen, flora_preview_path)
print(f"Saved flora atlas preview to {flora_preview_path}")

# Also copy all to artifact directory
import shutil
artifact_dir = "/home/huyen1905/.gemini/antigravity/brain/fed854e2-3b10-4d89-9cc2-ce9ec962f36a"
if os.path.exists(artifact_dir):
    shutil.copy(preview_path, os.path.join(artifact_dir, "preview.png"))
    shutil.copy(preview_river_path, os.path.join(artifact_dir, "preview_river.png"))
    shutil.copy(macro_preview_path, os.path.join(artifact_dir, "preview_macro_map.png"))
    shutil.copy(flora_preview_path, os.path.join(artifact_dir, "preview_flora_atlas.png"))
    print("Copied all previews to artifact directory!")

pygame.quit()
print("All verification steps passed cleanly!")
