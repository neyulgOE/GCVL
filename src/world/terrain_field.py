"""
Resolution-independent continent field for Prehistoric Stone Age Natural World.

Noise is sampled in normalized world coordinates u, v in [0, 1], not tile indexes,
so any map dimensions (40x40, 80x80, 200x200) maintain the exact same landforms.
Heights are stretched across the full dynamic range [0, 1] via percentile normalization (_stretch),
guaranteeing sharp shores, floodplains, hills, and crags without flat single-color tiers.
(Pure Primeval Nature — Zero human structures or artificial elements).
"""

from __future__ import annotations
import math
import random
from typing import Dict, List, Sequence, Tuple, Set, Any

Pos = Tuple[int, int]


class GradientNoise2D:
    """Self-contained 2D gradient noise with Fractal Brownian Motion (fBm)."""

    def __init__(self, noise_salt: int = 42) -> None:
        rng = random.Random(noise_salt)
        perm = list(range(256))
        rng.shuffle(perm)
        self.perm = perm + perm
        self.gradients = [
            (math.cos(2.0 * math.pi * i / 12.0), math.sin(2.0 * math.pi * i / 12.0))
            for i in range(12)
        ]

    @staticmethod
    def _fade(t: float) -> float:
        return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + t * (b - a)

    def _grad(self, hash_val: int, x: float, y: float) -> float:
        gx, gy = self.gradients[hash_val % 12]
        return gx * x + gy * y

    def noise2d(self, x: float, y: float) -> float:
        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        u = self._fade(xf)
        v = self._fade(yf)
        aa = self.perm[self.perm[xi] + yi]
        ab = self.perm[self.perm[xi] + yi + 1]
        ba = self.perm[self.perm[xi + 1] + yi]
        bb = self.perm[self.perm[xi + 1] + yi + 1]
        x1 = self._lerp(self._grad(aa, xf, yf), self._grad(ba, xf - 1.0, yf), u)
        x2 = self._lerp(
            self._grad(ab, xf, yf - 1.0), self._grad(bb, xf - 1.0, yf - 1.0), u
        )
        return self._lerp(x1, x2, v)

    def fbm(
        self,
        x: float,
        y: float,
        octaves: int = 4,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
        base_scale: float = 1.0,
    ) -> float:
        total = 0.0
        amplitude = 1.0
        frequency = base_scale
        max_value = 0.0
        for _ in range(octaves):
            total += self.noise2d(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity
        if max_value <= 0.0:
            return 0.5
        return max(0.0, min(1.0, 0.5 + (total / max_value) * 0.85))


def sample_continent(
    u: float,
    v: float,
    elev_n: GradientNoise2D,
    moist_n: GradientNoise2D,
    temp_n: GradientNoise2D,
    ridge_n: GradientNoise2D,
) -> Tuple[float, float, float]:
    """Sample continent topography in normalized [0, 1] coordinates."""
    # Domain warping
    wu = u + (elev_n.fbm(u + 3.1, v + 0.4, octaves=3, persistence=0.5, base_scale=2.1) - 0.5) * 0.10
    wv = v + (elev_n.fbm(u + 8.7, v + 2.2, octaves=3, persistence=0.5, base_scale=2.1) - 0.5) * 0.10

    # Base FBM noise & ridged multifractal
    n = elev_n.fbm(wu, wv, octaves=5, persistence=0.56, base_scale=3.4)
    ridged = 1.0 - abs(ridge_n.fbm(wu + 2.0, wv, octaves=4, persistence=0.5, base_scale=4.8) * 2.0 - 1.0)

    # Directional continental biases
    north = max(0.0, (0.32 - wv) / 0.32)
    west = max(0.0, (0.28 - wu) / 0.28)
    south = max(0.0, (wv - 0.74) / 0.26)

    h = n
    h += 0.20 * north * (0.30 + 0.70 * ridged)
    h += 0.12 * west * ridged
    h -= 0.16 * south
    h += 0.15 * (ridged ** 1.3) * max(0.0, n - 0.42)
    h = max(0.0, min(1.0, h))

    # Moisture distribution (eastern primeval forest corridor & southern wetland)
    m = moist_n.fbm(wu, wv, octaves=4, persistence=0.52, base_scale=3.1)
    east = max(0.0, (wu - 0.55) / 0.45)
    m = max(0.0, min(1.0, m + 0.14 * east + 0.12 * south - 0.10 * west))

    # Temperature (colder north alpine, warmer southern delta)
    raw_temp = temp_n.fbm(wu, wv, octaves=3, persistence=0.5, base_scale=2.4)
    temperature = max(0.0, min(1.0, 0.72 * v + 0.28 * raw_temp))

    return h, m, temperature


def river_center(row_f: float, cols: int, rows: int) -> float:
    """Meandering river spine scaled proportionally to map width."""
    t = row_f / max(1.0, rows - 1.0)
    wave = 0.10 * math.sin(t * math.pi * 2.15) + 0.045 * math.cos(t * math.pi * 4.1)
    return cols * (0.58 + wave)


def river_half_width(row_f: float, cols: int, rows: int) -> float:
    """Hydraulic channel width, narrower in northern headwaters, broader in southern basin."""
    t = row_f / max(1.0, rows - 1.0)
    scale = max(0.65, cols / 80.0)
    if t <= 0.28:
        base = 1.35 + 0.25 * math.sin(t * 12.0)
    elif t >= 0.78:
        base = 2.5 + 0.55 * math.sin(t * 10.0)
    else:
        base = 1.9 + 0.35 * math.sin(t * 9.0)
    ford = 1.15 * math.exp(-((t - 0.45) ** 2) / 0.0035)
    return max(0.75, (base + ford) * scale)


def _line(a: Pos, b: Pos) -> List[Pos]:
    """Bresenham line algorithm for ramps and natural paths."""
    x0, y0 = a
    x1, y1 = b
    pts: List[Pos] = []
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return pts


def _stretch(grid: List[List[float]]) -> None:
    """Percentile normalization stretching heights across full dynamic range [0.0, 1.0]."""
    vals = sorted(v for row in grid for v in row)
    if len(vals) < 4:
        return
    lo = vals[max(0, int(len(vals) * 0.06))]
    hi = vals[min(len(vals) - 1, int(len(vals) * 0.94))]
    span = hi - lo
    if span < 1e-4:
        return
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            row[c] = max(0.0, min(1.0, (v - lo) / span))


def _inside(c: int, r: int, cols: int, rows: int) -> bool:
    return 0 <= c < cols and 0 <= r < rows


def build_natural_play_field(cols: int, rows: int, noise_salt: int = 2026) -> Dict[str, Any]:
    """
    Resolution-independent natural field generator for Stone Age wilderness.
    - 5 Discrete Elevation Tiers (0..4) with 2.5D crag cliff drops and natural walkable ramps.
    - 5 Ground Material Horizons: Scree Talus, Forest Humus, Steppe Meadow, Riparian Mud, River Sand.
    - S-Curve Meandering River with Stepping Stone Ford and Asymmetrical Point Bar Sandbanks.
    - 100% Pure Nature — Zero human structures or artificial elements.
    """
    cols = max(16, int(cols))
    rows = max(16, int(rows))
    elev_n = GradientNoise2D(noise_salt)
    moist_n = GradientNoise2D(noise_salt + 1337)
    temp_n = GradientNoise2D(noise_salt + 7919)
    ridge_n = GradientNoise2D(noise_salt + 97)

    # 1. Heightmap generation via normalized sampling (u, v in 0..1)
    height = [[0.0] * cols for _ in range(rows)]
    moisture = [[0.0] * cols for _ in range(rows)]
    temperature = [[0.0] * cols for _ in range(rows)]

    for r in range(rows):
        v = r / max(1.0, rows - 1.0)
        for c in range(cols):
            u = c / max(1.0, cols - 1.0)
            h, m, t = sample_continent(u, v, elev_n, moist_n, temp_n, ridge_n)
            height[r][c] = h
            moisture[r][c] = m
            temperature[r][c] = t

    # Full dynamic range stretching
    _stretch(height)

    ford_row = int(round(0.45 * (rows - 1)))
    log_row = int(round(0.60 * (rows - 1)))
    point_bar_row = int(round(0.48 * (rows - 1)))

    # 2. Elevation Tiers (Levels 0..4)
    elev = [[2] * cols for _ in range(rows)]
    for r in range(rows):
        rc = river_center(r, cols, rows)
        hw = river_half_width(r, cols, rows)
        v = r / max(1.0, rows - 1.0)
        for c in range(cols):
            h = height[r][c]
            in_channel = abs((c + 0.5) - rc) <= hw + 0.15
            near = abs((c + 0.5) - rc) <= hw + 3.2 * max(0.65, cols / 80.0)
            if in_channel:
                tier = 0
            elif near and h < 0.72:
                tier = 1
            elif v >= 0.78 and h < 0.58:
                tier = 1
            elif h < 0.34:
                tier = 1
            elif h < 0.52:
                tier = 2
            elif h < 0.70:
                tier = 3
            else:
                tier = 4
            elev[r][c] = tier

    # 3. Natural Ramps connecting terraces & highland passes
    ramps: Set[Pos] = set()

    # Pass connecting northern highland terrace to central valley
    central_c = int(round(cols * 0.48))
    central_r = int(round(rows * 0.42))
    north_pass_top = (central_c, max(0, central_r - 8))
    north_pass_bot = (central_c, central_r)
    for c, r in _line(north_pass_top, north_pass_bot):
        ramps.add((c, r))
        elev[r][c] = 2

    # Western Highland Pass
    west_r = int(round(rows * 0.40))
    west_high = (max(0, int(cols * 0.08)), west_r)
    west_mouth = (min(cols - 1, int(cols * 0.32)), west_r)
    for c, r in _line(west_high, west_mouth):
        ramps.add((c, r))
        if elev[r][c] >= 4:
            elev[r][c] = 3
        elif elev[r][c] == 3 and c > west_high[0] + 1:
            elev[r][c] = 2

    # 4. 2.5D Cliff Drops (South, East, West)
    cliff_s = [[0] * cols for _ in range(rows)]
    cliff_e = [[0] * cols for _ in range(rows)]
    cliff_w = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if (c, r) in ramps:
                continue
            cur = elev[r][c]
            if r < rows - 1 and (c, r + 1) not in ramps:
                s = elev[r + 1][c]
                if cur > s and s >= 1:
                    cliff_s[r][c] = cur - s
            if c < cols - 1 and (c + 1, r) not in ramps:
                e = elev[r][c + 1]
                if cur > e and e >= 1:
                    cliff_e[r][c] = cur - e
            if c > 0 and (c - 1, r) not in ramps:
                w = elev[r][c - 1]
                if cur > w and w >= 1:
                    cliff_w[r][c] = cur - w

    # 5. Ground Material Horizons
    terrain = [["steppe_meadow"] * cols for _ in range(rows)]
    water: Set[Pos] = set()
    solid: Set[Pos] = set()

    for r in range(rows):
        rc = river_center(r, cols, rows)
        hw = river_half_width(r, cols, rows)
        v = r / max(1.0, rows - 1.0)
        for c in range(cols):
            u = c / max(1.0, cols - 1.0)
            tier = elev[r][c]
            dist_river = abs((c + 0.5) - rc)

            if tier == 0 or dist_river <= hw + 0.15:
                terrain[r][c] = "water"
                elev[r][c] = 0
                water.add((c, r))
                solid.add((c, r))
            elif dist_river <= hw + 3.2:
                # Amber Point Bar Sandbanks along the river
                terrain[r][c] = "point_bar_sand"
            elif tier >= 4 or (tier == 3 and v < 0.42):
                terrain[r][c] = "scree_talus"
            elif u >= 0.68 and tier <= 3:
                terrain[r][c] = "forest_humus"
            elif v >= 0.75 or tier == 1:
                terrain[r][c] = "riparian_mud"
            else:
                terrain[r][c] = "steppe_meadow"

    # 6. River Crossings: Stepping Stone Ford
    def open_crossing(row: int, kind: str) -> None:
        rc = river_center(row, cols, rows)
        hw = river_half_width(row, cols, rows)
        for c in range(cols):
            if rc - hw - 0.2 <= c + 0.5 <= rc + hw + 0.2:
                terrain[row][c] = kind
                water.discard((c, row))
                solid.discard((c, row))
                if elev[row][c] == 0:
                    elev[row][c] = 1

    open_crossing(ford_row, "bridge_ford")
    open_crossing(log_row, "bridge_log")

    # 7. Prehistoric Natural Landmarks (Mammoth Fossil Ribs, Upstream Rapids, Monolith)
    rc_pb = int(round(river_center(point_bar_row, cols, rows)))
    hw_pb = int(round(river_half_width(point_bar_row, cols, rows)))
    rc_up = int(round(river_center(12, cols, rows)))

    landmarks = [
        {"type": "colossal_rib_fossils", "col": rc_pb + hw_pb + 2, "row": point_bar_row},
        {"type": "upstream_boulder_cascade", "col": rc_up, "row": 12},
        {"type": "mossy_monolith", "col": int(round(cols * 0.32)), "row": int(round(rows * 0.38))},
    ]

    return {
        "height": height,
        "moisture": moisture,
        "temperature": temperature,
        "elevation": elev,
        "terrain": terrain,
        "water": water,
        "solid": solid,
        "ramps": ramps,
        "cliff_south": cliff_s,
        "cliff_east": cliff_e,
        "cliff_west": cliff_w,
        "landmarks": landmarks,
        "ford_row": ford_row,
        "log_row": log_row,
        "point_bar_row": point_bar_row,
    }


# Backwards compatibility alias for old imports
build_play_field = build_natural_play_field

