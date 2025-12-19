"""
PDF format detection for NCAA baseball box scores.
"""

import re


def detect_pdf_format(text: str) -> str:
    """Detect which PDF format we're dealing with.

    Returns:
        'format_a': Original format (VMI at Virginia style, side-by-side stats with jersey #)
        'format_a_no_num': Format A variant without jersey numbers
        'format_b': Newer format (Team (record) -vs- Team (record) style)
    """
    if '-vs-' in text:
        return 'format_b'
    # Check for column headers
    if 'Player AB R H RBI BB SO LOB' in text:
        return 'format_b'
    if '# player pos ab r h rbi bb k po a lob' in text.lower():
        return 'format_a'
    # Format A without jersey numbers: "Player ab r h rbi bb k po a lob"
    if re.search(r'Player\s+ab\s+r\s+h\s+rbi\s+bb\s+k\s+po\s+a\s+lob', text, re.IGNORECASE):
        return 'format_a_no_num'
    if ' at ' in text.lower() or ' @ ' in text:
        # Check if it has jersey numbers
        if '# Player Pos' in text:
            return 'format_a'
        return 'format_a_no_num'
    return 'format_a'  # Default
