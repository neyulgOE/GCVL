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

def run_smoke_test(total_frames=300):
    print(f"=== Starting Smoke Test Gate ({total_frames} frames headless) ===")
    start_time = time.time()
    try:
        import pygame
        pygame.init()
        screen = pygame.display.set_mode((1024, 640))

        from src.core.game import Game
        print("Initializing Game instance...")
        init_start = time.time()
        game = Game()
        print(f"Game initialized in {time.time() - init_start:.3f}s.")

        print(f"Simulating {total_frames} frames...")
        dt = 1.0 / 60.0
        for frame in range(1, total_frames + 1):
            game.update(dt)
            game.render()
            if frame % 60 == 0:
                print(f"  Frame {frame}/{total_frames} OK")

        pygame.quit()
        elapsed = time.time() - start_time
        print(f"=== SMOKE TEST PASSED: {total_frames} frames in {elapsed:.3f}s ({total_frames/elapsed:.1f} FPS) ===")
        return 0
    except Exception as e:
        import traceback
        print("\n!!! SMOKE TEST FAILED WITH EXCEPTION !!!")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_smoke_test(300))

