# Missing Contracts Scraper Guide

## Overview

The Missing Contracts Scraper is designed to scrape contract data from CapWages for all **1,141 players** identified in the cross-reference analysis who appear in league stats but don't have contract data yet.

## Key Files

- **Script**: `scripts/ingest/scrape_missing_contracts.py`
- **Input**: `data/contracts/missing_contracts_players.csv` (1,141 players)
- **Output**: Individual contract CSV files in `data/contracts/` directory
- **Progress**: `data/contracts/missing_contracts_progress.json` (auto-saved)
- **Summary**: `data/contracts/missing_contracts_summary_TIMESTAMP.csv` (generated after completion)

## Features

### Intelligent Player Handling
- Automatically converts player names to CapWages slugs (e.g., "Sidney Crosby" -> "sidney-crosby")
- Handles special characters, accents, apostrophes, and hyphens correctly
- Maps scraped data to NHL Player IDs using unified roster

### Three Outcome Categories
1. **SUCCESS**: Contract data found and scraped
2. **NOT FOUND**: Player not on CapWages (likely retired/older players)
3. **FAILED**: Error during scraping (network issues, parsing errors, etc.)

### Progress Tracking
- Auto-saves progress every 10 players
- Can resume from any point if interrupted
- Detailed logging to both console and file

### Rate Limiting
- Configurable delay between requests (default: 2 seconds)
- Respectful scraping to avoid overwhelming CapWages servers

## Usage Examples

### 1. Scrape Only 2024-2025 Season Players (RECOMMENDED START)

This is the highest priority group - **177 active players**:

```bash
python3 scripts/ingest/scrape_missing_contracts.py --priority-season 2024-2025
```

### 2. Test with Small Batch

Test with just 10 players to verify everything works:

```bash
python3 scripts/ingest/scrape_missing_contracts.py --max 10 --priority-season 2024-2025
```

### 3. Scrape All Missing Players

Scrape all 1,141 players (will take ~1 hour with 2-second delay):

```bash
python3 scripts/ingest/scrape_missing_contracts.py
```

### 4. Resume After Interruption

If the script was interrupted at player 150:

```bash
python3 scripts/ingest/scrape_missing_contracts.py --start 150 --priority-season 2024-2025
```

### 5. Fast Mode (Use Cautiously)

Faster scraping with 1-second delay:

```bash
python3 scripts/ingest/scrape_missing_contracts.py --delay 1.0 --priority-season 2024-2025
```

## Command-Line Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--output-dir` | `-o` | `data/contracts` | Output directory for CSV files |
| `--delay` | `-d` | `2.0` | Delay between requests (seconds) |
| `--start` | `-s` | `0` | Start from this player index |
| `--max` | `-m` | `None` | Maximum number of players to process |
| `--priority-season` | `-p` | `None` | Filter to specific season (e.g., `2024-2025`) |
| `--progress-file` | | `missing_contracts_progress.json` | Progress tracking file |

## Output Format

For each successfully scraped player, three CSV files are created:

### 1. Summary File (`lastname_playerid_summary_TIMESTAMP.csv`)
Complete overview with:
- Player information (name, ID, team, position, number)
- Contract summary (type, signing date, value, cap hit)
- Year-by-year contract details

### 2. Contracts File (`lastname_playerid_contracts_TIMESTAMP.csv`)
Individual contracts with columns:
- player_name, contract_type, team_code, signing_date
- signed_by, length_years, total_value, expiry_status
- cap_hit, cap_percent, source_url

### 3. Contract Details File (`lastname_playerid_contract_details_TIMESTAMP.csv`)
Year-by-year breakdown with columns:
- season, clause, cap_hit, cap_percent, aav
- performance_bonuses, signing_bonuses, base_salary
- total_salary, minors_salary

## Player Breakdown by Season

| Season | Players Missing Contracts |
|--------|---------------------------|
| 2024-2025 | **177** (highest priority) |
| 2023-2024 | 151 |
| 2022-2023 | 97 |
| 2021-2022 | 123 |
| 2020-2021 | 79 |
| 2019-2020 | 91 |
| 2018-2019 | 95 |
| 2017-2018 | 104 |
| 2016-2017 | 94 |
| 2015-2016 | 130 |
| **TOTAL** | **1,141** |

## Expected Results

Based on testing:

- **Success Rate**: ~40-60% for active players (2024-2025)
- **Not Found Rate**: ~30-50% (older/retired players not on CapWages)
- **Error Rate**: ~1-5% (network issues, parsing errors)

