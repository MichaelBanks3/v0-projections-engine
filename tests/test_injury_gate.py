"""Tests for injury gate policy layer."""

import pytest
from valuation_engine.models.injury_gate import (
    decision_from_fields,
    apply_injury_gate,
    get_injury_summary,
    log_injury_summary
)


class TestInjuryGate:
    """Test injury gate policy functions."""
    
    def test_decision_from_fields_roster_status(self):
        """Test decision based on roster status."""
        # IR-like statuses should be zeroed
        assert decision_from_fields("IR", "") == "zero"
        assert decision_from_fields("PUP", "") == "zero"
        assert decision_from_fields("NFI", "") == "zero"
        assert decision_from_fields("Suspended", "") == "zero"
        
        # Case insensitive
        assert decision_from_fields("ir", "") == "zero"
        assert decision_from_fields("pup", "") == "zero"
    
    def test_decision_from_fields_injury_status(self):
        """Test decision based on injury status."""
        # Out/Doubtful should be zeroed
        assert decision_from_fields("", "Out") == "zero"
        assert decision_from_fields("", "Doubtful") == "zero"
        
        # Case insensitive
        assert decision_from_fields("", "out") == "zero"
        assert decision_from_fields("", "doubtful") == "zero"
    
    def test_decision_from_fields_pass_through(self):
        """Test pass-through cases."""
        # Questionable should pass through
        assert decision_from_fields("", "Questionable") == "pass"
        assert decision_from_fields("", "questionable") == "pass"
        
        # Active should pass through
        assert decision_from_fields("Active", "") == "pass"
        assert decision_from_fields("", "Active") == "pass"
        
        # Missing/empty should pass through
        assert decision_from_fields("", "") == "pass"
        assert decision_from_fields(None, None) == "pass"
    
    def test_apply_injury_gate(self):
        """Test injury gate application."""
        # Zero out cases
        assert apply_injury_gate(10.0, "IR", "") == 0.0
        assert apply_injury_gate(10.0, "", "Out") == 0.0
        assert apply_injury_gate(10.0, "", "Doubtful") == 0.0
        
        # Pass through cases
        assert apply_injury_gate(10.0, "Active", "") == 10.0
        assert apply_injury_gate(10.0, "", "Questionable") == 10.0
        assert apply_injury_gate(10.0, "", "") == 10.0
        
        # Integer points
        assert apply_injury_gate(10, "IR", "") == 0.0
        assert apply_injury_gate(10, "Active", "") == 10
    
    def test_get_injury_summary(self):
        """Test injury summary generation."""
        injury_data = {
            "player1": {"status": "IR", "injury_status": ""},
            "player2": {"status": "Active", "injury_status": "Out"},
            "player3": {"status": "Active", "injury_status": "Questionable"},
            "player4": {"status": "Active", "injury_status": "Active"},
            "player5": {"status": "Active", "injury_status": ""},
        }
        
        summary = get_injury_summary(injury_data)
        
        assert summary['total'] == 5
        assert summary['zeroed'] == 2  # player1 (IR) + player2 (Out)
        assert summary['questionable'] == 1  # player3
        assert summary['active'] == 2  # player4 + player5
    
    def test_log_injury_summary(self, caplog):
        """Test injury summary logging."""
        summary = {
            'zeroed': 5,
            'questionable': 10,
            'active': 100,
            'total': 115
        }
        
        with caplog.at_level("INFO"):
            log_injury_summary(summary, "live+cache")
        
        assert "InjuryGate: zeroed=5, questionable=10, active=100, source=live+cache" in caplog.text
