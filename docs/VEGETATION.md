# Primeval Reach vegetation baseline

The current world uses a deliberately cool **Late Paleolithic** baseline. The
Stone Age is not one single climate period, so this is a worldbuilding choice:
the northern highlands and high elevations are tundra/taiga, while the southern
forest, steppe and wetland regions remain productive.

`src/world/canonical_ecology.py` derives the vegetation layers from canonical
WorldData instead of making a second map:

- `temperature`: relative temperature, cooled by north-facing latitude and elevation;
- `moisture`: biome and distance-to-water signal;
- `canopy_cover`: large trees and conifers;
- `shrub_cover`: berries and low undergrowth;
- `ground_cover`: reeds, herbs and mushrooms;
- `vegetation_density`: combined ecological coverage used for diagnostics.

The first sprite mapping is intentionally conservative:

| Habitat | Canopy | Understory / ground |
| --- | --- | --- |
| Glacial / cold forest | tundra spruce + birch | sparse berry, mushroom, reed near water |
| Primeval forest | fern/cycad tree variants | berry bushes, mushrooms |
| Autumn steppe | steppe oak/pine | sparse berry scrub and grass/reed near water |
| Sanctuary / wetland edge | swamp mangrove, forest trees | berries, reeds, mushrooms |
| Terracotta desert | almost no trees | only very sparse scrub placeholder |

Run the canonical build to regenerate the layers and samples:

```bash
python3 tools/run_canonical_pipeline.py
python3 tools/render_world_samples.py
```

No `pydew` or `sprout_lands` vegetation is used by this layer.
