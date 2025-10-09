# HeartBeat Engine - Advanced Analytics Implementation

## Overview

A state-of-the-art analytics system for the Montreal Canadiens featuring advanced metrics computation, real-time NHL data integration, and a futuristic military-inspired UI.

## Architecture

### Backend Layer

#### 1. Advanced Metrics Computation (`orchestrator/tools/advanced_metrics.py`)

Pure Pandas-based computation engine for sophisticated hockey analytics:

**Player Form Index (PFI)**
- Recency-weighted composite score (0-100 scale)
- Components with weights:
  - EV Primary Points/60: 35%
  - Individual xG/60: 25%
  - Shot Assists/60: 15%
  - Controlled Entries/60: 15%
  - On-Ice xGF%: 10%
- Z-score normalization for fair comparison
- Trend indicators (up/down/stable)

**Team Momentum/Trends**
- Rolling xGF% (5 and 10 game windows)
- Special Teams Net (PP% + PK% vs league baseline)
- Pace metrics (CF/60 vs CA/60)
- PDO guardrails (shooting % + save %)
- Status indicators: hot/cold/sustainable

**Rival Threat Index (RTI)**
- Composite threat score for Atlantic Division rivals
- Components with weights:
  - Rolling xGF%: 30%
  - Schedule-adjusted points%: 20%
  - Special teams net: 20%
  - 5v5 goal share: 15%
  - Goalie workload/xGA: 10%
  - Rest/travel adjustment: 5%
- Threat levels: HIGH/MODERATE/LOW

**Fan Sentiment Proxy (FSP)**
- Statistical sentiment indicator (0-100)
- Derived from:
  - xGF% vs baseline
  - Special teams performance
  - PDO status
  - Star player PFI scores
- Sentiment bands: Very Positive, Positive, Neutral, Concerned, Very Concerned

#### 2. Data Client Extensions (`orchestrator/tools/parquet_data_client_v2.py`)

New methods for analytics data retrieval:
- `get_mtl_player_game_logs()` - Recent player performance
- `get_mtl_team_game_logs()` - Team game-by-game stats
- `get_division_teams_data()` - Atlantic Division team data

#### 3. API Endpoints (`backend/api/routes/analytics.py`)

**NHL API Proxies:**
- `GET /api/v1/analytics/nhl/standings` - Division standings
- `GET /api/v1/analytics/nhl/leaders` - League leaders (points/goals/assists)
- `GET /api/v1/analytics/nhl/scores` - Live scores (existing)
- `GET /api/v1/analytics/nhl/schedule` - Game schedule (existing)

**Advanced Analytics:**
- `GET /api/v1/analytics/mtl/advanced` - Comprehensive MTL analytics
  - Query params: `window` (default: 10), `season` (default: 2024-2025)
  - Returns: PFI, Team Trends, RTI, FSP in single payload
  - Optimized with caching (5-10 min TTL recommended)

### Frontend Layer

#### 1. API Client (`frontend/lib/api.ts`)

TypeScript methods added:
```typescript
getNHLStandings(date?: string): Promise<any>
getNHLLeaders(category: string, limit: number): Promise<any>
getMTLAdvancedAnalytics(window: number, season: string): Promise<any>
```

#### 2. Analytics Components

**DivisionWatch** (`DivisionWatch.tsx`)
- Atlantic Division standings table
- Highlights MTL position
- Shows W-L-OTL record, points, goal differential
- Real-time NHL API data

**LeagueLeaders** (`LeagueLeaders.tsx`)
- Top 5 league leaders in points/goals/assists
- Trophy icon for top performers
- Gold highlighting for podium positions

**PlayerFormLeaders** (`PlayerFormLeaders.tsx`)
- Top 5 MTL players by PFI score
- Color-coded scores: green (70+), white (55-69), yellow (45-54), red (<45)
- Trend arrows (up/down/stable)
- Detailed metric breakdowns (EVP/60, ixG/60, SA/60, ENT/60, xGF%)

**TeamTrendGauges** (`TeamTrendGauges.tsx`)
- Animated progress bars for:
  - xGF% (rolling window)
  - Special Teams Net
  - Pace (CF%)
  - PDO with status indicator
- Color-coded performance levels
- Shooting % and Save % breakdown

**RivalIndexTable** (`RivalIndexTable.tsx`)
- Top 5 Atlantic Division threats
- RTI scores with threat level badges
- Detailed metrics: xGF%, PTS%, ST NET, Recent Record
- Fire icon for high-threat teams (RTI >= 60)

**SentimentDial** (`SentimentDial.tsx`)
- Animated semicircle gauge (0-100)
- Color gradient: red → yellow → green
- Sentiment icons: smile/neutral/frown
- Impact factor breakdown grid
- Statistical proxy note

#### 3. Dashboard Integration (`MilitaryAnalyticsDashboard.tsx`)

**Layout Structure:**
1. Weekly Schedule Calendar (existing)
2. Division Watch + League Leaders
3. Player Form Index + Team Trends
4. Rival Threat Index + Fan Sentiment

**Data Fetching:**
- Parallel API calls on mount
- Error handling with graceful fallbacks
- Loading states for each component
- Auto-refresh capability (can add intervals)

## UI/UX Design

### Military-Inspired Design System

