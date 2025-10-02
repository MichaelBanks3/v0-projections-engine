"""Fantasy Football Valuation Engine

A comprehensive fantasy football projection system using nflverse data.
"""

__version__ = "0.1.0"
__author__ = "Fantasy Football Analytics"

from .models.projection_engine import ProjectionEngine
from .config.scoring import ScoringSystem
from .data.nfl_data_loader import NFLDataLoader

__all__ = ["ProjectionEngine", "ScoringSystem", "NFLDataLoader"]

