# HeartBeat Engine - LangGraph Orchestrator

**Montreal Canadiens Advanced Analytics Assistant**

A LangGraph-based orchestrator that coordinates between fine-tuned deepseek-ai/DeepSeek-R1-Distill-Qwen-32B model, Pinecone RAG, and Parquet analytics tools to provide sophisticated hockey analytics with role-based access control.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Components](#core-components)
- [Installation & Setup](#installation--setup)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Development](#development)
- [Testing](#testing)

## 📚 Complete Documentation

- **[README.md](README.md)** - This overview and getting started guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed technical architecture and design patterns
- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API documentation and usage examples
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide and best practices

## Architecture Overview

The HeartBeat orchestrator implements a hybrid intelligence system that combines:

- **Fine-tuned deepseek-ai/DeepSeek-R1-Distill-Qwen-32B**: Central reasoning engine trained on hockey analytics
- **Pinecone RAG**: Vector search for hockey domain knowledge and context
- **Parquet Analytics**: Real-time statistical queries and advanced metrics
- **Role-based Access**: Identity-aware processing for different user types

### Workflow Architecture

```
User Query → Intent Analysis → Router → Tools → Response Synthesis
     ↓              ↓           ↓        ↓            ↓
  Classify      Determine    Execute   Pinecone    Generate
   Query         Tools       Sequence    RAG      Response
   Type                                Parquet
                                      Analytics
```

### Key Features

- **Enterprise-Grade**: Production-ready with comprehensive error handling
- **Role-Based Access Control**: Coach, Player, Analyst, Staff, Scout permissions
- **Intelligent Routing**: Context-aware tool selection and execution sequencing
- **Hybrid Data Integration**: Seamless combination of contextual and analytical data
- **Professional Standards**: Clean architecture with comprehensive logging and monitoring

## Qwen3 Thinking — Reasoning‑First Orchestration (What’s New)

The orchestrator is optimized for Qwen3‑Next‑80B Thinking and lets the model truly “think on its feet,” using tools as amplifiers instead of constraints.

- Function‑calling stability
  - Tool turns run with a minimal config (temperature‑only) to avoid function‑calling dead‑ends and MAX_TOKENS stalls.
  - Final synthesis turns disable further tool calls and allow a large output budget so the model can write a complete answer.

- Rich toolbelt, model‑selected
  - Knowledge: `search_hockey_knowledge`
  - Rosters (API‑first): `get_team_roster`
  - Jerseys, per‑team: `find_player_by_team_and_number`
  - Jerseys, league‑wide: `find_players_by_number` (batch aggregation + TTL cache)
  - Schedule/Calendar: `get_schedule` (league or per‑team, date or range)
  - MTL analytics: `query_game_data`, `calculate_hockey_metrics`, `generate_visualization`

- Resilient data path
  - API‑first for freshness (NHL API), snapshot (Parquet) fallback, Pinecone RAG fallback for jersey and player lookups.
  - Telemetry on results (source: `api`, `snapshot`, `rag`, `cache`) for transparency in the UI.

- Output style
  - Plain text only, no Markdown or asterisks; clear hyphen bullets.

- Conversational memory (per user, per conversation)
  - The backend accepts a `conversation_id` and maintains a compact thread memory per authenticated user.
  - When context grows, older turns are summarized into a short memory so the model keeps direction without blowing token limits.
  - Short‑memory “last_entities” (e.g., last player/team referenced) help resolve pronouns in follow‑ups (e.g., “his metrics”).

- Typo and fuzzy name robustness
  - Player search uses fuzzy ranking and variants; roster/RAG lookups resolve common misspellings.
  - Example: a query like “who is mathew barzal” resolves correctly to Mathew Barzal (NYI) even with a typo.

## Core Components

### 1. Agent Orchestrator (`agents/heartbeat_orchestrator.py`)

Main coordination engine that manages the complete workflow:

- **LangGraph Integration**: State-based workflow management
- **Async Processing**: High-performance concurrent execution
- **Error Recovery**: Graceful degradation and fallback mechanisms

```python
from orchestrator import orchestrator, UserContext, UserRole

# Create user context
user = UserContext(
    user_id="coach_001",
    role=UserRole.COACH,
    team_access=["MTL"]
)

# Process query
result = await orchestrator.process_query(
    query="How is Suzuki performing this season?",
    user_context=user
)
```

### 2. Intent Analyzer (`nodes/intent_analyzer.py`)

Analyzes user queries to determine processing approach:

- **Query Classification**: Player analysis, team performance, game analysis, etc.
- **Tool Identification**: Determines required tools based on query patterns
- **Complexity Assessment**: Simple, moderate, or complex processing requirements

### 3. Smart Router (`nodes/router.py`)

Routes queries to appropriate tools with permission validation:

- **Permission Enforcement**: Role-based tool access control
- **Execution Sequencing**: Optimal tool execution order
- **Processing Strategies**: Single-tool, parallel, or multi-step approaches

### 4. Pinecone Retriever (`nodes/pinecone_retriever.py`)

Retrieves relevant hockey context and domain knowledge:

- **Vector Search**: Semantic similarity matching for hockey concepts
- **Query Optimization**: Hockey-specific query enhancement
- **Result Processing**: Quality validation and relevance scoring

### 5. Parquet Analyzer (`nodes/parquet_analyzer.py`)

Performs real-time analytics on structured hockey data:

- **Player Analytics**: Individual performance metrics and statistics
- **Team Analysis**: Team-level performance and comparative metrics
- **Game Analysis**: Event-level analysis and tactical insights
- **Advanced Metrics**: xG, Corsi, zone analysis calculations

### 6. Response Synthesizer (`nodes/response_synthesizer.py`)

Generates final responses using the fine-tuned model:

- **Role-Appropriate Formatting**: Tailored responses for different user types
- **Evidence Integration**: Combines RAG context with analytical data
- **Citation Management**: Source attribution and evidence chains
- **Model Integration**: SageMaker endpoint with OpenAI fallback

## Installation & Setup

### Prerequisites

- Python 3.11+
- AWS Account (for SageMaker integration)
- Pinecone Account (for vector search)

### Installation

```bash
# Install dependencies
pip install langgraph langchain langchain-community
pip install pinecone pandas pyarrow fastparquet
pip install openai boto3  # For fallback and AWS integration

# Set up environment variables
export PINECONE_API_KEY="your-pinecone-api-key"
export OPENAI_API_KEY="your-openai-api-key"  # For development fallback
```

### Configuration

Update `orchestrator/config/settings.py`:

```python
# Model configuration
settings.model.primary_model_endpoint = "your-sagemaker-endpoint"
settings.model.fallback_api_key = "your-openai-key"

# Pinecone configuration
settings.pinecone.api_key = "your-pinecone-key"
settings.pinecone.index_name = "heartbeat-unified"

# Data configuration
settings.parquet.data_directory = "data/processed"
```

## Usage Examples

### Basic Query Processing

```python
import asyncio
from orchestrator import orchestrator, UserContext, UserRole

async def main():
    # Create user context
    coach = UserContext(
        user_id="coach_001",
        role=UserRole.COACH,
        name="Head Coach",
        team_access=["MTL"]
    )
    
    # Process hockey analytics query
    result = await orchestrator.process_query(
        query="Compare Caufield's shooting percentage to league average",
        user_context=coach
    )
    
    print(f"Response: {result['response']}")
    print(f"Processing time: {result['processing_time_ms']}ms")
    print(f"Tools used: {[t['tool'] for t in result['tool_results']]}")

asyncio.run(main())
```

### Conversational Threads (per user)

Give each chat a `conversation_id` so the orchestrator can preserve context across turns. Older context is summarized automatically to stay within model limits.

```python
from orchestrator import orchestrator, UserContext, UserRole

user = UserContext(user_id="analyst_hughes", role=UserRole.ANALYST, team_access=["MTL"])

# Turn 1
res1 = await orchestrator.process_query(
    query="Tell me about Nick Suzuki",
    user_context=user
)

# Turn 2 (same conversation id passed via API layer)
res2 = await orchestrator.process_query(
    query="What about his performance metrics last season?",
    user_context=user
)
```

### Jersey Lookups (API‑first, league‑wide)

```python
# Single team
res = await orchestrator.process_query(
    query="Who wears number 14 on MTL?",
    user_context=user
)

# League‑wide count (batch + cache)
res = await orchestrator.process_query(
    query="How many players wear number 16 in the league?",
    user_context=user
)
```

### Role-Based Access Examples

```python
# Coach query - full tactical access
coach_result = await orchestrator.process_query(
    query="What are our powerplay weaknesses against Boston's penalty kill?",
    user_context=UserContext(user_id="coach", role=UserRole.COACH)
)

# Player query - personal focus
player_result = await orchestrator.process_query(
    query="How can I improve my faceoff percentage?",
    user_context=UserContext(user_id="player", role=UserRole.PLAYER)
)

# Analyst query - comprehensive data access
analyst_result = await orchestrator.process_query(
    query="Analyze correlation between zone entries and expected goals",
    user_context=UserContext(user_id="analyst", role=UserRole.ANALYST)
)
```

### Schedule / Calendar Queries (league or team)

```python
# League schedule for today
res = await orchestrator.process_query(
    query="Show today's NHL schedule",
    user_context=user
)

# Team upcoming schedule (next 7 days)
res = await orchestrator.process_query(
    query="Show the next 7 days of schedule for MTL",
    user_context=user
)
```

### Custom Query Types

```python
from orchestrator.utils.state import QueryType

# Specify query type for optimized processing
result = await orchestrator.process_query(
    query="Break down our last game against Toronto",
    user_context=coach,
    query_type=QueryType.GAME_ANALYSIS
)
```

## Configuration

### User Roles and Permissions

| Role | Data Scope | Advanced Metrics | Opponent Data | Tactical Analysis |
|------|------------|------------------|---------------|-------------------|
| **Coach** | Team, Player, Game, Strategy | ✅ | ✅ | ✅ |
| **Player** | Personal, Team, Game | ✅ | ❌ | ❌ |
| **Analyst** | Team, Player, Game, League | ✅ | ✅ | ✅ |
| **Staff** | Team, Game | ❌ | ❌ | ❌ |
| **Scout** | Player, Opponent, League | ✅ | ✅ | ✅ |

### Model Configuration

```python
@dataclass
class ModelConfig:
    primary_model_endpoint: str = ""  # SageMaker endpoint
    primary_model_name: str = "heartbeat-deepseek-r1-qwen-32b"
    fallback_model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 0.95
```

### Orchestration Settings

```python
@dataclass
class OrchestrationConfig:
    max_iterations: int = 10
    timeout_seconds: int = 30
    max_parallel_tools: int = 3
    tool_timeout_seconds: int = 15
    max_response_length: int = 2000
    require_citations: bool = True
```

## API Reference

### Main Orchestrator

#### `orchestrator.process_query(query, user_context, query_type=None)`

Process a hockey analytics query through the complete workflow.

**Parameters:**
- `query` (str): User's hockey analytics question
- `user_context` (UserContext): User identity and permissions
- `query_type` (QueryType, optional): Query classification hint

**Returns:**
- `dict`: Complete response with data, citations, and metadata

**Response Format:**
```python
{
    "response": str,              # Final response text
    "query_type": str,            # Classified query type
    "evidence_chain": List[str],  # Source citations
    "tool_results": List[dict],   # Tool execution results
    "processing_time_ms": int,    # Total processing time
    "user_role": str,            # User role
    "errors": List[str]          # Any error messages
}
```

### State Management

#### `create_initial_state(user_context, query, query_type=None)`

Create initial workflow state.

#### `UserContext(user_id, role, name="", team_access=["MTL"], session_id="", preferences={})`

User context for identity-aware processing.

### Configuration

#### `settings.validate_config()`

Validate orchestrator configuration.

**Returns:**
- `bool`: True if configuration is valid

## Development

### Project Structure

```
orchestrator/
├── __init__.py              # Main exports
├── README.md               # This documentation
├── agents/                 # Main orchestrator logic
│   ├── __init__.py
│   └── heartbeat_orchestrator.py
├── config/                 # Configuration management
│   ├── __init__.py
│   └── settings.py
├── nodes/                  # LangGraph workflow nodes
│   ├── __init__.py
│   ├── intent_analyzer.py
│   ├── router.py
│   ├── pinecone_retriever.py
│   ├── parquet_analyzer.py
│   └── response_synthesizer.py
└── utils/                  # Utilities and state management
    ├── __init__.py
    └── state.py
```

### Adding New Node Types

1. Create new node class inheriting base patterns:

```python
class CustomAnalyzerNode:
    def process(self, state: AgentState) -> AgentState:
        # Node processing logic
        return state
```

2. Add to workflow in `heartbeat_orchestrator.py`:

```python
workflow.add_node("custom_analysis", self._custom_analysis_node)
```

3. Update routing logic in `router.py` for new tool types.

### Extending Query Types

Add new query types in `utils/state.py`:

```python
class QueryType(Enum):
    # Existing types...
    INJURY_ANALYSIS = "injury_analysis"
    TRADE_EVALUATION = "trade_evaluation"
```

Update intent analyzer patterns in `nodes/intent_analyzer.py`.

## Testing

### Running Tests

```bash
# Run orchestrator tests
python test_orchestrator.py

# Test specific components
python -m pytest orchestrator/tests/
```

### Test Coverage

The test suite covers:

- **Configuration Validation**: Settings and permissions
- **State Management**: Workflow state transitions
- **Intent Analysis**: Query classification accuracy
- **Routing Logic**: Tool selection and sequencing
- **Integration Testing**: End-to-end workflow execution

### Mock Data Testing

The orchestrator includes comprehensive mock data for testing without external dependencies:

- Mock Pinecone responses for RAG testing
- Mock Parquet data for analytics testing
- Mock model responses for synthesis testing

## Performance Considerations

### Optimization Features

- **Caching**: Intelligent caching of frequent queries
- **Parallel Processing**: Concurrent tool execution where possible
- **Memory Management**: Efficient handling of large datasets
- **Response Streaming**: Progressive response generation

### Monitoring and Logging

- **Execution Tracking**: Detailed timing and performance metrics
- **Error Logging**: Comprehensive error tracking and debugging
- **Usage Analytics**: Query patterns and performance analysis

### Scalability

- **Horizontal Scaling**: Multiple orchestrator instances
- **Load Balancing**: Distributed query processing
- **Resource Management**: Efficient resource utilization

## Integration Points

### SageMaker Model Integration

The orchestrator is designed to integrate seamlessly with your fine-tuned deepseek-ai/DeepSeek-R1-Distill-Qwen-32B model:

```python
# Update model endpoint when training completes
settings.model.primary_model_endpoint = "your-sagemaker-endpoint-url"
```

### Pinecone RAG Integration

Connect to your existing Pinecone index:

```python
settings.pinecone.index_name = "heartbeat-unified"
settings.pinecone.namespace = "mtl-2024-2025"
```

### Parquet Data Integration

Point to your processed hockey data:

```python
settings.parquet.data_directory = "data/processed"
```

## Support and Maintenance

### Logging Configuration

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Error Handling

The orchestrator implements comprehensive error handling:

- **Graceful Degradation**: Fallback responses when tools fail
- **Circuit Breakers**: Prevent cascading failures
- **Retry Logic**: Automatic retry for transient failures
- **User-Friendly Errors**: Clear error messages for end users

### Health Checks

```python
# Validate system health
is_healthy = settings.validate_config()
if not is_healthy:
    print("System configuration issues detected")
```

---

**HeartBeat Engine Team**  
Version 1.0.0  
Built with enterprise-grade standards for Montreal Canadiens analytics
