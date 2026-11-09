"""
Visual Enhancer for Green Valley Tales (GCVL).
Provides reusable, high-performance visual polish tools:
- Pre-rendered ellipse drop shadows for all 2.5D world entities (Player, Animals, NPCs, Obstacles)
- Cozy Wooden / Parchment UI panels (Stardew Valley & Sprout Lands aesthetic)
- Crisp drop-shadow pixel typography
- Cached multi-ring radial glow halos for warm point lights
"""

import pygame
import math


class VisualEnhancer:
    _shadow_cache = {}
    _glow_cache = {}

    @classmethod
    def get_shadow_surface(cls, width: int, height: int, color=(15, 20, 35, 95)) -> pygame.Surface:
        """Returns a cached ellipse drop-shadow surface."""
        w = max(2, int(width))
        h = max(2, int(height))
        key = (w, h, color)
        if key not in cls._shadow_cache:
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, color, (0, 0, w, h))
            cls._shadow_cache[key] = surf
        return cls._shadow_cache[key]

    @classmethod
    def draw_drop_shadow(cls, surface: pygame.Surface, center_pos: tuple, width: int, height: int, color=(15, 20, 35, 95)):
        """
        Draws a soft ellipse drop shadow centered at center_pos (world screen coordinates).
        Cached to guarantee 60 FPS without per-frame surface creation.
        """
        shadow_surf = cls.get_shadow_surface(width, height, color)
        topleft = (int(center_pos[0] - width // 2), int(center_pos[1] - height // 2))
        surface.blit(shadow_surf, topleft)

    @staticmethod
    def draw_cozy_panel(surface: pygame.Surface, rect: pygame.Rect, border_radius: int = 10,
                        bg_color=(245, 233, 206), wood_border=(92, 58, 33), 
                        inner_wood=(181, 131, 90), highlight=(255, 248, 231), shadow_alpha=110):
        """
        Draws a warm cozy wooden/parchment panel (Stardew Valley / Sprout Lands style).
        Replaces flat plain rectangles with authentic warm tactile frames.
        """
        # 1. Drop shadow under panel
        shadow_rect = rect.move(0, 4)
        shadow_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, shadow_alpha), (0, 0, rect.width, rect.height), border_radius=border_radius)
        surface.blit(shadow_surf, shadow_rect.topleft)

        # 2. Outer dark wood border
        pygame.draw.rect(surface, wood_border, rect, border_radius=border_radius)

        # 3. Inner lighter wood layer
        if rect.width > 12 and rect.height > 12:
            inner_wood_rect = rect.inflate(-6, -6)
            pygame.draw.rect(surface, inner_wood, inner_wood_rect, border_radius=max(2, border_radius - 2))

        # 4. Parchment cream paper core
        if rect.width > 24 and rect.height > 24:
            paper_rect = rect.inflate(-12, -12)
            pygame.draw.rect(surface, bg_color, paper_rect, border_radius=max(2, border_radius - 4))

            # 5. Thin 3D pixel highlight rim
            pygame.draw.rect(surface, highlight, paper_rect, width=2, border_radius=max(2, border_radius - 4))

    @staticmethod
    def draw_text_with_shadow(surface: pygame.Surface, text: str, font: pygame.font.Font,
                              pos: tuple, text_color=(74, 48, 32), shadow_color=(210, 190, 160), 
                              offset=(1, 1), antialias=True) -> pygame.Rect:
        """
        Renders crisp text with a distinct drop shadow for readable, tactile typography.
        """
        shadow_surf = font.render(text, antialias, shadow_color)
        text_surf = font.render(text, antialias, text_color)
        
        surface.blit(shadow_surf, (pos[0] + offset[0], pos[1] + offset[1]))
        return surface.blit(text_surf, pos)

    @classmethod
    def get_radial_glow(cls, radius: int, color=(255, 220, 150)) -> pygame.Surface:
        """
        Generates and caches smooth multi-ring radial glow texture for warm point lights.
        """
        r = max(4, int(radius))
        key = (r, color[:3])
        if key not in cls._glow_cache:
            size = r * 2
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            steps = max(8, r // 4)
            for i in range(steps, 0, -1):
                curr_r = int(r * (i / steps))
                # Smooth quadratic falloff
                falloff = (1.0 - (i / steps)) ** 1.6
                alpha = int(255 * falloff)
                ring_color = (*color[:3], alpha)
                pygame.draw.circle(surf, ring_color, (r, r), curr_r)
            cls._glow_cache[key] = surf
        return cls._glow_cache[key]
