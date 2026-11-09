"""
Smooth 2D Camera for Stone Age: Primeval World.
Tracks target entity with dt-based exponential smoothing
and clamps to world boundaries. Supports screen shake.
"""

import pygame
import random
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, WORLD_WIDTH, WORLD_HEIGHT

class Camera:
    def __init__(self, width=WORLD_WIDTH, height=WORLD_HEIGHT):
        self.width = width
        self.height = height
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.shake_x = 0.0
        self.shake_y = 0.0
        self._shake_timer = 0.0
        self._shake_duration = 0.0
        self._shake_intensity = 0.0
        self._smoothing = 6.0  # Higher = snappier, lower = smoother

    def snap_to(self, target_rect):
        """Immediately snaps camera to target without lerp."""
        self.offset_x = float(target_rect.centerx - SCREEN_WIDTH // 2)
        self.offset_y = float(target_rect.centery - SCREEN_HEIGHT // 2)
        self._clamp()

    def update(self, target_rect, dt=1/60.0):
        """Center the camera on target_rect with dt-based exponential smoothing."""
        target_x = float(target_rect.centerx - SCREEN_WIDTH // 2)
        target_y = float(target_rect.centery - SCREEN_HEIGHT // 2)

        # Exponential smoothing: camera feels the same at any framerate
        factor = 1.0 - pow(0.5, self._smoothing * dt)
        self.offset_x += (target_x - self.offset_x) * factor
        self.offset_y += (target_y - self.offset_y) * factor

        # Decay internal screen shake
        if self._shake_timer > 0:
            self._shake_timer -= dt
            if self._shake_timer <= 0:
                self._shake_timer = 0.0
                self.shake_x = 0.0
                self.shake_y = 0.0
            else:
                fade = self._shake_timer / max(0.001, self._shake_duration)
                self.shake_x = random.uniform(-self._shake_intensity, self._shake_intensity) * fade
                self.shake_y = random.uniform(-self._shake_intensity, self._shake_intensity) * fade

        self._clamp()

    def trigger_shake(self, intensity=3.5, duration=0.15):
        """Trigger an instant decaying screen shake effect (e.g. for impacts)."""
        self._shake_intensity = max(self._shake_intensity, intensity)
        self._shake_duration = duration
        self._shake_timer = duration

    def _clamp(self):
        """Clamp camera to world boundaries."""
        self.offset_x = max(0, min(self.offset_x, self.width - SCREEN_WIDTH))
        self.offset_y = max(0, min(self.offset_y, self.height - SCREEN_HEIGHT))

    def set_shake(self, sx, sy):
        """Set screen shake offset (from weather system)."""
        if self._shake_timer <= 0:
            self.shake_x = sx
            self.shake_y = sy

    def apply(self, entity_or_rect):
        """Returns rect shifted by camera offset (includes shake)."""
        if hasattr(entity_or_rect, "rect"):
            r = entity_or_rect.rect
        else:
            r = entity_or_rect
        return r.move(-int(self.offset_x + self.shake_x), 
                      -int(self.offset_y + self.shake_y))

    def apply_pos(self, pos):
        """Convert world coordinates to screen coordinates."""
        return (int(pos[0] - self.offset_x - self.shake_x), 
                int(pos[1] - self.offset_y - self.shake_y))

    world_to_screen = apply_pos

    def screen_to_world(self, screen_pos):
        """Convert screen coordinates back to world coordinates."""
        return (int(screen_pos[0] + self.offset_x + self.shake_x), 
                int(screen_pos[1] + self.offset_y + self.shake_y))
