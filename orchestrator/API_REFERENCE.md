# HeartBeat Engine - API Reference

**Montreal Canadiens Advanced Analytics Assistant**

## Quick Reference

### Main Orchestrator

```python
from orchestrator import orchestrator, UserContext, UserRole

# Process query
result = await orchestrator.process_query(
    query="How is Suzuki performing this season?",
    user_context=UserContext(user_id="coach", role=UserRole.COACH)
)
```

## Core Classes

### `HeartBeatOrchestrator`

Main orchestrator class that coordinates the complete workflow.

#### Methods

##### `async process_query(query, user_context, query_type=None)`

Process a hockey analytics query through the complete orchestrator workflow.

**Parameters:**
- `query` (str): User's hockey analytics query
- `user_context` (UserContext): User identity and permissions
- `query_type` (QueryType, optional): Optional hint about query type

**Returns:**
- `dict`: Complete response with data, citations, and metadata

**Response Format:**
```python
{
    "response": str,                    # Final response text
    "query_type": str,                  # Classified query type
    "evidence_chain": List[str],        # Source citations
    "tool_results": List[dict],         # Tool execution results
    "processing_time_ms": int,          # Total processing time
    "user_role": str,                   # User role
    "errors": List[str]                 # Any error messages
}
```

**Example:**
```python
coach = UserContext(user_id="coach_001", role=UserRole.COACH)
result = await orchestrator.process_query(
    "Compare Caufield's shooting percentage to league average",
    coach
)
print(f"Response: {result['response']}")
```

---

## Data Classes

### `UserContext`

User context for identity-aware processing.

```python
@dataclass
class UserContext:
    user_id: str                              # Unique user identifier
    role: UserRole                            # User role (COACH, PLAYER, etc.)
    name: str = ""                           # Display name
    team_access: List[str] = ["MTL"]         # Accessible teams
    session_id: str = ""                     # Session identifier
    preferences: Dict[str, Any] = {}         # User preferences
```

**Example:**
```python
coach = UserContext(
    user_id="coach_001",
    role=UserRole.COACH,
    name="Head Coach",
    team_access=["MTL"],
    session_id="session_123"
)
```

### `ToolResult`

Result from a tool execution.

```python
@dataclass
class ToolResult:
    tool_type: ToolType                      # Type of tool executed
    success: bool                            # Execution success status
    data: Any = None                         # Tool output data
    error: Optional[str] = None              # Error message if failed
    execution_time_ms: int = 0               # Execution time
    citations: List[str] = []                # Source citations
```

---

## Enums

### `UserRole`

User roles for identity-aware data access.

```python
class UserRole(Enum):
    COACH = "coach"                          # Full tactical and strategic access
    PLAYER = "player"                        # Personal and team performance focus
    ANALYST = "analyst"                      # Comprehensive data access
    STAFF = "staff"                          # Basic team operations
    SCOUT = "scout"                          # Player evaluation and recruitment
```

### `QueryType`

Types of queries the orchestrator can handle.

```python
class QueryType(Enum):
    PLAYER_ANALYSIS = "player_analysis"       # Individual player performance
    TEAM_PERFORMANCE = "team_performance"     # Team-level statistics
    GAME_ANALYSIS = "game_analysis"           # Specific game breakdown
    MATCHUP_COMPARISON = "matchup_comparison" # Head-to-head comparisons
    TACTICAL_ANALYSIS = "tactical_analysis"   # Strategic and tactical insights
    STATISTICAL_QUERY = "statistical_query"   # Direct statistical lookups
    GENERAL_HOCKEY = "general_hockey"         # General hockey questions
```

### `ToolType`

Available tools in the orchestrator.

```python
class ToolType(Enum):
    VECTOR_SEARCH = "vector_search"          # Pinecone RAG retrieval
    PARQUET_QUERY = "parquet_query"          # Statistical data queries
    CALCULATE_METRICS = "calculate_metrics"  # Advanced metric calculations
    MATCHUP_ANALYSIS = "matchup_analysis"    # Comparative analysis
    VISUALIZATION = "visualization"          # Charts and visualizations
```

