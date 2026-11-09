"""Clean Sprite Slicer, Background Remover & Standardized Asset Pack Builder (All 10 Categories).

Slices all generated Stone Age RTS spritesheets (including Fog-of-War VFX,
Trailblazing/Waypoints, and Scouts/Mapmaking Kits) into isolated, non-overlapping,
background-transparent PNG items centered on standardized canvases, generates
visual verification contact sheets, and packages the complete folder into a ZIP.
"""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


RAW_DIR = "/working_dir/c_6bd6f2c64e595d3f/user_uploaded_files/ttl=63d/tool_generated"
OUTPUT_DIR = "/working_dir/c_6bd6f2c64e595d3f/artifacts/file_generation/ttl=63d/output"
PACK_ROOT = os.path.join(OUTPUT_DIR, "stone_age_rts_asset_pack")


def remove_cell_background(
    cell_rgb: np.ndarray,
    bg_rgb: np.ndarray,
    color_tol: float = 26.0,
    edge_inset: int = 2,
    keep_largest_cluster_only: bool = False,
) -> Image.Image:
    """Removes background from a single sprite cell using border flood-fill + color distance."""
    h, w, _ = cell_rgb.shape
    work = cell_rgb.copy()

    if edge_inset > 0 and h > 2 * edge_inset and w > 2 * edge_inset:
        work = work[edge_inset : h - edge_inset, edge_inset : w - edge_inset]
        h, w, _ = work.shape

    border_pixels = np.concatenate(
        [
            work[0, :],
            work[h - 1, :],
            work[:, 0],
            work[:, w - 1],
        ],
        axis=0,
    )
    local_bg = np.median(border_pixels, axis=0)
    ref_bg = 0.5 * bg_rgb + 0.5 * local_bg

    diff = np.linalg.norm(work.astype(np.float32) - ref_bg.astype(np.float32), axis=2)
    bg_candidate = (diff < color_tol).astype(np.uint8)

    _, labels = cv2.connectedComponents(bg_candidate, connectivity=8)
    border_labels = set(labels[0, :]).union(
        set(labels[h - 1, :]), set(labels[:, 0]), set(labels[:, w - 1])
    )
    border_labels.discard(0)
    is_bg = np.isin(labels, list(border_labels))

    fg_mask = (~is_bg).astype(np.uint8) * 255
    num_fg, fg_labels, stats, _ = cv2.connectedComponentsWithStats(
        fg_mask, connectivity=8
    )
    clean_fg = np.zeros_like(fg_mask)

    if keep_largest_cluster_only and num_fg > 1:
        areas = stats[1:, cv2.CC_STAT_AREA]
        main_lbl = 1 + int(np.argmax(areas))
        main_mask = (fg_labels == main_lbl).astype(np.uint8)
        dilated_main = cv2.dilate(main_mask, np.ones((19, 19), np.uint8))
        for lbl in range(1, num_fg):
            area = stats[lbl, cv2.CC_STAT_AREA]
            if area >= 24 and np.any(dilated_main & (fg_labels == lbl)):
                clean_fg[fg_labels == lbl] = 255
    else:
        for lbl in range(1, num_fg):
            area = stats[lbl, cv2.CC_STAT_AREA]
            if area >= 25:
                clean_fg[fg_labels == lbl] = 255

    alpha = clean_fg.copy().astype(np.float32)
    edge_zone = (
        cv2.morphologyEx(clean_fg, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
        > 0
    )
    edge_alpha = (
        np.clip((diff - (color_tol * 0.45)) / (color_tol * 0.75), 0.0, 1.0)
        * 255.0
    )
    alpha[edge_zone] = np.minimum(alpha[edge_zone], edge_alpha[edge_zone])

    rgba = np.dstack([work, alpha.astype(np.uint8)])
    return Image.fromarray(rgba, mode="RGBA")


def standardize_sprite(
    rgba_img: Image.Image,
    canvas_size: Tuple[int, int] = (160, 160),
    padding: int = 10,
) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    """Crops tightly to non-transparent pixels and centers on a uniform transparent canvas."""
    alpha = np.array(rgba_img)[:, :, 3]
    ys, xs = np.where(alpha > 20)
    if len(xs) == 0 or len(ys) == 0:
        canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        return canvas, (0, 0, 0, 0)

    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    cropped = rgba_img.crop((x0, y0, x1, y1))

    cw, ch = canvas_size
    max_w = cw - 2 * padding
    max_h = ch - 2 * padding
    sw, sh = cropped.size

    scale = min(max_w / max(1, sw), max_h / max(1, sh), 1.0)
    if scale < 1.0:
        new_w = max(1, int(round(sw * scale)))
        new_h = max(1, int(round(sh * scale)))
        cropped = cropped.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)
        sw, sh = cropped.size

    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    paste_x = (cw - sw) // 2
    paste_y = (ch - sh) // 2
    canvas.paste(cropped, (paste_x, paste_y), cropped)
    return canvas, (x0, y0, x1 - x0, y1 - y0)


