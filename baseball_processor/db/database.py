"""
SQLite database manager for NCAA Baseball Processor.

Provides CRUD operations for games, player stats, milestones,
and crossover tracking data.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager

from .schema import SCHEMA_SQL, SCHEMA_VERSION


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            from ..utils.constants import BASE_DIR
            db_path = BASE_DIR / "baseball.db"
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            # Set schema version
            existing = conn.execute("SELECT version FROM schema_version").fetchone()
            if not existing:
                conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
            conn.commit()

    @contextmanager
    def _connect(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

    # === GAME OPERATIONS ===

    def game_exists(self, game_key: str) -> bool:
        """Check if a game already exists in the database."""
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM games WHERE game_key = ?", (game_key,)).fetchone()
            return row is not None

    def upsert_game(self, game_data: Dict[str, Any]) -> int:
        """Insert or update a game and its associated player stats.

        Args:
            game_data: Full game data dict (same format as JSON cache)

        Returns:
            Game ID
        """
        meta = game_data.get('metadata', {})
        box_score = game_data.get('box_score', {})

        date = meta.get('date', '')
        date_yyyymmdd = meta.get('date_yyyymmdd', '')
        away_team = meta.get('away_team', '')
        home_team = meta.get('home_team', '')
        game_pk = meta.get('game_pk')

        # Build unique game key
        if game_pk:
            game_key = f"pk_{game_pk}"
        else:
            game_key = f"{date_yyyymmdd}_{away_team}_{home_team}"

        # Determine source and level
        source = meta.get('source', 'ncaa')
        if game_data.get('format') == 'milb_api':
            source = meta.get('source', 'milb')

        # Resolve level/league
        level = ''
        league = ''
        try:
            from ..utils.constants import resolve_level_and_league
            if source in ('milb', 'partner'):
                level, league = resolve_level_and_league(meta, home_team)
            else:
                level = 'NCAA'
                from ..utils.constants import get_conference
                league = get_conference(home_team)
        except Exception:
            pass

        with self._connect() as conn:
            # Upsert game
            conn.execute("""
                INSERT INTO games (game_key, date, date_yyyymmdd, away_team, home_team,
                    away_score, home_score, venue, level, league, source, game_pk, raw_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(game_key) DO UPDATE SET
                    away_score=excluded.away_score, home_score=excluded.home_score,
                    raw_json=excluded.raw_json, updated_at=datetime('now')
            """, (
                game_key, date, date_yyyymmdd, away_team, home_team,
                meta.get('away_team_score'), meta.get('home_team_score'),
                meta.get('venue', ''), level, league, source, game_pk,
                json.dumps(game_data),
            ))

            game_id = conn.execute("SELECT id FROM games WHERE game_key = ?", (game_key,)).fetchone()['id']

            # Clear existing lines for this game (for re-processing)
            conn.execute("DELETE FROM batting_lines WHERE game_id = ?", (game_id,))
            conn.execute("DELETE FROM pitching_lines WHERE game_id = ?", (game_id,))

            # Insert batting lines
            for side in ['away', 'home']:
                team = meta.get(f'{side}_team', '')
                for player in box_score.get(f'{side}_batting', []):
                    name = player.get('full_name') or player.get('name', '')
                    if not name:
                        continue
                    conn.execute("""
                        INSERT OR IGNORE INTO batting_lines
                        (game_id, player_name, team, side, bref_id, player_id,
                         ab, r, h, rbi, bb, k, hr, doubles, triples, sb, hbp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        game_id, name, team, side,
                        player.get('bref_id', ''), player.get('player_id', ''),
                        player.get('at_bats', player.get('ab', 0)),
                        player.get('runs', player.get('r', 0)),
                        player.get('hits', player.get('h', 0)),
                        player.get('rbi', 0),
                        player.get('walks', player.get('bb', 0)),
                        player.get('strikeouts', player.get('k', 0)),
                        player.get('home_runs', player.get('hr', 0)),
                        player.get('doubles', player.get('2b', 0)),
                        player.get('triples', player.get('3b', 0)),
                        player.get('stolen_bases', player.get('sb', 0)),
                        player.get('hit_by_pitch', player.get('hbp', 0)),
                    ))

            # Insert pitching lines
            for side in ['away', 'home']:
                team = meta.get(f'{side}_team', '')
                for idx, player in enumerate(box_score.get(f'{side}_pitching', [])):
                    name = player.get('full_name') or player.get('name', '')
                    if not name:
                        continue
                    decision = player.get('decision', '')
                    if not decision:
                        if player.get('win'): decision = 'W'
                        elif player.get('loss'): decision = 'L'
                        elif player.get('save'): decision = 'S'
                    conn.execute("""
                        INSERT OR IGNORE INTO pitching_lines
                        (game_id, player_name, team, side, pitcher_order, bref_id, player_id,
                         ip, h, r, er, bb, k, hr, pitches, bf, hbp, decision)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        game_id, name, team, side, idx,
                        player.get('bref_id', ''), player.get('player_id', ''),
                        str(player.get('innings_pitched', player.get('ip', '0.0'))),
                        player.get('hits', player.get('h', 0)),
                        player.get('runs', player.get('r', 0)),
                        player.get('earned_runs', player.get('er', 0)),
                        player.get('walks', player.get('bb', 0)),
                        player.get('strikeouts', player.get('k', 0)),
                        player.get('home_runs', player.get('hr', 0)),
                        player.get('pitches', player.get('np', 0)),
                        player.get('batters_faced', player.get('bf', 0)),
                        player.get('hit_by_pitch', player.get('hbp', 0)),
                        decision,
                    ))

            conn.commit()
            return game_id

    def get_all_games(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load all games from database as original JSON format.

        Args:
            source: Optional filter by source ('ncaa', 'milb', 'partner')

        Returns:
            List of game data dicts (same format as JSON cache)
        """
        with self._connect() as conn:
            if source:
                rows = conn.execute(
                    "SELECT raw_json FROM games WHERE source = ? ORDER BY date_yyyymmdd",
                    (source,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT raw_json FROM games ORDER BY date_yyyymmdd"
                ).fetchall()

            games = []
            for row in rows:
                if row['raw_json']:
                    games.append(json.loads(row['raw_json']))
            return games

    def get_game_count(self, source: Optional[str] = None) -> int:
        """Get count of games in database."""
        with self._connect() as conn:
            if source:
                row = conn.execute("SELECT COUNT(*) as cnt FROM games WHERE source = ?", (source,)).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) as cnt FROM games").fetchone()
            return row['cnt']

    # === MILESTONE OPERATIONS ===

    def upsert_milestone(self, game_id: int, milestone_type: str, player_name: str,
                         team: str, opponent: str, level: str, league: str,
                         details: Dict[str, Any]) -> None:
        """Insert or update a milestone."""
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO milestones (game_id, milestone_type, player_name, team, opponent, level, league, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id, milestone_type, player_name) DO UPDATE SET
                    details=excluded.details
            """, (game_id, milestone_type, player_name, team, opponent, level, league, json.dumps(details)))
            conn.commit()

    # === CROSSOVER OPERATIONS ===

    def upsert_crossover_link(self, player_name: str, bref_id: Optional[str],
                               mlb_api_id: Optional[int], levels_seen: str,
                               ncaa_teams: str, pro_teams: str,
                               ncaa_games: int, pro_games: int) -> None:
        """Insert or update a crossover player link."""
        with self._connect() as conn:
            if bref_id:
                conn.execute("""
                    INSERT INTO crossover_links (player_name, bref_id, mlb_api_id, levels_seen,
                        ncaa_teams, pro_teams, ncaa_games, pro_games, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(bref_id) DO UPDATE SET
                        player_name=excluded.player_name, mlb_api_id=excluded.mlb_api_id,
                        levels_seen=excluded.levels_seen, ncaa_teams=excluded.ncaa_teams,
                        pro_teams=excluded.pro_teams, ncaa_games=excluded.ncaa_games,
                        pro_games=excluded.pro_games, updated_at=datetime('now')
                """, (player_name, bref_id, mlb_api_id, levels_seen, ncaa_teams, pro_teams, ncaa_games, pro_games))
            elif mlb_api_id:
                conn.execute("""
                    INSERT INTO crossover_links (player_name, bref_id, mlb_api_id, levels_seen,
                        ncaa_teams, pro_teams, ncaa_games, pro_games, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(mlb_api_id) DO UPDATE SET
                        player_name=excluded.player_name, bref_id=excluded.bref_id,
                        levels_seen=excluded.levels_seen, ncaa_teams=excluded.ncaa_teams,
                        pro_teams=excluded.pro_teams, ncaa_games=excluded.ncaa_games,
                        pro_games=excluded.pro_games, updated_at=datetime('now')
                """, (player_name, bref_id, mlb_api_id, levels_seen, ncaa_teams, pro_teams, ncaa_games, pro_games))
            conn.commit()

    # === DRAFT OPERATIONS ===

    def upsert_draft_pick(self, pick_data: Dict[str, Any]) -> None:
        """Insert or update a draft pick."""
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO draft_picks (year, round, pick_number, player_name, school,
                    team, position, mlb_api_id, bref_id, signed, bonus, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(year, round, pick_number) DO UPDATE SET
                    player_name=excluded.player_name, school=excluded.school,
                    team=excluded.team, position=excluded.position,
                    mlb_api_id=excluded.mlb_api_id, bref_id=excluded.bref_id,
                    signed=excluded.signed, bonus=excluded.bonus,
                    raw_json=excluded.raw_json
            """, (
                pick_data['year'], pick_data['round'], pick_data['pick_number'],
                pick_data['player_name'], pick_data.get('school', ''),
                pick_data['team'], pick_data.get('position', ''),
                pick_data.get('mlb_api_id'), pick_data.get('bref_id'),
                pick_data.get('signed', 0), pick_data.get('bonus', ''),
                json.dumps(pick_data.get('raw', {})),
            ))
            conn.commit()

    def get_draft_picks_for_player(self, player_name: Optional[str] = None,
                                    bref_id: Optional[str] = None,
                                    mlb_api_id: Optional[int] = None) -> List[Dict]:
        """Look up draft picks by player identifiers."""
        with self._connect() as conn:
            if bref_id:
                rows = conn.execute("SELECT * FROM draft_picks WHERE bref_id = ?", (bref_id,)).fetchall()
                if rows:
                    return [dict(r) for r in rows]
            if mlb_api_id:
                rows = conn.execute("SELECT * FROM draft_picks WHERE mlb_api_id = ?", (mlb_api_id,)).fetchall()
                if rows:
                    return [dict(r) for r in rows]
            if player_name:
                rows = conn.execute(
                    "SELECT * FROM draft_picks WHERE LOWER(player_name) LIKE ?",
                    (f"%{player_name.lower()}%",)
                ).fetchall()
                return [dict(r) for r in rows]
            return []

    def get_all_draft_picks(self, year: Optional[int] = None) -> List[Dict]:
        """Get all draft picks, optionally filtered by year."""
        with self._connect() as conn:
            if year:
                rows = conn.execute(
                    "SELECT * FROM draft_picks WHERE year = ? ORDER BY round, pick_number",
                    (year,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM draft_picks ORDER BY year DESC, round, pick_number"
                ).fetchall()
            return [dict(r) for r in rows]

    # === MIGRATION ===

    def migrate_from_cache(self, cache_dir: Path, source: str = 'ncaa') -> Tuple[int, int]:
        """Import games from JSON cache directory into database.

        Args:
            cache_dir: Path to cache directory with JSON files
            source: Source label ('ncaa', 'milb', 'partner')

        Returns:
            Tuple of (imported_count, error_count)
        """
        if not cache_dir.exists():
            print(f"Cache directory not found: {cache_dir}")
            return (0, 0)

        json_files = list(cache_dir.glob("*.json"))
        print(f"Migrating {len(json_files)} {source} games from {cache_dir}...")

        imported = 0
        errors = 0

        with self._connect() as conn:
            # Start a processing run
            conn.execute(
                "INSERT INTO processing_runs (source, notes) VALUES (?, ?)",
                ('migrate', f"Migrating {source} cache from {cache_dir}")
            )
            run_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    game_data = json.load(f)
                self.upsert_game(game_data)
                imported += 1
                if imported % 50 == 0:
                    print(f"  Migrated {imported}/{len(json_files)}...")
            except Exception as e:
                print(f"  Error migrating {json_file.name}: {e}")
                errors += 1

        # Update processing run
        with self._connect() as conn:
            conn.execute(
                "UPDATE processing_runs SET completed_at=datetime('now'), games_processed=?, errors=? WHERE id=?",
                (imported, errors, run_id)
            )
            conn.commit()

        print(f"Migration complete: {imported} imported, {errors} errors")
        return (imported, errors)

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        with self._connect() as conn:
            stats = {}
            for table in ['games', 'batting_lines', 'pitching_lines', 'milestones', 'crossover_links', 'draft_picks']:
                row = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
                stats[table] = row['cnt']
            # Breakdown by source
            for source in ['ncaa', 'milb', 'partner']:
                row = conn.execute("SELECT COUNT(*) as cnt FROM games WHERE source = ?", (source,)).fetchone()
                stats[f'games_{source}'] = row['cnt']
            return stats
