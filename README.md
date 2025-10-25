# HeartBeat Engine

## Intelligent Enterprise Platform for NHL Operations

**HeartBeat Engine** implements a sophisticated three-layer intelligent platform architecture designed for comprehensive NHL operations and analytics. This enterprise-grade system transforms raw hockey data into actionable intelligence through a structured approach that mirrors modern data platforms like Palantir Foundry.

### Platform Architecture Overview

#### Foundation Layer: Unified Ontology and Data Lake (HeartBeat's "Foundry")
At the base of our platform is a unified data ontology that acts as HeartBeat's long-term memory – a dynamic "digital twin" of the NHL world. This foundation layer consolidates disparate sources (NHL API stats, contract databases, scouting info, etc.) into BigQuery tables and views, modeling hockey operations as interconnected digital objects with defined relationships.

**Key Capabilities:**
- **Data Integration**: Unified schema across all hockey data sources with BigQuery optimization
- **Ontology Schema**: Core object types (Players, Teams, Games, Contracts) with relationship mapping
- **Single Source of Truth**: Grounded AI responses in real-world data, eliminating hallucination
- **Real-time Synchronization**: Continuous data updates from NHL APIs and manual sources

#### Tool/Logic Layer: AI Orchestrator and Secure Actions (HeartBeat's "AIP Logic")
The intelligence layer implements an AI Orchestrator that functions like Palantir's AIP Logic – interpreting user requests and executing optimal sequences of tools and functions. This layer transforms natural language queries into structured analytical workflows.

**Key Capabilities:**
- **Conversational Analytics**: Complex queries like "How effective was Montreal's power play against Toronto in 3rd periods?"
- **Autonomous Tool Orchestration**: Multi-step planning with xG calculations, zone analysis, and matchup comparisons
- **Hybrid Intelligence**: Combines RAG contextual knowledge with real-time Parquet SQL queries
- **Enterprise Security**: Role-based access control with data scoping and audit trails

#### Presentation Layer: Context-Aware Global AI Interface
The top layer provides a seamless, context-aware AI interface that understands user intent, current page context, and analytical focus. This creates an intelligent assistant that enhances every interaction within the platform.

**Key Capabilities:**
- **Global Context Awareness**: AI understands current page, selected players, active filters, and visualization states
- **Intelligent Query Processing**: Natural language enhanced with situational awareness
- **Proactive Insights**: Automatic suggestions based on current analytical view
- **Multi-Modal Integration**: Unified experience across rink visualizations, charts, and data tables

Coaches, players, scouts, analysts, and other hockey professionals can ask natural-language questions (e.g., "Analyze power play efficiency trends across the Atlantic Division" or "What's the impact of pairing young defensemen with veterans on zone exits?" or "Show me all high-danger scoring chances from the playoffs") and receive dynamic, data-grounded responses: aggregated stats (e.g., xG differentials), interactive visualizations (e.g., shot heatmaps on NHL rinks), trend breakdowns, and prescriptive recommendations (e.g., "Target east-slot rushes—increases scoring probability by 18%").

## Key Differentiators

### Comprehensive NHL Coverage
- **League-Wide Intelligence**: Comprehensive analysis across all 32 NHL teams with team-specific tactical insights and strategic patterns.
- **Universal Hockey Metrics**: Advanced analytics optimized for all playing styles, from speed-focused systems to defensive structures.
- **Multi-Team Comparisons**: Cross-organizational analysis enabling benchmarking and competitive intelligence.

### Dynamic & Proactive Analysis
- **Retrieval-Augmented Generation (RAG)**: Uses LLM to interpret queries, retrieve relevant events, execute on-the-fly analysis.
- **No Pre-coded Queries**: Handles any natural language question without predefined templates.
- **Real-time Insights**: Generates tables, plots, and recommendations dynamically.

### Context-Aware AI Integration (Planned)
- **Global Assistant Access**: Persistent AI sidebar available throughout the entire web application experience.
- **Automatic Context Detection**: AI automatically understands current page context, player focus, team analysis, and data visualization state.
- **Intelligent Query Processing**: Natural language queries enhanced with situational awareness of user's current navigation and focus.
- **Contextual Suggestions**: Proactive insights and recommendations based on current analytical view or player profile being examined.

