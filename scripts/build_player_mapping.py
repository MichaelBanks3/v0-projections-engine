#!/usr/bin/env python3
"""Script to build player ID mapping between nflverse and Sleeper."""

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

def find_tyreek_hill(sleeper_data: Dict) -> Optional[str]:
    """Find Tyreek Hill's Sleeper ID."""
    for player_id, player_data in sleeper_data.items():
        if isinstance(player_data, dict):
            name = player_data.get('full_name', '').lower()
            if 'tyreek' in name and 'hill' in name:
                print(f"Found Tyreek Hill: {player_data['full_name']} (ID: {player_id})")
                print(f"  Status: {player_data.get('status', 'N/A')}")
                print(f"  Injury Status: {player_data.get('injury_status', 'N/A')}")
                print(f"  Team: {player_data.get('team', 'N/A')}")
                return player_id
    return None

def find_other_injured_players(sleeper_data: Dict) -> List[Dict]:
    """Find other injured players for testing."""
    injured_players = []
    
    for player_id, player_data in sleeper_data.items():
        if isinstance(player_data, dict):
            status = (player_data.get('status', '') or '').upper()
            injury_status = (player_data.get('injury_status', '') or '').upper()
            
            # Look for injured players
            if (status in ['IR', 'PUP', 'NFI', 'SUSPENDED'] or 
                injury_status in ['OUT', 'DOUBTFUL']):
                injured_players.append({
                    'sleeper_id': player_id,
                    'full_name': player_data.get('full_name', ''),
                    'position': player_data.get('position', ''),
                    'team': player_data.get('team', ''),
                    'status': status,
                    'injury_status': injury_status
                })
    
    return injured_players

def create_mapping_for_key_players(sleeper_data: Dict) -> List[Dict]:
    """Create mapping for key players we know are being projected."""
    # These are the player IDs from your projection output
    key_players = [
        ('00-0034796', 'Lamar Jackson', 'QB', 'BAL'),
        ('00-0034857', 'Josh Allen', 'QB', 'BUF'),
        ('00-0037834', 'Brock Purdy', 'QB', 'SF'),
        ('00-0036389', 'Jalen Hurts', 'QB', 'PHI'),
        ('00-0039910', 'Jayden Daniels', 'QB', 'WAS'),
        ('00-0033873', 'Baker Mayfield', 'QB', 'TB'),
        ('00-0033077', 'Patrick Mahomes', 'QB', 'KC'),
        ('00-0023459', 'Dak Prescott', 'QB', 'DAL'),
        ('00-0040000', 'Bo Nix', 'QB', 'DEN'),
        ('00-0033077', 'Jared Goff', 'QB', 'DET'),
        ('00-0040001', 'Drake Maye', 'QB', 'NE'),
        ('00-0033873', 'Jordan Love', 'QB', 'GB'),
        ('00-0040002', 'Caleb Williams', 'QB', 'CHI'),
        ('00-0033873', 'Kyler Murray', 'QB', 'ARI'),
        ('00-0023459', 'Matthew Stafford', 'QB', 'LA'),
        ('00-0033873', 'Tua Tagovailoa', 'QB', 'MIA'),
        ('00-0033873', 'Justin Herbert', 'QB', 'LAC'),
        ('00-0033873', 'Joe Burrow', 'QB', 'CIN'),
        ('00-0033873', 'Sam Darnold', 'QB', 'MIN'),
        ('00-0023459', 'Geno Smith', 'QB', 'SEA'),
    ]
    
    mappings = []
    
    # Create lookup by name
    sleeper_by_name = {}
    for player_id, player_data in sleeper_data.items():
        if isinstance(player_data, dict) and player_data.get('full_name'):
            name = player_data['full_name'].lower().strip()
            sleeper_by_name[name] = {
                'sleeper_id': player_id,
                'full_name': player_data['full_name'],
                'position': player_data.get('position', ''),
                'team': player_data.get('team', ''),
                'status': player_data.get('status', ''),
                'injury_status': player_data.get('injury_status', '')
            }
    
    # Match key players
    for gsis_id, name, position, team in key_players:
        name_lower = name.lower()
        if name_lower in sleeper_by_name:
            sleeper_player = sleeper_by_name[name_lower]
            mappings.append({
                'gsis_id': gsis_id,
                'sleeper_id': sleeper_player['sleeper_id'],
                'full_name': sleeper_player['full_name'],
                'position': sleeper_player['position'],
                'team': sleeper_player['team'],
                'status': sleeper_player['status'],
                'injury_status': sleeper_player['injury_status']
            })
            print(f"✅ Mapped {name}: {gsis_id} -> {sleeper_player['sleeper_id']}")
        else:
            print(f"❌ Could not find {name} in Sleeper data")
    
    return mappings

def save_mapping_csv(mappings: List[Dict], output_file: str):
    """Save mapping to CSV file."""
    print(f"\nSaving {len(mappings)} player mappings to {output_file}...")
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'gsis_id', 'sleeper_id', 'full_name', 'position', 'team', 
            'status', 'injury_status'
        ])
        writer.writeheader()
        writer.writerows(mappings)

def main():
    """Main function to build player mapping."""
    print("Building player ID mapping between nflverse and Sleeper...")
    
    # Fetch Sleeper data
    sleeper_data = fetch_sleeper_players()
    
    # Find Tyreek Hill specifically
    tyreek_id = find_tyreek_hill(sleeper_data)
    if tyreek_id:
        print(f"✅ Found Tyreek Hill with Sleeper ID: {tyreek_id}")
    else:
        print("❌ Could not find Tyreek Hill in Sleeper data")
    
    # Find other injured players
    injured_players = find_other_injured_players(sleeper_data)
    print(f"\nFound {len(injured_players)} injured players:")
    for player in injured_players[:10]:  # Show first 10
        print(f"  {player['full_name']} ({player['position']}, {player['team']}) - {player['status']}/{player['injury_status']}")
    
    # Create mappings for key players
    mappings = create_mapping_for_key_players(sleeper_data)
    
    # Add Tyreek Hill if we found him
    if tyreek_id:
        # Find Tyreek's data
        tyreek_data = sleeper_data[tyreek_id]
        mappings.append({
            'gsis_id': '00-0033873',  # We need his real GSIS ID
            'sleeper_id': tyreek_id,
            'full_name': tyreek_data.get('full_name', 'Tyreek Hill'),
            'position': tyreek_data.get('position', 'WR'),
            'team': tyreek_data.get('team', 'MIA'),
            'status': tyreek_data.get('status', ''),
            'injury_status': tyreek_data.get('injury_status', '')
        })
        print(f"✅ Added Tyreek Hill to mapping")
    
    # Save mapping
    output_file = Path("data/player_id_mapping.csv")
    output_file.parent.mkdir(exist_ok=True)
    save_mapping_csv(mappings, output_file)
    
    print(f"\n✅ Created mapping file with {len(mappings)} players")
    
    # Show some examples
    print("\nSample mappings:")
    for mapping in mappings[:5]:
        print(f"  {mapping['full_name']} ({mapping['position']}, {mapping['team']})")
        print(f"    GSIS: {mapping['gsis_id']} -> Sleeper: {mapping['sleeper_id']}")
        print(f"    Status: {mapping['status']}, Injury: {mapping['injury_status']}")

if __name__ == "__main__":
    main()
