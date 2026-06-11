import requests
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("yt_downloader")


def fetch_releases(repo: str, timeout: int = 12) -> List[Dict[str, Any]]:
    api_url = f"https://api.github.com/repos/{repo}/releases"
    r = requests.get(api_url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def choose_release(releases: List[Dict[str, Any]], channel: str = "stable") -> Optional[Dict[str, Any]]:
    """Choose a release from the list based on the channel.

    stable: first non-prerelease
    beta: first prerelease
    """
    if channel == "stable":
        for r in releases:
            if not r.get('prerelease'):
                return r
        return None
    elif channel == "beta":
        for r in releases:
            if r.get('prerelease'):
                return r
        return None
    else:
        logger.error(f"Unknown update channel: {channel}")
        return None


def find_exe_asset_and_hash(release: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], Optional[str]]]:
    """Return (asset_dict, expected_hash_hex) for the best-matching exe asset in the release.
    expected_hash_hex is None if digest not present.
    """
    if not release:
        return None
    assets = release.get('assets', [])
    asset = None
    # Prefer assets with 'setup' in the name first
    for a in assets:
        name = a.get('name', '').lower()
        if name.endswith('.exe') and 'setup' in name:
            asset = a
            break
    # Next prefer explicit YT-Downloader exe names
    if not asset:
        for a in assets:
            name = a.get('name', '').lower()
            if name.endswith('.exe') and ('yt-downloader' in name or 'yt_downloader' in name):
                asset = a
                break
    # Finally, fallback to any exe
    if not asset:
        for a in assets:
            if a.get('name', '').lower().endswith('.exe'):
                asset = a
                break
    if not asset:
        return None

    digest = asset.get('digest') or ''
    expected = None
    if digest.startswith('sha256:'):
        expected = digest.split(':', 1)[1]

    return asset, expected
