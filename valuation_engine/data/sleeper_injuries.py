"""Sleeper API integration for injury data with caching."""

import json
import logging
import requests
from pathlib import Path
from typing import Dict, Optional, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Sleeper API endpoints
SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"

# Cache file paths
CACHE_DIR = Path("data/cache")
IR_CACHE_FILE = CACHE_DIR / "ir_players_2025.json"
PLAYERS_SNAPSHOT_FILE = CACHE_DIR / "players_snapshot.json"


class SleeperInjuryFetcher:
    """Fetches and caches injury data from Sleeper API."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the fetcher.
        
        Args:
            cache_dir: Directory for caching data
        """
        self.cache_dir = Path(cache_dir or "data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.ir_cache_file = self.cache_dir / "ir_players_2025.json"
        self.players_snapshot_file = self.cache_dir / "players_snapshot.json"
        
        # Request settings
        self.timeout = 20
        self.max_retries = 2
        self.backoff_factor = 0.5
        
    def fetch_players_raw(self) -> Optional[Dict]:
        """Fetch raw player data from Sleeper API with retries.
        
        Returns:
            Raw player data dict or None if failed
        """
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Fetching Sleeper player data (attempt {attempt + 1})")
                response = requests.get(SLEEPER_PLAYERS_URL, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Successfully fetched {len(data)} players from Sleeper")
                
                # Save snapshot for fallback
                self._save_players_snapshot(data)
                
                return data
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries:
                    import time
                    time.sleep(self.backoff_factor * (2 ** attempt))
                else:
                    logger.error("All attempts failed to fetch Sleeper data")
                    return None
    
    def normalize_player_data(self, raw_data: Dict) -> Dict[str, Dict]:
        """Normalize raw Sleeper data to minimal format.
        
        Args:
            raw_data: Raw player data from Sleeper API
            
        Returns:
            Normalized player data: {player_id: {id, full_name, team, status, injury_status, news_updated}}
        """
        normalized = {}
        
        for player_id, player_data in raw_data.items():
            if not isinstance(player_data, dict):
                continue
                
            normalized[player_id] = {
                'id': player_id,
                'full_name': player_data.get('full_name', ''),
                'team': player_data.get('team', ''),
                'status': player_data.get('status', ''),
                'injury_status': player_data.get('injury_status', ''),
                'news_updated': player_data.get('news_updated', ''),
                'depth_chart_order': player_data.get('depth_chart_order'),
                'depth_chart_position': player_data.get('depth_chart_position'),
            }
        
        return normalized
    
    def get_ir_players(self, normalized_data: Dict) -> Set[str]:
        """Extract players with IR-like status.
        
        Args:
            normalized_data: Normalized player data
            
        Returns:
            Set of player IDs with IR-like status
        """
        ir_players = set()
        
        for player_id, player_data in normalized_data.items():
            status = (player_data.get('status', '') or '').upper()
            if status in ['IR', 'PUP', 'NFI', 'SUSPENDED']:
                ir_players.add(player_id)
        
        logger.info(f"Found {len(ir_players)} players with IR-like status")
        return ir_players
    
    def _save_players_snapshot(self, data: Dict) -> None:
        """Save raw player data as snapshot for fallback."""
        try:
            with open(self.players_snapshot_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'data': data
                }, f, indent=2)
            logger.debug(f"Saved players snapshot to {self.players_snapshot_file}")
        except Exception as e:
            logger.warning(f"Failed to save players snapshot: {e}")
    
    def _load_players_snapshot(self) -> Optional[Dict]:
        """Load players snapshot for fallback."""
        try:
            if not self.players_snapshot_file.exists():
                return None
                
            with open(self.players_snapshot_file, 'r') as f:
                snapshot = json.load(f)
                
            # Check if snapshot is recent (within 24 hours)
            timestamp = datetime.fromisoformat(snapshot['timestamp'])
            if datetime.now() - timestamp > timedelta(hours=24):
                logger.warning("Players snapshot is older than 24 hours")
                return None
                
            logger.info("Using players snapshot for fallback")
            return snapshot['data']
            
        except Exception as e:
            logger.warning(f"Failed to load players snapshot: {e}")
            return None
    
    def _save_ir_cache(self, ir_players: Set[str]) -> None:
        """Save IR players cache."""
        try:
            with open(self.ir_cache_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'ir_players': list(ir_players)
                }, f, indent=2)
            logger.debug(f"Saved IR cache to {self.ir_cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save IR cache: {e}")
    
    def _load_ir_cache(self) -> Set[str]:
        """Load IR players cache."""
        try:
            if not self.ir_cache_file.exists():
                return set()
                
            with open(self.ir_cache_file, 'r') as f:
                cache = json.load(f)
                
            return set(cache.get('ir_players', []))
            
        except Exception as e:
            logger.warning(f"Failed to load IR cache: {e}")
            return set()
    
    def get_injury_data_with_cache(self) -> Dict[str, Dict]:
        """Get injury data with caching strategy.
        
        Returns:
            Normalized injury data for all players
        """
        # Try to fetch fresh data
        raw_data = self.fetch_players_raw()
        
        if raw_data is not None:
            # Fresh fetch succeeded - normalize and update caches
            normalized_data = self.normalize_player_data(raw_data)
            ir_players = self.get_ir_players(normalized_data)
            self._save_ir_cache(ir_players)
            
            logger.info("Using fresh Sleeper data")
            return normalized_data
        
        else:
            # Fresh fetch failed - use cached data
            logger.warning("Fresh fetch failed, using cached data")
            
            # Try to load snapshot
            raw_data = self._load_players_snapshot()
            if raw_data is not None:
                normalized_data = self.normalize_player_data(raw_data)
                # Use existing IR cache (don't update it)
                ir_cache = self._load_ir_cache()
                logger.info(f"Using snapshot data with {len(ir_cache)} cached IR players")
                return normalized_data
            
            else:
                # No cached data available - return empty dict
                logger.error("No cached data available, returning empty injury data")
                return {}


# Global fetcher instance
_fetcher = None

def get_sleeper_fetcher() -> SleeperInjuryFetcher:
    """Get global Sleeper fetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = SleeperInjuryFetcher()
    return _fetcher

def get_injury_data_with_cache() -> Dict[str, Dict]:
    """Get injury data with caching (convenience function)."""
    return get_sleeper_fetcher().get_injury_data_with_cache()
