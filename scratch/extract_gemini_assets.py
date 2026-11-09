import os, sys
sys.path.insert(0, os.path.abspath('libs'))
sys.path.insert(0, os.path.abspath('.'))
import pygame

pygame.init()
pygame.display.set_mode((1, 1))

def feather_surface(surf, border_fade=8):
    w, h = surf.get_size()
    alpha_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    alpha_surf.blit(surf, (0, 0))
    for y in range(h):
        for x in range(w):
            dist_x = min(x, w - 1 - x)
            dist_y = min(y, h - 1 - y)
            min_dist = min(dist_x, dist_y)
            if min_dist < border_fade:
                factor = min_dist / float(border_fade)
                r, g, b, a = alpha_surf.get_at((x, y))
                new_a = int(a * factor)
                alpha_surf.set_at((x, y), (r, g, b, new_a))
    return alpha_surf

os.makedirs("assets/ui/icons", exist_ok=True)
os.makedirs("assets/units", exist_ok=True)
os.makedirs("assets/wildlife", exist_ok=True)
os.makedirs("assets/buildings", exist_ok=True)

# =============================================================================
# 1. UI & HUD ASSETS (ref_ui_hud_kit.jpg: 1024x572)
# =============================================================================
ui_img = pygame.image.load("assets/sprites/ref_ui_hud_kit.jpg")

# Circular Minimap Frame (top right: x: 720..980, y: 35..295, approx 250x250)
mini_frame_crop = (728, 36, 252, 252)
mini_surf = pygame.Surface((mini_frame_crop[2], mini_frame_crop[3]))
mini_surf.blit(ui_img, (0, 0), mini_frame_crop)
feathered_mini = feather_surface(mini_surf, border_fade=6)
pygame.image.save(feathered_mini, "assets/ui/minimap_bone_frame.png")

# Stone & Leather Control Panel Frame (top left: x: 20..350, y: 35..295)
panel_crop = (24, 38, 328, 250)
panel_surf = pygame.Surface((panel_crop[2], panel_crop[3]))
panel_surf.blit(ui_img, (0, 0), panel_crop)
pygame.image.save(panel_surf, "assets/ui/stone_panel_frame.png")

# Unit Info Card Frame (top center: x: 370..700, y: 35..295)
unit_card_crop = (372, 38, 324, 250)
uc_surf = pygame.Surface((unit_card_crop[2], unit_card_crop[3]))
uc_surf.blit(ui_img, (0, 0), unit_card_crop)
pygame.image.save(uc_surf, "assets/ui/unit_card_frame.png")

# 6 Resource Icons (Bottom Left: y: 320..560)
# Meat: (25, 325, 100, 100), Berries: (140, 325, 100, 100), Flint: (255, 325, 100, 100), Wood: (370, 325, 100, 100)
# Ivory/Tusk: (25, 440, 100, 100), Fire/Warmth: (140, 440, 100, 100)
res_boxes = {
    "icon_meat": (24, 322, 100, 104),
    "icon_berries": (140, 322, 100, 104),
    "icon_flint": (256, 322, 100, 104),
    "icon_wood": (372, 322, 100, 104),
    "icon_ivory": (24, 436, 100, 104),
    "icon_warmth": (140, 436, 100, 104),
}
for name, box in res_boxes.items():
    s = pygame.Surface((box[2], box[3]))
    s.blit(ui_img, (0, 0), box)
    scaled = pygame.transform.smoothscale(s, (48, 48))
    pygame.image.save(scaled, f"assets/ui/icons/{name}.png")

# 6 Lascaux Cave-Painting Tech Icons (Bottom Right: y: 320..560)
# Tech 1 (Fire Mastery): (625, 322, 100, 104), Tech 2 (Flintknapping): (745, 322, 100, 104), Tech 3 (Boar Hunting): (865, 322, 100, 104)
# Tech 4 (Hide Clothing): (625, 436, 100, 104), Tech 5 (Megalithic Rituals): (745, 436, 100, 104), Tech 6 (Mammoth Domestication): (865, 436, 100, 104)
tech_boxes = {
    "tech_fire": (624, 322, 102, 104),
    "tech_flintknapping": (744, 322, 102, 104),
    "tech_hunting": (864, 322, 102, 104),
    "tech_clothing": (624, 436, 102, 104),
    "tech_rituals": (744, 436, 102, 104),
    "tech_domestication": (864, 436, 102, 104),
}
for name, box in tech_boxes.items():
    s = pygame.Surface((box[2], box[3]))
    s.blit(ui_img, (0, 0), box)
    scaled = pygame.transform.smoothscale(s, (64, 64))
    pygame.image.save(scaled, f"assets/ui/icons/{name}.png")