### Interactive Player Analysis
- **Event-Level Visualization**: Interactive NHL rink displays showing player actions with precise coordinate mapping.
- **Multi-Dimensional Filtering**: Filter events by zone, action type, shift sequences, and game situations.
- **Hover Tooltips**: Detailed action breakdowns with success rates, outcomes, and contextual information.

### Contract Intelligence Engine (In Development)
- **Player Trajectory Modeling**: Advanced analytics engine computing player performance trajectories using historical data patterns.
- **Contract Viability Assessment**: Real-time evaluation of contract proposals based on performance projections and market comparables.
- **Risk Analysis**: Predictive modeling for injury risk, performance decline, and career longevity factors. 

### Scalable Architecture
- **MVP Foundation**: Starts offline with extensive local tabular and visual data; evolves to real-time ingestion.
- **Extensible Design**: Ready for 2025-26 data, interactive visualizations, NHL API integrations (possibly).
- **Cloud-Ready**: Deployable on Hugging Face Spaces with offline fallback for sensitive data.

## Technical Architecture

### Three-Layer Implementation

#### Foundation Layer Implementation
- **BigQuery Data Lake**: Unified storage for all NHL data with optimized Parquet files
- **Ontology Schema**: Structured relationships between Players, Teams, Games, Contracts, and Events
- **Data Pipeline**: ETL processes ingesting from NHL APIs, contract databases, and manual sources
- **Real-time Synchronization**: Continuous updates maintaining data freshness and accuracy

#### Tool/Logic Layer Implementation
**Central Intelligence:** LangGraph-based agent orchestrator powered by **Qwen3-Next-80B Thinking** on Google Cloud Vertex AI

**Dual-Model Architecture:**
- **Primary Reasoning**: Qwen3-Next-80B Thinking (MoE, reasoning-first, function calling)
- **Vision Specialist**: Qwen3-VL (invoked on-demand for shot maps, formations, video frames)

**Processing Flow:**
```
User Query → Intent Analysis → Autonomous Tool Orchestration → Tool Execution → Synthesis → Response
```

**Node Architecture:**
- **Intent Node**: Query classification and parameter extraction with multi-step reasoning
- **Router Node**: Determines RAG vs Parquet vs hybrid vs vision analysis needs  
- **Vector Search**: Semantic retrieval from hockey knowledge chunks
- **Parquet SQL**: Real-time analytics queries on game/player data
- **Analytics Tools**: xG calculations, zone entry/exit stats, matchup comparisons
- **Vision Delegate**: Selectively invokes Qwen3-VL for visual analysis when needed
- **Visualization**: Dynamic heatmaps, charts, and statistical displays

### System Guards & Identity Management
- **User/Role Filters**: Identity-aware data scoping and permissions
- **Resource Guards**: Row/byte caps, query timeouts, retry logic
- **Caching Layer**: Intelligent caching for performance optimization
- **Security**: `resolve_current_user` with data access enforcement

### Hybrid Data Architecture
- **RAG System**: Hockey domain knowledge and contextual explanations
- **Live Analytics**: Real-time Parquet queries for current statistics
- **Tool Integration**: Seamless combination of historical and live data

### Google Cloud Vertex AI Integration
- **Model Hosting**: Vertex AI Model Garden (MaaS) for managed inference
- **Core Reasoning**: Qwen3-Next-80B Thinking with function calling and structured outputs
- **Vision Processing**: Qwen3-VL invoked selectively for visual analysis tasks
- **Quota Management**: Cloud-native controls for cost optimization
- **Scalable Inference**: Auto-scaling endpoints for production workloads

