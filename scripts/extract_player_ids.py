#!/usr/bin/env python3
"""
Player ID Extraction Script

This script processes all 82 Montreal Canadiens play-by-play CSV files to extract
and consolidate player information into a canonical player mapping file.

The script:
1. Reads all CSV files from the mtl_play_by_play directory
2. Extracts player first name, last name, and reference ID
3. Creates a unique mapping ensuring each reference ID maps to one player
4. Handles data inconsistencies and reports any conflicts
5. Outputs a clean player_ids.csv file

Author: AI Assistant
Date: September 25, 2025
"""

import pandas as pd
import os
import glob
from pathlib import Path
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_player_ids():
    """
    Extract and consolidate player IDs from all play-by-play CSV files.
    
    Returns:
        pd.DataFrame: Consolidated player information
    """
    
    # Define paths
    play_by_play_dir = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/mtl_play_by_play")
    output_dir = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/processed")
    output_file = output_dir / "player_ids.csv"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all CSV files
    csv_files = list(play_by_play_dir.glob("*.csv"))
    csv_files.sort()  # Sort for consistent processing order
    
    logger.info(f"Found {len(csv_files)} CSV files to process")
    
    if len(csv_files) == 0:
        logger.error("No CSV files found in the mtl_play_by_play directory!")
        return None
    
    # Dictionary to store player information
    # Key: reference_id, Value: dict with player info
    players_dict = {}
    
    # Dictionary to track conflicts
    conflicts = defaultdict(list)
    
    # Process each CSV file
    for i, csv_file in enumerate(csv_files, 1):
        try:
            logger.info(f"Processing file {i}/{len(csv_files)}: {csv_file.name}")
            
            # Read the CSV file
            df = pd.read_csv(csv_file)
            
            # Extract player data - filter out rows where player info is missing
            player_data = df[['playerFirstName', 'playerLastName', 'playerReferenceId']].copy()
            
            # Remove rows where any player field is NaN or empty
            player_data = player_data.dropna()
            player_data = player_data[
                (player_data['playerFirstName'].str.strip() != '') &
                (player_data['playerLastName'].str.strip() != '') &
                (player_data['playerReferenceId'].astype(str).str.strip() != '')
            ]
            
            # Remove duplicates within this file
            player_data = player_data.drop_duplicates()
            
            # Process each player record
            for _, row in player_data.iterrows():
                ref_id = str(int(float(row['playerReferenceId'])))  # Convert to string, handle float format
                first_name = row['playerFirstName'].strip()
                last_name = row['playerLastName'].strip()
                
                if ref_id in players_dict:
                    # Check for conflicts (same ID, different name)
                    existing = players_dict[ref_id]
                    if (existing['first_name'] != first_name or 
                        existing['last_name'] != last_name):
                        
                        conflict_info = {
                            'file': csv_file.name,
                            'existing': f"{existing['first_name']} {existing['last_name']}",
                            'new': f"{first_name} {last_name}",
                            'ref_id': ref_id
                        }
                        conflicts[ref_id].append(conflict_info)
                        logger.warning(f"Conflict detected for ID {ref_id}: "
                                     f"'{existing['first_name']} {existing['last_name']}' vs "
                                     f"'{first_name} {last_name}' in {csv_file.name}")
                else:
                    # Add new player
                    players_dict[ref_id] = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'reference_id': ref_id,
                        'first_seen_in': csv_file.name
                    }
            
        except Exception as e:
            logger.error(f"Error processing {csv_file.name}: {str(e)}")
            continue
    
    # Convert to DataFrame
    if players_dict:
        players_list = []
        for ref_id, player_info in players_dict.items():
            players_list.append({
                'reference_id': player_info['reference_id'],
                'first_name': player_info['first_name'],
                'last_name': player_info['last_name'],
                'full_name': f"{player_info['first_name']} {player_info['last_name']}",
                'first_seen_in_file': player_info['first_seen_in']
            })
        
        players_df = pd.DataFrame(players_list)
        
        # Sort by reference ID for consistency
        players_df = players_df.sort_values('reference_id').reset_index(drop=True)
        
        # Save to CSV
        players_df.to_csv(output_file, index=False)
        
        # Log summary statistics
        logger.info(f"Successfully processed {len(csv_files)} files")
        logger.info(f"Extracted {len(players_df)} unique players")
        logger.info(f"Found {len(conflicts)} reference IDs with conflicts")
        logger.info(f"Output saved to: {output_file}")
        
        # Report conflicts if any
        if conflicts:
            conflicts_file = output_dir / "player_conflicts.txt"
            with open(conflicts_file, 'w') as f:
                f.write("Player Reference ID Conflicts Report\n")
                f.write("="*50 + "\n\n")
                
                for ref_id, conflict_list in conflicts.items():
                    f.write(f"Reference ID: {ref_id}\n")
                    for conflict in conflict_list:
                        f.write(f"  File: {conflict['file']}\n")
                        f.write(f"  Existing: {conflict['existing']}\n")
                        f.write(f"  Conflicting: {conflict['new']}\n")
                    f.write("\n")
            
            logger.warning(f"Conflicts report saved to: {conflicts_file}")
        
        # Display sample of results
        logger.info("\nSample of extracted players:")
        logger.info(players_df.head(10).to_string(index=False))
        
        return players_df
    
    else:
        logger.error("No player data found in any files!")
        return None

def main():
    """Main execution function"""
    try:
        logger.info("Starting player ID extraction process...")
        
        result = extract_player_ids()
        
        if result is not None:
            logger.info("Player ID extraction completed successfully!")
            logger.info(f"Total unique players found: {len(result)}")
        else:
            logger.error("Player ID extraction failed!")
            
    except Exception as e:
        logger.error(f"Unexpected error in main execution: {str(e)}")

if __name__ == "__main__":
    main()
