#!/usr/bin/env python3
"""
Verification script for ncaab_processor refactoring.

Run this before and after each refactoring phase to ensure nothing breaks.
Stores baseline outputs and compares against them after changes.

Usage:
    python verify_refactor.py --create-baseline  # Create baseline before refactoring
    python verify_refactor.py --verify           # Verify after refactoring
    python verify_refactor.py --test-imports     # Just test that imports work
"""

import argparse
import json
import hashlib
import sys
from pathlib import Path
from typing import Optional


# Baseline storage
BASELINE_DIR = Path(__file__).parent / ".refactor_baseline"


def test_imports() -> bool:
    """Test that all expected imports work."""
    print("Testing imports...")
    errors = []

    # Test ncaab_parser imports
    try:
        from ncaab_parser import parse_ncaab_pdf, convert_pdf_to_json
        print("  ✓ from ncaab_parser import parse_ncaab_pdf, convert_pdf_to_json")
    except ImportError as e:
        errors.append(f"  ✗ ncaab_parser: {e}")

    # Test dataclass imports (if exposed)
    try:
        from ncaab_parser import PlayerBattingStats, PitcherStats, PlayEvent
        print("  ✓ from ncaab_parser import PlayerBattingStats, PitcherStats, PlayEvent")
    except ImportError:
        # These might not be exported - that's OK
        print("  - Dataclasses not exported from ncaab_parser (OK)")

    # Test ncaab_html_generator imports
    try:
        from ncaab_html_generator import generate_html_page
        print("  ✓ from ncaab_html_generator import generate_html_page")
    except ImportError as e:
        errors.append(f"  ✗ ncaab_html_generator: {e}")

    # Test name_matcher imports
    try:
        from name_matcher import NameMatcher, enrich_game_data
        print("  ✓ from name_matcher import NameMatcher, enrich_game_data")
    except ImportError as e:
        errors.append(f"  ✗ name_matcher: {e}")

    # Test baseball_processor imports
    try:
        from baseball_processor import main, process_games
        print("  ✓ from baseball_processor import main, process_games")
    except ImportError as e:
        errors.append(f"  ✗ baseball_processor: {e}")

    # Test baseball_processor.main imports from ncaab_parser
    try:
        # This is how main.py imports it
        sys.path.insert(0, str(Path(__file__).parent))
        from ncaab_parser import parse_ncaab_pdf as main_parse
        print("  ✓ baseball_processor/main.py style import works")
    except ImportError as e:
        errors.append(f"  ✗ baseball_processor/main.py style import: {e}")

    if errors:
        print("\nImport errors:")
        for err in errors:
            print(err)
        return False

    print("\nAll imports successful!")
    return True


def hash_json(data: dict) -> str:
    """Create a hash of JSON data for comparison."""
    # Sort keys for consistent hashing
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(json_str.encode()).hexdigest()


def normalize_html(html: str) -> str:
    """Normalize HTML for comparison (remove timestamps, etc.)."""
    import re
    # Remove any timestamps or generated dates
    html = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', 'TIMESTAMP', html)
    html = re.sub(r'Generated on.*?<', 'Generated on TIMESTAMP<', html)
    return html


def test_pdf_parsing(pdf_path: Path) -> Optional[dict]:
    """Parse a PDF and return the result."""
    try:
        from ncaab_parser import parse_ncaab_pdf
        result = parse_ncaab_pdf(str(pdf_path))
        return result
    except Exception as e:
        print(f"  ✗ Failed to parse {pdf_path.name}: {e}")
        return None


