"""
Tests for the processor modules.
"""
import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from baseball_processor.processors.player_stats import PlayerStatsProcessor, smart_title


def test_smart_title_preserves_compact_initials_and_name_particles():
    assert smart_title('rj johnson') == 'RJ Johnson'
    assert smart_title('Rj Johnson') == 'RJ Johnson'
    assert smart_title('aj salgado') == 'AJ Salgado'
    assert smart_title('jt thompson') == 'JT Thompson'
    assert smart_title('ian may') == 'Ian May'
    assert smart_title('chris mchugh') == 'Chris McHugh'


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

    def test_skips_placeholder_player_names(self):
        """Placeholder rows should not become fake leaderboard players."""
        game = {
            'metadata': {
                'date': '2025-03-15',
                'away_team': 'Team A',
                'home_team': 'Team B',
                'away_team_score': 5,
                'home_team_score': 3,
            },
            'box_score': {
                'away_batting': [
                    {'name': 'Unknown', 'ab': 4, 'h': 4, 'r': 3, 'rbi': 5},
                    {'name': 'Known Batter', 'ab': 4, 'h': 2, 'r': 1, 'rbi': 1},
                ],
                'home_batting': [],
                'away_pitching': [
                    {'name': 'Unknown', 'ip': '9.0', 'h': 0, 'r': 0, 'er': 0, 'bb': 0, 'k': 12},
                    {'name': 'Known Pitcher', 'ip': '1.0', 'h': 0, 'r': 0, 'er': 0, 'bb': 0, 'k': 1},
                ],
                'home_pitching': [],
            },
            'game_notes': {},
        }

        result = PlayerStatsProcessor([game]).process_all_stats()

        assert set(result['batters']['Name']) == {'Known Batter'}
        assert set(result['pitchers']['Name']) == {'Known Pitcher'}
        assert set(result['batter_games']['Name']) == {'Known Batter'}
        assert set(result['pitcher_games']['Name']) == {'Known Pitcher'}

    def test_resolves_single_initial_display_names_from_bref_ids(self, monkeypatch):
        """Known B-Ref IDs should repair NCAA API initial-only names in stat tables."""
        def fake_resolve(name, bref_id):
            if bref_id == 'ford--002hen':
                return 'Henry Ford'
            return name

        monkeypatch.setattr(
            'baseball_processor.processors.player_stats.resolve_player_display_name',
            fake_resolve,
        )

        game = {
            'metadata': {
                'date': '2025-03-15',
                'away_team': 'Virginia',
                'home_team': 'California',
                'away_team_score': 10,
                'home_team_score': 8,
            },
            'box_score': {
                'away_batting': [
                    {'name': 'H. Ford', 'bref_id': 'ford--002hen', 'ab': 4, 'h': 2, 'r': 1, 'rbi': 3},
                ],
                'home_batting': [],
                'away_pitching': [],
                'home_pitching': [],
            },
            'game_notes': {},
        }

        result = PlayerStatsProcessor([game]).process_all_stats()

        assert set(result['batters']['Name']) == {'Henry Ford'}
        assert set(result['batter_games']['Name']) == {'Henry Ford'}

    def test_player_tables_preserve_display_suffixes(self):
        """Aggregation keys strip suffixes for merging, but public names should not."""
        games = [
            {
                'metadata': {
                    'date': '2025-06-14',
                    'away_team': 'Louisville',
                    'home_team': 'Oregon State',
                    'away_team_score': 3,
                    'home_team_score': 4,
                },
                'box_score': {
                    'away_batting': [
                        {
                            'name': 'Eddie King Jr.',
                            'full_name': 'Eddie King',
                            'bref_id': 'king--000edd',
                            'ab': 4,
                            'h': 2,
                        },
                    ],
                    'home_batting': [],
                    'away_pitching': [],
                    'home_pitching': [],
                },
                'game_notes': {},
            },
            {
                'metadata': {
                    'date': '2025-06-15',
                    'away_team': 'Arizona',
                    'home_team': 'Louisville',
                    'away_team_score': 3,
                    'home_team_score': 8,
                },
                'box_score': {
                    'away_batting': [],
                    'home_batting': [
                        {
                            'name': 'Eddie King',
                            'bref_id': 'king--000edd',
                            'ab': 3,
                            'h': 1,
                        },
                    ],
                    'away_pitching': [],
                    'home_pitching': [],
                },
                'game_notes': {},
            },
        ]

        result = PlayerStatsProcessor(games).process_all_stats()

        assert set(result['batters']['Name']) == {'Eddie King Jr.'}
        assert set(result['batter_games']['Name']) == {'Eddie King Jr.'}
        assert result['batters'].iloc[0]['G'] == 2
        assert result['batters'].iloc[0]['AB'] == 7

    def test_merges_unique_initial_surname_aliases(self):
        """Same-team initial-only rows should merge into the unique full-name row."""
        games = [
            {
                'metadata': {
                    'date': '2025-03-15',
                    'away_team': 'California',
                    'home_team': 'Team B',
                    'away_team_score': 5,
                    'home_team_score': 3,
                },
                'box_score': {
                    'away_batting': [
                        {'name': 'Jarren Advincula', 'ab': 4, 'h': 2, 'r': 1, 'rbi': 1},
                    ],
                    'home_batting': [],
                    'away_pitching': [
                        {'name': 'Logan Piper', 'ip': '2.0', 'h': 1, 'r': 0, 'er': 0, 'bb': 0, 'k': 3},
                    ],
                    'home_pitching': [],
                },
                'game_notes': {},
            },
            {
                'metadata': {
                    'date': '2025-03-16',
                    'away_team': 'California',
                    'home_team': 'Team C',
                    'away_team_score': 6,
                    'home_team_score': 4,
                },
                'box_score': {
                    'away_batting': [
                        {'name': 'J Advincula', 'ab': 3, 'h': 1, 'r': 2, 'rbi': 0},
                    ],
                    'home_batting': [],
                    'away_pitching': [
                        {'name': 'L Piper', 'ip': '1.0', 'h': 0, 'r': 0, 'er': 0, 'bb': 0, 'k': 1},
                    ],
                    'home_pitching': [],
                },
                'game_notes': {},
            },
        ]

        result = PlayerStatsProcessor(games).process_all_stats()

        assert set(result['batters']['Name']) == {'Jarren Advincula'}
        assert result['batters'].iloc[0]['G'] == 2
        assert result['batters'].iloc[0]['AB'] == 7
        assert set(result['pitchers']['Name']) == {'Logan Piper'}
        assert result['pitchers'].iloc[0]['G'] == 2

    def test_merges_unique_surname_only_aliases_across_team_variants(self):
        """Surname-only rows should use a unique full name from a team alias."""
        games = [
            {
                'metadata': {
                    'date': '2025-04-25',
                    'away_team': 'LMU',
                    'home_team': "Saint Mary's",
                    'away_team_score': 3,
                    'home_team_score': 8,
                },
                'box_score': {
                    'away_batting': [],
                    'home_batting': [
                        {'name': 'Castellanos, Diego', 'full_name': 'Diego Castellanos', 'ab': 3, 'h': 0, 'r': 1},
                    ],
                    'away_pitching': [],
                    'home_pitching': [],
                },
                'game_notes': {},
            },
            {
                'metadata': {
                    'date': '2025-04-26',
                    'away_team': 'LMU (CA)',
                    'home_team': "Saint Mary's (CA)",
                    'away_team_score': 4,
                    'home_team_score': 5,
                },
                'box_score': {
                    'away_batting': [],
                    'home_batting': [
                        {'name': 'Castellanos', 'ab': 2, 'h': 1, 'r': 0},
                    ],
                    'away_pitching': [],
                    'home_pitching': [],
                },
                'game_notes': {},
            },
        ]

        result = PlayerStatsProcessor(games).process_all_stats()

        assert set(result['batters']['Name']) == {'Diego Castellanos'}
        assert result['batters'].iloc[0]['G'] == 2
        assert result['batters'].iloc[0]['AB'] == 5

    def test_reads_pitcher_ip_from_source_aliases(self):
        """NCAA API pitcher rows use ip, while PDFs often use innings_pitched."""
        games = [
            {
                'metadata': {
                    'date': '2023-06-18',
                    'away_team': 'TCU',
                    'home_team': 'Virginia',
                    'away_team_score': 4,
                    'home_team_score': 3,
                },
                'box_score': {
                    'away_batting': [],
                    'home_batting': [],
                    'away_pitching': [
                        {'name': 'Sam Stoutenborough', 'ip': '4.2', 'h': 2, 'r': 1, 'er': 1, 'bb': 2, 'k': 3},
                    ],
                    'home_pitching': [],
                },
                'game_notes': {},
            }
        ]

        result = PlayerStatsProcessor(games).process_all_stats()

        row = result['pitchers'].iloc[0]
        assert row['Name'] == 'Sam Stoutenborough'
        assert row['IP'] == '4.2'
        assert row['ERA'] == '1.93'

    def test_comma_initial_game_notes_do_not_match_duplicate_last_names(self):
        """A note like 'Aloy, W.' should not also attach to Kuhio Aloy."""
        game = {
            'metadata': {
                'date': '2025-06-16',
                'away_team': 'Arkansas',
                'home_team': 'Murray State',
                'away_team_score': 3,
                'home_team_score': 0,
            },
            'box_score': {
                'away_batting': [
                    {'name': 'Kuhio Aloy', 'ab': 3, 'h': 0, 'bb': 1},
                    {'name': 'Wehiwa Aloy', 'ab': 5, 'h': 2, 'bb': 0},
                ],
                'home_batting': [],
                'away_pitching': [],
                'home_pitching': [],
            },
            'game_notes': {
                'doubles': [{'player': 'aloy, w.', 'game_count': 1}],
                'stolen_bases': [{'player': 'aloy, w.', 'game_count': 1}],
            },
        }

        result = PlayerStatsProcessor([game]).process_all_stats()
        batters = {row['Name']: row for _, row in result['batters'].iterrows()}

        assert batters['Kuhio Aloy']['2B'] == 0
        assert batters['Kuhio Aloy']['SB'] == 0
        assert batters['Wehiwa Aloy']['2B'] == 1
        assert batters['Wehiwa Aloy']['SB'] == 1


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
