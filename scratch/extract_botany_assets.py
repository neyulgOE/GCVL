"""
Extraction script for Prehistoric Botany, Trees, and Foraging Assets.
Slices 3 reference sheets into transparent PNGs with feathered alphas:
1. ref_trees_spritesheet.jpg -> assets/trees/
2. ref_flora_lifecycle_spritesheet.jpg -> assets/flora/
3. ref_foraging_props_icons.jpg -> assets/ui/icons/ & assets/items/
"""

import os
import numpy as np
from PIL import Image

os.makedirs("assets/trees", exist_ok=True)
os.makedirs("assets/flora", exist_ok=True)
os.makedirs("assets/ui/icons", exist_ok=True)
os.makedirs("assets/items", exist_ok=True)

def remove_background_and_feather(im, bg_rgb, dist_thresh=28.0, feather_px=4):
    """Converts a cropped PIL image to RGBA, making pixels close to bg_rgb transparent with soft alpha falloff."""
    arr = np.array(im.convert("RGB"), dtype=float)
    bg = np.array(bg_rgb, dtype=float)
    dist = np.linalg.norm(arr - bg, axis=2)
    
    # Alpha mask: 0 if dist <= dist_thresh, 255 if dist >= dist_thresh + feather_px * 6
    alpha = np.clip((dist - dist_thresh) / (feather_px * 6.0), 0.0, 1.0) * 255.0
    alpha = alpha.astype(np.uint8)

    rgba = np.dstack((arr.astype(np.uint8), alpha))
    return Image.fromarray(rgba, "RGBA")


# =========================================================================
# 1. EXTRACT ICONS & CRAFTING PROPS (assets/sprites/ref_foraging_props_icons.jpg)
# =========================================================================
print("Extracting foraging icons & props...")
icons_im = Image.open("assets/sprites/ref_foraging_props_icons.jpg")
icons_bg = [36, 42, 54]

icon_col_ranges = [(188, 314), (365, 491), (542, 664), (716, 843)]
icon_row_ranges = [(19, 151), (164, 283), (301, 411), (432, 554)]

icon_names = [
    # Row 0: Baskets
    ["basket_berries", "basket_nuts", "basket_mushrooms", "basket_empty"],
    # Row 1: Fibers & Thatch
    ["fiber_cordage", "thatch_bundle", "resin_bowl", "plant_stalks"],
    # Row 2: Tubers, Grains, Honey
    ["wild_tubers", "roasted_acorns", "honeycomb", "grain_sheaf"],
    # Row 3: Herbalism & Medicine
    ["medicine_pouch", "poultice_wrap", "mortar_pestle", "dried_herbs"]
]

for r_idx, r_range in enumerate(icon_row_ranges):
    for c_idx, c_range in enumerate(icon_col_ranges):
        name = icon_names[r_idx][c_idx]
        x0, x1 = c_range
        y0, y1 = r_range
        # Padding
        crop = icons_im.crop((max(0, x0 - 4), max(0, y0 - 4), min(1024, x1 + 4), min(572, y1 + 4)))
        clean = remove_background_and_feather(crop, icons_bg, dist_thresh=24.0, feather_px=3)
        
        # Save to both icons and items
        clean.save(f"assets/ui/icons/{name}.png")
        clean.save(f"assets/items/{name}.png")
print("Saved 16 foraging & botanical crafting icons!")


# =========================================================================
# 2. EXTRACT 3-STAGE FLORA LIFECYCLE (assets/sprites/ref_flora_lifecycle_spritesheet.jpg)
# =========================================================================
print("Extracting 3-stage flora lifecycle...")
flora_im = Image.open("assets/sprites/ref_flora_lifecycle_spritesheet.jpg")
flora_bg = [48, 52, 56]

