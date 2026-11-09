"""
Fishing and River Aquatic System for Green Valley Tales.
Includes Bobber casting, bite alert, interactive tension-bar minigame,
species determination based on season/weather/time, and crab pots.
"""

import pygame
import random
import math
from src.settings import FISH_DATA, PALETTE, TILE_SIZE

class FishingSystem:
    # States
    IDLE = "idle"
    CASTING = "casting"
    WAITING = "waiting"
    BITE = "bite"
    MINIGAME = "minigame"
    CAUGHT = "caught"

    def __init__(self):
        self.state = self.IDLE
        self.bobber_world_pos = (0, 0)
        self.target_water_tile = None
        self.bite_timer = 0.0
        self.bite_window = 1.8  # seconds to react
        
        # Minigame parameters
        self.bar_y = 120.0       # player green bar position (0 to 200)
        self.bar_height = 48.0   # height of green capture zone
        self.fish_y = 100.0      # fish target position
        self.fish_target_y = 100.0
        self.fish_speed = 1.5
        self.fish_timer = 0.0
        self.catch_progress = 40.0  # 0 to 100%
        self.current_fish_id = "carp"
        self.caught_fish_item = None
        
        # Minigame dimensions
        self.mg_width = 32
        self.mg_height = 200

    def start_fishing(self, target_tile_world_pos):
        self.state = self.CASTING
        self.bobber_world_pos = target_tile_world_pos
        self.bite_timer = random.uniform(2.5, 6.0)

    def cancel(self):
        self.state = self.IDLE
        self.caught_fish_item = None

    def trigger_bite(self):
        self.state = self.BITE
        self.bite_timer = self.bite_window

    def start_minigame(self, season_id, weather, hour):
        self.state = self.MINIGAME
        self.bar_y = 100.0
        self.fish_y = 100.0
        self.fish_target_y = 100.0
        self.catch_progress = 35.0
        self.current_fish_id = self._roll_fish(season_id, weather, hour)
        diff = FISH_DATA[self.current_fish_id]["difficulty"]
        self.fish_speed = 1.4 * diff
        self.bar_height = max(34.0, 52.0 - diff * 5.0)

    def _roll_fish(self, season_id, weather, hour):
        candidates = []
        is_raining = (weather in ["rain", "storm"])
        is_night = (hour >= 19 or hour < 6)
        is_morning = (6 <= hour <= 10)

        for fid, data in FISH_DATA.items():
            if season_id not in data["seasons"]:
                continue
            t = data["time"]
            if t == "all":
                candidates.append(fid)
            elif t == "morning" and is_morning:
                candidates.append(fid)
            elif t == "day" and not is_night:
                candidates.append(fid)
            elif t == "night_or_rain" and (is_night or is_raining):
                candidates.append(fid)

        if not candidates:
            return "paleo_carp" if "paleo_carp" in FISH_DATA else (list(FISH_DATA.keys())[0] if FISH_DATA else "paleo_carp")
        # Golden prehistoric fish rare chance (8%)
        if "golden_paleo_fish" in candidates and random.random() < 0.08:
            return "golden_paleo_fish"
        if "golden_trout" in candidates and random.random() < 0.08:
            return "golden_trout"
        candidates = [c for c in candidates if c != "golden_trout"]
        return random.choice(candidates) if candidates else "carp"

    def update(self, dt, holding_space_or_mouse, season_id, weather, hour):
        """
        Updates fishing logic.
        Returns:
            event: "PLAY_BITE_SFX", "PLAY_SUCCESS_SFX", or None
        """
        event = None

        if self.state == self.CASTING:
            self.state = self.WAITING

        elif self.state == self.WAITING:
            self.bite_timer -= dt
            if self.bite_timer <= 0:
                self.trigger_bite()
                event = "PLAY_BITE_SFX"

        elif self.state == self.BITE:
            self.bite_timer -= dt
            if self.bite_timer <= 0:
                # Fish escaped before reeling
                self.state = self.IDLE

        elif self.state == self.MINIGAME:
            # 1. Update Green Bar (Player control)
            if holding_space_or_mouse:
                self.bar_y -= 140.0 * dt  # move up
            else:
                self.bar_y += 110.0 * dt  # fall down by gravity
            self.bar_y = max(0.0, min(self.bar_y, self.mg_height - self.bar_height))

            # 2. Update Fish AI target
            self.fish_timer -= dt
            if self.fish_timer <= 0:
                self.fish_timer = random.uniform(0.6, 1.8)
                self.fish_target_y = random.uniform(10, self.mg_height - 10)

            # Move fish smoothly towards target
            dy = self.fish_target_y - self.fish_y
            self.fish_y += dy * self.fish_speed * dt * 2.0
            self.fish_y = max(4.0, min(self.fish_y, self.mg_height - 4.0))

            # 3. Check if fish is inside green capture bar
            fish_in_bar = (self.bar_y <= self.fish_y <= self.bar_y + self.bar_height)
            if fish_in_bar:
                self.catch_progress += 28.0 * dt
                if self.catch_progress >= 100.0:
                    # Success!
                    self.state = self.CAUGHT
                    fish_info = FISH_DATA[self.current_fish_id]
                    self.caught_fish_item = {
                        "type": "fish",
                        "id": self.current_fish_id,
                        "name": fish_info["name"].split(" (")[0],
                        "price": fish_info["price"]
                    }
                    event = "PLAY_SUCCESS_SFX"
            else:
                self.catch_progress -= 18.0 * dt
                if self.catch_progress <= 0:
                    # Failed, fish escaped
                    self.state = self.IDLE

        return event

    def draw_bobber(self, screen, camera):
        """Draw the animated bobber floating in the river."""
        if self.state in [self.CASTING, self.WAITING, self.BITE, self.MINIGAME]:
            screen_x, screen_y = camera.apply_pos(self.bobber_world_pos)
            
            # Water ripples
            pygame.draw.circle(screen, (180, 220, 255, 120), (screen_x, screen_y), 8, 1)
            
            # Bobber (Red/White)
            bob_offset = math.sin(pygame.time.get_ticks() * 0.006) * 2
            by = screen_y + int(bob_offset)
            pygame.draw.circle(screen, (230, 50, 40), (screen_x, by - 2), 4)
            pygame.draw.circle(screen, (245, 245, 250), (screen_x, by + 1), 3)

            # "!" alert on bite
            if self.state == self.BITE:
                # Exclamation mark bubble
                pygame.draw.rect(screen, (255, 230, 80), (screen_x - 8, by - 28, 16, 18), border_radius=4)
                pygame.draw.rect(screen, (120, 70, 20), (screen_x - 8, by - 28, 16, 18), 1, border_radius=4)
                font = pygame.font.SysFont("dejavusans", 14, bold=True)
                txt = font.render("!", True, (180, 40, 20))
                screen.blit(txt, (screen_x - 3, by - 27))

    def draw_minigame(self, screen, x, y):
        """Draw the interactive fishing mini-game HUD bar."""
        if self.state != self.MINIGAME:
            return

        # Background panel
        panel_rect = pygame.Rect(x - 8, y - 24, self.mg_width + 42, self.mg_height + 40)
        pygame.draw.rect(screen, PALETTE["ui_panel"], panel_rect, border_radius=6)
        pygame.draw.rect(screen, PALETTE["ui_border"], panel_rect, 3, border_radius=6)

        # Main track
        track_rect = pygame.Rect(x, y, self.mg_width, self.mg_height)
        pygame.draw.rect(screen, (40, 70, 95), track_rect, border_radius=3)
        pygame.draw.rect(screen, (20, 35, 50), track_rect, 2, border_radius=3)

        # Player green capture bar
        bar_rect = pygame.Rect(x + 2, y + int(self.bar_y), self.mg_width - 4, int(self.bar_height))
        pygame.draw.rect(screen, (75, 210, 85), bar_rect, border_radius=3)
        pygame.draw.rect(screen, (135, 245, 145), bar_rect, 2, border_radius=3)

        # Fish icon inside track
        fish_screen_y = y + int(self.fish_y)
        pygame.draw.ellipse(screen, (245, 130, 40), (x + 8, fish_screen_y - 6, 16, 12))
        pygame.draw.polygon(screen, (200, 80, 20), [(x + 20, fish_screen_y), (x + 26, fish_screen_y - 4), (x + 26, fish_screen_y + 4)])

        # Progress bar (Vertical on right)
        prog_x = x + self.mg_width + 8
        prog_w = 12
        pygame.draw.rect(screen, (60, 50, 40), (prog_x, y, prog_w, self.mg_height), border_radius=2)
        fill_h = int((self.catch_progress / 100.0) * self.mg_height)
        if fill_h > 0:
            fill_rect = pygame.Rect(prog_x, y + self.mg_height - fill_h, prog_w, fill_h)
            col = (230, 80, 50) if self.catch_progress < 30 else (90, 215, 90)
            pygame.draw.rect(screen, col, fill_rect, border_radius=2)
        pygame.draw.rect(screen, (30, 25, 20), (prog_x, y, prog_w, self.mg_height), 1, border_radius=2)
