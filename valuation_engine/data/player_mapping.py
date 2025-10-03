"""Player ID mapping utilities for Sleeper and nflverse integration."""

import csv
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PlayerIDMapper:
    """Maps between different player ID systems."""
    
    def __init__(self, mapping_file: Optional[str] = None):
        """Initialize the mapper.
        
        Args:
            mapping_file: Path to CSV mapping file
        """
        self.mapping_file = Path(mapping_file or "data/player_id_mapping.csv")
        self.gsis_to_sleeper: Dict[str, str] = {}
        self.sleeper_to_gsis: Dict[str, str] = {}
        self._load_mapping()
    
    def _load_mapping(self) -> None:
        """Load player ID mapping from CSV file."""
        if not self.mapping_file.exists():
            logger.warning(f"Mapping file not found: {self.mapping_file}")
            return
        
        try:
            with open(self.mapping_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    gsis_id = row.get('gsis_id', '').strip()
                    sleeper_id = row.get('sleeper_id', '').strip()
                    
                    if gsis_id and sleeper_id:
                        self.gsis_to_sleeper[gsis_id] = sleeper_id
                        self.sleeper_to_gsis[sleeper_id] = gsis_id
            
            logger.info(f"Loaded {len(self.gsis_to_sleeper)} player ID mappings")
            
        except Exception as e:
            logger.error(f"Failed to load player mapping: {e}")
    
    def gsis_to_sleeper_id(self, gsis_id: str) -> Optional[str]:
        """Convert gsis_id to sleeper_id.
        
        Args:
            gsis_id: NFL gsis_id
            
        Returns:
            Sleeper ID or None if not found
        """
        return self.gsis_to_sleeper.get(gsis_id)
    
    def sleeper_to_gsis_id(self, sleeper_id: str) -> Optional[str]:
        """Convert sleeper_id to gsis_id.
        
        Args:
            sleeper_id: Sleeper player ID
            
        Returns:
            GSIS ID or None if not found
        """
        return self.sleeper_to_gsis.get(sleeper_id)
    
    def has_mapping(self, gsis_id: str) -> bool:
        """Check if gsis_id has a mapping to Sleeper.
        
        Args:
            gsis_id: NFL gsis_id
            
        Returns:
            True if mapping exists
        """
        return gsis_id in self.gsis_to_sleeper


# Global mapper instance
_mapper = None

def get_player_mapper() -> PlayerIDMapper:
    """Get global player mapper instance."""
    global _mapper
    if _mapper is None:
        _mapper = PlayerIDMapper()
    return _mapper
