"""Injury gate policy layer - deterministic rules for injury filtering."""

from typing import Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)


def decision_from_fields(status: str, injury_status: str) -> str:
    """Determine if player should be zeroed out based on status fields.
    
    Args:
        status: Player roster status (IR, PUP, NFI, Suspended, Active, etc.)
        injury_status: Injury status (Out, Doubtful, Questionable, etc.)
        
    Returns:
        "zero" if player should be zeroed out, "pass" otherwise
    """
    # Normalize to uppercase for comparison, handle None values
    status_upper = (status or "").upper() if status is not None else ""
    injury_status_upper = (injury_status or "").upper() if injury_status is not None else ""
    
    # Zero out if roster status indicates long-term absence
    if status_upper in ['IR', 'PUP', 'NFI', 'SUSPENDED', 'INACTIVE', 'PRACTICE SQUAD']:
        return "zero"
    
    # Zero out if injury status indicates game absence
    if injury_status_upper in ['OUT', 'DOUBTFUL', 'IR', 'PUP']:
        return "zero"
    
    # Pass through for all other cases
    # This includes: Questionable, Active, Probable, and any missing/unknown status
    return "pass"


def apply_injury_gate(points: Union[float, int], status: str, injury_status: str) -> Union[float, int]:
    """Apply injury gate to projected points.
    
    Args:
        points: Base projected points
        status: Player roster status
        injury_status: Player injury status
        
    Returns:
        Original points if player should play, 0.0 if zeroed out
    """
    decision = decision_from_fields(status, injury_status)
    
    if decision == "zero":
        return 0.0
    else:
        return points


def get_injury_summary(injury_data: Dict[str, Dict]) -> Dict[str, int]:
    """Get summary statistics for injury data.
    
    Args:
        injury_data: Normalized injury data from Sleeper
        
    Returns:
        Dictionary with counts by status
    """
    summary = {
        'zeroed': 0,
        'questionable': 0,
        'active': 0,
        'total': len(injury_data)
    }
    
    for player_data in injury_data.values():
        status = player_data.get('status', '') or ''
        injury_status = player_data.get('injury_status', '') or ''
        
        decision = decision_from_fields(status, injury_status)
        
        if decision == "zero":
            summary['zeroed'] += 1
        elif (injury_status or '').upper() == 'QUESTIONABLE':
            summary['questionable'] += 1
        else:
            summary['active'] += 1
    
    return summary


def log_injury_summary(summary: Dict[str, int], source: str = "unknown") -> None:
    """Log injury summary in the specified format.
    
    Args:
        summary: Injury summary statistics
        source: Data source description
    """
    logger.info(
        f"InjuryGate: zeroed={summary['zeroed']}, "
        f"questionable={summary['questionable']}, "
        f"active={summary['active']}, "
        f"source={source}"
    )
