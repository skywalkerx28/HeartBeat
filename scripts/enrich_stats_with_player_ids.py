"""
Enrich League Player Stats with Player IDs and Birth Dates

This script adds player ID and date of birth columns to all unified player stats files
by matching player names with the unified_roster_historical.json file.

INPUT:
- data/processed/rosters/unified_roster_historical.json (lookup source)
- data/processed/league_player_stats/{season}/unified_player_stats_{season}.csv

OUTPUT:
- Updates each CSV with two new columns: 'Player ID' and 'Date of Birth'

Author: HeartBeat Engine
Date: October 2025
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import re
import unicodedata


def normalize_accents(text: str) -> str:
    """
    Remove accents and special characters from text.
    Example: 'Slafkovský' -> 'Slafkovsky'
    """
    
    if not text:
        return ""
    
    # Normalize to NFD (decomposed form) and remove combining characters
    nfd = unicodedata.normalize('NFD', text)
    ascii_text = nfd.encode('ascii', 'ignore').decode('utf-8')
    
    return ascii_text


def load_player_lookup(unified_roster_path: str) -> Tuple[Dict[str, Tuple[str, str]], Dict[str, Tuple[str, str]], Dict[str, List[Tuple[str, str, str]]]]:
    """
    Load unified roster and create multiple lookup dictionaries for robust matching.
    
    Args:
        unified_roster_path: Path to unified_roster_historical.json
        
    Returns:
        Tuple of three dictionaries:
        - exact_lookup: exact name (lowercase) -> (player_id, birth_date)
        - normalized_lookup: accent-normalized name -> (player_id, birth_date, original_name)
        - lastname_lookup: last name -> list of (full_name, player_id, birth_date)
    """
    
    print(f"Loading unified roster from: {unified_roster_path}")
    
    with open(unified_roster_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    exact_lookup = {}
    normalized_lookup = {}
    lastname_lookup = {}
    
    for player in data['players']:
        name = player.get('name', '').strip()
        player_id = str(player.get('id', ''))
        birth_date = player.get('birthDate', '')
        
        if name:
            # Exact match lookup (case-insensitive)
            exact_lookup[name.lower()] = (player_id, birth_date)
            
            # Accent-normalized lookup
            normalized = normalize_accents(name).lower()
            normalized_lookup[normalized] = (player_id, birth_date, name)
            
            # Last name lookup for fuzzy matching
            parts = name.split()
            if parts:
                last_name = parts[-1].lower()
                if last_name not in lastname_lookup:
                    lastname_lookup[last_name] = []
                lastname_lookup[last_name].append((name, player_id, birth_date))
    
    print(f"  Loaded {len(exact_lookup):,} players with multiple lookup strategies")
    
    return exact_lookup, normalized_lookup, lastname_lookup


def normalize_name(name: str) -> str:
    """
    Normalize player name for better matching.
    Removes extra spaces, handles special characters.
    """
    
    if pd.isna(name):
        return ""
    
    name = str(name).strip()
    name = re.sub(r'\s+', ' ', name)
    
    return name


def find_player_match(
    player_name: str,
    exact_lookup: Dict[str, Tuple[str, str]],
    normalized_lookup: Dict[str, Tuple[str, str, str]],
    lastname_lookup: Dict[str, List[Tuple[str, str, str]]]
) -> Optional[Tuple[str, str, str]]:
    """
    Find player match using multiple strategies.
    
    Returns:
        Tuple of (player_id, birth_date, match_type) or None
    """
    
    if not player_name:
        return None
    
    # Strategy 1: Exact match (case-insensitive)
    player_lower = player_name.lower()
    if player_lower in exact_lookup:
        player_id, birth_date = exact_lookup[player_lower]
        return (player_id, birth_date, 'exact')
    
    # Strategy 2: Accent-normalized match
    normalized = normalize_accents(player_name).lower()
    if normalized in normalized_lookup:
        player_id, birth_date, original = normalized_lookup[normalized]
        return (player_id, birth_date, 'normalized')
    
    # Strategy 3: Last name + first initial match
    parts = player_name.split()
    if len(parts) >= 2:
        last_name = parts[-1].lower()
        first_initial = parts[0][0].lower() if parts[0] else ''
        
        if last_name in lastname_lookup:
            candidates = lastname_lookup[last_name]
            
            # Try to match on first initial
            for full_name, player_id, birth_date in candidates:
                roster_parts = full_name.split()
                if roster_parts:
                    roster_first_initial = roster_parts[0][0].lower()
                    if roster_first_initial == first_initial:
                        return (player_id, birth_date, 'lastname_initial')
    
    return None


def enrich_stats_file(
    stats_file: Path,
    exact_lookup: Dict[str, Tuple[str, str]],
    normalized_lookup: Dict[str, Tuple[str, str, str]],
    lastname_lookup: Dict[str, List[Tuple[str, str, str]]],
    season: str
) -> Tuple[int, int, int, Dict[str, int]]:
    """
    Enrich a single stats file with player IDs and birth dates.
    
    Args:
        stats_file: Path to the stats CSV file
        exact_lookup: Exact name matching dictionary
        normalized_lookup: Accent-normalized matching dictionary
        lastname_lookup: Last name matching dictionary
        season: Season string for reporting
        
    Returns:
        Tuple of (total_players, matched_players, unmatched_players, match_type_counts)
    """
    
    print(f"\nProcessing {season}...")
    print(f"  File: {stats_file.name}")
    
    df = pd.read_csv(stats_file)
    
    print(f"  Total rows: {len(df):,}")
    
    # Initialize new columns
    df['Player ID'] = ''
    df['Date of Birth'] = ''
    
    matched = 0
    unmatched = 0
    unmatched_players = []
    match_type_counts = {'exact': 0, 'normalized': 0, 'lastname_initial': 0}
    
    for idx, row in df.iterrows():
        player_name = normalize_name(row.get('Player', ''))
        
        result = find_player_match(player_name, exact_lookup, normalized_lookup, lastname_lookup)
        
        if result:
            player_id, birth_date, match_type = result
            df.at[idx, 'Player ID'] = player_id
            df.at[idx, 'Date of Birth'] = birth_date
            matched += 1
            match_type_counts[match_type] += 1
        else:
            unmatched += 1
            if player_name:
                unmatched_players.append(player_name)
    
    # Reorder columns: put Player ID and Date of Birth right after Player
    cols = df.columns.tolist()
    
    # Find the index of 'Player' column
    player_idx = cols.index('Player')
    
    # Remove the new columns from their current position
    cols.remove('Player ID')
    cols.remove('Date of Birth')
    
    # Insert them right after 'Player'
    cols.insert(player_idx + 1, 'Player ID')
    cols.insert(player_idx + 2, 'Date of Birth')
    
    df = df[cols]
    
    # Save enriched file
    df.to_csv(stats_file, index=False)
    
    print(f"  Matched: {matched:,} players ({matched/len(df)*100:.1f}%)")
    print(f"    - Exact: {match_type_counts['exact']}")
    print(f"    - Normalized (accents): {match_type_counts['normalized']}")
    print(f"    - Last name + initial: {match_type_counts['lastname_initial']}")
    print(f"  Unmatched: {unmatched:,} players ({unmatched/len(df)*100:.1f}%)")
    
    if unmatched_players and unmatched <= 10:
        print(f"  Unmatched names: {', '.join(unmatched_players[:10])}")
    
    return len(df), matched, unmatched, match_type_counts


def main():
    """Main execution function."""
    
    base_path = Path("/Users/xavier.bouchard/Desktop/HeartBeat")
    unified_roster_path = base_path / "data/processed/rosters/unified_roster_historical.json"
    stats_base_path = base_path / "data/processed/league_player_stats"
    
    # Load player lookup with multiple strategies
    exact_lookup, normalized_lookup, lastname_lookup = load_player_lookup(unified_roster_path)
    
    # Define seasons to process
    seasons = [
        '2015-2016', '2016-2017', '2017-2018', '2018-2019', '2019-2020',
        '2020-2021', '2021-2022', '2022-2023', '2023-2024', '2024-2025'
    ]
    
    print(f"\n{'='*80}")
    print("ENRICHING LEAGUE PLAYER STATS WITH PLAYER IDs AND BIRTH DATES")
    print(f"{'='*80}")
    
    total_stats = {
        'total_players': 0,
        'total_matched': 0,
        'total_unmatched': 0,
        'seasons_processed': 0,
        'seasons_failed': [],
        'match_types': {'exact': 0, 'normalized': 0, 'lastname_initial': 0}
    }
    
    for season in seasons:
        season_key = season.replace('-', '')
        stats_file = stats_base_path / season / f"unified_player_stats_{season_key}.csv"
        
        if not stats_file.exists():
            print(f"\nWARNING: File not found for {season}")
            total_stats['seasons_failed'].append(season)
            continue
        
        try:
            players, matched, unmatched, match_types = enrich_stats_file(
                stats_file, exact_lookup, normalized_lookup, lastname_lookup, season
            )
            
            total_stats['total_players'] += players
            total_stats['total_matched'] += matched
            total_stats['total_unmatched'] += unmatched
            total_stats['seasons_processed'] += 1
            
            for match_type, count in match_types.items():
                total_stats['match_types'][match_type] += count
            
        except Exception as e:
            print(f"\nERROR processing {season}: {str(e)}")
            import traceback
            traceback.print_exc()
            total_stats['seasons_failed'].append(season)
    
    # Print summary
    print(f"\n{'='*80}")
    print("ENRICHMENT SUMMARY")
    print(f"{'='*80}")
    print(f"Seasons processed: {total_stats['seasons_processed']}/10")
    print(f"Total player records: {total_stats['total_players']:,}")
    print(f"Successfully matched: {total_stats['total_matched']:,} ({total_stats['total_matched']/total_stats['total_players']*100:.1f}%)")
    print(f"\nMatch breakdown:")
    print(f"  - Exact matches: {total_stats['match_types']['exact']:,}")
    print(f"  - Accent-normalized: {total_stats['match_types']['normalized']:,}")
    print(f"  - Last name + initial: {total_stats['match_types']['lastname_initial']:,}")
    print(f"\nUnmatched: {total_stats['total_unmatched']:,} ({total_stats['total_unmatched']/total_stats['total_players']*100:.1f}%)")
    
    if total_stats['seasons_failed']:
        print(f"\nWARNING - Failed seasons: {', '.join(total_stats['seasons_failed'])}")
    
    print(f"\nEnrichment complete! All stats files now include Player ID and Date of Birth columns.")


if __name__ == "__main__":
    main()

