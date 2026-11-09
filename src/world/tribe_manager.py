"""
Tribe Settlement Manager Stub.
Da loai bo hoan toan con nguoi va bo lac khoi the gioi tu nhien.
"""


class TribeSettlementManager:
    def __init__(self, primitive_structures=None):
        self.structures = primitive_structures
        self.villagers = []
        self.ancestral_records = []
        self.recent_events = []
        self.stockpile = {"meat": 0, "berries": 0, "fish": 0, "wood": 0, "stone": 0, "pelt": 0}

    @property
    def housing_capacity(self):
        return 0

    @property
    def alive_villagers(self):
        return []

    @property
    def dead_villagers(self):
        return []

    @property
    def current_population(self):
        return 0

    @property
    def total_food_units(self):
        return 0

    def update(self, dt, time_sys=None, obstacles_map=None):
        pass

    def select_in_box(self, screen_rect, camera):
        return False

    def select_single_at_world(self, wx, wy, radius=24):
        return None

    def deselect_all(self):
        pass

    def get_selected_villagers(self):
        return []

    def command_selected_move(self, target_wx, target_wy):
        pass

    def command_selected_interact(self, target_type, target_pos, target_obj=None):
        pass

    def get_idle_villager(self):
        return None

    def draw_events(self, surface, fonts):
        pass

    def draw(self, surface, camera, fonts):
        pass

