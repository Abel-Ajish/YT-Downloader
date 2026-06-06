import json
import os
from pathlib import Path

class SettingsManager:
    def __init__(self):
        self.settings_dir = Path.home() / ".yt_downloader"
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.settings_dir / "settings.json"
        self.defaults = {
            "appearance_mode": "System",
            "save_dir": str(Path.home() / "Downloads"),
            "window_geometry": "680x680+100+100",
            "last_quality": "Best Available",
            "last_type": "Video (.MP4/.MKV)",
            "playlist_enabled": False,
            "subtitles_enabled": False,
            "no_ffmpeg_enabled": False
        }
        self.settings = self.load_settings()

    def load_settings(self):
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    loaded = json.load(f)
                    # Merge defaults with loaded settings to ensure all keys exist
                    return {**self.defaults, **loaded}
            except Exception:
                return self.defaults
        return self.defaults

    def save_settings(self, settings):
        self.settings.update(settings)
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception:
            pass

    def get(self, key):
        return self.settings.get(key, self.defaults.get(key))