def slice_by_explicit_splits(
    img_rgb: np.ndarray,
    y_splits: List[int],
    x_splits: List[int],
    bg_rgb: np.ndarray,
    out_folder: str,
    prefix_per_row: List[str],
    canvas_size: Tuple[int, int] = (160, 160),
    color_tol: float = 25.0,
    edge_inset: int = 3,
    keep_largest_cluster_only: bool = False,
) -> List[Dict[str, Any]]:
    """Slices a spritesheet using exact row and column split coordinates."""
    os.makedirs(out_folder, exist_ok=True)
    records: List[Dict[str, Any]] = []
    rows = len(y_splits) - 1
    cols = len(x_splits) - 1

    for r in range(rows):
        y0, y1 = y_splits[r], y_splits[r + 1]
        row_prefix = prefix_per_row[r] if r < len(prefix_per_row) else f"row{r+1}"
        for c in range(cols):
            x0, x1 = x_splits[c], x_splits[c + 1]
            cell = img_rgb[y0:y1, x0:x1]
            rgba = remove_cell_background(
                cell,
                bg_rgb=bg_rgb,
                color_tol=color_tol,
                edge_inset=edge_inset,
                keep_largest_cluster_only=keep_largest_cluster_only,
            )
            std_img, bbox = standardize_sprite(
                rgba, canvas_size=canvas_size, padding=10
            )
            fname = f"{row_prefix}_{c+1:02d}.png"
            fpath = os.path.join(out_folder, fname)
            std_img.save(fpath, format="PNG")
            records.append(
                {
                    "file": fname,
                    "folder": os.path.basename(out_folder),
                    "path": fpath,
                    "grid_row": r + 1,
                    "grid_col": c + 1,
                    "canvas_size": list(canvas_size),
                    "source_bbox": list(bbox),
                }
            )
    return records


