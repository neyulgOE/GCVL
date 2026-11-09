"""
Offline Save and Load System for Stone Age: Dawn of Tribe.
Stores complete prehistoric state into JSON file (saves/slot1.json).
Supports inventory, primitive structures, era quest progression, and crafting.
"""

import json
import os

SAVE_DIR = "saves"
SAVE_FILE = os.path.join(SAVE_DIR, "slot1.json")

class SaveSystem:
    @staticmethod
    def ensure_save_dir():
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR, exist_ok=True)

    @staticmethod
    def save_game(time_sys, weather_sys, player, inventory, map_mgr, animals_mgr, shipping_bin, 
                  storage=None, crafting_sys=None, primitive_structures=None, era_quest_sys=None):
        SaveSystem.ensure_save_dir()
        data = {
            "version": 4.0,
            "title": "Stone Age: Dawn of Tribe",
            "time": time_sys.to_dict(),
            "weather": weather_sys.weather,
            "player": player.to_dict(),
            "inventory": inventory.to_dict(),
            "map": map_mgr.to_dict(),
            "animals": animals_mgr.to_dict(),
            "shipping_bin": shipping_bin.to_dict()
        }
        if storage:
            data["storage"] = storage.to_dict()
        if crafting_sys:
            data["crafting"] = crafting_sys.to_dict()
        if primitive_structures:
            data["primitive_structures"] = primitive_structures.to_dict()
        if era_quest_sys:
            data["era_quests"] = era_quest_sys.to_dict()

        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print("Lỗi lưu file save:", e)
            return False

    @staticmethod
    def load_game(time_sys, weather_sys, player, inventory, map_mgr, animals_mgr, shipping_bin, 
                  storage=None, crafting_sys=None, primitive_structures=None, era_quest_sys=None):
        if not os.path.exists(SAVE_FILE):
            return False

        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            time_sys.from_dict(data.get("time", {}))
            weather_sys.weather = data.get("weather", "sunny")
            player.from_dict(data.get("player", {}))
            inventory.from_dict(data.get("inventory", {}))
            map_mgr.from_dict(data.get("map", {}))
            animals_mgr.from_dict(data.get("animals", {}))
            shipping_bin.from_dict(data.get("shipping_bin", {}))
            if storage and "storage" in data:
                storage.from_dict(data["storage"])
            if crafting_sys and "crafting" in data:
                crafting_sys.from_dict(data["crafting"])
            if primitive_structures and "primitive_structures" in data:
                primitive_structures.from_dict(data["primitive_structures"])
            if era_quest_sys and "era_quests" in data:
                era_quest_sys.from_dict(data["era_quests"])
            return True
        except Exception as e:
            print("Lỗi tải file save:", e)
            return False

    @staticmethod
    def save_exists():
        return os.path.exists(SAVE_FILE)
