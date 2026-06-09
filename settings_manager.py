import json
import os
import logging
from pathlib import Path

logger = logging.getLogger("yt_downloader")


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
            ,"download_retry_count": 2,
            # Update channel controls which GitHub release stream to follow:
            #  - "stable": pick the latest non-prerelease release
            #  - "beta": pick the latest prerelease
            "update_channel": "stable",
            # The app must not collect telemetry by default per user request
            "telemetry_opt_in": False
        }
        self.settings = self.load_settings()

    def load_settings(self):
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge defaults with loaded settings to ensure all keys exist
                    merged = {**self.defaults, **loaded}
                    return merged
            except Exception as exc:
                logger.error(f"Failed to load settings: {exc}")
                return self.defaults
        return self.defaults

    def save_settings(self, settings):
        # Update in-memory settings first
        self.settings.update(settings)

        temp_file = self.settings_file.with_suffix('.tmp')
        try:
            # Write to a temp file first, then atomically replace
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            # Atomic replace
            os.replace(str(temp_file), str(self.settings_file))
        except Exception as exc:
            logger.error(f"Failed to save settings atomically: {exc}")
            # Attempt a best-effort direct write as fallback
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(self.settings, f, indent=4, ensure_ascii=False)
            except Exception as exc2:
                logger.critical(f"Failed to write settings fallback: {exc2}")

    def get(self, key, default=None):
        return self.settings.get(key, default if default is not None else self.defaults.get(key))
