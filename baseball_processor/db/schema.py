"""
SQLite database schema for NCAA Baseball Processor.

Tables:
- games: Core game metadata (date, teams, scores, venue, level)
- batting_lines: Individual player batting lines per game
- pitching_lines: Individual player pitching lines per game
- milestones: Detected milestones (type, player, game reference)
- crossover_links: Links between player IDs across systems
- processing_runs: Audit trail of processing runs
"""

SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- Processing run audit trail
CREATE TABLE IF NOT EXISTS processing_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    source TEXT NOT NULL,  -- 'ncaa', 'milb', 'partner', 'migrate'
    games_processed INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    notes TEXT
);

-- Core game data
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_key TEXT UNIQUE NOT NULL,  -- unique identifier: date_away_home or game_pk
    date TEXT NOT NULL,
    date_yyyymmdd TEXT,
    away_team TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_score INTEGER,
    home_score INTEGER,
    venue TEXT,
    level TEXT,  -- NCAA, Triple-A, Double-A, etc.
    league TEXT,  -- conference or league name
    source TEXT NOT NULL,  -- 'ncaa', 'milb', 'partner'
    game_pk INTEGER,  -- MLB Stats API game PK (for MiLB/Partner)
    raw_json TEXT,  -- full original JSON for regeneration
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_games_date ON games(date_yyyymmdd);
CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_team, away_team);
CREATE INDEX IF NOT EXISTS idx_games_level ON games(level);
CREATE INDEX IF NOT EXISTS idx_games_source ON games(source);
CREATE INDEX IF NOT EXISTS idx_games_game_pk ON games(game_pk);

-- Player batting lines
CREATE TABLE IF NOT EXISTS batting_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    side TEXT NOT NULL,  -- 'home' or 'away'
    bref_id TEXT,
    player_id TEXT,  -- MLB API player ID
    ab INTEGER DEFAULT 0,
    r INTEGER DEFAULT 0,
    h INTEGER DEFAULT 0,
    rbi INTEGER DEFAULT 0,
    bb INTEGER DEFAULT 0,
    k INTEGER DEFAULT 0,
    hr INTEGER DEFAULT 0,
    doubles INTEGER DEFAULT 0,
    triples INTEGER DEFAULT 0,
    sb INTEGER DEFAULT 0,
    hbp INTEGER DEFAULT 0,
    UNIQUE(game_id, player_name, team, side)
);

CREATE INDEX IF NOT EXISTS idx_batting_game ON batting_lines(game_id);
CREATE INDEX IF NOT EXISTS idx_batting_player ON batting_lines(player_name);
CREATE INDEX IF NOT EXISTS idx_batting_bref ON batting_lines(bref_id);

-- Player pitching lines
CREATE TABLE IF NOT EXISTS pitching_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    side TEXT NOT NULL,
    pitcher_order INTEGER DEFAULT 0,  -- 0 = starter
    bref_id TEXT,
    player_id TEXT,
    ip TEXT DEFAULT '0.0',
    h INTEGER DEFAULT 0,
    r INTEGER DEFAULT 0,
    er INTEGER DEFAULT 0,
    bb INTEGER DEFAULT 0,
    k INTEGER DEFAULT 0,
    hr INTEGER DEFAULT 0,
    pitches INTEGER DEFAULT 0,
    bf INTEGER DEFAULT 0,
    hbp INTEGER DEFAULT 0,
    decision TEXT,  -- W, L, S, or empty
    UNIQUE(game_id, player_name, team, side)
);

CREATE INDEX IF NOT EXISTS idx_pitching_game ON pitching_lines(game_id);
CREATE INDEX IF NOT EXISTS idx_pitching_player ON pitching_lines(player_name);
CREATE INDEX IF NOT EXISTS idx_pitching_bref ON pitching_lines(bref_id);

-- Detected milestones
CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    milestone_type TEXT NOT NULL,  -- e.g., 'perfect_games', 'multi_hr_games'
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    opponent TEXT NOT NULL,
    level TEXT,
    league TEXT,
    details TEXT,  -- JSON with milestone-specific stats (IP, K, HR, etc.)
    UNIQUE(game_id, milestone_type, player_name)
);

CREATE INDEX IF NOT EXISTS idx_milestones_type ON milestones(milestone_type);
CREATE INDEX IF NOT EXISTS idx_milestones_game ON milestones(game_id);
CREATE INDEX IF NOT EXISTS idx_milestones_player ON milestones(player_name);

-- Player crossover links (maps IDs across systems)
CREATE TABLE IF NOT EXISTS crossover_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    bref_id TEXT,
    mlb_api_id INTEGER,
    levels_seen TEXT,  -- comma-separated: 'NCAA,Double-A,Triple-A'
    ncaa_teams TEXT,
    pro_teams TEXT,
    ncaa_games INTEGER DEFAULT 0,
    pro_games INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(bref_id),
    UNIQUE(mlb_api_id)
);

CREATE INDEX IF NOT EXISTS idx_crossover_name ON crossover_links(player_name);
CREATE INDEX IF NOT EXISTS idx_crossover_bref ON crossover_links(bref_id);
CREATE INDEX IF NOT EXISTS idx_crossover_mlb ON crossover_links(mlb_api_id);

-- Draft data (for draft tracking feature)
CREATE TABLE IF NOT EXISTS draft_picks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    round INTEGER NOT NULL,
    pick_number INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    school TEXT,
    team TEXT NOT NULL,  -- drafting MLB team
    position TEXT,
    mlb_api_id INTEGER,
    bref_id TEXT,
    signed INTEGER DEFAULT 0,  -- 1 if signed, 0 if not
    bonus TEXT,
    raw_json TEXT,
    UNIQUE(year, round, pick_number)
);

CREATE INDEX IF NOT EXISTS idx_draft_player ON draft_picks(player_name);
CREATE INDEX IF NOT EXISTS idx_draft_school ON draft_picks(school);
CREATE INDEX IF NOT EXISTS idx_draft_mlb_id ON draft_picks(mlb_api_id);
CREATE INDEX IF NOT EXISTS idx_draft_bref ON draft_picks(bref_id);
CREATE INDEX IF NOT EXISTS idx_draft_year ON draft_picks(year);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
"""
