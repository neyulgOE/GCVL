# Primeval Reach vegetation baseline

The current world uses a deliberately cool **Late Paleolithic** baseline. The
Stone Age is not one single climate period, so this is a worldbuilding choice:
the northern highlands and high elevations are tundra/taiga, while the southern
forest, steppe and wetland regions remain productive.

`src/world/canonical_ecology.py` derives the vegetation layers from canonical
WorldData instead of making a second map. The placement pass is hierarchical:
mature trees reserve space first, then lower layers fill the remaining habitat
with smaller occupancy radii. This keeps forest clusters organic and preserves
open megafauna corridors.

- `temperature`: relative temperature, cooled by north-facing latitude and elevation;
- `moisture`: biome and distance-to-water signal;
- `canopy_cover`: large trees and conifers;
- `shrub_cover`: berries and low undergrowth;
- `ground_cover`: reeds, herbs and mushrooms;
- `vegetation_density`: combined ecological coverage used for diagnostics.

The persisted flora data has six ordered layers:

1. `emergent` — rare giant forest/sanctuary trees;
2. `canopy` — forest, steppe grove, tundra and wetland trees;
3. `understory` — shade and water-edge low growth;
4. `shrub` — forest-edge berry bushes and scrub;
5. `herb_ground` — reeds, mushrooms, moss and tuber/herb patches;
6. `litter_soil` — fallen branches, clay deposits and exposed ore records.

The generator writes the exact instances to
`debug_outputs/primeval_world_flora.json` and compact arrays into
`debug_outputs/primeval_world_data.npz`. `Game3D` consumes those persisted
instances and applies distance-based LOD so small ground props disappear first
at long range while the canopy silhouette remains stable.

The first sprite mapping is intentionally conservative:

| Habitat | Canopy | Understory / ground |
| --- | --- | --- |
| Glacial / cold forest | tundra spruce + birch | sparse berry, mushroom, reed near water |
| Primeval forest | fern/cycad tree variants | berry bushes, mushrooms |
| Autumn steppe | steppe oak/pine | sparse berry scrub and grass/reed near water |
| Sanctuary / wetland edge | swamp mangrove, forest trees | berries, reeds, mushrooms |
| Terracotta desert | almost no trees; only oasis-edge grove candidates | sparse scrub/soil records |

Run the canonical build to regenerate the layers and samples:

```bash
python3 tools/run_canonical_pipeline.py
python3 tools/render_world_samples.py
```

No `pydew` or `sprout_lands` vegetation is used by this layer.
