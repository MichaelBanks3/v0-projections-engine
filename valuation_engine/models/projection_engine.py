"""Main projection engine that orchestrates data loading and model predictions."""

import logging
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from datetime import datetime

from ..data.nfl_data_loader import NFLDataLoader
from ..config.scoring import ScoringSystem, ScoringType
from .base_projector import StatisticalProjector

logger = logging.getLogger(__name__)


class ProjectionEngine:
    """Main engine for generating fantasy football projections."""
    
    def __init__(self, 
                 scoring_system: Union[str, ScoringType, ScoringSystem] = ScoringType.PPR,
                 cache_dir: Optional[str] = None):
        """Initialize the projection engine.
        
        Args:
            scoring_system: Scoring system to use ('standard', 'ppr', 'half_ppr', or ScoringSystem instance)
            cache_dir: Directory for caching data
        """
        # Set up scoring system
        if isinstance(scoring_system, str):
            scoring_system = ScoringType(scoring_system)
        if isinstance(scoring_system, ScoringType):
            self.scoring_system = ScoringSystem.get_scoring_system(scoring_system)
        else:
            self.scoring_system = scoring_system
        
        # Initialize data loader
        self.data_loader = NFLDataLoader(cache_dir=cache_dir)
        
        # Initialize projectors for each position
        self.projectors = {
            'QB': StatisticalProjector('QB'),
            'RB': StatisticalProjector('RB'),
            'WR': StatisticalProjector('WR'),
            'TE': StatisticalProjector('TE')
        }
        
        self._is_fitted = False
        self._training_data = None
        
        logger.info(f"ProjectionEngine initialized with {scoring_system} scoring")
    
    def fit(self, seasons: Optional[List[int]] = None) -> None:
        """Train projection models on historical data.
        
        Args:
            seasons: Seasons to use for training. Defaults to last 3 seasons.
        """
        if seasons is None:
            current_season = self.data_loader.current_season
            seasons = [current_season - i for i in range(3)]
        
        logger.info(f"Training projection models on seasons: {seasons}")
        
        # Load training data
        training_data = self.data_loader.load_player_stats(seasons=seasons)
        training_data = self._prepare_training_data(training_data)
        
        # Train each position projector
        for position, projector in self.projectors.items():
            position_data = training_data[training_data['position'] == position]
            if len(position_data) > 0:
                projector.fit(position_data)
                logger.info(f"Trained {position} projector on {len(position_data)} records")
            else:
                logger.warning(f"No training data found for position {position}")
        
        self._training_data = training_data
        self._is_fitted = True
        logger.info("All projection models trained successfully")
    
    def get_weekly_projections(self, 
                             week: int,
                             season: int,
                             player_ids: Optional[List[str]] = None,
                             positions: Optional[List[str]] = None) -> pd.DataFrame:
        """Generate weekly projections for players.
        
        Args:
            week: Target week number
            season: Target season
            player_ids: Specific players to project. If None, projects all active players.
            positions: Positions to include. If None, includes all positions.
            
        Returns:
            DataFrame with weekly projections
        """
        if not self._is_fitted:
            logger.info("Models not fitted. Training on default seasons...")
            self.fit()
        
        # Get roster data for active players
        rosters = self.data_loader.load_rosters(seasons=[season])
        
        # Filter by positions if specified
        if positions:
            rosters = rosters[rosters['position'].isin(positions)]
        
        # Filter by player_ids if specified (roster uses gsis_id, stats use player_id)
        if player_ids:
            rosters = rosters[rosters['gsis_id'].isin(player_ids)]
        
        projections = []
        
        for _, player in rosters.iterrows():
            player_id = player['gsis_id']  # Use gsis_id from roster data
            position = player['position']
            
            # Skip if we don't have a projector for this position
            if position not in self.projectors:
                continue
            
            try:
                # Get player's historical data
                player_data = self._get_player_historical_data(player_id)
                
                if player_data.empty:
                    logger.warning(f"No historical data for player {player_id}")
                    continue
                
                # Generate projection
                projection = self.projectors[position].predict_weekly(
                    player_data=player_data,
                    week=week,
                    season=season
                )
                
                # Add player metadata
                projection.update({
                    'player_id': player_id,
                    'player_name': player.get('full_name', player.get('player_name', '')),
                    'position': position,
                    'team': player.get('team', ''),
                    'week': week,
                    'season': season
                })
                
                projections.append(projection)
                
            except Exception as e:
                logger.error(f"Error projecting for player {player_id}: {e}")
                continue
        
        if not projections:
            logger.warning("No projections generated")
            return pd.DataFrame()
        
        projections_df = pd.DataFrame(projections)
        projections_df = projections_df.sort_values('projected_points', ascending=False)
        
        logger.info(f"Generated {len(projections_df)} weekly projections for week {week}, {season}")
        return projections_df
    
    def get_seasonal_projections(self,
                               season: int,
                               player_ids: Optional[List[str]] = None,
                               positions: Optional[List[str]] = None) -> pd.DataFrame:
        """Generate seasonal projections for players.
        
        Args:
            season: Target season
            player_ids: Specific players to project. If None, projects all active players.
            positions: Positions to include. If None, includes all positions.
            
        Returns:
            DataFrame with seasonal projections
        """
        if not self._is_fitted:
            logger.info("Models not fitted. Training on default seasons...")
            self.fit()
        
        # Get roster data for active players
        rosters = self.data_loader.load_rosters(seasons=[season])
        
        # Filter by positions if specified
        if positions:
            rosters = rosters[rosters['position'].isin(positions)]
        
        # Filter by player_ids if specified (roster uses gsis_id)
        if player_ids:
            rosters = rosters[rosters['gsis_id'].isin(player_ids)]
        
        projections = []
        
        for _, player in rosters.iterrows():
            player_id = player['gsis_id']  # Use gsis_id from roster data
            position = player['position']
            
            # Skip if we don't have a projector for this position
            if position not in self.projectors:
                continue
            
            try:
                # Get player's historical data
                player_data = self._get_player_historical_data(player_id)
                
                if player_data.empty:
                    logger.warning(f"No historical data for player {player_id}")
                    continue
                
                # Generate projection
                projection = self.projectors[position].predict_seasonal(
                    player_data=player_data,
                    season=season
                )
                
                # Add player metadata
                projection.update({
                    'player_id': player_id,
                    'player_name': player.get('full_name', player.get('player_name', '')),
                    'position': position,
                    'team': player.get('team', ''),
                    'season': season
                })
                
                projections.append(projection)
                
            except Exception as e:
                logger.error(f"Error projecting for player {player_id}: {e}")
                continue
        
        if not projections:
            logger.warning("No projections generated")
            return pd.DataFrame()
        
        projections_df = pd.DataFrame(projections)
        projections_df = projections_df.sort_values('projected_points', ascending=False)
        
        logger.info(f"Generated {len(projections_df)} seasonal projections for {season}")
        return projections_df
    
    def get_player_projection(self,
                            player_id: str,
                            projection_type: str = "weekly",
                            week: Optional[int] = None,
                            season: Optional[int] = None) -> Dict[str, Any]:
        """Get projection for a specific player.
        
        Args:
            player_id: NFL player ID
            projection_type: 'weekly' or 'seasonal'
            week: Target week (required for weekly projections)
            season: Target season (defaults to current season)
            
        Returns:
            Dictionary with player projection details
        """
        if season is None:
            season = self.data_loader.current_season
        
        if projection_type == "weekly" and week is None:
            raise ValueError("Week is required for weekly projections")
        
        # Get player info
        rosters = self.data_loader.load_rosters(seasons=[season])
        player_info = rosters[rosters['gsis_id'] == player_id]
        
        if player_info.empty:
            raise ValueError(f"Player {player_id} not found for season {season}")
        
        player_info = player_info.iloc[0]
        position = player_info['position']
        
        if position not in self.projectors:
            raise ValueError(f"Projections not available for position {position}")
        
        # Get historical data
        player_data = self._get_player_historical_data(player_id)
        
        # Generate projection
        if projection_type == "weekly":
            projection = self.projectors[position].predict_weekly(
                player_data=player_data,
                week=week,
                season=season
            )
        else:
            projection = self.projectors[position].predict_seasonal(
                player_data=player_data,
                season=season
            )
        
        # Add player metadata
        projection.update({
            'player_id': player_id,
            'player_name': player_info.get('full_name', player_info.get('player_name', '')),
            'position': position,
            'team': player_info.get('team', ''),
            'season': season
        })
        
        if projection_type == "weekly":
            projection['week'] = week
        
        return projection
    
    def _prepare_training_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """Prepare training data by calculating fantasy points and features."""
        df = raw_data.copy()
        
        # Calculate fantasy points for each game using scoring system
        fantasy_points = []
        for _, row in df.iterrows():
            stats = {
                'passing_yards': row.get('passing_yards', 0),
                'passing_tds': row.get('passing_tds', 0),
                'interceptions': row.get('interceptions', 0),
                'rushing_yards': row.get('rushing_yards', 0),
                'rushing_tds': row.get('rushing_tds', 0),
                'receiving_yards': row.get('receiving_yards', 0),
                'receiving_tds': row.get('receiving_tds', 0),
                'receptions': row.get('receptions', 0),
                'fumbles_lost': row.get('fumbles_lost', 0)
            }
            points = self.scoring_system.calculate_fantasy_points(stats)
            fantasy_points.append(points)
        
        df['fantasy_points'] = fantasy_points
        
        # Sort by player and date for time series features
        df = df.sort_values(['player_id', 'season', 'week'])
        
        return df
    
    def _get_player_historical_data(self, player_id: str) -> pd.DataFrame:
        """Get historical data for a specific player."""
        if self._training_data is None:
            # Load fresh data if needed
            seasons = [self.data_loader.current_season - i for i in range(3)]
            training_data = self.data_loader.load_player_stats(seasons=seasons)
            self._training_data = self._prepare_training_data(training_data)
        
        player_data = self._training_data[self._training_data['player_id'] == player_id].copy()
        
        # Sort by most recent games first
        player_data = player_data.sort_values(['season', 'week'], ascending=False)
        
        return player_data

