"""
Livestock System for Green Valley Tales.
Handles Chickens and Cows with AI roaming, feeding, petting (affection hearts),
and daily production of Eggs and Milk.
"""

import random
import math
from src.settings import ANIMAL_DATA

class Animal:
    def __init__(self, animal_type, x, y, name=None):
        self.animal_type = animal_type
        self.data = ANIMAL_DATA[animal_type]
        self.name = name or self.data["name"].split(" (")[0]
        
        self.x = float(x)
        self.y = float(y)
        self.target_x = self.x
        self.target_y = self.y
        self.vx = 0.0
        self.vy = 0.0
        
        # Pixels per second. Animal movement must use delta time just like
        # player movement so a faster display does not make livestock race.
        self.speed = 48.0 if animal_type in ["chicken", "wild_chicken"] else 30.0
        self.direction = "right"
        self.anim_frame = 0
        self.anim_timer = 0.0
        
        # Stats
        self.affection = 0  # 0 - 1000
        self.is_petted_today = False
        self.is_fed_today = True  # starts fed
        self.has_produced_today = False
        
        # AI State
        self.state = "idle"  # "idle", "walk", "graze"
        self.state_timer = random.uniform(2.0, 5.0)
        self.heart_popup_timer = 0.0

    @property
    def hearts(self):
        """Number of full hearts (0 to 5)."""
        return min(5, self.affection // 200)

    def pet(self):
        """Pet the animal. Returns True if successfully petted for the first time today."""
        if not self.is_petted_today:
            self.is_petted_today = True
            self.affection = min(1000, self.affection + 35)
            self.heart_popup_timer = 2.0
            return True
        return False

    def update(self, dt, home_x, home_y, wander_radius=180):
        # Heart effect timer
        if self.heart_popup_timer > 0:
            self.heart_popup_timer -= dt

        # State machine
        self.state_timer -= dt
        if self.state_timer <= 0:
            self._pick_new_state(home_x, home_y, wander_radius)

        # Movement
        if self.state == "walk":
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.hypot(dx, dy)
            if dist < 4.0:
                self.state = "idle"
                self.state_timer = random.uniform(2.0, 6.0)
            else:
                step = min(dist, self.speed * min(dt, 0.05))
                self.x += (dx / dist) * step
                self.y += (dy / dist) * step
                self.direction = "right" if dx >= 0 else "left"
                
                # Animation
                self.anim_timer += dt
                if self.anim_timer >= 0.2:
                    self.anim_timer = 0
                    self.anim_frame = (self.anim_frame + 1) % 2
        else:
            self.anim_frame = 0

    def _pick_new_state(self, home_x, home_y, radius):
        r = random.random()
        if r < 0.45:
            # Pick a walk destination near its home pasture
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(20, radius)
            self.target_x = home_x + math.cos(angle) * dist
            self.target_y = home_y + math.sin(angle) * dist
            self.state = "walk"
            self.state_timer = random.uniform(4.0, 8.0)
        elif r < 0.75:
            self.state = "graze"
            self.state_timer = random.uniform(3.0, 7.0)
        else:
            self.state = "idle"
            self.state_timer = random.uniform(2.0, 5.0)

    def next_day(self):
        """Called overnight: reset daily interactions and generate products."""
        self.is_petted_today = False
        
        product = None
        if self.is_fed_today:
            # Chance for high quality product based on affection
            high_quality = (random.randint(0, 1000) < self.affection)
            prod_id = self.data["large_product"] if high_quality else self.data["product"]
            prod_name = self.data["large_product_name"] if high_quality else self.data["product_name"]
            prod_price = self.data["large_product_price"] if high_quality else self.data["product_price"]

            product = {
                "id": prod_id,
                "type": "animal_product",
                "name": prod_name,
                "price": prod_price,
                "animal_name": self.name
            }
            self.has_produced_today = True
        else:
            # Drop affection if not fed
            self.affection = max(0, self.affection - 20)
            self.has_produced_today = False

        # Reset fed status
        self.is_fed_today = False
        return product

    def feed(self):
        self.is_fed_today = True

    def to_dict(self):
        return {
            "type": self.animal_type,
            "x": self.x,
            "y": self.y,
            "name": self.name,
            "affection": self.affection,
            "is_petted_today": self.is_petted_today,
            "is_fed_today": self.is_fed_today
        }

    @classmethod
    def from_dict(cls, data):
        a = cls(data["type"], data["x"], data["y"], data["name"])
        a.affection = data.get("affection", 0)
        a.is_petted_today = data.get("is_petted_today", False)
        a.is_fed_today = data.get("is_fed_today", True)
        return a
