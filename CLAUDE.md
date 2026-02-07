# Claude Code Instructions

## Python
Always use `python3` instead of `python` for all commands.

## Project Structure
- `baseball_processor/` - Main Python package
- `engines/` - Milestone detection (43 types)
- `parsers/` - HTML parsing for NCAA stats
- `website/` - Website generation

## Running the Processor
```bash
python3 -m baseball_processor [input_path]
```

## Key Files
- `baseball_processor/engines/milestone_engine.py` - Milestone detection
- `baseball_processor/website/generator.py` - Website generation

## Architecture Notes
- Milestone engine uses tiered elif pattern (only highest tier reported per category)
- Covers NCAA and MiLB/Partner League baseball data (no MLB)
- MiLB data comes from MLB Stats API (statsapi.mlb.com) which serves minor league data
- Player crossover tracking links NCAA and MiLB players via Chadwick Bureau Register
- Sports-Reference sites hide tables in HTML comments for lazy loading - must extract and parse them with BeautifulSoup Comment class

## Error Handling
When encountering repeated errors or discovering project-specific quirks:
- Update this CLAUDE.md file with the finding
- Add to "Do NOT" section if it's a common mistake
- Add to "Architecture Notes" if it's a structural insight

## Do NOT
- Create nested `baseball_processor/baseball_processor/` directory structure
- Use `python` command (always `python3`)
