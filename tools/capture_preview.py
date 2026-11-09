"""
Captures a preview screenshot of the in-game world.
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

game = Game()
# Center camera on the river and central savanna
game.free_cam.target.set_pos(45 * 64, 38 * 64)
game.camera.snap_to(game.free_cam.target.rect)

# Run 60 frames to settle particles and animations
for _ in range(60):
    game.update(1.0 / 60.0)
    game.render()

out_path = "/home/huyen1905/.gemini/antigravity/brain/fed854e2-3b10-4d89-9cc2-ce9ec962f36a/preview_nature_world.png"
pygame.image.save(game.screen, out_path)
print(f"Saved nature preview to {out_path}")
pygame.quit()
