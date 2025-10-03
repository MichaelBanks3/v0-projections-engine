#!/usr/bin/env python3
"""Build corrected player mapping for only active NFL roster players."""

import csv
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional

def fetch_sleeper_players() -> Dict:
    """Fetch all players from Sleeper API."""
    print("Fetching Sleeper player data...")
    response = requests.get("https://api.sleeper.app/v1/players/nfl", timeout=30)
    response.raise_for_status()
    return response.json()

def fetch_nflverse_rosters():
    """Fetch roster data from nflverse."""
    print("Fetching nflverse roster data...")
    try:
        import sys
        sys.path.append('.')
        from valuation_engine.data.nfl_data_loader import NFLDataLoader
        loader = NFLDataLoader()
        rosters = loader.load_rosters([2024])
        return rosters
    except Exception as e:
        print(f"Error loading nflverse data: {e}")
        return None

def filter_active_roster_players(sleeper_data: Dict) -> Dict:
    """Filter to only active players on NFL rosters."""
    fantasy_positions = {'QB', 'RB', 'WR', 'TE'}
    active_roster_players = {}
    
    for player_id, player_data in sleeper_data.items():
        if isinstance(player_data, dict) and player_data is not None:
            position = (player_data.get('position', '') or '').upper()
            active = player_data.get('active', None)
            team = player_data.get('team', None)
            
            # Filter: fantasy position AND active AND on a team
            if (position in fantasy_positions and 
                active and 
                team is not None):
                active_roster_players[player_id] = player_data
    
    print(f"Found {len(active_roster_players)} active roster players")
    return active_roster_players

def create_name_lookup(nflverse_data):
    """Create lookup dictionary from nflverse data."""
    if nflverse_data is None:
        return {}
    
    lookup = {}
    for _, row in nflverse_data.iterrows():
        name = row.get('full_name', '').lower().strip()
        if name:
            lookup[name] = row.get('gsis_id', '')
    
    print(f"Created lookup for {len(lookup)} nflverse players")
    return lookup

def build_corrected_mapping(sleeper_active: Dict, nflverse_lookup: Dict) -> List[Dict]:
    """Build mapping for active roster players only."""
    mappings = []
    matched_count = 0
    rookie_count = 0
    
    for sleeper_id, sleeper_data in sleeper_active.items():
        full_name = sleeper_data.get('full_name', '')
        position = sleeper_data.get('position', '')
        team = sleeper_data.get('team', '')
        status = sleeper_data.get('status', '')
        injury_status = sleeper_data.get('injury_status', '')
        
        # Try to find matching nflverse player
        name_lower = full_name.lower().strip()
        gsis_id = nflverse_lookup.get(name_lower, '')
        
        if gsis_id:
            # Found match in nflverse
            matched_count += 1
        else:
            # Rookie or player not in nflverse - use placeholder ID
            gsis_id = f"ROOKIE_{sleeper_id}"
            rookie_count += 1
        
        mappings.append({
            'gsis_id': gsis_id,
            'sleeper_id': sleeper_id,
            'full_name': full_name,
            'position': position,
            'team': team,
            'status': status,
            'injury_status': injury_status
        })
    
    print(f"Mapping complete: {matched_count} matched, {rookie_count} rookies")
    return mappings

def analyze_injury_coverage(mappings: List[Dict]) -> Dict:
    """Analyze injury coverage in the mapping."""
    total_players = len(mappings)
    injured_players = 0
    questionable_players = 0
    
    for mapping in mappings:
        status = (mapping.get('status', '') or '').upper()
        injury_status = (mapping.get('injury_status', '') or '').upper()
        
        # Count players that should be zeroed out
        if (status in ['IR', 'PUP', 'NFI', 'SUSPENDED', 'INACTIVE'] or 
            injury_status in ['OUT', 'DOUBTFUL', 'IR']):
            injured_players += 1
        elif injury_status == 'QUESTIONABLE':
            questionable_players += 1
    
    coverage = {
        'total_players': total_players,
        'injured_players': injured_players,
        'questionable_players': questionable_players,
        'active_players': total_players - injured_players - questionable_players
    }
    
    return coverage

def save_mapping_csv(mappings: List[Dict], output_file: str):
    """Save mapping to CSV file."""
    print(f"Saving {len(mappings)} player mappings to {output_file}...")
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'gsis_id', 'sleeper_id', 'full_name', 'position', 'team', 
            'status', 'injury_status'
        ])
        writer.writeheader()
        writer.writerows(mappings)

def main():
    """Main function to build corrected player mapping."""
    print("Building corrected player mapping for active NFL roster players...")
    
    # Fetch data
    sleeper_data = fetch_sleeper_players()
    nflverse_data = fetch_nflverse_rosters()
    
    # Filter to active roster players only
    sleeper_active = filter_active_roster_players(sleeper_data)
    
    # Create nflverse lookup
    nflverse_lookup = create_name_lookup(nflverse_data)
    
    # Build corrected mapping
    mappings = build_corrected_mapping(sleeper_active, nflverse_lookup)
    
    # Analyze coverage
    coverage = analyze_injury_coverage(mappings)
    
    # Quality gates
    print(f"\n=== QUALITY GATES ===")
    print(f"Total mapped players: {coverage['total_players']}")
    print(f"Injured players: {coverage['injured_players']}")
    print(f"Questionable players: {coverage['questionable_players']}")
    print(f"Active players: {coverage['active_players']}")
    
    # Check coverage expectations
    if coverage['total_players'] < 750:
        print(f"⚠️  WARNING: Only {coverage['total_players']} players mapped (expected ~750-800)")
    elif coverage['total_players'] > 850:
        print(f"⚠️  WARNING: {coverage['total_players']} players mapped (expected ~750-800)")
    else:
        print(f"✅ Player count within expected range: {coverage['total_players']}")
    
    if coverage['injured_players'] == 0:
        print(f"⚠️  WARNING: No injured players found - check injury data")
    else:
        print(f"✅ Found {coverage['injured_players']} injured players for filtering")
    
    # Save mapping
    output_file = Path("data/player_id_mapping.csv")
    output_file.parent.mkdir(exist_ok=True)
    save_mapping_csv(mappings, output_file)
    
    print(f"\n✅ Corrected mapping complete!")
    print(f"📁 Saved to: {output_file}")
    
    # Show some examples
    print(f"\nSample mappings:")
    for mapping in mappings[:5]:
        print(f"  {mapping['full_name']} ({mapping['position']}, {mapping['team']})")
        print(f"    GSIS: {mapping['gsis_id']} -> Sleeper: {mapping['sleeper_id']}")
        print(f"    Status: {mapping['status']}, Injury: {mapping['injury_status']}")

if __name__ == "__main__":
    main()