### Why Some Players Aren't Found

CapWages primarily covers:
- Current NHL players
- Recent players (last 5-10 years)
- Players with significant contracts

Players NOT typically found:
- Retired players from earlier seasons
- Players who never signed significant contracts
- Players who only played a few games
- AHL/minor league only players

## Monitoring Progress

### Console Output

The script provides real-time updates:

```
[63/177] Processing: Matthew Poitras (ID: 8483505)
  Most Recent Season: 2024-2025
  CapWages Slug: matthew-poitras
  URL: https://capwages.com/players/matthew-poitras
  ✓ SUCCESS: 1 contracts scraped
```

### Log File

Detailed logging is saved to:
```
data/contracts/missing_contracts_scrape.log
```

### Progress File

JSON file with current state:
```json
{
  "started_at": "2025-10-17T12:26:31",
  "total_players": 177,
  "processed": 63,
  "succeeded": 42,
  "not_found": 19,
  "failed": 2,
  "current_index": 62
}
```

## Summary Report

After completion, a comprehensive CSV summary is generated:

**Sections**:
1. Overall Statistics (total, success rate, etc.)
2. Successful Scrapes (player name, ID, contracts found)
3. Not Found Players (likely retired/older)
4. Failed Scrapes (errors that need investigation)

## Recommended Workflow

### Phase 1: Current Season (HIGH PRIORITY)
```bash
# Test first
python3 scripts/ingest/scrape_missing_contracts.py --max 10 --priority-season 2024-2025

# Run full 2024-2025 season (177 players, ~6-10 minutes)
python3 scripts/ingest/scrape_missing_contracts.py --priority-season 2024-2025
```

### Phase 2: Recent Seasons
```bash
# 2023-2024 season (151 players)
python3 scripts/ingest/scrape_missing_contracts.py --priority-season 2023-2024

# 2022-2023 season (97 players)
python3 scripts/ingest/scrape_missing_contracts.py --priority-season 2022-2023
```

### Phase 3: All Remaining Players
```bash
# Scrape all 1,141 players (~40-60 minutes)
python3 scripts/ingest/scrape_missing_contracts.py
```

## Handling Interruptions

If interrupted (Ctrl+C), the script saves progress automatically.

To resume:
```bash
# Check last processed index in progress file
cat data/contracts/missing_contracts_progress.json | grep current_index

# Resume from that index
python3 scripts/ingest/scrape_missing_contracts.py --start 150
```

## Database Integration

All successfully scraped contracts are automatically:
1. **Stored in Database**: `data/heartbeat_news.duckdb`
   - `player_contracts` table
   - `contract_details` table
2. **Exported to CSV**: Individual files per player
3. **Mapped to NHL IDs**: Using `unified_roster_historical.json`

## Troubleshooting

### Issue: "Player not found on CapWages"
**Solution**: Expected for older/retired players. These are tracked separately in the summary.

### Issue: Script crashes with network error
**Solution**: Simply re-run with `--start` flag to resume from last checkpoint.

### Issue: "Failed to load roster"
**Solution**: Ensure `data/processed/rosters/unified_roster_historical.json` exists.

### Issue: Rate limiting / 429 errors
**Solution**: Increase delay: `--delay 3.0` or `--delay 5.0`

## Performance Estimates

| Batch Size | Delay | Estimated Time |
|------------|-------|----------------|
| 177 (2024-2025) | 2s | ~6-10 minutes |
| 500 players | 2s | ~20-25 minutes |
| 1,141 (all) | 2s | ~40-60 minutes |
| 1,141 (all) | 1s | ~20-30 minutes |

## Success Criteria

After running, you should see:
- ✅ Contract CSV files created for successful players
- ✅ Progress saved to JSON file
- ✅ Summary CSV with detailed breakdown
- ✅ Log file with complete audit trail
- ✅ Data stored in DuckDB database

## Next Steps

After scraping:

1. **Review Summary Report**: Check success rate and identify patterns
2. **Validate Data**: Spot-check a few players' contracts
3. **Update Missing List**: Re-run `find_missing_contracts.py` to see remaining gaps
4. **Manual Research**: For high-priority players not found, research manually

## Notes

- The script respects CapWages by including user agent and rate limiting
- Some players may legitimately not have contract data (short careers, specific circumstances)
- The NHL Player ID mapping helps maintain data integrity across the system
- All files follow the same format as existing contract files for consistency

