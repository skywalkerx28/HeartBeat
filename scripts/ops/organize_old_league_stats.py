"""
Organize league player stats directories for seasons 2020-2021 and earlier.
Creates the same subfolder structure as newer seasons: forwards/defensemen with general/advanced subdirectories.
"""

import os
from pathlib import Path


def create_subfolder_structure(season_dir: Path) -> None:
    """
    Create the standard subfolder structure for a season directory.
    
    Structure:
    - forwards/
      - general/
      - advanced/
    - defensemen/
      - general/
      - advanced/
    """
    positions = ['forwards', 'defensemen']
    categories = ['general', 'advanced']
    
    for position in positions:
        for category in categories:
            subfolder_path = season_dir / position / category
            subfolder_path.mkdir(parents=True, exist_ok=True)
            print(f"Created: {subfolder_path}")


def main():
    """Organize league player stats for seasons 2020-2021 and earlier."""
    
    # Base directory
    base_dir = Path('/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/league_player_stats')
    
    # Seasons to organize (2020-2021 and earlier)
    seasons_to_organize = [
        '2015-2016',
        '2016-2017',
        '2017-2018',
        '2018-2019',
        '2019-2020',
        '2020-2021'
    ]
    
    print("Starting league player stats organization for older seasons...")
    print("=" * 80)
    
    for season in seasons_to_organize:
        season_dir = base_dir / season
        
        if not season_dir.exists():
            print(f"\nWarning: Season directory does not exist: {season_dir}")
            continue
        
        print(f"\nOrganizing season: {season}")
        print("-" * 80)
        create_subfolder_structure(season_dir)
    
    print("\n" + "=" * 80)
    print("Organization complete!")
    print("\nStructure created:")
    print("  - forwards/")
    print("    - general/")
    print("    - advanced/")
    print("  - defensemen/")
    print("    - general/")
    print("    - advanced/")


if __name__ == '__main__':
    main()

