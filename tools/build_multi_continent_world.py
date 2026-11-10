"""Assemble and render the Grand Multi-Continent Prehistoric World Atlas.

Stitches the continents from ow_7, ow_42, ow_2026_v4 and an organic desert continent
into a grand 4-continent world map ("THẾ GIỚI ĐA LỤC ĐỊA"):
- Northwest: LỤC ĐỊA BĂNG BẮC (ARCTICA) - from ow_7
- Northeast: LỤC ĐỊA ĐÔNG SƠN (ORIENTIS) - from ow_42
- Southwest: LỤC ĐỊA SA MẠC CÁT ĐỎ (GONDWANA) - desert & badlands continent
- Southeast: LỤC ĐỊA RỪNG THIÊNG (VERDANTIA) - from ow_2026_v4
- Central Ocean (Biển Trung Tâm) with tropical volcanic archipelagos & navigable straits.
"""

import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


def euclidean_distance(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    inf = 1e10
    f = np.where(mask, 0.0, inf).astype(np.float32)

    def _edt_1d(arr_2d: np.ndarray) -> np.ndarray:
        n_rows, n_cols = arr_2d.shape
        out = np.empty_like(arr_2d)
        x = np.arange(n_cols, dtype=np.float32)
        for i in range(n_rows):
            row = arr_2d[i]
            if np.all(row >= inf):
                out[i] = inf
                continue
            idx = np.where(row < inf)[0]
            if len(idx) == n_cols:
                out[i] = row
                continue
            best = np.full(n_cols, inf, dtype=np.float32)
            for j in idx:
                d = (x - j) ** 2 + row[j]
                best = np.minimum(best, d)
            out[i] = best
        return out

    d_cols = _edt_1d(f)
    d_full = _edt_1d(d_cols.T).T
    return np.sqrt(np.maximum(0.0, d_full))


def blur(arr: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0.25:
        return arr.astype(np.float32, copy=True)
    radius = max(1, int(math.ceil(sigma * 3.0)))
    x = np.arange(-radius, radius + 1, dtype=np.float32)
    k = np.exp(-(x * x) / (2.0 * sigma * sigma))
    k /= k.sum()
    padded_h = np.pad(arr.astype(np.float32, copy=False), ((0, 0), (radius, radius)), mode="edge")
    temp = np.zeros_like(arr, dtype=np.float32)
    for i, w in enumerate(k):
        temp += w * padded_h[:, i : i + arr.shape[1]]
    padded_v = np.pad(temp, ((radius, radius), (0, 0)), mode="edge")
    out = np.zeros_like(arr, dtype=np.float32)
    for i, w in enumerate(k):
        out += w * padded_v[i : i + arr.shape[0], :]
    return out


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    denom = edge1 - edge0
    if abs(denom) < 1e-6:
        denom = 1e-6 if denom >= 0 else -1e-6
    t = np.clip((x - edge0) / denom, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def scale_layer(arr: np.ndarray, target_sz: int, is_discrete: bool = False) -> np.ndarray:
    img = Image.fromarray(arr)
    res = Image.NEAREST if is_discrete else Image.BILINEAR
    return np.array(img.resize((target_sz, target_sz), res))


def build_stitched_multi_continent_world(out_size: int = 1024) -> dict:
    # 1. Load Source Continents
    f7 = np.load("/home/huyen1905/.gemini/antigravity/brain/fed854e2-3b10-4d89-9cc2-ce9ec962f36a/scratch/ow_7_field.npz")
    f42 = np.load("/home/huyen1905/.gemini/antigravity/brain/fed854e2-3b10-4d89-9cc2-ce9ec962f36a/scratch/ow_42_field.npz")
    f2026_v4 = np.load("/home/huyen1905/.gemini/antigravity/brain/fed854e2-3b10-4d89-9cc2-ce9ec962f36a/scratch/ow_2026_v4_field.npz")

    W_SIZE = out_size
    world_land = np.zeros((W_SIZE, W_SIZE), dtype=bool)
    world_elev = np.zeros((W_SIZE, W_SIZE), dtype=np.float32)
    world_biome = np.zeros((W_SIZE, W_SIZE), dtype=np.uint8)
    world_river = np.zeros((W_SIZE, W_SIZE), dtype=bool)
    world_lake = np.zeros((W_SIZE, W_SIZE), dtype=bool)
    world_moist = np.full((W_SIZE, W_SIZE), 0.5, dtype=np.float32)
    world_temp = np.full((W_SIZE, W_SIZE), 0.5, dtype=np.float32)

    def _extract(data):
        k_land = "is_land" if "is_land" in data else "land"
        k_river = "river_mask" if "river_mask" in data else "river"
        k_lake = "lake_mask" if "lake_mask" in data else None

        land = (data[k_land] > 0)
        elev = np.where(land, np.maximum(0.02, data["elevation"]), 0.0).astype(np.float32)
        biome = data["biome"]
        river = (data[k_river] > 0) if k_river in data else np.zeros_like(land)
        lake = (data[k_lake] > 0) if k_lake and k_lake in data else np.zeros_like(land)
        moist = data["moisture"].astype(np.float32)
        temp = data["temperature"].astype(np.float32)
        return {"land": land, "elev": elev, "biome": biome, "river": river, "lake": lake, "moist": moist, "temp": temp}

    # Continent 1 (Northwest): Arctica (Băng Bắc) from ow_7
    c1 = _extract(f7)

    # Continent 2 (Northeast): Orientis (Đông Sơn) from ow_42
    c2 = _extract(f42)

    # Continent 3 (Southwest): Gondwana (Hoang Mạc Cát Đỏ)
    # Built from flipped and terrain-transformed ow_42, remapped to rich desert & canyon biomes
    c3 = _extract(f42)
    # Flip horizontally and rotate 90 for completely different natural silhouette
    c3_land = np.rot90(np.fliplr(c3["land"]), 1)
    c3_elev = np.rot90(np.fliplr(c3["elev"]), 1)
    c3_river = np.rot90(np.fliplr(c3["river"]), 1)
    c3_lake = np.rot90(np.fliplr(c3["lake"]), 1)
    c3_moist = np.rot90(np.fliplr(c3["moist"]), 1) * 0.45
    c3_temp = np.clip(np.rot90(np.fliplr(c3["temp"]), 1) * 1.35 + 0.25, 0.0, 1.0)
    # Remap biomes: mountains -> red-rock mesa/canyon (7/4), plains -> golden desert dunes (9), valleys -> savanna (10)
    c3_biome = np.zeros_like(c3["biome"])
    c3_biome[c3_land] = 9  # Hoang mạc cát
    c3_biome[c3_land & (c3_elev > 0.45)] = 4  # Núi đá đỏ
    c3_biome[c3_land & (c3_moist > 0.24)] = 10 # Xavan
    c3_biome[c3_land & (c3_moist > 0.35)] = 8  # Thảo nguyên khô
    c3 = {"land": c3_land, "elev": c3_elev, "biome": c3_biome, "river": c3_river, "lake": c3_lake, "moist": c3_moist, "temp": c3_temp}

    # Continent 4 (Southeast): Verdantia (Rừng Thiêng & Quần Đảo) from ow_2026_v4
    c4 = _extract(f2026_v4)
    # Remap biomes of c4 to match standard 1..13 palette
    c4_biome = np.zeros_like(c4["biome"])
    c4_biome[c4["land"]] = 6   # Rừng ôn đới
    c4_biome[c4["land"] & (c4["biome"] == 11)] = 11 # Rừng nhiệt đới
    c4_biome[c4["land"] & (c4["biome"] == 14)] = 2  # Băng tuyết đỉnh núi
    c4_biome[c4["land"] & (c4["biome"] == 13)] = 4  # Núi đá
    c4_biome[c4["land"] & (c4["biome"] == 6)]  = 9  # Cát vàng
    c4_biome[c4["land"] & (c4["biome"] == 7)]  = 4  # Vách đá
    c4_biome[c4["land"] & (c4["biome"] == 8)]  = 10 # Xavan
    c4_biome[c4["land"] & (c4["biome"] == 9)]  = 7  # Đồng cỏ
    c4_biome[c4["land"] & (c4["biome"] == 3)]  = 1  # Bờ cát
    c4["biome"] = c4_biome

    # Placement in 1024x1024 canvas
    target_sz = 456
    continents_placed = [
        ("NW", c1, 28, 28),
        ("NE", c2, 28, 540),
        ("SW", c3, 540, 28),
        ("SE", c4, 540, 540),
    ]

    for name, cont, roff, coff in continents_placed:
        s_land = scale_layer(cont["land"].astype(np.uint8), target_sz, is_discrete=True) > 0
        s_elev = scale_layer(cont["elev"], target_sz, is_discrete=False)
        s_biome = scale_layer(cont["biome"], target_sz, is_discrete=True)
        s_river = scale_layer(cont["river"].astype(np.uint8), target_sz, is_discrete=True) > 0
        s_lake = scale_layer(cont["lake"].astype(np.uint8), target_sz, is_discrete=True) > 0
        s_moist = scale_layer(cont["moist"], target_sz, is_discrete=False)
        s_temp = scale_layer(cont["temp"], target_sz, is_discrete=False)

        r_slice = slice(roff, roff + target_sz)
        c_slice = slice(coff, coff + target_sz)

        world_land[r_slice, c_slice] |= s_land
        world_elev[r_slice, c_slice] = np.where(s_land, s_elev, world_elev[r_slice, c_slice])
        world_biome[r_slice, c_slice] = np.where(s_land, s_biome, world_biome[r_slice, c_slice])
        world_river[r_slice, c_slice] |= s_river
        world_lake[r_slice, c_slice] |= s_lake
        world_moist[r_slice, c_slice] = np.where(s_land, s_moist, world_moist[r_slice, c_slice])
        world_temp[r_slice, c_slice] = np.where(s_land, s_temp, world_temp[r_slice, c_slice])

    # 2. Add Organic Central Ocean Island Chain (Stepping-Stone Atolls & Volcanic Sanctuaries)
    y_grid, x_grid = np.mgrid[0:W_SIZE, 0:W_SIZE]
    rng = np.random.RandomState(2026)
    island_specs = [
        # (cy, cx, rx, ry, angle, biome_id, max_h)
        (512, 512, 18, 14, 25, 11, 0.42),   # Central Ocean Primeval Atoll
        (512, 385, 14, 10, -18, 7, 0.32),   # West-Central Strait Islet
        (512, 638, 15, 11, 15, 11, 0.35),   # East-Central Coral Islet
        (385, 512, 12, 16, -30, 6, 0.30),   # North-Central Channel Islet
        (638, 512, 16, 12, 40, 10, 0.34),   # South-Central Savanna Islet
        (460, 460, 9, 8, 10, 1, 0.22),      # Coral sandbar
        (565, 565, 10, 8, -25, 1, 0.24),    # Coral sandbar
    ]

    for cy, cx, rx, ry, lang, b_id, max_h in island_specs:
        th = math.radians(lang)
        ct, st = math.cos(th), math.sin(th)
        dx = x_grid - cx
        dy = y_grid - cy
        xr = (dx * ct + dy * st) / rx
        yr = (-dx * st + dy * ct) / ry
        dist_sq = xr * xr + yr * yr
        m = dist_sq <= 1.0
        world_land |= m
        world_elev = np.where(m, np.maximum(world_elev, max_h * (1.0 - dist_sq)), world_elev)
        world_biome = np.where(m, b_id, world_biome)

    return {
        "land": world_land,
        "elev": world_elev,
        "biome": world_biome,
        "river": world_river,
        "lake": world_lake,
        "moist": world_moist,
        "temp": world_temp,
        "W_SIZE": W_SIZE,
    }


def render_stitched_multi_continent_map(fields: dict, out_size: int = 1024) -> Image.Image:
    land = fields["land"]
    elev = fields["elev"]
    biome = fields["biome"]
    river = fields["river"]
    lake = fields["lake"]
    H, W = land.shape

    # Euclidean distance transforms
    coast_sea_px = euclidean_distance(land)
    coast_inland_px = euclidean_distance(~land)

    rgb = np.zeros((H, W, 3), dtype=np.float32)

    # 1. Deep Ocean Bathymetry with Turquoise Coastal Shelf
    deep_col = np.array([12.0, 74.0, 114.0], dtype=np.float32)
    mid_col  = np.array([20.0, 106.0, 142.0], dtype=np.float32)
    reef_col = np.array([44.0, 192.0, 210.0], dtype=np.float32)
    surf_col = np.array([160.0, 235.0, 240.0], dtype=np.float32)

    sea_t = np.clip(coast_sea_px / (W * 0.040), 0.0, 1.0)
    reef_w = np.exp(-((coast_sea_px / 7.2) ** 1.35))
    surf_w = np.exp(-((coast_sea_px / 1.8) ** 1.5))

    for ch in range(3):
        c = mid_col[ch] + (deep_col[ch] - mid_col[ch]) * (sea_t ** 0.72)
        c = c * (1.0 - reef_w) + reef_col[ch] * reef_w
        c = c * (1.0 - 0.45 * surf_w) + surf_col[ch] * (0.45 * surf_w)
        rgb[:, :, ch] = c

    # 2. Biome Palette
    BIOME_COLORS = {
        1:  np.array([220.0, 204.0, 156.0]),  # Bờ cát
        2:  np.array([242.0, 246.0, 250.0]),  # Băng tuyết
        3:  np.array([146.0, 158.0, 118.0]),  # Đài nguyên
        4:  np.array([112.0, 114.0, 110.0]),  # Núi đá
        5:  np.array([46.0, 88.0, 62.0]),     # Rừng lá kim
        6:  np.array([52.0, 118.0, 48.0]),    # Rừng ôn đới
        7:  np.array([122.0, 172.0, 68.0]),   # Đồng cỏ
        8:  np.array([184.0, 174.0, 98.0]),   # Thảo nguyên khô
        9:  np.array([238.0, 190.0, 112.0]),  # Hoang mạc cát
        10: np.array([196.0, 160.0, 72.0]),   # Xavan
        11: np.array([28.0, 82.0, 32.0]),     # Rừng nhiệt đới
        12: np.array([68.0, 122.0, 96.0]),    # Đầm lầy
        13: np.array([44.0, 128.0, 168.0]),   # Hồ
        14: np.array([245.0, 248.0, 252.0]),  # Băng tuyết đỉnh cao
    }

    land_rgb = np.zeros((H, W, 3), dtype=np.float32)
    for b_id, col in BIOME_COLORS.items():
        m = (biome == b_id) & land
        if np.any(m):
            land_rgb[m] = col

    unassigned = land & (land_rgb.sum(axis=2) < 1.0)
    if np.any(unassigned):
        land_rgb[unassigned] = np.array([122.0, 172.0, 68.0])

    # 3. Topographic Shaded Relief
    dy, dx = np.gradient(elev * 75.0)
    nx = -dx
    ny = -dy
    nz = np.ones_like(elev)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx /= norm
    ny /= norm
    nz /= norm

    lx, ly, lz = -0.60, -0.55, 0.58
    ndotl = np.clip(nx * lx + ny * ly + nz * lz, 0.0, 1.0)
    relief = smoothstep(1.5, 8.0, coast_inland_px) * (0.45 + 0.55 * smoothstep(0.06, 0.40, elev))
    raw_shade = 0.70 + 0.48 * ndotl
    crevice = elev - blur(elev, 1.4)
    ao = np.clip(1.0 + crevice * 2.2, 0.82, 1.15)
    shade = 1.0 + (raw_shade * ao - 1.0) * relief

    for ch in range(3):
        land_rgb[:, :, ch] = np.clip(land_rgb[:, :, ch] * shade, 0.0, 255.0)

    # 4. Rivers & Lakes
    c_water = np.array([32.0, 134.0, 176.0], dtype=np.float32)
    water_mask = (river | lake) & land
    for ch in range(3):
        land_rgb[:, :, ch] = np.where(water_mask, c_water[ch], land_rgb[:, :, ch])

    # Composite land onto ocean with smooth anti-aliased shoreline
    land_float = blur(land.astype(np.float32), 0.60)
    for ch in range(3):
        rgb[:, :, ch] = rgb[:, :, ch] * (1.0 - land_float) + land_rgb[:, :, ch] * land_float

    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")
    if out_size != W:
        img = img.resize((out_size, out_size), resample=_BICUBIC)

    # 5. Professional Cartographic Overlay (Tactical Grid, Compass, Continent Cartouches)
    overlay = Image.new("RGBA", (out_size, out_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    def _font(sz: int, bold: bool = False):
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "assets/fonts/DejaVuSans-Bold.ttf" if bold else "assets/fonts/DejaVuSans.ttf",
        ]
        for p in candidates:
            if Path(p).exists():
                return ImageFont.truetype(p, sz)
        return ImageFont.load_default()

    font_grid = _font(11)
    font_cont = _font(12, bold=True)
    font_sea = _font(11, bold=True)
    font_legend_title = _font(12, bold=True)
    font_legend_item = _font(10)
    font_compass = _font(14, bold=True)

    # Grid 12x12
    step = out_size / 12.0
    for k in range(1, 12):
        pos = int(round(k * step))
        draw.line([(pos, 0), (pos, out_size)], fill=(215, 238, 248, 28), width=1)
        draw.line([(0, pos), (out_size, pos)], fill=(215, 238, 248, 28), width=1)

    for k in range(12):
        draw.text((int(round(k * step + step * 0.45)), 6), chr(ord("A") + k), fill=(215, 238, 248, 185), font=font_grid)
        draw.text((6, int(round(k * step + step * 0.42))), str(k + 1), fill=(215, 238, 248, 185), font=font_grid)

    # Compass Rose at Top-Right
    cx = out_size - int(out_size * 0.075)
    cy = int(out_size * 0.080)
    cr = int(out_size * 0.038)
    draw.polygon([(cx, cy - cr), (cx - cr // 4, cy), (cx, cy - cr // 5), (cx + cr // 4, cy)], fill=(245, 240, 225, 240))
    draw.polygon([(cx, cy + cr), (cx - cr // 4, cy), (cx, cy + cr // 5), (cx + cr // 4, cy)], fill=(115, 110, 95, 210))
    draw.polygon([(cx - cr, cy), (cx, cy - cr // 4), (cx - cr // 5, cy), (cx, cy + cr // 4)], fill=(165, 160, 140, 210))
    draw.polygon([(cx + cr, cy), (cx, cy - cr // 4), (cx + cr // 5, cy), (cx, cy + cr // 4)], fill=(205, 200, 185, 230))
    draw.text((cx - 5, cy - cr - 18), "B", fill=(245, 240, 225, 245), font=font_compass)

    # The 4 Continent Cartouche Labels
    continents_info = [
        ("LỤC ĐỊA BĂNG BẮC (ARCTICA)", 255, 45, (200, 235, 255)),
        ("LỤC ĐỊA ĐÔNG SƠN (ORIENTIS)", 760, 45, (220, 245, 215)),
        ("LỤC ĐỊA HOANG MẠC (GONDWANA)", 255, 555, (255, 215, 150)),
        ("LỤC ĐỊA RỪNG THIÊNG (VERDANTIA)", 760, 555, (180, 240, 190)),
    ]

    for c_title, tx, ty, tcol in continents_info:
        bbox_w = len(c_title) * 7.5
        draw.rounded_rectangle(
            [(tx - bbox_w // 2 - 8, ty - 3), (tx + bbox_w // 2 + 8, ty + 19)],
            radius=5,
            fill=(12, 22, 34, 215),
            outline=(195, 180, 140, 185),
            width=1,
        )
        draw.text((tx - bbox_w // 2, ty), c_title, fill=tcol, font=font_cont)

    # Oceans, Straits, & Atolls
    seas_info = [
        ("BIỂN TRUNG TÂM (CENTRAL OCEAN)", 512, 502, (140, 215, 240)),
        ("EO BIỂN BẮC HẢI", 512, 240, (125, 195, 225)),
        ("EO BIỂN NAM HẢI", 512, 780, (125, 195, 225)),
        ("EO BIỂN TÂY DƯƠNG", 250, 508, (125, 195, 225)),
        ("EO BIỂN ĐÔNG DƯƠNG", 770, 508, (125, 195, 225)),
    ]

    for s_title, tx, ty, scol in seas_info:
        sb_w = len(s_title) * 6.5
        draw.text((tx - sb_w // 2 + 1, ty + 1), s_title, fill=(10, 25, 40, 210), font=font_sea)
        draw.text((tx - sb_w // 2, ty), s_title, fill=scol, font=font_sea)

    # Legend Box on Bottom-Left
    leg_w = int(out_size * 0.22)
    row_h = 17
    leg_entries = [
        ("Băng tuyết", (242, 246, 250)),
        ("Vách núi đá", (112, 114, 110)),
        ("Đài nguyên", (146, 158, 118)),
        ("Rừng lá kim", (46, 88, 62)),
        ("Rừng ôn đới", (52, 118, 48)),
        ("Đồng cỏ", (122, 172, 68)),
        ("Thảo nguyên khô", (184, 174, 98)),
        ("Hoang mạc", (238, 190, 112)),
        ("Xavan", (196, 160, 72)),
        ("Rừng nhiệt đới", (28, 82, 32)),
        ("Đầm lầy", (68, 122, 96)),
        ("Bờ cát", (220, 204, 156)),
    ]
    leg_h = int(row_h * (len(leg_entries) + 2.4))
    lx0 = 26
    ly0 = out_size - leg_h - 18

    draw.rounded_rectangle([(lx0, ly0), (lx0 + leg_w, ly0 + leg_h)], radius=8, fill=(12, 20, 32, 225), outline=(195, 180, 140, 190), width=2)
    draw.text((lx0 + 10, ly0 + 8), "THẾ GIỚI ĐA LỤC ĐỊA", fill=(245, 232, 180, 255), font=font_legend_title)
    draw.line([(lx0 + 10, ly0 + 26), (lx0 + leg_w - 10, ly0 + 26)], fill=(160, 145, 115, 130), width=1)

    for idx, (b_name, b_col) in enumerate(leg_entries):
        ry = ly0 + 32 + idx * row_h
        chip_w = 12
        draw.rectangle([(lx0 + 12, ry + 2), (lx0 + 12 + chip_w, ry + 2 + chip_w)], fill=b_col + (255,))
        draw.rectangle([(lx0 + 12, ry + 2), (lx0 + 12 + chip_w, ry + 2 + chip_w)], outline=(30, 40, 50, 160), width=1)
        draw.text((lx0 + 16 + chip_w + 4, ry), b_name, fill=(235, 238, 240, 245), font=font_legend_item)

    final_img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return final_img


def generate_multi_continent_overworld(
    out_path: str = "assets/sprites/world_overview_macro.png",
    size_px: int = 1024,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fields = build_stitched_multi_continent_world(out_size=size_px)
    img = render_stitched_multi_continent_map(fields, out_size=size_px)
    img.save(out_path, optimize=True)

    npz_path = out_path.with_name(out_path.stem + "_field.npz")
    dy, dx = np.gradient(fields["elev"])
    slope = np.hypot(dx, dy).astype(np.float32)
    np.savez_compressed(
        npz_path,
        elevation=fields["elev"].astype(np.float32),
        moisture=fields["moist"].astype(np.float32),
        temperature=fields["temp"].astype(np.float32),
        land=fields["land"].astype(np.uint8),
        is_land=fields["land"],
        river=fields["river"].astype(np.uint8),
        river_mask=fields["river"],
        lake=fields["lake"].astype(np.uint8),
        lake_mask=fields["lake"],
        biome=fields["biome"],
        region=fields["biome"],
        slope=slope,
        world_width=int(size_px),
        world_height=int(size_px),
    )

    regions = [
        {"id": "arctica", "name": "Lục Địa Băng Bắc (Arctica)", "biome": "alpine_glacial", "center_uv": [0.25, 0.25]},
        {"id": "orientis", "name": "Lục Địa Đông Sơn (Orientis)", "biome": "mountain_lakes", "center_uv": [0.75, 0.25]},
        {"id": "gondwana", "name": "Lục Địa Hoang Mạc (Gondwana)", "biome": "desert_badlands", "center_uv": [0.25, 0.75]},
        {"id": "verdantia", "name": "Lục Địa Rừng Thiêng (Verdantia)", "biome": "primeval_jungle", "center_uv": [0.75, 0.75]},
        {"id": "central_ocean", "name": "Biển Trung Tâm & Quần Đảo San Hô", "biome": "coral_atolls", "center_uv": [0.50, 0.50]},
    ]
    json_path = out_path.with_name(out_path.stem + "_regions.json")
    import json
    json_path.write_text(json.dumps({"world": "Thế Giới Đa Lục Địa", "continents": regions}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Grand Multi-Continent World saved to: {out_path} ({size_px}x{size_px})")
    return out_path


if __name__ == "__main__":
    generate_multi_continent_overworld()

