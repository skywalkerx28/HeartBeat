# Contract Terminal Implementation

## Overview
A trading platform-inspired financial terminal for managing and visualizing NHL contract situations. Designed with military/Palantir aesthetics for hockey operations staff.

## Page Location
**URL:** `/contracts`
**File:** `frontend/app/contracts/page.tsx`

## Layout Structure

### Terminal Header (Fixed)
- **Left:** Organization branding (Montreal Canadiens - Contract Terminal)
- **Center:** Key metrics dashboard
  - Cap Space
  - NHL Roster count (X/23)
  - Cap Utilization percentage
- **Right:** Live clock and sync status

### Three-Column Grid Layout

#### LEFT COLUMN (300px): AHL/Minors Roster
- **Header:** AHL Roster with player count
- **Content:** Scrollable list of AHL contract players
- **Features:**
  - Compact player cards
  - Cap hit display
  - Years remaining indicator
  - Position and age metadata

#### CENTER COLUMN (Flexible): Main Terminal Display
- **Top Section:** Contract Timeline Visualization
  - Multi-year cap commitment projection (2025-2030)
  - Bar chart showing cap hit by season
  - Player count per season
  - Cap ceiling reference line
  - Interactive hover tooltips
  
- **Bottom Section (280px):** Two-panel grid
  - **Left Panel:** Top Prospects List
    - Draft year, position, age
    - Current league
    - Quick reference for pipeline talent
  
  - **Right Panel:** Live Transaction Feed
    - Real-time activity updates
    - Transaction types: trades, signings, recalls, injuries
    - Timestamp formatting (minutes/hours/days ago)
    - Auto-refresh every 60 seconds

#### RIGHT COLUMN (300px): NHL Roster
- **Header:** NHL Roster with capacity indicator (X/23)
- **Content:** Scrollable list of NHL roster contracts
- **Features:**
  - Player links to profile pages
  - Cap hit per player
  - Contract years remaining (color-coded)
  - Position and age

## Components Created

### 1. RosterContractList.tsx
**Location:** `frontend/components/contracts/RosterContractList.tsx`

Reusable contract list component for displaying player contracts in a compact, terminal-style format.

**Props:**
- `contracts`: Array of player contract data
- `compact`: Boolean for minimal display mode

**Features:**
- Color-coded contract status (years remaining)
  - Red: 1 year or less
  - Yellow: 2 years
  - White: 3+ years
- Formatted currency display
- Player profile links
- Hover states for interaction

### 2. ContractTimeline.tsx
**Location:** `frontend/components/contracts/ContractTimeline.tsx`

Central visualization showing multi-year cap commitment projections.

**Props:**
- `contracts`: Player contract array
- `capCeiling`: NHL salary cap ceiling
- `totalCapHit`: Current cap hit total

**Features:**
- 6-year projection (2025-2030)
- Animated bar chart with Framer Motion
- Cap ceiling reference line
- Hover tooltips with detailed breakdowns
- Percentage utilization calculations
- Player count per season

### 3. ProspectsList.tsx
**Location:** `frontend/components/contracts/ProspectsList.tsx`

Display of top organizational prospects and pipeline talent.

**Props:**
- `teamAbbrev`: Team abbreviation for API queries

**Features:**
- Top 5 prospects display
- Draft year, position, age metadata
- Current league assignment
- API integration with fallback to mock data
- Clean, minimal design

### 4. TransactionFeed.tsx
**Location:** `frontend/components/contracts/TransactionFeed.tsx`

Live activity feed showing recent NHL transactions.

**Props:**
- `teamAbbrev`: Team abbreviation for filtering

**Features:**
- Real-time transaction updates
- Auto-refresh (60-second intervals)
- Transaction type icons
  - Trades: Arrow exchange
  - Signings: Plus circle
  - Recalls: Plus circle
  - Injuries: Bell alert
- Smart timestamp formatting
- Color-coded by transaction type
- Animated entry/exit with Framer Motion

## API Integration

### Contract Data
- **Endpoint:** `GET /api/v1/market/contracts/team/{team_abbrev}`
- **Client:** `getTeamContracts()` from `lib/marketApi`
- **Data:** Player contracts with cap hits, years remaining, roster status

### Cap Summary
- **Endpoint:** `GET /api/v1/market/cap/team/{team_abbrev}`
- **Client:** `getTeamCapSummary()` from `lib/marketApi`
- **Data:** Cap ceiling, commitments, projections

### Prospects
- **Endpoint:** `GET /api/v1/nhl/prospects/{team_abbrev}`
- **Data:** Organizational prospect pool

### Transactions
- **Endpoint:** `GET /api/v1/nhl/transactions/{team_abbrev}?limit=10`
- **Data:** Recent team transactions (trades, signings, moves)

## Design Principles

### Color Scheme
- **Background:** Pure black (bg-gray-950)
- **Accents:** Red (#EF4444) for active indicators
- **Text:** White primary, gray-400/500 secondary, red-400 for warnings
- **Glass Morphism:** backdrop-blur-xl with black/40 backgrounds
- **Borders:** border-white/5 and border-white/10 for subtle separation

### Typography
- **Font:** font-military-display for all UI elements
- **Sizing:** Compact (text-xs to text-sm for most UI)
- **Spacing:** tracking-wider/widest for uppercase text
- **Case:** UPPERCASE for headers and tactical terms

### Interactive Elements
- **Hover:** Subtle scale transforms, bg-white/5 transitions
- **Active:** Pulsing red dots with ping animation
- **Cards:** Glass backgrounds with backdrop-blur-xl
- **Transitions:** duration-300 for smooth interactions

### Animations
- **Page Entry:** Framer Motion with staggered delays
- **Bar Charts:** Height animations with spring physics
- **List Items:** Fade-in with x-translation
- **Feed Updates:** AnimatePresence for enter/exit

## Technical Features

### State Management
- Real-time clock updates (1-second intervals)
- Contract data fetching and transformation
- Roster separation (NHL vs AHL)
- Cap space calculations
- Transaction auto-refresh

### Data Transformation
- API contracts → UI contract format
- Roster status filtering (NHL, IR, AHL, Minor)
- Currency formatting ($X.XXM format)
- Timestamp humanization (Xm/Xh/Xd ago)

### Performance
- Memoized calculations (useMemo for expensive computations)
- Efficient filtering and mapping
- Lazy data loading
- Conditional rendering

## Usage

Access the Contract Terminal at `/contracts` in the HeartBeat application.

The page provides a comprehensive financial overview suitable for:
- General Managers
- Assistant GMs
- Cap management staff
- Hockey operations personnel
- Scouting departments

## Future Enhancements

Potential additions:
1. Team selector dropdown (currently fixed to MTL)
2. Contract comparison tools
3. Trade simulator with cap implications
4. Export functionality for reports
5. Historical contract performance tracking
6. Contract alert notifications (expirations, arbitration dates)
7. Multi-team cap comparison view
8. Integration with player performance metrics

