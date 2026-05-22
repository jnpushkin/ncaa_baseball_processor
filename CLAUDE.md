# Claude Code Instructions

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
- `--from-cache-only` and `--from-db` set `NCAA_BASEBALL_OFFLINE=1` so stale Chadwick cache data is loaded locally instead of refreshing over the network
- `--from-cache-only` with a single-game or NCAA API date source flag must not fetch on a cache miss
- Single-game/date source flags are exclusive source modes; do not silently add default NCAA/API/MiLB/Partner batches when they are used
- Sports-Reference sites hide tables in HTML comments for lazy loading - must extract and parse them with BeautifulSoup Comment class

## Error Handling
When encountering repeated errors or discovering project-specific quirks:
- Update this CLAUDE.md file with the finding
- Add to "Do NOT" section if it's a common mistake
- Add to "Architecture Notes" if it's a structural insight

## Do NOT
- Create nested `baseball_processor/baseball_processor/` directory structure
- Use `python` command (always `python3`)
