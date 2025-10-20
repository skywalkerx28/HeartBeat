# NHL Depth Chart Scraper Guide

## Overview

The HeartBeat bot now includes a comprehensive depth chart scraper that extracts complete organizational rosters from CapWages for all 32 NHL teams.

## What It Extracts

For each team, the scraper captures:

1. **Roster** - Active NHL roster (forwards, defense, goalies, injured reserve)
2. **Non-Roster** - Players under contract but in AHL/ECHL/minors
3. **Unsigned** - Draft picks and players whose rights are owned by the team

## Player Information Captured

For each player:
- Player name
- Position
- Roster status (roster / non_roster / unsigned)
- Jersey number
- Cap hit
- Cap percentage
- Age
- Contract expiry
- Handedness (L/R)
- Birthplace
- Draft information
- Source URL

## Usage

### Scrape a Single Team (with CSV export)

```bash
python3 -m backend.bot.scrape_depth_charts --team VGK
```

This will:
- Scrape the depth chart from CapWages
- Store data in the database
- **Automatically export to CSV** at `data/depth_charts/VGK_depth_chart_YYYY-MM-DD.csv`

### Scrape Multiple Teams

```bash
python3 -m backend.bot.scrape_depth_charts --teams VGK MTL TOR BOS
```

### Scrape All 32 Teams

```bash
python3 -m backend.bot.scrape_depth_charts --all
```

### Export Only (No Scraping)

If you've already scraped data and just want to generate CSV files:

```bash
# Single team
python3 -m backend.bot.scrape_depth_charts --team VGK --export-csv

# Multiple teams
python3 -m backend.bot.scrape_depth_charts --teams VGK MTL TOR --export-csv

# All teams
python3 -m backend.bot.scrape_depth_charts --all --export-csv
```

### Skip CSV Export

If you only want to scrape to the database without generating CSVs:

```bash
python3 -m backend.bot.scrape_depth_charts --team VGK --no-csv
```

## Team Codes

All 32 NHL teams are supported:

**Atlantic Division:**
- MTL (Montreal Canadiens)
- TOR (Toronto Maple Leafs)
- BOS (Boston Bruins)
- BUF (Buffalo Sabres)
- OTT (Ottawa Senators)
- DET (Detroit Red Wings)
- FLA (Florida Panthers)
- TBL (Tampa Bay Lightning)

**Metropolitan Division:**
- NYR (New York Rangers)
- NYI (New York Islanders)
- PHI (Philadelphia Flyers)
- WSH (Washington Capitals)
- CAR (Carolina Hurricanes)
- NJD (New Jersey Devils)
- CBJ (Columbus Blue Jackets)
- PIT (Pittsburgh Penguins)

**Central Division:**
- COL (Colorado Avalanche)
- DAL (Dallas Stars)
- MIN (Minnesota Wild)
- NSH (Nashville Predators)
- STL (St. Louis Blues)
- WPG (Winnipeg Jets)
- CHI (Chicago Blackhawks)
- UTA (Utah Hockey Club)

**Pacific Division:**
- VGK (Vegas Golden Knights)
- SEA (Seattle Kraken)
- LAK (Los Angeles Kings)
- SJS (San Jose Sharks)
- ANA (Anaheim Ducks)
- VAN (Vancouver Canucks)
- CGY (Calgary Flames)
- EDM (Edmonton Oilers)

## Data Storage

### Database

All roster data is stored in the `team_rosters` table in the HeartBeat News database (`data/heartbeat_news.duckdb`).

Each scrape creates a timestamped snapshot, allowing you to track roster changes over time.

### CSV Files

CSV files are automatically generated and saved to `data/depth_charts/` with the format:

```
{TEAM_CODE}_depth_chart_{YYYY-MM-DD}.csv
```

For example: `VGK_depth_chart_2025-10-18.csv`

**CSV Columns:**
- `player_name` - Player's full name
- `position` - Position(s) played
- `roster_status` - roster / non_roster / unsigned
- `jersey_number` - Jersey number (if assigned)
- `age` - Player age
- `cap_hit` - Annual cap hit (formatted with $ and commas)
- `cap_percent` - Percentage of salary cap
- `contract_expiry` - Contract expiry year
- `handed` - Shoots/Catches (L/R)
- `birthplace` - Player's birthplace
- `draft_info` - Draft year and details
- `scraped_date` - Date the data was scraped

## Example Output

```
2025-10-18 09:27:57,350 - __main__ - INFO - Successfully scraped Vegas Golden Knights (VGK)
2025-10-18 09:27:57,350 - __main__ - INFO -   Roster: 30 players
2025-10-18 09:27:57,350 - __main__ - INFO -   Non-Roster: 26 players
2025-10-18 09:27:57,350 - __main__ - INFO -   Unsigned: 10 players
2025-10-18 09:27:57,350 - __main__ - INFO -   Total Cap Hit: $211,565,510
```

## Accessing the Data

You can query the roster data using the database connection:

```python
from backend.bot import db

# Get latest roster for a team
with db.get_connection() as conn:
    roster = db.get_team_roster(conn, 'VGK', latest_only=True)
    
    for player in roster:
        print(f"{player['player_name']} - {player['position']} - {player['roster_status']}")
```

## Data Source

All data is scraped from CapWages.com, a trusted source for NHL salary cap and contract information.

## Rate Limiting

The scraper includes built-in delays to be respectful of the CapWages server. When scraping all 32 teams, expect the process to take several minutes.

## Notes

- Each scrape creates a new snapshot with the current date
- Players are automatically deduplicated within the same snapshot
- Cap hit values are stored in dollars (not formatted)
- The scraper handles injured reserve players, retainedburied contracts, and all roster statuses

## Integration

This depth chart data can be integrated with:
- Contract analysis tools
- Roster comparison features
- Salary cap tracking
- Player movement tracking
- Organizational depth analysis

