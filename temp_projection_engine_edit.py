# Edit the ProjectionEngine to add QB benching filter

# 1. Update constructor to add qb_benching_filter parameter
def __init__(self, 
             scoring_system: Union[str, ScoringType, ScoringSystem] = ScoringType.PPR,
             cache_dir: Optional[str] = None,
             injury_filter: bool = True,
             qb_benching_filter: bool = True):
    """Initialize the projection engine.
    
    Args:
        scoring_system: Scoring system to use ('standard', 'ppr', 'half_ppr', or ScoringSystem instance)
        cache_dir: Directory for caching data
        injury_filter: Whether to apply injury filtering
        qb_benching_filter: Whether to apply QB benching filter (zero out non-starting QBs)
    """
    # ... existing code ...
    
    # Injury filtering settings
    self.injury_filter = injury_filter
    self.qb_benching_filter = qb_benching_filter
    
    # ... rest of existing code ...
    
    logger.info(f"ProjectionEngine initialized with {scoring_system} scoring, injury_filter={injury_filter}, qb_benching_filter={qb_benching_filter}")

# 2. Update _apply_availability_filters to include QB benching filter
def _apply_availability_filters(self, projections_df: pd.DataFrame, week: int, season: int) -> pd.DataFrame:
    """Apply availability filters (bye weeks, injuries, QB benching, etc.) to projections.
    
    Args:
        projections_df: DataFrame with projections
        week: Target week
        season: Target season
        
    Returns:
        DataFrame with availability filters applied
    """
    logger.info(f"Applying availability filters for week {week}, season {season}")
    
    # Apply bye week filter
    projections_df = self._apply_bye_week_filter(projections_df, week, season)
    
    # Apply injury filter if enabled
    if self.injury_filter:
        projections_df = self._apply_injury_filter(projections_df)
    
    # Apply QB benching filter if enabled
    if self.qb_benching_filter:
        projections_df = self._apply_qb_benching_filter(projections_df)
    
    return projections_df

# 3. Add the new _apply_qb_benching_filter method
def _apply_qb_benching_filter(self, projections_df: pd.DataFrame) -> pd.DataFrame:
    """Apply QB benching filter to zero out non-starting QBs.
    
    Args:
        projections_df: DataFrame with projections
        
    Returns:
        DataFrame with non-starting QBs zeroed out
    """
    try:
        # Import here to avoid circular imports
        from ..data.sleeper_injuries import get_injury_data_with_cache
        from ..data.player_mapping import get_player_mapper
        
        # Get Sleeper data for depth chart info
        injury_data = get_injury_data_with_cache()
        if not injury_data:
            logger.warning("No Sleeper data available, skipping QB benching filter")
            return projections_df
        
        # Get player mapper
        mapper = get_player_mapper()
        
        zeroed_count = 0
        
        # Apply QB benching filter to each QB
        for index, row in projections_df.iterrows():
            if row.get('position') != 'QB':
                continue
                
            gsis_id = row.get('player_id', '')
            if not gsis_id:
                continue
            
            # Map gsis_id to sleeper_id
            sleeper_id = mapper.gsis_to_sleeper_id(gsis_id)
            if not sleeper_id:
                # No mapping available - treat as starting
                continue
            
            # Get Sleeper data for this player
            player_data = injury_data.get(sleeper_id, {})
            depth_chart_order = player_data.get('depth_chart_order')
            
            # Zero out if depth_chart_order > 1 (not starting)
            if depth_chart_order is not None and depth_chart_order > 1:
                original_points = row['projected_points']
                if original_points > 0:
                    projections_df.at[index, 'projected_points'] = 0.0
                    projections_df.at[index, 'confidence_lower'] = 0.0
                    projections_df.at[index, 'confidence_upper'] = 0.0
                    zeroed_count += 1
                    
                    player_name = row.get('player_name', 'Unknown')
                    logger.debug(f"Zeroed out benched QB: {player_name} (depth_chart_order={depth_chart_order})")
        
        if zeroed_count > 0:
            logger.info(f"QB benching filter zeroed out {zeroed_count} non-starting QBs")
        
        return projections_df
        
    except Exception as e:
        logger.error(f"Error applying QB benching filter: {e}")
        # Return original dataframe if there's an error
        return projections_df
