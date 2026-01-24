"""
Pytest configuration and shared fixtures for NCAA Baseball Processor tests.
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_game_data():
    """Provide a minimal valid game data structure for testing."""
    return {
        "metadata": {
            "away_team": "Team A",
            "home_team": "Team B",
            "away_team_score": 5,
            "home_team_score": 3,
            "date": "03/15/2024",
            "stadium": "Test Stadium",
            "city": "Test City",
            "state": "TX",
            "attendance": "1500"
        },
        "batting": {
            "away": [
                {
                    "name": "John Smith",
                    "position": "SS",
                    "ab": 4,
                    "r": 1,
                    "h": 2,
                    "rbi": 1,
                    "bb": 0,
                    "so": 1,
                    "2b": 0,
                    "3b": 0,
                    "hr": 1,
                    "sb": 0
                },
                {
                    "name": "Mike Jones",
                    "position": "CF",
                    "ab": 4,
                    "r": 2,
                    "h": 3,
                    "rbi": 2,
                    "bb": 1,
                    "so": 0,
                    "2b": 1,
                    "3b": 0,
                    "hr": 0,
                    "sb": 1
                }
            ],
            "home": [
                {
                    "name": "Bob Wilson",
                    "position": "1B",
                    "ab": 4,
                    "r": 1,
                    "h": 1,
                    "rbi": 1,
                    "bb": 0,
                    "so": 2,
                    "2b": 0,
                    "3b": 0,
                    "hr": 1,
                    "sb": 0
                }
            ]
        },
        "pitching": {
            "away": [
                {
                    "name": "Tom Brown",
                    "ip": "6.0",
                    "h": 4,
                    "r": 2,
                    "er": 2,
                    "bb": 2,
                    "so": 7,
                    "hr": 1,
                    "decision": "W"
                }
            ],
            "home": [
                {
                    "name": "Jim Davis",
                    "ip": "5.2",
                    "h": 6,
                    "r": 4,
                    "er": 4,
                    "bb": 3,
                    "so": 5,
                    "hr": 1,
                    "decision": "L"
                }
            ]
        },
        "linescore": {
            "away": {
                "innings": ["0", "1", "0", "2", "1", "0", "1", "0", "0"],
                "r": 5,
                "h": 8,
                "e": 1
            },
            "home": {
                "innings": ["0", "0", "1", "0", "1", "0", "1", "0", "0"],
                "r": 3,
                "h": 6,
                "e": 2
            }
        }
    }


@pytest.fixture
def multiple_games_data(sample_game_data):
    """Provide multiple game data entries for aggregation tests."""
    import copy

    game1 = copy.deepcopy(sample_game_data)

    game2 = copy.deepcopy(sample_game_data)
    game2["metadata"]["date"] = "03/16/2024"
    game2["metadata"]["away_team_score"] = 8
    game2["metadata"]["home_team_score"] = 6

    game3 = copy.deepcopy(sample_game_data)
    game3["metadata"]["date"] = "03/17/2024"
    game3["metadata"]["stadium"] = "Different Stadium"
    game3["metadata"]["away_team_score"] = 2
    game3["metadata"]["home_team_score"] = 4

    return [game1, game2, game3]


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Provide a temporary cache directory for testing."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir
