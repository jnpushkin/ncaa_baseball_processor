#!/usr/bin/env python3
"""
Name Matcher for NCAAB Box Scores

Matches abbreviated player names from PDFs (e.g., "McCarthy, J.", "J. McCarthy")
to full roster entries with Baseball Reference IDs.
"""

import json
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


# Minimum confidence threshold for accepting a match
# Matches below this threshold will be rejected to prevent incorrect player assignments
MIN_CONFIDENCE = 0.5


@dataclass
class MatchResult:
    """Result of a name match attempt."""
    matched: bool
    player: Optional[dict] = None
    confidence: float = 0.0
    match_type: str = ""  # "exact", "last_initial", "last_only", "fuzzy"


class NameMatcher:
    """Matches abbreviated names to full roster entries."""

    def __init__(self, roster_path: Optional[str] = None):
        """
        Initialize the matcher with an optional roster.

        Args:
            roster_path: Path to a roster JSON file
        """
        self.rosters = {}  # team_name -> list of players
        self.players_by_last = {}  # last_name.lower() -> list of players

        if roster_path:
            self.load_roster(roster_path)

    def load_roster(self, roster_path: str, team_key: Optional[str] = None) -> None:
        """
        Load a roster from a JSON file.

        Args:
            roster_path: Path to roster JSON file
            team_key: Optional key to use for this team (default: from file)
        """
        with open(roster_path, 'r') as f:
            roster = json.load(f)

        team_name = team_key or roster.get('team_name', Path(roster_path).stem)
        players = roster.get('players', [])

        # Extract year from filename (e.g., "2023_virginia_cavaliers.json")
        filename = Path(roster_path).stem
        year_match = re.match(r'^(\d{4})_', filename)
        roster_year = int(year_match.group(1)) if year_match else None

        self.rosters[team_name] = players

        # Index by last name for fast lookup
        for player in players:
            # Add roster year to player for later matching
            player['_roster_year'] = roster_year

            last_name = player.get('last_name', '').lower()
            if last_name:
                if last_name not in self.players_by_last:
                    self.players_by_last[last_name] = []
                self.players_by_last[last_name].append(player)

    def load_rosters_from_dir(self, roster_dir: str) -> int:
        """
        Load all roster JSON files from a directory.

        Args:
            roster_dir: Directory containing roster JSON files

        Returns:
            Number of rosters loaded
        """
        roster_path = Path(roster_dir)
        count = 0

        for json_file in roster_path.glob("*.json"):
            try:
                # Handle supplemental pitchers file differently
                if 'supplemental' in json_file.name:
                    self._load_supplemental(str(json_file))
                else:
                    self.load_roster(str(json_file))
                count += 1
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading {json_file}: {e}")

        return count

    def _load_supplemental(self, filepath: str) -> None:
        """Load supplemental player data (pitchers not in main rosters)."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        players = data.get('players', [])
        for player in players:
            last_name = player.get('last_name', '').lower()
            if last_name:
                if last_name not in self.players_by_last:
                    self.players_by_last[last_name] = []
                self.players_by_last[last_name].append(player)

    # Known typos in source PDFs: {typo: correction}
    TYPO_CORRECTIONS = {
        'FUNY, Matty': 'Fung, Matty',
        'FUNY': 'Fung',
    }

    def clean_name(self, name: str) -> str:
        """
        Clean a player name by removing position annotations and other artifacts.

        Args:
            name: Raw player name from box score

        Returns:
            Cleaned name string
        """
        if not name:
            return name

        # Fix known typos
        if name in self.TYPO_CORRECTIONS:
            name = self.TYPO_CORRECTIONS[name]

        # Remove position annotations like "3b/1b", "pr/2b", "cf/lf", "(ph/lf)"
        # These appear at the end of names, sometimes with space, sometimes without
        name = re.sub(r'\s*\([^)]*\)\s*$', '', name)  # (ph/lf) at end
        name = re.sub(r'\s*[123]?[bB]/[123]?[bB]\s*$', '', name)  # 3b/1b at end
        name = re.sub(r'\s+(?:ph|pr|dh|cf|lf|rf|ss|[123]?b|c)/(?:ph|pr|dh|cf|lf|rf|ss|[123]?b|c)\s*$', '', name, flags=re.IGNORECASE)  # pr/2b, cf/lf
        name = re.sub(r'\s+(?:ph|pr|dh|cf|lf|rf|ss|[123]b|c)\s*$', '', name, flags=re.IGNORECASE)  # Single position

        # Remove game note prefixes like "SB:", "2B:", "CS:", "E:", "SF:", "SH:"
        name = re.sub(r'^(SB|2B|3B|HR|CS|E|SF|SH|HBP|IBB|SO|WP|PB|BK):\s*', '', name)

        # Remove trailing stat notations like "(1)"
        name = re.sub(r'\s*\(\d+\)\s*', ' ', name)

        # Remove "Totals" and anything after
        if 'Totals' in name:
            name = name.split('Totals')[0]

        # Handle ALL CAPS names - convert to title case but preserve suffixes
        if name.isupper() and len(name) > 2:
            # Split on comma if present
            if ',' in name:
                parts = name.split(',', 1)
                last = parts[0].strip().title()
                first = parts[1].strip().title() if len(parts) > 1 else ''
                # Preserve Jr., Sr., III, etc.
                first = re.sub(r'\bIii\b', 'III', first)
                first = re.sub(r'\bIi\b', 'II', first)
                first = re.sub(r'\bIv\b', 'IV', first)
                name = f"{last}, {first}" if first else last
            else:
                name = name.title()
                name = re.sub(r'\bIii\b', 'III', name)
                name = re.sub(r'\bIi\b', 'II', name)
                name = re.sub(r'\bIv\b', 'IV', name)

        return name.strip()

    def parse_name(self, name: str) -> dict:
        """
        Parse a name string into components.

        Handles formats:
        - "Last, First" or "Last, F."
        - "First Last"
        - "F. Last"

        Returns:
            Dict with 'first', 'last', 'first_initial', 'full_first' keys
        """
        # Clean the name first
        name = self.clean_name(name)
        name = name.strip()
        result = {
            'first': '',
            'last': '',
            'first_initial': '',
            'full_first': False,
            'original': name
        }

        if not name:
            return result

        # Handle "Last, First" or "Last, F." format
        if ',' in name:
            parts = name.split(',', 1)
            result['last'] = parts[0].strip()
            first_part = parts[1].strip() if len(parts) > 1 else ''

            # Check if it's an initial (single letter or letter with period)
            if re.match(r'^[A-Za-z]\.?$', first_part):
                result['first_initial'] = first_part.rstrip('.').upper()
                result['full_first'] = False
            else:
                result['first'] = first_part
                result['first_initial'] = first_part[0].upper() if first_part else ''
                result['full_first'] = True

        # Handle "F. Last" format
        elif re.match(r'^[A-Za-z]\.\s+', name):
            match = re.match(r'^([A-Za-z])\.\s+(.+)$', name)
            if match:
                result['first_initial'] = match.group(1).upper()
                result['last'] = match.group(2).strip()
                result['full_first'] = False

        # Handle "First Last" format
        else:
            parts = name.split()
            if len(parts) >= 2:
                # Check for suffixes
                suffixes = {'jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv', 'v'}
                if parts[-1].lower() in suffixes and len(parts) > 2:
                    result['last'] = f"{parts[-2]} {parts[-1]}"
                    result['first'] = ' '.join(parts[:-2])
                else:
                    result['last'] = parts[-1]
                    result['first'] = ' '.join(parts[:-1])

                result['first_initial'] = result['first'][0].upper() if result['first'] else ''
                result['full_first'] = True
            elif len(parts) == 1:
                # Single name - assume it's last name
                result['last'] = parts[0]

        return result

    def match(self, name: str, team: Optional[str] = None, number: Optional[str] = None, year: Optional[int] = None) -> MatchResult:
        """
        Match a name to a roster entry.

        Args:
            name: Player name (can be abbreviated)
            team: Optional team name to restrict search
            number: Optional jersey number for disambiguation
            year: Optional game year to prefer matching roster year

        Returns:
            MatchResult with matched player info
        """
        parsed = self.parse_name(name)

        if not parsed['last']:
            return MatchResult(matched=False)

        last_lower = parsed['last'].lower()

        # Handle suffixes and compound last names - try variants
        suffixes = ['jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv', 'v']
        prefixes = ['van', 'de', 'la', 'le', 'von', 'del', 'da', 'mc', 'mac', "o'"]
        last_variants = [last_lower]

        # Check if last name has a suffix
        last_parts = last_lower.split()
        if len(last_parts) > 1:
            if last_parts[-1] in suffixes:
                # Add variant without suffix
                last_variants.append(' '.join(last_parts[:-1]))
            elif last_parts[0] in prefixes:
                # Compound last name like "Van Sickle" - also try just the second part
                last_variants.append(' '.join(last_parts[1:]))

        # Add variants with common suffixes
        for suf in ['jr', 'jr.', 'iii', 'ii']:
            last_variants.append(f"{last_lower} {suf}")

        # Get candidate players from all variants
        candidates = []
        for variant in last_variants:
            candidates.extend(self.players_by_last.get(variant, []))

        # Track if team filtering was applied
        team_filtered = False
        year_filtered = False

        # Filter by year FIRST - this is important because the same player may appear
        # in multiple year rosters with the same bref_id. We want to match to the
        # roster version from the game's year before deduplication removes alternatives.
        if year and candidates:
            year_matches = [p for p in candidates if p.get('_roster_year') == year]
            if year_matches:
                candidates = year_matches
                year_filtered = True

        # Remove duplicates while preserving order (after year filter)
        seen = set()
        unique_candidates = []
        for c in candidates:
            cid = c.get('bref_id', id(c))
            if cid not in seen:
                seen.add(cid)
                unique_candidates.append(c)
        candidates = unique_candidates

        # Filter by team if specified
        if team and candidates:
            team_lower = team.lower()
            filtered = [p for p in candidates
                       if team_lower in str(self.get_player_team(p)).lower()]
            if filtered:
                candidates = filtered
                team_filtered = True

        if not candidates:
            return MatchResult(matched=False)

        # If only one candidate after filtering, higher confidence
        if len(candidates) == 1:
            # Confidence boost if team/year was specified and matched
            base_conf = 0.9 if parsed['full_first'] else (0.85 if (team_filtered or year_filtered) else 0.7)
            return MatchResult(
                matched=True,
                player=candidates[0],
                confidence=base_conf,
                match_type="last_only" if not parsed['first_initial'] else "last_initial"
            )

        # Multiple candidates - try to disambiguate

        # Try exact first name match
        if parsed['full_first'] and parsed['first']:
            first_lower = parsed['first'].lower()
            exact_matches = [p for p in candidates
                           if p.get('first_name', '').lower() == first_lower]
            if len(exact_matches) == 1:
                return MatchResult(
                    matched=True,
                    player=exact_matches[0],
                    confidence=1.0,
                    match_type="exact"
                )

        # Try first initial match
        if parsed['first_initial']:
            initial = parsed['first_initial'].upper()
            initial_matches = [p for p in candidates
                             if p.get('first_name', '').upper().startswith(initial)]
            if len(initial_matches) == 1:
                return MatchResult(
                    matched=True,
                    player=initial_matches[0],
                    confidence=0.85,
                    match_type="last_initial"
                )
            elif len(initial_matches) > 1:
                # Multiple matches with same initial - use jersey number if available
                if number:
                    number_matches = [p for p in initial_matches
                                     if str(p.get('number', '')) == str(number)]
                    if len(number_matches) == 1:
                        return MatchResult(
                            matched=True,
                            player=number_matches[0],
                            confidence=0.95,
                            match_type="last_initial_number"
                        )

                # Return first match with lower confidence
                return MatchResult(
                    matched=True,
                    player=initial_matches[0],
                    confidence=0.6,
                    match_type="last_initial_ambiguous"
                )

        # No first name info - try jersey number
        if number:
            number_matches = [p for p in candidates
                            if str(p.get('number', '')) == str(number)]
            if len(number_matches) == 1:
                return MatchResult(
                    matched=True,
                    player=number_matches[0],
                    confidence=0.8,
                    match_type="last_number"
                )

        # Return first candidate with low confidence
        return MatchResult(
            matched=True,
            player=candidates[0],
            confidence=0.4,
            match_type="last_only_ambiguous"
        )

    def get_player_team(self, player: dict) -> str:
        """Get the team name for a player."""
        for team_name, players in self.rosters.items():
            if player in players:
                return team_name
        return ""

    def get_bref_id(self, name: str, team: Optional[str] = None, number: Optional[str] = None, year: Optional[int] = None) -> Optional[str]:
        """
        Get the Baseball Reference ID for a player name.

        Args:
            name: Player name
            team: Optional team name
            number: Optional jersey number
            year: Optional game year

        Returns:
            bref_id if found, None otherwise
        """
        result = self.match(name, team, number, year)
        if result.matched and result.player:
            return result.player.get('bref_id')
        return None

    def get_full_name(self, name: str, team: Optional[str] = None, number: Optional[str] = None, year: Optional[int] = None) -> Optional[str]:
        """
        Get the full name for an abbreviated player name.

        Args:
            name: Player name (possibly abbreviated)
            team: Optional team name
            number: Optional jersey number
            year: Optional game year

        Returns:
            Full name if found, None otherwise
        """
        result = self.match(name, team, number, year)
        if result.matched and result.player:
            return result.player.get('name')
        return None


def enrich_game_data(game_data: dict, matcher: NameMatcher) -> dict:
    """
    Enrich parsed game data with bref_ids for all players.

    Args:
        game_data: Parsed game data from ncaab_parser
        matcher: NameMatcher instance with loaded rosters

    Returns:
        Enriched game data with bref_ids added to player entries
    """
    # Get team names for matching
    away_team = game_data.get('metadata', {}).get('away_team', '')
    home_team = game_data.get('metadata', {}).get('home_team', '')

    # Extract year from game date
    game_date = game_data.get('metadata', {}).get('date', '')
    game_year = None
    if game_date:
        # Try different date formats
        year_match = re.search(r'(\d{4})', game_date)
        if year_match:
            game_year = int(year_match.group(1))

    # Enrich batting stats
    for player in game_data.get('box_score', {}).get('away_batting', []):
        _enrich_player(player, matcher, away_team, game_year)

    for player in game_data.get('box_score', {}).get('home_batting', []):
        _enrich_player(player, matcher, home_team, game_year)

    # Enrich pitching stats
    for player in game_data.get('box_score', {}).get('away_pitching', []):
        _enrich_player(player, matcher, away_team, game_year)

    for player in game_data.get('box_score', {}).get('home_pitching', []):
        _enrich_player(player, matcher, home_team, game_year)

    return game_data


def _enrich_player(player: dict, matcher: NameMatcher, team: str, year: Optional[int] = None) -> None:
    """Add bref_id and full_name to a player dict."""
    name = player.get('name', '')
    number = player.get('number', '')

    result = matcher.match(name, team, number, year)

    # Only accept matches above the minimum confidence threshold
    if result.matched and result.player and result.confidence >= MIN_CONFIDENCE:
        player['bref_id'] = result.player.get('bref_id')
        player['full_name'] = result.player.get('name')
        player['match_confidence'] = result.confidence
    else:
        player['bref_id'] = None
        player['full_name'] = None
        player['match_confidence'] = result.confidence if result.matched else 0.0


# CLI for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Name Matcher Test Utility")
        print("\nUsage:")
        print("  python name_matcher.py <roster_dir> <name> [team]")
        print("\nExamples:")
        print('  python name_matcher.py rosters "McCarthy, J."')
        print('  python name_matcher.py rosters "J. McCarthy" "Virginia"')
        print('  python name_matcher.py rosters "Henry Ford"')
        sys.exit(1)

    roster_dir = sys.argv[1]
    name = sys.argv[2]
    team = sys.argv[3] if len(sys.argv) > 3 else None

    matcher = NameMatcher()
    count = matcher.load_rosters_from_dir(roster_dir)
    print(f"Loaded {count} rosters")
    print(f"Total players indexed: {sum(len(p) for p in matcher.players_by_last.values())}")

    print(f"\nSearching for: '{name}'" + (f" (team: {team})" if team else ""))

    result = matcher.match(name, team)

    if result.matched:
        print(f"\nMatch found!")
        print(f"  Full name: {result.player.get('name')}")
        print(f"  bref_id: {result.player.get('bref_id')}")
        print(f"  Confidence: {result.confidence:.0%}")
        print(f"  Match type: {result.match_type}")
    else:
        print("\nNo match found")
