"""
Crop entities and lifecycle simulation for Green Valley Tales.
Handles planting, daily watering, stage-by-stage growth, seasonal withering,
and multi-harvest regrow mechanics.
"""

from src.settings import CROPS_DATA

class Crop:
    def __init__(self, crop_id, col, row, days_grown=0, watered_today=False):
        self.crop_id = crop_id
        self.col = col
        self.row = row
        self.data = CROPS_DATA[crop_id]
        
        self.days_grown = days_grown
        self.watered_today = watered_today
        self.is_mature = False
        self.is_dead = False
        self.current_stage = 0
        self._update_stage()

    def _update_stage(self):
        total_days = self.data["grow_days"]
        stages = self.data["stages"]
        
        if self.days_grown >= total_days:
            self.current_stage = stages - 1
            self.is_mature = True
        else:
            self.is_mature = False
            progress = self.days_grown / total_days
            self.current_stage = min(stages - 2, int(progress * (stages - 1)))

    def water(self):
        self.watered_today = True

    def next_day(self, current_season_id, is_raining=False):
        """Called overnight by MapManager."""
        # 1. Season check (Corn / Wild corn can grow in Summer and Fall)
        valid_seasons = [self.data["season"]]
        if self.crop_id in ["corn", "wild_corn"]:
            valid_seasons.append("fall")

        if current_season_id not in valid_seasons:
            self.is_dead = True
            return

        # 2. Advance growth if watered
        if self.watered_today or is_raining:
            if not self.is_mature:
                self.days_grown += 1
                self._update_stage()

        # 3. Reset daily water status
        self.watered_today = is_raining

    def harvest(self):
        """
        Harvest the mature crop.
        Returns:
            produce_data: dict of produce item
            keep_plant: bool (True if regrows, False if single harvest)
        """
        if not self.is_mature or self.is_dead:
            return None, False

        produce = {
            "type": "crop",
            "id": self.crop_id,
            "name": self.data["name"].split(" (")[0],
            "price": self.data["sell_price"]
        }

        # Check if regrows
        regrow = self.data["regrow_days"]
        if regrow > 0:
            # Keep plant, roll back days
            self.days_grown = self.data["grow_days"] - regrow
            self._update_stage()
            return produce, True
        else:
            return produce, False

    def to_dict(self):
        return {
            "crop_id": self.crop_id,
            "col": self.col,
            "row": self.row,
            "days_grown": self.days_grown,
            "watered_today": self.watered_today,
            "is_dead": self.is_dead
        }

    @classmethod
    def from_dict(cls, data):
        c = cls(
            crop_id=data["crop_id"],
            col=data["col"],
            row=data["row"],
            days_grown=data.get("days_grown", 0),
            watered_today=data.get("watered_today", False)
        )
        c.is_dead = data.get("is_dead", False)
        c._update_stage()
        return c
