"""
Player ID unification using the Chadwick Bureau Register.

Maps between different baseball player ID systems:
- key_bbref_minors: Baseball-Reference minors/register format (e.g., "fielde001pri")
- key_bbref: Baseball-Reference MLB format (e.g., "fieldpr01")
- key_mlbam: MLB Stats API numeric ID (e.g., 425902)

Data source: https://github.com/chadwickbureau/register
"""

import csv
import os
import json
import ssl
import certifi
from pathlib import Path
from typing import Dict, Optional, Tuple
import urllib.request
import urllib.error
import time
from datetime import datetime, timedelta

# Cache directory for Chadwick data
CHADWICK_CACHE_DIR = Path(__file__).parent.parent.parent / 'chadwick_data'
CHADWICK_RAW_URL = 'https://raw.githubusercontent.com/chadwickbureau/register/master/data'

# Auto-refresh cache if older than this many days
CACHE_MAX_AGE_DAYS = 7


class PlayerIDMapper:
    """
    Maps player IDs between different baseball ID systems.

    Uses the Chadwick Bureau Register for authoritative mappings.
    """

    def __init__(self, auto_download: bool = True):
        """
        Initialize the player ID mapper.

        Args:
            auto_download: If True, automatically download Chadwick data if not cached
        """
        self.register_to_mlb: Dict[str, str] = {}  # bbref_minors -> bbref
        self.mlb_to_register: Dict[str, str] = {}  # bbref -> bbref_minors
        self.mlbam_to_register: Dict[int, str] = {}  # mlbam -> bbref_minors
        self.mlbam_to_mlb: Dict[int, str] = {}  # mlbam -> bbref
        self.register_to_mlbam: Dict[str, int] = {}  # bbref_minors -> mlbam
        self.mlb_to_mlbam: Dict[str, int] = {}  # bbref -> mlbam

        # Player names for reference
        self.register_to_name: Dict[str, str] = {}
        self.mlb_to_name: Dict[str, str] = {}
        self.mlbam_to_name: Dict[int, str] = {}

        self._loaded = False

        if auto_download:
            self.ensure_data()

    def ensure_data(self, force_refresh: bool = False) -> bool:
        """
        Ensure Chadwick data is downloaded and loaded.

        Auto-refreshes if cache is older than CACHE_MAX_AGE_DAYS.

        Args:
            force_refresh: If True, force re-download even if cache exists

        Returns:
            True if data was loaded successfully
        """
        if self._loaded and not force_refresh:
            return True

        cache_file = CHADWICK_CACHE_DIR / 'player_id_map.json'

        # Check if cache needs refresh (older than max age)
        needs_refresh = force_refresh
        if cache_file.exists() and not force_refresh:
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age > timedelta(days=CACHE_MAX_AGE_DAYS):
                print(f"Chadwick cache is {cache_age.days} days old, refreshing...")
                needs_refresh = True

        # Try to load from cache if it's fresh
        if cache_file.exists() and not needs_refresh:
            try:
                self._load_from_cache(cache_file)
                return True
            except Exception as e:
                print(f"Failed to load cache: {e}")
                needs_refresh = True

        # Download fresh data
        if needs_refresh:
            # Delete old CSV files to force re-download
            for old_csv in CHADWICK_CACHE_DIR.glob('people-*.csv'):
                old_csv.unlink()

        # Download and process Chadwick data
        if not self._download_chadwick_data():
            # If download fails but we have a cache, use it anyway
            if cache_file.exists():
                print("Download failed, using existing cache")
                try:
                    self._load_from_cache(cache_file)
                    return True
                except:
                    pass
            return False

        # Process the CSV files
        self._process_chadwick_data()

        # Save to cache
        self._save_to_cache(cache_file)

        return True

    def _download_chadwick_data(self) -> bool:
        """Download Chadwick register CSV files."""
        CHADWICK_CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Create SSL context with certifi certificates
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            # Fallback: disable SSL verification (not ideal but works)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        # Download each file (people-0.csv through people-f.csv)
        files_to_download = [f'people-{c}.csv' for c in '0123456789abcdef']

        for filename in files_to_download:
            local_path = CHADWICK_CACHE_DIR / filename

            # Skip if already downloaded
            if local_path.exists():
                continue

            url = f'{CHADWICK_RAW_URL}/{filename}'
            print(f"Downloading {filename}...")

            try:
                request = urllib.request.Request(url)
                with urllib.request.urlopen(request, context=ssl_context) as response:
                    with open(local_path, 'wb') as out_file:
                        out_file.write(response.read())
                time.sleep(0.5)  # Be polite to GitHub
            except urllib.error.URLError as e:
                print(f"Failed to download {filename}: {e}")
                return False

        return True

    def _process_chadwick_data(self):
        """Process downloaded Chadwick CSV files to build ID mappings."""
        files = list(CHADWICK_CACHE_DIR.glob('people-*.csv'))

        for csv_file in files:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    key_bbref = row.get('key_bbref', '').strip()
                    key_bbref_minors = row.get('key_bbref_minors', '').strip()
                    key_mlbam = row.get('key_mlbam', '').strip()

                    # Build player name
                    name_first = row.get('name_first', '').strip()
                    name_last = row.get('name_last', '').strip()
                    full_name = f"{name_first} {name_last}".strip()

                    # Map register to MLB
                    if key_bbref_minors and key_bbref:
                        self.register_to_mlb[key_bbref_minors] = key_bbref
                        self.mlb_to_register[key_bbref] = key_bbref_minors

                    # Map MLBAM to other IDs
                    if key_mlbam:
                        try:
                            mlbam_int = int(key_mlbam)
                            if key_bbref_minors:
                                self.mlbam_to_register[mlbam_int] = key_bbref_minors
                                self.register_to_mlbam[key_bbref_minors] = mlbam_int
                            if key_bbref:
                                self.mlbam_to_mlb[mlbam_int] = key_bbref
                                self.mlb_to_mlbam[key_bbref] = mlbam_int
                            if full_name:
                                self.mlbam_to_name[mlbam_int] = full_name
                        except ValueError:
                            pass

                    # Store names
                    if key_bbref_minors and full_name:
                        self.register_to_name[key_bbref_minors] = full_name
                    if key_bbref and full_name:
                        self.mlb_to_name[key_bbref] = full_name

        self._loaded = True
        print(f"Loaded {len(self.register_to_mlb)} register->MLB mappings")
        print(f"Loaded {len(self.mlbam_to_register)} MLBAM->register mappings")
        print(f"Loaded {len(self.mlbam_to_mlb)} MLBAM->MLB mappings")

    def _load_from_cache(self, cache_file: Path):
        """Load mappings from JSON cache."""
        with open(cache_file, 'r') as f:
            data = json.load(f)

        self.register_to_mlb = data.get('register_to_mlb', {})
        self.mlb_to_register = data.get('mlb_to_register', {})
        self.mlbam_to_register = {int(k): v for k, v in data.get('mlbam_to_register', {}).items()}
        self.mlbam_to_mlb = {int(k): v for k, v in data.get('mlbam_to_mlb', {}).items()}
        self.register_to_mlbam = {k: int(v) for k, v in data.get('register_to_mlbam', {}).items()}
        self.mlb_to_mlbam = {k: int(v) for k, v in data.get('mlb_to_mlbam', {}).items()}
        self.register_to_name = data.get('register_to_name', {})
        self.mlb_to_name = data.get('mlb_to_name', {})
        self.mlbam_to_name = {int(k): v for k, v in data.get('mlbam_to_name', {}).items()}

        self._loaded = True
        print(f"Loaded player ID mappings from cache ({len(self.register_to_mlb)} mappings)")

    def _save_to_cache(self, cache_file: Path):
        """Save mappings to JSON cache."""
        data = {
            'register_to_mlb': self.register_to_mlb,
            'mlb_to_register': self.mlb_to_register,
            'mlbam_to_register': {str(k): v for k, v in self.mlbam_to_register.items()},
            'mlbam_to_mlb': {str(k): v for k, v in self.mlbam_to_mlb.items()},
            'register_to_mlbam': self.register_to_mlbam,
            'mlb_to_mlbam': self.mlb_to_mlbam,
            'register_to_name': self.register_to_name,
            'mlb_to_name': self.mlb_to_name,
            'mlbam_to_name': {str(k): v for k, v in self.mlbam_to_name.items()},
        }

        with open(cache_file, 'w') as f:
            json.dump(data, f)

        print(f"Saved player ID mappings to {cache_file}")

    def get_mlb_id(self, register_id: str) -> Optional[str]:
        """
        Get MLB BBRef ID from register ID.

        Args:
            register_id: Register format ID (e.g., "fielde001pri")

        Returns:
            MLB format ID (e.g., "fieldpr01") or None
        """
        return self.register_to_mlb.get(register_id)

    def get_register_id(self, mlb_id: str) -> Optional[str]:
        """
        Get register ID from MLB BBRef ID.

        Args:
            mlb_id: MLB format ID (e.g., "fieldpr01")

        Returns:
            Register format ID (e.g., "fielde001pri") or None
        """
        return self.mlb_to_register.get(mlb_id)

    def get_register_from_mlbam(self, mlbam_id: int) -> Optional[str]:
        """
        Get register ID from MLB Stats API ID.

        Args:
            mlbam_id: Numeric MLBAM ID (e.g., 425902)

        Returns:
            Register format ID or None
        """
        return self.mlbam_to_register.get(mlbam_id)

    def get_mlb_from_mlbam(self, mlbam_id: int) -> Optional[str]:
        """
        Get MLB BBRef ID from MLB Stats API ID.

        Args:
            mlbam_id: Numeric MLBAM ID

        Returns:
            MLB format ID or None
        """
        return self.mlbam_to_mlb.get(mlbam_id)

    def get_mlbam_from_register(self, register_id: str) -> Optional[int]:
        """
        Get MLB Stats API ID from register ID.

        Args:
            register_id: Register format ID

        Returns:
            Numeric MLBAM ID or None
        """
        return self.register_to_mlbam.get(register_id)

    def get_all_ids(self, any_id) -> Dict[str, any]:
        """
        Get all available IDs for a player given any one ID.

        Args:
            any_id: Any player ID (register, MLB, or MLBAM)

        Returns:
            Dict with all available IDs and player name
        """
        result = {
            'register_id': None,
            'mlb_id': None,
            'mlbam_id': None,
            'name': None,
        }

        # Try as register ID
        if isinstance(any_id, str) and any_id in self.register_to_mlb:
            result['register_id'] = any_id
            result['mlb_id'] = self.register_to_mlb.get(any_id)
            result['mlbam_id'] = self.register_to_mlbam.get(any_id)
            result['name'] = self.register_to_name.get(any_id)
            return result

        # Try as MLB ID
        if isinstance(any_id, str) and any_id in self.mlb_to_register:
            result['mlb_id'] = any_id
            result['register_id'] = self.mlb_to_register.get(any_id)
            result['mlbam_id'] = self.mlb_to_mlbam.get(any_id)
            result['name'] = self.mlb_to_name.get(any_id)
            return result

        # Try as MLBAM ID
        try:
            mlbam_int = int(any_id)
            if mlbam_int in self.mlbam_to_register:
                result['mlbam_id'] = mlbam_int
                result['register_id'] = self.mlbam_to_register.get(mlbam_int)
                result['mlb_id'] = self.mlbam_to_mlb.get(mlbam_int)
                result['name'] = self.mlbam_to_name.get(mlbam_int)
                return result
        except (ValueError, TypeError):
            pass

        return result


# Singleton instance for convenience
_mapper_instance: Optional[PlayerIDMapper] = None


def get_player_id_mapper() -> PlayerIDMapper:
    """Get the singleton PlayerIDMapper instance."""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = PlayerIDMapper()
    return _mapper_instance


def unify_player_id(any_id) -> Dict[str, any]:
    """
    Convenience function to get all IDs for a player.

    Args:
        any_id: Any player ID

    Returns:
        Dict with register_id, mlb_id, mlbam_id, and name
    """
    return get_player_id_mapper().get_all_ids(any_id)
