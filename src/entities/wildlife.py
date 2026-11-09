"""
Prehistoric Wildlife & Apex Predator System for Stone Age: Dawn of Tribe.
Hệ thống Động Vật Hoang Dã & Dã Thú Săn Mồi Tiền Sử:
- Voi Ma Mút Khổng Lồ (Mammoth): Thần thú vĩ đại, cần nhiều thợ săn phối hợp.
- Bò Rừng Cổ Đại (Ancient Bison): Động vật bầy đàn, húc càn khi bị tấn công.
- Hổ Răng Kiếm (Sabertooth Tiger): Thú săn mồi nguy hiểm, rình rập vồ cắn dân làng.
- Bầy Sói Xám (Dire Wolves): Đi theo bầy, sủa gọi bầy và vây ráp mục tiêu.
- Hươu Khổng Lồ (Giant Deer): Nhanh nhẹn, hoảng sợ tháo chạy khi bị tiếp cận.
"""

import pygame
import math
import random
from src.settings import TILE_SIZE
from src.core.visual_enhancer import VisualEnhancer

BEAST_CONFIGS = {
    "mammoth": {
        "name": "Voi Ma Mút Khổng Lồ",
        "max_hp": 450.0,
        "speed": 55.0,
        "damage": 35.0,
        "is_predator": False,
        "retaliates": True,
        "harvest": {"meat": 150, "pelt": 12, "tusk": 4},
        "color": (155, 105, 55),
        "size": (96, 72)
    },
    "ancient_bison": {
        "name": "Bò Rừng Cổ Đại",
        "max_hp": 180.0,
        "speed": 75.0,
        "damage": 22.0,
        "is_predator": False,
        "retaliates": True,
        "harvest": {"meat": 60, "pelt": 6},
        "color": (115, 68, 38),
        "size": (64, 48)
    },
    "sabertooth": {
        "name": "Hổ Răng Kiếm",
        "max_hp": 120.0,
        "speed": 115.0,
        "damage": 28.0,
        "is_predator": True,
        "retaliates": True,
        "harvest": {"meat": 40, "pelt": 5},
        "color": (210, 140, 50),
        "size": (56, 40)
    },
    "dire_wolf": {
        "name": "Chó Sói Xám",
        "max_hp": 75.0,
        "speed": 125.0,
        "damage": 18.0,
        "is_predator": True,
        "retaliates": True,
        "harvest": {"meat": 25, "pelt": 3},
        "color": (120, 125, 130),
        "size": (44, 32)
    },
    "giant_deer": {
        "name": "Hươu Sừng Tấm Khổng Lồ",
        "max_hp": 85.0,
        "speed": 110.0,
        "damage": 5.0,
        "is_predator": False,
        "retaliates": False,
        "harvest": {"meat": 35, "pelt": 4},
        "color": (160, 110, 65),
        "size": (52, 44)
    },
    "cave_bear": {
        "name": "Gấu Hang Khổng Lồ",
        "max_hp": 260.0,
        "speed": 65.0,
        "damage": 32.0,
        "is_predator": True,
        "retaliates": True,
        "harvest": {"meat": 90, "pelt": 8},
        "color": (95, 65, 40),
        "size": (72, 54)
    },
    "wild_boar": {
        "name": "Lợn Lòi Tiền Sử",
        "max_hp": 90.0,
        "speed": 95.0,
        "damage": 14.0,
        "is_predator": False,
        "retaliates": True,
        "harvest": {"meat": 35, "pelt": 3},
        "color": (120, 90, 60),
        "size": (48, 36)
    },
    "marsh_crocodilian": {
        "name": "Cá Sấu Đầm Lầy Cổ Đại",
        "max_hp": 160.0,
        "speed": 70.0,
        "damage": 25.0,
        "is_predator": True,
        "retaliates": True,
        "harvest": {"meat": 50, "pelt": 5},
        "color": (70, 85, 55),
        "size": (74, 38)
    },
    "fish_shoal": {
        "name": "Đàn Cá Sông",
        "max_hp": 20.0,
        "speed": 45.0,
        "damage": 0.0,
        "is_predator": False,
        "retaliates": False,
        "harvest": {"meat": 15, "pelt": 0},
        "color": (80, 140, 160),
        "size": (36, 24)
    }
}

