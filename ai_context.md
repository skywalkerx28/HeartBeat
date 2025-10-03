# AI Context: HeartBeat Engine Development Guide

## Project Mission
**HeartBeat Engine** is an AI-powered analytics platform tailored exclusively for the Montreal Canadiens. At its core, it's a semantic search and analysis "AI index" that transforms a collection of tabular and visual data (covering recent seasons ~millions granular events like shots, passes, possessions, and coordinates) into an intelligent, conversational knowledge base.

Coaches, players, scouts, analysts, and other authorized personnel can ask natural-language questions (e.g., "Analyze the Habs power play efficiency against Toronto's last season" or "What's the impact of pairing Hutson with Dobson on xGF?" or "Show me all of my shorthanded shifts from last season") and receive dynamic, data-grounded responses: aggregated stats (e.g., xG differentials), visualizations (e.g., shot heatmaps on a rink), trend breakdowns, and even prescriptive recommendations (e.g., "Target east-slot rushes—boosts scoring by 18%").

## Key Differentiators

### Hyper-Tailored for MTL
- **Canadiens-Specific Logic**: Embeds Montreal-specific insights (e.g., St. Louis' transition style, youth metrics like player development trends and prospect performances) via custom prompts and fine-tuning
- **Habs-Centric Metrics**: Optimized for Montreal's playing style, personnel, and strategic priorities

### Dynamic & Proactive Analysis
- **Retrieval-Augmented Generation (RAG)**: Uses LLM to interpret queries, retrieve relevant events, execute on-the-fly analysis
- **No Pre-coded Queries**: Handles any natural language question without predefined templates
- **Real-time Insights**: Generates tables, plots, and recommendations dynamically

### Scalable Architecture
- **MVP Foundation**: Starts offline with extensive local tabular and visual data; evolves to real-time ingestion
- **Extensible Design**: Ready for 2025-26 data, interactive visualizations, NHL API integrations
- **Cloud-Ready**: Deployable on Hugging Face Spaces with offline fallback for sensitive data

## Core Development Philosophy

### **EFFICIENCY & SIMPLICITY FIRST**
- **Prioritize simple, optimal code over complex systems**
- **Avoid over-engineering** - solve problems with the minimal viable solution
- **Performance matters** - optimize for speed and memory usage
- **Maintainable code** - clear, readable, well-documented
- **Iterative development** - build MVP first, then enhance

### **MTL-Centric Focus**
- All features must enhance Canadiens analysis capabilities
- Embed Montreal-specific logic and metrics
- Optimize for Habs playing style and personnel
- Consider coach preferences and team priorities

## Technical Architecture

### LangGraph Orchestrator Core
**Central Intelligence:** LangGraph-based agent orchestrator powered by fine-tuned `Qwen/Qwen3-VL-235B-A22B-Thinking`

**Processing Flow:**
```
User Query → Intent Classification → Router → Tools → Synthesis → Response
```

**Node Architecture:**
- **Intent Node**: Query classification and parameter extraction
- **Router Node**: Determines RAG vs Parquet vs hybrid data needs
- **Vector Search**: Semantic retrieval from hockey knowledge chunks
- **Parquet SQL**: Real-time analytics queries on game/player data
- **Analytics Tools**: xG calculations, zone entry/exit stats, matchup comparisons
- **Vision Analysis Node**: Video clip analysis, rink diagram interpretation, and visual pattern recognition
- **Visualization**: Dynamic heatmaps, charts, and statistical displays
- **Synthesis**: Context-aware response generation with evidence citation

### System Guards & Identity Management
- **User/Role Filters**: Identity-aware data scoping and permissions
- **Resource Guards**: Row/byte caps, query timeouts, retry logic
- **Caching Layer**: Intelligent caching for performance optimization
- **Security**: `resolve_current_user` with data access enforcement

### Hybrid Data Architecture
- **RAG System**: Hockey domain knowledge and contextual explanations
- **Live Analytics**: Real-time Parquet queries for current statistics
- **Tool Integration**: Seamless combination of historical and live data
- **Multimodal Processing**: Vision-language capabilities with enhanced spatial reasoning

### SageMaker Model Training & Deployment
- **Training Infrastructure**: AWS SageMaker for large-scale model fine-tuning
- **Model Registry**: Centralized model versioning and deployment management
- **Scalable Inference**: Auto-scaling endpoints for production workloads

### Tech Stack
- **Orchestration**: LangGraph agent workflows with Qwen3 Agent Framework integration and custom node architecture
- **Core Model**: Qwen/Qwen3-VL-235B-A22B-Thinking (235B total, 22B active parameters, MIT licensed)
- **Multimodal Processing**: Vision-language capabilities with 256K-1M token context window
- **ML Platform**: AWS SageMaker for enterprise-grade training and inference
- **Vector Database**: Pinecone with hybrid semantic + keyword search
- **Analytics Backend**: Python 3.13, pandas, pyarrow for Parquet optimization
- **Video Processing**: FFmpeg integration with enhanced video analysis capabilities
- **Visualization**: Dynamic matplotlib/seaborn charts with real-time generation
- **Frontend**: React + TypeScript interface with Tailwind CSS
- **Backend**: FastAPI services with async processing capabilities
- **Security**: AWS IAM policies, Secrets Manager, and role-based access control
- **Infrastructure**: Terraform-ready AWS configurations and deployment scripts

## Major Development Phases

### Phase 1: Data Preparation & Ingestion Pipeline - COMPLETED
**Goal**: Clean, unified, query-ready dataset with optimized storage formats
**Key Tasks**:
- [COMPLETED] Audit & concatenate CSVs for schema consistency (82 games + 32 matchups)
- [COMPLETED] Data cleaning, enrichment, and feature derivation
- [COMPLETED] Chunking for RAG (500-event summaries, JSON formatted)
- [COMPLETED] Initial Parquet database setup (90% compression, 10x faster queries)
**Efficiency Focus**: Vectorized pandas operations, chunked processing, compressed storage

### Phase 2: Vectorization & Retrieval System - COMPLETED
**Goal**: Enable semantic search over hockey events with multi-tier retrieval
**Key Tasks**:
- [COMPLETED] Embedding generation for semantic search (Sentence-BERT optimization)
- [COMPLETED] Pinecone vector database implementation
- [COMPLETED] Hybrid search (semantic + keyword filtering)
- [COMPLETED] MTL-specific embedding fine-tuning (Habs terminology)
**Efficiency Focus**: Batch processing, memory-efficient embeddings, sub-second retrieval

### Phase 3: LangGraph Orchestrator & Analysis Engine - IN PROGRESS
**Goal**: Implement a sophisticated LangGraph-based agent orchestrator leveraging the Qwen3 Agent Framework with fine-tuned Qwen/Qwen3-VL-235B-A22B-Thinking, seamlessly combining hybrid RAG + real-time analytics for dynamic multimodal hockey analysis with enterprise-grade security and performance.

#### Architecture Implementation:
- **LangGraph Agent Core:** LangGraph orchestrator enhanced with Qwen3 Agent Framework integration, powered by fine-tuned `Qwen/Qwen3-VL-235B-A22B-Thinking` for advanced multimodal reasoning, autonomous tool orchestration, and sophisticated agentic capabilities
- **Node-based Workflow:** Intent → Router → Vector Search → Parquet SQL → Analytics Tools → Visualization → Synthesis
- **Identity-Aware System:** User role enforcement with data scoping and permissions
- **Hybrid Intelligence:** RAG chunks for hockey context + live Parquet queries + video analysis capabilities
- **Tool Orchestration:** xG calculations, zone entry/exit analysis, matchup comparisons, dynamic visualizations
- **Multimodal Processing:** Vision-language analysis of game footage, rink diagrams, and statistical visualizations

#### Technical Implementation Strategy:

##### 3.1 Qwen3 Agent Framework Integration within LangGraph
**Enhanced LangGraph Architecture:**
```
LangGraph Orchestrator (Enhanced)
├── Qwen3 Agent Framework Layer
│   ├── Autonomous Tool Planning
│   ├── Multi-step Reasoning
│   ├── Context-Aware Decision Making
│   └── Adaptive Learning
├── Core LangGraph Nodes
│   ├── Intent Analysis Node
│   ├── Router Node
│   ├── Tool Execution Nodes
│   └── Synthesis Node
└── Qwen/Qwen3-VL-235B-A22B-Thinking Model
```

**Integration Approach:**
- **Framework Enhancement**: Qwen3 Agent Framework serves as an intelligent layer within LangGraph, enhancing node decision-making and tool orchestration
- **Preserved Structure**: Core LangGraph workflow (Intent → Router → Tools → Synthesis) remains intact but with enhanced agentic capabilities
- **Autonomous Enhancement**: Qwen3 agents autonomously optimize tool selection, parameter generation, and execution strategies within each LangGraph node
- **Contextual Intelligence**: Framework provides situation-aware reasoning that adapts to complex hockey analytics scenarios

**Agent Framework Capabilities within LangGraph:**
- **Autonomous Tool Orchestration**: Qwen3 agents within LangGraph nodes autonomously plan and execute multi-step analytical workflows
- **Contextual Reasoning**: Advanced reasoning over hockey domain knowledge with situation-aware decision making
- **Multimodal Agent Actions**: Vision-language agents capable of analyzing game footage, rink diagrams, and statistical visualizations
- **Adaptive Learning**: Continuous improvement through interaction patterns and user feedback
- **Enterprise Agent Security**: Role-based agent permissions with data access controls and audit trails

##### 3.3 LangGraph Node Orchestration System
```
LangGraph Processing Flow:
User Query → Intent Node → Router Node → Tool Execution → Synthesis Node → Response
     ↓             ↓            ↓              ↓               ↓
Identity Check  Classify &   RAG/Parquet   Analytics &    Evidence-based
& Permissions  Extract Params  Selection   Visualization   Response Gen
```

**LangGraph Node Architecture:**
- **Intent Node**: Query classification, parameter extraction, and user identity resolution with multimodal input support
- **Router Node**: Intelligent routing between RAG chunks, Parquet queries, video analysis, or hybrid approaches
- **Vector Search Node**: Semantic retrieval from hockey knowledge chunks with metadata filtering
- **Parquet SQL Node**: Real-time analytics queries with user-scoped data access
- **Analytics Tools Node**: xG calculations, zone entry/exit stats, matchup comparisons
- **Vision Analysis Node**: Video clip analysis, rink diagram interpretation, and visual pattern recognition
- **Visualization Node**: Dynamic heatmap and chart generation based on query results
- **Synthesis Node**: Context-aware response generation with multimodal source attribution

**Enterprise Features:**
- **Identity Management**: `resolve_current_user` with role-based data filtering
- **Resource Guards**: Row/byte limits, query timeouts, retry logic, intelligent caching
- **Security Layer**: Permission enforcement at each node with audit trail logging
- **Performance Optimization**: Parallel tool execution where possible, result caching

##### 3.4 RAG Chain Architecture
```
RAG Pipeline:
Query Processing → Retrieval (Pinecone) → Context Enhancement → Generation (Fine-tuned LLM)
     ↓                    ↓                           ↓                        ↓
Tokenization +       Semantic search +           Multi-source synthesis +   Prompt engineering +
Embedding           Hybrid filtering             Fact checking             Structured output
```

**Vector Database Implementation:**
- **Embedding Model**: Sentence-BERT optimized for sports analytics domain
- **Index Strategy**: HNSW (Hierarchical Navigable Small World) for sub-second retrieval
- **Hybrid Search**: Combines semantic similarity with keyword-based filtering
- **Metadata Filtering**: Game date, opponent, player, situation-specific retrieval

##### 3.5 Dynamic Analysis Tool Ecosystem for LLM
**Key Tasks**:
- Design MTL-specific prompts and system messages (Canadiens terminology)
- Implement hybrid RAG + tool chains with LangChain (context + live data integration)
- Create dynamic analysis tools enabling LLM to process any query combination
- Build real-time calculation capabilities (Corsi, zone entries, advanced metrics)

**LLM Tool Arsenal:**
```python
class HabsAnalysisTools:
    def query_team_stats(self, filters: dict, metrics: list):
        """Real-time team statistics with contextual explanations"""
        # Dynamic filtering: opponent, period, situation, date range
        
    def analyze_player_performance(self, player: str, context: dict):
        """Multi-dimensional player analysis with live calculations"""
        # Zone performance, line combinations, situational effectiveness
        
    def compare_scenarios(self, scenario_a: dict, scenario_b: dict):
        """Dynamic comparative analysis across any dimensions"""
        # Team vs team, player vs player, situation vs situation
        
    def calculate_advanced_metrics(self, data_source: str, metric_type: str):
        """On-demand calculation of complex hockey analytics"""
        # Corsi, expected goals, possession metrics, zone analysis
```

**Dynamic Tool Categories:**
- **Query Tools**: Real-time parquet data filtering and aggregation with hockey context
- **Analytics Tools**: Advanced metric calculation (Corsi, xG, zone analysis, possession)
- **Comparison Tools**: Multi-dimensional performance analysis and benchmarking
- **Visualization Tools**: Dynamic chart and heatmap generation from live query results
- **Context Tools**: Integrate RAG hockey knowledge with real-time data calculations

**CRITICAL REQUIREMENT**: LLM must be equipped with tools to answer ANY query combination dynamically, not limited to pre-computed static responses

##### 3.5.1 Tool Architecture Implementation
**Real-World Query Examples Requiring Dynamic Tools:**
- *"Montreal's shot blocking vs Toronto in 3rd periods this season"* → Requires filtering + context
- *"Compare Hutson's zone exits when paired with different defensemen"* → Requires joins + calculations  
- *"Show power play efficiency trends over last 10 games"* → Requires temporal analysis + visualization
- *"How does Montreal's penalty kill perform against teams with >25% power play?"* → Requires cross-dataset analysis

**Tool Implementation Strategy:**
```python
class HabsQueryEngine:
    def __init__(self):
        self.rag_chunks = load_contextual_chunks()  # Hockey knowledge
        self.parquet_tools = ParquetQueryTools()    # Live data access
        self.hockey_context = HockeyContextProvider()  # Domain expertise
        
    def process_query(self, query: str):
        # 1. Get hockey context from RAG
        context = self.rag_chunks.retrieve(query)
        
        # 2. Determine required tools
        tools_needed = self.analyze_query_requirements(query)
        
        # 3. Execute with tools + context
        return self.llm.generate(
            query=query,
            context=context,
            tools=tools_needed  # Real-time calculation capabilities
        )
```

##### 3.6 Structured Output Generation
**Key Tasks**:
- **Dynamic Visualization Engine**: Interactive shot heatmaps, performance charts, statistical tables
- **Response Formatting Pipeline**: Context-aware templates, data-to-narrative conversion
- **Source Attribution**: Clear indication of data sources and calculation methods

##### 3.7 Fine-Tuning & Optimization
**Domain-Specific Training:**
- **Custom Dataset**: 2,198 QA pairs focused on hockey analytics terminology + multimodal video datasets
- **Montreal Context**: Fine-tuning on Canadiens-specific language and references
- **Statistical Literacy**: Training on proper interpretation of advanced metrics
- **Conversational Flow**: Optimization for multi-turn analytical conversations
- **Multimodal Training**: Video analysis, rink diagram interpretation, statistical visualization understanding
- **SageMaker Infrastructure**: Enterprise-grade model training on AWS platform with Qwen/Qwen3-VL-235B-A22B-Thinking

**Performance Optimization:**
- **Query Caching**: Intelligent caching of frequent queries and calculations
- **Batch Processing**: Optimized batch operations for complex multi-game analysis
- **Memory Management**: Efficient handling of large datasets during analysis
- **Response Time Targets**: <2 seconds for basic queries, <5 seconds for complex analysis

##### 3.8 Testing & Validation Framework
**Automated Testing Suite:**
- **Unit Tests**: Individual component functionality (retrieval accuracy, calculation precision)
- **Integration Tests**: End-to-end query processing and response generation
- **Performance Benchmarks**: Query response times, retrieval accuracy metrics

**Human Evaluation Protocol:**
- **Expert Review**: Validation by hockey analysts and coaches
- **User Testing**: Real-world query testing with target user groups

#### Success Metrics:
- **Query Accuracy**: >90% statistically correct responses with enhanced multimodal reasoning
- **Response Time**: <3 seconds average for complex queries, <5 seconds for multimodal analysis
- **User Satisfaction**: >4.5/5 rating on response quality and relevance
- **Retrieval Precision**: >85% relevant information retrieval across text and visual data
- **Contextual Understanding**: >80% accurate interpretation of analytical intent
- **Multimodal Performance**: >85% accuracy in video analysis and visual pattern recognition
- **Context Window Utilization**: Efficient processing of 256K-1M token contexts for comprehensive analysis

**Efficiency Focus**: Lightweight models, cached responses, minimal API calls, intelligent data routing

### Phase 4: Enhanced Analytics & Testing - PLANNED
- [ ] **Advanced Visualizations**: Interactive heatmaps and performance charts
- [ ] **Video Integration**: Seamless video clip embedding in responses
- [ ] **Performance Optimization**: Query caching and response time improvements
- [ ] **Comprehensive Testing**: Unit tests, integration tests, and user validation

### Phase 5: Production Deployment - PLANNED
- [ ] **Containerization**: Docker deployment with optimized environments
- [ ] **Cloud Deployment**: AWS SageMaker endpoints and scalable infrastructure
- [ ] **Monitoring**: Performance metrics and error tracking
- [ ] **User Training**: Documentation and onboarding materials

## Code Development Guidelines

### **Performance Priorities**
1. **Data Processing**: Vectorized pandas operations over loops
2. **Memory Usage**: Process data in chunks, use appropriate data types
3. **Query Speed**: Optimize database queries, use indexing
4. **Model Inference**: Use efficient models, cache results
5. **File I/O**: Minimize disk reads, use compressed formats

### **Architecture Principles**
- **Modular Design**: Small, focused functions with single responsibilities
- **Configuration Management**: External config files for parameters
- **Error Handling**: Graceful failure with informative messages
- **Logging**: Comprehensive logging for debugging and monitoring
- **Testing**: Unit tests for all core functionality

### **Habs-Specific Considerations**
- **Player Mapping**: Efficient ID-to-name lookups
- **Game Context**: Include opponent, period, score differential
- **Team Logic**: Flag Habs events, calculate team-relative metrics
- **Strategic Insights**: Focus on transition, special teams, youth development

## Data Overview

- **Source**: NHL play-by-play CSV files and archive game footage (from recent relevant seasons)
- **Volume**: ~Millions granular events and thousands of game footage
- **Key Fields**: xCoord, yCoord, type, playerReferenceId, expectedGoalsOnNet, period, gameTime
- **Processing**: Unified schema, derived features (shot_distance, possession_duration), Habs event flagging

## Data Schema Understanding

### **Multi-Tier Data Architecture**

#### **Primary Analytics Layer (Parquet)**
**Location**: `/data/processed/analytics/`
**Format**: Compressed Parquet files (90% smaller than CSV)
**Use Case**: High-performance analytics and complex queries

**Core Fields in Play-by-Play Data (315K+ events):**
- `gameReferenceId`: Unique game identifier
- `id`: Sequential event ID within game
- `period`: Game period (1, 2, 3, OT)
- `periodTime`: Time elapsed in period
- `gameTime`: Total game time elapsed
- `xCoord`, `yCoord`: Spatial coordinates on rink
- `xAdjCoord`, `yAdjCoord`: Adjusted coordinates for rink orientation
- `type`: Event type (shot, pass, faceoff, etc.)
- `playerReferenceId`: Player identifier
- `playerJersey`: Jersey number
- `playerPosition`: Player position (C, LW, RW, D, G)
- `team`: Team abbreviation
- `expectedGoalsOnNet`: xG value for shots
- `game_id`: Processed game identifier
- `source_file`: Original CSV filename for traceability

#### **LLM Context Layer (JSON)**
**Location**: `/data/processed/llm_model/`
**Format**: Structured JSON for LLM consumption
**Use Case**: Fast retrieval and contextual responses

**Available JSON Files:**
- `rag_chunks_2024_2025.json`: 1,152 text chunks for semantic search
- `qa_pairs_2024_2025.json`: 2,528 Q&A pairs for fine-tuning
- `matchup_analysis_2024_2025.json`: Statistical matchup data
- `game_summaries_2024_2025.json`: Narrative game summaries

#### **Backup Layer (CSV)**
**Location**: `/data/processed/backups/`
**Format**: Original CSV files for compatibility
**Use Case**: Data recovery and legacy system integration

### **Derived Features (Automatically Generated)**
- `shot_distance`: Distance from center (sqrt(x² + y²))
- `shot_angle`: Angle from goal in degrees
- `possession_duration`: Time between consecutive events
- `is_habs_event`: Boolean flag for Canadiens actions
- `zone`: Offensive/Defensive/Neutral zone classification
- `playZone`: Specific rink zone (center, left, right, etc.)
- `playSection`: Detailed zone section for advanced analysis

## Technical Constraints & Optimizations

### Memory Management (ACHIEVED)
- Process large CSVs in chunks (automated ETL pipeline)
- Use Parquet format for 90% compressed storage
- Implement data type optimization and memory-efficient processing
- Clear memory after processing large datasets
- Handle 315K+ events efficiently without memory errors

### Performance Targets (CURRENT STATUS)
- Data loading: <60 seconds for all CSV files (achieved in ~30 seconds)
- Query response: <3 seconds for complex analysis (Parquet enables this)
- Embedding generation: <15 minutes for full dataset (Phase 2 target)
- Memory usage: <8GB during processing (achieved with chunked processing)
- 10x query performance improvement over CSV

### Scalability Considerations (IMPLEMENTED)
- Enterprise-grade data architecture with multi-tier storage
- Season-based file naming for easy expansion
- Modular architecture supporting cloud migration
- Intelligent caching strategy for LLM responses
- Lazy loading capabilities for large datasets
- Support for both CSV and archived game footage integration
- Real-time data ingestion pipeline ready for NHL API

### Current Performance Metrics
- **Storage Efficiency**: 90% compression (143MB → 14MB)
- **Query Performance**: 10x faster than CSV baseline
- **Data Integrity**: Zero data loss during ETL processing
- **Scalability**: Supports multiple seasons with consistent naming
- **Backup Reliability**: Automated CSV backups for data safety
- **Model Specifications**: Qwen3-VL-235B-A22B-Thinking (235B total, 22B active parameters)
- **Context Capacity**: 256K tokens native, extendable to 1M tokens
- **Multimodal Support**: Vision-language processing with enhanced spatial reasoning

## Development Status

### Completed Infrastructure
- **Model Migration**: Upgraded to Qwen/Qwen3-VL-235B-A22B-Thinking for multimodal capabilities
- **AWS Integration**: SageMaker training infrastructure and endpoint management
- **Project Reorganization**: Restructured codebase with proper separation of concerns
- **Data Architecture**: Organized training assets and video clip storage with multimodal support
- **Infrastructure Setup**: AWS policy files and deployment configurations

### Current Capabilities
- **LangGraph Orchestrator**: Agent-based workflow with intent analysis and routing
- **Hybrid Intelligence**: RAG + real-time Parquet SQL integration
- **Video Analytics**: Video clip retrieval and analysis capabilities
- **Multi-modal Interface**: React + TypeScript chat interface with analytics panels
- **Enterprise Security**: Role-based access control and data scoping

## Success Metrics

### Technical KPIs
- **Model**: Qwen/Qwen3-VL-235B-A22B-Thinking (235B total, 22B active parameters, MIT licensed)
- **Context Window**: 256K tokens native, extendable to 1M tokens for comprehensive game analysis
- **Query Accuracy**: Target 90%+ statistically correct responses with enhanced reasoning
- **Response Time**: <3 seconds average for complex analytical queries, <5 seconds for multimodal analysis
- **Training Data**: 2,198 hockey analytics QA pairs for fine-tuning + multimodal video datasets
- **Retrieval Precision**: >85% relevant information retrieval across text and visual data
- **Tool Integration**: Dynamic RAG + Parquet SQL hybrid queries + vision-language processing
- **Multimodal Capabilities**: Video analysis, rink diagram interpretation, statistical visualization processing

### User Experience KPIs
- **Query Flexibility**: Handles natural language queries without predefined templates
- **Insight Quality**: Provides actionable insights combining historical patterns and recommendations
- **Visualization**: Generates dynamic visualizations and statistical outputs automatically
- **User Satisfaction**: >4.5/5 rating on response quality and relevance
- **Retrieval Precision**: >85% relevant information retrieval across text and visual data
- **Contextual Understanding**: >80% accurate interpretation of analytical intent

### Code Quality KPIs
- **Architecture**: Modular design with clear separation of concerns
- **Performance**: Optimized ETL pipeline with automated quality validation
- **Scalability**: Enterprise-grade data architecture supporting production workloads
- **Security**: Role-based access control and data scoping implementation

## Deployment Strategy

### MVP Deployment
- Local development environment with real-time query processing
- Hugging Face Spaces for easy sharing and collaboration
- Docker containerization for reproducibility and deployment consistency
- Offline-first design for data security and Montreal-specific requirements

### Production Considerations
- Cloud migration path with AWS SageMaker endpoints and scalable infrastructure
- Database optimization for concurrent users (coaches, analysts, players)
- API rate limiting and intelligent caching for performance
- Monitoring, logging, and analytics infrastructure
- Security hardening for sensitive team data
- Scalable architecture supporting multiple seasons and real-time updates

## Installation & Setup

### Prerequisites
- Python 3.13+
- Git
- 8GB+ RAM (for ML model processing)
- AWS CLI configured (for SageMaker integration)

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
export OPENAI_API_KEY="your-openai-key"  # For fallback model

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
├── app/                          # Streamlit application (legacy)
├── backend/                      # FastAPI backend services
├── frontend/                     # Next.js React frontend
├── orchestrator/                 # LangGraph agent orchestration
├── data/                         # Data processing and storage
│   ├── processed/
│   │   └── llm_model/
│   │       └── training/         # ML training assets
│   └── clips/                    # Video clip storage
├── infrastructure/               # AWS infrastructure files
├── scripts/                      # Utility and deployment scripts
└── venv/                         # Virtual environment (gitignored)
```

## Usage Examples

### Basic Queries
```python
from app.main import initialize_system

# Initialize the HeartBeat system
system = initialize_system()

# Query the analytics engine
response = system.query("How effective was Montreal's power play against Toronto?")
print(response.content)
print(response.analytics)
```

### Advanced Analysis
```python
# Multi-game performance analysis
response = system.query("Compare Suzuki's performance in 5v5 vs power play situations")

# Trend analysis with video clips
response = system.query("What's the impact of youth pairings on zone exit success?")

# Predictive insights with visualizations
response = system.query("Which matchups should we target for better scoring opportunities?")
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

- **Model**: Qwen/Qwen3-VL-235B-A22B-Thinking (235B total, 22B active parameters, MIT licensed)
- **Context Window**: 256K tokens native, extendable to 1M tokens
- **Query Accuracy**: Target 90%+ statistically correct responses
- **Response Time**: <3 seconds average for complex queries, <5 seconds for multimodal analysis
- **Training Data**: 2,198 QA pairs focused on hockey analytics terminology
- **Retrieval Precision**: >85% relevant information retrieval
- **Tool Integration**: Dynamic RAG + Parquet SQL hybrid queries

## Collaboration Guidelines

### For AI Assistants
- Always prioritize efficiency and simplicity in implementation
- Ask for clarification rather than making assumptions about requirements
- Focus on delivering working, well-tested code rather than perfect code
- Document design decisions and trade-offs clearly in comments
- Test thoroughly and validate against real Montreal Canadiens data
- Maintain consistency with established patterns and architecture

### For Human Developers
- Review code for performance bottlenecks and optimization opportunities
- Ensure all features meet Montreal Canadiens-specific requirements
- Test with real Habs data scenarios and edge cases
- Focus on authorized personnel access and data security requirements
- Document any deviations from this guide with justification
- Validate that new features integrate properly with existing ETL pipeline

---

## **CURRENT PROJECT STATUS SUMMARY**

### **PHASE 1: COMPLETED (Data Foundation)**
- **82 NHL games processed** (315K+ events, 31 matchups)
- **Enterprise data architecture** (Parquet + JSON multi-tier system)
- **90% storage compression** with 10x query performance gains
- **Automated ETL pipeline** with quality validation
- **Scalable directory structure** ready for multiple seasons

### **PHASE 2: COMPLETED (Vector Search System)**
- **Pinecone vector database** implementation completed
- **Sentence-BERT embeddings** for semantic search
- **Hybrid search architecture** for semantic + keyword filtering
- **MTL-specific terminology** optimization implemented

### **PHASE 3: IN PROGRESS (LangGraph Orchestrator & Analysis Engine)**
- **LangGraph Agent Core:** LangGraph orchestrator enhanced with Qwen3 Agent Framework integration, powered by fine-tuned `Qwen/Qwen3-VL-235B-A22B-Thinking` for advanced multimodal reasoning, autonomous tool orchestration, and sophisticated agentic capabilities
- **Node-based Workflow:** Intent → Router → Vector Search → Parquet SQL → Analytics Tools → Visualization → Synthesis
- **Identity-Aware System:** User role enforcement with data scoping and permissions
- **Hybrid Intelligence:** RAG chunks for hockey context + live Parquet queries + video analysis capabilities
- **Tool Orchestration:** xG calculations, zone entry/exit analysis, matchup comparisons, dynamic visualizations
- **Multimodal Processing:** Vision-language analysis of game footage, rink diagrams, and statistical visualizations

### **KEY ACHIEVEMENTS**
- **World-class data foundation** with industry-standard practices
- **Performance optimization** exceeding initial targets
- **Scalable architecture** supporting enterprise growth
- **Montreal Canadiens focus** with domain-specific optimizations
- **Production-ready ETL** with comprehensive error handling
- **AWS SageMaker integration** for enterprise-grade model training
- **Multimodal capabilities** with Qwen/Qwen3-VL-235B-A22B-Thinking
- **Modern tech stack** with React/TypeScript frontend and FastAPI backend

---

**Remember**: This is a **world-class foundation** for a professional AI analytics platform. Our methodical approach ensures sustainable long-term success with enterprise-grade reliability and performance. The architecture we've built will support advanced AI capabilities for years to come!
