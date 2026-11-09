"""
Prehistoric Obstacles and Resource Entities for Stone Age: Dawn of Tribe.
Includes:
- Ground Pickups: Branches, River Pebbles, Wild Berry Bushes, Clay Patches
- Trees & Timber: Forest Trees, Fallen Logs, Ancient Stumps
- Stone & Minerals: Small Rocks, Boulders, Copper Veins
"""

import pygame
import random
import math
from src.settings import TILE_SIZE

class Obstacle:
    def __init__(self, obs_type, col, row, health=1, max_health=1, jitter_x=None, jitter_y=None, variant=None, growth_stage="ripe"):
        self.obs_type = obs_type
        self.col = col
        self.row = row
        self.health = health
        self.max_health = max_health
        self.shake_offset = 0.0
        self.shake_timer = 0.0
        self.growth_stage = growth_stage  # "sprout", "ripe", "depleted"
        self.regrow_timer = 0.0
        
        # Sub-tile pixel jitter for organic, non-grid nature placement
        if jitter_x is not None:
            self.jitter_x = jitter_x
        else:
            self.jitter_x = random.randint(-12, 12) if self.is_ground_pickup else random.randint(-4, 4)
            
        if jitter_y is not None:
            self.jitter_y = jitter_y
        else:
            self.jitter_y = random.randint(-10, 10) if self.is_ground_pickup else random.randint(-4, 4)

        # Visual variant index (e.g. 0..2 for berry shrubs or mushrooms)
        self.variant = variant if variant is not None else random.randint(0, 2)

    @property
    def is_ground_pickup(self):
        """Returns True if this resource is a small ground prop (branch, pebble, mushroom)."""
        return self.obs_type in ["branch", "pebble", "wild_bush", "weeds", "prop_bone", "prop_mushroom"]

    def update(self, dt=1/60.0):
        if self.shake_timer > 0:
            self.shake_timer -= dt
            if self.shake_timer <= 0:
                self.shake_timer = 0.0
                self.shake_offset = 0.0
            else:
                progress = self.shake_timer / 0.28
                self.shake_offset = math.sin((0.28 - self.shake_timer) * 36.0) * 6.0 * progress
        else:
            self.shake_offset = 0.0

        # Botanical Regeneration Lifecycle (Depleted -> Sprout -> Ripe)
        if self.regrow_timer > 0:
            self.regrow_timer -= dt
            if self.regrow_timer <= 0:
                if self.growth_stage == "depleted":
                    self.growth_stage = "sprout"
                    self.regrow_timer = 60.0
                elif self.growth_stage == "sprout":
                    self.growth_stage = "ripe"
                    self.regrow_timer = 0.0

    def to_dict(self):
        return {
            "type": self.obs_type,
            "col": self.col,
            "row": self.row,
            "health": self.health,
            "max_health": self.max_health,
            "jitter_x": self.jitter_x,
            "jitter_y": self.jitter_y,
            "variant": self.variant,
            "growth_stage": self.growth_stage
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["type"],
            data["col"],
            data["row"],
            data.get("health", 1),
            data.get("max_health", 1),
            jitter_x=data.get("jitter_x"),
            jitter_y=data.get("jitter_y"),
            variant=data.get("variant"),
            growth_stage=data.get("growth_stage", "ripe")
        )
