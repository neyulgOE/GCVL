"""
Tribal Villager Entity for Stone Age: Dawn of Tribe.
Cư dân bộ tộc nguyên thủy - Hệ thống Dân số Sinh Lão Bệnh Tử & Điều dân RTS.
Permadeath: Chết vĩnh viễn, không thể hồi sinh.
"""

import pygame
import math
import random
from src.settings import TILE_SIZE
from src.core.visual_enhancer import VisualEnhancer

TRIBAL_MALE_NAMES = [
    "Ogg", "Boomer", "Ror", "Korg", "Bram", "Grok", "Vorn", 
    "Toran", "Thak", "Ugor", "Dakar", "Zul"
]

TRIBAL_FEMALE_NAMES = [
    "Tara", "Una", "Naya", "Sula", "Elor", "Miko", "Kaya", 
    "Veda", "Sona", "Lura", "Mira", "Zira"
]

class TribalVillager:
    def __init__(self, villager_id, name=None, gender=None, age_seasons=24, role="worker", x=1600, y=1400):
        self.id = villager_id
        self.gender = gender if gender else random.choice(["male", "female"])
        if name:
            self.name = name
        else:
            self.name = random.choice(TRIBAL_MALE_NAMES if self.gender == "male" else TRIBAL_FEMALE_NAMES)

        self.age_seasons = age_seasons
        self.role = role  # "chieftain", "shaman", "hunter", "gatherer", "worker", "child"
        self._update_life_stage()

        # Vitals & Survival Stats
        self.max_health = 100.0
        self.health = 100.0
        self.hunger = 85.0     # 0..100 (0 = starving to death)
        self.warmth = 90.0     # 0..100 (0 = hypothermia / freezing)
        self.is_injured = False  # Trọng thương từ thú săn
        self.is_sick = False     # Bệnh do rét hoặc nhiễm trùng
        self.is_dead = False     # Permadeath!
        self.death_cause = ""

        # Position & Movement
        self.x = float(x)
        self.y = float(y)
        self.target_x = None
        self.target_y = None
        self.direction = "down"  # "down", "up", "left", "right"
        self.anim_timer = random.uniform(0.0, 0.5)
        self.anim_frame = 0

        # AI Behavior & Work Task
        self.state = "idle"  # "idle", "walk", "gather", "chop", "hunt", "carry_back", "flee", "eat", "rest"
        self.target_object = None   # Target bush/tree/rock/animal
        self.action_timer = 0.0
        self.idle_wander_timer = random.uniform(2.0, 6.0)

        # Inventory / Gùi hàng
        self.carrying = None  # {"id": "wood", "count": 2, "max": 5}

        # RTS Selection
        self.is_selected = False
        self.hitbox = pygame.Rect(int(self.x - 16), int(self.y - 12), 32, 24)

    def _update_life_stage(self):
        """Calculates stage based on age in seasons (1 year = 4 seasons)."""
        if self.age_seasons <= 12:
            self.stage = "child"      # 0 - 3 tuổi tiền sử: Trẻ nhỏ học việc
            if self.role != "child":
                self.role = "child"
        elif self.age_seasons <= 45:
            self.stage = "adult"      # 4 - 11 tuổi: Tráng niên săn bắn
            if self.role == "child":
                self.role = "hunter" if self.gender == "male" else "gatherer"
        else:
            self.stage = "elder"      # 12+ tuổi: Lão niên thông thái

    @property
    def speed(self):
        """Current movement speed based on age and health condition."""
        if self.is_dead:
            return 0.0
        base = 105.0
        if self.stage == "child":
            base = 120.0  # Trẻ nhỏ nhanh nhẹn
        elif self.stage == "elder":
            base = 80.0   # Người già bước đi chậm rãi
        
        # Penalties
        if self.is_injured:
            base *= 0.5   # Bị thương đi tập tễnh
        if self.hunger < 20:
            base *= 0.7   # Đói lả
        if self.warmth < 25:
            base *= 0.75  # Cóng lạnh
        return base

    def command_move_to(self, target_wx, target_wy):
        """Player gives direct order to move to location."""
        if self.is_dead:
            return
        self.target_x = float(target_wx)
        self.target_y = float(target_wy)
        self.target_object = None
        self.state = "walk"

    def command_interact(self, target_type, target_pos, target_obj=None):
        """Player commands villager to gather, chop, hunt, or build."""
        if self.is_dead:
            return
        self.target_x = float(target_pos[0])
        self.target_y = float(target_pos[1])
        self.target_object = target_obj
        
        if target_type == "tree":
            self.state = "chop"
        elif target_type in ["bush", "pebble", "clay", "branch"]:
            self.state = "gather"
        elif target_type in ["animal", "predator"]:
            self.state = "hunt"
        elif target_type == "structure":
            self.state = "build"
        else:
            self.state = "walk"

    def take_damage(self, amount, cause="Dã thú tấn công"):
        """Inflicts damage on villager. Triggers injury or permadeath."""
        if self.is_dead:
            return
        self.health = max(0.0, self.health - amount)
        if self.health <= 40.0:
            self.is_injured = True
        if self.health <= 0.0:
            self.die(cause)

    def die(self, cause="Kiệt sức"):
        """Permadeath: Villager perishes permanently."""
        self.is_dead = True
        self.health = 0.0
        self.death_cause = cause
        self.state = "dead"
        self.target_x = None
        self.target_y = None
        self.is_selected = False

    def update(self, dt, settlement_mgr, obstacles_map=None):
        """Simulation tick for villager."""
        if self.is_dead:
            return

        # 1. Survival Vitals Degradation
        # Hunger drops by ~2.5 per minute of real time
        self.hunger = max(0.0, self.hunger - dt * 0.15)
        if self.hunger <= 0.0:
            self.take_damage(dt * 2.0, "Chết đói")

        # Warmth check: near fire or in shelter?
        is_near_fire = settlement_mgr.is_near_fire(self.x, self.y)
        is_in_shelter = settlement_mgr.is_near_shelter(self.x, self.y)
        if is_near_fire or is_in_shelter:
            self.warmth = min(100.0, self.warmth + dt * 10.0)
            if self.is_sick and random.random() < 0.005:
                self.is_sick = False  # Hơi ấm giúp lành bệnh cảm
        else:
            # Drop warmth faster at night or in winter
            chill_rate = 0.3 if settlement_mgr.is_winter else 0.08
            self.warmth = max(0.0, self.warmth - dt * chill_rate)
            if self.warmth <= 0.0:
                self.is_sick = True
                self.take_damage(dt * 1.5, "Chết rét")

        # Wound bleeding
        if self.is_injured and not self.is_sick:
            self.health = max(10.0, self.health - dt * 0.2)  # Drained down to critical

        # 2. Movement / Pathing Execution
        if self.target_x is not None and self.target_y is not None:
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.hypot(dx, dy)

            # Update orientation
            if abs(dx) > abs(dy):
                self.direction = "right" if dx > 0 else "left"
            else:
                self.direction = "down" if dy > 0 else "up"

            if dist > 8.0:
                step = self.speed * dt
                self.x += (dx / dist) * min(dist, step)
                self.y += (dy / dist) * min(dist, step)
                self.anim_timer += dt
                if self.anim_timer >= 0.15:
                    self.anim_timer = 0.0
                    self.anim_frame = (self.anim_frame + 1) % 4
            else:
                # Arrived at destination
                self.target_x = None
                self.target_y = None
                self._handle_arrival(settlement_mgr)

        elif self.state == "idle":
            # Idle wander near campfire/shelters
            self.idle_wander_timer -= dt
            if self.idle_wander_timer <= 0:
                self.idle_wander_timer = random.uniform(3.0, 7.0)
                # Wander around campfire
                cf_x, cf_y = settlement_mgr.get_campfire_center()
                rx = cf_x + random.randint(-120, 120)
                ry = cf_y + random.randint(-90, 90)
                self.command_move_to(rx, ry)
                self.state = "idle"

        # Update hitbox center
        self.hitbox.center = (int(self.x), int(self.y))

    def _handle_arrival(self, settlement_mgr):
        """Handles action when arriving at target destination."""
        if self.state == "carry_back":
            # Deposit carried items into settlement stockpile
            if self.carrying:
                settlement_mgr.deposit_resources(self.carrying["id"], self.carrying["count"])
                self.carrying = None
            self.state = "idle"

        elif self.state == "hunt" and self.target_object:
            if getattr(self.target_object, "is_dead", False):
                # Carcass harvest
                meat_taken = self.target_object.harvest_meat(15)
                if meat_taken > 0:
                    self.carrying = {"id": "meat", "count": meat_taken}
                    st_x, st_y = settlement_mgr.get_storage_center()
                    self.command_move_to(st_x, st_y)
                    self.state = "carry_back"
                else:
                    self.target_object = None
                    self.state = "idle"
            else:
                # Hunter attacks beast
                dmg = 22.0 if self.role in ["hunter", "chieftain"] else 12.0
                self.target_object.take_damage(dmg, attacker=self)
                # Continue pursuing if beast is still alive
                if not self.target_object.is_dead:
                    self.target_x = self.target_object.x + random.randint(-25, 25)
                    self.target_y = self.target_object.y + random.randint(-25, 25)
                else:
                    # Target just died! Start harvesting on next tick
                    self.target_x = self.target_object.x
                    self.target_y = self.target_object.y

        elif self.state in ["gather", "chop"]:
            # Harvest action
            if self.carrying is None:
                # Collect
                item_id = "wood" if self.state == "chop" else "berries"
                self.carrying = {"id": item_id, "count": 5}
                # Turn back to storage
                st_x, st_y = settlement_mgr.get_storage_center()
                self.command_move_to(st_x, st_y)
                self.state = "carry_back"
            else:
                self.state = "idle"
        else:
            self.state = "idle"

    @classmethod
    def _load_unit_sprites(cls):
        if hasattr(cls, "_unit_sprites"):
            return
        cls._unit_sprites = {}
        import os
        scale_map = {
            # 1. Gatherer / Builder / Worker
            "gatherer_idle": ("assets/stone_age/01_units_villagers/unit_gatherer_builder_01.png", (36, 54)),
            "gatherer_carry_wood": ("assets/stone_age/01_units_villagers/unit_gatherer_builder_02.png", (36, 54)),
            "gatherer_walk": ("assets/stone_age/01_units_villagers/unit_gatherer_builder_03.png", (36, 54)),
            "gatherer_chop": ("assets/stone_age/01_units_villagers/unit_gatherer_builder_04.png", (36, 54)),
            "gatherer_axe_ready": ("assets/stone_age/01_units_villagers/unit_gatherer_builder_05.png", (36, 54)),
            "gatherer_basket": ("assets/stone_age/01_units_villagers/unit_gatherer_builder_06.png", (36, 54)),
            "gatherer_basket_walk": ("assets/stone_age/01_units_villagers/unit_gatherer_builder_08.png", (36, 54)),
            "gatherer_side": ("assets/stone_age/01_units_villagers/unit_gatherer_builder_09.png", (36, 54)),

            # 2. Flint Spear Hunter / Scout
            "spear_hunter_crouch": ("assets/stone_age/01_units_villagers/unit_flint_spear_hunter_01.png", (40, 56)),
            "spear_hunter_aim": ("assets/stone_age/01_units_villagers/unit_flint_spear_hunter_02.png", (40, 56)),
            "spear_hunter_thrust": ("assets/stone_age/01_units_villagers/unit_flint_spear_hunter_03.png", (44, 56)),
            "spear_hunter_ready": ("assets/stone_age/01_units_villagers/unit_flint_spear_hunter_04.png", (42, 56)),
            "spear_hunter_walk": ("assets/stone_age/01_units_villagers/unit_flint_spear_hunter_05.png", (42, 56)),
            "spear_hunter_throw": ("assets/stone_age/01_units_villagers/unit_flint_spear_hunter_07.png", (44, 56)),
            "spear_hunter_side": ("assets/stone_age/01_units_villagers/unit_flint_spear_hunter_09.png", (40, 56)),

            # 3. Mammoth Bone Warrior / Chieftain
            "bone_warrior_guard": ("assets/stone_age/01_units_villagers/unit_mammoth_bone_warrior_01.png", (42, 58)),
            "bone_warrior_shield": ("assets/stone_age/01_units_villagers/unit_mammoth_bone_warrior_02.png", (42, 58)),
            "bone_warrior_walk": ("assets/stone_age/01_units_villagers/unit_mammoth_bone_warrior_03.png", (42, 58)),
            "bone_warrior_strike": ("assets/stone_age/01_units_villagers/unit_mammoth_bone_warrior_04.png", (44, 58)),
            "bone_warrior_swing": ("assets/stone_age/01_units_villagers/unit_mammoth_bone_warrior_06.png", (42, 58)),

            # 4. Tribal Shaman / Mystic
            "shaman_staff": ("assets/stone_age/01_units_villagers/unit_tribal_shaman_01.png", (40, 56)),
            "shaman_chant": ("assets/stone_age/01_units_villagers/unit_tribal_shaman_02.png", (40, 56)),
            "shaman_walk": ("assets/stone_age/01_units_villagers/unit_tribal_shaman_04.png", (40, 56)),
            "shaman_fire_ritual": ("assets/stone_age/01_units_villagers/unit_tribal_shaman_05.png", (44, 58)),
            "shaman_gourd": ("assets/stone_age/01_units_villagers/unit_tribal_shaman_06.png", (40, 56)),
            "shaman_torch": ("assets/stone_age/01_units_villagers/unit_tribal_shaman_07.png", (42, 58)),
        }
        for k, (p, sz) in scale_map.items():
            if os.path.exists(p):
                try:
                    raw = pygame.image.load(p).convert_alpha()
                    bbox = raw.get_bounding_rect()
                    if bbox.width > 0 and bbox.height > 0:
                        raw = raw.subsurface(bbox)
                    cls._unit_sprites[k] = pygame.transform.smoothscale(raw, sz)
                except Exception:
                    cls._unit_sprites[k] = None
            else:
                cls._unit_sprites[k] = None

    def _get_active_sprite(self):
        self._load_unit_sprites()
        spr_key = "gatherer_idle"
        is_moving = (self.target_x is not None)

        if self.role == "hunter":
            if self.state == "hunt":
                spr_key = "spear_hunter_thrust" if self.anim_frame in [1, 3] else "spear_hunter_throw"
            elif is_moving:
                spr_key = "spear_hunter_walk" if self.anim_frame in [0, 2] else "spear_hunter_side"
            else:
                spr_key = "spear_hunter_aim" if self.anim_frame == 0 else "spear_hunter_crouch"
        elif self.role == "shaman":
            if self.state in ["rest", "eat"]:
                spr_key = "shaman_fire_ritual"
            elif is_moving:
                spr_key = "shaman_walk"
            else:
                spr_key = "shaman_staff" if self.anim_frame == 0 else "shaman_gourd"
        elif self.role in ["chieftain", "warrior"]:
            if self.state == "hunt" or (self.target_object and hasattr(self.target_object, "hp")):
                spr_key = "bone_warrior_swing" if self.anim_frame in [1, 3] else "bone_warrior_strike"
            elif is_moving:
                spr_key = "bone_warrior_walk"
            else:
                spr_key = "bone_warrior_guard" if self.anim_frame == 0 else "bone_warrior_shield"
        else: # gatherer / worker / child
            if self.carrying and self.carrying.get("id") == "wood":
                spr_key = "gatherer_carry_wood"
            elif self.state == "chop":
                spr_key = "gatherer_chop" if self.anim_frame in [1, 3] else "gatherer_axe_ready"
            elif self.carrying and self.carrying.get("id") == "berries":
                spr_key = "gatherer_basket_walk" if is_moving else "gatherer_basket"
            elif self.state == "gather":
                spr_key = "gatherer_basket"
            elif is_moving:
                spr_key = "gatherer_walk" if self.anim_frame in [0, 2] else "gatherer_side"
            else:
                spr_key = "gatherer_idle"

        spr = self._unit_sprites.get(spr_key) or self._unit_sprites.get("gatherer_idle")
        if spr and self.stage == "child":
            cw = int(spr.get_width() * 0.72)
            ch = int(spr.get_height() * 0.72)
            return pygame.transform.smoothscale(spr, (cw, ch))
        return spr

    def draw(self, surface, camera, fonts):
        """Draws prehistoric tribal villager, selection ring, status icons, and carrying bag."""
        screen_pos = camera.world_to_screen((self.x, self.y))
        sx, sy = screen_pos

        # Frustum culling
        if not (-64 <= sx <= surface.get_width() + 64 and -64 <= sy <= surface.get_height() + 64):
            return

        font_tiny = fonts.get("tiny", pygame.font.SysFont("dejavusans", 10, bold=True))

        # 1. Selection Decal under feet
        if self.is_selected:
            # Pulsing golden amber RTS selection ring
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 140.0)
            sr_w = int(38 + pulse * 4)
            sr_h = int(18 + pulse * 2)
            sel_surf = pygame.Surface((sr_w + 4, sr_h + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(sel_surf, (255, 190, 40, 220), (2, 2, sr_w, sr_h), 2)
            pygame.draw.ellipse(sel_surf, (255, 230, 120, 75), (4, 4, sr_w - 4, sr_h - 4))
            surface.blit(sel_surf, (sx - (sr_w + 4) // 2, sy + 6 - (sr_h + 4) // 2))

        # 2. Soft Drop Shadow
        VisualEnhancer.draw_drop_shadow(surface, (sx, sy + 6), 34, 14, color=(15, 20, 35, 95))

        # 3. Dead body on ground
        if self.is_dead:
            # Fallen prehistoric human silhouette with skull marker
            pygame.draw.ellipse(surface, (110, 75, 55), (sx - 16, sy - 6, 32, 14))
            pygame.draw.circle(surface, (180, 140, 105), (sx - 12, sy), 6)
            # Bone/Skull tomb marker
            pygame.draw.circle(surface, (240, 235, 220), (sx + 8, sy - 10), 4)
            pygame.draw.line(surface, (200, 195, 185), (sx + 8, sy - 6), (sx + 8, sy - 2), 2)
            # Dead name
            d_lbl = font_tiny.render(f"✝ {self.name} ({self.death_cause})", True, (215, 170, 160))
            surface.blit(d_lbl, (sx - d_lbl.get_width() // 2, sy - 24))
            return

        # 4. Animated Prehistoric Villager Body
        bob = -1 if (self.target_x is not None and self.anim_frame in [0, 2]) else 0
        active_spr = self._get_active_sprite() or self._unit_sprites.get("gatherer_idle")

        if active_spr:
            # Authentic sliced Stone Age pixel-art archetype
            spr = active_spr if self.direction != "left" else pygame.transform.flip(active_spr, True, False)
            sw, sh = spr.get_size()
            surface.blit(spr, (sx - sw // 2, sy - sh + 6 + bob))
        else:
            # Fallback procedural body
            SKIN = (215, 165, 125) if self.gender == "male" else (225, 175, 135)
            HAIR = (40, 28, 20) if self.stage != "elder" else (195, 195, 200)
            PELT = (165, 105, 50) if self.gender == "male" else (145, 115, 75)
            BONE = (245, 240, 230)

            scale = 0.75 if self.stage == "child" else (0.95 if self.stage == "elder" else 1.0)

            # Legs / Leather moccasins
            leg_l = -2 if (self.target_x is not None and self.anim_frame == 0) else 0
            leg_r = 2 if (self.target_x is not None and self.anim_frame == 2) else 0
            pygame.draw.rect(surface, (100, 65, 35), (sx - 6, sy - 6 + bob + leg_l, 4, 10), border_radius=2)
            pygame.draw.rect(surface, (100, 65, 35), (sx + 2, sy - 6 + bob + leg_r, 4, 10), border_radius=2)

            # Fur tunic / grass dress
            tunic_w = int(18 * scale)
            tunic_h = int(20 * scale)
            pygame.draw.rect(surface, PELT, (sx - tunic_w // 2, sy - 24 + bob, tunic_w, tunic_h), border_radius=4)
            # Jagged fur hem
            pygame.draw.line(surface, (90, 50, 25), (sx - tunic_w // 2, sy - 5 + bob), (sx + tunic_w // 2, sy - 5 + bob), 2)

            # Carrying Gùi / Backpack on back
            if self.carrying:
                g_col = (130, 85, 45) if self.carrying["id"] == "wood" else (185, 45, 55)
                pygame.draw.rect(surface, (80, 50, 25), (sx - 12, sy - 22 + bob, 6, 12), border_radius=2)
                pygame.draw.circle(surface, g_col, (sx - 9, sy - 16 + bob), 4)

            # Head & Hair
            head_r = int(7 * scale)
            pygame.draw.circle(surface, SKIN, (sx, sy - 28 + bob), head_r)

            # Facial warpaint streak
            if self.role in ["hunter", "chieftain"]:
                pygame.draw.line(surface, (200, 50, 40), (sx - 4, sy - 27 + bob), (sx - 2, sy - 25 + bob), 2)
                pygame.draw.line(surface, (200, 50, 40), (sx + 2, sy - 27 + bob), (sx + 4, sy - 25 + bob), 2)

            # Hair
            pygame.draw.ellipse(surface, HAIR, (sx - head_r - 2, sy - 36 + bob, (head_r + 2) * 2, 11))
            if self.stage == "elder":
                # White beard
                pygame.draw.polygon(surface, HAIR, [(sx - 3, sy - 24 + bob), (sx + 3, sy - 24 + bob), (sx, sy - 18 + bob)])
            else:
                # Bone hairpin
                pygame.draw.line(surface, BONE, (sx - 7, sy - 34 + bob), (sx + 7, sy - 36 + bob), 2)

            # Weapon / Tool in hand
            if self.role in ["hunter", "chieftain"]:
                pygame.draw.line(surface, (110, 70, 35), (sx + 10, sy - 38 + bob), (sx + 10, sy + bob), 2)
                pygame.draw.polygon(surface, (90, 95, 105), [(sx + 8, sy - 38 + bob), (sx + 12, sy - 38 + bob), (sx + 10, sy - 46 + bob)])
            elif self.role == "shaman":
                pygame.draw.line(surface, (120, 80, 40), (sx + 9, sy - 34 + bob), (sx + 9, sy + bob), 2)
                pygame.draw.circle(surface, (90, 220, 240), (sx + 9, sy - 36 + bob), 3)

        # 5. Overhead Info & Status Alerts (Clean RTS Style)
        # Show Nameplate & Stamina Bar ONLY when unit is selected!
        if self.is_selected:
            name_col = (255, 235, 170)
            role_title = {
                "chieftain": "Tộc Trưởng",
                "shaman": "Thầy Mo",
                "hunter": "Thợ Săn",
                "gatherer": "Hái Lượm",
                "child": "Trẻ Nhỏ"
            }.get(self.role, self.role.capitalize())
            n_lbl = font_tiny.render(f"{self.name} • {role_title}", True, name_col)
            nb_w = n_lbl.get_width() + 8
            nb_surf = pygame.Surface((nb_w, 14), pygame.SRCALPHA)
            pygame.draw.rect(nb_surf, (28, 20, 14, 215), (0, 0, nb_w, 14), border_radius=3)
            pygame.draw.rect(nb_surf, (220, 160, 60, 220), (0, 0, nb_w, 14), 1, border_radius=3)
            surface.blit(nb_surf, (sx - nb_w // 2, sy - 52 + bob))
            surface.blit(n_lbl, (sx - n_lbl.get_width() // 2, sy - 51 + bob))

            # Health bar when selected
            bar_w = 28
            bar_h = 3
            bx = sx - bar_w // 2
            by = sy - 36 + bob
            pygame.draw.rect(surface, (30, 24, 18), (bx - 1, by - 1, bar_w + 2, bar_h + 2), border_radius=1)
            fill_w = int((self.health / self.max_health) * bar_w)
            h_col = (90, 225, 100) if self.health > 50 else ((235, 190, 60) if self.health > 25 else (235, 55, 55))
            pygame.draw.rect(surface, h_col, (bx, by, fill_w, bar_h), border_radius=1)
        elif self.health < 80.0:
            # Discrete pip indicator above head only if injured
            pip_col = (235, 60, 60) if self.health < 40 else (240, 180, 50)
            pygame.draw.circle(surface, (20, 15, 10), (sx, sy - 40 + bob), 3)
            pygame.draw.circle(surface, pip_col, (sx, sy - 40 + bob), 2)

        # Floating Alerts (Hunger, Cold, Injury)
        alerts = []
        if self.hunger < 25:
            alerts.append("🍖")
        if self.warmth < 30:
            alerts.append("❄️")
        if self.is_injured:
            alerts.append("🩸")

        if alerts:
            al_txt = " ".join(alerts)
            al_lbl = font_tiny.render(al_txt, True, (255, 255, 255))
            surface.blit(al_lbl, (sx - al_lbl.get_width() // 2, sy - 63 + bob))
