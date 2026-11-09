"""
Time and Calendar System for Stone Age: Primeval World.
Handles continuous 24-hour day/night cycle, 28-day prehistoric seasons
(Spring, Summer, Fall, Winter), year progression, and celestial time.
(Pure Natural World Simulation — continuous flow, no pass-out).
"""

from src.settings import (
    SEASONS, DAYS_PER_SEASON, GAME_START_HOUR, REAL_SECONDS_PER_GAME_10_MINUTES
)


class TimeSystem:
    def __init__(self):
        self.year = 1
        self.season_idx = 0  # 0: Spring, 1: Summer, 2: Fall, 3: Winter
        self.day = 1
        self.hour = GAME_START_HOUR
        self.minute = 0

        self.accumulated_time = 0.0
        self.is_paused = False

    @property
    def season_info(self):
        return SEASONS[self.season_idx]

    @property
    def season_id(self):
        return SEASONS[self.season_idx]["id"]

    @property
    def season_name(self):
        return SEASONS[self.season_idx]["name"]

    @property
    def time_string(self):
        """Format 12-hour or 24-hour digital clock display."""
        period = "AM" if self.hour < 12 or self.hour == 24 else "PM"
        display_hour = self.hour % 12
        if display_hour == 0:
            display_hour = 12
        return f"{display_hour:02d}:{self.minute:02d} {period}"

    @property
    def day_string(self):
        return f"Năm {self.year} - {self.season_name} - Ngày {self.day}"

    def update(self, dt):
        """Continuously advance time based on delta time."""
        if self.is_paused:
            return None

        self.accumulated_time += dt
        while self.accumulated_time >= REAL_SECONDS_PER_GAME_10_MINUTES:
            self.accumulated_time -= REAL_SECONDS_PER_GAME_10_MINUTES
            self.minute += 10
            if self.minute >= 60:
                self.minute = 0
                self.hour += 1
                if self.hour >= 24:
                    self.hour = 0
                    self.advance_day()

        return None

    def advance_day(self):
        """Advances to the next calendar day and transitions seasons seamlessly."""
        self.day += 1
        if self.day > DAYS_PER_SEASON:
            self.day = 1
            self.season_idx += 1
            if self.season_idx >= len(SEASONS):
                self.season_idx = 0
                self.year += 1

        return {
            "day": self.day,
            "season_id": self.season_id,
            "season_name": self.season_name,
            "year": self.year
        }

    def to_dict(self):
        return {
            "year": self.year,
            "season_idx": self.season_idx,
            "day": self.day,
            "hour": self.hour,
            "minute": self.minute
        }

    def from_dict(self, data):
        self.year = data.get("year", 1)
        self.season_idx = data.get("season_idx", 0)
        self.day = data.get("day", 1)
        self.hour = data.get("hour", GAME_START_HOUR)
        self.minute = data.get("minute", 0)
