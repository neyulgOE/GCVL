# GCVL world pipeline

The current map is authored from the canonical atlas supplied for Primeval
Reach.  There is one supported build path:

```text
assets/sprites/primeval_reach_canonical_atlas.png
        |
        v
tools/generate_primeval_world.py
        |
        +--> debug_outputs/primeval_world_data.npz + manifest.json
        +--> stone_age_world_200x200.json (compatibility only)
        +--> debug_outputs/primeval_world_texture.png
        +--> debug_outputs/primeval_world_heightmap.png
        +--> debug_outputs/primeval_world_vegetation_density.png
        +--> debug_outputs/primeval_world_temperature.png
        +--> assets/sprites/world_atlas.png
        +--> assets/sprites/world_overview_macro.png
        |
        v
tools/render_primeval_world_3d.py
        |
        +--> debug_outputs/primeval_world.obj/.mtl
        +--> debug_outputs/primeval_world_3d_preview.png
        |
        v
main.py -> src/core/game_3d.py
```

Run the complete export with:

```bash
python3 tools/run_canonical_pipeline.py
```

`main.py` uses the 3D runtime by default. The 2D renderer remains available
only as a compatibility view:

```bash
GCVL_RENDERER=2d python3 main.py
```

## Files that are not canonical

- `tools/run_full_primeval_reach_pipeline.py` and `tools/run_phase*.py` are
  experimental procedural validation pipelines. They write only under
  `debug_outputs/experimental_*` and must not replace the canonical atlas.
- `tools/build_*.py` are historical procedural generators kept for reference.
  They are not used by the game or the canonical build.
- `_removed/`, `scratch/`, and the all-in-one asset bundle are archival or
  development material, not runtime entry points.

Do not run a historical generator as a map build command. If the canonical
atlas changes, run `tools/run_canonical_pipeline.py` so the JSON, texture,
heightmap, WorldData, OBJ, and preview stay synchronized. Runtime 3D reads
`primeval_world_data.npz`; the 200x200 JSON is retained only for older tools.
