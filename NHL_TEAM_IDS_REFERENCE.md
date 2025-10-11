# NHL Team IDs Reference

## Official NHL Team IDs for API Integration

Based on the official NHL franchise data, these are the correct team IDs to use when making NHL API calls:

### Eastern Conference

#### Atlantic Division
- **MTL** (Montréal Canadiens): `id: 8`
- **TOR** (Toronto Maple Leafs): `id: 10`
- **BOS** (Boston Bruins): `id: 6`
- **BUF** (Buffalo Sabres): `id: 7`
- **OTT** (Ottawa Senators): `id: 9`
- **DET** (Detroit Red Wings): `id: 17`
- **FLA** (Florida Panthers): `id: 13`
- **TBL** (Tampa Bay Lightning): `id: 14`

#### Metropolitan Division
- **NYR** (New York Rangers): `id: 3`
- **NYI** (New York Islanders): `id: 2`
- **PHI** (Philadelphia Flyers): `id: 4`
- **WSH** (Washington Capitals): `id: 15`
- **CAR** (Carolina Hurricanes): `id: 12`
- **NJD** (New Jersey Devils): `id: 1`
- **CBJ** (Columbus Blue Jackets): `id: 29`
- **PIT** (Pittsburgh Penguins): `id: 5`

### Western Conference

#### Central Division
- **COL** (Colorado Avalanche): `id: 21`
- **DAL** (Dallas Stars): `id: 25`
- **MIN** (Minnesota Wild): `id: 30`
- **NSH** (Nashville Predators): `id: 18`
- **STL** (St. Louis Blues): `id: 19`
- **WPG** (Winnipeg Jets): `id: 52`
- **CHI** (Chicago Blackhawks): `id: 16`
- **UTA** (Utah Hockey Club): `id: 59`

#### Pacific Division
- **VGK** (Vegas Golden Knights): `id: 54`
- **SEA** (Seattle Kraken): `id: 55`
- **LAK** (Los Angeles Kings): `id: 26`
- **SJS** (San Jose Sharks): `id: 28`
- **ANA** (Anaheim Ducks): `id: 24`
- **VAN** (Vancouver Canucks): `id: 23`
- **CGY** (Calgary Flames): `id: 20`
- **EDM** (Edmonton Oilers): `id: 22`

## Important Notes

### Team ID vs Franchise ID
- ✅ **USE**: `id` field for NHL API calls
- ❌ **DON'T USE**: `franchiseId` field

### Recent Changes
- **Arizona Coyotes** → **Utah Hockey Club** (`id: 59`)
  - Both `ARI` and `UTA` map to team ID 59
  - Team moved to Utah for 2024-25 season

### NHL API Integration
```typescript
// Correct usage in API calls
const teamId = 8  // MTL Canadiens
const apiUrl = `https://api-web.nhle.com/v1/roster/${teamId}/current`

// Logo URLs still use team abbreviation
const logoUrl = `https://assets.nhle.com/logos/nhl/svg/MTL_light.svg`
```

### Franchise History
The data includes historical franchises (inactive teams):
- Quebec Nordiques (now Colorado Avalanche)
- Hartford Whalers (now Carolina Hurricanes)  
- Atlanta Thrashers (now Winnipeg Jets)
- And many other historical teams

**For current NHL operations, only use the 32 active franchises listed above.**

## Implementation Status
✅ Updated in `frontend/lib/profileApi.ts`:
- `getTeamIdFromAbbrev()` function uses official NHL team IDs
- `getTeamNameFromAbbrev()` function includes all current teams
- `TEAM_INFO_MAP` updated with Utah Hockey Club

This ensures proper NHL API integration when the backend endpoints are implemented.
