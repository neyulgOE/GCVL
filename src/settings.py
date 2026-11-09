"""
Settings and game constants for Stone Age: Primeval World.
Bộ Mô Phỏng Thế Giới Hoang Dã Tự Nhiên Thời Đồ Đá (Pure Nature Observation Simulator).
"""

# Screen & Display Settings
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 640
FPS = 60
TITLE = "Stone Age: Primeval World - Bộ Mô Phỏng Thiên Nhiên Tiền Sử"

# Tile & Map Settings
TILE_SIZE = 64
MAP_COLS = 80
MAP_ROWS = 80
WORLD_WIDTH = MAP_COLS * TILE_SIZE  # 5120 px
WORLD_HEIGHT = MAP_ROWS * TILE_SIZE  # 5120 px

# Player Settings
PLAYER_SPEED = 252.0
PLAYER_MAX_STAMINA = 100.0
STAMINA_RECOVERY_SLEEP = 100.0

# Tool Stamina Costs
STAMINA_COST_HANDS = 0.5
STAMINA_COST_HOE = 2.0
STAMINA_COST_WATER = 1.0
STAMINA_COST_AXE = 2.5
STAMINA_COST_PICKAXE = 3.0
STAMINA_COST_SCYTHE = 1.5
STAMINA_COST_FISHING = 3.5

# Time & Season System (Stone Age Seasons)
START_YEAR = 1
START_SEASON_INDEX = 0  # 0: Mùa Băng Tan (Spring), 1: Mùa Nắng Hạ (Summer), 2: Mùa Lá Rụng (Fall), 3: Mùa Băng Giá (Winter)
SEASONS = [
    {"name": "Mùa Băng Tan (Spring)", "id": "spring", "color": (120, 180, 100)},
    {"name": "Mùa Nắng Hạ (Summer)", "id": "summer", "color": (180, 170, 70)},
    {"name": "Mùa Thu Rừng (Fall)", "id": "fall", "color": (190, 120, 60)},
    {"name": "Mùa Băng Giá (Winter)", "id": "winter", "color": (170, 200, 220)}
]
DAYS_PER_SEASON = 28
GAME_START_HOUR = 6
GAME_END_HOUR = 24
GAME_PASS_OUT_HOUR = 2

# Game time flow: Real seconds per in-game 10 minutes
REAL_SECONDS_PER_GAME_10_MINUTES = 2.5  # 1 hour = 15s

# Stone Age Eras (Kỷ Nguyên Tiến Hóa)
ERA_PALEOLITHIC = "paleolithic"  # Kỷ Đồ Đá Cũ (Sơ Khai)
ERA_NEOLITHIC = "neolithic"      # Kỷ Đồ Đá Mới (Nông Nghiệp & Định Cư)
ERA_BRONZE = "bronze"            # Kỷ Đồ Đồng (Bình Minh Bộ Lạc)

ERAS_DATA = {
    ERA_PALEOLITHIC: {
        "name": "Thời Đồ Đá Cũ (Paleolithic)",
        "subtitle": "Kỷ Sơ Khai - Sinh Tồn & Nhặt Nhạnh",
        "description": "Thu lượm cành cây, đá cuội, chế tác công cụ thô sơ và nhóm đống lửa trại đầu tiên.",
        "badge_color": (150, 120, 90),
        "icon": "flint"
    },
    ERA_NEOLITHIC: {
        "name": "Thời Đồ Đá Mới (Neolithic)",
        "subtitle": "Kỷ Định Cư - Nông Nghiệp & Thuần Hóa",
        "description": "Đẽo đá mài bóng, nung gốm đất sét, khai mở trồng trọt và thuần hóa muôn loài.",
        "badge_color": (90, 160, 100),
        "icon": "stone_hoe"
    },
    ERA_BRONZE: {
        "name": "Thời Đồ Đồng (Bronze Age)",
        "subtitle": "Kỷ Hưng Thịnh - Kim Khí & Bộ Tộc",
        "description": "Luyện quặng đồng, rèn công cụ kim loại sắc bén, dựng Trụ Totem và mở rộng bờ cõi.",
        "badge_color": (210, 140, 50),
        "icon": "bronze_axe"
    }
}

# Empty compatibility dicts (no human economy / agriculture)
CROPS_DATA = {}
FISH_DATA = {}
ANIMAL_DATA = {}

# Stone Age Palette (Earthy, Warm Primitive Pixel Art Palette)
PALETTE = {
    "bg_black": (14, 12, 16),
    "grass_spring": (98, 165, 72),
    "grass_summer": (125, 175, 58),
    "grass_fall": (172, 132, 60),
    "grass_winter": (200, 218, 226),
    "dirt_dry": (160, 110, 68),
    "dirt_tilled": (128, 80, 48),
    "dirt_watered": (86, 50, 28),
    "water_deep": (40, 102, 150),
    "water_shallow": (65, 140, 188),
    "water_foam": (205, 230, 250),
    "wood_dark": (88, 52, 30),
    "wood_light": (152, 102, 65),
    "stone_grey": (126, 134, 140),
    "stone_dark": (80, 86, 92),
    "flint_glow": (240, 140, 40),
    "ui_panel": (238, 224, 198),
    "ui_panel_dark": (48, 38, 32),
    "ui_border": (102, 62, 40),
    "ui_text_dark": (44, 26, 16),
    "shell_pink": (245, 190, 180),
    "stamina_high": (65, 190, 75),
    "stamina_mid": (220, 170, 35),
    "stamina_low": (210, 55, 45),
    "night_overlay": (10, 15, 45),
    "sunset_overlay": (180, 80, 40),
    "fire_orange": (255, 120, 20),
    "bronze": (205, 127, 50)
}
