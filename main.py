#!/usr/bin/env python3
"""
Stone Age: Dawn of Tribe - Khai Hoang Thời Đồ Đá.
2D Pixel Art Prehistoric Survival & Civilization Building Game.
Cross-platform: Linux & Windows.
"""

import sys
import os

# Add root directory and workspace libs to python path for module imports
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)
libs_dir = os.path.join(root_dir, "libs")
if os.path.exists(libs_dir):
    sys.path.insert(0, libs_dir)

from src.core.game import Game

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()
