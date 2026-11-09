"""
Primitive Structures Manager for Stone Age: Dawn of Tribe.
Coordinates placed prehistoric base structures:
- Campfire (Lửa Trại) - Level 0..2 (Cooking, warmth, night glow)
- Shelter (Chòi Trú Ẩn) - Level 1..4 (Leaf Lean-to -> Fur Tent -> Mud Hut -> Tribal Longhouse)
- Clay Kiln (Lò Nung Đất Sét) - Level 0..1 (Pottery firing, smelting)
- Tribal Totem (Trụ Totem Tổ Tiên) - Level 0..1 (Sacred blessing, crop growth boost)
"""

import pygame
import math
import random
from src.settings import TILE_SIZE, PALETTE
from src.core.visual_enhancer import VisualEnhancer

class PrimitiveStructures:
    def __init__(self):
        # Structure levels (0 = unbuilt/foundation, 1+ = built & upgrade tiers)
        self.campfire_level = 1   # Starts at Level 1 (Lửa Trại Bộ Tộc đang cháy rực)
        self.shelter_level = 1    # Starts at Level 1 (Hang Đá Cội Nguồn / Chòi Trú Ẩn)
        self.kiln_level = 1       # Flintknapping workshop
        self.totem_level = 1      # Megalithic Totem Shrine
        self.storage_level = 1    # Resource cache
        self.grass_tents = 2      # Tribal grass huts
        self.pelt_tipis = 2       # Mammoth hide tipis

        # Tile Coordinates on 80x80 Prehistoric RTS World (Central Basin around (40, 38))
        self.campfire_pos = (40, 38)   # Central camp gathering fire (Tier 2 Basin)
        self.shelter_pos = (38, 30)    # Ancestral Rock Shelter (Tier 3 Hillside Terrace)
        self.kiln_pos = (37, 40)       # Flintknapping workshop
        self.totem_pos = (35, 42)      # Megalithic Shrine
        self.storage_pos = (42, 35)    # Meat Smoker & Drying Rack (Buffer zone)
        self.gate_pos = (45, 40)       # Stake & Mammoth Bone Beast Barrier (Buffer zone boundary)
        self.grass_tent_spots = [(35, 36), (37, 38)]
        self.pelt_tipi_spots = [(42, 36), (43, 38)]

        # Animation state & floating ember particle simulation
        self.anim_timer = 0.0
        self.total_time = 0.0
        self.flame_frame = 0
        self.embers = [
            {
                "x": random.uniform(-12, 12),
                "y": random.uniform(-6, 6),
                "vx": random.uniform(-6, 6),
                "vy": random.uniform(-28, -16),
                "life": random.uniform(0.1, 1.4),
                "max_life": 1.4
            }
            for _ in range(16)
        ]

        # Texture Cache for high-res tactical sprites
        self._sprites = {}
        self._load_tactical_sprites()

    def _load_tactical_sprites(self):
        """Loads and prepares high-res prehistoric sprites from tactical concept art."""
        paths = {
            "cave_hearth": ("assets/stone_age/03_buildings_structures/01_ancestral_rock_shelter.png", (240, 200)),
            "grass_tent": ("assets/stone_age/03_buildings_structures/single_thatch_hut.png", (120, 110)),
            "pelt_tipi": ("assets/stone_age/03_buildings_structures/single_pelt_tipi.png", (100, 120)),
            "campfire": ("assets/tactical_extracted/campfire.png", (56, 68)),
            "flint_workshop": ("assets/stone_age/03_buildings_structures/03_flintknapping_workshop.png", (160, 133)),
            "meat_smoker": ("assets/stone_age/03_buildings_structures/04_meat_smoking_and_tanning_racks.png", (160, 133)),
            "megalithic_shrine": ("assets/stone_age/03_buildings_structures/05_megalithic_totem_shrine.png", (160, 133)),
            "palisade_gate": ("assets/stone_age/03_buildings_structures/06_palisade_gate_and_watchtower.png", (180, 150)),
        }
        import os
        for k, (p, sz) in paths.items():
            if os.path.exists(p):
                try:
                    raw = pygame.image.load(p).convert_alpha()
                    self._sprites[k] = pygame.transform.smoothscale(raw, sz)
                except Exception:
                    self._sprites[k] = None

    def upgrade_structure(self, target_name, new_level):
        """Upgrades or constructs a structure to specified level."""
        if target_name == "campfire":
            self.campfire_level = max(self.campfire_level, new_level)
        elif target_name == "shelter":
            self.shelter_level = max(self.shelter_level, new_level)
        elif target_name == "clay_kiln":
            self.kiln_level = max(self.kiln_level, new_level)
        elif target_name == "totem":
            self.totem_level = max(self.totem_level, new_level)
        elif target_name == "storage":
            self.storage_level = max(self.storage_level, new_level)
        elif target_name == "grass_tent":
            self.grass_tents += 1
        elif target_name == "pelt_tipi":
            self.pelt_tipis += 1

    def is_near_campfire(self, world_x, world_y, distance_threshold=96):
        """Checks if world coordinates are within interaction reach of Campfire."""
        if self.campfire_level <= 0:
            return False
        cx = self.campfire_pos[0] * TILE_SIZE + TILE_SIZE // 2
        cy = self.campfire_pos[1] * TILE_SIZE + TILE_SIZE // 2
        dist = math.hypot(world_x - cx, world_y - cy)
        return dist <= distance_threshold

    def is_near_shelter(self, world_x, world_y, distance_threshold=128):
        """Checks if world coordinates are within sleep reach of Shelter."""
        sx = self.shelter_pos[0] * TILE_SIZE + TILE_SIZE
        sy = self.shelter_pos[1] * TILE_SIZE + TILE_SIZE
        dist = math.hypot(world_x - sx, world_y - sy)
        return dist <= distance_threshold

    def update(self, dt):
        """Updates structure animations (fire flicker, drifting smoke & embers, totem hum)."""
        self.total_time += dt
        self.anim_timer += dt
        if self.anim_timer >= 0.12:
            self.anim_timer = 0.0
            self.flame_frame = (self.flame_frame + 1) % 4

        # Simulate floating glowing campfire ember particles
        for e in self.embers:
            e["life"] -= dt
            e["y"] += e["vy"] * dt
            # gentle wind sway
            e["x"] += e["vx"] * dt + math.sin(self.total_time * 4.0 + e["y"] * 0.1) * 0.4
            if e["life"] <= 0:
                e["life"] = random.uniform(0.6, 1.4)
                e["max_life"] = e["life"]
                e["x"] = random.uniform(-14, 14)
                e["y"] = random.uniform(-4, 6)
                e["vx"] = random.uniform(-6, 6)
                e["vy"] = random.uniform(-30, -18)

    def draw(self, surface, camera, fonts):
        """Draws all active primitive structures in world coordinates."""
        font_tiny = fonts.get("tiny", pygame.font.SysFont("dejavusans", 10, bold=True))
        font_sm = fonts.get("small", pygame.font.SysFont("dejavusans", 12, bold=True))

        # -------------------------------------------------------------
        # 1. CAMPFIRE (Tile 25, 23)
        # -------------------------------------------------------------
        cf_wx = self.campfire_pos[0] * TILE_SIZE
        cf_wy = self.campfire_pos[1] * TILE_SIZE
        cf_sx, cf_sy = camera.world_to_screen((cf_wx, cf_wy))

        # Only draw if on screen
        if -100 <= cf_sx <= surface.get_width() + 100 and -100 <= cf_sy <= surface.get_height() + 100:
            self._draw_campfire(surface, cf_sx, cf_sy, font_tiny)

        # -------------------------------------------------------------
        # 2. SHELTER (Tile 22, 19 - approx 3x3 tiles area)
        # -------------------------------------------------------------
        sh_wx = self.shelter_pos[0] * TILE_SIZE
        sh_wy = self.shelter_pos[1] * TILE_SIZE
        sh_sx, sh_sy = camera.world_to_screen((sh_wx, sh_wy))

        if -200 <= sh_sx <= surface.get_width() + 200 and -200 <= sh_sy <= surface.get_height() + 200:
            self._draw_shelter(surface, sh_sx, sh_sy, font_sm)

        # -------------------------------------------------------------
        # 2.5. GRASS TENTS & PELT TIPIS (Additional Housing)
        # -------------------------------------------------------------
        for i in range(min(self.grass_tents, len(self.grass_tent_spots))):
            gx, gy = self.grass_tent_spots[i]
            gsx, gsy = camera.world_to_screen((gx * TILE_SIZE, gy * TILE_SIZE))
            if -100 <= gsx <= surface.get_width() + 100 and -100 <= gsy <= surface.get_height() + 100:
                self._draw_grass_tent(surface, gsx, gsy, font_tiny)

        for i in range(min(self.pelt_tipis, len(self.pelt_tipi_spots))):
            tx, ty = self.pelt_tipi_spots[i]
            tsx, tsy = camera.world_to_screen((tx * TILE_SIZE, ty * TILE_SIZE))
            if -100 <= tsx <= surface.get_width() + 100 and -100 <= tsy <= surface.get_height() + 100:
                self._draw_pelt_tipi(surface, tsx, tsy, font_tiny)

        # -------------------------------------------------------------
        # 3. FLINTKNAPPING WORKSHOP
        # -------------------------------------------------------------
        k_wx = self.kiln_pos[0] * TILE_SIZE
        k_wy = self.kiln_pos[1] * TILE_SIZE
        k_sx, k_sy = camera.world_to_screen((k_wx, k_wy))
        if -150 <= k_sx <= surface.get_width() + 150 and -150 <= k_sy <= surface.get_height() + 150:
            self._draw_kiln(surface, k_sx, k_sy, font_tiny)

        # -------------------------------------------------------------
        # 4. MEGALITHIC TOTEM SHRINE
        # -------------------------------------------------------------
        t_wx = self.totem_pos[0] * TILE_SIZE
        t_wy = self.totem_pos[1] * TILE_SIZE
        t_sx, t_sy = camera.world_to_screen((t_wx, t_wy))
        if -150 <= t_sx <= surface.get_width() + 150 and -150 <= t_sy <= surface.get_height() + 150:
            self._draw_totem(surface, t_sx, t_sy, font_tiny)

        # -------------------------------------------------------------
        # 5. MEAT SMOKING & DRYING RACK
        # -------------------------------------------------------------
        smk_wx = self.storage_pos[0] * TILE_SIZE
        smk_wy = self.storage_pos[1] * TILE_SIZE
        smk_sx, smk_sy = camera.world_to_screen((smk_wx, smk_wy))
        if -150 <= smk_sx <= surface.get_width() + 150 and -150 <= smk_sy <= surface.get_height() + 150:
            smk_img = self._sprites.get("meat_smoker")
            if smk_img:
                VisualEnhancer.draw_drop_shadow(surface, (smk_sx + 35, smk_sy + 94), 130, 24, color=(15, 20, 35, 75))
                surface.blit(smk_img, (smk_sx - 45, smk_sy - 35))

        # -------------------------------------------------------------
        # 6. STAKE & MAMMOTH BONE BEAST BARRIER (Paleolithic Defense)
        # -------------------------------------------------------------
        gate_sx, gate_sy = camera.world_to_screen((self.gate_pos[0] * TILE_SIZE, self.gate_pos[1] * TILE_SIZE))
        if -150 <= gate_sx <= surface.get_width() + 150 and -150 <= gate_sy <= surface.get_height() + 150:
            gt_img = self._sprites.get("palisade_gate")
            if gt_img:
                VisualEnhancer.draw_drop_shadow(surface, (gate_sx + 45, gate_sy + 96), 150, 26, color=(15, 20, 35, 80))
                surface.blit(gt_img, (gate_sx - 45, gate_sy - 50))
                # Authentic Paleolithic Mammoth Bone & Stake Palisade reinforcements
                # Left Mammoth Tusk (Ivory curve)
                pygame.draw.arc(surface, (235, 230, 215), (gate_sx - 38, gate_sy + 20, 48, 65), math.pi * 0.4, math.pi * 1.3, 5)
                pygame.draw.arc(surface, (185, 175, 155), (gate_sx - 36, gate_sy + 22, 44, 61), math.pi * 0.4, math.pi * 1.3, 2)
                # Right Mammoth Tusk
                pygame.draw.arc(surface, (235, 230, 215), (gate_sx + 78, gate_sy + 20, 48, 65), -math.pi * 0.3, math.pi * 0.6, 5)
                pygame.draw.arc(surface, (185, 175, 155), (gate_sx + 80, gate_sy + 22, 44, 61), -math.pi * 0.3, math.pi * 0.6, 2)
                # Forward-angled sharpened stakes (chông gỗ vót nhọn chống thú)
                for st_x, st_angle in [(-22, -0.2), (-10, -0.1), (92, 0.1), (104, 0.2)]:
                    p_base = (gate_sx + st_x, gate_sy + 85)
                    p_tip = (gate_sx + st_x + int(st_angle * 30), gate_sy + 55)
                    pygame.draw.line(surface, (65, 42, 22), p_base, p_tip, 5)
                    pygame.draw.line(surface, (140, 110, 70), (p_base[0] + 1, p_base[1]), (p_tip[0] + 1, p_tip[1]), 2)

    def _draw_campfire(self, surface, sx, sy, font):
        """Draws primitive campfire with realistic tactical art, warm ash bed, multi-layer pulsing glow, and rising embers."""
        ts = TILE_SIZE

        # 1. Warm Ash & Trampled Earth Base
        VisualEnhancer.draw_drop_shadow(surface, (sx + ts // 2, sy + 38), 52, 18, color=(35, 25, 18, 90))

        # 2. Authentic Sliced Campfire Sprite or Procedural Fireplace
        cf_img = self._sprites.get("campfire")
        if cf_img:
            surface.blit(cf_img, (sx + 2, sy - 14))
        else:
            # Fallback stone ring & crossed logs
            for i in range(8):
                angle = i * (math.pi * 2 / 8)
                px = sx + ts // 2 + int(math.cos(angle) * 18)
                py = sy + ts // 2 + 10 + int(math.sin(angle) * 10)
                pygame.draw.circle(surface, (120, 115, 110), (px, py), 5)
            pygame.draw.line(surface, (70, 40, 20), (sx + 16, sy + 46), (sx + ts - 16, sy + 28), 5)
            pygame.draw.line(surface, (90, 50, 25), (sx + 16, sy + 28), (sx + ts - 16, sy + 46), 5)

        # 3. Soft Warm Ambient Firelight Aura
        # Natural firelight breathing with sine wave (smooth alpha blending for rich organic warmth)
        pulse = math.sin(self.total_time * 6.0) * 3.0
        glow_r = int(52 + pulse)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        center_g = (glow_r, glow_r)
        for r_step in range(glow_r, 8, -6):
            frac = (r_step - 8) / float(glow_r - 8)
            alpha = int(35 * (1.0 - frac))
            pygame.draw.circle(glow_surf, (255, 145, 35, alpha), center_g, r_step)

        surface.blit(glow_surf, (sx + ts // 2 - glow_r, sy + 32 - glow_r))

        # 4. Floating Glowing Ember Sparks (drifting up and swaying)
        for e in self.embers:
            ex = sx + ts // 2 + int(e["x"])
            ey = sy + 32 + int(e["y"])
            alpha_ratio = max(0.0, min(1.0, e["life"] / e["max_life"]))
            spark_alpha = int(240 * alpha_ratio)
            spark_col = (255, 200, 60, spark_alpha) if e["life"] > 0.5 else (255, 90, 30, spark_alpha)
            spark_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(spark_surf, spark_col, (2, 2), 2 if e["life"] > 0.7 else 1)
            surface.blit(spark_surf, (ex - 2, ey - 2))

    def _draw_grass_tent(self, surface, sx, sy, font):
        """Draws grass lean-to tent with trampled earth base."""
        gt_img = self._sprites.get("grass_tent")
        if gt_img:
            VisualEnhancer.draw_drop_shadow(surface, (sx + 45, sy + 88), 96, 22, color=(15, 20, 35, 75))
            surface.blit(gt_img, (sx - 15, sy - 15))
        else:
            pygame.draw.polygon(surface, (95, 135, 55), [(sx, sy + 40), (sx + 30, sy), (sx + 60, sy + 40)])

    def _draw_pelt_tipi(self, surface, sx, sy, font):
        """Draws mammoth pelt tipi tent with packed loam base."""
        pt_img = self._sprites.get("pelt_tipi")
        if pt_img:
            VisualEnhancer.draw_drop_shadow(surface, (sx + 40, sy + 90), 80, 20, color=(15, 20, 35, 75))
            surface.blit(pt_img, (sx - 10, sy - 25))
        else:
            pygame.draw.polygon(surface, (140, 90, 50), [(sx, sy + 50), (sx + 25, sy), (sx + 50, sy + 50)])

    def _draw_shelter(self, surface, sx, sy, font):
        """Draws primitive rock shelter with trampled cave apron."""
        ts = TILE_SIZE
        w = 3 * ts
        h = 3 * ts

        # Use tactical Cave Hearth with ivory tusks if available
        cave_img = self._sprites.get("cave_hearth")
        if cave_img:
            # Soft contact drop shadow under massive rock base & tusks
            VisualEnhancer.draw_drop_shadow(surface, (sx + 100, sy + 180), 220, 26, color=(15, 20, 35, 75))
            surface.blit(cave_img, (sx - 20, sy - 15))
            return

        # Drop shadow fallback
        pygame.draw.ellipse(surface, (0, 0, 0, 80), (sx + 10, sy + h - 24, w - 20, 22))

        if self.shelter_level == 1:
            pygame.draw.line(surface, (80, 50, 25), (sx + 20, sy + h - 16), (sx + w // 2, sy + 24), 8)
            pygame.draw.line(surface, (70, 45, 20), (sx + w - 20, sy + h - 16), (sx + w // 2, sy + 24), 8)
            pygame.draw.line(surface, (100, 60, 30), (sx + w // 2, sy + 24), (sx + w // 2, sy + h - 16), 6)
            leaf_poly = [(sx + 14, sy + h - 20), (sx + w // 2, sy + 20), (sx + w - 14, sy + h - 20)]
            pygame.draw.polygon(surface, (130, 140, 60), leaf_poly)
            pygame.draw.polygon(surface, (90, 100, 40), leaf_poly, 3)
            pygame.draw.polygon(surface, (30, 25, 20), [(sx + w // 2 - 20, sy + h - 20), (sx + w // 2, sy + h - 55), (sx + w // 2 + 20, sy + h - 20)])
        elif self.shelter_level == 2:
            tepee_poly = [(sx + 10, sy + h - 18), (sx + w // 2, sy + 10), (sx + w - 10, sy + h - 18)]
            pygame.draw.polygon(surface, (150, 100, 65), tepee_poly)
            pygame.draw.polygon(surface, (90, 55, 30), tepee_poly, 4)
            pygame.draw.polygon(surface, (45, 30, 20), [(sx + w // 2 - 22, sy + h - 18), (sx + w // 2, sy + h - 65), (sx + w // 2 + 22, sy + h - 18)])

    def _draw_kiln(self, surface, sx, sy, font):
        """Draws prehistoric flintknapping & toolmakers workshop from tactical artwork."""
        ws_img = self._sprites.get("flint_workshop")
        if ws_img:
            VisualEnhancer.draw_drop_shadow(surface, (sx + 32, sy + 94), 130, 24, color=(15, 20, 35, 75))
            surface.blit(ws_img, (sx - 48, sy - 35))
            return

        ts = TILE_SIZE
        pygame.draw.ellipse(surface, (0, 0, 0, 70), (sx + 6, sy + ts - 16, ts - 12, 14))
        dome_rect = pygame.Rect(sx + 10, sy + 12, ts - 20, ts - 20)
        pygame.draw.ellipse(surface, (175, 105, 60), dome_rect)
        pygame.draw.ellipse(surface, (110, 60, 30), dome_rect, 3)

    def _draw_totem(self, surface, sx, sy, font):
        """Draws megalithic standing stone totem shrine from tactical artwork."""
        shrine_img = self._sprites.get("megalithic_shrine")
        if shrine_img:
            VisualEnhancer.draw_drop_shadow(surface, (sx + 35, sy + 88), 130, 24, color=(15, 20, 35, 75))
            surface.blit(shrine_img, (sx - 45, sy - 45))
            return

        ts = TILE_SIZE
        w = ts
        h = int(ts * 1.6)
        pygame.draw.ellipse(surface, (0, 0, 0, 70), (sx + 8, sy + h - 16, w - 16, 14))
        pillar_rect = pygame.Rect(sx + 18, sy + 16, w - 36, h - 24)
        pygame.draw.rect(surface, (110, 80, 50), pillar_rect, border_radius=4)
        pygame.draw.rect(surface, (60, 40, 25), pillar_rect, 3, border_radius=4)

    def to_dict(self):
        return {
            "campfire_level": self.campfire_level,
            "shelter_level": self.shelter_level,
            "kiln_level": self.kiln_level,
            "totem_level": self.totem_level,
            "storage_level": self.storage_level
        }

    def from_dict(self, data):
        if not data:
            return
        self.campfire_level = data.get("campfire_level", 0)
        self.shelter_level = data.get("shelter_level", 1)
        self.kiln_level = data.get("clay_kiln_level", data.get("kiln_level", 0))
        self.totem_level = data.get("totem_level", 0)
        self.storage_level = data.get("storage_level", 1)