def test_html_generation(game_data: dict, roster_dir: Path) -> Optional[str]:
    """Generate HTML from game data and return it."""
    try:
        from ncaab_html_generator import generate_html_page
        from name_matcher import NameMatcher, enrich_game_data

        # Create matcher and enrich data
        matcher = NameMatcher(None)
        if roster_dir.exists():
            matcher.load_rosters_from_dir(str(roster_dir))

        enriched = enrich_game_data(game_data, matcher)
        html = generate_html_page(enriched)
        return html
    except Exception as e:
        print(f"  ✗ Failed to generate HTML: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_name_matching(roster_dir: Path) -> Optional[dict]:
    """Test name matching functionality."""
    try:
        from name_matcher import NameMatcher

        matcher = NameMatcher(None)
        if roster_dir.exists():
            count = matcher.load_rosters_from_dir(str(roster_dir))
            print(f"  Loaded {count} rosters")

        # Test some common name formats
        test_cases = [
            ("Smith, J.", "virginia", None),
            ("Johnson", "california", None),
            ("Williams, Mike", None, None),
        ]

        results = {}
        for name, team, number in test_cases:
            result = matcher.match(name, team, number)
            results[f"{name}|{team}"] = {
                "matched": result.matched,
                "confidence": result.confidence,
                "match_type": result.match_type,
            }

        return results
    except Exception as e:
        print(f"  ✗ Name matching test failed: {e}")
        return None


def create_baseline():
    """Create baseline outputs for comparison."""
    print("Creating baseline...")

    BASELINE_DIR.mkdir(exist_ok=True)

    base_dir = Path(__file__).parent
    pdf_dir = base_dir / "pdfs"
    cache_dir = base_dir / "cache"
    roster_dir = base_dir / "rosters"

    baseline = {
        "imports_ok": test_imports(),
        "parse_results": {},
        "html_hashes": {},
        "name_match_results": None,
    }

    # Test parsing a few PDFs
    if pdf_dir.exists():
        pdfs = list(pdf_dir.glob("*.pdf"))[:3]  # Test first 3 PDFs
        for pdf in pdfs:
            print(f"  Parsing {pdf.name}...")
            result = test_pdf_parsing(pdf)
            if result:
                baseline["parse_results"][pdf.name] = hash_json(result)

                # Also test HTML generation
                print(f"  Generating HTML for {pdf.name}...")
                html = test_html_generation(result, roster_dir)
                if html:
                    baseline["html_hashes"][pdf.name] = hashlib.md5(
                        normalize_html(html).encode()
                    ).hexdigest()

    # Test using cached JSON if no PDFs parsed
    if not baseline["parse_results"] and cache_dir.exists():
        jsons = list(cache_dir.glob("*.json"))[:3]
        for json_file in jsons:
            print(f"  Testing HTML generation from {json_file.name}...")
            with open(json_file) as f:
                game_data = json.load(f)
            html = test_html_generation(game_data, roster_dir)
            if html:
                baseline["html_hashes"][json_file.name] = hashlib.md5(
                    normalize_html(html).encode()
                ).hexdigest()

    # Test name matching
    print("  Testing name matching...")
    baseline["name_match_results"] = test_name_matching(roster_dir)

    # Save baseline
    baseline_file = BASELINE_DIR / "baseline.json"
    with open(baseline_file, "w") as f:
        json.dump(baseline, f, indent=2)

    print(f"\nBaseline saved to {baseline_file}")
    return True


def verify():
    """Verify current outputs match baseline."""
    print("Verifying against baseline...")

    baseline_file = BASELINE_DIR / "baseline.json"
    if not baseline_file.exists():
        print("No baseline found! Run with --create-baseline first.")
        return False

    with open(baseline_file) as f:
        baseline = json.load(f)

    errors = []

    # Test imports
    if not test_imports():
        errors.append("Import test failed")

    base_dir = Path(__file__).parent
    pdf_dir = base_dir / "pdfs"
    cache_dir = base_dir / "cache"
    roster_dir = base_dir / "rosters"

    # Test PDF parsing
    for pdf_name, expected_hash in baseline.get("parse_results", {}).items():
        pdf_path = pdf_dir / pdf_name
        if pdf_path.exists():
            print(f"  Verifying {pdf_name}...")
            result = test_pdf_parsing(pdf_path)
            if result:
                actual_hash = hash_json(result)
                if actual_hash != expected_hash:
                    errors.append(f"Parse output changed for {pdf_name}")
                    print(f"    ✗ Hash mismatch: {expected_hash} != {actual_hash}")
                else:
                    print(f"    ✓ Parse output matches")

    # Test HTML generation
    for file_name, expected_hash in baseline.get("html_hashes", {}).items():
        # Try to find the source file
        if file_name.endswith(".pdf"):
            pdf_path = pdf_dir / file_name
            if pdf_path.exists():
                result = test_pdf_parsing(pdf_path)
                if result:
                    html = test_html_generation(result, roster_dir)
                    if html:
                        actual_hash = hashlib.md5(normalize_html(html).encode()).hexdigest()
                        if actual_hash != expected_hash:
                            errors.append(f"HTML output changed for {file_name}")
                            print(f"    ✗ HTML hash mismatch")
                        else:
                            print(f"    ✓ HTML output matches for {file_name}")
        elif file_name.endswith(".json"):
            json_path = cache_dir / file_name
            if json_path.exists():
                with open(json_path) as f:
                    game_data = json.load(f)
                html = test_html_generation(game_data, roster_dir)
                if html:
                    actual_hash = hashlib.md5(normalize_html(html).encode()).hexdigest()
                    if actual_hash != expected_hash:
                        errors.append(f"HTML output changed for {file_name}")
                        print(f"    ✗ HTML hash mismatch for {file_name}")
                    else:
                        print(f"    ✓ HTML output matches for {file_name}")

    # Test name matching
    if baseline.get("name_match_results"):
        print("  Verifying name matching...")
        current_results = test_name_matching(roster_dir)
        if current_results != baseline["name_match_results"]:
            errors.append("Name matching results changed")
            print("    ✗ Name matching results differ")
        else:
            print("    ✓ Name matching results match")

    if errors:
        print(f"\n❌ Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return False

    print("\n✅ All verifications passed!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Verify refactoring doesn't break functionality")
    parser.add_argument("--create-baseline", action="store_true", help="Create baseline outputs")
    parser.add_argument("--verify", action="store_true", help="Verify against baseline")
    parser.add_argument("--test-imports", action="store_true", help="Just test imports")

    args = parser.parse_args()

    if args.test_imports:
        sys.exit(0 if test_imports() else 1)
    elif args.create_baseline:
        sys.exit(0 if create_baseline() else 1)
    elif args.verify:
        sys.exit(0 if verify() else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
