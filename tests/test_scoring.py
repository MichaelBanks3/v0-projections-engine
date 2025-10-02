"""Tests for scoring system functionality."""

import pytest
from valuation_engine.config.scoring import ScoringSystem, ScoringType


class TestScoringSystem:
    """Test scoring system calculations."""
    
    def test_standard_scoring(self):
        """Test standard scoring system."""
        scoring = ScoringSystem.get_scoring_system(ScoringType.STANDARD)
        
        # Test QB stats
        qb_stats = {
            'passing_yards': 300,
            'passing_tds': 2,
            'interceptions': 1,
            'rushing_yards': 20,
            'rushing_tds': 1
        }
        
        expected = (300/25) + (2*4) + (1*-2) + (20/10) + (1*6)
        actual = scoring.calculate_fantasy_points(qb_stats)
        assert actual == expected
    
    def test_ppr_scoring(self):
        """Test PPR scoring system."""
        scoring = ScoringSystem.get_scoring_system(ScoringType.PPR)
        
        # Test WR stats
        wr_stats = {
            'receiving_yards': 100,
            'receiving_tds': 1,
            'receptions': 8,
            'fumbles_lost': 1
        }
        
        expected = (100/10) + (1*6) + (8*1) + (1*-2)
        actual = scoring.calculate_fantasy_points(wr_stats)
        assert actual == expected
    
    def test_half_ppr_scoring(self):
        """Test Half-PPR scoring system."""
        scoring = ScoringSystem.get_scoring_system(ScoringType.HALF_PPR)
        
        # Test RB stats
        rb_stats = {
            'rushing_yards': 80,
            'rushing_tds': 1,
            'receiving_yards': 30,
            'receptions': 4
        }
        
        expected = (80/10) + (1*6) + (30/10) + (4*0.5)
        actual = scoring.calculate_fantasy_points(rb_stats)
        assert actual == expected
    
    def test_empty_stats(self):
        """Test scoring with empty stats."""
        scoring = ScoringSystem.get_scoring_system(ScoringType.PPR)
        assert scoring.calculate_fantasy_points({}) == 0.0
    
    def test_missing_stats(self):
        """Test scoring with missing stat keys."""
        scoring = ScoringSystem.get_scoring_system(ScoringType.PPR)
        stats = {'passing_yards': 250}  # Only one stat
        
        expected = 250/25  # Only passing yards counted
        actual = scoring.calculate_fantasy_points(stats)
        assert actual == expected

