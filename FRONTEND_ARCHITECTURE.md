# HeartBeat Engine - Frontend Architecture Guide

**Complete Next.js + TypeScript + Tailwind UI Implementation Strategy**

## 🏗️ Architecture Overview

```
HeartBeat Engine Architecture:

┌─────────────────────────────────────────────────────────────┐
│                    Next.js Frontend                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Tailwind UI │  │   Hockey    │  │    TypeScript       │  │
│  │ Components  │  │ Analytics   │  │    Interfaces       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    FastAPI Gateway                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Query     │  │    Auth     │  │      Cache          │  │
│  │  Routing    │  │  Middleware │  │     Layer           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│              Your Existing Python Backend                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Orchestrator│  │  Pinecone   │  │   Vertex AI         │  │
│  │  (Enhanced) │  │    RAG      │  │   Qwen3-Next-80B    │  │
│  │             │  │             │  │   Thinking Model    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Directory Structure Created

```
HeartBeat/
├── frontend/                          # NEW - Next.js Frontend
│   ├── components/
│   │   ├── tailwind-ui/              # YOUR TAILWIND UI COMPONENTS GO HERE
│   │   │   ├── analytics/            # Dashboard cards, KPI displays
│   │   │   ├── data-display/         # Tables, lists, grids
│   │   │   ├── charts/              # Chart containers, legends
│   │   │   ├── navigation/          # Tabs, sidebars, breadcrumbs
│   │   │   ├── forms/               # Search, filters, inputs
│   │   │   └── layout/              # Page layouts, containers
│   │   └── hockey-specific/          # Custom hockey components
│   ├── lib/tailwind-ui-blocks/       # YOUR COMPLETE UI BLOCKS GO HERE
│   │   ├── dashboard-blocks/         # Full dashboard sections
│   │   ├── analytics-blocks/         # Analytics page layouts
│   │   └── table-blocks/            # Advanced table configs
│   ├── pages/                       # Next.js pages
│   ├── styles/                      # Global CSS, Tailwind config
│   ├── types/                       # TypeScript definitions
│   ├── hooks/                       # Custom React hooks
│   └── utils/                       # Utility functions
├── backend/                          # ✨ NEW - FastAPI Gateway
│   ├── api/
│   │   ├── routes/                  # API endpoints
│   │   ├── models/                  # Pydantic models
│   │   └── services/                # Business logic wrappers
│   └── main.py                      # FastAPI app entry point
└── [existing structure unchanged]    # ✅ ALL YOUR CURRENT CODE STAYS
    ├── orchestrator/                # ✅ No changes
    ├── app/                         # ✅ Keep for internal use
    ├── data/                        # ✅ All data processing stays
    └── sagemaker_training_src/      # ✅ Training code unchanged
```

## What You Need to Do Next

### Step 1: Add Your Tailwind UI Components

**From your Tailwind UI dashboard, download these categories:**

#### Analytics Components → `frontend/components/tailwind-ui/analytics/`
- Stat cards
- KPI displays  
- Performance metrics
- Dashboard cards
- Progress indicators

#### Data Display → `frontend/components/tailwind-ui/data-display/`
- Advanced tables
- Data lists
- Comparison grids
- Statistical displays
- Filter panels

#### Charts → `frontend/components/tailwind-ui/charts/`
- Chart containers
- Legend components
- Tooltip systems
- Interactive controls

#### Navigation → `frontend/components/tailwind-ui/navigation/`
- Tab systems
- Sidebar navigation
- Breadcrumbs
- Menu components

#### Complete Blocks → `frontend/lib/tailwind-ui-blocks/`
- Dashboard page layouts
- Analytics page sections
- Table page templates
- Complete UI patterns

### Step 2: Install Next.js with TypeScript

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app
npm install @tailwindui/react @headlessui/react @heroicons/react
```

### Step 3: I'll Build Hockey-Specific Components

Once you add your Tailwind UI components, I'll create:

#### Hockey Analytics Components
```typescript
// frontend/components/hockey-specific/PlayerPerformanceCard.tsx
interface PlayerStats {
  name: string;
  position: 'C' | 'LW' | 'RW' | 'D' | 'G';
  goals: number;
  assists: number;
  points: number;
  ice_time: string;
  plus_minus: number;
}

// Using your Tailwind UI card as the foundation
export function PlayerPerformanceCard({ player }: { player: PlayerStats }) {
  // Adapts your premium Tailwind UI component for hockey data
}
```

#### Role-Based Dashboards
```typescript
// frontend/components/hockey-specific/CoachDashboard.tsx
export function CoachDashboard() {
  // Uses your Tailwind UI dashboard blocks
  // Customized for coaching needs
}

// frontend/components/hockey-specific/PlayerDashboard.tsx  
export function PlayerDashboard() {
  // Uses your Tailwind UI analytics blocks
  // Focused on personal performance
}
```

## 🚀 Development Workflow

### Phase 1: Component Foundation (Week 1)
1. **You**: Add Tailwind UI components to directories
2. **Me**: Set up Next.js project with TypeScript
3. **Me**: Create hockey-specific component adaptations
4. **Me**: Build FastAPI wrapper around your orchestrator

### Phase 2: Page Development (Week 2)
1. **Me**: Create role-based dashboard pages
2. **Me**: Build analytics and comparison interfaces
3. **Me**: Integrate with your Python backend via API
4. **Me**: Add authentication and role management

### Phase 3: Advanced Features (Week 3)
1. **Me**: Add real-time query streaming
2. **Me**: Implement advanced data visualizations
3. **Me**: Build interactive player/team comparison tools
4. **Me**: Performance optimization and caching

## Design System Integration

### Montreal Canadiens Branding
```css
/* Integrated into your Tailwind UI components */
:root {
  --habs-red: #AF1E2D;
  --habs-blue: #192168;  
  --habs-white: #FFFFFF;
  --ice-blue: #E8F4F8;
}
```

### Component Customization Strategy
1. **Use your Tailwind UI as foundation** - Professional, tested components
2. **Apply Montreal Canadiens colors** - Team branding integration
3. **Add hockey-specific data structures** - Player stats, game data, etc.
4. **Enhance with TypeScript** - Type safety for complex hockey data

## 📊 Data Flow

### Query Processing
```
User Input → Next.js Frontend → FastAPI Gateway → Your Orchestrator → Response
```

### Real-time Updates
```
Python Backend → WebSocket/SSE → Next.js Frontend → Component Update
```

## 🔒 Authentication Flow

### Role-Based Access
```typescript
// Types for your existing user roles
type UserRole = 'coach' | 'player' | 'analyst' | 'scout' | 'staff';

// Components adapt based on role
interface DashboardProps {
  userRole: UserRole;
  // Shows/hides features based on permissions
}
```

## Expected Results

### Professional Interface
- **Premium Tailwind UI components** adapted for hockey analytics
- **Montreal Canadiens branding** throughout the interface  
- **TypeScript type safety** for all hockey data structures
- **Responsive design** for desktop, tablet, and mobile

### Advanced Functionality
- **Real-time query processing** with your Stanley orchestrator
- **Interactive data visualizations** using your Parquet analytics
- **Role-based dashboards** tailored to each user type
- **Evidence-based responses** with clear source attribution

### Performance
- **Fast, modern interface** built on Next.js 14
- **Efficient data loading** with caching and streaming
- **Seamless integration** with your existing Python backend
- **Production-ready deployment** with Docker and cloud hosting

---

## Next Actions

1. **Download your Tailwind UI components** into the created directory structure
2. **Let me know when they're added** so I can begin the Next.js setup
3. **I'll build the complete frontend** using your premium components as the foundation

**The result will be a state-of-the-art hockey analytics interface that looks like a $500K+ enterprise application, powered by your world-class Python backend.**