class PrehistoricBeast:
    def __init__(self, beast_type, x, y):
        self.type = beast_type
        self.cfg = BEAST_CONFIGS.get(beast_type, BEAST_CONFIGS["ancient_bison"])
        self.name = self.cfg["name"]

        self.x = float(x)
        self.y = float(y)
        self.max_hp = self.cfg["max_hp"]
        self.hp = self.max_hp
        self.speed = self.cfg["speed"]
        self.damage = self.cfg["damage"]
        self.is_predator = self.cfg["is_predator"]

        self.state = "roam"  # "roam", "stalk", "chase", "attack", "flee", "dead"
        self.target = None   # Target villager or player
        self.target_x = self.x
        self.target_y = self.y
        self.direction = "right"
        self.anim_timer = random.uniform(0.0, 0.5)
        self.anim_frame = 0

        self.roam_timer = random.uniform(3.0, 8.0)
        self.attack_cooldown = 0.0
        self.is_dead = False
        self.meat_left = self.cfg["harvest"]["meat"]
        self.pelt_left = self.cfg["harvest"].get("pelt", 0)

        bw, bh = self.cfg["size"]
        self.hitbox = pygame.Rect(int(self.x - bw // 2), int(self.y - bh // 2), bw, bh)

        self._sprite = self._get_tactical_sprite(self.type)

    def _get_current_sprite(self):
        """Returns dynamic state-based authentic Stone Age megafauna sprite."""
        try:
            from src.core.assets import AssetManager
            am = AssetManager.get()
            ts = am.textures
        except Exception:
            ts = {}

        if self.type == "mammoth":
            if self.state in ["roam", "chase"]:
                return ts.get("mammoth_walk") or self._sprite
            return ts.get("mammoth_idle") or self._sprite
        elif self.type == "sabertooth":
            if self.state in ["chase", "attack"]:
                return ts.get("sabertooth_pounce") or self._sprite
            elif self.state == "stalk":
                return ts.get("sabertooth_stalk") or self._sprite
            return ts.get("sabertooth_idle") or self._sprite
        elif self.type == "ancient_bison":
            if self.state in ["flee", "chase"]:
                return ts.get("bison_charge") or self._sprite
            return ts.get("bison_graze") or self._sprite
        elif self.type == "cave_bear":
            if self.state in ["attack", "alert"]:
                return ts.get("cave_bear_stand") or self._sprite
            return ts.get("cave_bear_walk") or self._sprite
        elif self.type == "dire_wolf":
            if self.state in ["alert", "howl"]:
                return ts.get("dire_wolf_howl") or self._sprite
            return ts.get("dire_wolf_run") or self._sprite
        elif self.type == "wild_boar":
            return ts.get("wild_boar") or self._sprite
        elif self.type == "marsh_crocodilian":
            return ts.get("marsh_crocodile") or self._sprite
        elif self.type == "fish_shoal":
            return ts.get("fish_shoal") or self._sprite

        return self._sprite

    @classmethod
    def _get_tactical_sprite(cls, beast_type):
        try:
            from src.core.assets import AssetManager
            am = AssetManager.get()
            tex_map = {
                "mammoth": "mammoth_walk",
                "ancient_bison": "bison_charge",
                "sabertooth": "sabertooth_pounce",
                "dire_wolf": "dire_wolf_run",
                "cave_bear": "cave_bear_walk",
                "wild_boar": "wild_boar",
                "marsh_crocodilian": "marsh_crocodile",
                "fish_shoal": "fish_shoal",
            }
            if beast_type in tex_map and tex_map[beast_type] in am.textures:
                return am.textures[tex_map[beast_type]]
        except Exception:
            pass

        if not hasattr(cls, "_cached_sprites"):
            cls._cached_sprites = {}
            import os
            # Mapping beast ids to primary high-res sliced sprites from assets/wildlife/
            paths = {
                "mammoth": ("assets/stone_age/02_megafauna_wildlife/wildlife_mammoth_and_smilodon_01.png", (96, 76)),
                "ancient_bison": ("assets/stone_age/02_megafauna_wildlife/wildlife_steppe_bison_01.png", (78, 62)),
                "sabertooth": ("assets/stone_age/02_megafauna_wildlife/wildlife_mammoth_and_smilodon_06.png", (68, 50)),
                "dire_wolf": ("assets/stone_age/02_megafauna_wildlife/wildlife_cavebear_and_direwolf_04.png", (56, 42)),
                "cave_bear": ("assets/stone_age/02_megafauna_wildlife/wildlife_cavebear_and_direwolf_01.png", (76, 58)),
                "wild_boar": ("assets/stone_age/02_megafauna_wildlife/wildlife_wild_boar_01.png", (52, 38)),
                "marsh_crocodilian": ("assets/stone_age/02_megafauna_wildlife/wildlife_crocodilian_and_fish_01.png", (80, 42)),
                "fish_shoal": ("assets/stone_age/02_megafauna_wildlife/wildlife_crocodilian_and_fish_04.png", (40, 26)),
                "giant_deer": ("assets/tactical_extracted/deer.png", (52, 44)),
            }
            # Fallbacks
            fallbacks = {
                "mammoth": "assets/wildlife/mammoth_walk.png",
                "ancient_bison": "assets/wildlife/bison_charge.png",
                "sabertooth": "assets/wildlife/sabertooth_pounce.png",
            }
            for b_id, (p, sz) in paths.items():
                target_p = p if os.path.exists(p) else fallbacks.get(b_id, "")
                if target_p and os.path.exists(target_p):
                    try:
                        raw = pygame.image.load(target_p).convert_alpha()
                        cls._cached_sprites[b_id] = pygame.transform.smoothscale(raw, sz)
                    except Exception:
                        cls._cached_sprites[b_id] = None
                else:
                    cls._cached_sprites[b_id] = None
        return cls._cached_sprites.get(beast_type)

    def take_damage(self, amount, attacker=None):
        """Beast takes hit from hunter spear/arrow."""
        if self.is_dead:
            return
        self.hp = max(0.0, self.hp - amount)

        # Retaliate or flee
        if self.cfg["retaliates"] and attacker:
            self.target = attacker
            self.state = "chase"
        elif not self.cfg["retaliates"]:
            self.state = "flee"
            if attacker:
                # Run in opposite direction
                dx = self.x - attacker.x
                dy = self.y - attacker.y
                dist = math.hypot(dx, dy) or 1.0
                self.target_x = self.x + (dx / dist) * 350
                self.target_y = self.y + (dy / dist) * 350

        if self.hp <= 0:
            self.die()

    def die(self):
        """Beast falls, becoming a rich resource carcass."""
        self.is_dead = True
        self.hp = 0.0
        self.state = "dead"
        self.target = None

    def update(self, dt, beasts=None, *args, **kwargs):
        """Simulation tick for wild beast AI in natural prehistoric ecosystem."""
        if self.is_dead:
            return

        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

        # 1. PREDATOR STALKING & CHASE LOGIC
        if self.is_predator and self.state in ["roam", "stalk"]:
            potential_prey = []
            if beasts:
                for b in beasts:
                    if b is not self and not b.is_dead and not b.is_predator and b.type != "mammoth":
                        dist = math.hypot(self.x - b.x, self.y - b.y)
                        if dist <= 240.0:
                            potential_prey.append((dist, b))
            if potential_prey:
                potential_prey.sort(key=lambda item: item[0])
                self.target = potential_prey[0][1]
                self.state = "chase"

        # 2. HERBIVORE FLEE FROM NEARBY PREDATOR
        if not self.is_predator and self.state == "roam" and beasts:
            for b in beasts:
                if b is not self and not b.is_dead and b.is_predator:
                    p_dist = math.hypot(self.x - b.x, self.y - b.y)
                    if p_dist <= 180.0:
                        self.state = "flee"
                        dx = self.x - b.x
                        dy = self.y - b.y
                        dist = math.hypot(dx, dy) or 1.0
                        self.target_x = max(128.0, min(80 * 64.0 - 128.0, self.x + (dx / dist) * 280.0))
                        self.target_y = max(128.0, min(80 * 64.0 - 128.0, self.y + (dy / dist) * 280.0))
                        break

        # 3. CHASE STATE
        if self.state == "chase" and self.target:
            target_dead = getattr(self.target, "is_dead", False)
            if target_dead:
                self.target = None
                self.state = "roam"
                return

            dx = self.target.x - self.x
            dy = self.target.y - self.y
            dist = math.hypot(dx, dy)

            # Prey panics and flees
            if hasattr(self.target, "state") and self.target.state != "flee" and not getattr(self.target, "is_predator", False):
                self.target.state = "flee"
                t_dx = self.target.x - self.x
                t_dy = self.target.y - self.y
                t_dist = math.hypot(t_dx, t_dy) or 1.0
                self.target.target_x = max(128.0, min(80 * 64.0 - 128.0, self.target.x + (t_dx / t_dist) * 260.0))
                self.target.target_y = max(128.0, min(80 * 64.0 - 128.0, self.target.y + (t_dy / t_dist) * 260.0))

            if dist > 38.0:
                step = self.speed * 1.25 * dt
                self.x += (dx / dist) * step
                self.y += (dy / dist) * step
                self.direction = "right" if dx > 0 else "left"
            else:
                # Attack reach
                if self.attack_cooldown <= 0:
                    self.attack_cooldown = 1.4
                    if hasattr(self.target, "take_damage"):
                        self.target.take_damage(self.damage, attacker=self)

        # 4. ROAM STATE
        elif self.state == "roam":
            self.roam_timer -= dt
            if self.roam_timer <= 0:
                self.roam_timer = random.uniform(3.0, 7.0)
                new_x = self.x + random.randint(-160, 160)
                new_y = self.y + random.randint(-120, 120)
                self.target_x = max(128.0, min(80 * 64.0 - 128.0, new_x))
                self.target_y = max(128.0, min(80 * 64.0 - 128.0, new_y))

            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.hypot(dx, dy)
            if dist > 10.0:
                step = self.speed * dt
                self.x += (dx / dist) * step
                self.y += (dy / dist) * step
                self.direction = "right" if dx > 0 else "left"

        # 5. FLEE STATE
        elif self.state == "flee":
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.hypot(dx, dy)
            if dist > 15.0:
                step = self.speed * 1.35 * dt
                self.x += (dx / dist) * step
                self.y += (dy / dist) * step
                self.direction = "right" if dx > 0 else "left"
            else:
                self.state = "roam"

        # Clamp within world bounds & update hitbox
        self.x = max(64.0, min(80 * 64.0 - 64.0, self.x))
        self.y = max(64.0, min(80 * 64.0 - 64.0, self.y))
        bw, bh = self.cfg["size"]
        self.hitbox.center = (int(self.x), int(self.y))

    def harvest_meat(self, amount=10):
        """Harvests meat from fallen carcass."""
        if not self.is_dead:
            return 0
        taken = min(self.meat_left, amount)
        self.meat_left -= taken
        return taken

    def draw(self, surface, camera, fonts):
        """Renders authentic prehistoric beast silhouette, tusks, spots, horns."""
        screen_pos = camera.world_to_screen((self.x, self.y))
        sx, sy = screen_pos

        bw, bh = self.cfg["size"]
        # Frustum culling
        if not (-bw <= sx <= surface.get_width() + bw and -bh <= sy <= surface.get_height() + bh):
            return

        font_tiny = fonts.get("tiny", pygame.font.SysFont("dejavusans", 10, bold=True))

        # 1. Soft Drop shadow
        sh_w = bw + 8
        sh_h = bh // 2 + 4
        VisualEnhancer.draw_drop_shadow(surface, (sx, sy + bh // 4 + sh_h // 2), sh_w, sh_h, color=(15, 20, 35, 95))

        # 2. Carcass if dead
        if self.is_dead:
            pygame.draw.ellipse(surface, (90, 60, 40), (sx - bw // 2, sy - bh // 4, bw, bh // 2))
            # Meat bones visible
            for bx in range(sx - 15, sx + 20, 10):
                pygame.draw.line(surface, (240, 235, 220), (bx, sy - 8), (bx + 4, sy + 2), 2)
            # Carcass label
            lbl = font_tiny.render(f"🥩 Xác {self.name} ({self.meat_left} thịt)", True, (255, 215, 170))
            surface.blit(lbl, (sx - lbl.get_width() // 2, sy - bh // 2 - 16))
            return

        # 3. Living Beast Rendering
        curr_spr = self._get_current_sprite() or self._sprite
        if curr_spr:
            bob = int(math.sin(self.anim_timer * 6.0) * 2.0) if self.state in ["chase", "stalk", "roam"] else 0
            spr = curr_spr if self.direction == "right" else pygame.transform.flip(curr_spr, True, False)
            surface.blit(spr, (sx - spr.get_width() // 2, sy - spr.get_height() // 2 + bob))

            # Health bar above head (if injured)
            if self.hp < self.max_hp:
                bar_w = 40
                bar_h = 4
                pct = max(0.0, self.hp / self.max_hp)
                pygame.draw.rect(surface, (40, 20, 20), (sx - bar_w // 2, sy - bh // 2 - 8, bar_w, bar_h))
                pygame.draw.rect(surface, (220, 50, 50), (sx - bar_w // 2, sy - bh // 2 - 8, int(bar_w * pct), bar_h))

            # Beast Name label & Alert Icon
            n_col = (255, 120, 100) if self.is_predator else (240, 230, 210)
            prefix = "⚠️ " if self.state in ["chase", "stalk"] else ""
            n_lbl = font_tiny.render(f"{prefix}{self.name}", True, n_col)
            surface.blit(n_lbl, (sx - n_lbl.get_width() // 2, sy - bh // 2 - 20))
            return

        col = self.cfg["color"]

        if self.type == "mammoth":
            # Giant Mammoth
            # Body & fur hump
            pygame.draw.ellipse(surface, col, (sx - 44, sy - 34, 88, 54))
            pygame.draw.ellipse(surface, (120, 75, 40), (sx - 38, sy - 44, 52, 34))  # Hump
            # 4 Heavy pillar legs
            pygame.draw.rect(surface, (110, 70, 35), (sx - 36, sy + 8, 14, 22), border_radius=3)
            pygame.draw.rect(surface, (110, 70, 35), (sx - 16, sy + 8, 14, 22), border_radius=3)
            pygame.draw.rect(surface, (110, 70, 35), (sx + 8, sy + 8, 14, 22), border_radius=3)
            pygame.draw.rect(surface, (110, 70, 35), (sx + 24, sy + 8, 14, 22), border_radius=3)
            # Head & Trunk
            hx = sx + 32 if self.direction == "right" else sx - 32
            pygame.draw.circle(surface, col, (hx, sy - 14), 22)
            # Trunk curving down
            tx = hx + 16 if self.direction == "right" else hx - 16
            pygame.draw.arc(surface, col, (tx - 10, sy - 10, 24, 38), 0, math.pi, 6)
            # Giant Curved Ivory Tusks
            t_col = (245, 240, 225)
            if self.direction == "right":
                pygame.draw.arc(surface, t_col, (hx + 4, sy - 18, 36, 42), -0.5, math.pi * 0.8, 4)
            else:
                pygame.draw.arc(surface, t_col, (hx - 40, sy - 18, 36, 42), 0.2, math.pi * 1.5, 4)

        elif self.type == "ancient_bison":
            # Ancient Bison
            pygame.draw.ellipse(surface, col, (sx - 28, sy - 20, 56, 36))
            pygame.draw.ellipse(surface, (80, 45, 25), (sx - 24, sy - 28, 34, 26))  # Heavy shoulder hump
            # Legs
            pygame.draw.rect(surface, (80, 45, 25), (sx - 20, sy + 8, 8, 14), border_radius=2)
            pygame.draw.rect(surface, (80, 45, 25), (sx + 12, sy + 8, 8, 14), border_radius=2)
            # Curved Horns
            hx = sx + 22 if self.direction == "right" else sx - 22
            pygame.draw.circle(surface, col, (hx, sy - 10), 14)
            pygame.draw.arc(surface, (230, 225, 215), (hx - 8, sy - 24, 18, 20), 0, math.pi, 3)

        elif self.type == "sabertooth":
            # Sabertooth Tiger
            pygame.draw.ellipse(surface, col, (sx - 24, sy - 16, 48, 28))
            # Leopard/tiger dark spots
            pygame.draw.circle(surface, (130, 80, 30), (sx - 12, sy - 8), 3)
            pygame.draw.circle(surface, (130, 80, 30), (sx + 4, sy - 6), 3)
            pygame.draw.circle(surface, (130, 80, 30), (sx - 2, sy - 12), 2)
            # Muscular paws
            pygame.draw.rect(surface, (160, 100, 35), (sx - 18, sy + 6, 7, 12), border_radius=2)
            pygame.draw.rect(surface, (160, 100, 35), (sx + 11, sy + 6, 7, 12), border_radius=2)
            # Head with Glowing predator eyes & Giant Saber Canines
            hx = sx + 20 if self.direction == "right" else sx - 20
            pygame.draw.circle(surface, col, (hx, sy - 10), 12)
            pygame.draw.circle(surface, (255, 230, 80), (hx + 2 if self.direction == "right" else hx - 2, sy - 11), 2)  # Glowing eye
            # Iconic White Saber Teeth protruding down
            tx = hx + 5 if self.direction == "right" else hx - 5
            pygame.draw.polygon(surface, (250, 245, 235), [(tx, sy - 4), (tx + 3, sy - 4), (tx + 1, sy + 7)])

        elif self.type == "dire_wolf":
            # Dire Wolf
            pygame.draw.ellipse(surface, col, (sx - 18, sy - 12, 36, 22))
            pygame.draw.rect(surface, (80, 85, 90), (sx - 14, sy + 4, 5, 10), border_radius=2)
            pygame.draw.rect(surface, (80, 85, 90), (sx + 9, sy + 4, 5, 10), border_radius=2)
            hx = sx + 14 if self.direction == "right" else sx - 14
            pygame.draw.circle(surface, col, (hx, sy - 8), 9)
            pygame.draw.polygon(surface, (70, 75, 80), [(hx - 4, sy - 14), (hx - 1, sy - 19), (hx + 2, sy - 14)])  # Pointy ear

        else:
            # Giant Deer
            pygame.draw.ellipse(surface, col, (sx - 20, sy - 14, 40, 26))
            pygame.draw.line(surface, col, (sx - 12, sy + 6), (sx - 12, sy + 18), 3)
            pygame.draw.line(surface, col, (sx + 10, sy + 6), (sx + 10, sy + 18), 3)
            hx = sx + 18 if self.direction == "right" else sx - 18
            pygame.draw.circle(surface, col, (hx, sy - 14), 10)
            # Giant Spreading Antlers
            pygame.draw.line(surface, (220, 210, 195), (hx, sy - 18), (hx + 8, sy - 32), 3)
            pygame.draw.line(surface, (220, 210, 195), (hx, sy - 18), (hx - 8, sy - 30), 2)

        # 4. Overhead Name & Health Bar (When damaged or targeted)
        if self.hp < self.max_hp:
            bar_w = 40
            bar_h = 5
            bx = sx - bar_w // 2
            by = sy - bh // 2 - 12
            pygame.draw.rect(surface, (40, 25, 20), (bx - 1, by - 1, bar_w + 2, bar_h + 2), border_radius=2)
            fill_w = int((self.hp / self.max_hp) * bar_w)
            h_col = (235, 60, 50) if self.is_predator else (80, 210, 90)
            pygame.draw.rect(surface, h_col, (bx, by, fill_w, bar_h), border_radius=1)

        # Name label
        n_col = (255, 120, 100) if self.is_predator else (240, 230, 210)
        n_lbl = font_tiny.render(self.name, True, n_col)
        surface.blit(n_lbl, (sx - n_lbl.get_width() // 2, sy - bh // 2 - 24))
