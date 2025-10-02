"""Fantasy football scoring system configurations."""

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel


class ScoringType(str, Enum):
    """Supported fantasy scoring systems."""
    STANDARD = "standard"
    PPR = "ppr"
    HALF_PPR = "half_ppr"


class ScoringSystem(BaseModel):
    """Fantasy football scoring configuration."""
    
    # Passing
    passing_yards_per_point: float = 25.0  # 1 point per 25 yards
    passing_td: float = 4.0
    passing_interception: float = -2.0
    passing_2pt: float = 2.0
    
    # Rushing
    rushing_yards_per_point: float = 10.0  # 1 point per 10 yards
    rushing_td: float = 6.0
    rushing_2pt: float = 2.0
    
    # Receiving
    receiving_yards_per_point: float = 10.0  # 1 point per 10 yards
    receiving_td: float = 6.0
    receiving_2pt: float = 2.0
    reception: float = 0.0  # PPR bonus
    
    # Fumbles
    fumble_lost: float = -2.0
    
    @classmethod
    def get_scoring_system(cls, scoring_type: ScoringType) -> "ScoringSystem":
        """Get predefined scoring system."""
        if scoring_type == ScoringType.STANDARD:
            return cls()
        elif scoring_type == ScoringType.PPR:
            return cls(reception=1.0)
        elif scoring_type == ScoringType.HALF_PPR:
            return cls(reception=0.5)
        else:
            raise ValueError(f"Unknown scoring type: {scoring_type}")
    
    def calculate_fantasy_points(self, stats: Dict[str, float]) -> float:
        """Calculate fantasy points for given player stats."""
        points = 0.0
        
        # Passing
        points += stats.get("passing_yards", 0) / self.passing_yards_per_point
        points += stats.get("passing_tds", 0) * self.passing_td
        points += stats.get("interceptions", 0) * self.passing_interception
        points += stats.get("passing_2pt", 0) * self.passing_2pt
        
        # Rushing
        points += stats.get("rushing_yards", 0) / self.rushing_yards_per_point
        points += stats.get("rushing_tds", 0) * self.rushing_td
        points += stats.get("rushing_2pt", 0) * self.rushing_2pt
        
        # Receiving
        points += stats.get("receiving_yards", 0) / self.receiving_yards_per_point
        points += stats.get("receiving_tds", 0) * self.receiving_td
        points += stats.get("receiving_2pt", 0) * self.receiving_2pt
        points += stats.get("receptions", 0) * self.reception
        
        # Fumbles
        points += stats.get("fumbles_lost", 0) * self.fumble_lost
        
        return round(points, 2)

