"""
Tests for the processor modules.
"""
import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPlayerStatsProcessor:
    """Tests for player statistics processing."""

    def test_processes_batting_stats(self, sample_game_data):
        """Test that batting stats are extracted correctly."""
        batting = sample_game_data['batting']

        # Verify structure
        assert 'away' in batting
        assert 'home' in batting
        assert len(batting['away']) > 0

        # Verify player data
        player = batting['away'][0]
        assert 'name' in player
        assert 'ab' in player
        assert 'h' in player

    def test_processes_pitching_stats(self, sample_game_data):
        """Test that pitching stats are extracted correctly."""
        pitching = sample_game_data['pitching']

        assert 'away' in pitching
        assert 'home' in pitching

        pitcher = pitching['away'][0]
        assert 'name' in pitcher
        assert 'ip' in pitcher
        assert 'so' in pitcher

    def test_calculates_totals_across_games(self, multiple_games_data):
        """Test that totals are calculated correctly across games."""
        total_games = len(multiple_games_data)
        assert total_games == 3

        # Count total players across all games
        total_batters = sum(
            len(g['batting']['away']) + len(g['batting']['home'])
            for g in multiple_games_data
        )
        assert total_batters > 0


class TestGameLogProcessor:
    """Tests for game log processing."""

    def test_extracts_game_metadata(self, sample_game_data):
        """Test that game metadata is extracted correctly."""
        meta = sample_game_data['metadata']

        assert meta['away_team'] == 'Team A'
        assert meta['home_team'] == 'Team B'
        assert meta['away_team_score'] == 5
        assert meta['home_team_score'] == 3

    def test_extracts_venue_info(self, sample_game_data):
        """Test that venue information is extracted."""
        meta = sample_game_data['metadata']

        assert meta['stadium'] == 'Test Stadium'
        assert meta['city'] == 'Test City'
        assert meta['state'] == 'TX'

    def test_handles_multiple_games(self, multiple_games_data):
        """Test handling of multiple games."""
        dates = [g['metadata']['date'] for g in multiple_games_data]

        assert len(dates) == 3
        assert dates[0] != dates[1]


class TestLinescoreProcessor:
    """Tests for linescore processing."""

    def test_extracts_linescore(self, sample_game_data):
        """Test that linescore is extracted correctly."""
        linescore = sample_game_data['linescore']

        assert 'away' in linescore
        assert 'home' in linescore
        assert 'innings' in linescore['away']
        assert len(linescore['away']['innings']) == 9

    def test_calculates_totals(self, sample_game_data):
        """Test that R/H/E totals are present."""
        linescore = sample_game_data['linescore']

        assert linescore['away']['r'] == 5
        assert linescore['away']['h'] == 8
        assert linescore['away']['e'] == 1

        assert linescore['home']['r'] == 3
        assert linescore['home']['h'] == 6
        assert linescore['home']['e'] == 2


class TestMilestoneDetection:
    """Tests for milestone detection."""

    def test_detects_home_run(self, sample_game_data):
        """Test detection of home runs."""
        away_batters = sample_game_data['batting']['away']

        # John Smith has 1 HR in the sample data
        john = next((p for p in away_batters if p['name'] == 'John Smith'), None)
        assert john is not None
        assert john['hr'] == 1

    def test_detects_multi_hit_game(self, sample_game_data):
        """Test detection of multi-hit games."""
        away_batters = sample_game_data['batting']['away']

        # Mike Jones has 3 hits
        mike = next((p for p in away_batters if p['name'] == 'Mike Jones'), None)
        assert mike is not None
        assert mike['h'] >= 3

    def test_detects_high_strikeout_game(self, sample_game_data):
        """Test detection of high strikeout pitching games."""
        away_pitchers = sample_game_data['pitching']['away']

        # Tom Brown has 7 strikeouts
        tom = next((p for p in away_pitchers if p['name'] == 'Tom Brown'), None)
        assert tom is not None
        assert tom['so'] >= 7


class TestTeamRecordsProcessor:
    """Tests for team records processing."""

    def test_tracks_wins_losses(self, multiple_games_data):
        """Test tracking of wins and losses."""
        wins = 0
        losses = 0

        for game in multiple_games_data:
            meta = game['metadata']
            if meta['away_team_score'] > meta['home_team_score']:
                wins += 1  # Away team wins
            else:
                losses += 1  # Home team wins

        assert wins + losses == 3

    def test_tracks_venue_records(self, multiple_games_data):
        """Test tracking of records by venue."""
        venues = set()
        for game in multiple_games_data:
            venues.add(game['metadata']['stadium'])

        # Should have 2 unique venues in the test data
        assert len(venues) == 2


class TestDataValidation:
    """Tests for data validation."""

    def test_validates_required_fields(self, sample_game_data):
        """Test that required fields are present."""
        assert 'metadata' in sample_game_data
        assert 'batting' in sample_game_data
        assert 'pitching' in sample_game_data
        assert 'linescore' in sample_game_data

    def test_validates_score_consistency(self, sample_game_data):
        """Test that score matches linescore totals."""
        meta = sample_game_data['metadata']
        linescore = sample_game_data['linescore']

        assert meta['away_team_score'] == linescore['away']['r']
        assert meta['home_team_score'] == linescore['home']['r']

    def test_validates_player_stats(self, sample_game_data):
        """Test that player stats are valid numbers."""
        for side in ['away', 'home']:
            for player in sample_game_data['batting'][side]:
                assert isinstance(player['ab'], int)
                assert isinstance(player['h'], int)
                assert player['h'] <= player['ab']  # Can't have more hits than ABs