---

## State Management

### `create_initial_state(user_context, query, query_type=None)`

Create initial state for a new orchestrator workflow.

**Parameters:**
- `user_context` (UserContext): User identity and permissions
- `query` (str): User's query
- `query_type` (QueryType, optional): Query type hint

**Returns:**
- `AgentState`: Initial workflow state

**Example:**
```python
from orchestrator.utils.state import create_initial_state, QueryType

initial_state = create_initial_state(
    user_context=coach,
    query="Analyze our powerplay efficiency",
    query_type=QueryType.TEAM_PERFORMANCE
)
```

### Utility Functions

#### `has_required_data(state)`

Check if we have sufficient data to generate a response.

#### `should_continue_processing(state, max_iterations=10)`

Determine if processing should continue.

#### `add_tool_result(state, result)`

Add a tool execution result to the state.

#### `add_error(state, error)`

Add an error message to the state.

---

## Configuration

### `OrchestratorSettings`

Main settings class for HeartBeat orchestrator.

#### Properties

- `model`: ModelConfig - Model configuration
- `pinecone`: PineconeConfig - Pinecone settings
- `parquet`: ParquetConfig - Parquet data settings
- `orchestration`: OrchestrationConfig - Workflow settings

#### Methods

##### `get_user_permissions(role)`

Get permissions for a specific user role.

**Parameters:**
- `role` (UserRole): User role

**Returns:**
- `dict`: Permission configuration

##### `validate_config()`

Validate configuration settings.

**Returns:**
- `bool`: True if configuration is valid

**Example:**
```python
from orchestrator.config.settings import settings

# Get coach permissions
coach_perms = settings.get_user_permissions(UserRole.COACH)
print(f"Coach can access: {coach_perms['data_scope']}")

# Validate configuration
if settings.validate_config():
    print("Configuration is valid")
```

---

## Configuration Classes

### `ModelConfig`

Model configuration for different deployment scenarios.

```python
@dataclass
class ModelConfig:
    primary_model_endpoint: str = ""         # SageMaker endpoint URL
    primary_model_name: str = "heartbeat-deepseek-r1-qwen-32b"
    fallback_model: str = "gpt-4o-mini"      # Development fallback
    fallback_api_key: str = ""               # OpenAI API key
    temperature: float = 0.1                 # Model temperature
    max_tokens: int = 4096                   # Maximum response tokens
    top_p: float = 0.95                      # Nucleus sampling parameter
```

### `PineconeConfig`

Pinecone vector database configuration.

```python
@dataclass
class PineconeConfig:
    api_key: str = ""                        # Pinecone API key
    environment: str = "us-east-1"           # Pinecone environment
    index_name: str = "heartbeat-unified"    # Index name
    namespace: str = "mtl-2024-2025"         # Namespace for MTL data
    top_k: int = 5                           # Number of results to retrieve
    score_threshold: float = 0.7             # Minimum relevance score
```

### `ParquetConfig`

Parquet analytics configuration.

```python
@dataclass
class ParquetConfig:
    data_directory: str = "data/processed"   # Data directory path
    cache_enabled: bool = True               # Enable result caching
    cache_ttl_seconds: int = 300             # Cache time-to-live
    max_query_results: int = 1000            # Maximum query results
```

### `OrchestrationConfig`

Core orchestration settings.

```python
@dataclass
class OrchestrationConfig:
    max_iterations: int = 10                 # Maximum workflow iterations
    timeout_seconds: int = 30                # Query timeout
    enable_debug_logging: bool = True        # Debug logging
    max_parallel_tools: int = 3              # Maximum parallel tools
    tool_timeout_seconds: int = 15           # Individual tool timeout
    max_response_length: int = 2000          # Maximum response length
    require_citations: bool = True           # Require source citations
```

---

## Usage Examples

### Basic Query Processing

