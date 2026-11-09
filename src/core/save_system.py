"""
Save and Load System for Stone Age Nature Observation Simulator.
Saves and loads simulation state: time, season, climate, and observation camera position.
"""

import json
import os

SAVE_DIR = "saves"
SAVE_FILE = os.path.join(SAVE_DIR, "nature_state.json")

class SaveSystem:
    @staticmethod
    def ensure_save_dir():
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR, exist_ok=True)

    @staticmethod
    def save_state(time_sys, weather_sys, free_cam=None):
        SaveSystem.ensure_save_dir()
        data = {
            "version": 5.0,
            "title": "Stone Age Nature Simulator",
            "time": time_sys.to_dict(),
            "weather": weather_sys.weather,
        }
        if free_cam and hasattr(free_cam, "target"):
            data["camera"] = {
                "x": free_cam.target.x,
                "y": free_cam.target.y
            }

        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print("Lỗi lưu trạng thái tự nhiên:", e)
            return False

    @staticmethod
    def load_state(time_sys, weather_sys, free_cam=None):
        if not os.path.exists(SAVE_FILE):
            return False

        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "time" in data:
                time_sys.from_dict(data["time"])
            if "weather" in data:
                weather_sys.weather = data["weather"]
            if free_cam and "camera" in data:
                cx = data["camera"].get("x", 40 * 64)
                cy = data["camera"].get("y", 38 * 64)
                free_cam.set_pos(cx, cy)
            return True
        except Exception as e:
            print("Lỗi nạp trạng thái tự nhiên:", e)
            return False

    @staticmethod
    def save_exists():
        return os.path.exists(SAVE_FILE)
