import os, sys, math
sys.path.insert(0, os.path.abspath('libs'))
sys.path.insert(0, os.path.abspath('.'))
import pygame

pygame.init()
pygame.display.set_mode((1, 1))

out_dir = "assets/tactical_extracted"

def feather_surface(surf, border_fade=12):
    w, h = surf.get_size()
    alpha_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    alpha_surf.blit(surf, (0, 0))
    # Apply soft vignette around outer edges
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

for fname in ["cave_hearth.png", "grass_tent_1.png", "grass_tent_2.png", 
              "pelt_tipi_1.png", "pelt_tipi_2.png", "campfire.png"]:
    p = os.path.join(out_dir, fname)
    if os.path.exists(p):
        raw = pygame.image.load(p).convert_alpha()
        feathered = feather_surface(raw, border_fade=10)
        pygame.image.save(feathered, p)
        print(f"Feathered {fname}")

print("Feathering complete!")
