"""
Headless Smoke Test Gate for Stone Age Nature Observation Simulator.
Runs game headless for 300 frames (update + render), exits 0 on success, 1 on error.
"""

import os
import sys
import time

# Ensure local libs and project root are in sys.path
sys.path.insert(0, os.path.abspath("libs"))
sys.path.insert(0, os.path.abspath("."))

# Enforce headless mode
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

def run_smoke_test(total_frames=180):
    print(f"=== Starting Smoke Test Gate ({total_frames} frames headless) ===")
    start_time = time.time()
    try:
        import pygame
        pygame.init()
        screen = pygame.display.set_mode((1024, 640))

        # 1. Kiểm thử Engine 3D Phối cảnh (Game3D)
        print("--- [1/2] Kiểm thử 3D Perspective Spectator Engine (Game3D) ---")
        from src.core.game_3d import Game3D
        g3d = Game3D(headless=True)
        print("Game3D initialized. Simulating frames...")
        dt = 1.0 / 60.0
        for frame in range(1, total_frames + 1):
            g3d.update(dt)
            g3d.render()
            if frame % 60 == 0:
                print(f"  [3D] Frame {frame}/{total_frames} OK")

        # 2. Kiểm thử Engine 2D Mô phỏng Sinh thái (Game)
        print("--- [2/2] Kiểm thử 2D Wilderness Simulation Engine (Game) ---")
        from src.core.game import Game
        game = Game()
        print("Game 2D initialized. Simulating frames...")
        for frame in range(1, total_frames + 1):
            game.update(dt)
            game.render()
            if frame % 60 == 0:
                print(f"  [2D] Frame {frame}/{total_frames} OK")

        pygame.quit()
        elapsed = time.time() - start_time
        print(f"=== SMOKE TEST PASSED: Cả 2 Engine 3D và 2D đều vượt qua trong {elapsed:.3f}s! ===")
        return 0
    except Exception as e:
        import traceback
        print("\n!!! SMOKE TEST FAILED WITH EXCEPTION !!!")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_smoke_test(300))

