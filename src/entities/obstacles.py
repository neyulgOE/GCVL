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
        """Returns True if this resource can be gathered directly by hand or any tool."""
        return self.obs_type in ["branch", "pebble", "wild_bush", "weeds", "prop_bone", "prop_mushroom"]

    def hit(self, tool_type="hands"):
        """
        Attempt to gather or damage obstacle.
        Returns:
            drops: list of dicts (items dropped) if destroyed, None if still alive or invalid tool.
            hit_success: bool (whether the action was valid).
        """
        valid = False
        damage = 1

        # 1. Bare hands or any tool can collect ground foraging resources
        if self.obs_type == "wild_bush":
            if self.growth_stage == "depleted":
                return None, False  # Bush is currently bare and regenerating
            valid = True
            damage = 1
        elif self.obs_type in ["branch", "pebble", "prop_bone", "prop_mushroom"]:
            valid = True
            damage = 1
        elif self.obs_type == "weeds":
            # Scythe or bare hands
            valid = True
            damage = 1
        elif self.obs_type == "clay_patch":
            # Digging stick, hoe, or pickaxe
            if tool_type in ["hoe", "pickaxe", "digging_stick", "stone_hoe", "bronze_hoe"]:
                valid = True
        elif self.obs_type in ["rock_small", "boulder", "copper_rock"]:
            if tool_type in ["pickaxe", "stone_pick", "bronze_pick"]:
                valid = True
        elif self.obs_type in ["tree_stump", "log", "tree", "tree_steppe", "tree_forest", "tree_tundra", "tree_swamp"]:
            if tool_type in ["axe", "primitive_axe", "polished_axe", "bronze_axe"]:
                valid = True

        if not valid:
            return None, False

        self.health -= damage
        self.shake_timer = 0.28

        if self.health <= 0:
            return self.get_drops(), True
        return None, True

    def get_drops(self):
        drops = []
        # --- Prehistoric Ground Foraging ---
        if self.obs_type == "branch":
            qty = random.randint(2, 3)
            drops.append({"id": "branch", "type": "material", "name": "Cành Cây Khô (Branch)", "price": 2, "qty": qty})
        elif self.obs_type == "pebble":
            drops.append({"id": "pebble", "type": "material", "name": "Đá Cuội (Pebble)", "price": 3, "qty": 2})
            if random.random() < 0.35:
                drops.append({"id": "flint", "type": "material", "name": "Đá Lửa (Flint)", "price": 8, "qty": 1})
        elif self.obs_type == "wild_bush":
            drops.append({"id": "berries", "type": "food", "name": "Quả Dâu Rừng (Wild Berries)", "price": 8, "stamina_restore": 15, "qty": random.randint(2, 4)})
            drops.append({"id": "fiber", "type": "material", "name": "Sợi Cỏ Dại (Fiber)", "price": 4, "qty": 2})
            if random.random() < 0.25:
                drops.append({"id": "wild_roots", "type": "seed", "name": "Hạt Củ Dại Đầm Lầy", "qty": 1})
        elif self.obs_type == "clay_patch":
            drops.append({"id": "clay", "type": "material", "name": "Đất Sét Bờ Suối (Clay)", "price": 6, "qty": random.randint(2, 3)})
        elif self.obs_type == "copper_rock":
            drops.append({"id": "pebble", "type": "material", "name": "Đá Cuội", "price": 3, "qty": 3})
            drops.append({"id": "copper_ore", "type": "material", "name": "Quặng Đồng Nguyên Sinh", "price": 25, "qty": random.randint(1, 2)})
            if random.random() < 0.15:
                drops.append({"id": "ancient_amber", "type": "rare", "name": "Hổ Phách Cổ Đại", "price": 280, "qty": 1, "is_rare": True})

        # --- Standard Clearing ---
        elif self.obs_type == "weeds":
            drops.append({"id": "fiber", "type": "material", "name": "Sợi Cỏ (Fiber)", "price": 4, "qty": 2})
        elif self.obs_type == "rock_small":
            drops.append({"id": "pebble", "type": "material", "name": "Đá Cuội (Pebble)", "price": 3, "qty": 2})
            if random.random() < 0.25:
                drops.append({"id": "flint", "type": "material", "name": "Đá Lửa (Flint)", "price": 8, "qty": 1})
        elif self.obs_type == "boulder":
            drops.append({"id": "pebble", "type": "material", "name": "Đá Cuội (Pebble)", "price": 3, "qty": 5})
            drops.append({"id": "flint", "type": "material", "name": "Đá Lửa (Flint)", "price": 8, "qty": 2})
            if random.random() < 0.30:
                drops.append({"id": "copper_ore", "type": "material", "name": "Quặng Đồng", "price": 25, "qty": 1})
        elif self.obs_type in ["tree_stump", "log"]:
            drops.append({"id": "wood", "type": "material", "name": "Gỗ (Wood)", "price": 8, "qty": 4})
            drops.append({"id": "branch", "type": "material", "name": "Cành Cây Khô", "price": 2, "qty": 2})
        elif self.obs_type == "prop_bone":
            drops.append({"id": "bone", "type": "material", "name": "Xương Thú Cổ Đại (Mammoth Bone)", "price": 15, "qty": random.randint(2, 4)})
            if random.random() < 0.25:
                drops.append({"id": "ivory", "type": "rare", "name": "Ngà Voi Ma Mút (Mammoth Ivory)", "price": 120, "qty": 1, "is_rare": True})
        elif self.obs_type == "prop_mushroom":
            drops.append({"id": "mushroom", "type": "food", "name": "Nấm Rừng Cổ Đại (Ancient Mushroom)", "price": 10, "stamina_restore": 20, "qty": random.randint(2, 3)})
            if random.random() < 0.35:
                drops.append({"id": "herbs", "type": "material", "name": "Dược Thảo Rừng (Medicinal Herbs)", "price": 15, "qty": 1})
        elif self.obs_type in ["tree", "tree_steppe", "tree_forest", "tree_tundra", "tree_swamp"]:
            drops.append({"id": "wood", "type": "material", "name": "Gỗ (Wood)", "price": 8, "qty": 7})
            drops.append({"id": "branch", "type": "material", "name": "Cành Cây Khô", "price": 2, "qty": 4})
            if random.random() < 0.20:
                drops.append({"id": "ancient_amber", "type": "rare", "name": "Hổ Phách Cổ Đại", "price": 280, "qty": 1, "is_rare": True})

        return drops

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
