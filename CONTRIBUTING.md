# Contributing & Data Maintenance Guide

This document explains how to update the NCAA Baseball Processor when team information changes.

## Reference Data Locations

| Data Type | File Location |
|-----------|---------------|
| Stadium coordinates | `baseball_processor/utils/stadiums.py` |
| MiLB stadiums | `baseball_processor/utils/milb_stadiums.py` |
| Partner league stadiums | `baseball_processor/utils/partner_stadiums.py` |
| Conference data | `baseball_processor/utils/constants.py` |
| Team names normalization | `utils/names.py` → `UPPERCASE_TEAMS` |
| PDF format parsers | `parsers/format_a.py`, `parsers/format_b.py` |

## Common Update Scenarios

### 1. Adding a New Stadium

**Example:** Adding a new NCAA stadium

Edit `baseball_processor/utils/stadiums.py`:

```python
STADIUMS = {
    # ...existing stadiums...
    'New Stadium Name': {
        'team': 'Team Name',
        'city': 'City',
        'state': 'ST',
        'lat': 00.0000,
        'lng': -00.0000,
        'conference': 'Conference Name'
    },
}
```

### 2. Team Changes Conference

**Step 1:** Update stadium data with new conference:

```python
'Stadium Name': {
    'team': 'Team Name',
    'city': 'City',
    'state': 'ST',
    'lat': 00.0000,
    'lng': -00.0000,
    'conference': 'New Conference'  # Updated
}
```

**Step 2:** Update `constants.py` if conference lists are maintained there.

### 3. Adding a New PDF Format

NCAA baseball box scores come in various PDF formats. To add support for a new format:

1. **Create a new parser** in `parsers/`:
   ```
   parsers/format_c.py
   ```

2. **Update format detection** in `parsers/format_detection.py`:
   ```python
   def detect_format(html_content):
       # Add detection logic for new format
       if 'unique_identifier' in html_content:
           return 'format_c'
       # ...existing detection
   ```

3. **Register the parser** in `parsers/__init__.py`.

### 4. Adding MiLB Team Data

Edit `baseball_processor/utils/milb_stadiums.py`:

```python
MILB_STADIUMS = {
    'Team Name': {
        'stadium': 'Stadium Name',
        'city': 'City',
        'state': 'ST',
        'lat': 00.0000,
        'lng': -00.0000,
        'level': 'AAA',  # AAA, AA, A+, A, A-
        'affiliate': 'MLB Team'
    },
}
```

### 5. Updating Team Name Normalization

Teams with all-caps names or special formatting should be added to `utils/names.py`:

```python
UPPERCASE_TEAMS = {
    'lsu': 'LSU',
    'usc': 'USC',
    'ucla': 'UCLA',
    'unlv': 'UNLV',
    # Add new entries
    'newteam': 'NEWTEAM',
}
```

### 6. Adding Roster Data

Place roster CSV files in the `rosters/` directory:

```
rosters/
├── team_name_2024.csv
├── team_name_2025.csv
└── ...
```

CSV format:
```csv
name,number,position,class,bats,throws,hometown
John Smith,23,INF,Jr,R,R,Springfield IL
```

## PDF Processing Workflow

1. **Place PDFs** in `pdfs/` directory
2. **Convert to HTML** (if needed):
   ```bash
   python3 pdf_to_html.py
   ```
3. **Process games**:
   ```bash
   python3 -m baseball_processor
   ```

## Cache Management

**Clear all cache:**
```bash
rm -rf cache/*.json
```

**Clear specific game cache:**
```bash
rm cache/game_name.json
```

**Force re-parse specific game:**
```bash
python3 -m baseball_processor --no-cache path/to/game.pdf
```

## MiLB Integration

The processor can integrate MiLB data from the MLB Stats API:

```bash
# Process MiLB games
python3 -m baseball_processor --milb

# Process specific MiLB game by ID
python3 -m baseball_processor --milb-game 12345
```

MiLB game IDs are stored in `data/milb_game_ids.json`.

## MLB Game Tracker Integration

The processor can read cached data from MLB Game Tracker for player crossover:

```bash
# Include MLB data for crossover tracking
python3 -m baseball_processor --include-mlb
```

Requires MLB Game Tracker cache at the configured path in `constants.py`.

## Player Crossover Tracking

The system tracks players across:
- NCAA Baseball
- MiLB (Minor League Baseball)
- MLB (via MLB Game Tracker)
- Partner leagues (Cape Cod, Northwoods, etc.)

Configure crossover in `player_crossover.py`.

## Conference Reference

### Power 5 Conferences
- ACC
- Big 12
- Big Ten
- Pac-12
- SEC

### Other D1 Conferences
- AAC
- Atlantic 10
- Big East
- Big West
- CAA
- Conference USA
- Ivy League
- MAAC
- MAC
- Missouri Valley
- Mountain West
- Northeast
- Ohio Valley
- Patriot League
- SoCon
- Sun Belt
- WAC
- WCC

## After Making Changes

1. **Clear cache** to regenerate data:
   ```bash
   rm -rf cache/*.json
   ```

2. **Run tests** (if available):
   ```bash
   pytest tests/ -v
   ```

3. **Regenerate outputs**:
   ```bash
   python3 -m baseball_processor --from-cache-only
   ```

4. **Verify changes** in the generated Excel and HTML files.

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_helpers.py -v

# Run with coverage
pytest tests/ --cov=baseball_processor
```

## Type Checking

```bash
# Run mypy
mypy baseball_processor/

# Run on specific module
mypy baseball_processor/utils/helpers.py
```

## Troubleshooting

### PDF Parsing Errors

1. Check the PDF format matches a supported parser
2. Try converting with `pdf_to_html.py` first
3. Check for OCR issues in scanned PDFs

### Missing Player Data

1. Verify roster files are up to date
2. Check name normalization in `utils/names.py`
3. Review the name matching logic in `name_matcher.py`

### Stadium Not Found

1. Add the stadium to the appropriate stadiums file
2. Verify coordinates using Google Maps
3. Check conference assignment is correct