### Tech Stack
- **Orchestration**: LangGraph agent workflows with custom node architecture
- **Core Reasoning Model**: Qwen3-Next-80B Thinking (80B MoE parameters, reasoning-first design)
- **Vision Model**: Qwen3-VL (on-demand invocation for visual analysis)
- **AI Platform**: Google Cloud Vertex AI Model Garden for managed serving
- **Vector Database**: Pinecone with hybrid semantic + keyword search
- **Analytics Backend**: Python 3.13, pandas, pyarrow for Parquet optimization
- **Video Processing**: FFmpeg integration with enhanced video analysis capabilities
- **Visualization**: Dynamic matplotlib/seaborn charts with real-time generation
- **Frontend**: React + TypeScript interface with Tailwind CSS
- **Backend**: FastAPI services with async processing capabilities
- **Database**: GCP Cloud SQL PostgreSQL with connection pooling and indexing
- **Task Scheduling**: Google Cloud Run Jobs for automated content collection
- **Security**: Google Cloud IAM, Secret Manager, and role-based access control
- **Infrastructure**: Google Cloud Platform with Cloud Run, Cloud SQL, and Cloud Logging

## Interactive Features

### Real-Time Rink Visualization
- **Precision Event Mapping**: Every player action plotted on accurate NHL rink coordinates
- **Dynamic Filtering System**: Filter by zones (DZ/NZ/OZ), action types, and individual shift sequences
- **Success Rate Analytics**: Real-time calculation of action success rates by zone with visual feedback
- **Hover Intelligence**: Detailed tooltips showing action type, result, zone, period, and shift context
- **Military UI Design**: Professional interface with glass morphism effects and tactical styling

### Advanced Player Profiles
- **Game Log Analysis**: Expandable game-by-game breakdowns with advanced metrics
- **Shift-Level Granularity**: Filter events down to specific shift sequences within games
- **Multi-Dimensional Analytics**: Cross-reference opponent matchups, line combinations, and deployment patterns
- **Interactive Dropdowns**: Season selection with dynamic data loading and responsive design

## Data Overview

- **Source**: NHL play-by-play CSV files and archive game footage (from multiple seasons across all teams).
- **Volume**: ~Millions granular events and thousands of game footage across the league.
- **Key Fields**: xCoord, yCoord, type, playerReferenceId, expectedGoalsOnNet, period, gameTime.
- **Processing**: Unified schema, derived features (shot_distance, possession_duration), league-wide event flagging.

## Development Status

### Completed Infrastructure
- **Model Architecture**: Dual-model system with Qwen3-Next-80B Thinking (reasoning) and Qwen3-VL (vision)
- **Cloud Platform**: Google Cloud Vertex AI integration for managed inference and hosting
- **Qwen3 Orchestrator**: Autonomous agent orchestrator with full tool visibility and continuous reasoning
- **Web UI Integration**: Complete Next.js + TypeScript frontend with military UI design and chat interface
- **Data Pipeline**: Comprehensive ETL pipeline with Parquet optimization and RAG chunking
- **Tool Framework**: Extensive tool arsenal for NHL data, rosters, live games, and analytics
- **API Infrastructure**: FastAPI backend with multiple routes (query, analytics, clips, auth)
- **Deployment**: Multiple Vertex AI endpoints deployed (working, corrected, Hugging Face)

### Current Capabilities
- **LangGraph Orchestrator**: Agent-based workflow with intent analysis and routing
- **Hybrid Intelligence**: RAG + real-time Parquet SQL integration
- **Interactive Rink Visualization**: Real-time NHL rink displays with event plotting, filtering, and hover analytics
- **Player Profile System**: Comprehensive player pages with game logs, advanced metrics, and interactive visualizations
- **Multi-Dimensional Filtering**: Zone-based, action-based, and shift-based event filtering with success rate analytics
- **Video Analytics**: Video clip retrieval and analysis capabilities
- **Multi-modal Interface**: React + TypeScript chat interface with analytics panels
- **Enterprise Security**: Role-based access control and data scoping

### Phase 3: Advanced LangGraph Orchestrator (In Progress)

**Goal:** Implement a sophisticated LangGraph-based agent orchestrator powered by Qwen3-Next-80B Thinking on Vertex AI, seamlessly combining hybrid RAG + real-time analytics with on-demand vision processing, enabling dynamic multimodal hockey analysis with enterprise-grade security and performance.

