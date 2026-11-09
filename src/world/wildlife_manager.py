"""
Wildlife Manager for Stone Age: Dawn of Tribe.
Quản lý Quần thể Sinh thái Động Vật & Dã Thú Tiền Sử:
- Phân bổ động vật khắp các đại địa hình (Voi Ma Mút ở thung lũng, Hổ răng kiếm trong rừng, Sói ở đồi núi)
- Tương tác tầm nhìn với Sương Mù Chiến Tranh (Fog of War)
- Vòng tuần hoàn sinh thái: Sinh sản và di cư theo mùa
"""

import pygame
import random
from src.settings import TILE_SIZE, MAP_COLS, MAP_ROWS
from src.entities.wildlife import PrehistoricBeast

class WildlifeManager:
    def __init__(self):
        self.beasts = []
        self.respawn_timer = 180.0
        self._spawn_initial_wildlife()

    def _spawn_initial_wildlife(self):
        """Populates the open 80x80 prehistoric world with authentic fauna according to biomes."""
        # 1. Woolly Mammoths in Northern Tundra (cols 25..55, rows 6..14)
        self.beasts.append(PrehistoricBeast("mammoth", 35 * TILE_SIZE, 10 * TILE_SIZE))
        self.beasts.append(PrehistoricBeast("mammoth", 45 * TILE_SIZE, 8 * TILE_SIZE))
        self.beasts.append(PrehistoricBeast("mammoth", 52 * TILE_SIZE, 12 * TILE_SIZE))

        # 2. Dire Wolves in Northern Tundra (cols 15..35, rows 4..12)
        self.beasts.append(PrehistoricBeast("dire_wolf", 22 * TILE_SIZE, 8 * TILE_SIZE))
        self.beasts.append(PrehistoricBeast("dire_wolf", 28 * TILE_SIZE, 6 * TILE_SIZE))
        self.beasts.append(PrehistoricBeast("dire_wolf", 32 * TILE_SIZE, 5 * TILE_SIZE))

        # 3. Cave Bears in Western Megalithic Highlands (cols 4..18, rows 25..45)
        self.beasts.append(PrehistoricBeast("cave_bear", 8 * TILE_SIZE, 28 * TILE_SIZE))
        self.beasts.append(PrehistoricBeast("cave_bear", 14 * TILE_SIZE, 42 * TILE_SIZE))

        # 4. Sabertooth Tigers lurking in Eastern Primeval Forest (cols 60..74, rows 22..48)
        self.beasts.append(PrehistoricBeast("sabertooth", 62 * TILE_SIZE, 26 * TILE_SIZE))
        self.beasts.append(PrehistoricBeast("sabertooth", 68 * TILE_SIZE, 40 * TILE_SIZE))

        # 5. Ancient Bisons roaming Steppe Grasslands (cols 26..38, rows 22..35)
        self.beasts.append(PrehistoricBeast("ancient_bison", 28 * TILE_SIZE, 25 * TILE_SIZE))
        self.beasts.append(PrehistoricBeast("ancient_bison", 32 * TILE_SIZE, 28 * TILE_SIZE))
        self.beasts.append(PrehistoricBeast("ancient_bison", 34 * TILE_SIZE, 22 * TILE_SIZE))

        # 6. Giant Deer in Forest Glades (cols 58..68, rows 35..50)
        self.beasts.append(PrehistoricBeast("giant_deer", 60 * TILE_SIZE, 36 * TILE_SIZE))
        self.beasts.append(PrehistoricBeast("giant_deer", 65 * TILE_SIZE, 45 * TILE_SIZE))

        # 7. Wild Boars foraging near River Shrubland (cols 44..48, rows 25..45)
        self.beasts.append(PrehistoricBeast("wild_boar", 46 * TILE_SIZE, 28 * TILE_SIZE))
        self.beasts.append(PrehistoricBeast("wild_boar", 47 * TILE_SIZE, 42 * TILE_SIZE))

        # 8. Marsh Crocodilians along Southern Mangrove Swamp & Delta (cols 42..56, rows 66..76)
        self.beasts.append(PrehistoricBeast("marsh_crocodilian", 46 * TILE_SIZE, 68 * TILE_SIZE))
        self.beasts.append(PrehistoricBeast("marsh_crocodilian", 52 * TILE_SIZE, 74 * TILE_SIZE))

    def update(self, dt, villagers, player, settlement_mgr):
        """Simulation tick for all beasts."""
        for b in self.beasts:
            b.update(dt, villagers, player, settlement_mgr)

        # Periodic ecological respawn for hunted game
        self.respawn_timer -= dt
        if self.respawn_timer <= 0:
            self.respawn_timer = 240.0
            alive_count = len([b for b in self.beasts if not b.is_dead])
            if alive_count < 8:
                # Spawn new wild herd animal
                spawn_type = random.choice(["ancient_bison", "giant_deer", "dire_wolf"])
                sx = random.randint(10, MAP_COLS - 6) * TILE_SIZE
                sy = random.randint(5, MAP_ROWS - 6) * TILE_SIZE
                self.beasts.append(PrehistoricBeast(spawn_type, sx, sy))

    def get_beast_at_world(self, wx, wy, radius=48):
        """Finds beast clicked by player."""
        for b in self.beasts:
            if not b.is_dead and b.hitbox.collidepoint(wx, wy):
                return b
        return None

    def draw(self, surface, camera, fonts, fog_of_war=None):
        """
        Draws beasts. In AOE style, moving wild animals in unexplored or fogged
        zones are hidden from view unless within active vision!
        """
        # Sort by Y coordinate
        sorted_beasts = sorted(self.beasts, key=lambda b: b.y)

        for b in sorted_beasts:
            # Check fog of war visibility
            if fog_of_war and fog_of_war.is_enabled:
                col = int(b.x // TILE_SIZE)
                row = int(b.y // TILE_SIZE)
                # Dead carcasses are visible if tile was explored
                if b.is_dead:
                    if not fog_of_war.is_tile_explored(col, row):
                        continue
                else:
                    # Living moving beasts require active visibility (STATE_VISIBLE)
                    if not fog_of_war.is_tile_visible(col, row):
                        continue

            b.draw(surface, camera, fonts)
