# Codex Instructions

## Python
Always use `python3` instead of `python` for all commands.

## Project Structure
- `baseball_processor/` - Main Python package
- `baseball_processor/engines/` - Source-neutral event detection
- `baseball_processor/normalization.py` - Canonical adapter for mixed NCAA/MiLB/Partner source shapes
- `baseball_processor/processors/` - Player stats, game logs, team records, milestone detection
- `parsers/` - NCAA PDF/API, MiLB API, and Partner League parsers
- `website/` - Website generation

## Running the Processor
```bash
python3 -m baseball_processor [input_path]
```

## Key Files
- `baseball_processor/engines/milestone_engine.py` - Milestone detection rules
- `baseball_processor/processors/milestones.py` - Milestone DataFrame wrapper
- `baseball_processor/website/generator.py` - Website generation
- `baseball_processor/website/serializers.py` - Website JSON serializers
- `baseball_processor/website/parity.py` - Non-blocking website data parity checks
- `baseball_processor/audit.py` / `scripts/audit_data_integrity.py` - Data-preservation audit for cache and generated website output

## Architecture Notes
- Milestone engine uses tiered elif pattern (only highest tier reported per category)
- Processors should use `baseball_processor.normalization.normalize_game()` when source-specific stat key aliases matter
- Website per-game detail JSON should be emitted from normalized rows so the React modal does not depend on parser-specific stat names
- Run `python3 scripts/audit_data_integrity.py --strict-generated-from-cache` after refactors that could affect game identity or generated website coverage
- Covers NCAA and MiLB/Partner League baseball data (no MLB)
- MiLB data comes from MLB Stats API (statsapi.mlb.com) which serves minor league data
- Player crossover tracking links NCAA and MiLB players via Chadwick Bureau Register
- Missing NCAA player B-Ref links should be resolved by matching the player's team/year roster scraped from Baseball-Reference first; avoid global Chadwick exact-name matching unless team/year context makes the match unambiguous
- `--from-cache-only` and `--from-db` set `NCAA_BASEBALL_OFFLINE=1` so stale Chadwick cache data is loaded locally instead of refreshing over the network
- `--from-cache-only` with a single-game or NCAA API date source flag must not fetch on a cache miss
- Single-game/date source flags are exclusive source modes; do not silently add default NCAA/API/MiLB/Partner batches when they are used
- Current affiliated MiLB team/league/venue metadata is season-dependent; run `python3 scripts/sync_milb_metadata.py --strict-location` to refresh `data/milb_active_teams_<season>.json`, then run `python3 scripts/audit_milb_metadata.py --strict --require-generated` before deploys where the pro checklist/map matters
- Current MLB Draft League club metadata is season-dependent; run `python3 scripts/sync_mlb_draft_league_metadata.py --strict-location` to refresh `data/mlb_draft_league_teams_<season>.json`, then run `python3 scripts/audit_mlb_draft_league_metadata.py --strict --require-generated`
- `MILB_STADIUM_DATA` should be treated as coordinate/logo/history overrides; active affiliated checklist identity should come from generated MiLB metadata when present
- MLB Draft League games can arrive through the MLB Stats API with `format='milb_api'`; parser/normalization/generator logic must let `metadata.source='partner'` take precedence over transport format
- MLB Stats API `sportId=22` includes non-Draft-League clubs, college/tournament teams, and special opponents like Canada/Mexico; filter generated MLB Draft League checklist metadata through the official `mlbdraftleague.com/teams` club list
- MiLB venues can host multiple active teams; keep unique internal venue keys separate from display venue names rather than assuming the stadium-map dict key is always the public stadium label
- Pioneer League HTML hitter tables omit XBH/SB columns; parse `.stats-summary` batting notes and merge them back into player rows before processing
- NCAA API pitching `np` is currently a strikes proxy and pitcher `hr` is fabricated as zero; do not treat those as authoritative source-disagreement fields against PDF box scores
- NCAA API batting `k` can be unavailable even when placeholder or pitcher-echo rows have strikeout values; ignore placeholder rows and impossible `AB=0, K>0` batting echoes when deciding source-disagreement authority
- NCAA API names can be initial-only or lowercase-clipped (`A. Anderson`, `aide Taurek`); do not let those overwrite better PDF/roster display names or source-quality labels
- Sports-Reference sites hide tables in HTML comments for lazy loading - must extract and parse them with BeautifulSoup Comment class
- MiLB Partner League detection must use exact normalized league-name matching; substring checks make `Atlantic League` match affiliated `South Atlantic League` games and misclassify them as Partner/Independent

## Error Handling
When encountering repeated errors or discovering project-specific quirks:
- Update this AGENTS.md file with the finding
- Add to "Do NOT" section if it's a common mistake
- Add to "Architecture Notes" if it's a structural insight

## Do NOT
- Create nested `baseball_processor/baseball_processor/` directory structure
- Use `python` command (always `python3`)
- Do not fill missing player `bref_id` values from a name-only global Chadwick match when multiple same-name candidates exist; fetch/use the Baseball-Reference roster for that team and season
- Do not treat NCAA API player names that start lowercase or use single initials as full names when merging with PDF rows
- Do not classify a parsed partner/Draft League game as affiliated MiLB just because it was fetched through the MLB Stats API
- Do not add Canada/Mexico or other special-opponent `sportId=22` entries to the MLB Draft League checklist/map unless they appear on the official Draft League teams page
