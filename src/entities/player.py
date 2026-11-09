"""
Player Entity for Green Valley Tales.
Handles 4-directional movement, Mouse Click-to-Move, hybrid keyboard-mouse controls,
stamina management, tool swinging animations, and interaction targeting.
"""

import pygame
import math
from src.settings import (
    TILE_SIZE, PLAYER_SPEED, PLAYER_MAX_STAMINA,
    STAMINA_COST_HOE, STAMINA_COST_WATER, STAMINA_COST_AXE,
    STAMINA_COST_PICKAXE, STAMINA_COST_SCYTHE, STAMINA_COST_FISHING,
    TOOL_HOE, TOOL_WATER_CAN, TOOL_AXE, TOOL_PICKAXE, TOOL_SCYTHE, TOOL_FISHING_ROD
)

class Player:
    def __init__(self, x=1560.0, y=1780.0):
        self.x = float(x)
        self.y = float(y)
        
        self.direction = "down"
        self.vx = 0.0
        self.vy = 0.0
        self.is_moving = False
        
        # Animation
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.action_state = None   # "hoe", "axe", "water"
        self.action_timer = 0.0
        
        # Mouse Click-to-Move destination
        self.move_target = None  # (world_x, world_y)
        self.click_marker_timer = 0.0
        self.click_marker_pos = (0, 0)
        
        # Stamina
        self.max_stamina = PLAYER_MAX_STAMINA
        self.stamina = PLAYER_MAX_STAMINA
        self.is_exhausted = False
        
        # Hitbox at feet for 64px grid collisions
        self.hitbox = pygame.Rect(int(self.x - 18), int(self.y - 12), 36, 24)
        
        # Footstep dust particle state
        self.footstep_timer = 0.0
        self.footstep_emitted = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x - 24), int(self.y - 30), 48, 54)

    @property
    def center(self):
        return (self.x, self.y)

    @property
    def forward_tile(self):
        """Calculates grid tile (col, row) directly in front of facing direction."""
        cx, cy = self.center
        reach = TILE_SIZE
        if self.direction == "down":
            cy += reach
        elif self.direction == "up":
            cy -= reach
        elif self.direction == "left":
            cx -= reach
        elif self.direction == "right":
            cx += reach

        col = int(cx // TILE_SIZE)
        row = int(cy // TILE_SIZE)
        return col, row

    def face_towards(self, target_world_x, target_world_y):
        """Face towards a specific world coordinate (e.g. mouse cursor)."""
        cx, cy = self.center
        dx = target_world_x - cx
        dy = target_world_y - cy

        if abs(dx) > abs(dy):
            self.direction = "right" if dx > 0 else "left"
        else:
            self.direction = "down" if dy > 0 else "up"

    def is_in_reach(self, col, row, max_tiles=2.2):
        """Checks if a grid tile is within arm's reach of player."""
        cx, cy = self.center
        tile_center_x = col * TILE_SIZE + (TILE_SIZE // 2)
        tile_center_y = row * TILE_SIZE + (TILE_SIZE // 2)
        dist = math.hypot(tile_center_x - cx, tile_center_y - cy)
        return dist <= (max_tiles * TILE_SIZE)

    def trigger_action(self, action_name):
        """Triggers tool swinging animation."""
        self.action_state = action_name
        self.action_timer = 0.35

    def set_move_target(self, world_x, world_y):
        """Command player to navigate to mouse click destination."""
        self.move_target = (float(world_x), float(world_y))
        self.click_marker_pos = (int(world_x), int(world_y))
        self.click_marker_timer = 0.5

    def handle_keyboard_input(self, keys):
        """Manual WASD / Arrow keys movement. Cancels mouse pathing."""
        dx, dy = 0.0, 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1.0
            self.direction = "up"
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1.0
            self.direction = "down"
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1.0
            self.direction = "left"
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1.0
            self.direction = "right"

        if dx != 0 or dy != 0:
            self.move_target = None
            if dx != 0 and dy != 0:
                dx *= 0.7071
                dy *= 0.7071

            speed = PLAYER_SPEED * (0.5 if self.is_exhausted else 1.0)
            self.vx = dx * speed
            self.vy = dy * speed
            self.is_moving = True
        elif self.move_target is None:
            self.vx = 0.0
            self.vy = 0.0
            self.is_moving = False

    def update(self, dt, map_manager):
        # Do not let a debugger pause or a window drag move the player through
        # walls in one very large simulation step.
        dt = min(dt, 0.05)
        # Click marker ripple timer
        if self.click_marker_timer > 0:
            self.click_marker_timer -= dt

        # Tool swing animation timer
        if self.action_timer > 0:
            self.action_timer -= dt
            if self.action_timer <= 0:
                self.action_state = None

        # Mouse click-to-move navigation
        if self.move_target:
            tx, ty = self.move_target
            cx, cy = self.center
            dx = tx - cx
            dy = ty - cy
            dist = math.hypot(dx, dy)

            if dist < 8.0:
                self.move_target = None
                self.vx = 0.0
                self.vy = 0.0
                self.is_moving = False
            else:
                self.face_towards(tx, ty)
                speed = PLAYER_SPEED * (0.5 if self.is_exhausted else 1.0)
                self.vx = (dx / dist) * speed
                self.vy = (dy / dist) * speed
                self.is_moving = True

        # Walking animation frames (4 frames) & footstep particle timing
        self.footstep_emitted = False
        if self.is_moving:
            self.anim_timer += dt
            if self.anim_timer >= 0.14:
                self.anim_timer = 0.0
                self.anim_frame = (self.anim_frame + 1) % 4

            self.footstep_timer += dt
            if self.footstep_timer >= 0.22:
                self.footstep_timer = 0.0
                self.footstep_emitted = True
        else:
            self.footstep_timer = 0.0
            self.anim_timer += dt
            if self.anim_timer >= 0.5:
                self.anim_timer = 0.0
                self.anim_frame = (self.anim_frame + 1) % 2

        # Move X & check collision
        old_x = self.x
        self.x += self.vx * dt
        self.hitbox.centerx = int(self.x)
        if map_manager.check_collision(self.hitbox):
            self.x = old_x
            self.hitbox.centerx = int(self.x)
            if self.move_target and abs(self.vy) < 0.1:
                self.move_target = None

        # Move Y & check collision
        old_y = self.y
        self.y += self.vy * dt
        self.hitbox.centery = int(self.y)
        if map_manager.check_collision(self.hitbox):
            self.y = old_y
            self.hitbox.centery = int(self.y)
            if self.move_target and abs(self.vx) < 0.1:
                self.move_target = None

    def draw_click_marker(self, screen, camera):
        """Draw animated ripple ring when mouse clicks to move."""
        if self.click_marker_timer > 0:
            mx, my = camera.apply_pos(self.click_marker_pos)
            radius = int((1.0 - (self.click_marker_timer / 0.5)) * 18) + 6
            alpha = int((self.click_marker_timer / 0.5) * 220)
            ripple_surf = pygame.Surface((radius * 2 + 6, radius * 2 + 6), pygame.SRCALPHA)
            pygame.draw.circle(ripple_surf, (255, 235, 120, alpha), (radius + 3, radius + 3), radius, 2)
            pygame.draw.circle(ripple_surf, (255, 255, 255, alpha), (radius + 3, radius + 3), 3)
            screen.blit(ripple_surf, (mx - radius - 3, my - radius - 3))

    def consume_stamina(self, amount):
        self.stamina = max(0.0, self.stamina - amount)
        if self.stamina <= 0.0:
            self.is_exhausted = True

    def recover_stamina(self, amount):
        self.stamina = min(self.max_stamina, self.stamina + amount)
        if self.stamina > 20.0:
            self.is_exhausted = False

    def get_tool_stamina_cost(self, tool_id):
        costs = {
            TOOL_HOE: STAMINA_COST_HOE,
            TOOL_WATER_CAN: STAMINA_COST_WATER,
            TOOL_AXE: STAMINA_COST_AXE,
            TOOL_PICKAXE: STAMINA_COST_PICKAXE,
            TOOL_SCYTHE: STAMINA_COST_SCYTHE,
            TOOL_FISHING_ROD: STAMINA_COST_FISHING
        }
        return costs.get(tool_id, 1.0)

    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "direction": self.direction,
            "stamina": self.stamina,
            "is_exhausted": self.is_exhausted
        }

    def from_dict(self, data):
        self.x = data.get("x", 1560.0)
        self.y = data.get("y", 1780.0)
        self.direction = data.get("direction", "down")
        self.stamina = data.get("stamina", PLAYER_MAX_STAMINA)
        self.is_exhausted = data.get("is_exhausted", False)
        self.hitbox.centerx = int(self.x)
        self.hitbox.centery = int(self.y)
