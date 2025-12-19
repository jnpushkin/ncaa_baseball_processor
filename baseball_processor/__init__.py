"""
NCAA Baseball Stats Processor

Process box score PDFs and generate statistics, Excel workbooks, and interactive HTML.
"""

from .main import main, process_games

__version__ = "1.0.0"
__all__ = ["main", "process_games"]