print("Saved all UI frames and icons!")

# =============================================================================
# 2. BUILDINGS ASSETS (ref_buildings_spritesheet.jpg: 1024x572)
# =============================================================================
bldg_img = pygame.image.load("assets/sprites/ref_buildings_spritesheet.jpg")
bldg_crops = {
    "cave_hearth_handprints": (30, 60, 310, 240),
    "tipis_and_thatch_hut": (355, 25, 310, 265),
    "flintknapping_workshop": (685, 60, 320, 220),
    "meat_smoking_racks": (25, 315, 305, 230),
    "megalithic_shrine": (360, 315, 305, 230),
    "palisade_gate_and_tower": (685, 305, 320, 250),
}
for name, box in bldg_crops.items():
    s = pygame.Surface((box[2], box[3]))
    s.blit(bldg_img, (0, 0), box)
    feathered = feather_surface(s, border_fade=8)
    pygame.image.save(feathered, f"assets/buildings/{name}.png")

print("Saved all building structures!")

# =============================================================================
# 3. MEGAFAUNA & WILDLIFE (ref_wildlife_spritesheet.jpg: 1024x572)
# =============================================================================
wild_img = pygame.image.load("assets/sprites/ref_wildlife_spritesheet.jpg")
beast_crops = {
    "mammoth_idle": (20, 30, 135, 125),
    "mammoth_walk": (165, 30, 140, 125),
    "sabertooth_pounce": (535, 55, 125, 80),
    "sabertooth_stalk": (690, 65, 125, 75),
    "bison_graze": (24, 168, 125, 95),
    "bison_charge": (685, 165, 130, 95),
    "cave_bear_stand": (350, 280, 95, 120),
    "cave_bear_walk": (32, 290, 115, 85),
    "dire_wolf_howl": (535, 290, 115, 90),
    "dire_wolf_run": (690, 300, 125, 80),
    "wild_boar": (40, 405, 100, 75),
    "marsh_crocodile": (20, 490, 145, 75),
    "fish_shoal": (540, 500, 125, 60),
}
for name, box in beast_crops.items():
    s = pygame.Surface((box[2], box[3]))
    s.blit(wild_img, (0, 0), box)
    feathered = feather_surface(s, border_fade=6)
    pygame.image.save(feathered, f"assets/wildlife/{name}.png")

print("Saved all megafauna sprites!")

# =============================================================================
# 4. TRIBAL UNITS (ref_units_spritesheet.jpg: 1024x572)
# =============================================================================
unit_img = pygame.image.load("assets/sprites/ref_units_spritesheet.jpg")
# Row 0: Gatherer/Builder, Row 1: Spear Hunter, Row 2: Mammoth Warrior, Row 3: Shaman
# Cell w is approx 102.4, h is approx 143
unit_archetypes = {
    "gatherer_idle": (24, 25, 75, 115),
    "gatherer_carry_wood": (118, 25, 75, 115),
    "gatherer_chop": (420, 25, 75, 115),
    "gatherer_basket": (525, 25, 75, 115),
    "spear_hunter_aim": (108, 165, 85, 115),
    "spear_hunter_thrust": (410, 165, 95, 115),
    "spear_hunter_throw": (610, 165, 95, 115),
    "bone_warrior_guard": (15, 305, 90, 125),
    "bone_warrior_shield": (110, 305, 90, 125),
    "bone_warrior_swing": (310, 305, 90, 125),
    "shaman_staff": (20, 445, 85, 120),
    "shaman_fire_ritual": (410, 440, 95, 125),
    "shaman_gourd": (520, 445, 85, 120),
}
for name, box in unit_archetypes.items():
    s = pygame.Surface((box[2], box[3]))
    s.blit(unit_img, (0, 0), box)
    feathered = feather_surface(s, border_fade=5)
    pygame.image.save(feathered, f"assets/units/{name}.png")

print("Saved all tribal unit sprites!")
print("ALL NEW SPRITES EXTRACTED & PREPARED SUCCESSFULLY!")
