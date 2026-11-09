"""
Particle System for Green Valley Tales.
Handles tool-use effects (soil dust, wood chips, water splashes),
ambient seasonal particles (leaves, pollen, snow), and UI sparkles.
"""

import pygame
import random
import math
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life",
                 "color", "size", "gravity", "friction", "fade_alpha",
                 "rotation", "rot_speed", "shape")

    def __init__(self, x, y, vx, vy, life, color, size=3,
                 gravity=0, friction=0.98, shape="circle"):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.life = float(life)
        self.max_life = float(life)
        self.color = color
        self.size = float(size)
        self.gravity = float(gravity)
        self.friction = float(friction)
        self.fade_alpha = 255
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-180, 180)
        self.shape = shape

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.vx *= self.friction
        self.vy *= self.friction
        self.life -= dt
        self.rotation += self.rot_speed * dt

        if self.shape in ("petal", "leaf"):
            self.x += math.sin(self.life * 3.5) * 18.0 * dt
        elif self.shape == "firefly":
            self.x += math.cos(self.life * 2.2) * 14.0 * dt
            self.y += math.sin(self.life * 3.1) * 12.0 * dt

        # Smooth fade out
        ratio = max(0, self.life / self.max_life)
        self.fade_alpha = int(255 * ratio * ratio)

        return self.life > 0

    def draw(self, screen, cam_offset_x=0, cam_offset_y=0):
        if self.fade_alpha <= 0:
            return

        sx = int(self.x - cam_offset_x)
        sy = int(self.y - cam_offset_y)

        # Frustum culling
        if sx < -20 or sx > SCREEN_WIDTH + 20 or sy < -20 or sy > SCREEN_HEIGHT + 20:
            return

        sz = max(1, int(self.size * (self.life / self.max_life)))

        if self.shape == "circle":
            surf = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            r, g, b = self.color[:3]
            pygame.draw.circle(surf, (r, g, b, self.fade_alpha), (sz, sz), sz)
            screen.blit(surf, (sx - sz, sy - sz))

        elif self.shape == "square":
            surf = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            r, g, b = self.color[:3]
            pygame.draw.rect(surf, (r, g, b, self.fade_alpha), (0, 0, sz * 2, sz * 2))
            rotated = pygame.transform.rotate(surf, self.rotation)
            screen.blit(rotated, (sx - rotated.get_width() // 2,
                                  sy - rotated.get_height() // 2))

        elif self.shape == "line":
            r, g, b = self.color[:3]
            length = max(2, int(self.size * 1.5))
            end_x = sx + int(math.cos(math.radians(self.rotation)) * length)
            end_y = sy + int(math.sin(math.radians(self.rotation)) * length)
            line_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(line_surf, (r, g, b, self.fade_alpha),
                           (sx, sy), (end_x, end_y), max(1, sz // 2))
            screen.blit(line_surf, (0, 0))

        elif self.shape == "leaf":
            surf = pygame.Surface((sz * 3, sz * 3), pygame.SRCALPHA)
            r, g, b = self.color[:3]
            pygame.draw.ellipse(surf, (r, g, b, self.fade_alpha),
                              (sz // 2, 0, sz * 2, sz))
            rotated = pygame.transform.rotate(surf, self.rotation)
            screen.blit(rotated, (sx - rotated.get_width() // 2,
                                  sy - rotated.get_height() // 2))

        elif self.shape == "petal":
            surf = pygame.Surface((sz * 3, sz * 3), pygame.SRCALPHA)
            r, g, b = self.color[:3]
            pygame.draw.ellipse(surf, (r, g, b, self.fade_alpha), (sz // 2, 0, sz * 2, max(2, int(sz * 1.2))))
            pygame.draw.circle(surf, (255, 255, 255, min(255, self.fade_alpha + 30)), (sz, sz // 2), max(1, sz // 3))
            rotated = pygame.transform.rotate(surf, self.rotation)
            screen.blit(rotated, (sx - rotated.get_width() // 2,
                                  sy - rotated.get_height() // 2))

        elif self.shape == "firefly":
            pulse = max(0.2, 0.6 + 0.4 * math.sin(self.life * 6.0))
            cur_alpha = min(255, int(self.fade_alpha * pulse))
            glow_sz = max(3, sz * 3)
            surf = pygame.Surface((glow_sz * 2, glow_sz * 2), pygame.SRCALPHA)
            r, g, b = self.color[:3]
            # Outer soft aura
            pygame.draw.circle(surf, (r, g, b, max(0, cur_alpha // 4)), (glow_sz, glow_sz), glow_sz)
            # Mid glow
            pygame.draw.circle(surf, (r, g, b, max(0, cur_alpha // 2)), (glow_sz, glow_sz), max(2, glow_sz // 2))
            # Bright yellow-white core
            pygame.draw.circle(surf, (255, 255, 220, cur_alpha), (glow_sz, glow_sz), max(1, glow_sz // 4))
            screen.blit(surf, (sx - glow_sz, sy - glow_sz))


class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.ambient_particles = []  # Separate list for ambient (seasonal)
        self._ambient_timer = 0
        self._max_particles = 200
        self._max_ambient = 50

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
        self.ambient_particles = [p for p in self.ambient_particles if p.update(dt)]

    def draw_world(self, screen, cam_offset_x, cam_offset_y):
        """Draw world-space particles (tool effects, etc.)."""
        for p in self.particles:
            p.draw(screen, cam_offset_x, cam_offset_y)

    def draw_screen(self, screen):
        """Draw screen-space particles (ambient, UI effects)."""
        for p in self.ambient_particles:
            p.draw(screen)

    def update_ambient(self, dt, season_id, weather, is_night=False):
        """Spawn seasonal ambient particles with rich atmospheric effects."""
        self._ambient_timer += dt

        if weather in ("rain", "storm"):
            return  # Let weather system handle rain

        if self._ambient_timer >= 0.25 and len(self.ambient_particles) < self._max_ambient:
            self._ambient_timer = 0

            # Nighttime fireflies (dusk to dawn)
            if is_night:
                self._spawn_firefly()
            elif season_id == "spring":
                # Swaying cherry blossom petals
                self._spawn_petal()
            elif season_id == "summer":
                # Drifting dandelion fluff and sun motes
                self._spawn_mote()
            elif season_id == "fall":
                # Cascading autumn foliage
                self._spawn_leaf()
            elif season_id == "winter":
                # Soft ambient snowflakes
                if weather == "sunny":
                    self._spawn_ambient_snow()

    def _spawn_petal(self):
        x = random.randint(-20, SCREEN_WIDTH + 20)
        y = random.randint(-10, 0)
        vx = random.uniform(8, 28)
        vy = random.uniform(12, 28)
        life = random.uniform(5, 9)
        colors = [(255, 192, 203), (255, 182, 193), (255, 215, 225), (255, 230, 240)]
        self.ambient_particles.append(
            Particle(x, y, vx, vy, life, random.choice(colors),
                     size=random.uniform(3, 5), gravity=1.5, friction=0.998, shape="petal")
        )

    def _spawn_firefly(self):
        x = random.randint(20, SCREEN_WIDTH - 20)
        y = random.randint(40, SCREEN_HEIGHT - 40)
        vx = random.uniform(-6, 6)
        vy = random.uniform(-4, 4)
        life = random.uniform(4, 8)
        colors = [(190, 255, 80), (220, 255, 110), (160, 245, 90)]
        self.ambient_particles.append(
            Particle(x, y, vx, vy, life, random.choice(colors),
                     size=random.uniform(2, 4), gravity=0, friction=0.99, shape="firefly")
        )

    def _spawn_mote(self):
        x = random.randint(-20, SCREEN_WIDTH + 20)
        y = random.randint(-10, 0)
        vx = random.uniform(-10, 10)
        vy = random.uniform(8, 20)
        life = random.uniform(4, 7)
        colors = [(255, 248, 210), (255, 235, 175), (255, 255, 235)]
        self.ambient_particles.append(
            Particle(x, y, vx, vy, life, random.choice(colors),
                     size=random.uniform(2, 3), gravity=1.0, friction=0.995, shape="circle")
        )

    def _spawn_leaf(self):
        x = random.randint(-20, SCREEN_WIDTH + 20)
        y = random.randint(-10, 0)
        vx = random.uniform(-25, 25)
        vy = random.uniform(15, 40)
        life = random.uniform(5, 10)
        colors = [(210, 120, 40), (190, 90, 30), (230, 160, 50),
                  (180, 60, 20), (160, 110, 30)]
        self.ambient_particles.append(
            Particle(x, y, vx, vy, life, random.choice(colors),
                     size=random.uniform(3, 6), gravity=5, friction=0.997, shape="leaf")
        )

    def _spawn_ambient_snow(self):
        x = random.randint(-20, SCREEN_WIDTH + 20)
        y = random.randint(-10, 0)
        vx = random.uniform(-8, 8)
        vy = random.uniform(12, 30)
        life = random.uniform(6, 12)
        self.ambient_particles.append(
            Particle(x, y, vx, vy, life, (240, 245, 255),
                     size=random.uniform(2, 5), gravity=2, friction=0.998, shape="circle")
        )

    # ----- Tool Effect Emitters -----

    def emit_dirt_puff(self, world_x, world_y, count=8):
        """Soil dust when using hoe."""
        if len(self.particles) >= self._max_particles:
            return
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(30, 80)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - random.uniform(20, 50)
            life = random.uniform(0.3, 0.7)
            colors = [(168, 120, 75), (145, 100, 60), (190, 140, 90)]
            self.particles.append(
                Particle(world_x + random.uniform(-8, 8),
                         world_y + random.uniform(-4, 4),
                         vx, vy, life, random.choice(colors),
                         size=random.uniform(2, 5), gravity=120, friction=0.94)
            )

    def emit_wood_chips(self, world_x, world_y, count=6):
        """Wood chips when chopping tree/stump/log."""
        if len(self.particles) >= self._max_particles:
            return
        for _ in range(count):
            angle = random.uniform(-math.pi * 0.8, -math.pi * 0.2)
            speed = random.uniform(50, 120)
            vx = math.cos(angle) * speed + random.uniform(-20, 20)
            vy = math.sin(angle) * speed
            life = random.uniform(0.4, 0.9)
            colors = [(142, 88, 48), (166, 114, 73), (120, 70, 35)]
            self.particles.append(
                Particle(world_x + random.uniform(-6, 6),
                         world_y + random.uniform(-10, 0),
                         vx, vy, life, random.choice(colors),
                         size=random.uniform(2, 5), gravity=200, friction=0.92, shape="square")
            )

    def emit_rock_sparks(self, world_x, world_y, count=5):
        """Sparks when mining rock/boulder."""
        if len(self.particles) >= self._max_particles:
            return
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(60, 140)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 40
            life = random.uniform(0.2, 0.5)
            colors = [(255, 245, 200), (220, 220, 230), (255, 220, 120)]
            self.particles.append(
                Particle(world_x + random.uniform(-4, 4),
                         world_y + random.uniform(-4, 4),
                         vx, vy, life, random.choice(colors),
                         size=random.uniform(1, 3), gravity=250, friction=0.90)
            )

    def emit_water_splash(self, world_x, world_y, count=6):
        """Water splash when watering crops."""
        if len(self.particles) >= self._max_particles:
            return
        for _ in range(count):
            angle = random.uniform(-math.pi, 0)
            speed = random.uniform(20, 60)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 20
            life = random.uniform(0.3, 0.6)
            colors = [(120, 190, 240), (90, 170, 230), (160, 210, 250)]
            self.particles.append(
                Particle(world_x + random.uniform(-10, 10),
                         world_y + random.uniform(-5, 5),
                         vx, vy, life, random.choice(colors),
                         size=random.uniform(2, 4), gravity=150, friction=0.93)
            )

    def emit_harvest_sparkle(self, world_x, world_y, count=10):
        """Sparkle effect when harvesting crops."""
        if len(self.particles) >= self._max_particles:
            return
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(20, 60)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 30
            life = random.uniform(0.4, 0.8)
            colors = [(255, 245, 100), (255, 200, 50), (255, 255, 200)]
            self.particles.append(
                Particle(world_x + random.uniform(-12, 12),
                         world_y + random.uniform(-12, 12),
                         vx, vy, life, random.choice(colors),
                         size=random.uniform(2, 4), gravity=40, friction=0.96)
            )

    def emit_leaf_burst(self, world_x, world_y, count=5):
        """Leaves scatter when cutting weeds/bushes."""
        if len(self.particles) >= self._max_particles:
            return
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(30, 80)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 25
            life = random.uniform(0.5, 1.2)
            colors = [(95, 195, 65), (80, 175, 50), (115, 210, 75)]
            self.particles.append(
                Particle(world_x + random.uniform(-8, 8),
                         world_y + random.uniform(-8, 8),
                         vx, vy, life, random.choice(colors),
                         size=random.uniform(3, 6), gravity=80, friction=0.95, shape="leaf")
            )

    def emit_chimney_smoke(self, world_x, world_y):
        """Gentle rising translucent smoke puffs from chimneys."""
        if len(self.particles) >= self._max_particles:
            return
        vx = random.uniform(6, 18)
        vy = random.uniform(-25, -45)
        life = random.uniform(2.0, 3.6)
        gray = random.randint(210, 240)
        self.particles.append(
            Particle(world_x + random.uniform(-4, 4),
                     world_y + random.uniform(-3, 3),
                     vx, vy, life, (gray, gray, gray),
                     size=random.uniform(5, 10), gravity=-4, friction=0.99)
        )

