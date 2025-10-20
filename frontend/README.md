# HeartBeat Engine - Next.js Frontend

**Stanley - Montreal Canadiens Advanced Analytics Assistant**  
State-of-the-art hockey analytics interface built with Next.js, TypeScript, and Tailwind UI.

## 🏒 Project Structure

```
frontend/
├── components/
│   ├── tailwind-ui/           # Your premium Tailwind UI components
│   │   ├── analytics/         # Dashboard cards, KPI displays, stat blocks
│   │   ├── data-display/      # Tables, lists, comparison grids
│   │   ├── charts/           # Chart containers, legend components
│   │   ├── navigation/       # Tabs, breadcrumbs, sidebar navigation
│   │   ├── forms/           # Search bars, filters, input components
│   │   └── layout/          # Page layouts, grid systems, containers
│   └── hockey-specific/      # Custom hockey analytics components
│       ├── PlayerCard.tsx    # Player performance displays
│       ├── GameSummary.tsx   # Game analysis components
│       ├── StatComparison.tsx # Player/team comparisons
│       └── LineupBuilder.tsx # Interactive lineup tools
├── lib/
│   └── tailwind-ui-blocks/   # Complete pre-built sections
│       ├── dashboard-blocks/ # Full dashboard layouts
│       ├── analytics-blocks/ # Analytics page sections
│       └── table-blocks/    # Advanced table configurations
├── pages/                   # Next.js pages (App Router)
├── styles/                  # Global CSS and Tailwind config
├── types/                   # TypeScript type definitions
├── hooks/                   # Custom React hooks
└── utils/                   # Utility functions
```

## Component Categories

### Analytics Components (Priority 1)
- **Player Performance Cards**: Individual player stats with trends
- **Team Dashboard**: Overall team performance metrics
- **Game Analysis**: Detailed game breakdowns
- **Comparison Tables**: Side-by-side player/team comparisons

### Data Display Components (Priority 2)
- **Advanced Tables**: Sortable, filterable data grids
- **Stat Lists**: Clean statistical displays
- **Progress Indicators**: Performance trends and improvements

### Chart Components (Priority 3)
- **Chart Containers**: Wrappers for Plotly/D3 visualizations
- **Legend Systems**: Chart legend and annotation components
- **Interactive Controls**: Chart filtering and customization

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- Your Tailwind UI component library
- Access to HeartBeat Python backend

### Installation
```bash
cd frontend
npm create next-app@latest . --typescript --tailwind --app
npm install @tailwindui/react @headlessui/react @heroicons/react
```

### Development
```bash
npm run dev
```

## 📁 How to Add Your Tailwind UI Components

### Step 1: Download Components by Category
From your Tailwind UI dashboard, download components into these folders:

**Analytics Components:**
- Stat cards → `components/tailwind-ui/analytics/`
- KPI displays → `components/tailwind-ui/analytics/`
- Dashboard layouts → `lib/tailwind-ui-blocks/dashboard-blocks/`

**Data Display:**
- Tables → `components/tailwind-ui/data-display/`
- Lists → `components/tailwind-ui/data-display/`
- Grids → `components/tailwind-ui/data-display/`

**Navigation:**
- Tabs → `components/tailwind-ui/navigation/`
- Sidebars → `components/tailwind-ui/navigation/`
- Breadcrumbs → `components/tailwind-ui/navigation/`

### Step 2: Customize for Hockey Analytics
Each Tailwind UI component will be adapted for:
- Montreal Canadiens branding (#AF1E2D red, #192168 blue)
- Hockey-specific data structures
- TypeScript interfaces for player/team data
- Integration with Python backend APIs

### Step 3: Build Composite Components
Combine multiple Tailwind UI components to create:
- Complete dashboard pages
- Player profile layouts
- Game analysis interfaces
- Comparison tools

## Design System

### Montreal Canadiens Branding
```css
:root {
  --habs-red: #AF1E2D;
  --habs-blue: #192168;
  --habs-white: #FFFFFF;
  --ice-blue: #E8F4F8;
}
```

### Component Naming Convention
- `TailwindUI[ComponentName]` - Original Tailwind UI components
- `Hockey[ComponentName]` - Hockey-specific adaptations
- `[Role][ComponentName]` - Role-specific components (CoachDashboard, PlayerStats)

## 🔗 Backend Integration

### API Endpoints
```typescript
// Integration with your Python FastAPI backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://10.121.114.200:8000';

// Query Stanley (your orchestrator)
POST /api/v1/query
GET  /api/v1/player/{id}/stats
GET  /api/v1/team/analytics
GET  /api/v1/games/{id}/analysis
```

### Type Definitions
```typescript
// types/hockey.ts
interface PlayerStats {
  name: string;
  position: 'C' | 'LW' | 'RW' | 'D' | 'G';
  goals: number;
  assists: number;
  points: number;
  plus_minus: number;
  ice_time: string;
  // ... more hockey-specific fields
}
```

## 📊 Data Visualization Strategy

### Chart Integration
- **Plotly.js**: Advanced statistical charts
- **D3.js**: Custom hockey visualizations (rink diagrams, shot maps)
- **Chart.js**: Simple performance trends

### Interactive Elements
- Hover states for detailed stats
- Click-through navigation to detailed views
- Real-time updates from Python backend

## 🔒 Authentication & Roles

### User Roles
- **Coach**: Full tactical analysis and strategy tools
- **Player**: Personal performance and team context
- **Analyst**: Advanced metrics and league comparisons
- **Scout**: Player evaluation and opponent analysis
- **Staff**: High-level summaries and operational insights

### Role-Based UI
Components adapt based on user role:
```typescript
interface ComponentProps {
  userRole: 'coach' | 'player' | 'analyst' | 'scout' | 'staff';
  // Component shows/hides features based on role
}
```

---

**Next Steps:**
1. Add your Tailwind UI components to the appropriate directories
2. Install Next.js with TypeScript and Tailwind CSS
3. Begin adapting components for hockey analytics
4. Integrate with your existing Python backend via FastAPI

**The result will be a professional, state-of-the-art hockey analytics interface that leverages your premium UI components with your world-class Python analytics backend.**
