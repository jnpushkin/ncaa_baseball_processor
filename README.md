# NCAA Baseball Processor

A Python tool for tracking baseball games across NCAA, MiLB, and independent Partner Leagues. Parses box scores, detects milestones, tracks player crossover between levels, and generates an interactive website and Excel workbook.

## Quick Start

```bash
# Install
git clone https://github.com/jnpushkin/ncaa_baseball_processor.git
cd ncaa_baseball_processor
pip3 install -r requirements.txt

# Download a box score PDF from a team's athletics website, then:
cp ~/Downloads/boxscore.pdf pdfs/20260321_UConn_vs_SanDiegoState_SanDiego.pdf

# Run the processor
python3 -m baseball_processor
```

This parses all PDFs in `pdfs/`, fetches any MiLB/Partner League games listed in their respective `game_ids.txt` files, detects milestones, and generates:
- `Baseball_Stats.html` — interactive single-page website (auto-deployed to Surge.sh)
- `Baseball_Stats.xlsx` — Excel workbook with detailed statistics

To regenerate output from previously cached data without re-parsing:
```bash
python3 -m baseball_processor --from-cache-only
```

## Features

- Parse NCAA PDF box scores with automatic format detection
- Fetch MiLB game data from the MLB Stats API
- Fetch Partner League games (Pioneer, Atlantic, American Association, Frontier)
- Track player crossover between NCAA and MiLB via Chadwick Bureau Register
- Detect 43 types of statistical milestones
- Generate interactive single-page HTML website with game log, player stats, team records, stadium map, scorigami, and schedule
- Generate Excel workbook with detailed statistics
- Auto-deploy to Surge.sh

## Installation

```bash
git clone https://github.com/jnpushkin/ncaa_baseball_processor.git
cd ncaa_baseball_processor
pip3 install -r requirements.txt
```

## Adding Games

### NCAA Games

1. Go to the home team's athletics website and find the box score page for the game
2. Download the box score PDF (usually linked on the page)
3. Rename and save it to the `pdfs/` directory with this naming convention:
   ```
   YYYYMMDD_AwayTeam_vs_HomeTeam_City.pdf
   ```
   For example: `20250214_Nevada_vs_California_Berkeley.pdf`
   - Use the game date in `YYYYMMDD` format
   - Use team names without spaces (e.g. `SanDiegoState`, not `San Diego State`)
   - City is the home team's city (no spaces)
4. Run the processor:
   ```bash
   python3 -m baseball_processor
   ```

The PDF is automatically parsed, cached as JSON in `cache/`, and included in output generation. On subsequent runs, cached games are loaded instantly unless `--no-cache` is used.

### MiLB Games

1. Find the game on MiLB.com and get the `game_pk` from the URL
2. Add the ID to `milb/game_ids.txt` (one per line):
   ```
   788401
   784595
   ```
3. Run:
   ```bash
   python3 -m baseball_processor
   ```

Or process a single game directly:
```bash
python3 -m baseball_processor --milb-game 788401
```

### Partner League Games

1. Find the game on the league's website and get the game ID
2. Add it to `partner/game_ids.txt` in the format `league:game_id`:
   ```
   pioneer:20240828_fhp1
   atlantic:612414
   american_association:497562
   ```
3. Run:
   ```bash
   python3 -m baseball_processor
   ```

Or process a single game directly:
```bash
python3 -m baseball_processor --partner-game pioneer:20240828_fhp1
```

**Supported Partner Leagues:**
| League | ID Source |
|--------|----------|
| Pioneer League | Game code from pioneerleague.com URL (e.g. `20240828_fhp1`) |
| Atlantic League | `gameid` from Pointstreak URL |
| American Association | `gameid` from Pointstreak URL |
| Frontier League | `gameid` from Pointstreak URL |

## Usage

```bash
# Process all games (NCAA PDFs + MiLB + Partner League)
python3 -m baseball_processor

# Regenerate output from cached data only (no parsing or API calls)
python3 -m baseball_processor --from-cache-only

# Process a specific PDF directory
python3 -m baseball_processor /path/to/pdfs
```

### Command Line Options

**Input Options:**

| Option | Description |
|--------|-------------|
| `input_path` | Path to PDF file or directory (default: `pdfs/`) |
| `--from-cache-only` | Load all games from cache (no parsing or API calls) |
| `--no-cache` | Re-parse all PDFs (ignore cache) |

**Output Options:**

| Option | Description |
|--------|-------------|
| `-o`, `--output-excel FILE` | Excel output filename (default: `Baseball_Stats.xlsx`) |
| `--save-json` | Save intermediate JSON data file |
| `--excel-only` | Generate only Excel, skip website |
| `--website-only` | Generate only website, skip Excel |

**Game Source Options:**

| Option | Description |
|--------|-------------|
| `--no-milb` | Exclude MiLB games |
| `--milb-only` | Process only MiLB games (skip NCAA) |
| `--milb-game ID` | Process a single MiLB game by `game_pk` |
| `--no-partner` | Exclude Partner League games |
| `--partner-game ID` | Process a single Partner League game (format: `league:game_id`) |
| `--crossover` | Generate player crossover report |

**Schedule Options:**

| Option | Description |
|--------|-------------|
| `--schedule` | Scrape upcoming game schedule from D1Baseball.com |
| `--refresh-schedule` | Force refresh schedule cache |
| `--schedule-days N` | Number of days ahead to scrape (default: full season Feb 14 - Jun 30) |

**Deploy Options:**

| Option | Description |
|--------|-------------|
| `--no-deploy` | Skip automatic Surge.sh deployment |
| `--deploy-domain DOMAIN` | Surge domain (default: `ncaa-baseball.surge.sh`) |

## Directory Structure

```
ncaa_baseball_processor/
├── baseball_processor/     # Main Python package
│   ├── main.py            # Entry point
│   ├── engines/           # Milestone detection (43 types)
│   ├── parsers/           # HTML parsing for NCAA stats
│   ├── excel/             # Excel workbook generation
│   ├── utils/             # Constants, stadium data
│   └── website/           # HTML website generation
├── parsers/               # Box score format parsers
├── pdfs/                  # Input NCAA PDF box scores
├── cache/                 # Cached parsed NCAA game data
├── milb/
│   ├── game_ids.txt       # MiLB game IDs to process
│   └── cache/             # Cached MiLB game data
├── partner/
│   ├── game_ids.txt       # Partner League game IDs to process
│   └── cache/             # Cached Partner League game data
├── rosters/               # Team roster JSON files
├── data/                  # Miscellaneous data files
└── README.md
```

## Data Sources

- **NCAA box scores:** PDF files from team athletics websites
- **MiLB data:** MLB Stats API (`statsapi.mlb.com`)
- **Partner Leagues:** Pioneer League website, Pointstreak (Atlantic, American Association, Frontier)
- **Player crossover:** Chadwick Bureau Register
- **Stadium data:** Custom database with coordinates for map visualization
- **Schedule:** D1Baseball.com

## License

MIT License