```python
import asyncio
from orchestrator import orchestrator, UserContext, UserRole

async def basic_query():
    # Create user context
    analyst = UserContext(
        user_id="analyst_001",
        role=UserRole.ANALYST,
        name="Senior Analyst"
    )
    
    # Process query
    result = await orchestrator.process_query(
        query="What are Suzuki's advanced metrics this season?",
        user_context=analyst
    )
    
    # Display results
    print(f"Response: {result['response']}")
    print(f"Processing time: {result['processing_time_ms']}ms")
    print(f"Evidence: {result['evidence_chain']}")

asyncio.run(basic_query())
```

### Role-Based Query Examples

```python
# Coach query - tactical analysis
coach_result = await orchestrator.process_query(
    query="How should we adjust our powerplay against Boston's penalty kill?",
    user_context=UserContext(user_id="coach", role=UserRole.COACH)
)

# Player query - personal performance
player_result = await orchestrator.process_query(
    query="How can I improve my faceoff percentage in the defensive zone?",
    user_context=UserContext(user_id="player", role=UserRole.PLAYER)
)

# Scout query - player evaluation
scout_result = await orchestrator.process_query(
    query="Evaluate this prospect's defensive positioning and potential NHL fit",
    user_context=UserContext(user_id="scout", role=UserRole.SCOUT)
)
```

### Advanced Configuration

```python
from orchestrator.config.settings import settings

# Update model configuration
settings.model.primary_model_endpoint = "your-sagemaker-endpoint"
settings.model.temperature = 0.2

# Update Pinecone configuration
settings.pinecone.api_key = "your-pinecone-key"
settings.pinecone.top_k = 8

# Update orchestration settings
settings.orchestration.max_response_length = 3000
settings.orchestration.timeout_seconds = 45

# Validate configuration
if not settings.validate_config():
    print("Configuration validation failed")
```

### Error Handling

```python
async def robust_query():
    try:
        result = await orchestrator.process_query(
            query="Complex analytical query",
            user_context=UserContext(user_id="user", role=UserRole.ANALYST)
        )
        
        if result.get('errors'):
            print(f"Warnings: {result['errors']}")
        
        return result['response']
        
    except Exception as e:
        print(f"Query failed: {str(e)}")
        return "Sorry, I encountered an error processing your request."
```

### Batch Processing

```python
async def process_multiple_queries():
    queries = [
        "How is Caufield performing?",
        "What are our team defensive metrics?",
        "Analyze last game's powerplay opportunities"
    ]
    
    user = UserContext(user_id="coach", role=UserRole.COACH)
    
    # Process queries concurrently
    tasks = [
        orchestrator.process_query(query, user) 
        for query in queries
    ]
    
    results = await asyncio.gather(*tasks)
    
    for i, result in enumerate(results):
        print(f"Query {i+1}: {result['response'][:100]}...")
```

---

## Error Codes and Messages

### Common Error Scenarios

| Error Type | Description | Resolution |
|------------|-------------|------------|
| `ConfigurationError` | Missing API keys or invalid settings | Check configuration validation |
| `PermissionError` | User lacks access to requested data | Verify user role and permissions |
| `NetworkError` | External service unavailable | Check network connectivity |
| `DataError` | Missing or corrupted data files | Verify data file availability |
| `ProcessingError` | Analysis or model execution failed | Check logs for specific details |

### Error Response Format

```python
{
    "response": "Error message for user",
    "error": "Technical error details",
    "processing_time_ms": int,
    "success": False
}
```

---

## Performance Guidelines

### Optimization Tips

1. **Use Specific Query Types**: Provide query_type hints for faster processing
2. **Cache Results**: Enable caching for repeated queries
3. **Limit Scope**: Use role-based access to limit data scope
4. **Monitor Performance**: Track processing times and optimize bottlenecks

### Performance Metrics

- **Query Processing**: Target <3 seconds for standard queries
- **Tool Execution**: Individual tools should complete <15 seconds
- **Memory Usage**: Efficient memory management for large datasets
- **Concurrent Requests**: Support for multiple simultaneous queries

---

**API Reference**  
**HeartBeat Engine - Montreal Canadiens Analytics**  
Version 1.0.0