#### Architecture Implementation:
- **LangGraph Agent Core:** LangGraph orchestrator powered by Qwen3-Next-80B Thinking for advanced reasoning, multi-step planning, and autonomous tool orchestration with function calling
- **Dual-Model Strategy:** Qwen3-Next-80B Thinking handles all reasoning/planning; Qwen3-VL invoked selectively for visual analysis
- **Node-based Workflow:** Intent → Router → Vector Search → Parquet SQL → Analytics Tools → [Vision Delegate] → Visualization → Synthesis
- **Identity-Aware System:** User role enforcement with data scoping and permissions
- **Hybrid Intelligence:** RAG chunks for hockey context + live Parquet queries + on-demand video analysis
- **Tool Orchestration:** xG calculations, zone entry/exit analysis, matchup comparisons, dynamic visualizations
- **Vertex AI Integration:** Managed serving via Google Cloud Model Garden with quota controls and cost optimization

#### Core Objectives:
- **Conversational Analytics:** Enable complex queries like "How effective was Montreal's power play against Toronto in 3rd periods?" with multi-step tool usage
- **Smart Routing:** Intelligent decision-making between RAG knowledge, live data, or hybrid approaches based on query intent
- **Real-time Tool Integration:** Dynamic analytics capabilities with timeout handling, caching, and error recovery
- **Contextual Synthesis:** Evidence-based responses combining historical patterns with current performance data
- **Global Context Awareness:** AI assistant understands current page context, active filters, selected players, and visualization states automatically
- **Role-based Access:** User-specific data filtering and permission enforcement for coaches, players, analysts, and staff

#### Technical Implementation Strategy:

##### 3.1 Dual-Model Architecture on Vertex AI
**LangGraph Orchestrator with Vertex AI:**
```
LangGraph Orchestrator (Vertex AI)
├── Primary Reasoning Engine
│   ├── Qwen3-Next-80B Thinking
│   ├── Multi-step Planning & Decomposition
│   ├── Function Calling (Strict JSON)
│   └── Tool Orchestration
├── Core LangGraph Nodes
│   ├── Intent Analysis Node
│   ├── Router Node
│   ├── Tool Execution Nodes
│   ├── Vision Delegate Node (conditional)
│   └── Synthesis Node
└── Vision Specialist (On-Demand)
    └── Qwen3-VL for Visual Analysis
```

**Integration Approach:**
- **Reasoning-First Design**: Qwen3-Next-80B Thinking handles all planning, reasoning, and tool orchestration for hockey queries
- **MoE Efficiency**: Mixture-of-Experts architecture activates only subset of 80B parameters per token, controlling costs
- **Function Calling**: Strict JSON schemas for tool arguments prevent hallucination and enable deterministic execution
- **Vision Delegation**: Qwen3-VL invoked only when visual analysis required (shot maps, formations, video frames)
- **Vertex AI Hosting**: Managed serving via Google Cloud Model Garden with quota controls and auto-scaling
- **Cost Optimization**: Text-only queries stay on Thinking model; vision overhead only when necessary

**Dual-Model Capabilities:**
- **Autonomous Tool Orchestration**: Plans optimal tool chains (Pinecone → Parquet → Analytics → Visualization)
- **Contextual Reasoning**: Advanced reasoning over hockey domain knowledge with multi-step decomposition
- **Selective Vision Processing**: Only invokes vision model when query requires visual analysis
- **Enterprise Security**: Role-based permissions with data access controls and audit trails
- **Cloud Convenience**: Managed endpoints, quota management, and scalable infrastructure

