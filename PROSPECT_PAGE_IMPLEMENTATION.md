# Prospect Page Implementation Guide

## Overview

The Prospect page has been successfully implemented to replace the Draft page. This page provides comprehensive tracking for the Montreal Canadiens farm system (AHL) and prospect pool across various leagues (NCAA, CHL, Europe, etc.).

## Changes Made

### 1. File Structure
- **Created**: `/frontend/app/analytics/prospect/page.tsx` - New comprehensive prospect tracking page
- **Deleted**: `/frontend/app/analytics/draft/` - Old draft folder
- **Updated**: `/frontend/components/analytics/AnalyticsNavigation.tsx` - Changed navigation from "Draft" to "Prospect"

### 2. Navigation Update
The analytics navigation bar now displays:
- Market
- **Prospect** (updated from "Draft")
- Analytics
- League

## Page Features

### Main Components

#### 1. System Overview Cards
Three key metrics displayed at the top:
- **Total Prospects**: Count of all tracked prospects
- **AHL Roster**: Count of players in Laval Rocket (farm team)
- **Rising Stars**: Count of prospects trending upward

#### 2. Advanced Filtering System
Four-filter approach for data exploration:
- **League Filter**: ALL / AHL / CHL / NCAA / EUROPE / OTHER
- **Position Filter**: ALL / FORWARDS / DEFENSE / GOALIES
- **Status Filter**: ALL / RISING / STEADY / DECLINING
- **Search Bar**: Name or team search

#### 3. Prospect Roster Table
Comprehensive table displaying:
- Player name
- Position
- Age
- Draft information (Year, Round, Pick)
- Current team and league (with league icons)
- Statistics (Points, Goals, Assists)
- Plus/Minus rating
- Performance status (Rising/Steady/Declining with visual indicators)
- Potential rating (Elite/Top-6/Top-4/Middle-6/Bottom-6/Depth)

#### 4. Right Sidebar Panels

**HeartBeat Bot Status Panel** (Coming Soon)
- Displays planned automated monitoring features
- Will scan news sources, league websites, social media
- Planned features:
  - Auto-update player stats
  - Track injuries and transactions
  - Monitor performance trends
  - Alert on significant events

**League Breakdown Panel**
- Visual distribution of prospects across leagues
- Shows count and percentage for each league
- Animated progress bars

**Top Performers Panel**
- Lists top 5 prospects by points
- Shows league and point totals

**NHL Ready Panel**
- Lists prospects projected for NHL in current season
- Shows position and potential rating

## Design System Compliance

The page follows the established HeartBeat military/futuristic design system:

