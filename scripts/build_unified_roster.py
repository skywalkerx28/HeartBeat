"""
Build Unified NHL Roster Index (10-Year Historical)

Creates a single canonical roster file from all team rosters across
the last 10 seasons (2015-2016 through 2025-2026).

Features:
- Deduplicates players by NHL ID
- Tracks all teams and seasons for each player
- Maintains most recent player information
- Creates a comprehensive historical player database

Run after roster sync to update the unified index.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Set

TEAM_MAPPING = {
    "ANA": "Anaheim Ducks",
    "BOS": "Boston Bruins",
    "BUF": "Buffalo Sabres",
    "CAR": "Carolina Hurricanes",
    "CBJ": "Columbus Blue Jackets",
    "CGY": "Calgary Flames",
    "CHI": "Chicago Blackhawks",
    "COL": "Colorado Avalanche",
    "DAL": "Dallas Stars",
    "DET": "Detroit Red Wings",
    "EDM": "Edmonton Oilers",
    "FLA": "Florida Panthers",
    "LAK": "Los Angeles Kings",
    "MIN": "Minnesota Wild",
    "MTL": "Montreal Canadiens",
    "NJD": "New Jersey Devils",
    "NSH": "Nashville Predators",
    "NYI": "New York Islanders",
    "NYR": "New York Rangers",
    "OTT": "Ottawa Senators",
    "PHI": "Philadelphia Flyers",
    "PIT": "Pittsburgh Penguins",
    "SEA": "Seattle Kraken",
    "SJS": "San Jose Sharks",
    "STL": "St. Louis Blues",
    "TBL": "Tampa Bay Lightning",
    "TOR": "Toronto Maple Leafs",
    "UTA": "Utah Hockey Club",
    "VAN": "Vancouver Canucks",
    "VGK": "Vegas Golden Knights",
    "WPG": "Winnipeg Jets",
    "WSH": "Washington Capitals"
}


ALL_SEASONS = [
    '20152016', '20162017', '20172018', '20182019', '20192020',
    '20202021', '20212022', '20222023', '20232024', '20242025', '20252026'
]


def build_unified_roster_historical() -> Dict[str, Any]:
    """
    Build a unified roster index from all team rosters across 10 seasons.
    
    Deduplicates players by NHL ID and tracks their team history.
    """
    
    roster_dir = Path("data/processed/rosters")
    
    player_registry: Dict[int, Dict[str, Any]] = {}
    
    teams_list = []
    teams_processed: Set[str] = set()
    
    total_roster_files = 0
    total_raw_players = 0
    
    print(f"\nBuilding 10-Year Historical Unified Roster...")
    print(f"Seasons: {ALL_SEASONS[0][:4]}-{ALL_SEASONS[0][4:]} through {ALL_SEASONS[-1][:4]}-{ALL_SEASONS[-1][4:]}")
    print(f"Teams: {len(TEAM_MAPPING)}")
    print(f"{'='*80}\n")
    
    for season in ALL_SEASONS:
        season_display = f"{season[:4]}-{season[4:]}"
        print(f"\nProcessing Season: {season_display}")
        print(f"{'-'*80}")
        
        season_files = 0
        season_players = 0
        
        for team_code, team_name in sorted(TEAM_MAPPING.items()):
            team_dir = roster_dir / team_code / season
            roster_file = team_dir / f"{team_code}_roster_{season}.json"
            
            if not roster_file.exists():
                continue
            
            try:
                with open(roster_file, 'r', encoding='utf-8') as f:
                    roster_data = json.load(f)
                
                file_player_count = 0
                
                for position_group in ['forwards', 'defensemen', 'goalies']:
                    if position_group not in roster_data:
                        continue
                    
                    for player in roster_data[position_group]:
                        player_id = player.get('id')
                        if not player_id:
                            continue
                        
                        first_name = player.get('firstName', {})
                        if isinstance(first_name, dict):
                            first_name = first_name.get('default', '')
                        
                        last_name = player.get('lastName', {})
                        if isinstance(last_name, dict):
                            last_name = last_name.get('default', '')
                        
                        full_name = f"{first_name} {last_name}".strip()
                        position_code = player.get('positionCode', '')
                        
                        if player_id not in player_registry:
                            player_registry[player_id] = {
                                "type": "player",
                                "id": player_id,
                                "name": full_name,
                                "firstName": first_name,
                                "lastName": last_name,
                                "position": position_code,
                                "shootsCatches": player.get('shootsCatches', ''),
                                "heightInInches": player.get('heightInInches'),
                                "weightInPounds": player.get('weightInPounds'),
                                "birthDate": player.get('birthDate'),
                                "birthCountry": player.get('birthCountry'),
                                "headshot": player.get('headshot', ''),
                                "sweaterNumber": player.get('sweaterNumber', ''),
                                "currentTeam": team_code,
                                "currentTeamName": team_name,
                                "teamHistory": []
                            }
                        
                        player_registry[player_id]["teamHistory"].append({
                            "season": season,
                            "seasonDisplay": season_display,
                            "team": team_code,
                            "teamName": team_name,
                            "sweaterNumber": player.get('sweaterNumber', ''),
                            "headshot": player.get('headshot', '')
                        })
                        
                        if season == ALL_SEASONS[-1]:
                            player_registry[player_id]["currentTeam"] = team_code
                            player_registry[player_id]["currentTeamName"] = team_name
                            player_registry[player_id]["sweaterNumber"] = player.get('sweaterNumber', '')
                            player_registry[player_id]["headshot"] = player.get('headshot', '')
                        
                        file_player_count += 1
                        total_raw_players += 1
                
                if file_player_count > 0:
                    season_files += 1
                    season_players += file_player_count
                    teams_processed.add(team_code)
                    print(f"  {team_code:3} - {file_player_count:2} players")
                
            except Exception as e:
                print(f"  {team_code:3} - Error: {e}")
                continue
        
        total_roster_files += season_files
        print(f"  Season Total: {season_files} rosters, {season_players} player entries")
    
    all_players = sorted(player_registry.values(), key=lambda p: p['name'])
    
    teams_list = [
        {
            "type": "team",
            "id": team_code,
            "name": team_name,
            "code": team_code
        }
        for team_code, team_name in sorted(TEAM_MAPPING.items())
    ]
    
    position_counts = {
        "C": 0, "L": 0, "R": 0, "D": 0, "G": 0
    }
    for player in all_players:
        pos = player.get('position', '')
        if pos in position_counts:
            position_counts[pos] += 1
    
    print(f"\n{'='*80}")
    print(f"10-YEAR HISTORICAL ROSTER BUILD COMPLETE")
    print(f"{'='*80}")
    print(f"Total Roster Files Processed: {total_roster_files}")
    print(f"Total Raw Player Entries:     {total_raw_players:,}")
    print(f"Unique Players (Deduplicated): {len(all_players):,}")
    print(f"Teams with Data:               {len(teams_processed)}/{len(TEAM_MAPPING)}")
    print(f"\nPlayers by Position:")
    for pos, count in position_counts.items():
        pos_name = {
            'C': 'Centers',
            'L': 'Left Wings',
            'R': 'Right Wings',
            'D': 'Defense',
            'G': 'Goalies'
        }.get(pos, pos)
        print(f"  {pos_name:15} {count:,}")
    
    return {
        "metadata": {
            "type": "historical_unified_roster",
            "seasons_included": ALL_SEASONS,
            "seasons_display": f"{ALL_SEASONS[0][:4]}-{ALL_SEASONS[0][4:]} through {ALL_SEASONS[-1][:4]}-{ALL_SEASONS[-1][4:]}",
            "generated_at": datetime.now().isoformat(),
            "total_teams": len(teams_processed),
            "total_unique_players": len(all_players),
            "total_raw_entries": total_raw_players,
            "players_by_position": position_counts,
            "teams_processed": sorted(list(teams_processed))
        },
        "teams": teams_list,
        "players": all_players
    }


def main():
    """Main execution function."""
    
    unified_data = build_unified_roster_historical()
    
    output_file = Path("data/processed/rosters/unified_roster_historical.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"SUCCESS: Historical unified roster saved to:")
    print(f"  {output_file}")
    print(f"  File size: {output_file.stat().st_size / 1024:.1f} KB")
    print(f"\nThis file contains all unique players from the last 10 NHL seasons")
    print(f"with complete team history for each player.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()

