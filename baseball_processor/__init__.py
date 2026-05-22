"""
NCAA Baseball Stats Processor

Process box score PDFs and generate statistics, Excel workbooks, and interactive HTML.
"""

from .main import main
from .sources import load_source_games, process_pdf_games as process_games

__version__ = "1.0.0"
__all__ = ["main", "process_games", "load_source_games"]
