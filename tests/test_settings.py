import os
import json
from settings_manager import SettingsManager


def test_settings_atomic_write(tmp_path, monkeypatch):
    # Ensure SettingsManager uses a temporary home directory
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))

    sm = SettingsManager()
    assert sm.settings_dir.exists()

    # Save a setting and verify file exists and is valid JSON
    sm.save_settings({'test_key': 'value123'})
    settings_file = sm.settings_file
    assert settings_file.exists()

    with open(settings_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert data.get('test_key') == 'value123'
    # New defaults should include update_channel and telemetry_opt_in
    assert sm.get('update_channel') == 'stable'
    assert sm.get('telemetry_opt_in') is False
    # Verify temp file from atomic write was cleaned up
    for tmp in sm.settings_dir.glob('*.tmp'):
        assert False, f"Temp file was not cleaned up: {tmp}"
