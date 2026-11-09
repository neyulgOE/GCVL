"""
Fog of War System (Disabled by default for Full Natural World Observation).
"""

from src.settings import MAP_COLS, MAP_ROWS

STATE_UNEXPLORED = 0
STATE_FOGGED = 1
STATE_VISIBLE = 2


class FogOfWar:
    def __init__(self, cols=MAP_COLS, rows=MAP_ROWS):
        self.cols = cols
        self.rows = rows
        # Mo sang toan bo ban do tu nhien ngay tu dau
        self.grid = [[STATE_VISIBLE for _ in range(cols)] for _ in range(rows)]
        self.is_enabled = False

    def reveal_circle(self, center_col, center_row, radius_tiles=6):
        pass

    def update_visibility(self, vision_sources):
        pass

    def is_tile_visible(self, col, row):
        return True

    def is_tile_explored(self, col, row):
        return True

    def draw(self, surface, camera):
        # Khong ve man den che phu the gioi tu nhien
        return
