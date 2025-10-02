"""Base projection model interface and utilities."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseProjector(ABC):
    """Abstract base class for fantasy football projection models."""
    
    def __init__(self, position: str):
        """Initialize the projector.
        
        Args:
            position: Player position (QB, RB, WR, TE)
        """
        self.position = position.upper()
        self.is_trained = False
        self.model_params = {}
        
    @abstractmethod
    def fit(self, training_data: pd.DataFrame) -> None:
        """Train the projection model on historical data.
        
        Args:
            training_data: Historical player performance data
        """
        pass
    
    @abstractmethod
    def predict_weekly(self, 
                      player_data: pd.DataFrame,
                      week: int,
                      season: int,
                      **kwargs) -> Dict[str, float]:
        """Generate weekly fantasy point projection for a player.
        
        Args:
            player_data: Player's historical data
            week: Target week number
            season: Target season
            **kwargs: Additional context (matchup info, etc.)
            
        Returns:
            Dictionary with projection and confidence intervals
        """
        pass
    
    @abstractmethod
    def predict_seasonal(self,
                        player_data: pd.DataFrame,
                        season: int,
                        **kwargs) -> Dict[str, float]:
        """Generate seasonal fantasy point projection for a player.
        
        Args:
            player_data: Player's historical data  
            season: Target season
            **kwargs: Additional context
            
        Returns:
            Dictionary with seasonal projection and uncertainty
        """
        pass
    
    def _calculate_moving_averages(self, 
                                  data: pd.DataFrame,
                                  windows: List[int] = [3, 5, 10]) -> pd.DataFrame:
        """Calculate moving averages for key stats."""
        df = data.copy()
        
        for window in windows:
            df[f'fantasy_points_ma_{window}'] = (
                df.groupby('player_id')['fantasy_points']
                .rolling(window=window, min_periods=1)
                .mean()
                .reset_index(level=0, drop=True)
            )
            
        return df
    
    def _calculate_trend_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate trend and momentum features."""
        df = data.copy()
        
        # Calculate recent vs long-term averages
        df['recent_form'] = (
            df.groupby('player_id')['fantasy_points']
            .rolling(window=3, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )
        
        df['season_avg'] = (
            df.groupby(['player_id', 'season'])['fantasy_points']
            .expanding()
            .mean()
            .reset_index(level=[0,1], drop=True)
        )
        
        # Trend indicator (recent vs season average)
        df['trend_factor'] = df['recent_form'] / (df['season_avg'] + 0.1)  # Avoid division by zero
        
        return df
    
    def _add_positional_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add position-specific features."""
        df = data.copy()
        
        if self.position == 'QB':
            # QB-specific features
            df['pass_attempt_share'] = df.groupby(['team', 'season', 'week'])['passing_attempts'].transform(
                lambda x: x / x.sum() if x.sum() > 0 else 0
            )
            
        elif self.position in ['RB', 'WR', 'TE']:
            # Skill position features
            df['target_share'] = df.groupby(['team', 'season', 'week'])['targets'].transform(
                lambda x: x / x.sum() if x.sum() > 0 else 0
            )
            
            df['red_zone_share'] = df.groupby(['team', 'season', 'week'])['red_zone_targets'].transform(
                lambda x: x / x.sum() if x.sum() > 0 else 0
            )
            
        return df
    
    def _validate_prediction(self, prediction: Dict[str, float]) -> Dict[str, float]:
        """Validate and clean prediction output."""
        # Ensure non-negative fantasy points
        prediction['projected_points'] = max(0, prediction.get('projected_points', 0))
        
        # Ensure confidence intervals make sense
        if 'confidence_lower' in prediction and 'confidence_upper' in prediction:
            lower = prediction['confidence_lower']
            upper = prediction['confidence_upper']
            projected = prediction['projected_points']
            
            # Lower bound should be <= projected <= upper bound
            prediction['confidence_lower'] = min(lower, projected)
            prediction['confidence_upper'] = max(upper, projected)
        
        return prediction


class StatisticalProjector(BaseProjector):
    """Simple statistical projection model using moving averages and trends."""
    
    def __init__(self, position: str):
        super().__init__(position)
        self.position_weights = {
            'QB': {'recent': 0.4, 'season': 0.3, 'career': 0.3},
            'RB': {'recent': 0.5, 'season': 0.3, 'career': 0.2},
            'WR': {'recent': 0.4, 'season': 0.35, 'career': 0.25},
            'TE': {'recent': 0.4, 'season': 0.35, 'career': 0.25}
        }
        
    def fit(self, training_data: pd.DataFrame) -> None:
        """Fit the statistical model (calculate baseline stats)."""
        logger.info(f"Fitting statistical projector for {self.position}")
        
        # Calculate position baselines
        position_data = training_data[training_data['position'] == self.position]
        
        self.model_params = {
            'position_mean': position_data['fantasy_points'].mean(),
            'position_std': position_data['fantasy_points'].std(),
            'games_per_season': position_data.groupby(['player_id', 'season']).size().mean()
        }
        
        self.is_trained = True
        logger.info(f"Model fitted. Position average: {self.model_params['position_mean']:.2f} points")
    
    def predict_weekly(self, 
                      player_data: pd.DataFrame,
                      week: int,
                      season: int,
                      **kwargs) -> Dict[str, float]:
        """Generate weekly projection using weighted averages."""
        if not self.is_trained:
            raise ValueError("Model must be fitted before making predictions")
        
        # Get recent games (last 3)
        recent_games = player_data.head(3)
        
        # Calculate weighted average
        weights = self.position_weights[self.position]
        
        # Recent form (last 3 games)
        recent_avg = recent_games['fantasy_points'].mean() if len(recent_games) > 0 else 0
        
        # Season average
        season_data = player_data[player_data['season'] == season]
        season_avg = season_data['fantasy_points'].mean() if len(season_data) > 0 else 0
        
        # Career average
        career_avg = player_data['fantasy_points'].mean() if len(player_data) > 0 else 0
        
        # Weighted projection
        projection = (
            weights['recent'] * recent_avg +
            weights['season'] * season_avg +
            weights['career'] * career_avg
        )
        
        # If no historical data, use position average
        if projection == 0:
            projection = self.model_params['position_mean']
        
        # Calculate confidence interval based on player consistency
        player_std = player_data['fantasy_points'].std() if len(player_data) > 1 else self.model_params['position_std']
        
        return self._validate_prediction({
            'projected_points': round(projection, 2),
            'confidence_lower': round(max(0, projection - 1.96 * player_std), 2),
            'confidence_upper': round(projection + 1.96 * player_std, 2),
            'confidence_level': 0.95
        })
    
    def predict_seasonal(self,
                        player_data: pd.DataFrame,
                        season: int,
                        **kwargs) -> Dict[str, float]:
        """Generate seasonal projection by aggregating weekly projections."""
        if not self.is_trained:
            raise ValueError("Model must be fitted before making predictions")
        
        # Estimate games to be played (typically 17 regular season games)
        expected_games = kwargs.get('expected_games', 17)
        
        # Get weekly projection baseline
        weekly_projection = self.predict_weekly(player_data, week=1, season=season, **kwargs)
        weekly_points = weekly_projection['projected_points']
        
        # Seasonal projection is weekly * expected games
        seasonal_projection = weekly_points * expected_games
        
        # Adjust for injury risk and consistency
        injury_adjustment = kwargs.get('injury_risk', 0.9)  # 90% of games expected
        seasonal_projection *= injury_adjustment
        
        # Calculate seasonal uncertainty
        weekly_std = (weekly_projection['confidence_upper'] - weekly_projection['confidence_lower']) / 3.92
        seasonal_std = weekly_std * np.sqrt(expected_games)
        
        return self._validate_prediction({
            'projected_points': round(seasonal_projection, 1),
            'confidence_lower': round(max(0, seasonal_projection - 1.96 * seasonal_std), 1),
            'confidence_upper': round(seasonal_projection + 1.96 * seasonal_std, 1),
            'confidence_level': 0.95,
            'expected_games': expected_games * injury_adjustment
        })

