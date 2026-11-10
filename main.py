"""
Stone Age: Primeval World - Bộ Mô Phỏng & Quan Sát Hệ Sinh Thái Tiền Sử.
Thế giới hoang dã tự nhiên 100% (Pure Primeval Nature Simulator).
Camera tự do (Spectator Free-Cam), địa hình phân tầng và động vật cổ đại.
"""

import sys
import os

# Add root directory and workspace libs to python path for module imports
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)
libs_dir = os.path.join(root_dir, "libs")
if os.path.exists(libs_dir):
    sys.path.insert(0, libs_dir)

if os.environ.get("GCVL_RENDERER", "3d").lower() == "2d":
    from src.core.game import Game
else:
    from src.core.game_3d import Game3D as Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
