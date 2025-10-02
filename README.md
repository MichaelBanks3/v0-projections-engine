# Fantasy Football Valuation Engine

A Python-based fantasy football projection system that generates player projections for both weekly and seasonal performance using nflverse data.

## Features

- **Weekly Projections**: Baseline weekly fantasy point projections for individual players
- **Seasonal Projections**: Season-long projections with uncertainty modeling
- **Multiple Scoring Systems**: Support for Standard, PPR, and Half-PPR scoring
- **Data-Driven**: Uses comprehensive nflverse datasets for historical analysis
- **Extensible**: Modular design for adding additional data sources

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

```python
from valuation_engine import ProjectionEngine

# Initialize the engine
engine = ProjectionEngine(scoring_system='ppr')

# Get weekly projections
weekly_projections = engine.get_weekly_projections(week=1, season=2024)

# Get seasonal projections
seasonal_projections = engine.get_seasonal_projections(season=2024)
```

## Project Structure

```
valuation-engine/
├── valuation_engine/          # Main package
│   ├── data/                  # Data pipeline modules
│   ├── models/                # Projection models
│   ├── config/                # Configuration
│   └── utils/                 # Utility functions
├── tests/                     # Test suite
├── notebooks/                 # Jupyter notebooks for analysis
└── scripts/                   # CLI scripts
```

## Data Sources

- **Primary**: nflverse (via nflreadpy) - Comprehensive NFL statistics and play-by-play data
- **Future**: Injury reports, weather data, betting lines