##### 3.3 Hybrid RAG + Real-Time Query System
```
Query Processing Flow:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Query    │ -> │ Intent Analysis │ -> │  Hybrid         │ -> │  LLM with Tools │
│  "Montreal's    │    │  (Qwen3 Model)  │    │  Orchestration   │    │ Synthesis       │
│   shots  vs     │    │                 │    │                 │    │                 │
│   Toronto in    │    │  - Query type   │    │  - RAG chunks   │    │  - Hockey cntxt │
│   3rd periods"  │    │  - Complexity   │    │    (context)    │    │  - SQL tools    │
└─────────────────┘    │  - Data needs   │    │  - Parquet SQL  │    │  - Visualization│
                       │  - Filters      │    │    (live data)  │    │  - Calculation  │
                       └─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Low-Level Components:**
- **Query Classifier:** BERT-based model to categorize queries (basic stats, advanced analytics, trend analysis, predictive)
- **Hybrid Data Router:** Intelligent routing between RAG chunks (hockey context) and Parquet queries (live calculations)
- **Tool Provider:** Equips LLM with analytical tools for dynamic query processing and real-time calculations
- **Context Builder:** Combines hockey domain knowledge with live data for comprehensive, accurate responses

##### 3.4 RAG Chain Architecture
```
RAG Pipeline:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Query         │ -> │  Retrieval      │ -> │  Context        │ -> │  Generation     │
│   Processing    │    │   (Pinecone)    │    │  Enhancement    │    │  (Fine-tuned    │
│                 │    │                 │    │                 │    │  LLM)           │
│  - Tokenization │    │  - Semantic     │    │  - Multi-source │    │                 │
│  - Embedding    │    │    search       │    │    synthesis    │    │  - Prompt eng.  │
│  - Similarity   │    │  - Hybrid       │    │  - Fact check   │    │  - Structured   │
│    matching     │    │    filtering    │    │  - Relevance    │    │    output       │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Vector Database Implementation:**
- **Embedding Model:** Sentence-BERT optimized for sports analytics domain
- **Index Strategy:** HNSW (Hierarchical Navigable Small World) for sub-second retrieval
- **Hybrid Search:** Combines semantic similarity with keyword-based filtering
- **Metadata Filtering:** Game date, opponent, player, situation-specific retrieval

##### 3.5 Dynamic Analysis Tools for LLM

**LLM Tool Arsenal:**
```python
class HabsAnalysisTools:
    def query_parquet_data(self, sql_query: str, context: dict):
        """Execute real-time SQL queries on parquet files with hockey context"""
        # Dynamic filtering, aggregation, and calculation capabilities
        
    def calculate_advanced_metrics(self, data: pd.DataFrame, metric_type: str):
        """Calculate complex hockey metrics on-demand"""
        # Corsi, expected goals, zone entry success, possession metrics
        
    def compare_performance(self, filters: dict, comparison_type: str):
        """Dynamic performance comparisons across any dimensions"""
        # Player vs player, team vs team, situation vs situation
        
    def generate_visualizations(self, data: pd.DataFrame, chart_type: str):
        """Create dynamic charts and heatmaps from query results"""
        # Shot maps, performance trends, comparative analysis
```

**Dynamic Tool Categories:**
- **Data Query Tools:** Real-time parquet filtering, aggregation, and calculation
- **Hockey Analytics Tools:** Advanced metric calculation (Corsi, xG, zone analysis)
- **Comparison Tools:** Multi-dimensional performance analysis and benchmarking
- **Visualization Tools:** Dynamic chart and heatmap generation from live data
- **Context Integration Tools:** Combine RAG hockey knowledge with real-time calculations

**Critical Capability:** LLM can answer ANY query combination by dynamically using tools rather than relying on pre-computed static responses

##### 3.6 Structured Output Generation

**Dynamic Visualization Engine:**
```python
class HabsVisualizer:
    def create_shot_heatmap(self, shot_data, rink_template):
        """Generate interactive shot heatmaps with player tracking"""

    def generate_performance_charts(self, metrics_data):
        """Create comparative performance visualizations"""

    def build_statistical_tables(self, analysis_results):
        """Format complex statistical data into readable tables"""
```

**Response Formatting Pipeline:**
- **Template System:** Context-aware response templates for different query types
- **Data Formatting:** Automatic conversion of raw statistics into narrative form
- **Visual Integration:** Seamless embedding of charts and heatmaps in responses
- **Source Attribution:** Clear indication of data sources and calculation methods

##### 3.7 Fine-Tuning & Optimization

**Domain-Specific Training:**
- **Custom Dataset:** 2,198 QA pairs focused on hockey analytics terminology
- **Montreal Context:** Fine-tuning on Canadiens-specific language and references
- **Statistical Literacy:** Training on proper interpretation of advanced metrics
- **Conversational Flow:** Optimization for multi-turn analytical conversations
- **Vertex AI Training:** Enterprise-grade model training on Google Cloud infrastructure

