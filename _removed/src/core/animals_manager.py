"""
Manager for Livestock and Pets in Green Valley Tales.
Handles spawning, roaming AI, feeding, petting, and product collection.
"""

import pygame
from src.settings import TILE_SIZE
from src.entities.animals import Animal

class AnimalsManager:
    def __init__(self, barn_col=14, barn_row=6):
        self.barn_col = barn_col
        self.barn_row = barn_row
        self.home_x = (barn_col + 1.5) * TILE_SIZE
        self.home_y = (barn_row + 2.0) * TILE_SIZE
        
        self.animals = []
        self.ground_products = []  # Eggs/Milk dropped in pasture to pick up
        
        # Starter animals
        self._init_starter_animals()

    def _init_starter_animals(self):
        # In the Stone Age, players start without domesticated animals.
        # Animals can be tamed and penned after crafting an Animal Corral.
        self.animals = []

    def add_animal(self, animal_type):
        name = "Gà Rừng" if animal_type in ["chicken", "wild_chicken"] else "Bò Rừng"
        a = Animal(animal_type, self.home_x, self.home_y + 10, name=name)
        self.animals.append(a)

    def update(self, dt):
        for animal in self.animals:
            animal.update(dt, self.home_x, self.home_y, wander_radius=120)

    def advance_day(self):
        """Called overnight when player sleeps."""
        for animal in self.animals:
            prod = animal.next_day()
            if prod:
                # Spawn product item on ground near animal
                self.ground_products.append({
                    "item": prod,
                    "x": animal.x + 4,
                    "y": animal.y + 10
                })

    def interact_with_nearby_animal(self, player_x, player_y, max_dist=70):
        """
        Check if player is close enough to pet an animal or collect product.
        Returns:
            msg: str or None
            sfx: str or None
        """
        # 1. Check picking up ground products (Eggs / Milk)
        for i, gp in enumerate(self.ground_products):
            dist = ((player_x - gp["x"]) ** 2 + (player_y - gp["y"]) ** 2) ** 0.5
            if dist < max_dist:
                prod = gp["item"]
                self.ground_products.pop(i)
                return prod, "pickup"

        # 2. Check petting animals
        for animal in self.animals:
            dist = ((player_x - animal.x) ** 2 + (player_y - animal.y) ** 2) ** 0.5
            if dist < max_dist:
                success = animal.pet()
                animal.feed()  # petting also feeds them if outside
                sfx = "cluck" if animal.animal_type == "chicken" else "moo"
                if success:
                    return f"Bạn đã vuốt ve {animal.name}! (Tim: {animal.hearts}/5)", sfx
                else:
                    return f"{animal.name} đang vui vẻ gặm cỏ!", sfx

        return None, None

    def to_dict(self):
        return {
            "animals": [a.to_dict() for a in self.animals],
            "ground_products": self.ground_products
        }

    def from_dict(self, data):
        self.animals = [Animal.from_dict(d) for d in data.get("animals", [])]
        self.ground_products = data.get("ground_products", [])