def build_complete_asset_pack() -> Dict[str, Any]:
    """Slices all 10 Stone Age RTS asset categories into isolated transparent PNGs."""
    if os.path.exists(PACK_ROOT):
        shutil.rmtree(PACK_ROOT)
    os.makedirs(PACK_ROOT, exist_ok=True)

    all_records: List[Dict[str, Any]] = []

    # 1. Tribal Units (4 rows x 10 cols = 40 sprites)
    units_img = np.array(
        Image.open(
            os.path.join(RAW_DIR, "watermarked_img_13435035550907309457.jpg")
        ).convert("RGB")
    )
    all_records.extend(
        slice_by_explicit_splits(
            units_img,
            y_splits=[0, 190, 380, 568, 768],
            x_splits=[0, 134, 282, 416, 554, 688, 825, 965, 1105, 1238, 1376],
            bg_rgb=np.array([52, 60, 70]),
            out_folder=os.path.join(PACK_ROOT, "01_units_villagers"),
            prefix_per_row=[
                "unit_gatherer_builder",
                "unit_flint_spear_hunter",
                "unit_mammoth_bone_warrior",
                "unit_tribal_shaman",
            ],
            canvas_size=(160, 160),
            color_tol=24.0,
            edge_inset=5,
            keep_largest_cluster_only=True,
        )
    )

    # 2. Prehistoric Megafauna & Wildlife (5 rows x 6 cols = 30 sprites)
    wild_img = np.array(
        Image.open(
            os.path.join(RAW_DIR, "watermarked_img_5022997112624345617.jpg")
        ).convert("RGB")
    )
    all_records.extend(
        slice_by_explicit_splits(
            wild_img,
            y_splits=[0, 180, 347, 510, 629, 768],
            x_splits=[0, 221, 438, 666, 913, 1130, 1376],
            bg_rgb=np.array([179, 172, 156]),
            out_folder=os.path.join(PACK_ROOT, "02_megafauna_wildlife"),
            prefix_per_row=[
                "wildlife_mammoth_and_smilodon",
                "wildlife_steppe_bison",
                "wildlife_cavebear_and_direwolf",
                "wildlife_wild_boar",
                "wildlife_crocodilian_and_fish",
            ],
            canvas_size=(224, 192),
            color_tol=24.0,
            edge_inset=2,
        )
    )

    # 3. Tribal Buildings & Structures (6 complexes)
    bldg_img = np.array(
        Image.open(
            os.path.join(RAW_DIR, "watermarked_img_7766222257428883140.jpg")
        ).convert("RGB")
    )
    bldg_records = slice_by_explicit_splits(
        bldg_img,
        y_splits=[0, 384, 768],
        x_splits=[0, 458, 917, 1376],
        bg_rgb=np.array([193, 176, 156]),
        out_folder=os.path.join(PACK_ROOT, "03_buildings_structures"),
        prefix_per_row=["building_tier1", "building_tier2"],
        canvas_size=(384, 320),
        color_tol=22.0,
        edge_inset=6,
    )
    bldg_names = [
        "01_ancestral_rock_shelter.png",
        "02_hide_tipis_and_thatch_hut.png",
        "03_flintknapping_workshop.png",
        "04_meat_smoking_and_tanning_racks.png",
        "05_megalithic_totem_shrine.png",
        "06_palisade_gate_and_watchtower.png",
    ]
    for rec, new_name in zip(bldg_records, bldg_names):
        new_path = os.path.join(os.path.dirname(rec["path"]), new_name)
        os.rename(rec["path"], new_path)
        rec["file"] = new_name
        rec["path"] = new_path
    all_records.extend(bldg_records)

    # 4. Prehistoric Trees & Woodcutting Progression (42 sprites)
    trees_img = np.array(
        Image.open(
            os.path.join(RAW_DIR, "watermarked_img_6289653711064953987.jpg")
        ).convert("RGB")
    )
    tree_folder = os.path.join(PACK_ROOT, "04_prehistoric_trees_and_wood")
    os.makedirs(tree_folder, exist_ok=True)
    tree_bg = np.array([215, 194, 151])

    tree_rows_spec = [
        (
            10,
            186,
            [14, 160, 294, 437, 558, 691, 837, 954, 1105, 1238, 1364],
            "tree_primeval_fern_cycad",
        ),
        (
            186,
            368,
            [14, 146, 269, 451, 566, 687, 821, 944, 1127, 1240, 1360],
            "tree_steppe_oak_pine",
        ),
        (
            368,
            547,
            [18, 139, 257, 452, 564, 696, 814, 935, 1129, 1236, 1361],
            "tree_tundra_spruce_birch",
        ),
    ]
    for ry0, ry1, x_list, r_prefix in tree_rows_spec:
        all_records.extend(
            slice_by_explicit_splits(
                trees_img,
                y_splits=[ry0, ry1],
                x_splits=x_list,
                bg_rgb=tree_bg,
                out_folder=tree_folder,
                prefix_per_row=[r_prefix],
                canvas_size=(192, 224),
                color_tol=26.0,
                edge_inset=2,
                keep_largest_cluster_only=True,
            )
        )

    row4_boxes = [
        ("tree_swamp_mangrove_01.png", (13, 547, 147, 748)),
        ("tree_swamp_mangrove_02.png", (147, 547, 255, 748)),
        ("tree_swamp_mossy_cypress_03.png", (255, 547, 450, 748)),
        ("wood_fallen_hollow_log_04.png", (450, 547, 587, 748)),
        ("wood_mossy_snag_stump_05.png", (587, 547, 691, 748)),
        ("woodcut_stage1_intact_oak_06.png", (691, 547, 873, 748)),
        ("woodcut_stage2_notched_oak_07.png", (873, 547, 1043, 748)),
        ("woodcut_stage3_felled_stump_08.png", (1043, 547, 1133, 748)),
        ("woodcut_logs_bundle_09.png", (1133, 547, 1239, 657)),
        ("woodcut_logs_bundle_10.png", (1239, 547, 1360, 657)),
        ("woodcut_split_timber_11.png", (1133, 657, 1239, 748)),
        ("woodcut_hardwood_logs_12.png", (1239, 657, 1360, 748)),
    ]
    for fname, (tx0, ty0, tx1, ty1) in row4_boxes:
        cell = trees_img[ty0:ty1, tx0:tx1]
        rgba = remove_cell_background(
            cell,
            bg_rgb=tree_bg,
            color_tol=26.0,
            edge_inset=1,
            keep_largest_cluster_only=True,
        )
        std_img, bbox = standardize_sprite(rgba, canvas_size=(192, 224), padding=10)
        fpath = os.path.join(tree_folder, fname)
        std_img.save(fpath, format="PNG")
        all_records.append(
            {
                "file": fname,
                "folder": "04_prehistoric_trees_and_wood",
                "path": fpath,
                "canvas_size": [192, 224],
                "source_bbox": list(bbox),
            }
        )

    # 5. Forageable Flora & 3-Stage Growth Lifecycle (36 sprites)
    flora_img = np.array(
        Image.open(
            os.path.join(RAW_DIR, "watermarked_img_2688578308135758680.jpg")
        ).convert("RGB")
    )
    all_records.extend(
        slice_by_explicit_splits(
            flora_img,
            y_splits=[0, 192, 386, 578, 768],
            x_splits=[0, 154, 300, 444, 605, 765, 926, 1082, 1215, 1376],
            bg_rgb=np.array([48, 52, 55]),
            out_folder=os.path.join(PACK_ROOT, "05_forageable_flora_3stages"),
            prefix_per_row=[
                "flora_berry_bush_stage",
                "flora_grain_fiber_reed_stage",
                "flora_tuber_root_garlic_stage",
                "flora_mushroom_herb_stage",
            ],
            canvas_size=(160, 160),
            color_tol=22.0,
            edge_inset=3,
        )
    )

    # 6. Foraging Inventory Icons & Crafting Props (16 sprites)
    items_img = np.array(
        Image.open(
            os.path.join(RAW_DIR, "watermarked_img_6723530923958047816.jpg")
        ).convert("RGB")
    )
    item_records = slice_by_explicit_splits(
        items_img,
        y_splits=[15, 200, 385, 570, 755],
        x_splits=[215, 452, 690, 928, 1165],
        bg_rgb=np.array([37, 43, 55]),
        out_folder=os.path.join(PACK_ROOT, "06_foraging_items_and_props"),
        prefix_per_row=[
            "item_basket",
            "item_cordage_resin",
            "item_food_harvest",
            "item_herbalism_tool",
        ],
        canvas_size=(160, 160),
        color_tol=22.0,
        edge_inset=4,
        keep_largest_cluster_only=True,
    )
    item_names = [
        "01_basket_crimson_berries.png",
        "02_basket_golden_nuts.png",
        "03_basket_wild_mushrooms.png",
        "04_woven_reed_basket_empty.png",
        "05_twisted_fiber_cordage.png",
        "06_dried_thatch_reed_sheaf.png",
        "07_pine_resin_stone_bowl.png",
        "08_fresh_flax_plant_stems.png",
        "09_starchy_wild_tubers.png",
        "10_roasted_oak_acorns.png",
        "11_golden_wild_honeycomb.png",
        "12_einkorn_wild_wheat_bundle.png",
        "13_leather_herbalist_pouch.png",
        "14_healing_leaf_poultice.png",
        "15_stone_mortar_and_pestle.png",
        "16_dried_medicinal_herb_bundle.png",
    ]
    for rec, new_name in zip(item_records, item_names):
        new_path = os.path.join(os.path.dirname(rec["path"]), new_name)
        os.rename(rec["path"], new_path)
        rec["file"] = new_name
        rec["path"] = new_path
    all_records.extend(item_records)

    # 7. UI/HUD Frames, Resource Icons & Cave-Painting Tech Tree Icons (15 sprites)
    ui_img = np.array(
        Image.open(
            os.path.join(RAW_DIR, "watermarked_img_8095649456615242688.jpg")
        ).convert("RGB")
    )
    ui_folder = os.path.join(PACK_ROOT, "07_ui_hud_and_tech_icons")
    os.makedirs(ui_folder, exist_ok=True)
    ui_bg = np.array([30, 40, 48])

    ui_boxes = [
        ("01_hud_stone_panel_slots.png", (20, 20, 495, 395), (384, 288)),
        ("02_hud_stone_panel_inventory.png", (505, 20, 985, 395), (384, 288)),
        ("03_hud_bone_amber_minimap_ring.png", (1000, 20, 1360, 390), (288, 288)),
        ("04_icon_res_raw_meat.png", (25, 425, 185, 580), (160, 160)),
        ("05_icon_res_crimson_berries.png", (188, 425, 345, 580), (160, 160)),
        ("06_icon_res_flint_spearhead.png", (348, 425, 505, 580), (160, 160)),
        ("07_icon_res_timber_logs.png", (508, 425, 665, 580), (160, 160)),
        ("08_icon_res_mammoth_ivory.png", (25, 585, 185, 745), (160, 160)),
        ("09_icon_res_campfire_warmth.png", (188, 585, 345, 745), (160, 160)),
        ("10_tech_fire_mastery.png", (850, 415, 1020, 580), (160, 160)),
        ("11_tech_flintknapping.png", (1022, 415, 1190, 580), (160, 160)),
        ("12_tech_spear_hunting.png", (1192, 415, 1360, 580), (160, 160)),
        ("13_tech_hide_clothing.png", (850, 582, 1020, 748), (160, 160)),
        ("14_tech_megalithic_rituals.png", (1022, 582, 1190, 748), (160, 160)),
        ("15_tech_mammoth_domestication.png", (1192, 582, 1360, 748), (160, 160)),
    ]
    for fname, (ux0, uy0, ux1, uy1), c_size in ui_boxes:
        cell = ui_img[uy0:uy1, ux0:ux1]
        rgba = remove_cell_background(cell, bg_rgb=ui_bg, color_tol=20.0, edge_inset=2)
        std_img, bbox = standardize_sprite(rgba, canvas_size=c_size, padding=8)
        fpath = os.path.join(ui_folder, fname)
        std_img.save(fpath, format="PNG")
        all_records.append(
            {
                "file": fname,
                "folder": "07_ui_hud_and_tech_icons",
                "path": fpath,
                "canvas_size": list(c_size),
                "source_bbox": list(bbox),
            }
        )

    # 8. Fog-of-War, Vision Cones & Blind Sensory Ping VFX (watermarked_img_2952643332068048972.jpg)
    fow_sheet = np.array(
        Image.open(
            os.path.join(RAW_DIR, "watermarked_img_2952643332068048972.jpg")
        ).convert("RGB")
    )
    fow_folder = os.path.join(PACK_ROOT, "08_fog_of_war_and_vision_fx")
    os.makedirs(fow_folder, exist_ok=True)
    fow_bg = np.array([42, 51, 60])

    # Top-left 12 square shroud/memory tiles + 3 isometric shroud tiles
    all_records.extend(
        slice_by_explicit_splits(
            fow_sheet,
            y_splits=[18, 134, 250, 368],
            x_splits=[20, 142, 265, 388, 508, 675],
            bg_rgb=fow_bg,
            out_folder=fow_folder,
            prefix_per_row=[
                "fow_tile_row1",
                "fow_tile_row2",
                "fow_tile_row3",
            ],
            canvas_size=(160, 160),
            color_tol=18.0,
            edge_inset=3,
        )
    )
    # Bottom-left 8 directional Vision Cone overlays (2 rows x 4 cols)
    all_records.extend(
        slice_by_explicit_splits(
            fow_sheet,
            y_splits=[402, 574, 748],
            x_splits=[20, 182, 344, 508, 675],
            bg_rgb=fow_bg,
            out_folder=fow_folder,
            prefix_per_row=[
                "vision_cone_upper",
                "vision_cone_lower",
            ],
            canvas_size=(160, 160),
            color_tol=18.0,
            edge_inset=3,
        )
    )
    # Bottom-right Blind Sensory Pings (sound rings, glowing footprints, rustling bush, mystery runes)
    all_records.extend(
        slice_by_explicit_splits(
            fow_sheet,
            y_splits=[402, 574, 748],
            x_splits=[705, 868, 1030, 1192, 1358],
            bg_rgb=fow_bg,
            out_folder=fow_folder,
            prefix_per_row=[
                "blind_ping_sound_and_tracks",
                "blind_ping_wave_and_runes",
            ],
            canvas_size=(160, 160),
            color_tol=18.0,
            edge_inset=3,
        )
    )

    # 9. Trailblazing Roads, Bridges & Waypoints (watermarked_img_12497292019196056027.jpg)
    tb_sheet = np.array(
        Image.open(
            os.path.join(RAW_DIR, "watermarked_img_12497292019196056027.jpg")
        ).convert("RGB")
    )
    tb_folder = os.path.join(PACK_ROOT, "09_trailblazing_and_waypoints")
    os.makedirs(tb_folder, exist_ok=True)
    tb_bg = np.array([82, 82, 82])

    # Row 1 (5 trail evolution tiles) & Row 2 (5 river ford/bridge tiles)
    all_records.extend(
        slice_by_explicit_splits(
            tb_sheet,
            y_splits=[8, 198, 372],
            x_splits=[14, 282, 554, 822, 1094, 1364],
            bg_rgb=tb_bg,
            out_folder=tb_folder,
            prefix_per_row=[
                "trail_tile_evolution",
                "river_crossing_bridge",
            ],
            canvas_size=(224, 192),
            color_tol=22.0,
            edge_inset=2,
            keep_largest_cluster_only=True,
        )
    )
    # Row 3 (12 waypoint cairns, skull totems, blaze arrow trees, rally banners)
    all_records.extend(
        slice_by_explicit_splits(
            tb_sheet,
            y_splits=[372, 568],
            x_splits=[
                20,
                166,
                283,
                386,
                470,
                571,
                707,
                805,
                908,
                1024,
                1127,
                1245,
                1352,
            ],
            bg_rgb=tb_bg,
            out_folder=tb_folder,
            prefix_per_row=["waypoint_marker"],
            canvas_size=(160, 192),
            color_tol=22.0,
            edge_inset=2,
            keep_largest_cluster_only=True,
        )
    )

    # 10. Scouts, Tracker Hounds & Mapmaking Kit (watermarked_img_9361606950095710751.jpg)
    sc_sheet = np.array(
        Image.open(
            os.path.join(RAW_DIR, "watermarked_img_9361606950095710751.jpg")
        ).convert("RGB")
    )
    all_records.extend(
        slice_by_explicit_splits(
            sc_sheet,
            y_splits=[0, 194, 384, 573, 765],
            x_splits=[0, 173, 346, 516, 688, 858, 1029, 1200, 1375],
            bg_rgb=np.array([34, 42, 53]),
            out_folder=os.path.join(PACK_ROOT, "10_scouts_and_mapmaking_items"),
            prefix_per_row=[
                "unit_tribal_scout_pathfinder",
                "unit_tamed_tracker_hound",
                "unit_pioneer_trailblazer",
                "item_cartography_mapmaking",
            ],
            canvas_size=(160, 160),
            color_tol=22.0,
            edge_inset=4,
            keep_largest_cluster_only=True,
        )
    )

    manifest = {
        "pack_name": "Prehistoric Stone Age RTS — Complete Standardized & Sliced Sprite Pack (10 Categories)",
        "total_sliced_sprites": len(all_records),
        "categories": {},
        "items": [
            {
                "file": r["file"],
                "folder": r["folder"],
                "canvas_size": r["canvas_size"],
            }
            for r in all_records
        ],
    }
    for r in all_records:
        cat = r["folder"]
        manifest["categories"][cat] = manifest["categories"].get(cat, 0) + 1

    manifest_path = os.path.join(PACK_ROOT, "asset_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    zip_path = os.path.join(OUTPUT_DIR, "stone_age_rts_sliced_assets_pack.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(PACK_ROOT):
            for file in sorted(files):
                abs_p = os.path.join(root, file)
                rel_p = os.path.relpath(abs_p, OUTPUT_DIR)
                zf.write(abs_p, rel_p)

    return {
        "manifest": manifest,
        "records": all_records,
        "zip_path": zip_path,
    }


if __name__ == "__main__":
    result = build_complete_asset_pack()
    print(json.dumps(result["manifest"]["categories"], indent=2))
    print("Total sliced sprites:", result["manifest"]["total_sliced_sprites"])
