# NHL Depth Chart Scrape - Complete

## Summary

Successfully scraped complete organizational depth charts for all **32 NHL teams** from CapWages.

**Total Players Captured:** 2,109 players across the NHL

## Breakdown by Team

| Team | Players | Breakdown |
|------|---------|-----------|
| ANA  | 65      | Anaheim Ducks |
| BOS  | 68      | Boston Bruins |
| BUF  | 73      | Buffalo Sabres |
| CAR  | 75      | Carolina Hurricanes |
| CBJ  | 62      | Columbus Blue Jackets |
| CGY  | 65      | Calgary Flames |
| CHI  | 63      | Chicago Blackhawks |
| COL  | 59      | Colorado Avalanche |
| DAL  | 61      | Dallas Stars |
| DET  | 73      | Detroit Red Wings |
| EDM  | 64      | Edmonton Oilers |
| FLA  | 65      | Florida Panthers |
| LAK  | 62      | Los Angeles Kings |
| MIN  | 60      | Minnesota Wild |
| MTL  | 115     | Montreal Canadiens |
| NJD  | 70      | New Jersey Devils |
| NSH  | 66      | Nashville Predators |
| NYI  | 66      | New York Islanders |
| NYR  | 63      | New York Rangers |
| OTT  | 64      | Ottawa Senators |
| PHI  | 69      | Philadelphia Flyers |
| PIT  | 71      | Pittsburgh Penguins |
| SEA  | 66      | Seattle Kraken |
| SJS  | 78      | San Jose Sharks |
| STL  | 61      | St. Louis Blues |
| TBL  | 70      | Tampa Bay Lightning |
| TOR  | 72      | Toronto Maple Leafs |
| UTA  | 73      | Utah Mammoth |
| VAN  | 58      | Vancouver Canucks |
| VGK  | 59      | Vegas Golden Knights |
| WPG  | 58      | Winnipeg Jets |
| WSH  | 60      | Washington Capitals |

## Data Structure

Each CSV file contains:

### Essential Columns
- `player_name` - Full player name
- `position` - Position(s) played
- `roster_status` - **roster** / **non_roster** / **unsigned**
- `jersey_number` - Jersey number (if assigned)
- `age` - Player age

### Draft Information (for unsigned players)
- `drafted_by` - Team that drafted the player
- `draft_year` - Year player was drafted
- `draft_round` - Round selected
- `draft_overall` - Overall pick number
- `must_sign_date` - Deadline to sign player

### Metadata
- `scraped_date` - Date the data was captured (2025-10-18)

## File Locations

All CSV files are saved in:
```
/Users/xavier.bouchard/Desktop/HeartBeat/data/depth_charts/
```

Format: `{TEAM_CODE}_depth_chart_2025-10-18.csv`

## Database Storage

All data is also stored in:
```
/Users/xavier.bouchard/Desktop/HeartBeat/data/heartbeat_news.duckdb
```

Table: `team_rosters`

## Example: Vegas Golden Knights Unsigned Players

```csv
"Ihs-Wozniak, Jakob",C,unsigned,,18,VGK,2025,2,55,"Jun. 1, 2029",2025-10-18
"Ellis, Noah",RD,unsigned,,23,VGK,2020,6,184,"Aug. 15, 2026",2025-10-18
"Karki, Arttu",LD,unsigned,,20,VGK,2023,3,96,"Jun. 1, 2027",2025-10-18
```

Each unsigned player includes complete draft details for tracking development and signing deadlines.

## Usage

View any team's roster:
```bash
python3 view_roster.py VGK
python3 view_roster.py MTL
```

Re-scrape specific teams:
```bash
python3 -m backend.bot.scrape_depth_charts --teams VGK MTL TOR
```

Re-scrape all teams:
```bash
python3 -m backend.bot.scrape_depth_charts --all
```

## Notes

- Montreal Canadiens has the most players (115) including extensive unsigned/prospect pool
- Vancouver and Winnipeg have the smallest organizations (58 players each)
- All teams successfully scraped except initial Utah issue (now resolved as utah_mammoth)
- Financial details (cap hit, cap %) intentionally excluded - focus is organizational depth only
- Can be easily mapped to existing contract details using player names

## Next Steps

This organizational depth chart data can now be:
1. Cross-referenced with your existing contract database
2. Used to identify prospects and unsigned talent
3. Tracked over time to monitor organizational changes
4. Integrated into team roster pages
5. Used for prospect pipeline analysis

