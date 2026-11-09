"""
Fog of War System for Stone Age: Dawn of Tribe.
Hệ thống Sương Mù Chiến Tranh 3 Tầng (AOE Style):
- 0: Chưa từng thám hiểm (Đen kịt - Unexplored)
- 1: Đã từng đi qua (Mờ xám - Fogged, chỉ thấy địa hình tĩnh)
- 2: Đang có tầm nhìn (Sáng tỏ - Visible, thấy động vật và dã thú)
"""

import pygame
import math
from src.settings import TILE_SIZE, MAP_COLS, MAP_ROWS

STATE_UNEXPLORED = 0
STATE_FOGGED = 1
STATE_VISIBLE = 2

class FogOfWar:
    def __init__(self, cols=MAP_COLS, rows=MAP_ROWS):
        self.cols = cols
        self.rows = rows
        # 2D Grid: 0 = Unexplored, 1 = Fogged, 2 = Visible
        self.grid = [[STATE_UNEXPLORED for _ in range(cols)] for _ in range(rows)]
        self.fog_surface = pygame.Surface((cols * TILE_SIZE, rows * TILE_SIZE), pygame.SRCALPHA)
        self.fog_surface.fill((10, 8, 6, 255))
        self.is_enabled = True

        # Pre-reveal camp perimeter (bán kính 16 ô quanh bản doanh cội nguồn (40, 38))
        self.reveal_circle(40, 38, radius_tiles=16)

    def reveal_circle(self, center_col, center_row, radius_tiles=6):
        """Permanently explores and reveals circle of tiles."""
        r_sq = radius_tiles * radius_tiles
        for dr in range(-radius_tiles, radius_tiles + 1):
            for dc in range(-radius_tiles, radius_tiles + 1):
                if dr * dr + dc * dc <= r_sq:
                    c = center_col + dc
                    r = center_row + dr
                    if 0 <= c < self.cols and 0 <= r < self.rows:
                        self.grid[r][c] = max(self.grid[r][c], STATE_FOGGED)

    def update_visibility(self, vision_sources):
        """
        Updates dynamic vision.
        vision_sources: List of (world_x, world_y, radius_tiles)
        """
        if not self.is_enabled:
            return

        # 1. Degrade all currently VISIBLE (2) tiles to FOGGED (1)
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == STATE_VISIBLE:
                    self.grid[r][c] = STATE_FOGGED

        # 2. Promote tiles within sight range of active units to VISIBLE (2)
        for wx, wy, radius in vision_sources:
            center_col = int(wx // TILE_SIZE)
            center_row = int(wy // TILE_SIZE)
            r_sq = radius * radius

            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if dr * dr + dc * dc <= r_sq:
                        c = center_col + dc
                        r = center_row + dr
                        if 0 <= c < self.cols and 0 <= r < self.rows:
                            self.grid[r][c] = STATE_VISIBLE

    def is_tile_visible(self, col, row):
        """Returns True if tile is currently in active sight."""
        if not self.is_enabled:
            return True
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.grid[row][col] == STATE_VISIBLE
        return False

    def is_tile_explored(self, col, row):
        """Returns True if tile has ever been visited."""
        if not self.is_enabled:
            return True
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.grid[row][col] >= STATE_FOGGED
        return False

    def draw(self, surface, camera):
        """Draws fog of war overlay over visible camera viewport."""
        if not self.is_enabled:
            return

        ts = TILE_SIZE
        # Determine visible tile bounds on screen
        min_col = max(0, int(camera.offset_x // ts))
        max_col = min(self.cols, int((camera.offset_x + surface.get_width()) // ts) + 2)
        min_row = max(0, int(camera.offset_y // ts))
        max_row = min(self.rows, int((camera.offset_y + surface.get_height()) // ts) + 2)

        # Draw grid fog cells
        for r in range(min_row, max_row):
            for c in range(min_col, max_col):
                state = self.grid[r][c]
                if state == STATE_VISIBLE:
                    continue  # Perfectly clear

                sx, sy = camera.world_to_screen((c * ts, r * ts))
                if state == STATE_UNEXPLORED:
                    # Pitch black unknown veil
                    pygame.draw.rect(surface, (12, 10, 8), (sx, sy, ts, ts))
                elif state == STATE_FOGGED:
                    # Soft translucent grey veil (obscures moving animals)
                    fog_cell = pygame.Surface((ts, ts), pygame.SRCALPHA)
                    fog_cell.fill((16, 12, 8, 140))
                    surface.blit(fog_cell, (sx, sy))
