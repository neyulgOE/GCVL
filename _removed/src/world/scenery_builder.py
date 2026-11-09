"""
Scenery and Architecture Builder for Green Valley Tales.
Constructs high-fidelity pixel art town plaza composite, detailed storefronts,
cozy farmhouse exterior, water decorations, and ambient lighting sources.
"""

import pygame
import os
import math
import random
from src.settings import TILE_SIZE, MAP_COLS, MAP_ROWS, WORLD_WIDTH, WORLD_HEIGHT

# Palette constants for architectural masonry & nature
WOOD_DARK = (82, 48, 28)
WOOD_MID = (138, 86, 48)
WOOD_LIGHT = (194, 134, 82)
WOOD_PALE = (226, 178, 126)

STONE_DARK = (68, 72, 78)
STONE_MID = (118, 124, 134)
STONE_LIGHT = (168, 176, 188)
STONE_PALE = (212, 218, 226)

ROOF_RED_DARK = (130, 42, 34)
ROOF_RED = (185, 62, 48)
ROOF_RED_LIGHT = (224, 96, 78)

ROOF_SLATE_DARK = (42, 48, 58)
ROOF_SLATE = (72, 82, 98)
ROOF_SLATE_LIGHT = (110, 124, 145)

GOLD_ACCENT = (248, 204, 64)
LANTERN_GLOW = (255, 230, 140)