**Color Palette:**
- Primary: Pure black (`bg-gray-950`)
- Accent: Red (`#EF4444`, `red-600`)
- Text: White primary, gray-400/500 secondary
- Borders: `border-white/10` inactive, `border-white/30` active

**Visual Effects:**
- Glass morphism: `backdrop-blur-xl` with `bg-black/40`
- Subtle shadows: `shadow-white/5`
- Hover states: `scale: 1.02`, `border-white/30`
- Animations: Framer Motion with staggered delays

**Typography:**
- Font: `font-military-display` (defined in Tailwind config)
- Sizes: `text-xs` to `text-sm` for most UI
- Spacing: `tracking-wider/widest` for uppercase text
- Case: UPPERCASE for headers and labels

**Interactive Elements:**
- Animated progress bars
- Pulsing status indicators
- Color-coded metrics
- Trend arrows
- Threat level badges

## Data Flow

```
1. Frontend Component Mount
   ↓
2. Parallel API Calls
   - getNHLStandings()
   - getNHLLeaders()
   - getMTLAdvancedAnalytics()
   ↓
3. Backend Endpoints
   - Proxy NHL API (standings, leaders)
   - Compute advanced metrics (PFI, RTI, FSP)
   ↓
4. Data Processing
   - ParquetDataClientV2 loads data
   - advanced_metrics.py computes scores
   ↓
5. Response to Frontend
   - JSON with all analytics
   ↓
6. Component Rendering
   - Display with animations
   - Color coding
   - Interactive elements
```

## Performance Considerations

### Backend
- **Caching Strategy:**
  - NHL API data: 60-120 sec TTL
  - Advanced analytics: 5-10 min TTL
  - Use Redis or in-memory cache
  
- **Parquet Optimization:**
  - Column pruning (load only needed columns)
  - Row filtering at read time
  - Compression: ZSTD

### Frontend
- **Lazy Loading:**
  - Components load with skeletons
  - Staggered animations reduce jank
  
- **Data Refresh:**
  - Background refresh every 5-10 min
  - Visual indicator when stale
  
- **Responsive Design:**
  - Grid layout adapts to screen size
  - Mobile-optimized cards

## Testing Endpoints

### Quick Tests

1. **NHL Standings:**
```bash
curl http://localhost:8000/api/v1/analytics/nhl/standings
```

2. **League Leaders:**
```bash
curl http://localhost:8000/api/v1/analytics/nhl/leaders?category=points&limit=10
```

3. **MTL Advanced Analytics:**
```bash
curl http://localhost:8000/api/v1/analytics/mtl/advanced?window=10&season=2024-2025
```

## Next Steps

### Immediate Enhancements
1. Add refresh button for manual updates
2. Implement date selector for historical views
3. Add export functionality (CSV/PDF)
4. Create mobile-optimized layouts

### Future Features
1. **Trending Teams Endpoint**
   - Momentum indicators
   - Hot/cold streaks
   - Power rankings

2. **Interactive Filters**
   - Position filters (forwards/defense)
   - Time range selectors
   - Metric customization

3. **Comparison Views**
   - Player vs player
   - Team vs division average
   - Historical trends

4. **Real-time Updates**
   - WebSocket integration
   - Live game analytics
   - Push notifications

## File Structure

```
HeartBeat/
├── backend/
│   └── api/
│       └── routes/
│           └── analytics.py          (NHL + MTL endpoints)
├── orchestrator/
│   └── tools/
│       ├── advanced_metrics.py       (PFI, RTI, FSP, Trends)
│       └── parquet_data_client_v2.py (Data retrieval)
├── frontend/
│   ├── lib/
│   │   └── api.ts                    (API client)
│   └── components/
│       └── analytics/
│           ├── MilitaryAnalyticsDashboard.tsx
│           ├── DivisionWatch.tsx
│           ├── LeagueLeaders.tsx
│           ├── PlayerFormLeaders.tsx
│           ├── TeamTrendGauges.tsx
│           ├── RivalIndexTable.tsx
│           ├── SentimentDial.tsx
│           └── index.ts              (Exports)
```

## Deployment Notes

### Backend Requirements
- Python 3.9+
- FastAPI
- Pandas, NumPy
- httpx (for NHL API calls)
- Parquet support

### Frontend Requirements
- Next.js 14+
- React 18+
- Framer Motion
- Tailwind CSS
- Heroicons

### Environment Variables
```env
# Backend
HEARTBEAT_DATA_DIR=/path/to/data/processed

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Key Success Factors

1. **Data Quality**
   - Regularly updated Parquet files
   - Clean, normalized schemas
   - Proper error handling

2. **Performance**
   - Caching at multiple levels
   - Efficient Parquet queries
   - Lazy loading on frontend

3. **UX Excellence**
   - Consistent military aesthetic
   - Smooth animations
   - Clear data visualization
   - Responsive design

4. **Maintainability**
   - Clean separation of concerns
   - Typed interfaces
   - Comprehensive error handling
   - Documented metrics

## Support & Documentation

- Architecture: `/HEARTBEAT_ENGINE_ROADMAP.md`
- API Reference: `/orchestrator/API_REFERENCE.md`
- Frontend Design: `/frontend/README_MILITARY_UI.md`
- UI Integration: `/WEB_UI_INTEGRATION_COMPLETE.md`

---

Built with excellence for the Montreal Canadiens analytics platform.
Professional, avant-garde, state-of-the-art.