**Performance Optimization:**
- **Query Caching:** Intelligent caching of frequent queries and calculations
- **Batch Processing:** Optimized batch operations for complex multi-game analysis
- **Memory Management:** Efficient handling of large datasets during analysis
- **Response Time Targets:** <2 seconds for basic queries, <5 seconds for complex analysis

##### 3.8 Context-Aware Global AI Architecture (Planned)

**Global Context Management System:**
```
Context Pipeline:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Page State    │ -> │  Context        │ -> │  AI Query       │ -> │  Enhanced       │
│   Detection     │    │  Enrichment     │    │  Processing     │    │  Response       │
│                 │    │                 │    │                 │    │  Generation     │
│  - Current page │    │  - Player focus │    │  - Context-aware│    │  - Contextual   │
│  - Active data  │    │  - Team scope   │    │    routing      │    │    insights     │
│  - Filter state │    │  - Time range   │    │  - Smart tools  │    │  - Relevant     │
│  - User session │    │  - Data context │    │  - Auto-filters │    │    suggestions │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Technical Components:**
- **State Tracker:** React context provider monitoring current page, selected players, active filters, and visualization states
- **Context Injector:** Automatic context enhancement for AI queries based on user's current focus and navigation
- **Sidebar Integration:** Persistent AI interface with dynamic context display and query suggestions
- **Smart Routing:** Context-aware query processing that leverages current page data and user selections
- **Proactive Intelligence:** Automatic insights and suggestions based on current analytical view

##### 3.9 Testing & Validation Framework

**Automated Testing Suite:**
- **Unit Tests:** Individual component functionality (retrieval accuracy, calculation precision)
- **Integration Tests:** End-to-end query processing and response generation
- **Performance Benchmarks:** Query response times, retrieval accuracy metrics
- **Accuracy Validation:** Statistical calculation verification against known baselines

**Human Evaluation Protocol:**
- **Expert Review:** Validation by hockey analysts and coaches
- **User Testing:** Real-world query testing with target user groups
- **Iterative Improvement:** Continuous refinement based on user feedback
- **Edge Case Handling:** Robust processing of unusual or complex queries

#### Success Metrics:
- **Query Accuracy:** >90% statistically correct responses
- **Response Time:** <3 seconds average for complex queries
- **User Satisfaction:** >4.5/5 rating on response quality and relevance
- **Retrieval Precision:** >85% relevant information retrieval
- **Contextual Understanding:** >80% accurate interpretation of analytical intent

### Next Development Phases

#### Phase 4: Context-Aware Global AI Integration
- [ ] **Global Sidebar Integration**: Persistent AI assistant accessible from any page in the web application
- [ ] **Dynamic Context Injection**: Automatic context awareness based on current page, player, team, or data being viewed
- [ ] **Seamless Query Processing**: Natural language queries with full understanding of user's current focus and navigation state
- [ ] **Page-Specific Intelligence**: Contextual suggestions and insights relevant to current analytics view or player profile
- [ ] **Multi-Modal Context**: Integration with rink visualizations, charts, and data tables for comprehensive situational awareness

#### Phase 5: Enhanced Analytics & Testing
- [ ] **Advanced Visualizations**: Interactive heatmaps and performance charts
- [ ] **Video Integration**: Seamless video clip embedding in responses
- [ ] **Performance Optimization**: Query caching and response time improvements
- [ ] **Comprehensive Testing**: Unit tests, integration tests, and user validation

#### Phase 6: Contract Intelligence Engine
- [ ] **Player Performance Trajectory Modeling**: Historical pattern analysis for career development prediction
- [ ] **Contract Evaluation Algorithm**: Real-time assessment of contract proposals using performance projections
- [ ] **Market Analysis Integration**: Comparable player analysis and salary cap optimization
- [ ] **Risk Assessment Models**: Injury prediction, performance decline analysis, and career longevity factors

#### Phase 7: Production Deployment
- [ ] **Containerization**: Docker deployment with optimized environments
- [ ] **Cloud Deployment**: Google Cloud Run services and Vertex AI endpoints
- [ ] **Monitoring**: Cloud Logging, Cloud Monitoring, and performance metrics
- [ ] **User Training**: Documentation and onboarding materials

## Installation & Setup

### Prerequisites
- Python 3.13+
- Git
- 8GB+ RAM (for ML model processing)
- Google Cloud SDK configured (for Vertex AI and Cloud Run integration)
- Docker (for containerized deployments)

### Local Development Setup
```bash
# Clone repository
git clone https://github.com/skywalkerx28/HeartBeat.git
cd HeartBeat

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export OPENAI_API_KEY="your-openai-key"  # For fallback model
gcloud auth application-default login

