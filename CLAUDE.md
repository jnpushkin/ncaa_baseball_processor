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
- Similar architecture to MLB processor but for NCAA baseball data

## Do NOT
- Create nested `baseball_processor/baseball_processor/` directory structure
- Use `python` command (always `python3`)
