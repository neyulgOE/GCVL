"""
Weather and Dynamic Lighting System for Stone Age: Primeval World.
Handles Weather (Sunny, Rain, Storm, Snow), Day/Night ambient lighting mask,
soft radial cutouts for lanterns, fireflies with proper glow halos,
morning mist, rain splash pools, and smooth screen-shake during storms.
"""

import pygame
import random
import math
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, PALETTE
from src.core.visual_enhancer import VisualEnhancer

class WeatherSystem:
    def __init__(self):
        self.weather = "sunny"
        self.rain_particles = []
        self.snow_particles = []
        self.fireflies = []
        self.rain_splashes = []
        self.lightning_timer = 0
        self.is_flashing = False
        self.flash_alpha = 0
        self.screen_shake_x = 0
        self.screen_shake_y = 0
        self._shake_timer = 0

        # Mist system
        self.mist_alpha = 0
        self.mist_target_alpha = 0

        # Pre-rendered radial gradient cache for light sources
        self._light_cache = {}

        self._init_particles()

    def _init_particles(self):
        # Fireflies with glow properties
        for _ in range(30):
            self.fireflies.append({
                "x": random.randint(0, SCREEN_WIDTH),
                "y": random.randint(0, SCREEN_HEIGHT),
                "vx": random.uniform(-0.4, 0.4),
                "vy": random.uniform(-0.4, 0.4),
                "phase": random.uniform(0, math.pi * 2),
                "glow_size": random.uniform(4, 8),
                "pulse_speed": random.uniform(2.0, 4.0)
            })

        # Rain drops with depth layers (parallax)
        for _ in range(120):
            layer = random.choice([0, 0, 0, 1, 1, 2])  # More foreground drops
            speed_mult = 1.0 + layer * 0.3
            alpha_mult = 1.0 - layer * 0.25
            self.rain_particles.append({
                "x": random.randint(-50, SCREEN_WIDTH + 50),
                "y": random.randint(-20, SCREEN_HEIGHT),
                "speed": random.uniform(12, 18) * speed_mult,
                "len": random.randint(6, 14) + layer * 3,
                "layer": layer,
                "alpha": int(200 * alpha_mult),
                "wind_offset": random.uniform(-2, -4)
            })

        # Snow particles with variable sizes
        for _ in range(60):
            self.snow_particles.append({
                "x": random.randint(-20, SCREEN_WIDTH + 20),
                "y": random.randint(-20, SCREEN_HEIGHT),
                "speed": random.uniform(20, 45),
                "size": random.uniform(1.5, 4.0),
                "wobble_phase": random.uniform(0, math.pi * 2),
                "wobble_speed": random.uniform(1.5, 3.5),
                "wobble_amp": random.uniform(15, 40),
                "alpha": random.randint(140, 240)
            })

    def _get_light_gradient(self, radius, max_alpha):
        """Pre-render and cache radial gradient for light sources."""
        key = (radius, max_alpha)
        if key not in self._light_cache:
            size = radius * 2
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            # Multi-ring smooth falloff
            steps = max(6, radius // 4)
            for i in range(steps, 0, -1):
                curr_r = int(radius * (i / steps))
                falloff = (1.0 - (i / steps)) ** 1.8
                sub_a = int(max_alpha * falloff)
                pygame.draw.circle(surf, (0, 0, 0, sub_a), (radius, radius), curr_r)
            self._light_cache[key] = surf
        return self._light_cache[key]

    def pick_next_day_weather(self, season_id):
        rand = random.random()
        if season_id == "winter":
            self.weather = "snow" if rand < 0.6 else "sunny"
        elif season_id == "summer":
            if rand < 0.15:
                self.weather = "storm"
            elif rand < 0.35:
                self.weather = "rain"
            else:
                self.weather = "sunny"
        else:
            self.weather = "rain" if rand < 0.3 else "sunny"

    def update(self, dt):
        # Rain Particles with wind
        if self.weather in ["rain", "storm"]:
            wind = -3.5 if self.weather == "storm" else -2.0
            for p in self.rain_particles:
                p["y"] += p["speed"] * dt * 60.0
                p["x"] += (wind + p["wind_offset"]) * dt * 60.0
                if p["y"] > SCREEN_HEIGHT:
                    p["y"] = random.randint(-30, -5)
                    p["x"] = random.randint(-50, SCREEN_WIDTH + 100)
                    # Spawn splash at bottom
                    if random.random() < 0.3:
                        self.rain_splashes.append({
                            "x": p["x"], "y": SCREEN_HEIGHT - random.randint(10, 60),
                            "timer": 0.15, "size": random.uniform(2, 5)
                        })

        # Rain splashes decay
        self.rain_splashes = [s for s in self.rain_splashes
                             if self._update_splash(s, dt)]

        # Lightning with smooth flash
        if self.weather == "storm":
            self.lightning_timer -= dt
            if self.lightning_timer <= 0:
                self.lightning_timer = random.uniform(4.0, 10.0)
                self.flash_alpha = 220
                self._shake_timer = 0.2
            else:
                self.is_flashing = False
        
        # Smooth flash decay
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - dt * 600)

        # Screen shake decay
        if self._shake_timer > 0:
            self._shake_timer -= dt
            intensity = self._shake_timer * 8
            self.screen_shake_x = random.uniform(-intensity, intensity)
            self.screen_shake_y = random.uniform(-intensity, intensity)
        else:
            self.screen_shake_x = 0
            self.screen_shake_y = 0

        # Snow particles with wobble
        if self.weather == "snow":
            for p in self.snow_particles:
                p["wobble_phase"] += p["wobble_speed"] * dt
                p["y"] += p["speed"] * dt
                p["x"] += math.sin(p["wobble_phase"]) * p["wobble_amp"] * dt
                if p["y"] > SCREEN_HEIGHT + 10:
                    p["y"] = random.randint(-20, -5)
                    p["x"] = random.randint(-20, SCREEN_WIDTH + 20)

        # Fireflies with organic movement
        for ff in self.fireflies:
            ff["phase"] += ff["pulse_speed"] * dt
            ff["x"] += ff["vx"] + math.sin(ff["phase"]) * 0.4
            ff["y"] += ff["vy"] + math.cos(ff["phase"] * 0.7) * 0.3
            # Wrap around
            if ff["x"] < -10: ff["x"] = SCREEN_WIDTH + 10
            if ff["x"] > SCREEN_WIDTH + 10: ff["x"] = -10
            if ff["y"] < -10: ff["y"] = SCREEN_HEIGHT + 10
            if ff["y"] > SCREEN_HEIGHT + 10: ff["y"] = -10

        # Morning mist calculation (done in get_time_color_and_alpha)
        if self.mist_alpha != self.mist_target_alpha:
            diff = self.mist_target_alpha - self.mist_alpha
            self.mist_alpha += diff * dt * 2.0
            if abs(diff) < 1:
                self.mist_alpha = self.mist_target_alpha

    def _update_splash(self, splash, dt):
        splash["timer"] -= dt
        return splash["timer"] > 0

    def get_time_color_and_alpha(self, hour, minute):
        """Calculate ambient color overlay and opacity based on time of day."""
        total_minutes = hour * 60 + minute

        if 360 <= total_minutes < 480:
            # Dawn (06:00 -> 08:00): soft gentle peach-amber morning transition
            progress = (total_minutes - 360) / 120.0
            alpha = int(40 * (1.0 - progress))
            color = (255, 225, 200)
            self.mist_target_alpha = int(35 * (1.0 - progress))
        elif 480 <= total_minutes < 1050:
            # Full Daytime (08:00 -> 17:30): Clear natural daylight
            alpha = 0
            color = (0, 0, 0)
            self.mist_target_alpha = 0
        elif 1050 <= total_minutes < 1140:
            # Sunset (17:30 -> 19:00): Warm amber dusk
            progress = (total_minutes - 1050) / 90.0
            alpha = int(80 * progress)
            # Smooth sunset gradient: warm amber to dusky violet
            r = int(240 - 165 * progress)
            g = int(145 - 95 * progress)
            b = int(75 - 8 * progress)
            color = (r, g, b)
            self.mist_target_alpha = 0
        elif 1140 <= total_minutes <= 1440:
            # Night (19:00 -> 24:00): Rich midnight indigo (never dirty gray)
            progress = min(1.0, (total_minutes - 1140) / 90.0)
            alpha = int(75 + 75 * progress)
            color = (24, 30, 72)
            self.mist_target_alpha = 0
        else:
            # Midnight to Dawn (00:00 -> 06:00): Deep starry navy
            alpha = 150
            color = (22, 28, 68)
            self.mist_target_alpha = 0

        # Weather modifier (gloomy rain or storm)
        if self.weather in ["rain", "storm"]:
            alpha = max(alpha, 55)
            color = (30, 40, 60) if alpha <= 55 else color

        return color, alpha

    def draw_lighting(self, screen, hour, minute, light_sources):
        """
        Draw dynamic day/night lighting mask with cached radial gradients.
        """
        color, alpha = self.get_time_color_and_alpha(hour, minute)

        # Lightning flash (smooth fade)
        if self.flash_alpha > 5:
            flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, int(self.flash_alpha)))
            screen.blit(flash_surf, (0, 0))

        # If full daytime and sunny, maybe only draw morning mist
        if alpha <= 5:
            self._draw_mist(screen)
            return

        # Create darkness overlay
        dark_mask = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dark_mask.fill((*color, alpha))

        # Punch smooth light holes using cached gradients
        for (pos_x, pos_y), radius in light_sources:
            r = int(radius)
            light_cutout = self._get_light_gradient(r, alpha)
            rect = light_cutout.get_rect(center=(int(pos_x), int(pos_y)))
            dark_mask.blit(light_cutout, rect, special_flags=pygame.BLEND_RGBA_SUB)

        screen.blit(dark_mask, (0, 0))

        # Add warm amber halo on natural light sources at dusk and night
        if alpha >= 35:
            for (pos_x, pos_y), radius in light_sources:
                glow_r = int(radius * 0.75)
                glow_surf = VisualEnhancer.get_radial_glow(glow_r, (48, 36, 12))
                rect = glow_surf.get_rect(center=(int(pos_x), int(pos_y)))
                screen.blit(glow_surf, rect, special_flags=pygame.BLEND_RGBA_ADD)

        # Draw fireflies with proper glow halos at night
        if alpha >= 50:
            self._draw_fireflies(screen, alpha)

        # Morning mist
        self._draw_mist(screen)

    def _draw_fireflies(self, screen, darkness_alpha):
        """Draw dancing fireflies with soft glow halos."""
        intensity = min(1.0, darkness_alpha / 100.0)
        for ff in self.fireflies:
            glow_intensity = (math.sin(ff["phase"]) + 1.0) / 2.0
            if glow_intensity < 0.15:
                continue

            x, y = int(ff["x"]), int(ff["y"])
            glow_r = int(ff["glow_size"] * glow_intensity * 2.5)

            # Outer glow halo
            if glow_r > 2:
                glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                glow_alpha = int(50 * glow_intensity * intensity)
                for ring in range(glow_r, 0, -2):
                    ring_alpha = int(glow_alpha * (1.0 - ring / glow_r))
                    pygame.draw.circle(glow_surf, (200, 240, 80, ring_alpha),
                                     (glow_r, glow_r), ring)
                screen.blit(glow_surf, (x - glow_r, y - glow_r))

            # Core bright dot
            core_alpha = int(200 * glow_intensity * intensity)
            core_size = max(1, int(2 * glow_intensity))
            core_surf = pygame.Surface((core_size * 2 + 2, core_size * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(core_surf, (230, 255, 110, core_alpha),
                             (core_size + 1, core_size + 1), core_size)
            screen.blit(core_surf, (x - core_size - 1, y - core_size - 1))

    def _draw_mist(self, screen):
        """Draw subtle morning mist overlay."""
        if self.mist_alpha < 2:
            return
        mist_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        mist_surf.fill((220, 230, 240, int(self.mist_alpha)))
        screen.blit(mist_surf, (0, 0))

    def draw_weather(self, screen):
        """Draw rain streaks with splash effects, or volumetric snow."""
        if self.weather in ["rain", "storm"]:
            rain_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

            for p in self.rain_particles:
                alpha = p["alpha"]
                x1, y1 = int(p["x"]), int(p["y"])
                x2 = int(p["x"] + p["wind_offset"])
                y2 = int(p["y"] + p["len"])
                width = 1 if p["layer"] > 0 else 2
                pygame.draw.line(rain_surf, (170, 210, 245, alpha),
                               (x1, y1), (x2, y2), width)

            screen.blit(rain_surf, (0, 0))

            # Rain splash ripples
            for s in self.rain_splashes:
                ratio = s["timer"] / 0.15
                splash_alpha = int(160 * ratio)
                splash_r = int(s["size"] * (1.0 - ratio) * 3 + 1)
                if splash_alpha > 0 and splash_r > 0:
                    splash_surf = pygame.Surface((splash_r * 2 + 4, splash_r * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(splash_surf, (200, 225, 250, splash_alpha),
                                     (splash_r + 2, splash_r + 2), splash_r, 1)
                    screen.blit(splash_surf, (int(s["x"]) - splash_r - 2,
                                             int(s["y"]) - splash_r - 2))

        elif self.weather == "snow":
            snow_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for p in self.snow_particles:
                x, y = int(p["x"]), int(p["y"])
                sz = max(1, int(p["size"]))
                pygame.draw.circle(snow_surf, (245, 248, 255, p["alpha"]),
                                 (x, y), sz)
                # Subtle inner highlight
                if sz >= 2:
                    pygame.draw.circle(snow_surf, (255, 255, 255, min(255, p["alpha"] + 30)),
                                     (x - 1, y - 1), max(1, sz - 1))
            screen.blit(snow_surf, (0, 0))
