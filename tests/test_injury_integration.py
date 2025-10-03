"""Integration tests for injury filtering system."""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from valuation_engine.models.projection_engine import ProjectionEngine


class TestInjuryIntegration:
    """Test injury filtering integration with projection engine."""
    
    def test_projection_engine_injury_filter_off(self):
        """Test projection engine with injury filter disabled."""
        engine = ProjectionEngine(injury_filter=False)
        assert engine.injury_filter is False
    
    def test_projection_engine_injury_filter_on(self):
        """Test projection engine with injury filter enabled."""
        engine = ProjectionEngine(injury_filter=True)
        assert engine.injury_filter is True
    
    @patch('valuation_engine.data.sleeper_injuries.get_injury_data_with_cache')
    @patch('valuation_engine.data.player_mapping.get_player_mapper')
    def test_apply_injury_filter_success(self, mock_get_mapper, mock_get_injury_data):
        """Test successful injury filter application."""
        # Mock injury data
        injury_data = {
            "123": {
                "status": "Active",
                "injury_status": "Questionable"
            },
            "456": {
                "status": "IR",
                "injury_status": ""
            },
            "789": {
                "status": "Active",
                "injury_status": "Out"
            }
        }
        mock_get_injury_data.return_value = injury_data
        
        # Mock player mapper
        mock_mapper = MagicMock()
        mock_mapper.gsis_to_sleeper_id.side_effect = lambda gsis_id: {
            "00-0012345": "123",
            "00-0067890": "456", 
            "00-0099999": "789"
        }.get(gsis_id)
        mock_get_mapper.return_value = mock_mapper
        
        # Create test projections
        projections_df = pd.DataFrame([
            {
                "player_id": "00-0012345",
                "player_name": "Lamar Jackson",
                "position": "QB",
                "team": "BAL",
                "projected_points": 20.0,
                "confidence_lower": 15.0,
                "confidence_upper": 25.0
            },
            {
                "player_id": "00-0067890",
                "player_name": "Christian McCaffrey",
                "position": "RB",
                "team": "SF",
                "projected_points": 18.0,
                "confidence_lower": 12.0,
                "confidence_upper": 24.0
            },
            {
                "player_id": "00-0099999",
                "player_name": "Cooper Kupp",
                "position": "WR",
                "team": "LAR",
                "projected_points": 15.0,
                "confidence_lower": 10.0,
                "confidence_upper": 20.0
            }
        ])
        
        # Create engine and apply filter
        engine = ProjectionEngine(injury_filter=True)
        result = engine._apply_injury_filter(projections_df)
        
        # Check results
        assert len(result) == 3
        
        # Lamar Jackson (Questionable) - should pass through
        lamar_row = result[result['player_id'] == '00-0012345'].iloc[0]
        assert lamar_row['projected_points'] == 20.0
        assert lamar_row['injury_status'] == 'Questionable'
        
        # Christian McCaffrey (IR) - should be zeroed
        cmc_row = result[result['player_id'] == '00-0067890'].iloc[0]
        assert cmc_row['projected_points'] == 0.0
        assert cmc_row['confidence_lower'] == 0.0
        assert cmc_row['confidence_upper'] == 0.0
        assert cmc_row['roster_status'] == 'IR'
        
        # Cooper Kupp (Out) - should be zeroed
        kupp_row = result[result['player_id'] == '00-0099999'].iloc[0]
        assert kupp_row['projected_points'] == 0.0
        assert kupp_row['injury_status'] == 'Out'
    
    @patch('valuation_engine.data.sleeper_injuries.get_injury_data_with_cache')
    def test_apply_injury_filter_no_data(self, mock_get_injury_data):
        """Test injury filter with no injury data available."""
        # Mock no injury data
        mock_get_injury_data.return_value = {}
        
        projections_df = pd.DataFrame([
            {
                "player_id": "00-0012345",
                "player_name": "Lamar Jackson",
                "position": "QB",
                "team": "BAL",
                "projected_points": 20.0,
                "confidence_lower": 15.0,
                "confidence_upper": 25.0
            }
        ])
        
        engine = ProjectionEngine(injury_filter=True)
        result = engine._apply_injury_filter(projections_df)
        
        # Should return original dataframe unchanged
        assert len(result) == 1
        assert result.iloc[0]['projected_points'] == 20.0
    
    def test_apply_injury_filter_exception_handling(self):
        """Test injury filter exception handling."""
        # Mock exception in injury data fetch
        with patch('valuation_engine.data.sleeper_injuries.get_injury_data_with_cache') as mock_get_injury_data:
            mock_get_injury_data.side_effect = Exception("Network error")
            
            projections_df = pd.DataFrame([
                {
                    "player_id": "00-0012345",
                    "player_name": "Lamar Jackson",
                    "position": "QB",
                    "team": "BAL",
                    "projected_points": 20.0,
                    "confidence_lower": 15.0,
                    "confidence_upper": 25.0
                }
            ])
            
            engine = ProjectionEngine(injury_filter=True)
            result = engine._apply_injury_filter(projections_df)
            
            # Should return original dataframe unchanged on error
            assert len(result) == 1
            assert result.iloc[0]['projected_points'] == 20.0
