"""
Free Spectator Camera for Stone Age Nature Observation Simulator.
Allows smooth panning across the continent using WASD / Arrow keys,
speed boost via Shift, and Middle-Mouse drag.
"""

import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, WORLD_WIDTH, WORLD_HEIGHT
from src.core.camera import Camera

class SpectatorTarget:
    """Virtual target representing the current observation point."""
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.rect = pygame.Rect(int(self.x) - 16, int(self.y) - 16, 32, 32)

    def set_pos(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.rect.center = (int(self.x), int(self.y))

    @property
    def centerx(self):
        return int(self.x)

    @property
    def centery(self):
        return int(self.y)


class FreeCamera:
    def __init__(self, camera: Camera, start_x=None, start_y=None, world_w=WORLD_WIDTH, world_h=WORLD_HEIGHT):
        self.camera = camera
        self.world_w = world_w
        self.world_h = world_h

        # Default start at map center if not specified
        sx = start_x if start_x is not None else world_w // 2
        sy = start_y if start_y is not None else world_h // 2
        self.target = SpectatorTarget(sx, sy)

        # Pan movement settings
        self.base_speed = 650.0       # Pixels per second
        self.fast_speed = 1500.0      # Pixels per second when holding Shift
        self.slow_speed = 280.0       # Pixels per second when holding Ctrl

        # Mouse drag state (Middle mouse or Right mouse)
        self.is_dragging = False
        self.drag_start_mouse = (0, 0)
        self.drag_start_target = (0.0, 0.0)

        # Snap initial camera position
        self.camera.snap_to(self.target.rect)

    def handle_event(self, event):
        """Handles mouse drag panning (middle mouse or right mouse)."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (2, 3):  # Middle click (2) or Right click (3)
                self.is_dragging = True
                self.drag_start_mouse = event.pos
                self.drag_start_target = (self.target.x, self.target.y)
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button in (2, 3):
                self.is_dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                dx = event.pos[0] - self.drag_start_mouse[0]
                dy = event.pos[1] - self.drag_start_mouse[1]
                new_x = self.drag_start_target[0] - dx
                new_y = self.drag_start_target[1] - dy
                self.set_pos(new_x, new_y)
                return True
        return False

    def update(self, dt):
        """Reads keyboard inputs (WASD / Arrows) and smoothly pans camera."""
        keys = pygame.key.get_pressed()

        # Determine pan speed based on modifiers
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            speed = self.fast_speed
        elif keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
            speed = self.slow_speed
        else:
            speed = self.base_speed

        dx = 0.0
        dy = 0.0

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1.0

        if dx != 0.0 or dy != 0.0:
            # Normalize diagonal speed
            length = (dx * dx + dy * dy) ** 0.5
            dx /= length
            dy /= length

            new_x = self.target.x + dx * speed * dt
            new_y = self.target.y + dy * speed * dt
            self.set_pos(new_x, new_y)

        # Update smooth camera tracking
        self.camera.update(self.target.rect, dt)

    def set_pos(self, x, y):
        """Sets and clamps spectator target within map bounds."""
        min_x = SCREEN_WIDTH // 2
        max_x = max(min_x, self.world_w - SCREEN_WIDTH // 2)
        min_y = SCREEN_HEIGHT // 2
        max_y = max(min_y, self.world_h - SCREEN_HEIGHT // 2)

        clamped_x = max(min_x, min(x, max_x))
        clamped_y = max(min_y, min(y, max_y))
        self.target.set_pos(clamped_x, clamped_y)
