"""NFL data loader using nflreadpy for accessing nflverse datasets."""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
import polars as pl
from datetime import datetime

try:
    import nflreadpy as nfl
except ImportError:
    print("nflreadpy not installed. Run: pip install nflreadpy")
    nfl = None


logger = logging.getLogger(__name__)


class NFLDataLoader:
    """Loads and caches NFL data from nflverse using nflreadpy."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the data loader.
        
        Args:
            cache_dir: Directory to cache downloaded data. Defaults to ./data/cache
        """
        if nfl is None:
            raise ImportError("nflreadpy is required. Install with: pip install nflreadpy")
        
        self.cache_dir = Path(cache_dir or "./data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Current season detection
        self.current_season = self._get_current_season()
        logger.info(f"Initialized NFLDataLoader for season {self.current_season}")
    
    def _get_current_season(self) -> int:
        """Determine the current NFL season based on date."""
        now = datetime.now()
        # NFL season typically starts in September
        if now.month >= 9:
            return now.year
        else:
            return now.year - 1
    
    def load_player_stats(self, 
                         seasons: Optional[List[int]] = None,
                         stat_type: str = "weekly") -> pd.DataFrame:
        """Load player statistics from nflverse.
        
        Args:
            seasons: List of seasons to load. Defaults to current season.
            stat_type: Type of stats - "weekly" or "seasonal"
            
        Returns:
            DataFrame with player statistics
        """
        if seasons is None:
            seasons = [self.current_season]
        
        logger.info(f"Loading {stat_type} player stats for seasons: {seasons}")
        
        try:
            if stat_type == "weekly":
                # Load weekly player stats
                df = nfl.load_player_stats(seasons=seasons)
                if isinstance(df, pl.DataFrame):
                    df = df.to_pandas()
            else:
                # For seasonal stats, we'll aggregate weekly data
                weekly_df = nfl.load_player_stats(seasons=seasons)
                if isinstance(weekly_df, pl.DataFrame):
                    weekly_df = weekly_df.to_pandas()
                df = self._aggregate_seasonal_stats(weekly_df)
            
            logger.info(f"Loaded {len(df)} rows of {stat_type} player stats")
            return df
            
        except Exception as e:
            logger.error(f"Error loading player stats: {e}")
            raise
    
    def load_pbp_data(self, seasons: Optional[List[int]] = None) -> pd.DataFrame:
        """Load play-by-play data for advanced analytics.
        
        Args:
            seasons: List of seasons to load. Defaults to current season.
            
        Returns:
            DataFrame with play-by-play data
        """
        if seasons is None:
            seasons = [self.current_season]
        
        logger.info(f"Loading play-by-play data for seasons: {seasons}")
        
        try:
            df = nfl.load_pbp(seasons=seasons)
            if isinstance(df, pl.DataFrame):
                df = df.to_pandas()
            
            logger.info(f"Loaded {len(df)} plays of PBP data")
            return df
            
        except Exception as e:
            logger.error(f"Error loading PBP data: {e}")
            raise
    
    def load_schedules(self, seasons: Optional[List[int]] = None) -> pd.DataFrame:
        """Load NFL schedules for matchup analysis.
        
        Args:
            seasons: List of seasons to load. Defaults to current season.
            
        Returns:
            DataFrame with schedule data
        """
        if seasons is None:
            seasons = [self.current_season]
        
        logger.info(f"Loading schedules for seasons: {seasons}")
        
        try:
            df = nfl.load_schedules(seasons=seasons)
            if isinstance(df, pl.DataFrame):
                df = df.to_pandas()
            
            logger.info(f"Loaded {len(df)} games from schedules")
            return df
            
        except Exception as e:
            logger.error(f"Error loading schedules: {e}")
            raise
    
    def load_rosters(self, seasons: Optional[List[int]] = None) -> pd.DataFrame:
        """Load player rosters and information.
        
        Args:
            seasons: List of seasons to load. Defaults to current season.
            
        Returns:
            DataFrame with roster data
        """
        if seasons is None:
            seasons = [self.current_season]
        
        logger.info(f"Loading rosters for seasons: {seasons}")
        
        try:
            df = nfl.load_rosters(seasons=seasons)
            if isinstance(df, pl.DataFrame):
                df = df.to_pandas()
            
            logger.info(f"Loaded {len(df)} player roster records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading rosters: {e}")
            raise
    
    def _aggregate_seasonal_stats(self, weekly_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate weekly stats to seasonal totals."""
        # Group by player and season, sum relevant stats
        agg_cols = {
            'passing_yards': 'sum',
            'passing_tds': 'sum', 
            'interceptions': 'sum',
            'rushing_yards': 'sum',
            'rushing_tds': 'sum',
            'receiving_yards': 'sum',
            'receptions': 'sum',
            'receiving_tds': 'sum',
            'fumbles_lost': 'sum',
            'games': 'count'  # Number of games played
        }
        
        # Only aggregate columns that exist in the dataframe
        available_agg_cols = {k: v for k, v in agg_cols.items() 
                             if k in weekly_df.columns}
        
        seasonal_df = (weekly_df.groupby(['player_id', 'player_name', 'position', 'season'])
                              .agg(available_agg_cols)
                              .reset_index())
        
        return seasonal_df
    
    def get_player_projections_data(self, 
                                  player_id: str,
                                  seasons: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get comprehensive data for a specific player for projections.
        
        Args:
            player_id: NFL player ID
            seasons: Seasons to include. Defaults to last 3 seasons.
            
        Returns:
            Dictionary with player's historical data
        """
        if seasons is None:
            seasons = [self.current_season - i for i in range(3)]
        
        try:
            # Load player stats
            stats_df = self.load_player_stats(seasons=seasons)
            player_stats = stats_df[stats_df['player_id'] == player_id]
            
            # Load roster info
            roster_df = self.load_rosters(seasons=seasons)
            player_info = roster_df[roster_df['player_id'] == player_id]
            
            return {
                'player_id': player_id,
                'weekly_stats': player_stats,
                'player_info': player_info,
                'seasons_available': player_stats['season'].unique().tolist() if not player_stats.empty else []
            }
            
        except Exception as e:
            logger.error(f"Error getting player data for {player_id}: {e}")
            raise
    
    def get_team_bye_weeks(self, season: int) -> Dict[str, int]:
        """Get bye weeks for each team in a season.
        
        Args:
            season: NFL season year
            
        Returns:
            Dictionary mapping team abbreviation to bye week number
        """
        logger.info(f"Determining bye weeks for season {season}")
        
        try:
            # Load schedule data
            schedules = self.load_schedules(seasons=[season])
            
            # Get all weeks in the season (typically 1-18)
            all_weeks = set(range(1, 19))  # Regular season weeks
            
            # For each team, find which week they don't have a game
            bye_weeks = {}
            
            for team in schedules['home_team'].unique():
                # Get all weeks this team has a game (home or away)
                team_games = schedules[
                    (schedules['home_team'] == team) | 
                    (schedules['away_team'] == team)
                ]
                
                weeks_with_games = set(team_games['week'].unique())
                bye_week = all_weeks - weeks_with_games
                
                if len(bye_week) == 1:
                    bye_weeks[team] = list(bye_week)[0]
                elif len(bye_week) == 0:
                    logger.warning(f"No bye week found for team {team}")
                else:
                    logger.warning(f"Multiple bye weeks found for team {team}: {bye_week}")
            
            logger.info(f"Found bye weeks for {len(bye_weeks)} teams")
            return bye_weeks
            
        except Exception as e:
            logger.error(f"Error determining bye weeks: {e}")
            raise

