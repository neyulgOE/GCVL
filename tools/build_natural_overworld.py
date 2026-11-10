"""Generate a massive, complete natural prehistoric continent overworld map.

Synthesizes an expansive, complete prehistoric continent & archipelago
("ĐẠI LỤC NGUYÊN SINH") inspired by epic open-world survival game maps (Palworld, Ark):
- Fills ~72-76% of the world canvas (expansive landmass stretching across
  coordinates B to K and rows 2 to 11 with majestic peninsulas and deep fjords).
- Prominent Northwest peninsula stretching into the icy sea (like Image 1).
- Northwest / North Alpine Glacier Massif with gleaming snowfields, dark slate crags,
  and glacial tarn lakes.
- Northeast amber highland plateau and autumn badlands.
- Sprawling Central and Eastern lush emerald primeval rainforest, river floodplains,
  and rolling green meadows.
- Southwest golden sand dunes, terracotta mesa canyons, and warm savannas.
- Southeast detached lush island and stepping-stone archipelago.
- Multi-branching dendritic river networks originating from highland lakes and flowing
  through low valleys into coastal estuaries.
- Glowing turquoise shallow coastal reef shelves hugging the jagged fractal shores.
- Complete cartographic presentation:
  - Top coordinate letters A-L, left numbers 1-12.
  - Compass rose (North arrow "B") at top-right.
  - Cartouche legend "ĐẠI LỤC NGUYÊN SINH" with 12 colored biome chips.
  - Regional territory markers for megafauna habitats & natural landmarks.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_RESAMPLE = getattr(Image, "Resampling", Image)
_BICUBIC = _RESAMPLE.BICUBIC


class GradientNoise2D:
    """Deterministic 2D gradient noise table."""

    def __init__(self, seed: int = 42) -> None:
        rng = random.Random(seed)
        perm = list(range(256))
        rng.shuffle(perm)
        self.perm = perm + perm
        self.gradients = [
            (math.cos(2.0 * math.pi * i / 12.0), math.sin(2.0 * math.pi * i / 12.0))
            for i in range(12)
        ]


# ---------------------------------------------------------------------------
# Pure-NumPy Spatial Functions
# ---------------------------------------------------------------------------

def blur(arr: np.ndarray, sigma: float) -> np.ndarray:
    """Separable 1D Gaussian blur in pure NumPy."""
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


def euclidean_distance(mask: np.ndarray) -> np.ndarray:
    """Exact 2D Euclidean Distance Transform in pure NumPy."""
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


def label_components(mask: np.ndarray) -> Tuple[np.ndarray, List[int]]:
    """Connected component labeling in pure Python + NumPy."""
    from collections import deque

    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    sizes: List[int] = [0]
    current_label = 0
    for r in range(h):
        for c in range(w):
            if mask[r, c] and labels[r, c] == 0:
                current_label += 1
                q = deque([(r, c)])
                labels[r, c] = current_label
                count = 0
                while q:
                    cr, cc = q.popleft()
                    count += 1
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < h and 0 <= nc < w and mask[nr, nc] and labels[nr, nc] == 0:
                            labels[nr, nc] = current_label
                            q.append((nr, nc))
                sizes.append(count)
    return labels, sizes


def sample_fbm_grid(
    noise: GradientNoise2D,
    u: np.ndarray,
    v: np.ndarray,
    octaves: int = 5,
    persistence: float = 0.54,
    lacunarity: float = 2.06,
    base_scale: float = 3.0,
) -> np.ndarray:
    """Vectorized 2D fBm over coordinate arrays u, v."""
    perm = np.array(noise.perm, dtype=np.int32)
    grads = np.array(noise.gradients, dtype=np.float32)
    gx_lut = grads[:, 0]
    gy_lut = grads[:, 1]

    total = np.zeros_like(u, dtype=np.float32)
    amp = 1.0
    freq = base_scale
    max_amp = 0.0

    for _ in range(octaves):
        x = u * freq
        y = v * freq
        xi0 = np.floor(x).astype(np.int32)
        yi0 = np.floor(y).astype(np.int32)
        xf = (x - xi0).astype(np.float32)
        yf = (y - yi0).astype(np.float32)
        xi = xi0 & 255
        yi = yi0 & 255

        fade_x = xf * xf * xf * (xf * (xf * 6.0 - 15.0) + 10.0)
        fade_y = yf * yf * yf * (yf * (yf * 6.0 - 15.0) + 10.0)

        aa = perm[perm[xi] + yi] % 12
        ab = perm[perm[xi] + yi + 1] % 12
        ba = perm[perm[xi + 1] + yi] % 12
        bb = perm[perm[xi + 1] + yi + 1] % 12

        g_aa = gx_lut[aa] * xf + gy_lut[aa] * yf
        g_ba = gx_lut[ba] * (xf - 1.0) + gy_lut[ba] * yf
        g_ab = gx_lut[ab] * xf + gy_lut[ab] * (yf - 1.0)
        g_bb = gx_lut[bb] * (xf - 1.0) + gy_lut[bb] * (yf - 1.0)

        x1 = g_aa + fade_x * (g_ba - g_aa)
        x2 = g_ab + fade_x * (g_bb - g_ab)
        val = x1 + fade_y * (x2 - x1)

        total += val * amp
        max_amp += amp
        amp *= persistence
        freq *= lacunarity

    return np.clip(0.5 + (total / max(1e-6, max_amp)) * 0.88, 0.0, 1.0)


def sample_ridged_grid(
    noise: GradientNoise2D,
    u: np.ndarray,
    v: np.ndarray,
    octaves: int = 5,
    persistence: float = 0.56,
    lacunarity: float = 2.12,
    base_scale: float = 4.0,
) -> np.ndarray:
    """Sharp ridged multifractal field for mountain chains and canyons."""
    perm = np.array(noise.perm, dtype=np.int32)
    grads = np.array(noise.gradients, dtype=np.float32)
    gx_lut = grads[:, 0]
    gy_lut = grads[:, 1]

    total = np.zeros_like(u, dtype=np.float32)
    amp = 1.0
    freq = base_scale
    weight = np.ones_like(u, dtype=np.float32)
    max_amp = 0.0

    for _ in range(octaves):
        x = u * freq
        y = v * freq
        xi0 = np.floor(x).astype(np.int32)
        yi0 = np.floor(y).astype(np.int32)
        xf = (x - xi0).astype(np.float32)
        yf = (y - yi0).astype(np.float32)
        xi = xi0 & 255
        yi = yi0 & 255

        fade_x = xf * xf * xf * (xf * (xf * 6.0 - 15.0) + 10.0)
        fade_y = yf * yf * yf * (yf * (yf * 6.0 - 15.0) + 10.0)

        aa = perm[perm[xi] + yi] % 12
        ab = perm[perm[xi] + yi + 1] % 12
        ba = perm[perm[xi + 1] + yi] % 12
        bb = perm[perm[xi + 1] + yi + 1] % 12

        g_aa = gx_lut[aa] * xf + gy_lut[aa] * yf
        g_ba = gx_lut[ba] * (xf - 1.0) + gy_lut[ba] * yf
        g_ab = gx_lut[ab] * xf + gy_lut[ab] * (yf - 1.0)
        g_bb = gx_lut[bb] * (xf - 1.0) + gy_lut[bb] * (yf - 1.0)

        x1 = g_aa + fade_x * (g_ba - g_aa)
        x2 = g_ab + fade_x * (g_bb - g_ab)
        val = x1 + fade_y * (x2 - x1)

        signal = 1.0 - np.abs(val * 2.15)
        signal = np.clip(signal, 0.0, 1.0)
        signal = signal * signal * weight
        weight = np.clip(signal * 1.85, 0.15, 1.0)

        total += signal * amp
        max_amp += amp
        amp *= persistence
        freq *= lacunarity

    return np.clip(total / max(1e-6, max_amp), 0.0, 1.0)


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    denom = edge1 - edge0
    if abs(denom) < 1e-6:
        denom = 1e-6 if denom >= 0 else -1e-6
    t = np.clip((x - edge0) / denom, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def subdivide_and_meander(
    pts: List[Tuple[float, float]], seed: int, iterations: int = 4, roughness: float = 0.22
) -> List[Tuple[float, float]]:
    """Midpoint displacement for sinuous organic river polylines."""
    rng = random.Random(seed)
    cur = list(pts)
    for it in range(iterations):
        nxt: List[Tuple[float, float]] = [cur[0]]
        scale = roughness * (0.58 ** it)
        for i in range(len(cur) - 1):
            x0, y0 = cur[i]
            x1, y1 = cur[i + 1]
            mx = 0.5 * (x0 + x1)
            my = 0.5 * (y0 + y1)
            dx = x1 - x0
            dy = y1 - y0
            seg_len = math.hypot(dx, dy)
            if seg_len > 1e-6:
                nx = -dy / seg_len
                ny = dx / seg_len
                offset = rng.uniform(-1.0, 1.0) * seg_len * scale
                mx += nx * offset
                my += ny * offset
            nxt.append((mx, my))
            nxt.append((x1, y1))
        cur = nxt
    return cur


def dist_to_polyline(
    px: np.ndarray, py: np.ndarray, pts: List[Tuple[float, float]]
) -> Tuple[np.ndarray, np.ndarray]:
    """Minimum distance and progress t along polyline."""
    best_d = np.full_like(px, 1e9, dtype=np.float32)
    best_prog = np.zeros_like(px, dtype=np.float32)
    n_seg = len(pts) - 1
    for i in range(n_seg):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        dx = x1 - x0
        dy = y1 - y0
        l2 = dx * dx + dy * dy + 1e-12
        t = np.clip(((px - x0) * dx + (py - y0) * dy) / l2, 0.0, 1.0)
        proj_x = x0 + t * dx
        proj_y = y0 + t * dy
        d = np.hypot(px - proj_x, py - proj_y)
        prog = (i + t) / max(1, n_seg)
        better = d < best_d
        best_d = np.where(better, d, best_d)
        best_prog = np.where(better, prog, best_prog)
    return best_d, best_prog


# ---------------------------------------------------------------------------
# Grand Continent Synthesizer (Expansive Landmass ~72% of Map)
# ---------------------------------------------------------------------------

def build_grand_continent_fields(seed: int = 7, grid_size: int = 512) -> Dict[str, np.ndarray]:
    """
    Synthesize an expansive, complete prehistoric continent covering ~70-75% of the canvas.
    Reaches coordinates B to K and rows 2 to 11 with majestic peninsulas, bays, and archipelagos.
    """
    H = W = grid_size
    n_warp1 = GradientNoise2D(seed + 11)
    n_warp2 = GradientNoise2D(seed + 23)
    n_warp3 = GradientNoise2D(seed + 37)
    n_warp4 = GradientNoise2D(seed + 53)
    n_coast = GradientNoise2D(seed + 71)
    n_detail = GradientNoise2D(seed + 97)
    n_ridge1 = GradientNoise2D(seed + 131)
    n_ridge2 = GradientNoise2D(seed + 163)
    n_moist = GradientNoise2D(seed + 199)
    n_temp = GradientNoise2D(seed + 241)
    n_tex = GradientNoise2D(seed + 283)

    v_1d = np.linspace(0.0, 1.0, H, dtype=np.float32)
    u_1d = np.linspace(0.0, 1.0, W, dtype=np.float32)
    u, v = np.meshgrid(u_1d, v_1d)

    # 1. MULTI-SCALE DOMAIN WARPING
    w1_u = (sample_fbm_grid(n_warp1, u + 0.35, v + 0.65, octaves=4, base_scale=2.2) - 0.5) * 0.15
    w1_v = (sample_fbm_grid(n_warp2, u + 2.15, v + 1.35, octaves=4, base_scale=2.2) - 0.5) * 0.15
    wu = u + w1_u
    wv = v + w1_v

    w2_u = (sample_fbm_grid(n_warp3, wu + 4.2, wv + 2.8, octaves=5, base_scale=5.2) - 0.5) * 0.065
    w2_v = (sample_fbm_grid(n_warp4, wu + 1.7, wv + 6.3, octaves=5, base_scale=5.2) - 0.5) * 0.065
    wu2 = wu + w2_u
    wv2 = wv + w2_v

    # 2. CONTINENTAL SKELETON (Expansive Multi-Lobe Tectonic Landmass)
    def _lobe(cx: float, cy: float, rx: float, ry: float, angle_deg: float, amp: float) -> np.ndarray:
        th = math.radians(angle_deg)
        ct, st = math.cos(th), math.sin(th)
        dx = wu2 - cx
        dy = wv2 - cy
        xr = (dx * ct + dy * st) / rx
        yr = (-dx * st + dy * ct) / ry
        r2 = xr * xr + yr * yr
        return amp * np.exp(-r2 * 1.20)

    def _smax(a: np.ndarray, b: np.ndarray, k: float = 10.0) -> np.ndarray:
        m = np.maximum(a, b)
        return m + np.log(np.exp(-k * np.abs(a - b)) + 1.0) / k

    # Main Central Continental Body (Expansive core)
    mainland = _lobe(0.50, 0.52, 0.35, 0.36, 5.0, 0.95)

    # North-Western Horn Peninsula (Extending high up to row 2 & col B like Image 1!)
    mainland = _smax(mainland, _lobe(0.24, 0.22, 0.15, 0.17, 30.0, 0.88))
    mainland = _smax(mainland, _lobe(0.21, 0.12, 0.09, 0.13, 18.0, 0.85))
    mainland = _smax(mainland, _lobe(0.18, 0.06, 0.06, 0.09, 12.0, 0.82))

    # North / North-East Glacial Massif & Amber Highlands (Reaching up to row 2.5-3)
    mainland = _smax(mainland, _lobe(0.66, 0.28, 0.22, 0.19, -15.0, 0.92))
    mainland = _smax(mainland, _lobe(0.75, 0.24, 0.14, 0.12, -22.0, 0.86))
    mainland = _smax(mainland, _lobe(0.82, 0.31, 0.12, 0.08, -10.0, 0.80))

    # Eastern Promontories & Coastal Capes (Stretching towards column K)
    mainland = _smax(mainland, _lobe(0.78, 0.46, 0.18, 0.14, 12.0, 0.88))
    mainland = _smax(mainland, _lobe(0.86, 0.44, 0.11, 0.06, -8.0, 0.82))
    mainland = _smax(mainland, _lobe(0.84, 0.58, 0.12, 0.09, 15.0, 0.84))
    mainland = _smax(mainland, _lobe(0.80, 0.70, 0.14, 0.16, 25.0, 0.86))

    # Western Headlands & Slopes (Extending towards column B)
    mainland = _smax(mainland, _lobe(0.24, 0.46, 0.18, 0.22, -10.0, 0.90))
    mainland = _smax(mainland, _lobe(0.18, 0.60, 0.12, 0.16, 15.0, 0.86))

    # South-Western Desert Peninsula & Terracotta Badlands (Reaching row 10-11)
    mainland = _smax(mainland, _lobe(0.32, 0.76, 0.24, 0.20, 20.0, 0.92))
    mainland = _smax(mainland, _lobe(0.24, 0.86, 0.15, 0.13, 28.0, 0.88))
    mainland = _smax(mainland, _lobe(0.44, 0.86, 0.20, 0.15, -10.0, 0.88))

    # Deep Fjords, Embayments, and Coastal Inlets (Creating dramatic natural coastlines)
    bay_north = _lobe(0.44, 0.14, 0.11, 0.09, 10.0, 0.46)     # Northern Sound (between NW horn & NE massif)
    bay_east = _lobe(0.84, 0.51, 0.10, 0.065, 5.0, 0.48)      # Deep Eastern Bay
    bay_nw = _lobe(0.14, 0.32, 0.09, 0.08, -25.0, 0.44)       # NW Fjord Bight
    bay_south = _lobe(0.62, 0.94, 0.11, 0.08, -15.0, 0.45)    # Southern Estuary Bay
    bay_sw_cove = _lobe(0.17, 0.76, 0.08, 0.07, 30.0, 0.42)   # SW Desert Cove
    mainland = mainland - bay_north - bay_east - bay_nw - bay_south - bay_sw_cove

    # Offshore Archipelagos & Detached Sanctuary Islands
    se_island = _lobe(0.88, 0.88, 0.075, 0.095, -20.0, 0.82)
    se_spit = _lobe(0.81, 0.94, 0.060, 0.030, 8.0, 0.70)
    nw_islet = _lobe(0.16, 0.03, 0.024, 0.032, 12.0, 0.68)
    n_islet = _lobe(0.52, 0.04, 0.025, 0.028, -10.0, 0.65)
    e_islet = _lobe(0.94, 0.38, 0.026, 0.032, 20.0, 0.66)
    offshore = np.maximum(
        np.maximum(se_island, se_spit),
        np.maximum(np.maximum(nw_islet, n_islet), e_islet)
    )

    strait_se = _lobe(0.80, 0.83, 0.055, 0.085, 38.0, 0.46)
    continental = np.maximum(mainland - strait_se, offshore)

    # 7 Octaves of fractal coastline detail (coves, cliffs, beaches, headlands)
    coast_fbm = sample_fbm_grid(n_coast, wu2, wv2, octaves=7, persistence=0.56, base_scale=3.8)
    micro_fbm = sample_fbm_grid(n_detail, u, v, octaves=6, persistence=0.56, base_scale=11.5)
    fine_fbm = sample_fbm_grid(n_tex, u, v, octaves=6, persistence=0.57, base_scale=24.0)
    ridge_macro = sample_ridged_grid(n_ridge1, wu2, wv2, octaves=6, persistence=0.56, base_scale=4.2)
    ridge_fine = sample_ridged_grid(n_ridge2, u, v, octaves=6, persistence=0.56, base_scale=13.0)

    continental = (
        continental
        + (coast_fbm - 0.50) * 0.32
        + (micro_fbm - 0.50) * 0.12
        + (fine_fbm - 0.50) * 0.05
    )

    # Outer border buffer (only in outermost 1.5% so coast doesn't touch pixel 0 or W-1)
    edge_r = np.minimum(np.minimum(u, 1.0 - u), np.minimum(v, 1.0 - v))
    outer_guard = smoothstep(0.003, 0.022, edge_r)
    continental = continental * (0.35 + 0.65 * outer_guard) - (1.0 - outer_guard) * 0.30

    sea_level = 0.42
    raw_land = continental >= sea_level

    # Keep all real islands (>= 15 px)
    labels, sizes = label_components(raw_land)
    land = np.zeros_like(raw_land)
    for lbl_id, sz in enumerate(sizes):
        if lbl_id > 0 and sz >= 15:
            land |= (labels == lbl_id)

    # Fill tiny pinholes
    inv_labels, inv_sizes = label_components(~land)
    ocean_label = inv_labels[0, 0]
    for lbl_id, sz in enumerate(inv_sizes):
        if lbl_id > 0 and lbl_id != ocean_label and sz < 16:
            land |= (inv_labels == lbl_id)

    # 3. EXACT EUCLIDEAN DISTANCE & SMOOTH COASTAL RAMPS
    coast_inland_px = euclidean_distance(~land)
    coast_sea_px = euclidean_distance(land)
    coast_inland_smooth = blur(coast_inland_px, 4.0)

    # 4. REGIONAL BIOME WEIGHTS (Covering the entire continent naturally)
    warp_b = (coast_fbm - 0.5) * 0.14 + (micro_fbm - 0.5) * 0.08
    bx = wu2 + warp_b
    by = wv2 - warp_b * 0.8

    # (A) North / North-East Alpine Glacier Massif (like Image 1 & 2!)
    d_alp = np.hypot((bx - 0.67) / 0.20, (by - 0.27) / 0.16)
    w_alpine = smoothstep(1.05, 0.40, d_alp)

    # (B) North-Western Horn Peninsula (Cold Conifer & Tundra)
    d_nw = np.hypot((bx - 0.22) / 0.15, (by - 0.16) / 0.16)
    w_tundra = smoothstep(1.08, 0.42, d_nw) * (1.0 - 0.70 * w_alpine)

    # (C) North-Eastern Autumn Highland Plateau & Amber Badlands
    d_amb = np.hypot((bx - 0.50) / 0.18, (by - 0.22) / 0.12)
    w_amber = smoothstep(1.05, 0.38, d_amb) * (1.0 - 0.75 * w_alpine)

    # (D) South-Western Sun-Baked Golden Desert & Terracotta Canyons
    dx_des = (bx - 0.30) * 0.86 + (by - 0.79) * 0.50
    dy_des = -(bx - 0.30) * 0.50 + (by - 0.79) * 0.86
    d_des = np.hypot(dx_des / 0.28, dy_des / 0.16)
    w_desert = smoothstep(1.15, 0.44, d_des) * (1.0 - 0.85 * w_alpine)

    # (E) Central & Eastern Lush Primeval Rainforest, River Basin, & Meadows
    w_lush = np.clip(1.0 - 0.90 * w_alpine - 0.80 * w_desert - 0.65 * w_amber - 0.65 * w_tundra, 0.0, 1.0)

    # 5. HIGH-OCTAVE FRACTAL ELEVATION & TECTONIC MOUNTAIN SPINES
    hills_fbm = sample_fbm_grid(n_detail, wu, wv, octaves=6, persistence=0.54, base_scale=5.6)

    # Alpine Peaks & Glacial Cirque in the Northeast Massif
    massif_dome = np.exp(-(((wu2 - 0.67) / 0.16) ** 2 + ((wv2 - 0.27) / 0.14) ** 2))
    central_spine = np.exp(-(((wu2 - 0.48) / 0.22) ** 2 + ((wv2 - 0.42) / 0.18) ** 2))

    excess = np.clip((continental - sea_level) / 0.20, 0.0, 1.0)
    dist_ramp = smoothstep(0.0, 12.0, coast_inland_smooth)
    coast_ramp = 0.45 * excess + 0.55 * dist_ramp

    raw_elev = (
        0.06
        + 0.18 * hills_fbm
        + 0.07 * fine_fbm
        + w_alpine * (0.44 * massif_dome + 0.45 * ridge_macro + 0.24 * ridge_fine)
        + central_spine * 0.16 * ridge_macro
        + w_amber * (0.32 * ridge_macro + 0.20 * ridge_fine + 0.12 * hills_fbm)
        + w_desert * (0.24 * ridge_macro + 0.18 * ridge_fine + 0.12 * hills_fbm)
        + w_lush * (0.20 * hills_fbm + 0.18 * ridge_macro + 0.10 * ridge_fine)
    )
    elev = np.where(land, raw_elev * (0.18 + 0.82 * coast_ramp), 0.0)

    # 6. DENDRITIC RIVER NETWORKS & INLAND LAKES
    raw_rivers = [
        # 1. Great Alpine Trunk River (Glacial Massif -> Central Lake -> Deep East Bay)
        ([(0.63, 0.28), (0.57, 0.35), (0.52, 0.44), (0.58, 0.50), (0.68, 0.49), (0.78, 0.48)], 1.20),
        # 2. Northern Highland Tributary (Amber Plateau -> Great Trunk)
        ([(0.45, 0.20), (0.49, 0.28), (0.52, 0.36), (0.52, 0.44)], 0.85),
        # 3. Southern Braided Heartland River (Central Lake -> Southern Estuary)
        ([(0.52, 0.44), (0.50, 0.54), (0.54, 0.65), (0.58, 0.77), (0.61, 0.90)], 1.15),
        # 4. Western Valley River (NW Foothills -> Western Bay)
        ([(0.38, 0.30), (0.32, 0.38), (0.26, 0.46), (0.20, 0.50)], 0.90),
        # 5. South-West Desert Oasis Canyon Stream
        ([(0.38, 0.68), (0.32, 0.75), (0.27, 0.81), (0.24, 0.87)], 0.80),
        # 6. Eastern Forest Tributary
        ([(0.62, 0.58), (0.69, 0.63), (0.76, 0.67), (0.82, 0.70)], 0.80),
        # 7. NW Horn Coastal Stream
        ([(0.26, 0.18), (0.22, 0.12), (0.19, 0.07)], 0.65),
        # 8. SE Island Stream
        ([(0.89, 0.84), (0.87, 0.89), (0.83, 0.93)], 0.65),
    ]

    ru = u + (sample_fbm_grid(n_warp3, u + 3.1, v + 1.2, octaves=5, base_scale=9.5) - 0.5) * 0.026
    rv = v + (sample_fbm_grid(n_warp4, u + 5.4, v + 2.8, octaves=5, base_scale=9.5) - 0.5) * 0.026

    river_strength = np.zeros((H, W), dtype=np.float32)
    valley_carve = np.zeros((H, W), dtype=np.float32)

    for idx, (pts, scale_w) in enumerate(raw_rivers):
        meander_pts = subdivide_and_meander(pts, seed=seed + idx * 31, iterations=4, roughness=0.24)
        d_line, prog = dist_to_polyline(ru, rv, meander_pts)
        half_w = (0.0015 + 0.0022 * (prog ** 1.35)) * scale_w
        v_carve = np.exp(-((d_line / 0.020) ** 2)) * (0.35 + 0.65 * prog)
        valley_carve = np.maximum(valley_carve, v_carve)

        ch = np.clip(1.0 - (d_line / half_w), 0.0, 1.0)
        ch = ch * np.clip(1.0 - w_alpine * 0.85, 0.0, 1.0)
        river_strength = np.maximum(river_strength, ch)

    # Great Inland Lakes with natural winding shores
    lakes_spec = [
        (0.64, 0.32, 0.024, 0.016, -15.0),  # Glacial Cirque Tarn (under alpine peak)
        (0.52, 0.44, 0.030, 0.020, 18.0),   # Great Central Confluence Lake
        (0.31, 0.77, 0.025, 0.014, -20.0),  # Desert Oasis Lake
    ]
    lake_field = np.zeros((H, W), dtype=np.float32)
    # Natural multi-frequency perturbation for irregular lake shorelines
    lake_warp_u = ru + (sample_fbm_grid(n_coast, u + 2.4, v + 4.1, octaves=5, base_scale=12.0) - 0.5) * 0.035
    lake_warp_v = rv + (sample_fbm_grid(n_detail, u + 1.2, v + 6.3, octaves=5, base_scale=12.0) - 0.5) * 0.035

    for lx, ly, lrx, lry, lang in lakes_spec:
        th = math.radians(lang)
        ct, st = math.cos(th), math.sin(th)
        dx = lake_warp_u - lx
        dy = lake_warp_v - ly
        xr = (dx * ct + dy * st) / lrx
        yr = (-dx * st + dy * ct) / lry
        dist_sq = xr * xr + yr * yr
        l_val = np.exp(-dist_sq * 1.65) * (0.80 + 0.40 * micro_fbm)
        lake_field = np.maximum(lake_field, l_val)

    lake_mask = land & (lake_field > 0.58) & (coast_inland_px > 6.0)
    river_mask = land & ((river_strength > 0.24) | lake_mask)

    elev = np.where(land, elev * (1.0 - 0.36 * valley_carve), 0.0)
    elev = np.where(river_mask, np.minimum(elev, 0.12), elev)

    if np.any(land):
        p99 = float(np.percentile(elev[land], 99.5))
        if p99 > 1e-5:
            elev = np.where(land, np.clip(elev / p99, 0.01, 1.0), 0.0)

    # 7. CLIMATE & DISCRETE BIOMES
    temperature = np.clip(
        0.58
        - 0.65 * w_alpine
        - 0.30 * w_tundra
        + 0.38 * w_desert
        - 0.10 * w_amber
        - 0.35 * elev
        + 0.14 * (coast_fbm - 0.5),
        0.0,
        1.0,
    )
    moisture = np.clip(
        0.54
        + 0.34 * w_lush
        - 0.46 * w_desert
        - 0.14 * w_amber
        + 0.30 * valley_carve
        + 0.20 * (micro_fbm - 0.5),
        0.0,
        1.0,
    )

    ocean_depth = np.clip((coast_sea_px / (W * 0.055)) * (0.80 + 0.40 * coast_fbm), 0.0, 1.0)
    biome = np.zeros((H, W), dtype=np.uint8)
    biome[(~land) & (ocean_depth >= 0.42)] = 0
    biome[(~land) & (ocean_depth >= 0.16) & (ocean_depth < 0.42)] = 1
    biome[(~land) & (ocean_depth < 0.16)] = 2

    # Land biome assignment
    biome[land] = 10  # Rừng ôn đới
    biome[land & (moisture < 0.48)] = 9  # Đồng cỏ
    biome[land & (moisture > 0.62) & (micro_fbm > 0.40)] = 11  # Rừng nhiệt đới nguyên sinh
    biome[land & (w_tundra > 0.35)] = 5  # Đài nguyên
    biome[land & (w_tundra > 0.45) & (micro_fbm > 0.50)] = 6  # Rừng lá kim
    biome[land & (w_amber > 0.36)] = 8  # Thảo nguyên khô / cao nguyên hoàng thổ
    biome[land & (w_desert > 0.35)] = 12  # Hoang mạc cát
    biome[land & (w_desert > 0.30) & ((ridge_fine > 0.55) | (ridge_macro > 0.58))] = 7  # Núi đá đỏ
    biome[land & (w_alpine > 0.35)] = 14  # Băng tuyết
    biome[land & (w_alpine > 0.28) & (ridge_fine > 0.56)] = 13  # Vách núi đá
    biome[land & (coast_inland_px <= 3.0) & (w_alpine < 0.25) & (elev < 0.18)] = 3  # Bờ cát
    biome[land & (coast_inland_px <= 5.0) & (moisture > 0.65) & (elev < 0.14)] = 4  # Đầm lầy
    biome[river_mask] = 4  # Nước nội địa

    return {
        "land": land,
        "elev": elev,
        "moisture": moisture,
        "temperature": temperature,
        "ocean_depth": ocean_depth,
        "river": river_mask,
        "lake": lake_mask,
        "river_strength": river_strength,
        "valley_carve": valley_carve,
        "biome": biome,
        "coast_inland_px": coast_inland_px,
        "coast_sea_px": coast_sea_px,
        "coast_fbm": coast_fbm,
        "ridge_macro": ridge_macro,
        "ridge_fine": ridge_fine,
        "hills_fbm": hills_fbm,
        "micro_fbm": micro_fbm,
        "fine_fbm": fine_fbm,
        "w_alpine": w_alpine,
        "w_tundra": w_tundra,
        "w_amber": w_amber,
        "w_desert": w_desert,
        "w_lush": w_lush,
    }


# ---------------------------------------------------------------------------
# Grand Map Cartographic Renderer (Full Overworld with Tactical HUD)
# ---------------------------------------------------------------------------

def render_grand_overworld(fields: Dict[str, np.ndarray], out_size: int = 1024) -> Image.Image:
    """Render the grand complete overworld map with cartographic overlays."""
    land = fields["land"]
    elev = fields["elev"]
    river = fields["river"]
    lake = fields["lake"]
    river_strength = fields["river_strength"]
    valley_carve = fields["valley_carve"]
    coast_sea_px = fields["coast_sea_px"]
    coast_inland_px = fields["coast_inland_px"]
    coast_fbm = fields["coast_fbm"]
    ridge_macro = fields["ridge_macro"]
    ridge_fine = fields["ridge_fine"]
    hills_fbm = fields["hills_fbm"]
    micro_fbm = fields["micro_fbm"]
    fine_fbm = fields["fine_fbm"]
    w_alpine = fields["w_alpine"]
    w_tundra = fields["w_tundra"]
    w_amber = fields["w_amber"]
    w_desert = fields["w_desert"]

    H, W = elev.shape
    u_grid = np.linspace(0.0, 1.0, W, dtype=np.float32)[None, :]
    rgb = np.zeros((H, W, 3), dtype=np.float32)

    # 1. OCEAN BATHYMETRY & SHALLOW TURQUOISE REEF GLOW
    deep_col = np.array([12.0, 76.0, 114.0], dtype=np.float32)
    mid_col  = np.array([20.0, 108.0, 144.0], dtype=np.float32)
    reef_col = np.array([44.0, 190.0, 210.0], dtype=np.float32)
    surf_col = np.array([160.0, 235.0, 240.0], dtype=np.float32)

    sea_t = np.clip(coast_sea_px / (W * 0.050), 0.0, 1.0)
    reef_w = np.exp(-((coast_sea_px / (7.5 + 4.5 * coast_fbm)) ** 1.35)) * (0.75 + 0.25 * micro_fbm)
    surf_w = np.exp(-((coast_sea_px / 1.7) ** 1.5))

    for ch in range(3):
        c = mid_col[ch] + (deep_col[ch] - mid_col[ch]) * (sea_t ** 0.72)
        c = c * (1.0 - reef_w) + reef_col[ch] * reef_w
        c = c * (1.0 - 0.45 * surf_w) + surf_col[ch] * (0.45 * surf_w)
        rgb[:, :, ch] = c

    # 2. CONTINUOUS BIOME PIGMENT MIXING
    c_jungle      = np.array([22.0, 74.0, 26.0], dtype=np.float32)   # Rừng nhiệt đới
    c_forest      = np.array([46.0, 110.0, 38.0], dtype=np.float32)  # Rừng ôn đới
    c_meadow      = np.array([118.0, 168.0, 68.0], dtype=np.float32) # Đồng cỏ
    c_steppe      = np.array([174.0, 180.0, 92.0], dtype=np.float32) # Thảo nguyên khô
    c_tundra      = np.array([126.0, 142.0, 118.0], dtype=np.float32)# Đài nguyên
    c_conifer     = np.array([38.0, 84.0, 56.0], dtype=np.float32)   # Rừng lá kim
    c_amber_gold  = np.array([228.0, 170.0, 60.0], dtype=np.float32) # Cao nguyên hoàng thổ
    c_amber_rust  = np.array([166.0, 90.0, 42.0], dtype=np.float32)
    c_sand_gold   = np.array([244.0, 194.0, 108.0], dtype=np.float32)# Hoang mạc cát
    c_sand_pale   = np.array([238.0, 212.0, 150.0], dtype=np.float32)
    c_mesa_red    = np.array([198.0, 94.0, 50.0], dtype=np.float32)  # Hẻm núi đá đỏ
    c_snow_bright = np.array([245.0, 249.0, 253.0], dtype=np.float32)# Băng tuyết
    c_snow_shadow = np.array([208.0, 222.0, 234.0], dtype=np.float32)
    c_slate_dark  = np.array([62.0, 72.0, 82.0], dtype=np.float32)   # Vách núi đá
    c_slate_mid   = np.array([104.0, 114.0, 124.0], dtype=np.float32)
    c_beach       = np.array([232.0, 214.0, 156.0], dtype=np.float32)# Bờ cát
    c_wetland     = np.array([56.0, 118.0, 96.0], dtype=np.float32)  # Đầm lầy

    dy, dx = np.gradient(elev * 78.0)
    slope = np.hypot(dx, dy)

    canopy_t = smoothstep(0.30, 0.66, 0.55 * hills_fbm + 0.45 * micro_fbm)
    clearing_t = smoothstep(0.42, 0.74, 0.50 * ridge_macro + 0.50 * fine_fbm)

    land_rgb = np.zeros((H, W, 3), dtype=np.float32)
    for ch in range(3):
        green_mix = c_jungle[ch] * canopy_t + c_forest[ch] * (1.0 - canopy_t)
        green_mix = green_mix * (1.0 - 0.70 * clearing_t) + c_meadow[ch] * (0.70 * clearing_t)
        land_rgb[:, :, ch] = green_mix

    # Tundra & Conifer on NW Peninsula
    tundra_blend = smoothstep(0.20, 0.60, w_tundra + (micro_fbm - 0.5) * 0.16)
    conifer_t = smoothstep(0.35, 0.68, hills_fbm)
    for ch in range(3):
        tun_col = c_tundra[ch] * (1.0 - conifer_t) + c_conifer[ch] * conifer_t
        land_rgb[:, :, ch] = land_rgb[:, :, ch] * (1.0 - tundra_blend) + tun_col * tundra_blend

    # Amber Highlands
    amber_crag_t = smoothstep(0.38, 0.68, 0.55 * ridge_fine + 0.45 * ridge_macro)
    amber_blend = smoothstep(0.18, 0.62, w_amber + (micro_fbm - 0.5) * 0.18)
    for ch in range(3):
        amb_col = c_amber_gold[ch] * (1.0 - amber_crag_t) + c_amber_rust[ch] * amber_crag_t
        land_rgb[:, :, ch] = land_rgb[:, :, ch] * (1.0 - amber_blend) + amb_col * amber_blend

    # Desert & Mesa
    desert_core_w = smoothstep(0.22, 0.64, w_desert + (micro_fbm - 0.5) * 0.18)
    mesa_t = smoothstep(0.44, 0.72, 0.55 * ridge_fine + 0.45 * hills_fbm)
    dune_t = smoothstep(0.35, 0.70, fine_fbm)
    for ch in range(3):
        des_col = c_sand_gold[ch] * (1.0 - 0.45 * dune_t) + c_sand_pale[ch] * (0.45 * dune_t)
        des_col = des_col * (1.0 - 0.75 * mesa_t) + c_mesa_red[ch] * (0.75 * mesa_t)
        land_rgb[:, :, ch] = land_rgb[:, :, ch] * (1.0 - desert_core_w) + des_col * desert_core_w

    # Alpine Glacier & Snow Peaks (NE / North Massif)
    alpine_w = smoothstep(0.25, 0.55, w_alpine + (micro_fbm - 0.5) * 0.16 + (ridge_macro - 0.5) * 0.14)
    rock_exposure = np.clip(
        0.70 * smoothstep(0.48, 0.75, ridge_macro)
        + 0.55 * smoothstep(1.15, 2.35, slope)
        + 0.35 * smoothstep(0.60, 0.82, ridge_fine),
        0.0,
        0.95,
    )
    for ch in range(3):
        snow_c = c_snow_bright[ch] * (0.82 + 0.18 * fine_fbm) + c_snow_shadow[ch] * (0.18 * (1.0 - fine_fbm))
        rock_c = c_slate_dark[ch] * (0.65 + 0.35 * fine_fbm) + c_slate_mid[ch] * (0.35 * (1.0 - fine_fbm))
        alp_col = snow_c * (1.0 - rock_exposure) + rock_c * rock_exposure
        land_rgb[:, :, ch] = land_rgb[:, :, ch] * (1.0 - alpine_w) + alp_col * alpine_w

    # Sandy Beaches & Coastal Spits
    beach_w = (
        smoothstep(6.5, 1.4, coast_inland_px)
        * smoothstep(0.30, 0.10, elev)
        * (1.0 - 0.85 * alpine_w)
        * (0.65 + 0.35 * micro_fbm)
    )
    for ch in range(3):
        land_rgb[:, :, ch] = land_rgb[:, :, ch] * (1.0 - beach_w) + c_beach[ch] * beach_w

    # Wetland Estuary & Delta
    wetland_w = smoothstep(0.0, 7.0, coast_inland_px) * smoothstep(0.18, 0.06, elev) * smoothstep(0.25, 0.70, valley_carve)
    for ch in range(3):
        land_rgb[:, :, ch] = land_rgb[:, :, ch] * (1.0 - wetland_w) + c_wetland[ch] * wetland_w

    tex_grain = 0.92 + 0.16 * fine_fbm
    for ch in range(3):
        land_rgb[:, :, ch] *= tex_grain

    # 3. TOPOGRAPHIC HILLSHADING
    nx = -dx
    ny = -dy
    nz = np.ones_like(elev)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx /= norm
    ny /= norm
    nz /= norm

    lx, ly, lz = -0.60, -0.55, 0.58
    ndotl = np.clip(nx * lx + ny * ly + nz * lz, 0.0, 1.0)
    relief_strength = smoothstep(1.8, 9.0, coast_inland_px) * (0.45 + 0.55 * smoothstep(0.08, 0.42, elev))
    raw_shade = 0.70 + 0.48 * ndotl
    crevice = elev - blur(elev, 1.4)
    ao = np.clip(1.0 + crevice * 2.4, 0.82, 1.15)
    shade = 1.0 + (raw_shade * ao - 1.0) * relief_strength

    for ch in range(3):
        land_rgb[:, :, ch] = np.clip(land_rgb[:, :, ch] * shade, 0.0, 255.0)

    # 4. RIVERS & LAKES
    c_water_edge = np.array([58.0, 176.0, 198.0], dtype=np.float32)
    c_water_core = np.array([24.0, 116.0, 154.0], dtype=np.float32)
    water_alpha = np.maximum(
        smoothstep(0.18, 0.55, river_strength),
        lake.astype(np.float32),
    )
    core_t = np.clip((river_strength - 0.35) / 0.55, 0.0, 1.0)
    for ch in range(3):
        w_col = c_water_edge[ch] * (1.0 - core_t) + c_water_core[ch] * core_t
        land_rgb[:, :, ch] = np.where(
            land,
            land_rgb[:, :, ch] * (1.0 - water_alpha) + w_col * water_alpha,
            land_rgb[:, :, ch],
        )

    # Composite land onto ocean with anti-aliasing
    land_float = blur(land.astype(np.float32), 0.60)
    for ch in range(3):
        rgb[:, :, ch] = rgb[:, :, ch] * (1.0 - land_float) + land_rgb[:, :, ch] * land_float

    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")
    if out_size != W:
        img = img.resize((out_size, out_size), resample=_BICUBIC)

    # 5. AUTHENTIC CARTOGRAPHIC OVERLAYS (Tactical Grid, Compass, Legend, Landmarks)
    overlay = Image.new("RGBA", (out_size, out_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Fonts
    def _font(sz: int, bold: bool = False) -> ImageFont.ImageFont:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "assets/fonts/DejaVuSans-Bold.ttf" if bold else "assets/fonts/DejaVuSans.ttf",
        ]
        for p in candidates:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, sz)
                except Exception:
                    pass
        return ImageFont.load_default()

    font_grid = _font(max(10, out_size // 88))
    font_legend_title = _font(max(12, out_size // 64), bold=True)
    font_legend_item = _font(max(10, out_size // 86))
    font_compass = _font(max(14, out_size // 56), bold=True)
    font_landmark = _font(max(10, out_size // 84), bold=True)

    # Tactical Coordinate Grid A-L (12 cols) x 1-12 (12 rows)
    step = out_size / 12.0
    for k in range(1, 12):
        pos = int(round(k * step))
        draw.line([(pos, 0), (pos, out_size)], fill=(215, 238, 248, 28), width=1)
        draw.line([(0, pos), (out_size, pos)], fill=(215, 238, 248, 28), width=1)

    for k in range(12):
        col_letter = chr(ord("A") + k)
        row_num = str(k + 1)
        pos_x = int(round(k * step + step * 0.45))
        pos_y = int(round(k * step + step * 0.42))
        draw.text((pos_x, 6), col_letter, fill=(215, 238, 248, 185), font=font_grid)
        draw.text((6, pos_y), row_num, fill=(215, 238, 248, 185), font=font_grid)

    # Compass Rose at Top-Right (with North Arrow "B")
    cx = out_size - int(out_size * 0.075)
    cy = int(out_size * 0.080)
    cr = int(out_size * 0.038)
    draw.polygon([(cx, cy - cr), (cx - cr // 4, cy), (cx, cy - cr // 5), (cx + cr // 4, cy)], fill=(245, 240, 225, 240))
    draw.polygon([(cx, cy + cr), (cx - cr // 4, cy), (cx, cy + cr // 5), (cx + cr // 4, cy)], fill=(115, 110, 95, 210))
    draw.polygon([(cx - cr, cy), (cx, cy - cr // 4), (cx - cr // 5, cy), (cx, cy + cr // 4)], fill=(165, 160, 140, 210))
    draw.polygon([(cx + cr, cy), (cx, cy - cr // 4), (cx + cr // 5, cy), (cx, cy + cr // 4)], fill=(205, 200, 185, 230))
    draw.text((cx - 5, cy - cr - 18), "B", fill=(245, 240, 225, 245), font=font_compass)

    # Comprehensive Cartouche Legend "ĐẠI LỤC NGUYÊN SINH" at Bottom-Left
    legend_entries = [
        ("Băng tuyết", (245, 249, 253)),
        ("Vách núi đá", (95, 105, 115)),
        ("Đài nguyên", (126, 142, 118)),
        ("Rừng lá kim", (38, 84, 56)),
        ("Rừng ôn đới", (46, 110, 38)),
        ("Đồng cỏ", (118, 168, 68)),
        ("Thảo nguyên khô", (174, 180, 92)),
        ("Hoang mạc", (244, 194, 108)),
        ("Xavan", (228, 170, 60)),
        ("Rừng nhiệt đới", (22, 74, 26)),
        ("Đầm lầy", (56, 118, 96)),
        ("Bờ cát", (232, 214, 156)),
    ]

    leg_w = int(out_size * 0.235)
    row_h = int(out_size * 0.0175)
    leg_h = int(row_h * (len(legend_entries) + 2.4))
    lx0 = 26
    ly0 = out_size - leg_h - 18

    # Semi-transparent dark glass background with warm bone-gold border
    draw.rounded_rectangle(
        [(lx0, ly0), (lx0 + leg_w, ly0 + leg_h)],
        radius=8,
        fill=(12, 20, 32, 215),
        outline=(195, 180, 140, 190),
        width=2,
    )
    draw.text((lx0 + 12, ly0 + 8), "ĐẠI LỤC NGUYÊN SINH", fill=(245, 232, 180, 255), font=font_legend_title)
    draw.line([(lx0 + 12, ly0 + 28), (lx0 + leg_w - 12, ly0 + 28)], fill=(160, 145, 115, 130), width=1)

    for idx, (b_name, b_color) in enumerate(legend_entries):
        ry = ly0 + 34 + idx * row_h
        chip_w = int(row_h * 0.75)
        draw.rectangle([(lx0 + 14, ry + 2), (lx0 + 14 + chip_w, ry + 2 + chip_w)], fill=b_color + (255,))
        draw.rectangle([(lx0 + 14, ry + 2), (lx0 + 14 + chip_w, ry + 2 + chip_w)], outline=(30, 40, 50, 160), width=1)
        draw.text((lx0 + 18 + chip_w + 4, ry), b_name, fill=(235, 238, 240, 245), font=font_legend_item)

    # Regional Wildlife Territory & Landmark Pins
    landmarks = [
        ("Dãy Băng Sơn (Ma Mút)", 0.67, 0.26, (140, 220, 255), "right"),
        ("Thung Lũng Hươu Khổng Lồ", 0.52, 0.44, (120, 240, 140), "right"),
        ("Cao Nguyên Hoàng Thổ", 0.48, 0.22, (255, 215, 100), "left"),
        ("Bán Đảo Lãnh Nguyên", 0.22, 0.14, (180, 225, 220), "right"),
        ("Hoang Mạc Cát Đỏ (Bison)", 0.31, 0.77, (255, 175, 90), "right"),
        ("Rừng Nguyên Sinh Bạt Ngàn", 0.72, 0.62, (90, 230, 130), "right"),
        ("Châu Thổ Đầm Lầy Cá Cổ", 0.58, 0.88, (100, 210, 255), "left"),
        ("Đảo Tiền Tiêu Đông Nam", 0.88, 0.87, (160, 240, 180), "top"),
    ]

    for lm_name, pu, pv, pcol, align in landmarks:
        px = int(round(pu * out_size))
        py = int(round(pv * out_size))
        # Small circular diamond marker
        draw.polygon([(px, py - 6), (px + 5, py), (px, py + 6), (px - 5, py)], fill=pcol + (240,), outline=(10, 25, 40, 220))
        draw.ellipse([(px - 2, py - 2), (px + 2, py + 2)], fill=(255, 255, 255, 255))

        lm_len = len(lm_name) * 7.0
        if align == "left":
            tx = px - int(lm_len) - 8
            ty = py - 7
        elif align == "top":
            tx = px - int(lm_len // 2)
            ty = py - 20
        else:
            tx = px + 8
            ty = py - 7

        # Clamp to canvas
        tx = max(8, min(out_size - int(lm_len) - 8, tx))
        ty = max(8, min(out_size - 20, ty))

        # Label with shadow
        draw.text((tx + 1, ty + 1), lm_name, fill=(10, 18, 28, 230), font=font_landmark)
        draw.text((tx, ty), lm_name, fill=(245, 248, 250, 240), font=font_landmark)

    final_img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return final_img


# ---------------------------------------------------------------------------
# Public Generator Entry Point
# ---------------------------------------------------------------------------

def generate_natural_overworld(
    seed: int = 7,
    size_px: int = 1024,
    out_path: str | Path = "assets/sprites/world_overview_macro.png",
) -> Tuple[Path, Path]:
    """Generate the grand complete continental overworld map."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fields = build_grand_continent_fields(seed=seed, grid_size=512)
    img = render_grand_overworld(fields, out_size=size_px)
    img.save(out_path, optimize=True)

    npz_path = out_path.with_name(out_path.stem + "_field.npz")
    dy, dx = np.gradient(fields["elev"])
    slope = np.hypot(dx, dy).astype(np.float32)
    np.savez_compressed(
        npz_path,
        elevation=fields["elev"].astype(np.float32),
        moisture=fields["moisture"].astype(np.float32),
        temperature=fields["temperature"].astype(np.float32),
        land=fields["land"].astype(np.uint8),
        is_land=fields["land"],
        river=fields["river"].astype(np.uint8),
        river_mask=fields["river"],
        biome=fields["biome"],
        region=fields["biome"],
        slope=slope,
        world_width=int(size_px),
        world_height=int(size_px),
        seed=int(seed),
    )

    regions = [
        {"id": "glacial_massif", "name": "Dãy Núi Băng Tuyết & Ma Mút", "biome": "alpine_snow", "center_uv": [0.67, 0.26]},
        {"id": "nw_tundra_horn", "name": "Bán Đảo Lãnh Nguyên Phương Bắc", "biome": "tundra", "center_uv": [0.22, 0.14]},
        {"id": "amber_highlands", "name": "Cao Nguyên Hoàng Thổ", "biome": "amber_highland", "center_uv": [0.48, 0.22]},
        {"id": "emerald_heartland", "name": "Thung Lũng Hươu Khổng Lồ", "biome": "temperate_valley", "center_uv": [0.52, 0.44]},
        {"id": "primeval_jungle", "name": "Rừng Mưa Nhiệt Đới Nguyên Sinh", "biome": "primeval_jungle", "center_uv": [0.72, 0.62]},
        {"id": "red_canyon_desert", "name": "Hoang Mạc Cát Đỏ & Đàn Bison", "biome": "sand_desert", "center_uv": [0.31, 0.77]},
        {"id": "wetland_delta", "name": "Châu Thổ Đầm Lầy Cá Cổ", "biome": "wetland_delta", "center_uv": [0.59, 0.88]},
        {"id": "se_sanctuary", "name": "Đảo Tiền Tiêu Đông Nam", "biome": "coastal_sanctuary", "center_uv": [0.88, 0.88]},
    ]
    json_path = out_path.with_name(out_path.stem + "_regions.json")
    land_pct = float(round(100.0 * float(fields["land"].mean()), 1))
    json_path.write_text(
        json.dumps({"seed": seed, "land_percent": land_pct, "regions": regions}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return out_path, json_path


if __name__ == "__main__":
    s = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    out = sys.argv[2] if len(sys.argv) > 2 else "assets/sprites/world_overview_macro.png"
    p, _ = generate_natural_overworld(seed=s, size_px=1024, out_path=out)
    f = np.load(p.with_name(p.stem + "_field.npz"))
    land_pct = int(round(100.0 * float(f["land"].mean())))
    print(f"Grand continent overworld saved: {p} (1024x1024), land={land_pct}%")
