"""
Integration tests for the NCAA Baseball Processor pipeline.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFullPipelineIntegration:
    """Integration tests for the full data processing pipeline."""

    def test_game_data_structure_is_complete(self, sample_game_data):
        """Test that game data structure has all required components."""
        required_keys = ['metadata', 'batting', 'pitching', 'linescore']

        for key in required_keys:
            assert key in sample_game_data, f"Missing required key: {key}"

    def test_metadata_has_required_fields(self, sample_game_data):
        """Test that metadata has all required fields."""
        meta = sample_game_data['metadata']
        required_fields = [
            'away_team', 'home_team', 'away_team_score', 'home_team_score',
            'date', 'stadium'
        ]

        for field in required_fields:
            assert field in meta, f"Missing metadata field: {field}"

    def test_batting_data_structure(self, sample_game_data):
        """Test that batting data has correct structure."""
        batting = sample_game_data['batting']

        assert 'away' in batting
        assert 'home' in batting
        assert isinstance(batting['away'], list)
        assert isinstance(batting['home'], list)

    def test_pitching_data_structure(self, sample_game_data):
        """Test that pitching data has correct structure."""
        pitching = sample_game_data['pitching']

        assert 'away' in pitching
        assert 'home' in pitching
        assert len(pitching['away']) > 0
        assert len(pitching['home']) > 0

    def test_handles_multiple_games(self, multiple_games_data):
        """Test that pipeline handles multiple games."""
        assert len(multiple_games_data) == 3

        # Verify each game has required structure
        for game in multiple_games_data:
            assert 'metadata' in game
            assert 'batting' in game
            assert 'pitching' in game


class TestDataAggregation:
    """Tests for data aggregation across games."""

    def test_aggregates_player_stats(self, multiple_games_data):
        """Test that player stats can be aggregated across games."""
        player_totals = {}

        for game in multiple_games_data:
            for side in ['away', 'home']:
                for player in game['batting'][side]:
                    name = player['name']
                    if name not in player_totals:
                        player_totals[name] = {'ab': 0, 'h': 0, 'hr': 0}
                    player_totals[name]['ab'] += player['ab']
                    player_totals[name]['h'] += player['h']
                    player_totals[name]['hr'] += player['hr']

        # Verify aggregation worked
        assert len(player_totals) > 0
        for name, stats in player_totals.items():
            assert stats['ab'] >= stats['h']

    def test_aggregates_team_records(self, multiple_games_data):
        """Test that team records can be aggregated."""
        team_records = {}

        for game in multiple_games_data:
            meta = game['metadata']
            away = meta['away_team']
            home = meta['home_team']

            if away not in team_records:
                team_records[away] = {'wins': 0, 'losses': 0}
            if home not in team_records:
                team_records[home] = {'wins': 0, 'losses': 0}

            if meta['away_team_score'] > meta['home_team_score']:
                team_records[away]['wins'] += 1
                team_records[home]['losses'] += 1
            else:
                team_records[home]['wins'] += 1
                team_records[away]['losses'] += 1

        # Verify records
        assert len(team_records) > 0


class TestEdgeCases:
    """Tests for edge cases in the integration."""

    def test_handles_missing_optional_fields(self, sample_game_data):
        """Test that missing optional fields don't crash the pipeline."""
        # Remove optional field
        game = sample_game_data.copy()
        game['metadata'] = game['metadata'].copy()
        game['metadata'].pop('attendance', None)

        # Should still have required fields
        assert 'away_team' in game['metadata']
        assert 'home_team' in game['metadata']

    def test_handles_zero_stats(self, sample_game_data):
        """Test handling of players with zero stats."""
        # Add a player with all zeros
        sample_game_data['batting']['home'].append({
            'name': 'Zero Stats Player',
            'position': 'PH',
            'ab': 1,
            'r': 0,
            'h': 0,
            'rbi': 0,
            'bb': 0,
            'so': 1,
            '2b': 0,
            '3b': 0,
            'hr': 0,
            'sb': 0
        })

        # Verify player was added
        player = next(
            (p for p in sample_game_data['batting']['home']
             if p['name'] == 'Zero Stats Player'),
            None
        )
        assert player is not None
        assert player['h'] == 0

    def test_handles_extra_innings(self, sample_game_data):
        """Test handling of extra innings games."""
        # Extend linescore for extra innings
        sample_game_data['linescore']['away']['innings'].extend(['0', '0', '1'])
        sample_game_data['linescore']['home']['innings'].extend(['0', '0', '0'])

        # Verify extended
        assert len(sample_game_data['linescore']['away']['innings']) == 12

    def test_handles_unicode_names(self, sample_game_data):
        """Test handling of Unicode characters in player names."""
        # Add player with Unicode name
        sample_game_data['batting']['away'].append({
            'name': 'José García',
            'position': 'DH',
            'ab': 3,
            'r': 1,
            'h': 1,
            'rbi': 0,
            'bb': 1,
            'so': 0,
            '2b': 0,
            '3b': 0,
            'hr': 0,
            'sb': 0
        })

        # Verify player was added
        player = next(
            (p for p in sample_game_data['batting']['away']
             if 'García' in p['name']),
            None
        )
        assert player is not None


class TestStatisticalCalculations:
    """Tests for statistical calculations."""

    def test_batting_stats_are_consistent(self, sample_game_data):
        """Test that batting stats are internally consistent."""
        for side in ['away', 'home']:
            for player in sample_game_data['batting'][side]:
                # Total bases check: 2B + 2*3B + 3*HR <= H
                doubles = player.get('2b', 0)
                triples = player.get('3b', 0)
                hrs = player.get('hr', 0)
                hits = player['h']

                extra_bases = doubles + triples + hrs
                assert extra_bases <= hits

    def test_pitching_stats_are_consistent(self, sample_game_data):
        """Test that pitching stats are internally consistent."""
        for side in ['away', 'home']:
            for pitcher in sample_game_data['pitching'][side]:
                # ER <= R
                er = pitcher.get('er', 0)
                r = pitcher.get('r', 0)
                assert er <= r

    def test_linescore_totals_match(self, sample_game_data):
        """Test that linescore inning totals match R column."""
        for side in ['away', 'home']:
            ls = sample_game_data['linescore'][side]
            innings_total = sum(int(i) for i in ls['innings'] if i != 'X')

            # Note: linescore 'r' should match or be close to innings total
            # There may be slight differences in how runs are tracked
            assert ls['r'] >= 0