class SceneryBuilder:
    @staticmethod
    def build_storefront_sprites(ts, fonts):
        """Builds authentic, detailed prehistoric tribal lodges for Thầy Mo Kraa, Tộc Trưởng Ogg, and Thợ Săn Boomer."""
        font_sm = fonts.get("small", pygame.font.SysFont("dejavusans", 12, bold=True))
        font_norm = fonts.get("normal", pygame.font.SysFont("dejavusans", 14, bold=True))
        font_large = fonts.get("large", pygame.font.SysFont("dejavusans", 16, bold=True))

        sprites = {}

        # =========================================================================
        # 1. ĐÀN TẾ & THẢO DƯỢC THẦY MO KRAA (Cols 10..18, Rows 9..14 -> 9 x 6 tiles = 576 x 384)
        # Giant Mammoth Rib Canopy, Glowing Spirit Stones, Hanging Medicinal Herbs & Braziers
        # =========================================================================
        w_m, h_m = 9 * ts, 6 * ts
        shop_m = pygame.Surface((w_m, h_m), pygame.SRCALPHA)

        # Soft ground shadow
        pygame.draw.ellipse(shop_m, (0, 0, 0, 75), (14, h_m - 34, w_m - 28, 30))

        # Mud & Clay Sanctuary Base Walls (Wattle-and-daub prehistoric earthen lodge)
        body_rect = pygame.Rect(28, 92, w_m - 56, h_m - 120)
        pygame.draw.rect(shop_m, (168, 114, 76), body_rect, border_radius=12)
        pygame.draw.rect(shop_m, (112, 68, 42), body_rect, 4, border_radius=12)

        # Earth texture & primitive red ochre hand stencils / spiral petroglyphs on walls
        for py in range(110, h_m - 35, 26):
            pygame.draw.line(shop_m, (142, 92, 58), (34, py), (w_m - 34, py), 2)
        # Hand stencils & spiral symbols in sacred ochre
        for hx, hy in [(70, 150), (w_m - 90, 150), (140, 175), (w_m - 160, 175)]:
            pygame.draw.circle(shop_m, (190, 50, 40), (hx, hy), 7)
            pygame.draw.circle(shop_m, (215, 80, 60), (hx, hy), 4)
            pygame.draw.circle(shop_m, (168, 114, 76), (hx, hy), 2)

        # Giant Curved Mammoth Rib Bones forming roof framework
        rib_color = (238, 232, 218)
        rib_shadow = (175, 168, 152)
        for rx in range(40, w_m - 40, 64):
            # Left curvature
            pygame.draw.arc(shop_m, rib_color, (rx - 20, 20, 80, 160), math.pi * 0.1, math.pi * 0.9, 6)
            pygame.draw.arc(shop_m, rib_shadow, (rx - 19, 21, 80, 160), math.pi * 0.1, math.pi * 0.9, 2)

        # Thick Wild Thatch & Dried Palm Frond Roof
        thatch_poly = [
            (14, 110), (w_m // 2, 12), (w_m - 14, 110)
        ]
        pygame.draw.polygon(shop_m, (148, 122, 62), thatch_poly)
        pygame.draw.polygon(shop_m, (95, 76, 35), thatch_poly, 5)

        # Wild grass thatch overhang layers
        for ty in range(28, 112, 14):
            frac = (ty - 12) / 98.0
            tx_left = int(14 + (w_m // 2 - 14) * (1.0 - frac))
            tx_right = int(w_m - 14 - (w_m // 2 - 14) * (1.0 - frac))
            pygame.draw.line(shop_m, (175, 148, 78), (tx_left, ty), (tx_right, ty), 3)
            for gx in range(tx_left + 12, tx_right - 10, 22):
                pygame.draw.line(shop_m, (120, 96, 46), (gx, ty), (gx - 4, ty + 10), 2)

        # Sacred Spirit Totem Mask atop roof peak
        totem_center = (w_m // 2, 42)
        pygame.draw.circle(shop_m, (242, 236, 222), totem_center, 18)
        pygame.draw.circle(shop_m, (160, 150, 135), totem_center, 18, 2)
        # Horns on mask
        pygame.draw.polygon(shop_m, (225, 218, 200), [(w_m // 2 - 16, 38), (w_m // 2 - 32, 16), (w_m // 2 - 8, 30)])
        pygame.draw.polygon(shop_m, (225, 218, 200), [(w_m // 2 + 16, 38), (w_m // 2 + 32, 16), (w_m // 2 + 8, 30)])
        # Glowing spirit turquoise eyes
        pygame.draw.circle(shop_m, (65, 215, 240), (w_m // 2 - 7, 40), 4)
        pygame.draw.circle(shop_m, (65, 215, 240), (w_m // 2 + 7, 40), 4)

        # Entrance Archway draped with Rawhide Pelts
        arch_w, arch_h = 160, 130
        arch_x = w_m // 2 - arch_w // 2
        arch_y = h_m - arch_h - 28
        pygame.draw.rect(shop_m, (34, 22, 16), (arch_x, arch_y, arch_w, arch_h), border_radius=10)
        # Rawhide curtain tied back with rope
        pygame.draw.polygon(shop_m, (185, 135, 82), [(arch_x, arch_y), (arch_x + 36, arch_y), (arch_x + 18, arch_y + arch_h), (arch_x, arch_y + arch_h)])
        pygame.draw.polygon(shop_m, (185, 135, 82), [(arch_x + arch_w - 36, arch_y), (arch_x + arch_w, arch_y), (arch_x + arch_w, arch_y + arch_h), (arch_x + arch_w - 18, arch_y + arch_h)])

        # Drying Herb Racks & Clay Jars flanking entrance
        # Left: Hanging sage, wild roots, mint bundles
        for hx, col in [(arch_x - 70, (80, 160, 65)), (arch_x - 44, (215, 180, 70)), (arch_x - 18, (120, 185, 90))]:
            pygame.draw.line(shop_m, (95, 60, 30), (hx, arch_y + 10), (hx, arch_y + 60), 3)
            for leaf_y in range(arch_y + 24, arch_y + 56, 8):
                pygame.draw.ellipse(shop_m, col, (hx - 8, leaf_y, 16, 8))

        # Right: Clay potion jars and ground grinding stone
        c1_rect = pygame.Rect(arch_x + arch_w + 24, arch_y + 50, 42, 48)
        pygame.draw.ellipse(shop_m, (195, 110, 55), c1_rect)
        pygame.draw.ellipse(shop_m, (140, 70, 30), c1_rect, 2)
        pygame.draw.rect(shop_m, (220, 130, 70), (arch_x + arch_w + 34, arch_y + 44, 22, 10), border_radius=2)

        # Sacred Earthen Braziers with Glowing Purple / Cyan Spirit Embers
        for bx in [arch_x - 84, arch_x + arch_w + 74]:
            pygame.draw.ellipse(shop_m, (65, 70, 78), (bx - 14, arch_y + 74, 28, 16))
            pygame.draw.rect(shop_m, (135, 75, 45), (bx - 10, arch_y + 60, 20, 18), border_radius=3)
            # Glowing flame
            pygame.draw.circle(shop_m, (85, 220, 255), (bx, arch_y + 54), 8)
            pygame.draw.circle(shop_m, (200, 245, 255), (bx, arch_y + 52), 4)

        # Burnt-Wood Tribal Plaque
        sign_w, sign_h = 360, 42
        sign_x, sign_y = w_m // 2 - sign_w // 2, 102
        pygame.draw.rect(shop_m, (42, 28, 18), (sign_x - 3, sign_y - 3, sign_w + 6, sign_h + 6), border_radius=6)
        pygame.draw.rect(shop_m, (88, 54, 30), (sign_x, sign_y, sign_w, sign_h), border_radius=5)
        pygame.draw.rect(shop_m, (215, 165, 75), (sign_x + 3, sign_y + 3, sign_w - 6, sign_h - 6), 2, border_radius=4)
        lbl_m = font_large.render("ĐÀN TẾ THẦY MO KRAA", True, (255, 238, 200))
        shop_m.blit(lbl_m, (w_m // 2 - lbl_m.get_width() // 2, sign_y + sign_h // 2 - lbl_m.get_height() // 2))

        sprites["shop_co_mai"] = shop_m

        # =========================================================================
        # 2. ĐẠI TRƯỚNG BỘ LẠC TỘC TRƯỞNG OGG (Cols 32..40, Rows 9..14 -> 9 x 6 tiles = 576 x 384)
        # Massive Bison Pelts, Crossed Mammoth Tusks, Spiked Log Palisade & Weapon Racks
        # =========================================================================
        w_b, h_b = 9 * ts, 6 * ts
        shop_b = pygame.Surface((w_b, h_b), pygame.SRCALPHA)

        # Soft drop shadow
        pygame.draw.ellipse(shop_b, (0, 0, 0, 80), (14, h_b - 34, w_b - 28, 30))

        # Sturdy Rough-Hewn Pine Log Walls
        b_body = pygame.Rect(26, 88, w_b - 52, h_b - 116)
        pygame.draw.rect(shop_b, (118, 72, 42), b_body, border_radius=10)
        pygame.draw.rect(shop_b, (65, 38, 20), b_body, 4, border_radius=10)

        # Horizontal rough bark logs
        for py in range(98, h_b - 32, 24):
            pygame.draw.line(shop_b, (85, 50, 26), (30, py), (w_b - 30, py), 4)
            pygame.draw.line(shop_b, (142, 92, 54), (32, py + 2), (w_b - 32, py + 2), 2)

        # High-Peaked Bison Fur & Thatch Roof
        roof_poly_b = [(12, 104), (w_b // 2, 10), (w_b - 12, 104)]
        pygame.draw.polygon(shop_b, (135, 78, 48), roof_poly_b)
        pygame.draw.polygon(shop_b, (62, 35, 18), roof_poly_b, 5)

        # Layered hide textures on roof
        for ry in range(26, 104, 16):
            frac = (ry - 10) / 94.0
            rx_left = int(12 + (w_b // 2 - 12) * (1.0 - frac))
            rx_right = int(w_b - 12 - (w_b // 2 - 12) * (1.0 - frac))
            pygame.draw.line(shop_b, (168, 102, 65), (rx_left, ry), (rx_right, ry), 4)
            for sx in range(rx_left + 16, rx_right - 10, 26):
                pygame.draw.line(shop_b, (54, 30, 16), (sx, ry), (sx, ry + 12), 2)

        # Massive Crossed Mammoth Tusks arching over entrance
        tusk_col = (245, 240, 228)
        tusk_shad = (180, 172, 155)
        # Left tusk curving up & right
        pygame.draw.arc(shop_b, tusk_col, (w_b // 2 - 140, 40, 130, 180), math.pi * 0.4, math.pi * 1.1, 8)
        pygame.draw.arc(shop_b, tusk_shad, (w_b // 2 - 138, 42, 130, 180), math.pi * 0.4, math.pi * 1.1, 3)
        # Right tusk curving up & left
        pygame.draw.arc(shop_b, tusk_col, (w_b // 2 + 10, 40, 130, 180), -math.pi * 0.1, math.pi * 0.6, 8)
        pygame.draw.arc(shop_b, tusk_shad, (w_b // 2 + 12, 42, 130, 180), -math.pi * 0.1, math.pi * 0.6, 3)

        # Great Elk Horns at the Peak
        pygame.draw.polygon(shop_b, (230, 222, 204), [(w_b // 2 - 18, 30), (w_b // 2 - 40, 6), (w_b // 2 - 8, 22)])
        pygame.draw.polygon(shop_b, (230, 222, 204), [(w_b // 2 + 18, 30), (w_b // 2 + 40, 6), (w_b // 2 + 8, 22)])

        # Longhouse Main Entrance with Heavy Bear Fur Canopy
        ent_w, ent_h = 160, 126
        ent_x = w_b // 2 - ent_w // 2
        ent_y = h_b - ent_h - 28
        pygame.draw.rect(shop_b, (28, 18, 12), (ent_x, ent_y, ent_w, ent_h), border_radius=8)
        pygame.draw.rect(shop_b, (135, 80, 48), (ent_x + 8, ent_y + 8, ent_w - 16, 34), border_radius=4)

        # Weapon Displays: Left = Flint Battle Spears, Right = Heavy Stone War Axes & Shields
        # Left Spears
        for spx in [ent_x - 70, ent_x - 46, ent_x - 22]:
            pygame.draw.line(shop_b, (150, 95, 50), (spx, ent_y + 10), (spx, ent_y + 100), 4)
            # Flint spear tip
            pygame.draw.polygon(shop_b, (65, 70, 80), [(spx, ent_y), (spx - 6, ent_y + 16), (spx + 6, ent_y + 16)])
            pygame.draw.polygon(shop_b, (115, 120, 135), [(spx, ent_y), (spx - 6, ent_y + 16), (spx + 6, ent_y + 16)], 1)

        # Right Hardened Hide Shield & Stone Axes
        shld_rect = pygame.Rect(ent_x + ent_w + 30, ent_y + 24, 52, 68)
        pygame.draw.ellipse(shop_b, (185, 120, 65), shld_rect)
        pygame.draw.ellipse(shop_b, (85, 45, 20), shld_rect, 3)
        # War clan red crest on shield
        pygame.draw.polygon(shop_b, (215, 45, 35), [(shld_rect.centerx, shld_rect.y + 10), 
                                                    (shld_rect.x + 10, shld_rect.y + 45), 
                                                    (shld_rect.right - 10, shld_rect.y + 45)])

        # Stone Tool Sharpening Anvil Slab
        slab_rect = pygame.Rect(ent_x + ent_w + 22, ent_y + 88, 68, 26)
        pygame.draw.ellipse(shop_b, (120, 125, 132), slab_rect)
        pygame.draw.ellipse(shop_b, (75, 80, 86), slab_rect, 2)

        # Roaring Hearth fire glow from entrance
        pygame.draw.ellipse(shop_b, (245, 95, 25), (ent_x + 35, ent_y + 70, ent_w - 70, 36))
        pygame.draw.ellipse(shop_b, (255, 215, 60), (ent_x + 50, ent_y + 78, ent_w - 100, 20))

        # Carved Wooden Clan Signboard
        sign_w, sign_h = 380, 42
        sign_x, sign_y = w_b // 2 - sign_w // 2, 98
        pygame.draw.rect(shop_b, (42, 24, 16), (sign_x - 3, sign_y - 3, sign_w + 6, sign_h + 6), border_radius=6)
        pygame.draw.rect(shop_b, (78, 42, 22), (sign_x, sign_y, sign_w, sign_h), border_radius=5)
        pygame.draw.rect(shop_b, (235, 120, 45), (sign_x + 3, sign_y + 3, sign_w - 6, sign_h - 6), 2, border_radius=4)
        lbl_b = font_large.render("ĐẠI TRƯỚNG TỘC TRƯỞNG OGG", True, (255, 235, 195))
        shop_b.blit(lbl_b, (w_b // 2 - lbl_b.get_width() // 2, sign_y + sign_h // 2 - lbl_b.get_height() // 2))

        sprites["shop_bac_bay"] = shop_b

        # =========================================================================
        # 3. CHÒI SĂN & TRẠI THUẦN THÚ BOOMER (Cols 20..30, Rows 3..8 -> 11 x 6 tiles = 704 x 384)
        # Rustic Pine Watchtower, Animal Fur Stretching Frames, Smoked Fish Racks & Corrals
        # =========================================================================
        w_t, h_t = 11 * ts, 6 * ts
        shop_t = pygame.Surface((w_t, h_t), pygame.SRCALPHA)

        # Soft drop shadow
        pygame.draw.ellipse(shop_t, (0, 0, 0, 80), (14, h_t - 34, w_t - 28, 30))

        # Sturdy Horizontal Notched Pine Lodge Body
        t_body = pygame.Rect(32, 88, w_t - 64, h_t - 114)
        pygame.draw.rect(shop_t, (148, 98, 58), t_body, border_radius=10)
        pygame.draw.rect(shop_t, (85, 48, 24), t_body, 4, border_radius=10)

        # Pine log ring ends
        for py in range(96, h_t - 30, 24):
            pygame.draw.line(shop_t, (108, 68, 36), (36, py), (w_t - 36, py), 3)
            # Log end notches
            pygame.draw.circle(shop_t, (185, 135, 85), (42, py + 10), 8)
            pygame.draw.circle(shop_t, (75, 45, 22), (42, py + 10), 8, 2)
            pygame.draw.circle(shop_t, (185, 135, 85), (w_t - 42, py + 10), 8)
            pygame.draw.circle(shop_t, (75, 45, 22), (w_t - 42, py + 10), 8, 2)

        # Sloped Heavy Reed Thatched Roof
        roof_poly_t = [(14, 98), (w_t // 2, 14), (w_t - 14, 98)]
        pygame.draw.polygon(shop_t, (158, 130, 72), roof_poly_t)
        pygame.draw.polygon(shop_t, (92, 70, 32), roof_poly_t, 5)

        # Thatch shading
        for ry in range(28, 98, 14):
            frac = (ry - 14) / 84.0
            rx_left = int(14 + (w_t // 2 - 14) * (1.0 - frac))
            rx_right = int(w_t - 14 - (w_t // 2 - 14) * (1.0 - frac))
            pygame.draw.line(shop_t, (185, 155, 88), (rx_left, ry), (rx_right, ry), 3)

        # Hunter's Wooden Lookout Watchtower on Roof Center
        tower_rect = pygame.Rect(w_t // 2 - 48, 4, 96, 58)
        pygame.draw.rect(shop_t, (115, 68, 36), tower_rect, border_radius=4)
        pygame.draw.rect(shop_t, (68, 38, 18), tower_rect, 3, border_radius=4)
        # Lookout rails
        for lx in range(w_t // 2 - 40, w_t // 2 + 42, 16):
            pygame.draw.line(shop_t, (175, 125, 75), (lx, 10), (lx, 36), 3)
        # Wolf skull trophy mounted on watchtower
        pygame.draw.ellipse(shop_t, (238, 234, 224), (w_t // 2 - 12, 14, 24, 18))
        pygame.draw.polygon(shop_t, (220, 215, 200), [(w_t // 2 - 8, 30), (w_t // 2 - 2, 36), (w_t // 2 + 4, 36), (w_t // 2 + 8, 30)])

        # Center Double Entrance Doors with Fur Drapes
        door_rect = pygame.Rect(w_t // 2 - 50, h_t - 150, 100, 120)
        pygame.draw.rect(shop_t, (35, 22, 14), door_rect, border_radius=6)
        pygame.draw.rect(shop_t, (135, 84, 48), (door_rect.x + 6, door_rect.y + 6, door_rect.w - 12, 28), border_radius=3)

        # Fur Stretching and Tanning Frame (West side)
        frame_rect = pygame.Rect(w_t // 2 - 270, h_t - 160, 110, 120)
        # Wood poles crossed
        pygame.draw.line(shop_t, (95, 58, 28), (frame_rect.x, frame_rect.y), (frame_rect.x, frame_rect.bottom), 5)
        pygame.draw.line(shop_t, (95, 58, 28), (frame_rect.right, frame_rect.y), (frame_rect.right, frame_rect.bottom), 5)
        pygame.draw.line(shop_t, (95, 58, 28), (frame_rect.x, frame_rect.y + 10), (frame_rect.right, frame_rect.y + 10), 4)
        pygame.draw.line(shop_t, (95, 58, 28), (frame_rect.x, frame_rect.bottom - 10), (frame_rect.right, frame_rect.bottom - 10), 4)
        # Stretched tiger/bear pelt inside frame
        pelt_poly = [
            (frame_rect.x + 16, frame_rect.y + 24), (frame_rect.right - 16, frame_rect.y + 24),
            (frame_rect.right - 12, frame_rect.bottom - 24), (frame_rect.x + 12, frame_rect.bottom - 24)
        ]
        pygame.draw.polygon(shop_t, (215, 138, 62), pelt_poly)
        for spot_x in range(frame_rect.x + 28, frame_rect.right - 24, 20):
            pygame.draw.circle(shop_t, (85, 45, 20), (spot_x, frame_rect.y + 50), 4)
            pygame.draw.circle(shop_t, (85, 45, 20), (spot_x + 8, frame_rect.y + 80), 4)

        # Smoked Fish & Venison Drying Rack (East side)
        rack_x = w_t // 2 + 150
        rack_y = h_t - 146
        pygame.draw.line(shop_t, (95, 58, 28), (rack_x, rack_y), (rack_x, rack_y + 106), 4)
        pygame.draw.line(shop_t, (95, 58, 28), (rack_x + 90, rack_y), (rack_x + 90, rack_y + 106), 4)
        pygame.draw.line(shop_t, (135, 85, 45), (rack_x - 6, rack_y + 16), (rack_x + 96, rack_y + 16), 3)
        pygame.draw.line(shop_t, (135, 85, 45), (rack_x - 6, rack_y + 54), (rack_x + 96, rack_y + 54), 3)
        # Hanging fish
        for fx in range(rack_x + 8, rack_x + 86, 20):
            pygame.draw.ellipse(shop_t, (190, 140, 85), (fx, rack_y + 18, 12, 28))
            pygame.draw.polygon(shop_t, (140, 95, 50), [(fx + 3, rack_y + 44), (fx + 6, rack_y + 50), (fx + 9, rack_y + 44)])
            pygame.draw.ellipse(shop_t, (175, 75, 60), (fx, rack_y + 56, 12, 26))

        # Carved Wooden Signboard with Bone Teeth
        sign_w, sign_h = 420, 42
        sign_x, sign_y = w_t // 2 - sign_w // 2, 104
        pygame.draw.rect(shop_t, (42, 26, 16), (sign_x - 3, sign_y - 3, sign_w + 6, sign_h + 6), border_radius=6)
        pygame.draw.rect(shop_t, (82, 48, 26), (sign_x, sign_y, sign_w, sign_h), border_radius=5)
        pygame.draw.rect(shop_t, (225, 215, 185), (sign_x + 3, sign_y + 3, sign_w - 6, sign_h - 6), 2, border_radius=4)
        lbl_t = font_large.render("CHÒI SĂN THỢ SĂN BOOMER", True, (255, 240, 205))
        shop_t.blit(lbl_t, (w_t // 2 - lbl_t.get_width() // 2, sign_y + sign_h // 2 - lbl_t.get_height() // 2))

        # Rawhide Torch Sconces flanking door
        for lx in [w_t // 2 - 84, w_t // 2 + 84]:
            pygame.draw.line(shop_t, (85, 50, 25), (lx, h_t - 130), (lx, h_t - 90), 3)
            pygame.draw.circle(shop_t, (255, 175, 40), (lx, h_t - 132), 7)
            pygame.draw.circle(shop_t, (255, 235, 120), (lx, h_t - 134), 4)

        sprites["shop_cu_ba_tri"] = shop_t

        return sprites

    @staticmethod
    def build_farmhouse_exterior(ts):
        """
        Builds a subtle atmospheric earthen campsite ground footprint for the player's primitive base.
        The actual progressive dwelling is rendered dynamically by PrimitiveStructures.
        """
        w, h = 624, 560
        camp = pygame.Surface((w, h), pygame.SRCALPHA)
        # Soft campsite clearing dirt footprint
        pygame.draw.ellipse(camp, (0, 0, 0, 40), (20, h - 180, w - 40, 150))
        pygame.draw.ellipse(camp, (150, 105, 65, 110), (40, h - 220, w - 80, 180))
        # Small river stones around perimeter
        for ang in range(0, 360, 24):
            rad = math.radians(ang)
            sx = int(w // 2 + math.cos(rad) * (w // 2 - 50))
            sy = int(h - 130 + math.sin(rad) * 65)
            pygame.draw.ellipse(camp, (135, 140, 145), (sx - 8, sy - 6, 16, 12))
            pygame.draw.ellipse(camp, (85, 90, 95), (sx - 8, sy - 6, 16, 12), 1)
        return camp

    @staticmethod
    def build_town_composite(ts, fonts):
        """
        Builds the entire Tribal Settlement (Bản Doanh Bộ Lạc) composite background (3200 x 2560)
        featuring ancient primeval earth, winding beaten red-clay trails, the Great Sacred Bonfire
        with towering carved megaliths, Mammoth Tusk gateway, and flaming tribal torches.
        """
        w, h = MAP_COLS * ts, MAP_ROWS * ts  # 3200 x 2560
        town_surf = pygame.Surface((w, h))

        # 1. Base Primeval Savannah / Ancient Forest Floor
        town_surf.fill((112, 160, 78))

        # Organic wild earth and dark grass patches
        random.seed(1337)
        for _ in range(950):
            gx = random.randint(0, w - 48)
            gy = random.randint(0, h - 48)
            gw = random.randint(28, 72)
            gh = random.randint(20, 54)
            r_val = random.random()
            if r_val < 0.4:
                gcol = (98, 145, 68)    # Deep shadow grass
            elif r_val < 0.7:
                gcol = (128, 172, 86)   # Sunlit lime grass
            else:
                gcol = (142, 108, 68)   # Exposed reddish fertile clay
            pygame.draw.ellipse(town_surf, gcol, (gx, gy, gw, gh))

        # 2. Main Tribal Gathering Clearing (Cols 13..37, Rows 11..29)
        p_x = 13 * ts
        p_y = 11 * ts
        p_w = 25 * ts
        p_h = 19 * ts

        # Clearing earthen ground
        clearing_rect = pygame.Rect(p_x - 12, p_y - 12, p_w + 24, p_h + 24)
        pygame.draw.ellipse(town_surf, (148, 102, 62), clearing_rect)
        pygame.draw.ellipse(town_surf, (168, 118, 74), (p_x, p_y, p_w, p_h))

        # River pebble scatter around tribal meeting grounds
        for _ in range(650):
            px = random.randint(p_x + 10, p_x + p_w - 20)
            py = random.randint(p_y + 10, p_y + p_h - 20)
            p_col = (150, 155, 160) if random.random() < 0.6 else (185, 145, 110)
            pygame.draw.ellipse(town_surf, p_col, (px, py, random.randint(6, 12), random.randint(4, 8)))

        # 3. Organic Winding Red-Clay & Beaten Dirt Trails
        # Trail West: Towards the Wild Farming Campsite (Cols 0..14, Rows 19..21)
        road_w = pygame.Rect(0, 19 * ts - 8, 14 * ts, 3 * ts + 16)
        pygame.draw.rect(town_surf, (156, 106, 66), road_w)
        for py in range(19 * ts, 22 * ts, 18):
            for px in range(0, 14 * ts, 24):
                if random.random() < 0.35:
                    pygame.draw.circle(town_surf, (138, 92, 54), (px + 10, py + 8), random.randint(4, 9))

        # Trail North: Towards Chieftain's Lodge & Animal Corral (Cols 24..26, Rows 5..11)
        road_n = pygame.Rect(24 * ts - 6, 5 * ts, 3 * ts + 12, 6 * ts)
        pygame.draw.rect(town_surf, (156, 106, 66), road_n)
        for py in range(5 * ts, 11 * ts, 20):
            for px in range(24 * ts, 27 * ts, 20):
                if random.random() < 0.4:
                    pygame.draw.circle(town_surf, (140, 96, 58), (px + 8, py + 8), random.randint(4, 8))

        # Trails branching to Shaman's Shrine (West) and Chieftain's Armory (East)
        # West branch to Shaman (cols 13..15, rows 12..15)
        pygame.draw.ellipse(town_surf, (156, 106, 66), (12 * ts, 13 * ts, 4 * ts, 3 * ts))
        # East branch to Chieftain (cols 31..34, rows 12..15)
        pygame.draw.ellipse(town_surf, (156, 106, 66), (31 * ts, 13 * ts, 4 * ts, 3 * ts))

        # 4. Central Sacred Great Bonfire & Megalithic Stone Circle (Col 25, Row 20)
        fc_x = 25 * ts + ts // 2
        fc_y = 20 * ts + ts // 2

        # Outer ritual circle of 12 ancient standing menhirs (Prehistoric megaliths)
        pygame.draw.circle(town_surf, (130, 85, 50), (fc_x, fc_y), 136)
        pygame.draw.circle(town_surf, (95, 60, 32), (fc_x, fc_y), 136, 4)

        for ang in range(0, 360, 30):
            rad = math.radians(ang)
            mx = int(fc_x + math.cos(rad) * 118)
            my = int(fc_y + math.sin(rad) * 118)
            # Megalith shadow
            pygame.draw.ellipse(town_surf, (0, 0, 0, 70), (mx - 14, my + 8, 28, 14))
            # Megalith stone pillar
            m_rect = pygame.Rect(mx - 12, my - 22, 24, 34)
            pygame.draw.rect(town_surf, (148, 154, 162), m_rect, border_radius=6)
            pygame.draw.rect(town_surf, (88, 92, 98), m_rect, 2, border_radius=6)
            # Red ochre ancient spiral rune on megalith
            pygame.draw.circle(town_surf, (205, 55, 45), (mx, my - 6), 5, 2)

        # Inner Fire Hearth: Encircled with heavy river boulders
        pygame.draw.circle(town_surf, (70, 75, 82), (fc_x, fc_y), 78)
        pygame.draw.circle(town_surf, (45, 48, 54), (fc_x, fc_y), 78, 3)
        # Deep fire pit ash bed
        pygame.draw.circle(town_surf, (36, 32, 28), (fc_x, fc_y), 66)

        # Huge Stacked Hardwood Logs
        log_col = (110, 68, 36)
        pygame.draw.line(town_surf, log_col, (fc_x - 48, fc_y - 20), (fc_x + 48, fc_y + 20), 10)
        pygame.draw.line(town_surf, log_col, (fc_x - 48, fc_y + 20), (fc_x + 48, fc_y - 20), 10)
        pygame.draw.line(town_surf, log_col, (fc_x, fc_y - 48), (fc_x, fc_y + 48), 10)
        pygame.draw.line(town_surf, log_col, (fc_x - 48, fc_y), (fc_x + 48, fc_y), 10)

        # Radiant Roaring Sacred Flames
        pygame.draw.circle(town_surf, (255, 65, 20), (fc_x, fc_y), 44)
        pygame.draw.circle(town_surf, (255, 145, 35), (fc_x, fc_y), 32)
        pygame.draw.circle(town_surf, (255, 225, 95), (fc_x, fc_y), 18)
        pygame.draw.circle(town_surf, (255, 255, 220), (fc_x, fc_y), 8)

        # Floating embers around sacred fire
        ember_locs = [(-28, -34), (32, -26), (-18, 36), (26, 30), (-40, 10), (38, -12)]
        for ex, ey in ember_locs:
            pygame.draw.circle(town_surf, (255, 200, 80), (fc_x + ex, fc_y + ey), 3)

        # 5. Tribal Flaming Torches on Spiked Stakes (Replaces modern street lampposts)
        lamp_positions = [
            (p_x + ts, p_y + ts),
            (p_x + p_w - ts, p_y + ts),
            (p_x + ts, p_y + p_h - ts),
            (p_x + p_w - ts, p_y + p_h - ts),
            (p_x + p_w // 2, p_y + ts),
            (p_x + p_w // 2, p_y + p_h - ts),
            (p_x + ts, p_y + p_h // 2),
            (p_x + p_w - ts, p_y + p_h // 2),
            # Entrance & path torches
            (4 * ts, 18 * ts),
            (9 * ts, 18 * ts),
            (23 * ts, 7 * ts),
            (27 * ts, 7 * ts)
        ]
        for lx, ly in lamp_positions:
            # Drop shadow
            pygame.draw.ellipse(town_surf, (0, 0, 0, 55), (lx - 12, ly + 28, 24, 10))
            # Spiked wooden stake
            pygame.draw.line(town_surf, (95, 58, 28), (lx, ly + 28), (lx, ly - 22), 6)
            pygame.draw.line(town_surf, (145, 92, 48), (lx - 1, ly + 26), (lx - 1, ly - 20), 2)
            # Rawhide rope wrap
            pygame.draw.rect(town_surf, (185, 140, 85), (lx - 5, ly - 12, 10, 8), border_radius=2)
            # Pitch-soaked torch head & flaming fire
            pygame.draw.circle(town_surf, (45, 40, 35), (lx, ly - 26), 7)
            # Fire flame
            pygame.draw.circle(town_surf, (255, 80, 25), (lx, ly - 32), 10)
            pygame.draw.circle(town_surf, (255, 185, 45), (lx, ly - 32), 6)
            pygame.draw.circle(town_surf, (255, 245, 160), (lx, ly - 34), 3)

        # 6. Mammoth Tusk Gateway at West Entrance (Col 2, Row 19..21)
        gate_x = 2 * ts
        gate_y = 20 * ts + ts // 2
        # Giant left tusk arching over road
        pygame.draw.arc(town_surf, (245, 240, 228), (gate_x - 30, gate_y - 120, 110, 160), math.pi * 0.4, math.pi * 1.1, 10)
        pygame.draw.arc(town_surf, (175, 168, 150), (gate_x - 28, gate_y - 118, 110, 160), math.pi * 0.4, math.pi * 1.1, 3)
        # Giant right tusk
        pygame.draw.arc(town_surf, (245, 240, 228), (gate_x + 20, gate_y - 120, 110, 160), -math.pi * 0.1, math.pi * 0.6, 10)
        pygame.draw.arc(town_surf, (175, 168, 150), (gate_x + 22, gate_y - 118, 110, 160), -math.pi * 0.1, math.pi * 0.6, 3)
        # Stone cairn bases for tusks
        pygame.draw.ellipse(town_surf, (120, 125, 130), (gate_x - 20, gate_y + 16, 36, 22))
        pygame.draw.ellipse(town_surf, (120, 125, 130), (gate_x + 60, gate_y + 16, 36, 22))

        # 7. Boundary Ancient Pine Trees & Dense Primitive Forest Borders
        for bx in range(0, w, 64):
            pygame.draw.circle(town_surf, (42, 92, 38), (bx + 32, 2 * ts), 44)
            pygame.draw.circle(town_surf, (58, 118, 52), (bx + 32, 2 * ts - 10), 38)
        for bx in range(0, w, 64):
            pygame.draw.circle(town_surf, (42, 92, 38), (bx + 32, 38 * ts), 44)
            pygame.draw.circle(town_surf, (58, 118, 52), (bx + 32, 38 * ts - 10), 38)
        for by in range(0, h, 64):
            pygame.draw.circle(town_surf, (42, 92, 38), (48 * ts, by + 32), 44)
            pygame.draw.circle(town_surf, (58, 118, 52), (48 * ts - 8, by + 32), 38)
        for by in range(0, h, 64):
            if not (18 * ts <= by <= 22 * ts):
                pygame.draw.circle(town_surf, (42, 92, 38), (2 * ts, by + 32), 44)
                pygame.draw.circle(town_surf, (58, 118, 52), (2 * ts + 8, by + 32), 38)

        # 8. Directional Bone Signpost at West Entrance leading to Wild Camp (col 1, row 18)
        sign_surf = pygame.Surface((84, 56), pygame.SRCALPHA)
        pygame.draw.rect(sign_surf, (95, 58, 28), (38, 24, 8, 30))
        pygame.draw.rect(sign_surf, (168, 118, 72), (2, 4, 80, 28), border_radius=4)
        pygame.draw.rect(sign_surf, (82, 48, 28), (2, 4, 80, 28), 2, border_radius=4)
        font_tiny = pygame.font.SysFont("dejavusans", 9, bold=True)
        txt = font_tiny.render("⬅ Khai Hoang", True, (255, 245, 215))
        sign_surf.blit(txt, (42 - txt.get_width() // 2, 10))
        town_surf.blit(sign_surf, (1 * ts + 6, 18 * ts + 8))

        return town_surf, lamp_positions

    @staticmethod
    def enhance_farm_composite(base_comp, ts, fonts=None):
        """
        Enhances the raw world_composite into an authentic prehistoric campsite and wilderness:
        Cleans the old farmhouse area into a primeval campsite clearing,
        crafts pointed wooden stake palisades, primitive log pier & bamboo raft,
        woven willow feeding troughs, prehistoric cliff cave paintings, and directional bone signpost.
        """
        comp = base_comp.copy()
        GRASS_BASE = (192, 212, 112)
        WATER_BASE = (155, 212, 195)

        def safe_load(path):
            img = pygame.image.load(path)
            try:
                return img.convert_alpha()
            except Exception:
                return img

        # Prehistoric Tileset Sprites
        grass_tile_p = "assets/tiles_extracted/tile_r2_c2.png"
        grass_tile = safe_load(grass_tile_p) if os.path.exists(grass_tile_p) else None
        dirt_tile_p = "assets/tiles_extracted/tile_r0_c2.png"
        dirt_tile = safe_load(dirt_tile_p) if os.path.exists(dirt_tile_p) else None
        bone_prop_p = "assets/tiles_extracted/tile_r8_c7.png"
        bone_prop = safe_load(bone_prop_p) if os.path.exists(bone_prop_p) else None
        mush_prop_p = "assets/tiles_extracted/tile_r8_c8.png"
        mush_prop = safe_load(mush_prop_p) if os.path.exists(mush_prop_p) else None

        # -------------------------------------------------------------
        # 0. CLEAN UP OLD HOUSE AREA INTO PRIMEVAL CAMPSITE CLEARING
        # (Cols 18..28, Rows 18..26)
        # -------------------------------------------------------------
        for c in range(18, 29):
            for r in range(18, 27):
                if grass_tile:
                    comp.blit(grass_tile, (c * ts, r * ts))
                else:
                    pygame.draw.rect(comp, (116, 168, 86), (c * ts, r * ts, ts, ts))

        # Campsite central beaten earth footprint
        for c in range(20, 27):
            for r in range(20, 25):
                if dirt_tile:
                    comp.blit(dirt_tile, (c * ts, r * ts))
                else:
                    pygame.draw.rect(comp, (156, 108, 68), (c * ts, r * ts, ts, ts))

        # Scattered campfire embers, bones, and mushrooms around campsite clearing
        if bone_prop:
            comp.blit(bone_prop, (18 * ts + 10, 24 * ts + 10))
            comp.blit(bone_prop, (28 * ts + 15, 19 * ts + 20))
        if mush_prop:
            comp.blit(mush_prop, (19 * ts + 20, 18 * ts + 10))
            comp.blit(mush_prop, (27 * ts + 30, 25 * ts + 15))

        # -------------------------------------------------------------
        # 1. CLEAN UP PASTURE & POINTED WOODEN STAKE PALISADE
        # (Cols 10..18, Rows 5..10)
        # -------------------------------------------------------------
        for c in range(11, 19):
            for r in range(6, 10):
                pygame.draw.rect(comp, (116, 168, 86), (c * ts, r * ts, ts, ts))
                for _ in range(3):
                    tx = c * ts + random.randint(8, 56)
                    ty = r * ts + random.randint(8, 56)
                    pygame.draw.line(comp, (95, 148, 65), (tx, ty), (tx, ty - 4), 2)

        for c in range(10, 19):
            pygame.draw.rect(comp, (116, 168, 86), (c * ts, 5 * ts + 20, ts, 44))

        # Pointed wooden stake palisade fencing (Primitive logs with sharpened tops)
        def draw_log_stake(surface, sx, sy):
            pygame.draw.line(surface, (95, 58, 28), (sx, sy + 58), (sx, sy + 14), 8)
            pygame.draw.line(surface, (145, 92, 48), (sx - 1, sy + 56), (sx - 1, sy + 16), 3)
            # Sharpened point
            pygame.draw.polygon(surface, (185, 125, 75), [(sx - 4, sy + 14), (sx, sy + 2), (sx + 4, sy + 14)])
            # Rawhide lashing
            pygame.draw.line(surface, (215, 180, 120), (sx - 4, sy + 28), (sx + 4, sy + 28), 2)

        # Top palisade (row 5)
        for cx in range(10 * ts, 19 * ts, 16):
            draw_log_stake(comp, cx, 5 * ts)
        # Left palisade (col 10)
        for ry in range(5 * ts, 11 * ts, 16):
            draw_log_stake(comp, 10 * ts, ry)
        # Right palisade (col 18)
        for ry in range(5 * ts, 11 * ts, 16):
            draw_log_stake(comp, 18 * ts + 48, ry)
        # Bottom palisade with entrance gap at col 14
        for cx in range(10 * ts, 14 * ts - 16, 16):
            draw_log_stake(comp, cx, 10 * ts + 32)
        for cx in range(15 * ts + 16, 19 * ts, 16):
            draw_log_stake(comp, cx, 10 * ts + 32)

        # Woven Willow Feeding Troughs
        # Trough 1 at (col 11, row 8)
        hay_trough = pygame.Surface((76, 40), pygame.SRCALPHA)
        pygame.draw.rect(hay_trough, (82, 52, 26), (0, 0, 76, 40), border_radius=4)
        pygame.draw.rect(hay_trough, (128, 85, 45), (4, 4, 68, 32), border_radius=2)
        for hy in range(8, 32, 6):
            pygame.draw.line(hay_trough, (225, 195, 75), (8, hy), (64, hy), 4)
            pygame.draw.line(hay_trough, (185, 150, 45), (12, hy + 2), (60, hy + 2), 2)
        comp.blit(hay_trough, (11 * ts + 10, 8 * ts + 12))

        # Water trough at (col 17, row 8)
        water_trough = pygame.Surface((54, 40), pygame.SRCALPHA)
        pygame.draw.rect(water_trough, (82, 52, 26), (0, 0, 54, 40), border_radius=4)
        pygame.draw.rect(water_trough, (105, 175, 210), (4, 4, 46, 32), border_radius=2)
        pygame.draw.line(water_trough, (190, 235, 255), (8, 10), (42, 10), 2)
        comp.blit(water_trough, (17 * ts + 6, 8 * ts + 12))

        # -------------------------------------------------------------
        # 2. CLEAN UP POND & ROUNDED PREHISTORIC SHORELINES
        # (Cols 29..34, Rows 7..12)
        # -------------------------------------------------------------
        for c in range(29, 35):
            for r in range(7, 13):
                pygame.draw.rect(comp, WATER_BASE, (c * ts, r * ts, ts, ts))
                pygame.draw.line(comp, (135, 198, 182), (c * ts + 10, r * ts + 20), (c * ts + 38, r * ts + 20), 2)
                pygame.draw.line(comp, (175, 228, 210), (c * ts + 26, r * ts + 44), (c * ts + 54, r * ts + 44), 2)

        # Round pond 4 corners
        pygame.draw.circle(comp, (116, 168, 86), (29 * ts, 7 * ts), 48)
        pygame.draw.circle(comp, (116, 168, 86), (35 * ts, 7 * ts), 48)
        pygame.draw.circle(comp, (116, 168, 86), (29 * ts, 13 * ts), 48)
        pygame.draw.circle(comp, (116, 168, 86), (35 * ts, 13 * ts), 48)

        # Shoreline edges & shadows
        for c in range(29, 35):
            pygame.draw.line(comp, (135, 172, 75), (c * ts, 7 * ts + 6), ((c + 1) * ts, 7 * ts + 6), 5)
            pygame.draw.line(comp, (105, 142, 60), (c * ts, 7 * ts + 10), ((c + 1) * ts, 7 * ts + 10), 3)

        # Water decs on pond
        wdec_path = "assets/pydew/environment/Water Decoration.png"
        if os.path.exists(wdec_path):
            w_sheet = safe_load(wdec_path)
            w_pebble = w_sheet.subsurface(pygame.Rect(64, 0, 64, 64))
            w_lily = w_sheet.subsurface(pygame.Rect(192, 0, 64, 64))
            comp.blit(w_lily, (30 * ts + 20, 8 * ts + 16))
            comp.blit(w_pebble, (33 * ts + 24, 7 * ts + 40))
            comp.blit(w_lily, (33 * ts + 12, 10 * ts + 22))
            comp.blit(w_pebble, (29 * ts + 36, 11 * ts + 16))

        # -------------------------------------------------------------
        # 3. RIVER BANK, PRIMITIVE LOG PIER & BAMBOO RAFT
        # -------------------------------------------------------------
        # Clean grass bank near dock
        for c in range(41, 45):
            for r in range(34, 38):
                pygame.draw.rect(comp, (116, 168, 86), (c * ts, r * ts, ts, ts))
                for _ in range(4):
                    tx = c * ts + random.randint(8, 56)
                    ty = r * ts + random.randint(8, 56)
                    pygame.draw.line(comp, (95, 148, 65), (tx, ty), (tx, ty - 4), 2)

        # North bank of river
        for c in range(8, 41):
            pygame.draw.line(comp, (135, 172, 75), (c * ts, 34 * ts), ((c + 1) * ts, 34 * ts), 4)
            pygame.draw.line(comp, (105, 142, 60), (c * ts, 34 * ts + 4), ((c + 1) * ts, 34 * ts + 4), 2)

        # Primitive Log Pier & Bamboo Raft (cols 38..40, row 35)
        # Pier logs
        pier_w = 3 * ts
        pygame.draw.rect(comp, (0, 0, 0, 70), (38 * ts + 4, 35 * ts + 50, pier_w, 20))
        for ly in range(35 * ts + 4, 35 * ts + 52, 12):
            pygame.draw.rect(comp, (110, 68, 38), (38 * ts + 4, ly, pier_w, 10), border_radius=3)
            pygame.draw.rect(comp, (155, 102, 56), (38 * ts + 4, ly + 2, pier_w, 6), border_radius=2)
            # Log ends
            pygame.draw.circle(comp, (175, 125, 75), (38 * ts + 6, ly + 5), 4)
            pygame.draw.circle(comp, (175, 125, 75), (38 * ts + pier_w - 6, ly + 5), 4)

        # Bamboo Raft moored beside pier
        raft_x = 39 * ts
        raft_y = 36 * ts + 12
        pygame.draw.rect(comp, (0, 0, 0, 60), (raft_x - 4, raft_y + 4, 88, 48), border_radius=6)
        for rx in range(raft_x, raft_x + 84, 12):
            pygame.draw.rect(comp, (170, 155, 70), (rx, raft_y, 10, 44), border_radius=4)
            pygame.draw.line(comp, (120, 105, 40), (rx, raft_y + 10), (rx + 10, raft_y + 10), 2)
            pygame.draw.line(comp, (120, 105, 40), (rx, raft_y + 34), (rx + 10, raft_y + 34), 2)

        # -------------------------------------------------------------
        # 4. NORTH MOUNTAIN CLIFFS & PREHISTORIC CAVE PAINTINGS
        # -------------------------------------------------------------
        hills_path = "assets/pydew/environment/Hills.png"
        if os.path.exists(hills_path):
            h_sheet = safe_load(hills_path)
            cliff_top = h_sheet.subsurface(pygame.Rect(128, 0, 64, 64))
            cliff_face = h_sheet.subsurface(pygame.Rect(128, 128, 64, 64))
            for c in range(0, 50):
                comp.blit(cliff_top, (c * ts, 0))
                comp.blit(cliff_face, (c * ts, 1 * ts))

        # Red Ochre Prehistoric Cave Paintings on Cliff Face (Cols 4..46)
        paintings = [
            # Mammoth silhouette at col 6
            (6 * ts + 12, 1 * ts + 18, "mammoth"),
            # Running Bison at col 16
            (16 * ts + 18, 1 * ts + 20, "bison"),
            # Spear Hunters at col 26
            (26 * ts + 10, 1 * ts + 16, "hunters"),
            # Handprints & Sun glyph at col 36
            (36 * ts + 24, 1 * ts + 18, "sun")
        ]
        OCHRE = (185, 48, 38)
        OCHRE_LIGHT = (215, 82, 65)

        for px, py, p_type in paintings:
            if p_type == "mammoth":
                # Mammoth body & hump
                pygame.draw.ellipse(comp, OCHRE, (px, py, 38, 26))
                pygame.draw.circle(comp, OCHRE, (px + 6, py + 8), 10)
                # Curved tusks
                pygame.draw.arc(comp, OCHRE_LIGHT, (px - 10, py + 6, 20, 20), 0, math.pi * 0.8, 3)
                # Trunk
                pygame.draw.line(comp, OCHRE, (px + 2, py + 14), (px - 4, py + 26), 3)
                # Legs
                pygame.draw.line(comp, OCHRE, (px + 10, py + 24), (px + 10, py + 34), 4)
                pygame.draw.line(comp, OCHRE, (px + 28, py + 24), (px + 28, py + 34), 4)
            elif p_type == "bison":
                # Running bison
                pygame.draw.ellipse(comp, OCHRE, (px, py + 4, 34, 20))
                pygame.draw.circle(comp, OCHRE, (px + 4, py + 8), 8)
                # Horns
                pygame.draw.arc(comp, OCHRE_LIGHT, (px - 2, py - 2, 12, 12), math.pi * 0.2, math.pi * 0.9, 2)
                # Running legs
                pygame.draw.line(comp, OCHRE, (px + 8, py + 20), (px + 2, py + 30), 3)
                pygame.draw.line(comp, OCHRE, (px + 26, py + 20), (px + 32, py + 28), 3)
            elif p_type == "hunters":
                # 2 stick figure hunters with spears
                for h_off in [0, 22]:
                    hx = px + h_off
                    pygame.draw.circle(comp, OCHRE, (hx, py + 4), 4)
                    pygame.draw.line(comp, OCHRE, (hx, py + 8), (hx, py + 22), 3)
                    pygame.draw.line(comp, OCHRE, (hx, py + 22), (hx - 4, py + 32), 2)
                    pygame.draw.line(comp, OCHRE, (hx, py + 22), (hx + 4, py + 32), 2)
                    # Raised spear
                    pygame.draw.line(comp, OCHRE_LIGHT, (hx - 8, py + 20), (hx + 14, py - 4), 2)
            elif p_type == "sun":
                # Sun & Spiral symbol
                pygame.draw.circle(comp, OCHRE, (px + 12, py + 12), 10, 2)
                pygame.draw.circle(comp, OCHRE, (px + 12, py + 12), 4)
                for ang in range(0, 360, 45):
                    rad = math.radians(ang)
                    sx1 = int(px + 12 + math.cos(rad) * 12)
                    sy1 = int(py + 12 + math.sin(rad) * 12)
                    sx2 = int(px + 12 + math.cos(rad) * 18)
                    sy2 = int(py + 12 + math.sin(rad) * 18)
                    pygame.draw.line(comp, OCHRE, (sx1, sy1), (sx2, sy2), 2)

        # Prehistoric valley pines
        tree_med_path = "assets/pydew/objects/tree_medium.png"
        tree_sm_path = "assets/pydew/objects/tree_small.png"
        if os.path.exists(tree_med_path) and os.path.exists(tree_sm_path):
            t_med = safe_load(tree_med_path)
            t_sm = safe_load(tree_sm_path)
            random.seed(42)
            for c in range(0, 50, 2):
                t_img = t_med if (c % 4 == 0) else t_sm
                ty = random.choice([0, 1 * ts - 20])
                shadow_w = 70 if t_img == t_med else 45
                t_shad = pygame.Surface((shadow_w, 20), pygame.SRCALPHA)
                pygame.draw.ellipse(t_shad, (0, 0, 0, 70), (0, 0, shadow_w, 20))
                comp.blit(t_shad, (c * ts + 10, ty + 100))
                comp.blit(t_img, (c * ts, ty))

        # Directional Signpost at East Road (col 44, row 18)
        sign_surf = pygame.Surface((84, 56), pygame.SRCALPHA)
        pygame.draw.rect(sign_surf, (95, 58, 28), (38, 24, 8, 30))
        pygame.draw.rect(sign_surf, (168, 118, 72), (2, 4, 80, 28), border_radius=4)
        pygame.draw.rect(sign_surf, (82, 48, 28), (2, 4, 80, 28), 2, border_radius=4)
        font_tiny = pygame.font.SysFont("dejavusans", 9, bold=True)
        txt = font_tiny.render("Bản Doanh ➡", True, (255, 245, 215))
        sign_surf.blit(txt, (42 - txt.get_width() // 2, 10))
        comp.blit(sign_surf, (44 * ts + 10, 18 * ts + 10))

        # =========================================================================
        # 6. STARTING BOTANICAL FORAGING GARDEN & WOODCUTTING PROGRESSION
        # =========================================================================
        flora_specs = [
            ("assets/flora/bramble_ripe.png", (52, 50), [(20 * ts + 8, 24 * ts + 12), (27 * ts + 4, 25 * ts + 8)]),
            ("assets/flora/einkorn_ripe.png", (54, 56), [(21 * ts + 14, 26 * ts + 6), (22 * ts + 20, 27 * ts + 4)]),
            ("assets/flora/burdock_ripe.png", (50, 52), [(25 * ts + 12, 23 * ts + 14)]),
            ("assets/flora/cattail_ripe.png", (50, 56), [(29 * ts + 14, 11 * ts + 10), (30 * ts + 16, 12 * ts + 16)]),
            ("assets/flora/mushroom_ripe.png", (52, 54), [(19 * ts + 14, 22 * ts + 8)]),
            ("assets/flora/herb_ripe.png", (48, 52), [(24 * ts + 16, 21 * ts + 12)]),
            ("assets/trees/timber_logs_stack.png", (48, 48), [(21 * ts + 10, 20 * ts + 16)]),
            ("assets/trees/tree_stump.png", (42, 44), [(19 * ts + 24, 20 * ts + 10)]),
        ]

        for path, (fw, fh), coords in flora_specs:
            if os.path.exists(path):
                raw_f = safe_load(path)
                scaled_f = pygame.transform.smoothscale(raw_f, (fw, fh))
                for fx, fy in coords:
                    # Ground shadow under botanical flora
                    sh_surf = pygame.Surface((fw + 8, 14), pygame.SRCALPHA)
                    pygame.draw.ellipse(sh_surf, (0, 0, 0, 65), (0, 0, fw + 8, 14))
                    comp.blit(sh_surf, (fx - 4, fy + fh - 10))
                    comp.blit(scaled_f, (fx, fy))

        return comp

    @staticmethod
    def load_environmental_props():
        """Loads water decorations, bridge sprites, and plant decorations from assets."""
        props = {}
        def safe_load(path):
            img = pygame.image.load(path)
            try:
                return img.convert_alpha()
            except Exception:
                return img

        # 1. Water Decorations from assets/pydew/environment/Water Decoration.png (256x64 -> 4 sprites of 64x64)
        wdec_path = "assets/pydew/environment/Water Decoration.png"
        if os.path.exists(wdec_path):
            sheet = safe_load(wdec_path)
            for i in range(4):
                props[f"water_dec_{i}"] = sheet.subsurface(pygame.Rect(i * 64, 0, 64, 64))

        # 2. Bridge from assets/pydew/environment/Bridge.png (320x192)
        bridge_path = "assets/pydew/environment/Bridge.png"
        if os.path.exists(bridge_path):
            b_sheet = safe_load(bridge_path)
            # Horizontal bridge (Rect 136, 0, 172, 64) -> scale to 192 x 64 (3 tiles wide)
            h_sub = b_sheet.subsurface(pygame.Rect(136, 0, 172, 64))
            props["bridge_horizontal"] = pygame.transform.scale(h_sub, (192, 64))
            # Vertical bridge (Rect 0, 8, 64, 172) -> scale to 64 x 192 (3 tiles high)
            v_sub = b_sheet.subsurface(pygame.Rect(0, 8, 64, 172))
            props["bridge_vertical"] = pygame.transform.scale(v_sub, (64, 192))

        # 3. Wooden Fences from assets/pydew/environment/Fences.png (256x256)
        fence_path = "assets/pydew/environment/Fences.png"
        if os.path.exists(fence_path):
            f_sheet = safe_load(fence_path)
            props["fence_h"] = f_sheet.subsurface(pygame.Rect(128, 192, 64, 64))
            props["fence_v"] = f_sheet.subsurface(pygame.Rect(0, 64, 64, 64))
            props["fence_tl"] = f_sheet.subsurface(pygame.Rect(64, 0, 64, 64))
            props["fence_tr"] = f_sheet.subsurface(pygame.Rect(192, 0, 64, 64))
            props["fence_bl"] = f_sheet.subsurface(pygame.Rect(64, 128, 64, 64))
            props["fence_br"] = f_sheet.subsurface(pygame.Rect(192, 128, 64, 64))
            props["fence_post"] = f_sheet.subsurface(pygame.Rect(0, 192, 64, 64))

        # 4. Wildflower / Plant Decorations from assets/pydew/environment/Plant Decoration.png (320x128)
        plant_path = "assets/pydew/environment/Plant Decoration.png"
        if os.path.exists(plant_path):
            p_sheet = safe_load(plant_path)
            for r in range(2):
                for c in range(5):
                    sub = p_sheet.subsurface(pygame.Rect(c * 64, r * 64, 64, 64))
                    if pygame.mask.from_surface(sub).count() > 50:
                        props[f"plant_dec_{r * 5 + c}"] = sub

        return props