# Run data preparation (if needed)
python scripts/etl_pipeline.py

# Start development servers
# Frontend (React/TypeScript)
cd frontend && npm run dev

# Backend (FastAPI)
cd backend && python main.py
```

### Project Structure
```
HeartBeat/
├── backend/                      # FastAPI backend services with Cloud Run deployment
├── frontend/                     # Next.js React frontend with Vercel deployment
├── orchestrator/                 # LangGraph agent orchestration on Vertex AI
├── bot/                          # Automated content collection system
├── ontology/                     # Unified data schema and BigQuery integration
├── data/                         # Data processing and storage
│   ├── processed/                # Parquet-optimized analytics data
│   │   └── llm_model/
│   │       └── training/         # ML training assets
│   └── clips/                    # Video clip storage
├── scripts/                      # Utility and deployment scripts
│   ├── gcp/                      # Google Cloud deployment configurations
│   └── media/                    # Media processing utilities
└── venv/                         # Virtual environment (gitignored)
```

### Data Setup
1. Place NHL CSV files in `data/raw/` (if available)
2. Configure Google Cloud credentials for Vertex AI and Cloud SQL access
3. Set up Pinecone vector database credentials
4. Initialize training data in `data/processed/llm_model/training/`
5. Deploy Cloud SQL PostgreSQL instance for news content storage

## Usage Examples

### Basic Queries
```python
# Initialize the HeartBeat system via API
import requests

# Query the analytics engine via REST API
response = requests.post("https://your-cloud-run-url/api/query",
    json={"query": "How effective was Montreal's power play against Toronto?"}
)
result = response.json()
print(result['content'])
print(result['analytics'])
```

### Advanced Analysis
```python
# Multi-game performance analysis
response = requests.post("https://your-cloud-run-url/api/query",
    json={"query": "Compare Suzuki's performance in 5v5 vs power play situations"}
)

# Trend analysis with video clips
response = requests.post("https://your-cloud-run-url/api/query",
    json={"query": "What's the impact of youth pairings on zone exit success?"}
)

# Predictive insights with visualizations
response = requests.post("https://your-cloud-run-url/api/query",
    json={"query": "Which matchups should we target for better scoring opportunities?"}
)
```

### Context-Aware Queries (Planned)
```python
# Context automatically injected based on current page
# User on McDavid's profile page with 2023-24 season selected
response = requests.post("https://your-cloud-run-url/api/query",
    json={"query": "How does this compare to league average?", "context": {"player": "McDavid", "season": "2023-24"}}
)
# AI automatically knows: current player (McDavid), season (2023-24), current metrics being viewed

# User viewing Oilers vs Flames matchup analysis with power play filter active
response = requests.post("https://your-cloud-run-url/api/query",
    json={"query": "What are the key weaknesses to exploit?", "context": {"teams": ["EDM", "CGY"], "situation": "power_play"}}
)
# AI automatically knows: teams (EDM vs CGY), situation (power play), current context

# User on team comparison page with multiple teams selected
response = requests.post("https://your-cloud-run-url/api/query",
    json={"query": "Which team has the best depth scoring?", "context": {"page": "team_comparison", "selected_teams": ["MTL", "TOR", "BOS"]}}
)
# AI automatically knows: selected teams, comparison context, current metrics being analyzed
```

### API Usage
```python
import requests

