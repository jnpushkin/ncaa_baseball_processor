"""Display-name helpers for player rows.

Identity normalization intentionally strips suffixes so rows can merge across
sources. These helpers preserve the richer public label when a source or roster
has the same normalized identity but different display detail.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from utils.names import normalize_name, normalize_player_name


DISPLAY_SUFFIX_RE = re.compile(r"\b(?:jr\.?|sr\.?|ii|iii|iv|v)\.?$", re.IGNORECASE)
DISPLAY_SUFFIX_TOKENS = {"jr", "sr", "ii", "iii", "iv", "v"}


def has_display_suffix(name: Any) -> bool:
    return bool(DISPLAY_SUFFIX_RE.search(str(name or "").strip()))


def display_suffix(name: Any) -> str:
    match = DISPLAY_SUFFIX_RE.search(str(name or "").strip())
    if not match:
        return ""
    token = match.group(0).rstrip(".").lower()
    return {
        "jr": "Jr.",
        "sr": "Sr.",
        "ii": "II",
        "iii": "III",
        "iv": "IV",
        "v": "V",
    }.get(token, match.group(0))


def has_non_suffix_all_caps_token(name: Any) -> bool:
    for token in re.findall(r"[A-Za-z.]+", str(name or "")):
        letters = re.sub(r"[^A-Za-z]", "", token)
        if len(letters) > 2 and letters.isupper() and letters.lower() not in DISPLAY_SUFFIX_TOKENS:
            return True
    return False


def has_richer_source_suffix(candidate: Any, current: Any) -> bool:
    candidate_name = normalize_player_name(str(candidate or "").strip())
    current_name = normalize_player_name(str(current or "").strip())
    return (
        bool(candidate_name)
        and bool(current_name)
        and normalize_name(candidate_name) == normalize_name(current_name)
        and has_display_suffix(candidate_name)
        and not has_display_suffix(current_name)
        and not has_non_suffix_all_caps_token(candidate_name)
    )


def row_source_display_name(row: Mapping[str, Any]) -> Any:
    full_name = row.get("full_name") or ""
    name = row.get("name") or ""
    if full_name and name:
        full_display = normalize_player_name(str(full_name or "").strip())
        name_display = normalize_player_name(str(name or "").strip())
        if normalize_name(full_display) == normalize_name(name_display):
            suffix = display_suffix(name_display)
            if suffix and not has_display_suffix(full_display):
                if has_non_suffix_all_caps_token(name_display):
                    return f"{full_display} {suffix}"
                return name
    return full_name or name


def best_display_name(current: Any, candidate: Any) -> str:
    current_name = normalize_player_name(str(current or "").strip())
    candidate_name = normalize_player_name(str(candidate or "").strip())
    if not current_name:
        return candidate_name
    if not candidate_name:
        return current_name
    if has_richer_source_suffix(candidate_name, current_name):
        return candidate_name
    if has_richer_source_suffix(current_name, candidate_name):
        return current_name
    if normalize_name(candidate_name) == normalize_name(current_name):
        suffix = display_suffix(candidate_name)
        if suffix and not has_display_suffix(current_name):
            return f"{current_name} {suffix}"
    return current_name
