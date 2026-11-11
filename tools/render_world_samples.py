"""Render a small, reproducible set of canonical world sample images."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.core.game_3d import Game3D
from tools.run_canonical_pipeline import run_canonical_pipeline


OUT_DIR = ROOT / "debug_outputs" / "runtime_previews"


def apply_preset(game: Game3D, key: int | None) -> None:
    if key is None:
        return
    preset = game.CAMERA_PRESETS[key]
    game.cam_x = preset["pos"][0] * game.grid_scale_x * game.TILE_SIZE_3D
    game.cam_y = preset["pos"][1]
    game.cam_z = preset["pos"][2] * game.grid_scale_z * game.TILE_SIZE_3D
    game.yaw = preset["yaw"]
    game.pitch = preset["pitch"]
    game.current_preset_name = preset["name"]


def render_sample(name: str, key: int | None) -> Path:
    game = Game3D(headless=True)
    apply_preset(game, key)
    for _ in range(8):
        game.update(1.0 / 60.0)
        game.render()
    out_path = OUT_DIR / f"sample_{name}.png"
    pygame.image.save(game.screen, str(out_path))
    pygame.quit()
    print(f"[SAMPLES] {out_path}")
    return out_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_canonical_pipeline()
    pygame.init()
    samples = [
        ("global", None),
        ("glacial_northwest", pygame.K_1),
        ("terracotta_southwest", pygame.K_2),
        ("autumn_northeast", pygame.K_3),
        ("southern_delta", pygame.K_4),
    ]
    for name, key in samples:
        render_sample(name, key)


if __name__ == "__main__":
    main()
