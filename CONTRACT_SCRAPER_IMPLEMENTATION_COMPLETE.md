# Contract Scraper Implementation - COMPLETE

## Overview

Successfully implemented a comprehensive contract scraping system that extracts NHL player contract data from CapWages.com and automatically maps player names to their official NHL player IDs.

---

## ✅ What Was Implemented

### 1. Contract-Only Scraping (No Player Stats)
- **Removed**: All player statistics scraping code
- **Focus**: Exclusively on contract details and financial data
- **Database**: Removed player_career_stats table and functions
- **CSV Export**: Only contract-related files generated

### 2. Player Name to ID Mapping System
- **Intelligent Matching**: Handles multiple name formats
  - "Sidney#87 Crosby" → 8471675
  - "Sidney Crosby" → 8471675
  - "Crosby, Sidney" → 8471675
  - "Crosby" (with team) → 8471675

- **Mapping Methods**:
  1. **Exact Match**: Normalized name matching
  2. **Fuzzy Match**: 85% similarity threshold using SequenceMatcher
  3. **Last Name + Team**: Fallback for partial names

- **Data Source**: `/data/processed/rosters/unified_roster_20252026.json`
  - 769 NHL players
  - 1,536 name lookup entries
  - Official NHL player IDs

### 3. Enhanced CSV File Naming
- **New Format**: `lastname_playerid_type_timestamp.csv`
- **Example**: `crosby_8471675_contracts_20251016_161342.csv`
- **No Jersey Number**: Clean filenames without #87 or similar
- **Components**:
  - Last name (lowercase)
  - NHL Player ID
  - File type (contracts, contract_details, summary)
  - Timestamp

### 4. Enriched Data Export

#### CSV Files Generated (3 files per player):
1. **Contracts**: `lastname_playerid_contracts_timestamp.csv`
2. **Contract Details**: `lastname_playerid_contract_details_timestamp.csv`
3. **Summary**: `lastname_playerid_summary_timestamp.csv`

#### Summary CSV Includes:
```csv
PLAYER CONTRACT SUMMARY
Player Name,Sidney#87 Crosby
NHL Player ID,8471675
Official Name,Sidney Crosby
Current Team,PIT
Position,C
Number,#87
Export Date,2025-10-16 16:13:42
```

---

## 📊 Data Captured

### Contract Overview (4 contracts for Sidney Crosby)
- Contract type (35+, Standard, Entry-Level, Extension)
- Signing team
- Signing date & GM
- Length (years)
- Total value
- Expiry status (UFA/RFA)

### Contract Details - Year by Year (22 seasons)
**All 10 Columns Captured**:
1. Season
2. Clause (NMC/NTC)
3. Cap Hit
4. Cap %
5. AAV (Average Annual Value)
6. Performance Bonuses
7. Signing Bonuses
8. Base Salary
9. Total Salary
10. **Minors Salary** (when applicable)

---

## 🗄️ Database Storage

### Tables:
- **player_contracts**: Main contract records with NHL player_id
- **contract_details**: Year-by-year financial breakdown

### Player ID Storage:
```sql
SELECT player_name, player_id, team_code, contract_type, signing_date 
FROM player_contracts 
WHERE lower(player_name) LIKE '%crosby%'
```

**Result**:
```
Name: Sidney#87 Crosby    ID: 8471675    Team: PIT   Type: 35+ Contract (Extension)
Name: Sidney#87 Crosby    ID: 8471675    Team: PIT   Type: Standard Contract (Extension)
Name: Sidney#87 Crosby    ID: 8471675    Team: PIT   Type: Standard Contract (Extension)
Name: Sidney#87 Crosby    ID: 8471675    Team: PIT   Type: Entry-Level Contract
```

---

## 🚀 Usage

### Command Line:
```bash
# Scrape any player from CapWages
python scripts/ingest/scrape_player_contract.py [player-slug]

# Examples
python scripts/ingest/scrape_player_contract.py sidney-crosby
python scripts/ingest/scrape_player_contract.py connor-mcdavid
python scripts/ingest/scrape_player_contract.py auston-matthews
```

### Output:
```
SUCCESS: Contract data scraped and exported

Player: Sidney#87 Crosby
NHL Player ID: 8471675
Official Name: Sidney Crosby
Contracts: 4
Contract Details: 22

CSV Files:
  contracts: data/contracts/crosby_8471675_contracts_20251016_161342.csv
  contract_details: data/contracts/crosby_8471675_contract_details_20251016_161342.csv
  summary: data/contracts/crosby_8471675_summary_20251016_161342.csv
```

---

## 🔧 Key Components

### 1. Player Mapper (`backend/bot/player_mapper.py`)
- `PlayerMapper` class: Manages roster loading and name matching
- `map_player_name_to_id()`: Convert CapWages name to NHL player ID
- `get_player_info()`: Get complete player data

### 2. Contract Scraper (`backend/bot/scrapers.py`)
- `scrape_capwages_player_profile()`: Extract contract data from CapWages
- Handles all contract types and financial details
- Extracts metadata (GM, dates, values)

### 3. Contract Exporter (`backend/bot/contract_exporter.py`)
- `export_contract_data_to_csv()`: Generate CSV files with clean naming
- `export_to_database_and_csv()`: Full pipeline (scrape → map → store → export)
- Automatic player ID enrichment

### 4. Database Functions (`backend/bot/db.py`)
- `insert_player_contract()`: Store contracts with player_id
- `insert_contract_detail()`: Store year-by-year details
- Deduplication logic

---

## 🎯 Verification - Sidney Crosby Test

### Input:
```
CapWages Name: "Sidney#87 Crosby"
URL: https://capwages.com/players/sidney-crosby
```

### Mapping Result:
```
NHL Player ID: 8471675
Official Name: Sidney Crosby
Team: PIT (Pittsburgh Penguins)
Position: C
Number: #87
```

### Data Extracted:
- ✅ 4 contracts (Entry-Level, 2 Extensions, 35+ Contract)
- ✅ 22 year-by-year contract details
- ✅ All financial data including minors salary
- ✅ Player ID correctly mapped and stored

### Files Generated:
```
crosby_8471675_contracts_20251016_161342.csv
crosby_8471675_contract_details_20251016_161342.csv
crosby_8471675_summary_20251016_161342.csv
```

---

## 📝 Technical Notes

### Name Normalization:
- Removes jersey numbers (#87)
- Handles special characters and punctuation
- Lowercase conversion
- Multiple format support

### Player ID Storage:
- Stored as VARCHAR in database
- Converted to string before insertion
- Included in all contract records

### Error Handling:
- Graceful fallback if player not found in roster
- Logs warnings for unmapped players
- Continues scraping even if mapping fails

---

## 🎉 Implementation Status: COMPLETE

All requirements have been successfully implemented:
- ✅ Contract-only scraping (no player stats)
- ✅ Player name to NHL ID mapping
- ✅ Clean CSV filenames (lastname_playerid format)
- ✅ No jersey numbers in filenames
- ✅ All contract data captured (including minors salary)
- ✅ Database storage with player IDs
- ✅ Comprehensive CSV export

**System is production-ready for building NHL contract database!**

