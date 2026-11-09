"""
Primitive Structures Stub.
Toan bo cong trinh nhan tao da duoc loai bo khoi the gioi tu nhien.
"""


class PrimitiveStructures:
    def __init__(self):
        self.campfire_level = 0
        self.shelter_level = 0
        self.kiln_level = 0
        self.totem_level = 0
        self.storage_level = 0
        self.grass_tents = 0
        self.pelt_tipis = 0
        self.campfire_pos = (-999, -999)
        self.shelter_pos = (-999, -999)

    def upgrade_structure(self, target_name, new_level):
        pass

    def is_near_campfire(self, world_x, world_y, distance_threshold=96):
        return False

    def is_near_shelter(self, world_x, world_y, distance_threshold=128):
        return False

    def update(self, dt):
        pass

    def draw(self, surface, camera, fonts):
        pass

    def to_dict(self):
        return {}

    def from_dict(self, data):
        pass