# 4 Rows:
# Row 0: Berries (Bramble, Cloudberry, Elderberry)
# Row 1: Grains & Fibers (Einkorn, Flax, Cattail)
# Row 2: Underground Tubers (Taro, Burdock, Garlic)
# Row 3: Fungi & Herbs (Mushroom, Cave Fungi, Red Herb)
flora_rows = [
    ("berries", (28, 128), ["bramble", "cloudberry", "elderberry"]),
    ("grain_fiber", (156, 275), ["einkorn", "flax", "cattail"]),
    ("tubers", (296, 416), ["taro", "burdock", "garlic"]),
    ("fungi_herbs", (440, 557), ["mushroom", "cavefungi", "herb"])
]

# 3 Stage Column Trios:
# Unripe Sprout (3 variants)
sprout_cols = [(34, 100), (134, 206), (238, 310)]
# Ripe Harvestable (3 variants)
ripe_cols = [(346, 456), (462, 566), (572, 674)]
# Depleted Foraged (3 variants)
depleted_cols = [(700, 796), (818, 894), (918, 1002)]

for cat, (y0, y1), species_list in flora_rows:
    for v_idx, species in enumerate(species_list):
        # 1. Unripe Sprout
        sx0, sx1 = sprout_cols[v_idx]
        scrop = flora_im.crop((sx0, y0, sx1, y1))
        sclean = remove_background_and_feather(scrop, flora_bg, dist_thresh=22.0, feather_px=3)
        sclean.save(f"assets/flora/{species}_sprout.png")

        # 2. Ripe Harvestable
        rx0, rx1 = ripe_cols[v_idx]
        rcrop = flora_im.crop((rx0, y0, rx1, y1))
        rclean = remove_background_and_feather(rcrop, flora_bg, dist_thresh=22.0, feather_px=3)
        rclean.save(f"assets/flora/{species}_ripe.png")

        # 3. Depleted Foraged
        dx0, dx1 = depleted_cols[v_idx]
        dcrop = flora_im.crop((dx0, y0, dx1, y1))
        dclean = remove_background_and_feather(dcrop, flora_bg, dist_thresh=22.0, feather_px=3)
        dclean.save(f"assets/flora/{species}_depleted.png")

print("Saved 36 flora lifecycle sprites (12 species x 3 stages)!")


# =========================================================================
# 3. EXTRACT TREES & WOODCUTTING PROGRESSION (assets/sprites/ref_trees_spritesheet.jpg)
# =========================================================================
print("Extracting prehistoric trees & woodcutting...")
trees_im = Image.open("assets/sprites/ref_trees_spritesheet.jpg")
trees_bg = [215, 192, 148]

# Tree crops by biome and progression
tree_slices = {
    # Primeval Forest
    "giant_tree_fern": (24, 14, 118, 135),
    "cycad": (225, 14, 313, 135),
    "araucaria_monkey_pine": (424, 14, 503, 135),
    
    # Steppe & Megalithic Highlands
    "steppe_ginkgo": (26, 144, 104, 270),
    "ancient_gnarled_oak": (208, 144, 328, 270),
    "resin_pine": (431, 144, 499, 270),
    
    # Tundra
    "tundra_spruce": (30, 279, 97, 404),
    "krummholz_dwarf_pine": (208, 279, 320, 404),
    "frost_white_birch": (426, 279, 501, 404),
    
    # Ancient Swamp / Mangrove
    "aerial_root_mangrove": (23, 414, 108, 546),
    "mossy_swamp_cypress": (196, 414, 329, 546),
    "hollow_log": (340, 420, 501, 540),
    
    # Woodcutting Progression (Row 3 right side)
    "tree_intact": (529, 414, 649, 546),
    "tree_chopped": (656, 414, 775, 546),
    "tree_stump": (779, 450, 840, 546),
    "timber_logs_bundle": (859, 450, 922, 546),
    "timber_logs_stack": (932, 450, 998, 546)
}

for name, (x0, y0, x1, y1) in tree_slices.items():
    crop = trees_im.crop((x0, y0, x1, y1))
    clean = remove_background_and_feather(crop, trees_bg, dist_thresh=26.0, feather_px=4)
    clean.save(f"assets/trees/{name}.png")

print("Saved 17 prehistoric tree & woodcutting progression sprites!")
print("All botany extraction completed successfully!")
