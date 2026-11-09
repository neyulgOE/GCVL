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

# Currency Name
CURRENCY_NAME = "Vỏ Sò (Shells)"
CURRENCY_ICON = "🐚"

# Standard Tool Identifiers & Aliases
TOOL_HOE = "hoe"
TOOL_WATER_CAN = "water_can"
TOOL_AXE = "axe"
TOOL_PICKAXE = "pickaxe"
TOOL_SCYTHE = "scythe"
TOOL_FISHING_ROD = "fishing_rod"

# Stone Age Specific Tool Definitions
STONE_AGE_TOOLS = {
    # Paleolithic
    "primitive_axe": {"base": TOOL_AXE, "name": "Rìu Đá Thô Sơ", "era": ERA_PALEOLITHIC, "stamina": 3.0, "power": 1},
    "digging_stick": {"base": TOOL_HOE, "name": "Gậy Bới Đất Nhọn", "era": ERA_PALEOLITHIC, "stamina": 2.5, "power": 1},
    "primitive_spear": {"base": TOOL_FISHING_ROD, "name": "Giáo Bắt Cá Thô Sơ", "era": ERA_PALEOLITHIC, "stamina": 3.5, "power": 1},
    "stone_pick": {"base": TOOL_PICKAXE, "name": "Búa Đá Sơ Khai", "era": ERA_PALEOLITHIC, "stamina": 3.0, "power": 1},
    "flint_striker": {"base": "fire", "name": "Bộ Đá Lửa Đánh Lửa", "era": ERA_PALEOLITHIC, "stamina": 1.0, "power": 1},
    
    # Neolithic
    "polished_axe": {"base": TOOL_AXE, "name": "Rìu Đá Mài Bóng", "era": ERA_NEOLITHIC, "stamina": 2.0, "power": 2},
    "stone_hoe": {"base": TOOL_HOE, "name": "Cuốc Đá Xới Đất", "era": ERA_NEOLITHIC, "stamina": 1.8, "power": 2},
    "clay_jug": {"base": TOOL_WATER_CAN, "name": "Bình Gốm Nung Múc Nước", "era": ERA_NEOLITHIC, "stamina": 1.0, "max_water": 35, "power": 2},
    "bone_rod": {"base": TOOL_FISHING_ROD, "name": "Cần Câu Móc Xương Cá", "era": ERA_NEOLITHIC, "stamina": 2.5, "power": 2},
    "bone_scythe": {"base": TOOL_SCYTHE, "name": "Liềm Răng Xương Cắt Cỏ", "era": ERA_NEOLITHIC, "stamina": 1.2, "power": 2},
    
    # Bronze Age
    "bronze_axe": {"base": TOOL_AXE, "name": "Rìu Đồng Sắc Bén", "era": ERA_BRONZE, "stamina": 1.5, "power": 3},
    "bronze_hoe": {"base": TOOL_HOE, "name": "Cuốc Đồng Khai Hoang", "era": ERA_BRONZE, "stamina": 1.2, "power": 3},
    "bronze_pick": {"base": TOOL_PICKAXE, "name": "Cuốc Chim Đồng Luyện", "era": ERA_BRONZE, "stamina": 2.0, "power": 3},
    "tribal_harpoon": {"base": TOOL_FISHING_ROD, "name": "Lao Săn Cá Bộ Lạc", "era": ERA_BRONZE, "stamina": 2.0, "power": 3}
}

# Prehistoric Crops & Wild Plants
CROPS_DATA = {
    "wild_roots": {
        "name": "Củ Dại Đầm Lầy (Wild Roots)",
        "season": "spring",
        "grow_days": 3,
        "stages": 4,
        "regrow_days": 0,
        "sell_price": 25,
        "seed_cost": 10,
        "color": (210, 190, 150)
    },
    "wild_wheat": {
        "name": "Lúa Mì Nguyên Thủy (Wild Wheat)",
        "season": "spring",
        "grow_days": 5,
        "stages": 4,
        "regrow_days": 0,
        "sell_price": 60,
        "seed_cost": 25,
        "color": (220, 200, 120)
    },
    "forest_berry": {
        "name": "Dâu Rừng Hoang Dã (Forest Berries)",
        "season": "spring",
        "grow_days": 6,
        "stages": 5,
        "regrow_days": 3,
        "sell_price": 90,
        "seed_cost": 45,
        "color": (210, 50, 60)
    },
    "wild_corn": {
        "name": "Bắp Rừng Tiền Sử (Wild Maize)",
        "season": "summer",
        "grow_days": 8,
        "stages": 5,
        "regrow_days": 3,
        "sell_price": 70,
        "seed_cost": 35,
        "color": (230, 210, 70)
    },
    "giant_squash": {
        "name": "Bí Đỏ Cổ Đại (Giant Squash)",
        "season": "fall",
        "grow_days": 9,
        "stages": 5,
        "regrow_days": 0,
        "sell_price": 180,
        "seed_cost": 80,
        "color": (230, 130, 30)
    }
}

# Prehistoric River Fish
FISH_DATA = {
    "river_crayfish": {
        "name": "Tôm Sông Khổng Lồ (River Crayfish)",
        "price": 25,
        "difficulty": 0.8,
        "time": "all",
        "seasons": ["spring", "summer", "fall", "winter"],
        "color": (190, 90, 70)
    },
    "paleo_carp": {
        "name": "Cá Chép Nguyên Sinh (Paleo Carp)",
        "price": 40,
        "difficulty": 1.0,
        "time": "all",
        "seasons": ["spring", "summer", "fall", "winter"],
        "color": (190, 160, 100)
    },
    "mud_catfish": {
        "name": "Cá Da Trơn Đầm Lầy (Mud Catfish)",
        "price": 75,
        "difficulty": 1.6,
        "time": "night_or_rain",
        "seasons": ["spring", "summer", "fall"],
        "color": (70, 80, 90)
    },
    "river_sturgeon": {
        "name": "Cá Tầm Suối Cổ (River Sturgeon)",
        "price": 120,
        "difficulty": 2.2,
        "time": "day",
        "seasons": ["fall", "winter"],
        "color": (100, 130, 160)
    },
    "golden_paleo_fish": {
        "name": "Cá Vàng Thần Thoại (Golden Paleo Fish)",
        "price": 280,
        "difficulty": 2.8,
        "time": "all",
        "seasons": ["spring", "summer", "fall", "winter"],
        "color": (255, 215, 0)
    }
}

# Prehistoric Tamed Animals
ANIMAL_DATA = {
    "wild_chicken": {
        "name": "Gà Rừng Cổ Đại (Wild Fowl)",
        "cost": 300,
        "product": "wild_egg",
        "product_name": "Trứng Gà Rừng Tươi",
        "large_product": "large_wild_egg",
        "large_product_name": "Trứng Gà Rừng Vàng",
        "product_price": 40,
        "large_product_price": 80,
        "color": (210, 170, 120),
        "days_to_produce": 1
    },
    "aurochs": {
        "name": "Bò Rừng Tiền Sử (Aurochs)",
        "cost": 800,
        "product": "rich_milk",
        "product_name": "Sữa Bò Rừng Đậm Đặc",
        "large_product": "golden_milk",
        "large_product_name": "Sữa Bò Rừng Thượng Hạng",
        "product_price": 90,
        "large_product_price": 160,
        "color": (160, 110, 70),
        "days_to_produce": 1
    }
}
# Backward compatibility aliases
ANIMAL_DATA["chicken"] = ANIMAL_DATA["wild_chicken"]
ANIMAL_DATA["cow"] = ANIMAL_DATA["aurochs"]

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