# Query via REST API
response = requests.post("http://localhost:8000/api/query",
    json={"query": "Analyze Montreal's shot distribution patterns"}
)
result = response.json()
```

## Performance Benchmarks

### Model Specifications
- **Core Reasoning Model**: Qwen3-Next-80B Thinking on Vertex AI
  - MoE architecture (subset of 80B parameters activate per token)
  - Reasoning-first design for multi-step planning
  - Function calling with strict JSON schemas
  - Managed serving via Google Cloud Model Garden
- **Vision Model**: Qwen3-VL on Vertex AI (on-demand)
  - Invoked only for visual analysis tasks
  - Shot maps, formation diagrams, video frames
  - Cost-optimized selective usage

### Target Performance Metrics
- **Query Accuracy**: Target 90%+ statistically correct responses with enhanced reasoning
- **Response Time**: <3 seconds for text queries, <5 seconds with vision analysis
- **Retrieval Precision**: >85% relevant information retrieval across text and visual data
- **Tool Integration**: Dynamic RAG + Parquet SQL hybrid queries + on-demand vision processing
- **Cost Efficiency**: MoE activates subset of parameters; vision model only when needed
- **Multimodal Capabilities**: Video analysis, rink diagram interpretation, statistical visualization processing
- **Infrastructure**: Google Cloud Run Jobs for automated tasks, Cloud SQL for data persistence

### Line Matchup Engine Performance
- **Prediction Accuracy**: 87.3% top-1, 94.2% top-3 deployment prediction accuracy
- **Feature Processing**: 65-dimensional feature vectors with team-aware and player-vs-player matchup priors
- **Memory Efficiency**: EWMA-weighted pattern storage with top-N pruning (25 matchups per player)
- **Real-time Performance**: <100ms candidate generation, <200ms full prediction pipeline
- **Bidirectional Intelligence**: Learns patterns from both MTL and opponent perspectives

### Reproducibility & Benchmarking Notes

**Important Performance Caveats:**

- **Benchmark Environment**: Performance metrics are measured on specific hardware configurations and may vary significantly across different systems
- **Data Dependency**: Accuracy metrics are highly dependent on training data quality, coverage, and recency
- **Evaluation Methodology**: Metrics use cross-validation on historical data; real-world performance may differ
- **Continuous Evolution**: Performance improves continuously through model updates and additional training data
- **Hardware Requirements**: Optimal performance requires adequate computational resources (8GB+ RAM, GPU recommended)

### Reproducible Testing

For reproducible benchmarks:
1. Use the standardized test suite in `/scripts/line_matchup_engine/test_*.py`
2. Follow the evaluation methodology documented in `TEAM_AWARE_SYSTEM_COMPLETE.md`
3. Ensure consistent data preprocessing and feature engineering
4. Run performance diagnostics: `python performance_diagnostics.py`

**Benchmark Results Disclaimer**: All performance metrics are estimates based on controlled testing environments and may not reflect production performance across all use cases and data scenarios.

## Contributing

### Development Philosophy
- **Efficiency First**: Prioritize simple, optimal code over complex systems
- **Hockey-Centric**: All features must enhance professional hockey analysis capabilities across all teams
- **Iterative Approach**: MVP focus with clear upgrade paths
- **Open Collaboration**: Welcome contributions from hockey analytics community

### Contribution Guidelines
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Standards
- **PEP 8** compliance for Python code
- **Type hints** for all function parameters
- **Docstrings** for all public functions
- **Unit tests** for new functionality
- **Performance profiling** for data processing functions

## Future Enhancements

### Phase 2 (Post-MVP)
- **Real-time Data**: NHL API integration for live game analysis
- **Advanced Visualizations**: AR rink overlays, player tracking animations
- **Predictive Modeling**: Game outcome forecasting, player performance prediction
- **Voice Interface**: Natural language voice queries and responses

### Research Directions
- **Advanced RAG**: Multi-modal embeddings (text + spatial data)
- **Reinforcement Learning**: Optimal strategy recommendations
- **Computer Vision**: Video clip retrieval for key moments
- **Network Analysis**: Player connectivity and chemistry modeling

## License

This project is licensed under the MIT License - see the [LICENSE] file for details.



**Built for Professional Hockey Analytics**

*For questions or collaboration opportunities, please open an issue or contact the maintainers.*
