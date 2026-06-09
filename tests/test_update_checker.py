import json
import types
import pytest

import update_checker


def make_release(tag, prerelease, assets):
    return {
        'tag_name': tag,
        'prerelease': prerelease,
        'assets': assets,
    }


def test_choose_release_stable_prefers_non_prerelease():
    r1 = make_release('v1.0.1', True, [])
    r2 = make_release('v1.0.2', False, [])
    chosen = update_checker.choose_release([r1, r2], channel='stable')
    assert chosen['tag_name'] == 'v1.0.2'


def test_choose_release_beta_prefers_prerelease():
    r1 = make_release('v1.0.1', False, [])
    r2 = make_release('v1.0.3-beta', True, [])
    chosen = update_checker.choose_release([r1, r2], channel='beta')
    assert chosen['tag_name'] == 'v1.0.3-beta'


def test_find_exe_asset_and_hash_prefers_setup_and_parses_digest():
    asset_setup = {'name': 'Setup-YTDownloader.exe', 'browser_download_url': 'http://x', 'digest': 'sha256:abcd1234'}
    asset_other = {'name': 'YT-Downloader.exe', 'browser_download_url': 'http://y', 'digest': 'sha256:ffee'}
    release = make_release('v1', False, [asset_other, asset_setup])
    result = update_checker.find_exe_asset_and_hash(release)
    assert result is not None
    asset, expected = result
    assert asset['name'] == 'Setup-YTDownloader.exe'
    assert expected == 'abcd1234'


def test_find_exe_asset_and_hash_handles_missing_digest():
    asset = {'name': 'YT-Downloader.exe', 'browser_download_url': 'http://y'}
    release = make_release('v2', True, [asset])
    result = update_checker.find_exe_asset_and_hash(release)
    assert result is not None
    asset2, expected2 = result
    assert asset2['name'] == 'YT-Downloader.exe'
    assert expected2 is None
