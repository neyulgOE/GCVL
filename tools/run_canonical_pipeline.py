"""Build the canonical Primeval Reach map and its 3D deliverables.

This is the only supported authoring pipeline for the current world:

    canonical atlas -> 200x200 world data -> texture/heightmap -> 3D preview/OBJ

The game runtime reads the same exported files.  Procedural atlas generators
are intentionally not imported here.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.generate_primeval_world import export_all
from tools.render_primeval_world_3d import main as export_3d


def run_canonical_pipeline() -> None:
    """Regenerate all canonical map and 3D outputs in dependency order."""
    export_all()
    export_3d()


if __name__ == "__main__":
    run_canonical_pipeline()
