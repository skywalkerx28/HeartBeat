#!/usr/bin/env python3
"""
Script to fetch current team information for all players in player_ids.csv
using the NHL Stats API and add a Current Team column to the CSV.
"""

import csv
import json
import requests
import time
import random
from typing import Optional

def get_player_current_team(player_id: str) -> Optional[str]:
    """
    Fetch current team for a player using NHL Stats API.

    Args:
        player_id: NHL player ID (e.g., '8471214')

    Returns:
        Current team abbreviation, or None if not found/error
    """
    # Try skater endpoint first
    skater_url = f'https://api.nhle.com/stats/rest/en/skater/summary?cayenneExp=playerId={player_id}'

    try:
        response = requests.get(skater_url, timeout=15)
        response.raise_for_status()

        data = response.json()

        if 'data' in data and len(data['data']) > 0:
            # Get the most recent season (first in the list)
            most_recent_season = data['data'][0]
            current_team = most_recent_season.get('teamAbbrevs')
            if current_team:  # Only return if we actually got a team
                return current_team

    except requests.exceptions.RequestException as e:
        # Log but continue to goalie endpoint
        pass
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        # Log but continue to goalie endpoint
        pass

    # Try goalie endpoint as fallback
    goalie_url = f'https://api.nhle.com/stats/rest/en/goalie/summary?cayenneExp=playerId={player_id}'

    try:
        response = requests.get(goalie_url, timeout=15)
        response.raise_for_status()

        data = response.json()

        if 'data' in data and len(data['data']) > 0:
            # Get the most recent season (first in the list)
            most_recent_season = data['data'][0]
            current_team = most_recent_season.get('teamAbbrevs')
            if current_team:  # Only return if we actually got a team
                return current_team

    except requests.exceptions.RequestException as e:
        # Only log errors for debugging, don't print for every player
        pass
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        # Only log errors for debugging, don't print for every player
        pass

    # If we get here, no team data was found
    return None

def main():
    """Main function to update player_ids.csv with current team data."""
    csv_path = 'data/processed/dim/player_ids.csv'
    backup_path = 'data/processed/dim/player_ids_backup.csv'

    # Read existing data
    players = []
    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            players.append(row)

    print(f'Loaded {len(players)} players from CSV')

    # Create backup
    with open(backup_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=players[0].keys())
        writer.writeheader()
        writer.writerows(players)

    print(f'Created backup at {backup_path}')

    # Update players with current team data
    updated_count = 0
    error_count = 0
    batch_size = 50  # Save progress every 50 players for faster feedback

    # Count players that already have team data
    initial_with_data = sum(1 for p in players if p.get('Current Team', '').strip())
    print(f'Starting with {initial_with_data} players already having team data')

    for i, player in enumerate(players):
        player_id = player['reference_id']
        full_name = player['full_name']

        # Skip if already has team data
        if player.get('Current Team', '').strip():
            continue

        # Fetch current team
        current_team = get_player_current_team(player_id)

        if current_team is not None and current_team.strip():
            player['Current Team'] = str(current_team).strip()
            updated_count += 1
        else:
            player['Current Team'] = ''  # Empty string for missing data
            error_count += 1

        # Print progress every 25 players
        if (i + 1) % 25 == 0:
            print(f'Processed {i+1}/{len(players)} players. Updated: {updated_count}, Errors: {error_count}')

        # Save progress every batch_size players
        if (i + 1) % batch_size == 0:
            print(f'Saving progress after {i + 1} players...')
            save_progress(csv_path, players)

        # Minimal rate limiting - very short delay
        if i < len(players) - 1:  # Don't delay after last player
            time.sleep(0.2)  # 0.2 second delay for faster processing

    # Final save
    save_progress(csv_path, players)

    print(f'\nCompleted!')
    print(f'Updated: {updated_count} players')
    print(f'Errors/Not found: {error_count} players')
    print(f'Total processed: {len(players)} players')

def save_progress(csv_path: str, players: list):
    """Save current progress to CSV file."""
    fieldnames = list(players[0].keys())
    if 'Current Team' not in fieldnames:
        fieldnames.append('Current Team')

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(players)

if __name__ == '__main__':
    main()
