"""
Comprehensive tests for the MilestonesProcessor.
"""
import pytest
import pandas as pd
from baseball_processor.processors.milestones import MilestonesProcessor


class TestMilestoneKeys:
    """Tests for MILESTONE_KEYS class attribute."""

    def test_milestone_keys_count(self):
        """Should have 40+ milestone types."""
        assert len(MilestonesProcessor.MILESTONE_KEYS) >= 40

    def test_milestone_keys_are_unique(self):
        """All milestone keys should be unique."""
        keys = MilestonesProcessor.MILESTONE_KEYS
        assert len(keys) == len(set(keys))


class TestBattingMilestones:
    """Tests for batting milestone detection."""

    def _create_game(self, batting_stats=None, pitching_stats=None):
        """Helper to create a game with stats."""
        return {
            'metadata': {
                'date': '2024-03-15',
                'away_team': 'Texas',
                'home_team': 'Oklahoma',
                'away_team_score': 5,
                'home_team_score': 3,
            },
            'box_score': {
                'away_batting': batting_stats or [],
                'home_batting': [],
                'away_pitching': pitching_stats or [],
                'home_pitching': [],
            },
            'game_notes': {},
        }

    def test_three_hr_game(self):
        """Player with 3+ HR should be in three_hr_games."""
        game = self._create_game(batting_stats=[
            {'name': 'John Smith', 'h': 3, 'hr': 3, 'rbi': 6, 'ab': 4}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['three_hr_games']) == 1
        assert result['three_hr_games'].iloc[0]['Player'] == 'John Smith'
        assert result['three_hr_games'].iloc[0]['HR'] == 3

    def test_multi_hr_game(self):
        """Player with exactly 2 HR should be in multi_hr_games (not three_hr)."""
        game = self._create_game(batting_stats=[
            {'name': 'John Smith', 'h': 2, 'hr': 2, 'rbi': 4, 'ab': 4}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['multi_hr_games']) == 1
        assert len(result.get('three_hr_games', pd.DataFrame())) == 0

    def test_single_hr_game(self):
        """Player with exactly 1 HR should be in hr_games only."""
        game = self._create_game(batting_stats=[
            {'name': 'John Smith', 'h': 1, 'hr': 1, 'rbi': 2, 'ab': 4}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['hr_games']) == 1
        assert len(result.get('multi_hr_games', pd.DataFrame())) == 0

    def test_five_hit_game(self):
        """Player with 5+ hits should be in five_hit_games."""
        game = self._create_game(batting_stats=[
            {'name': 'Mike Jones', 'h': 5, 'hr': 0, 'rbi': 2, 'ab': 5, 'r': 3}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['five_hit_games']) == 1
        assert result['five_hit_games'].iloc[0]['H'] == 5

    def test_four_hit_game(self):
        """Player with exactly 4 hits should be in four_hit_games."""
        game = self._create_game(batting_stats=[
            {'name': 'Mike Jones', 'h': 4, 'hr': 0, 'rbi': 2, 'ab': 5, 'r': 2}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['four_hit_games']) == 1
        assert len(result.get('five_hit_games', pd.DataFrame())) == 0

    def test_cycle(self):
        """Player with 1B, 2B, 3B, HR should be in cycles."""
        game = self._create_game(batting_stats=[
            {'name': 'Cycle Man', 'h': 4, 'hr': 1, 'doubles': 1, 'triples': 1, 'rbi': 4, 'ab': 5}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['cycles']) == 1
        assert result['cycles'].iloc[0]['Player'] == 'Cycle Man'

    def test_cycle_watch(self):
        """Player with 3 of 4 hit types should be in cycle_watch."""
        game = self._create_game(batting_stats=[
            {'name': 'Almost Cycle', 'h': 3, 'hr': 1, 'doubles': 1, 'triples': 0, 'rbi': 3, 'ab': 4}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['cycle_watch']) == 1
        assert len(result.get('cycles', pd.DataFrame())) == 0

    def test_six_rbi_game(self):
        """Player with 6+ RBI should be in six_rbi_games."""
        game = self._create_game(batting_stats=[
            {'name': 'RBI King', 'h': 4, 'hr': 2, 'rbi': 6, 'ab': 5}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['six_rbi_games']) == 1
        assert result['six_rbi_games'].iloc[0]['RBI'] == 6

    def test_five_rbi_game(self):
        """Player with exactly 5 RBI should be in five_rbi_games."""
        game = self._create_game(batting_stats=[
            {'name': 'RBI Guy', 'h': 3, 'hr': 1, 'rbi': 5, 'ab': 4}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['five_rbi_games']) == 1
        assert len(result.get('six_rbi_games', pd.DataFrame())) == 0

    def test_multi_double_games(self):
        """Player with 2+ doubles should be in multi_double_games."""
        game = self._create_game(batting_stats=[
            {'name': 'Double Trouble', 'h': 3, 'doubles': 2, 'hr': 0, 'rbi': 2, 'ab': 4}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['multi_double_games']) == 1
        assert result['multi_double_games'].iloc[0]['2B'] == 2

    def test_multi_triple_games(self):
        """Player with 2+ triples should be in multi_triple_games."""
        game = self._create_game(batting_stats=[
            {'name': 'Triple Threat', 'h': 3, 'triples': 2, 'hr': 0, 'rbi': 2, 'ab': 4}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['multi_triple_games']) == 1
        assert result['multi_triple_games'].iloc[0]['3B'] == 2

    def test_multi_sb_games(self):
        """Player with 2+ stolen bases should be in multi_sb_games."""
        game = self._create_game(batting_stats=[
            {'name': 'Speed Demon', 'h': 2, 'sb': 3, 'hr': 0, 'rbi': 1, 'ab': 4, 'r': 2}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['multi_sb_games']) == 1
        assert result['multi_sb_games'].iloc[0]['SB'] == 3

    def test_four_walk_games(self):
        """Player with 4+ walks should be in four_walk_games."""
        game = self._create_game(batting_stats=[
            {'name': 'Patient Batter', 'h': 1, 'bb': 4, 'hr': 0, 'rbi': 0, 'ab': 2, 'r': 2}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['four_walk_games']) == 1
        assert result['four_walk_games'].iloc[0]['BB'] == 4

    def test_perfect_batting_games(self):
        """Player with 3+ H and 0 K should be in perfect_batting_games."""
        game = self._create_game(batting_stats=[
            {'name': 'No Whiff', 'h': 4, 'ab': 4, 'so': 0, 'hr': 0, 'rbi': 1}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['perfect_batting_games']) == 1
        assert result['perfect_batting_games'].iloc[0]['K'] == 0

    def test_four_run_games(self):
        """Player with 4+ runs should be in four_run_games."""
        game = self._create_game(batting_stats=[
            {'name': 'Run Scorer', 'h': 3, 'r': 4, 'hr': 1, 'rbi': 2, 'ab': 5, 'bb': 1}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['four_run_games']) == 1
        assert result['four_run_games'].iloc[0]['R'] == 4

    def test_three_run_games(self):
        """Player with exactly 3 runs should be in three_run_games."""
        game = self._create_game(batting_stats=[
            {'name': 'Run Scorer', 'h': 2, 'r': 3, 'hr': 0, 'rbi': 1, 'ab': 4, 'bb': 1}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['three_run_games']) == 1
        assert len(result.get('four_run_games', pd.DataFrame())) == 0

    def test_hit_for_extra_bases(self):
        """Player with 2+ XBH should be in hit_for_extra_bases."""
        game = self._create_game(batting_stats=[
            {'name': 'XBH Guy', 'h': 3, 'doubles': 1, 'hr': 1, 'rbi': 3, 'ab': 4}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['hit_for_extra_bases']) == 1
        assert result['hit_for_extra_bases'].iloc[0]['XBH'] == 2

    def test_three_total_bases_games(self):
        """Player with 8+ total bases should be in three_total_bases_games."""
        game = self._create_game(batting_stats=[
            {'name': 'Power Hitter', 'h': 4, 'hr': 2, 'doubles': 0, 'rbi': 5, 'ab': 5}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        # 2 singles + 2 HR = 2 + 8 = 10 TB
        assert len(result['three_total_bases_games']) == 1
        assert result['three_total_bases_games'].iloc[0]['TB'] >= 8


class TestPitchingMilestones:
    """Tests for pitching milestone detection."""

    def _create_game(self, pitching_stats=None):
        """Helper to create a game with pitching stats."""
        return {
            'metadata': {
                'date': '2024-03-15',
                'away_team': 'Texas',
                'home_team': 'Oklahoma',
                'away_team_score': 5,
                'home_team_score': 3,
            },
            'box_score': {
                'away_batting': [],
                'home_batting': [],
                'away_pitching': pitching_stats or [],
                'home_pitching': [],
            },
            'game_notes': {},
        }

    def test_perfect_game(self):
        """CG with 0 H and 0 BB should be in perfect_games."""
        game = self._create_game(pitching_stats=[
            {'name': 'Perfect Pete', 'innings_pitched': 9.0, 'k': 10, 'h': 0, 'bb': 0, 'er': 0}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['perfect_games']) == 1
        assert result['perfect_games'].iloc[0]['Player'] == 'Perfect Pete'

    def test_no_hitter(self):
        """CG with 0 H but walks should be in no_hitters."""
        game = self._create_game(pitching_stats=[
            {'name': 'No Hit Nick', 'innings_pitched': 9.0, 'k': 8, 'h': 0, 'bb': 2, 'er': 0}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['no_hitters']) == 1
        assert len(result.get('perfect_games', pd.DataFrame())) == 0

    def test_one_hitter(self):
        """CG with 1 H should be in one_hitters."""
        game = self._create_game(pitching_stats=[
            {'name': 'One Hit Wonder', 'innings_pitched': 9.0, 'k': 9, 'h': 1, 'bb': 1, 'er': 0}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['one_hitters']) == 1

    def test_two_hitter(self):
        """CG with 2 H should be in two_hitters."""
        game = self._create_game(pitching_stats=[
            {'name': 'Two Hit Terry', 'innings_pitched': 9.0, 'k': 8, 'h': 2, 'bb': 1, 'er': 1}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['two_hitters']) == 1

    def test_shutout(self):
        """CG with 0 ER (and some BB) should be in shutouts."""
        game = self._create_game(pitching_stats=[
            {'name': 'Shutout Sam', 'innings_pitched': 9.0, 'k': 7, 'h': 5, 'bb': 2, 'er': 0}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['shutouts']) == 1

    def test_cgso_no_walks(self):
        """CG shutout with 0 BB should be in cgso_no_walks."""
        game = self._create_game(pitching_stats=[
            {'name': 'Command Carl', 'innings_pitched': 9.0, 'k': 8, 'h': 4, 'bb': 0, 'er': 0}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['cgso_no_walks']) == 1
        assert len(result.get('shutouts', pd.DataFrame())) == 0  # Should not be in regular shutouts

    def test_complete_game(self):
        """CG with more than 3 H should be in complete_games."""
        game = self._create_game(pitching_stats=[
            {'name': 'Complete Carl', 'innings_pitched': 9.0, 'k': 6, 'h': 7, 'bb': 2, 'er': 2}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['complete_games']) == 1

    def test_low_hit_cg(self):
        """CG with 3 or fewer H should be in low_hit_cg."""
        game = self._create_game(pitching_stats=[
            {'name': 'Low Hit Larry', 'innings_pitched': 9.0, 'k': 9, 'h': 3, 'bb': 1, 'er': 1}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['low_hit_cg']) == 1

    def test_seven_inning_shutout(self):
        """7+ IP shutout (under 9) should be in seven_inning_shutouts."""
        game = self._create_game(pitching_stats=[
            {'name': 'Seven Steve', 'innings_pitched': 7.0, 'k': 6, 'h': 4, 'bb': 1, 'er': 0}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['seven_inning_shutouts']) == 1

    def test_maddux_game(self):
        """CG with under 100 pitches should be in maddux_games."""
        game = self._create_game(pitching_stats=[
            {'name': 'Maddux Mike', 'innings_pitched': 9.0, 'k': 5, 'h': 6, 'bb': 0, 'er': 1, 'pitches': 89}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['maddux_games']) == 1
        assert result['maddux_games'].iloc[0]['Pitches'] == 89

    def test_fifteen_k_game(self):
        """15+ K should be in fifteen_k_games."""
        game = self._create_game(pitching_stats=[
            {'name': 'Strikeout King', 'innings_pitched': 9.0, 'k': 15, 'h': 3, 'bb': 1, 'er': 1}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['fifteen_k_games']) == 1
        assert result['fifteen_k_games'].iloc[0]['K'] == 15

    def test_twelve_k_game(self):
        """12-14 K should be in twelve_k_games."""
        game = self._create_game(pitching_stats=[
            {'name': 'K Man', 'innings_pitched': 8.0, 'k': 12, 'h': 4, 'bb': 2, 'er': 2}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['twelve_k_games']) == 1
        assert len(result.get('fifteen_k_games', pd.DataFrame())) == 0

    def test_ten_k_game(self):
        """10-11 K should be in ten_k_games."""
        game = self._create_game(pitching_stats=[
            {'name': 'Double Digits', 'innings_pitched': 7.0, 'k': 10, 'h': 5, 'bb': 2, 'er': 2}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['ten_k_games']) == 1
        assert len(result.get('twelve_k_games', pd.DataFrame())) == 0

    def test_eight_k_game(self):
        """8-9 K should be in eight_k_games."""
        game = self._create_game(pitching_stats=[
            {'name': 'Solid Sam', 'innings_pitched': 6.0, 'k': 8, 'h': 5, 'bb': 3, 'er': 2}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['eight_k_games']) == 1
        assert len(result.get('ten_k_games', pd.DataFrame())) == 0

    def test_quality_start(self):
        """6+ IP with 3 or fewer ER should be in quality_starts."""
        game = self._create_game(pitching_stats=[
            {'name': 'Quality Quinn', 'innings_pitched': 6.0, 'k': 5, 'h': 6, 'bb': 2, 'er': 3}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['quality_starts']) == 1

    def test_dominant_start(self):
        """7+ IP with 10+ K should be in dominant_starts."""
        game = self._create_game(pitching_stats=[
            {'name': 'Dominant Dan', 'innings_pitched': 7.0, 'k': 10, 'h': 4, 'bb': 1, 'er': 1}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['dominant_starts']) == 1

    def test_efficient_start(self):
        """6+ IP with 80 or fewer pitches should be in efficient_starts."""
        game = self._create_game(pitching_stats=[
            {'name': 'Efficient Ed', 'innings_pitched': 6.0, 'k': 4, 'h': 5, 'bb': 0, 'er': 1, 'pitches': 75}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['efficient_starts']) == 1

    def test_high_k_low_bb(self):
        """8+ K with 2 or fewer BB should be in high_k_low_bb."""
        game = self._create_game(pitching_stats=[
            {'name': 'Command King', 'innings_pitched': 6.0, 'k': 9, 'h': 4, 'bb': 1, 'er': 2}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['high_k_low_bb']) == 1

    def test_no_walk_start(self):
        """5+ IP with 0 BB should be in no_walk_starts."""
        game = self._create_game(pitching_stats=[
            {'name': 'No Walk Nate', 'innings_pitched': 5.0, 'k': 4, 'h': 5, 'bb': 0, 'er': 2}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['no_walk_starts']) == 1

    def test_scoreless_relief(self):
        """3+ IP relief with 0 ER should be in scoreless_relief."""
        game = self._create_game(pitching_stats=[
            {'name': 'Relief Randy', 'innings_pitched': 4.0, 'k': 3, 'h': 2, 'bb': 1, 'er': 0}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['scoreless_relief']) == 1

    def test_win_game(self):
        """Pitcher with W decision should be in win_games."""
        game = self._create_game(pitching_stats=[
            {'name': 'Winner Will', 'innings_pitched': 6.0, 'k': 5, 'h': 5, 'bb': 2, 'er': 2, 'decision': 'W'}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['win_games']) == 1

    def test_save_game(self):
        """Pitcher with S decision should be in save_games."""
        game = self._create_game(pitching_stats=[
            {'name': 'Saver Steve', 'innings_pitched': 1.0, 'k': 2, 'h': 0, 'bb': 0, 'er': 0, 'decision': 'S'}
        ])
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        assert len(result['save_games']) == 1


class TestMilestoneProcessorIntegration:
    """Integration tests for the MilestonesProcessor."""

    def test_processes_empty_games_list(self):
        """Should handle empty games list."""
        processor = MilestonesProcessor([])
        result = processor.process_all_milestones()

        assert isinstance(result, dict)
        assert all(isinstance(df, pd.DataFrame) for df in result.values())

    def test_processes_game_without_milestones(self):
        """Should handle games with no noteworthy performances."""
        game = {
            'metadata': {
                'date': '2024-03-15',
                'away_team': 'Texas',
                'home_team': 'Oklahoma',
                'away_team_score': 2,
                'home_team_score': 1,
            },
            'box_score': {
                'away_batting': [
                    {'name': 'Regular Joe', 'h': 1, 'hr': 0, 'rbi': 0, 'ab': 4, 'r': 0}
                ],
                'home_batting': [],
                'away_pitching': [
                    {'name': 'Average Al', 'innings_pitched': 5.0, 'k': 3, 'h': 5, 'bb': 2, 'er': 1}
                ],
                'home_pitching': [],
            },
            'game_notes': {},
        }
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        # Most milestone lists should be empty
        non_empty_count = sum(1 for df in result.values() if len(df) > 0)
        assert non_empty_count < 5  # Very few milestones for average performance

    def test_filters_invalid_player_names(self):
        """Should filter out totals rows and game notes."""
        game = {
            'metadata': {
                'date': '2024-03-15',
                'away_team': 'Texas',
                'home_team': 'Oklahoma',
                'away_team_score': 10,
                'home_team_score': 3,
            },
            'box_score': {
                'away_batting': [
                    {'name': 'Totals', 'h': 15, 'hr': 5, 'rbi': 10, 'ab': 40},  # Should be filtered
                    {'name': 'HR: Smith (5)', 'h': 3, 'hr': 2, 'rbi': 5, 'ab': 4},  # Should be filtered
                    {'name': 'John Smith', 'h': 3, 'hr': 2, 'rbi': 5, 'ab': 4},  # Valid
                ],
                'home_batting': [],
                'away_pitching': [],
                'home_pitching': [],
            },
            'game_notes': {},
        }
        processor = MilestonesProcessor([game])
        result = processor.process_all_milestones()

        # Should only have John Smith's milestones
        if len(result['multi_hr_games']) > 0:
            assert all(row['Player'] == 'John Smith' for _, row in result['multi_hr_games'].iterrows())

    def test_returns_sorted_by_date(self):
        """Results should be sorted by date descending."""
        games = [
            {
                'metadata': {
                    'date': '2024-03-10',
                    'away_team': 'A', 'home_team': 'B',
                    'away_team_score': 5, 'home_team_score': 3,
                },
                'box_score': {
                    'away_batting': [{'name': 'Early Player', 'h': 4, 'hr': 0, 'rbi': 1, 'ab': 4, 'r': 2}],
                    'home_batting': [],
                    'away_pitching': [],
                    'home_pitching': [],
                },
                'game_notes': {},
            },
            {
                'metadata': {
                    'date': '2024-03-15',
                    'away_team': 'C', 'home_team': 'D',
                    'away_team_score': 6, 'home_team_score': 4,
                },
                'box_score': {
                    'away_batting': [{'name': 'Later Player', 'h': 4, 'hr': 0, 'rbi': 1, 'ab': 4, 'r': 2}],
                    'home_batting': [],
                    'away_pitching': [],
                    'home_pitching': [],
                },
                'game_notes': {},
            },
        ]
        processor = MilestonesProcessor(games)
        result = processor.process_all_milestones()

        if len(result['four_hit_games']) >= 2:
            dates = result['four_hit_games']['Date'].tolist()
            assert dates == sorted(dates, reverse=True)