### Color Scheme
- Pure black background (bg-gray-950)
- Red accents (#EF4444) for active states and indicators
- White for primary text, gray-400/500 for secondary
- Transparency layers (white/5, white/10, red-600/10)

### Visual Style
- Glass morphism: backdrop-blur-xl with black/40 backgrounds
- Subtle borders: border-white/10 (inactive), border-white/30 (active)
- Technical grid background with cyan lines (rgba(6, 182, 212, 0.1))
- Radial gradient overlays
- Pulsing red dots for active indicators

### Typography
- font-military-display for all text
- Compact sizing (text-xs to text-sm)
- UPPERCASE for headers and labels
- tracking-wider/widest for uppercase text

### Animations
- Framer Motion for page transitions
- Staggered delays for sequential reveals (0.05 + index * 0.03)
- Pulse animations for status indicators
- Smooth hover transitions

## Data Structure

### Prospect Interface
```typescript
interface Prospect {
  playerId: string
  playerName: string
  position: string
  age: number
  draftYear: number
  draftRound: number
  draftPick: number
  currentLeague: string
  currentTeam: string
  gamesPlayed: number
  goals: number
  assists: number
  points: number
  plusMinus?: number
  status: 'rising' | 'steady' | 'declining'
  lastUpdate: string
  projectedNHLEta?: string
  potentialRating: 'Elite' | 'Top-6' | 'Top-4' | 'Middle-6' | 'Bottom-6' | 'Depth'
}
```

## Current Mock Data

The page currently displays mock data for 8 prospects:

### AHL Players (Laval Rocket)
1. **Lane Hutson** (D) - 2022 2nd round, Top-4 potential, Rising
2. **Owen Beck** (C) - 2022 2nd round, Middle-6 potential, Steady
3. **Joshua Roy** (LW) - 2021 5th round, Top-6 potential, Rising
4. **Logan Mailloux** (D) - 2021 1st round, Top-4 potential, Steady
5. **Xavier Simoneau** (C) - 2021 7th round, Depth potential, Steady

### NCAA Players
6. **Michael Hage** (C) - 2024 1st round (Michigan), Top-6 potential, Rising

### European Players
7. **Ivan Demidov** (RW) - 2024 1st round (SKA St. Petersburg), Elite potential, Rising

### CHL Players
8. **Quentin Miller** (D) - 2023 3rd round (Sudbury OHL), Top-4 potential, Rising

## Future Integration Points

### 1. Backend API Integration

Create API endpoints for prospect data:

```typescript
// Suggested API structure
/api/prospects/team/{teamId}
/api/prospects/player/{playerId}
/api/prospects/league/{leagueId}
/api/prospects/stats/update
```

### 2. HeartBeat Bot Integration

The page is designed to integrate with the future HeartBeat bot that will:
- Automatically scrape league websites for stats
- Monitor news sources for injuries/transactions
- Track social media for prospect updates
- Generate alerts for significant events
- Update prospect status trends

### 3. Real-time Data Sources

Potential data sources for automation:
- **AHL**: TheAHL.com API or web scraping
- **NCAA**: CollegeHockeyStats.net
- **CHL**: OHL/WHL/QMJHL official sites
- **KHL/European**: EliteProspects.com API
- **News**: Twitter API, hockey news aggregators
- **Draft info**: NHL.com draft database

### 4. Database Schema

Suggested tables:
```sql
prospects (
  player_id, name, position, age, birth_date,
  draft_year, draft_round, draft_pick, draft_team_id
)

prospect_stats (
  player_id, season, league, team, games_played,
  goals, assists, points, plus_minus, pim
)

prospect_status (
  player_id, status, potential_rating, nhl_eta,
  last_updated, trend_direction
)

prospect_updates (
  player_id, update_date, update_type, description,
  source_url
)
```

## Testing

To test the new page:

1. Start the frontend development server:
```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat/frontend
npm run dev
```

2. Navigate to: `http://localhost:3000/analytics/prospect`

3. Test filtering:
   - Change league filters (ALL, AHL, NCAA, etc.)
   - Change position filters (ALL, F, D, G)
   - Change status filters (ALL, rising, steady, declining)
   - Use search bar to find players by name

4. Verify design consistency:
   - Check that styling matches Market and Analytics pages
   - Verify military/futuristic theme is consistent
   - Test hover states on table rows
   - Confirm animations are smooth

## Next Steps

### Immediate Priorities
1. **Backend API Development**: Create prospect data endpoints
2. **Database Setup**: Design and implement prospect database schema
3. **Data Population**: Import current prospect data from EliteProspects or similar

### Medium-term Goals
1. **HeartBeat Bot Development**: Build automated prospect monitoring system
2. **Real-time Updates**: Implement WebSocket connections for live stat updates
3. **Historical Tracking**: Add performance charts and trend analysis
4. **Injury Tracking**: Integrate injury status and estimated return dates

### Long-term Vision
1. **AI-Powered Analysis**: Use LLM to generate prospect reports
2. **Comparison Tools**: Compare prospects across draft classes
3. **Projection Models**: Predict NHL success probability
4. **Video Integration**: Link to highlight clips from your video database

## File Locations

- Main page: `/frontend/app/analytics/prospect/page.tsx`
- Navigation: `/frontend/components/analytics/AnalyticsNavigation.tsx`
- Documentation: `/PROSPECT_PAGE_IMPLEMENTATION.md`

## Design Consistency

This implementation maintains perfect consistency with the existing HeartBeat design system:
- Uses BasePage component wrapper
- Includes AnalyticsNavigation
- Follows military UI color scheme (black, white, red)
- Uses font-military-display typography
- Implements glass morphism effects
- Contains technical grid backgrounds
- Features pulsing status indicators
- Employs Framer Motion animations

## Notes

- All text is professional (no emojis per project rules)
- Mobile-responsive grid layouts
- Optimized for performance with useMemo hooks
- TypeScript type safety throughout
- Clean separation of concerns
- Ready for backend integration

The page is production-ready from a UI perspective and awaits backend data integration and HeartBeat bot development for full functionality.

