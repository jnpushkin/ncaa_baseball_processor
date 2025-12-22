# NCAA Baseball Processor

A Python tool for parsing college baseball box scores and generating statistics for NCAA Division I baseball games.

## Features

- Parse PDF box scores (converted to HTML) from various sources
- Track games attended across multiple seasons
- Generate Excel workbooks with player/team statistics
- Generate interactive HTML website with:
  - Game log
  - Player statistics (batting and pitching)
  - Team records
  - Stadium tracking
  - Venue/city information

## Installation

```bash
# Clone the repository
git clone https://github.com/jnpushkin/ncaa_baseball_processor.git
cd ncaa_baseball_processor

# Install dependencies
pip install -r requirements.txt

# Install Playwright for PDF processing (if needed)
playwright install
```

## Usage

### Basic Usage

```bash
# Convert PDFs to HTML first
python3 pdf_to_html.py

# Process games and generate outputs
python3 -m baseball_processor

# Process specific directory
python3 -m baseball_processor /path/to/html/files
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--output-excel FILE` | Excel output filename (default: Baseball_Stats.xlsx) |
| `--save-json` | Save intermediate JSON data |
| `--from-cache-only` | Load from cached JSON instead of parsing HTML |
| `--excel-only` | Generate only Excel, skip website |
| `--website-only` | Generate only website, skip Excel |
| `--verbose` | Enable debug output |

## Directory Structure

```
ncaa_baseball_processor/
├── baseball_processor/     # Core processing modules
│   ├── __init__.py
│   ├── main.py            # Entry point
│   ├── utils/
│   │   ├── stadiums.py    # Stadium coordinates and names
│   │   └── constants.py   # Conference data
│   └── website/           # HTML website generation
├── parsers/               # Box score parsing
│   └── metadata.py        # Game metadata extraction
├── cache/                 # Cached parsed game data (gitignored)
├── pdfs/                  # Input PDF files (gitignored)
├── html_output/           # Converted HTML files
├── rosters/               # Team roster data
└── README.md
```

## Data Sources

- **Box scores:** PDF files from team athletics websites or NCAA
- **Stadium data:** Custom database with coordinates for map visualization

## License

MIT License
