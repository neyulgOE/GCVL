"""OpenGL 3D runtime for Stone Age: Primeval World.

This renderer deliberately keeps the existing procedural world and wildlife
simulation, but replaces the flat Pygame presentation with a perspective
camera, a heightmap terrain mesh, depth buffering and real 3D cliff faces.
"""

import math
import os
from pathlib import Path

import pyglet

if os.environ.get("GCVL_HEADLESS") == "1":
    pyglet.options["headless"] = True

from pyglet import gl
from pyglet.gl import glu
from pyglet.window import key, mouse

from src.settings import MAP_COLS, MAP_ROWS, TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT
from src.world.map_manager import MapManager
from src.world.wildlife_manager import WildlifeManager


class Game3D:
    """Perspective 3D spectator view over the procedural prehistoric world."""

    TILE_WORLD_SIZE = 2.0
    # The source heightmap is normalized; this scale keeps the valley readable
    # as terrain instead of turning every tier transition into a canyon.
    HEIGHT_WORLD_SCALE = 6.0
    WATER_LEVEL = 0.95
    GROUND_TEXTURE_SIZE = 2048

    TERRAIN_COLORS = {
        "steppe_meadow": (0.30, 0.52, 0.20),
        "forest_humus": (0.12, 0.30, 0.13),
        "riparian_mud": (0.34, 0.29, 0.19),
        "point_bar_sand": (0.67, 0.56, 0.34),
        "settlement_loam": (0.70, 0.58, 0.34),
        "scree_talus": (0.38, 0.38, 0.34),
        "water": (0.07, 0.27, 0.42),
        "bridge_ford": (0.40, 0.40, 0.34),
    }

    BEAST_COLORS = {
        "mammoth": (0.30, 0.20, 0.12),
        "ancient_bison": (0.36, 0.18, 0.08),
        "sabertooth": (0.68, 0.42, 0.12),
        "dire_wolf": (0.30, 0.32, 0.34),
        "giant_deer": (0.52, 0.32, 0.16),
        "cave_bear": (0.28, 0.16, 0.09),
        "wild_boar": (0.38, 0.24, 0.16),
    }

    def __init__(self, width=SCREEN_WIDTH, height=SCREEN_HEIGHT, headless=False):
        if headless:
            pyglet.options["headless"] = True

        self.width = width
        self.height = height
        config = gl.Config(double_buffer=True, depth_size=24)
        self.window = pyglet.window.Window(
            width=width,
            height=height,
            caption="Stone Age: Primeval World - 3D",
            resizable=True,
            visible=not headless,
            config=config,
        )

        self.map_mgr = MapManager()
        self.wildlife_mgr = WildlifeManager(self.map_mgr)
        self.render_heights = self._build_render_heightmap()
        self.keys = key.KeyStateHandler()
        self.window.push_handlers(self.keys)
        self.game_time = 0.0
        self.fps_label = pyglet.text.Label(
            "",
            x=14,
            y=height - 26,
            color=(235, 242, 226, 255),
            font_size=12,
            bold=True,
        )
        self.help_label = pyglet.text.Label(
            "WASD di chuyển | Q/E lên xuống | Chuột phải + kéo xoay | ESC thoát",
            x=14,
            y=12,
            color=(220, 230, 210, 230),
            font_size=11,
        )

        self.cam_x = MAP_COLS * self.TILE_WORLD_SIZE * 0.5
        self.cam_y = 18.0
        self.cam_z = MAP_ROWS * self.TILE_WORLD_SIZE * 0.5 + 34.0
        # Start looking from the south edge toward the map's north (negative Z).
        self.yaw = math.radians(0.0)
        self.pitch = math.radians(-28.0)
        self.mouse_look = False
        self.last_dt = 1.0 / 60.0

        self.window.on_draw = self.on_draw
        self.window.on_resize = self.on_resize
        self.window.on_key_press = self.on_key_press
        self.window.on_key_release = self.on_key_release
        self.window.on_mouse_press = self.on_mouse_press
        self.window.on_mouse_release = self.on_mouse_release
        self.window.on_mouse_drag = self.on_mouse_drag

        pyglet.clock.schedule_interval(self.update, 1.0 / 60.0)
        self._setup_gl()
        self._load_assets()

    def _setup_gl(self):
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LEQUAL)
        gl.glDisable(gl.GL_CULL_FACE)
        gl.glShadeModel(gl.GL_SMOOTH)
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)
        gl.glEnable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_LIGHT0)
        ambient = (gl.GLfloat * 4)(0.34, 0.37, 0.32, 1.0)
        diffuse = (gl.GLfloat * 4)(0.82, 0.78, 0.66, 1.0)
        direction = (gl.GLfloat * 4)(-0.35, 0.85, 0.28, 0.0)
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, ambient)
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, diffuse)
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, direction)
        gl.glTexEnvi(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)
        gl.glClearColor(0.035, 0.055, 0.09, 1.0)

    def _build_render_heightmap(self):
        """Smooth only the display mesh; gameplay collision stays tile-accurate."""
        source = [row[:] for row in self.map_mgr.heightmap]
        for _ in range(2):
            filtered = []
            for row in range(self.map_mgr.rows):
                out_row = []
                for col in range(self.map_mgr.cols):
                    total = 0.0
                    weight_total = 0.0
                    for dr in (-1, 0, 1):
                        rr = max(0, min(self.map_mgr.rows - 1, row + dr))
                        for dc in (-1, 0, 1):
                            cc = max(0, min(self.map_mgr.cols - 1, col + dc))
                            weight = 4.0 if dc == 0 and dr == 0 else (2.0 if dc == 0 or dr == 0 else 1.0)
                            total += source[rr][cc] * weight
                            weight_total += weight
                    smoothed = total / weight_total
                    out_row.append(source[row][col] * 0.30 + smoothed * 0.70)
                filtered.append(out_row)
            source = filtered
        return source

    def _load_assets(self):
        """Load the existing Stone Age PNG pack as OpenGL textures."""
        root = Path(__file__).resolve().parents[2]
        self.asset_root = root / "assets" / "stone_age"
        if not self.asset_root.exists():
            self.asset_root = root / "stone_age_rts_complete_all_in_one_bundle" / "02_SLICED_SPRITES_128_PNG"
        self.textures = {}

        terrain_files = {
            "steppe_meadow": "12_seamless_64x64_terrain_tiles/tile_01_steppe_grass.png",
            "forest_humus": "12_seamless_64x64_terrain_tiles/tile_02_primeval_forest_floor.png",
            "riparian_mud": "12_seamless_64x64_terrain_tiles/tile_07_ancient_swamp_mud.png",
            "point_bar_sand": "12_seamless_64x64_terrain_tiles/tile_04_pebble_river_shore.png",
            "settlement_loam": "12_seamless_64x64_terrain_tiles/tile_04_pebble_river_shore.png",
            "scree_talus": "12_seamless_64x64_terrain_tiles/tile_08_megalithic_granite_rock.png",
            "water": "12_seamless_64x64_terrain_tiles/tile_06_deep_river_water.png",
            "bridge_ford": "12_seamless_64x64_terrain_tiles/tile_05_shallow_ford_water.png",
        }
        self.terrain_textures = {
            name: self._load_texture(path) for name, path in terrain_files.items()
        }
        self.terrain_blend_texture = self._build_terrain_blend_texture(terrain_files)
        self.cliff_texture = self._load_texture(
            "12_seamless_64x64_terrain_tiles/tile_08_megalithic_granite_rock.png"
        )

        def variants(prefix, count):
            return [
                self._load_texture(f"04_prehistoric_trees_and_wood/{prefix}_{i:02d}.png")
                for i in range(1, count + 1)
            ]

        self.tree_textures = {
            "tree_steppe": variants("tree_steppe_oak_pine", 10),
            "tree_forest": variants("tree_primeval_fern_cycad", 10),
            "tree_tundra": variants("tree_tundra_spruce_birch", 10),
            "tree_swamp": [
                self._load_texture("04_prehistoric_trees_and_wood/tree_swamp_mangrove_01.png"),
                self._load_texture("04_prehistoric_trees_and_wood/tree_swamp_mangrove_02.png"),
            ],
        }
        self.flora_textures = {
            "wild_bush": [self._load_texture(f"05_forageable_flora_3stages/flora_berry_bush_stage_{i:02d}.png") for i in (3, 5, 7)],
            "weeds": [self._load_texture(f"05_forageable_flora_3stages/flora_grain_fiber_reed_stage_{i:02d}.png") for i in (3, 5, 7)],
            "prop_mushroom": [self._load_texture(f"05_forageable_flora_3stages/flora_mushroom_herb_stage_{i:02d}.png") for i in (3, 5, 7)],
        }
        self.beast_textures = {
            "mammoth": self._load_texture("02_megafauna_wildlife/wildlife_mammoth_and_smilodon_01.png"),
            "ancient_bison": self._load_texture("02_megafauna_wildlife/wildlife_steppe_bison_01.png"),
            "sabertooth": self._load_texture("02_megafauna_wildlife/wildlife_mammoth_and_smilodon_06.png"),
            "dire_wolf": self._load_texture("02_megafauna_wildlife/wildlife_cavebear_and_direwolf_04.png"),
            "giant_deer": self._load_texture("02_megafauna_wildlife/wildlife_steppe_bison_05.png"),
            "cave_bear": self._load_texture("02_megafauna_wildlife/wildlife_cavebear_and_direwolf_01.png"),
            "wild_boar": self._load_texture("02_megafauna_wildlife/wildlife_wild_boar_01.png"),
        }

    def _build_terrain_blend_texture(self, terrain_files):
        """Bake one continuous splat texture from the existing terrain tiles."""
        try:
            from PIL import Image, ImageDraw, ImageFilter
        except ImportError:
            return None

        size = self.GROUND_TEXTURE_SIZE
        cell_w = max(1, int(round(size / self.map_mgr.cols)))
        cell_h = max(1, int(round(size / self.map_mgr.rows)))
        layers = {}
        masks = {}
        material_order = [
            "steppe_meadow", "forest_humus", "riparian_mud", "point_bar_sand",
            "settlement_loam", "scree_talus", "bridge_ford",
        ]

        for terrain in material_order:
            relative = terrain_files.get(terrain)
            if relative is None:
                continue
            path = self.asset_root / relative
            if not path.exists():
                continue
            tile = Image.open(path).convert("RGB").resize(
                (cell_w, cell_h), Image.Resampling.BILINEAR
            )
            layer = Image.new("RGB", (size, size))
            for row in range(self.map_mgr.rows):
                for col in range(self.map_mgr.cols):
                    layer.paste(tile, (col * cell_w, row * cell_h))
            layers[terrain] = layer

            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            for row in range(self.map_mgr.rows):
                for col in range(self.map_mgr.cols):
                    if self.map_mgr.terrain[row][col] == terrain:
                        x0, y0 = col * cell_w, row * cell_h
                        draw.rectangle((x0, y0, x0 + cell_w, y0 + cell_h), fill=255)
            masks[terrain] = mask.filter(
                ImageFilter.GaussianBlur(radius=max(4, cell_w * 0.55))
            )

        if not layers:
            return None
        base = layers.get("steppe_meadow") or next(iter(layers.values()))
        for terrain in material_order:
            if terrain != "steppe_meadow" and terrain in layers:
                base = Image.composite(layers[terrain], base, masks[terrain])

        texture = pyglet.image.ImageData(
            size, size, "RGB", base.tobytes(), pitch=size * 3
        ).get_texture()
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture.id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        return texture

    def _load_texture(self, relative_path):
        path = self.asset_root / relative_path
        if not path.exists():
            return None
        try:
            texture = pyglet.image.load(str(path)).get_texture()
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture.id)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            return texture
        except Exception:
            return None

    def on_resize(self, width, height):
        self.width = max(1, width)
        self.height = max(1, height)
        gl.glViewport(0, 0, self.width, self.height)
        self.fps_label.y = self.height - 26
        return pyglet.event.EVENT_HANDLED

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE:
            self.window.close()

    def on_key_release(self, symbol, modifiers):
        return None

    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.RIGHT:
            self.mouse_look = True

    def on_mouse_release(self, x, y, button, modifiers):
        if button == mouse.RIGHT:
            self.mouse_look = False

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.mouse_look or buttons & mouse.RIGHT:
            self.yaw += dx * 0.006
            self.pitch = max(math.radians(-80), min(math.radians(-8), self.pitch - dy * 0.004))

    def _look_direction(self):
        cp = math.cos(self.pitch)
        return (
            math.sin(self.yaw) * cp,
            math.sin(self.pitch),
            -math.cos(self.yaw) * cp,
        )

    def update(self, dt):
        self.last_dt = min(0.05, max(0.0, dt))
        self.game_time += self.last_dt
        dx, _, dz = self._look_direction()
        right_x, right_z = math.cos(self.yaw), math.sin(self.yaw)
        speed = 18.0 * self.last_dt
        if self.keys[key.LSHIFT] or self.keys[key.RSHIFT]:
            speed *= 2.5
        if self.keys[key.W]:
            self.cam_x += dx * speed
            self.cam_z += dz * speed
        if self.keys[key.S]:
            self.cam_x -= dx * speed
            self.cam_z -= dz * speed
        if self.keys[key.A]:
            self.cam_x -= right_x * speed
            self.cam_z -= right_z * speed
        if self.keys[key.D]:
            self.cam_x += right_x * speed
            self.cam_z += right_z * speed
        if self.keys[key.Q]:
            self.cam_y += speed
        if self.keys[key.E]:
            self.cam_y -= speed
        self.cam_x = max(-10.0, min(MAP_COLS * self.TILE_WORLD_SIZE + 10.0, self.cam_x))
        self.cam_z = max(-10.0, min(MAP_ROWS * self.TILE_WORLD_SIZE + 10.0, self.cam_z))
        self.cam_y = max(3.0, min(100.0, self.cam_y))

        self.wildlife_mgr.update(self.last_dt, [], None, None)

    def _terrain_y(self, col, row):
        col = max(0, min(self.map_mgr.cols - 1, int(col)))
        row = max(0, min(self.map_mgr.rows - 1, int(row)))
        return self.render_heights[row][col] * self.HEIGHT_WORLD_SCALE

    def _terrain_normal(self, col, row):
        left = self._terrain_y(col - 1, row)
        right = self._terrain_y(col + 1, row)
        back = self._terrain_y(col, row - 1)
        front = self._terrain_y(col, row + 1)
        dx = (right - left) / (2.0 * self.TILE_WORLD_SIZE)
        dz = (front - back) / (2.0 * self.TILE_WORLD_SIZE)
        nx, ny, nz = -dx, 1.0, -dz
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        return nx / length, ny / length, nz / length

    def _tile_color(self, terrain):
        return self.TERRAIN_COLORS.get(terrain, (0.30, 0.40, 0.22))

    @staticmethod
    def _vertex(x, y, z):
        gl.glVertex3f(float(x), float(y), float(z))

    def _draw_terrain_mesh(self):
        s = self.TILE_WORLD_SIZE
        gl.glEnable(gl.GL_TEXTURE_2D)
        texture = self.terrain_blend_texture
        if texture:
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture.id)
            gl.glColor3f(1.0, 1.0, 1.0)
            gl.glBegin(gl.GL_QUADS)
            for row in range(self.map_mgr.rows - 1):
                for col in range(self.map_mgr.cols - 1):
                    x0, x1 = col * s, (col + 1) * s
                    z0, z1 = row * s, (row + 1) * s
                    u0 = col / (self.map_mgr.cols - 1)
                    u1 = (col + 1) / (self.map_mgr.cols - 1)
                    v0 = row / (self.map_mgr.rows - 1)
                    v1 = (row + 1) / (self.map_mgr.rows - 1)
                    vertices = (
                        (col, row, u0, v0, x0, z0),
                        (col + 1, row, u1, v0, x1, z0),
                        (col + 1, row + 1, u1, v1, x1, z1),
                        (col, row + 1, u0, v1, x0, z1),
                    )
                    for vc, vr, u, v, x, z in vertices:
                        gl.glNormal3f(*self._terrain_normal(vc, vr))
                        gl.glTexCoord2f(u, v)
                        self._vertex(x, self._terrain_y(vc, vr), z)
            gl.glEnd()
        else:
            # Fallback for environments without Pillow.
            for row in range(self.map_mgr.rows - 1):
                for col in range(self.map_mgr.cols - 1):
                    terrain = self.map_mgr.terrain[row][col]
                    texture = self.terrain_textures.get(terrain)
                    if texture:
                        gl.glBindTexture(gl.GL_TEXTURE_2D, texture.id)
                        gl.glColor3f(1.0, 1.0, 1.0)
                    else:
                        r, g, b = self._tile_color(terrain)
                        gl.glColor3f(r, g, b)
                    gl.glBegin(gl.GL_QUADS)
                    x0, x1 = col * s, (col + 1) * s
                    z0, z1 = row * s, (row + 1) * s
                    gl.glTexCoord2f(0.0, 0.0); self._vertex(x0, self._terrain_y(col, row), z0)
                    gl.glTexCoord2f(1.0, 0.0); self._vertex(x1, self._terrain_y(col + 1, row), z0)
                    gl.glTexCoord2f(1.0, 1.0); self._vertex(x1, self._terrain_y(col + 1, row + 1), z1)
                    gl.glTexCoord2f(0.0, 1.0); self._vertex(x0, self._terrain_y(col, row + 1), z1)
                    gl.glEnd()
        gl.glDisable(gl.GL_TEXTURE_2D)

    def _draw_water_surface(self):
        texture = self.terrain_textures.get("water")
        gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_TEXTURE_2D)
        if texture:
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture.id)
        gl.glColor3f(1.0, 1.0, 1.0) if texture else gl.glColor3f(0.05, 0.30, 0.52)
        gl.glBegin(gl.GL_QUADS)
        # Build the main river from its continuous centerline instead of
        # drawing one square quad per water tile. This removes the staircase
        # edge while keeping the gameplay water mask unchanged.
        for row in range(self.map_mgr.rows - 1):
            center0 = self.map_mgr.get_river_center_float(row)
            center1 = self.map_mgr.get_river_center_float(row + 1)
            width0 = self.map_mgr.get_river_half_width_float(row)
            width1 = self.map_mgr.get_river_half_width_float(row + 1)
            y0 = self.WATER_LEVEL + math.sin(self.game_time * 1.8 + row * 0.3) * 0.025
            y1 = self.WATER_LEVEL + math.sin(self.game_time * 1.8 + (row + 1) * 0.3) * 0.025
            x0_left = (center0 - width0) * self.TILE_WORLD_SIZE
            x0_right = (center0 + width0) * self.TILE_WORLD_SIZE
            x1_left = (center1 - width1) * self.TILE_WORLD_SIZE
            x1_right = (center1 + width1) * self.TILE_WORLD_SIZE
            z0, z1 = row * self.TILE_WORLD_SIZE, (row + 1) * self.TILE_WORLD_SIZE
            gl.glTexCoord2f(0.0, row / self.map_mgr.rows)
            self._vertex(x0_left, y0, z0)
            gl.glTexCoord2f(1.0, row / self.map_mgr.rows)
            self._vertex(x0_right, y0, z0)
            gl.glTexCoord2f(1.0, (row + 1) / self.map_mgr.rows)
            self._vertex(x1_right, y1, z1)
            gl.glTexCoord2f(0.0, (row + 1) / self.map_mgr.rows)
            self._vertex(x1_left, y1, z1)
        gl.glEnd()
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glEnable(gl.GL_LIGHTING)

    def _draw_cliff_faces(self):
        s = self.TILE_WORLD_SIZE
        texture = self.cliff_texture
        gl.glEnable(gl.GL_TEXTURE_2D)
        if texture:
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture.id)
        gl.glBegin(gl.GL_QUADS)
        for row in range(self.map_mgr.rows - 1):
            for col in range(self.map_mgr.cols - 1):
                current = self._terrain_y(col, row)
                if self.map_mgr.cliff_south[row][col] > 0:
                    lower = self._terrain_y(col, row + 1)
                    if current > lower + 0.1:
                        gl.glColor3f(1.0, 1.0, 1.0) if texture else gl.glColor3f(0.18, 0.16, 0.14)
                        x0, x1, z = col * s, (col + 1) * s, (row + 1) * s
                        gl.glTexCoord2f(0.0, 0.0)
                        self._vertex(x0, current, z)
                        gl.glTexCoord2f(1.0, 0.0)
                        self._vertex(x1, current, z)
                        gl.glTexCoord2f(1.0, 1.0)
                        self._vertex(x1, lower, z)
                        gl.glTexCoord2f(0.0, 1.0)
                        self._vertex(x0, lower, z)
                if self.map_mgr.cliff_east[row][col] > 0:
                    lower = self._terrain_y(col + 1, row)
                    if current > lower + 0.1:
                        gl.glColor3f(1.0, 1.0, 1.0) if texture else gl.glColor3f(0.21, 0.19, 0.16)
                        x, z0, z1 = (col + 1) * s, row * s, (row + 1) * s
                        gl.glTexCoord2f(0.0, 0.0)
                        self._vertex(x, current, z0)
                        gl.glTexCoord2f(1.0, 0.0)
                        self._vertex(x, current, z1)
                        gl.glTexCoord2f(1.0, 1.0)
                        self._vertex(x, lower, z1)
                        gl.glTexCoord2f(0.0, 1.0)
                        self._vertex(x, lower, z0)
        gl.glEnd()
        gl.glDisable(gl.GL_TEXTURE_2D)

    def _draw_billboard(self, texture, x, y, z, width, height, cross=False):
        """Draw a transparent PNG as a camera-facing 3D vegetation card."""
        if texture is None:
            return
        gl.glDisable(gl.GL_LIGHTING)
        aspect = texture.height / float(max(1, texture.width))
        height = max(height, width * aspect)
        angles = (self.yaw, self.yaw + math.pi * 0.5) if cross else (self.yaw,)
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDepthMask(gl.GL_TRUE)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture.id)
        gl.glColor4f(1.0, 1.0, 1.0, 1.0)
        for angle in angles:
            rx, rz = math.cos(angle) * width * 0.5, math.sin(angle) * width * 0.5
            gl.glBegin(gl.GL_QUADS)
            gl.glTexCoord2f(0.0, 0.0)
            self._vertex(x - rx, y, z - rz)
            gl.glTexCoord2f(1.0, 0.0)
            self._vertex(x + rx, y, z + rz)
            gl.glTexCoord2f(1.0, 1.0)
            self._vertex(x + rx, y + height, z + rz)
            gl.glTexCoord2f(0.0, 1.0)
            self._vertex(x - rx, y + height, z - rz)
            gl.glEnd()
        gl.glDisable(gl.GL_BLEND)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glEnable(gl.GL_LIGHTING)

    def _draw_natural_assets(self):
        """Place the existing tree/flora PNGs on the 3D terrain surface."""
        for (col, row), obstacle in self.map_mgr.obstacles.items():
            obs_type = obstacle.obs_type
            texture = None
            cross = False
            width, height = 1.7, 3.0
            if obs_type in self.tree_textures:
                choices = [tex for tex in self.tree_textures[obs_type] if tex]
                if choices:
                    texture = choices[obstacle.variant % len(choices)]
                cross = True
                width, height = 2.7, 4.0
            elif obs_type in self.flora_textures:
                choices = [tex for tex in self.flora_textures[obs_type] if tex]
                if choices:
                    texture = choices[obstacle.variant % len(choices)]
                width, height = 1.0, 1.1
            if texture is None:
                continue
            x = (col + 0.5 + obstacle.jitter_x / TILE_SIZE) * self.TILE_WORLD_SIZE
            z = (row + 0.5 + obstacle.jitter_y / TILE_SIZE) * self.TILE_WORLD_SIZE
            ground = self._terrain_y(col, row)
            self._draw_billboard(texture, x, ground, z, width, height, cross=cross)

    @staticmethod
    def _cube(cx, cy, cz, sx, sy, sz, color):
        x0, x1 = cx - sx * 0.5, cx + sx * 0.5
        y0, y1 = cy - sy * 0.5, cy + sy * 0.5
        z0, z1 = cz - sz * 0.5, cz + sz * 0.5
        faces = [
            ((0.78, 0.78, 0.78), [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]),
            ((1.00, 1.00, 1.00), [(x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (x1, y0, z1)]),
            ((0.90, 0.90, 0.90), [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)]),
            ((0.65, 0.65, 0.65), [(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)]),
            ((0.72, 0.72, 0.72), [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]),
            ((0.48, 0.48, 0.48), [(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)]),
        ]
        gl.glBegin(gl.GL_QUADS)
        for shade, vertices in faces:
            gl.glColor3f(color[0] * shade[0], color[1] * shade[1], color[2] * shade[2])
            for vertex in vertices:
                gl.glVertex3f(*vertex)
        gl.glEnd()

    def _draw_beast(self, beast):
        x = beast.x / TILE_SIZE * self.TILE_WORLD_SIZE
        z = beast.y / TILE_SIZE * self.TILE_WORLD_SIZE
        ground = beast.z * self.HEIGHT_WORLD_SCALE
        color = self.BEAST_COLORS.get(beast.type, (0.45, 0.30, 0.20))
        texture = self.beast_textures.get(beast.type)
        if texture:
            widths = {"mammoth": 3.8, "cave_bear": 2.6, "ancient_bison": 2.7, "giant_deer": 2.3}
            self._draw_billboard(texture, x, ground, z, widths.get(beast.type, 2.0), 2.5)
            return
        scale = {"mammoth": 1.45, "cave_bear": 1.10, "ancient_bison": 1.0}.get(beast.type, 0.78)
        body_y = ground + 0.75 * scale
        self._cube(x, body_y, z, 1.35 * scale, 0.85 * scale, 0.72 * scale, color)
        head_x = x + (0.78 if beast.direction == "right" else -0.78) * scale
        self._cube(head_x, ground + 1.05 * scale, z, 0.52 * scale, 0.55 * scale, 0.52 * scale, color)
        leg_color = tuple(v * 0.62 for v in color)
        for lx in (-0.43, 0.43):
            for lz in (-0.22, 0.22):
                self._cube(x + lx * scale, ground + 0.28 * scale, z + lz * scale,
                           0.18 * scale, 0.56 * scale, 0.18 * scale, leg_color)

    def _setup_camera(self):
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(62.0, self.width / float(max(1, self.height)), 0.1, 500.0)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        dx, dy, dz = self._look_direction()
        glu.gluLookAt(
            self.cam_x, self.cam_y, self.cam_z,
            self.cam_x + dx, self.cam_y + dy, self.cam_z + dz,
            0.0, 1.0, 0.0,
        )

    def _draw_overlay(self):
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, self.width, 0, self.height, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        self.fps_label.text = (
            f"3D OpenGL | Camera: {self.cam_x / self.TILE_WORLD_SIZE:.1f}, "
            f"{self.cam_z / self.TILE_WORLD_SIZE:.1f} | Thú: {len(self.wildlife_mgr.beasts)}"
        )
        self.fps_label.draw()
        self.help_label.draw()
        gl.glEnable(gl.GL_DEPTH_TEST)

    def on_draw(self):
        self.render()

    def render(self):
        self.window.clear()
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        self._setup_camera()
        self._draw_terrain_mesh()
        self._draw_water_surface()
        self._draw_natural_assets()
        for beast in self.wildlife_mgr.beasts:
            if not beast.is_dead:
                self._draw_beast(beast)
        self._draw_overlay()

    def run(self):
        pyglet.app.run()


if __name__ == "__main__":
    Game3D().run()
