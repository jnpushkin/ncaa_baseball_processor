"""
Tests for Chadwick player ID cache behavior.
"""

import json
import os
import time

from baseball_processor.utils import player_ids


def _write_cache(path):
    path.write_text(
        json.dumps(
            {
                "register_to_mlb": {"sample001": "sample01"},
                "mlb_to_register": {"sample01": "sample001"},
                "mlbam_to_register": {"123": "sample001"},
                "mlbam_to_mlb": {"123": "sample01"},
                "register_to_mlbam": {"sample001": 123},
                "mlb_to_mlbam": {"sample01": 123},
                "register_to_name": {"sample001": "Sample Player"},
                "mlb_to_name": {"sample01": "Sample Player"},
                "mlbam_to_name": {"123": "Sample Player"},
            }
        ),
        encoding="utf-8",
    )


def test_offline_mode_loads_stale_cache_without_downloading(tmp_path, monkeypatch):
    cache_file = tmp_path / "player_id_map.json"
    _write_cache(cache_file)
    old_timestamp = time.time() - (player_ids.CACHE_MAX_AGE_DAYS + 3) * 86400
    os.utime(cache_file, (old_timestamp, old_timestamp))

    monkeypatch.setattr(player_ids, "CHADWICK_CACHE_DIR", tmp_path)
    monkeypatch.setenv(player_ids.OFFLINE_ENV_VAR, "1")

    def fail_download(self):
        raise AssertionError("offline mode should not download Chadwick data")

    monkeypatch.setattr(player_ids.PlayerIDMapper, "_download_chadwick_data", fail_download)

    mapper = player_ids.PlayerIDMapper(auto_download=True)

    assert mapper.get_mlb_id("sample001") == "sample01"
    assert mapper.get_register_from_mlbam(123) == "sample001"


def test_offline_mode_returns_false_when_cache_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(player_ids, "CHADWICK_CACHE_DIR", tmp_path)
    monkeypatch.setenv(player_ids.OFFLINE_ENV_VAR, "1")

    def fail_download(self):
        raise AssertionError("offline mode should not download Chadwick data")

    monkeypatch.setattr(player_ids.PlayerIDMapper, "_download_chadwick_data", fail_download)

    mapper = player_ids.PlayerIDMapper(auto_download=False)

    assert mapper.ensure_data() is False


def test_load_cached_data_reads_names_without_downloading(tmp_path, monkeypatch):
    cache_file = tmp_path / "player_id_map.json"
    _write_cache(cache_file)

    monkeypatch.setattr(player_ids, "CHADWICK_CACHE_DIR", tmp_path)

    def fail_download(self):
        raise AssertionError("load_cached_data should not download Chadwick data")

    monkeypatch.setattr(player_ids.PlayerIDMapper, "_download_chadwick_data", fail_download)

    mapper = player_ids.PlayerIDMapper(auto_download=False)

    assert mapper.load_cached_data() is True
    assert mapper.get_player_name("sample001") == "Sample Player"
    assert mapper.get_player_name("sample01") == "Sample Player"
    assert mapper.get_player_name(123) == "Sample Player"
    assert mapper.get_player_name("123") == "Sample Player"
