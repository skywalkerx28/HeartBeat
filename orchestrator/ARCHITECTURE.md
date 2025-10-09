# HeartBeat Engine - Orchestrator Architecture

**Technical Architecture Documentation**  
**Montreal Canadiens Advanced Analytics Assistant**

## System Architecture Overview

The HeartBeat orchestrator implements a sophisticated LangGraph-based workflow that coordinates multiple AI systems to provide comprehensive hockey analytics. The architecture follows enterprise-grade patterns with clean separation of concerns, comprehensive error handling, and role-based security.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HeartBeat Orchestrator                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐ │
│  │   Intent    │───▶│    Router    │───▶│  Response Synthesis │ │
│  │  Analyzer   │    │              │    │                     │ │
│  └─────────────┘    └──────────────┘    └─────────────────────┘ │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────┐    ┌──────────────┐                            │
│  │  Pinecone   │    │   Parquet    │                            │
│  │ Retriever   │    │  Analyzer    │                            │
│  └─────────────┘    └──────────────┘                            │
├─────────────────────────────────────────────────────────────────┤
│                    External Integrations                        │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐ │
│  │ Fine-tuned  │    │   Pinecone   │    │     Parquet         │ │
│  │ DeepSeek-R1 │    │   Vector     │    │     Data            │ │
│  │ 70B Model   │    │   Database   │    │     Files           │ │
│  └─────────────┘    └──────────────┘    └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Core Design Principles

### 1. Enterprise-Grade Quality
- **Clean Architecture**: Clear separation of concerns with modular design
- **Professional Standards**: Comprehensive error handling, logging, and monitoring
- **Type Safety**: Full type annotations and validation
- **Documentation**: Extensive inline documentation and docstrings

### 2. Role-Based Security
- **Identity-Aware Processing**: User context flows through entire workflow
- **Permission Enforcement**: Role-based access control at every level
- **Data Scoping**: User-specific data filtering and access restrictions
- **Audit Trails**: Complete request tracking and logging

### 3. Hybrid Intelligence
- **RAG Integration**: Vector search for hockey domain knowledge
- **Real-Time Analytics**: Live statistical queries and calculations
- **Model Orchestration**: Fine-tuned model as central reasoning engine
- **Tool Coordination**: Intelligent sequencing and result integration

### 4. Production Readiness
- **Async Processing**: High-performance concurrent execution
- **Error Recovery**: Graceful degradation and fallback mechanisms
- **Monitoring**: Comprehensive metrics and health checks
- **Scalability**: Designed for horizontal scaling and load distribution

## Detailed Component Architecture

### 1. State Management (`utils/state.py`)

**Purpose**: Manages workflow state and data flow between nodes.

```python
class AgentState(TypedDict):
    # User context and query
    user_context: UserContext
    original_query: str
    query_type: QueryType
    
    # Processing state
    current_step: str
    iteration_count: int
    
    # Analysis and routing
    intent_analysis: Dict[str, Any]
    required_tools: List[ToolType]
    tool_sequence: List[str]
    
    # Tool execution results
    tool_results: Annotated[List[ToolResult], operator.add]
    
    # Data and context
    retrieved_context: List[Dict[str, Any]]
    analytics_data: Dict[str, Any]
    
    # Response generation
    evidence_chain: List[str]
    final_response: str
    
    # Metadata
    processing_time_ms: int
    error_messages: Annotated[List[str], operator.add]
    debug_info: Dict[str, Any]
```

**Key Features**:
- **Type Safety**: Comprehensive TypedDict definition
- **Immutable Operations**: Functional state updates
- **Evidence Tracking**: Complete audit trail of data sources
- **Error Management**: Centralized error collection and handling

### 2. Configuration Management (`config/settings.py`)

**Purpose**: Centralized configuration with validation and role-based permissions.

```python
class OrchestratorSettings:
    def __init__(self):
        self.model = ModelConfig()           # Model endpoints and parameters
        self.pinecone = PineconeConfig()     # Vector database configuration
        self.parquet = ParquetConfig()       # Analytics data configuration
        self.orchestration = OrchestrationConfig()  # Workflow settings
        
        # Role-based permissions matrix
        self.role_permissions = {
            UserRole.COACH: {
                "data_scope": ["team", "player", "game", "strategy"],
                "advanced_metrics": True,
                "opponent_data": True,
                "tactical_analysis": True
            },
            # ... other roles
        }
```

**Key Features**:
- **Environment Integration**: Automatic environment variable loading
- **Validation**: Comprehensive configuration validation
- **Role Matrix**: Detailed permission definitions for each user type
- **Extensibility**: Easy addition of new configuration parameters

### 3. Intent Analysis (`nodes/intent_analyzer.py`)

**Purpose**: Analyzes user queries to determine processing approach and required tools.

**Architecture**:
```python
class IntentAnalyzerNode:
    def __init__(self):
        # Pattern matching for query classification
        self.query_patterns = {
            QueryType.PLAYER_ANALYSIS: [patterns...],
            QueryType.TEAM_PERFORMANCE: [patterns...],
            # ... other types
        }
        
        # Tool requirement indicators
        self.tool_indicators = {
            ToolType.VECTOR_SEARCH: [patterns...],
            ToolType.PARQUET_QUERY: [patterns...],
            # ... other tools
        }
```

**Processing Flow**:
1. **Query Classification**: Pattern matching to determine query type
2. **Tool Identification**: Analyze query for required analytical tools
3. **Complexity Assessment**: Determine processing complexity level
4. **Context Requirements**: Identify need for hockey domain knowledge
5. **Data Requirements**: Determine analytical data needs

**Key Features**:
- **Pattern Recognition**: Sophisticated regex-based classification
- **Hockey-Specific**: Tailored for hockey terminology and concepts
- **Extensible**: Easy addition of new query types and patterns
- **Performance Optimized**: Efficient pattern matching algorithms

### 4. Smart Routing (`nodes/router.py`)

**Purpose**: Routes queries to appropriate tools with permission validation and execution sequencing.

**Architecture**:
```python
class RouterNode:
    def __init__(self):
        # Tool execution priorities
        self.tool_priorities = {
            ToolType.VECTOR_SEARCH: 1,      # Context first
            ToolType.PARQUET_QUERY: 2,      # Then data
            ToolType.CALCULATE_METRICS: 3,  # Then calculations
            ToolType.MATCHUP_ANALYSIS: 4,   # Then comparisons
            ToolType.VISUALIZATION: 5       # Finally visualizations
        }
```

**Processing Flow**:
1. **Permission Validation**: Check user permissions for requested tools
2. **Tool Filtering**: Remove unauthorized tools from execution plan
3. **Sequence Optimization**: Determine optimal execution order
4. **Approach Selection**: Choose processing strategy (single, parallel, multi-step)

**Execution Strategies**:
- **Single Tool**: Direct execution for simple queries
- **Context-First**: Prioritize domain knowledge retrieval
- **Multi-Step**: Complex sequential analysis
- **Parallel**: Concurrent tool execution (flagged, dependency-aware)

### 5. Pinecone Integration (`nodes/pinecone_retriever.py`)

**Purpose**: Retrieves relevant hockey context and domain knowledge from vector database.

**Architecture**:
```python
class PineconeRetrieverNode:
    def __init__(self):
        self.client = None
        self.index = None
        self._initialize_client()
    
    def _search_context(self, query, user_context, intent_analysis):
        # Query optimization for hockey domain
        optimized_query = self._optimize_query_for_hockey(query, intent_analysis)
        
        # Permission-based filtering
        search_filters = self._build_search_filters(user_context)
        
        # Relevance scoring and quality validation
        results = self._process_search_results(raw_results)
```

**Key Features**:
- **Query Optimization**: Hockey-specific query enhancement
- **Permission Filtering**: User-based content access control
- **Quality Validation**: Result relevance and content quality checks
- **Fallback Handling**: Graceful degradation when service unavailable
- **Caching**: Intelligent result caching for performance

### 6. Parquet Analytics (`nodes/parquet_analyzer.py`)

**Purpose**: Performs real-time analytics queries on structured hockey data.

**Architecture**:
```python
class ParquetAnalyzerNode:
    def __init__(self):
        self.data_directory = Path(settings.parquet.data_directory)
        self.cache = {} if settings.parquet.cache_enabled else None
        
        # Data file mapping
        self.data_files = {
            "player_stats": "fact/player_game_stats.parquet",
            "team_stats": "fact/team_game_stats.parquet",
            "play_by_play": "fact/play_by_play_events.parquet",
            # ... other data sources
        }
```

**Analysis Types**:
- **Player Performance**: Individual statistics and metrics
- **Team Analysis**: Team-level performance and comparisons
- **Game Analysis**: Event-level analysis and tactical insights
- **Matchup Analysis**: Comparative analysis and head-to-head metrics
- **Statistical Queries**: Direct statistical lookups and calculations

**Key Features**:
- **Data Validation**: Comprehensive data availability checking
- **Performance Optimization**: Efficient data loading and caching
- **Error Handling**: Graceful handling of missing or corrupted data
- **Extensibility**: Easy addition of new analysis types

### 7. Response Synthesis (`nodes/response_synthesizer.py`)

**Purpose**: Generates final responses using the fine-tuned model with integrated data.

**Architecture**:
```python
class ResponseSynthesizerNode:
    def __init__(self):
        self.model_config = settings.model
        
        # Role-specific response templates
        self.role_templates = {
            UserRole.COACH: {
                "system_prompt": "...",
                "style": "tactical_strategic",
                "focus": ["strategy", "matchups", "deployment"]
            },
            # ... other roles
        }
```

**Processing Flow**:
1. **Data Integration**: Combine RAG context with analytics data
2. **Prompt Construction**: Build comprehensive synthesis prompt
3. **Model Invocation**: Call fine-tuned model or fallback
4. **Response Processing**: Validate and format final response
5. **Citation Management**: Add source attribution and evidence chains

**Model Integration**:
- **Primary Model**: SageMaker endpoint for fine-tuned DeepSeek-R1-Distill-Qwen-32B
- **Fallback Model**: OpenAI API for development and testing
- **Template Fallback**: Static responses when models unavailable

## Data Flow Architecture

### Request Processing Flow

```
1. User Query Input
   ├── User Authentication & Context Creation
   └── Initial State Creation

2. Intent Analysis
   ├── Query Classification (Player/Team/Game/Tactical/Statistical)
   ├── Tool Requirement Analysis
   └── Complexity Assessment

3. Smart Routing
   ├── Permission Validation
   ├── Tool Filtering
   └── Execution Sequence Planning

4. Tool Execution
   ├── Pinecone RAG Retrieval (if required)
   │   ├── Query Optimization
   │   ├── Vector Search
   │   └── Result Processing
   │
   └── Parquet Analytics (if required)
       ├── Data Loading
       ├── Analysis Execution
       └── Result Formatting

5. Response Synthesis
   ├── Data Integration
   ├── Prompt Construction
   ├── Model Invocation
   └── Response Formatting

6. Final Response
   ├── Citation Management
   ├── Quality Validation
   └── User Delivery
```

### State Transitions

```
Initial State → Intent Analysis → Routing → Tool Execution → Synthesis → Complete

State Updates:
- current_step: Tracks processing stage
- iteration_count: Prevents infinite loops
- tool_results: Accumulates tool outputs
- evidence_chain: Builds citation trail
- error_messages: Collects any issues
- debug_info: Maintains processing metadata
```

## Security Architecture

### Role-Based Access Control

```python
# Permission Matrix
ROLE_PERMISSIONS = {
    UserRole.COACH: {
        "data_scope": ["team", "player", "game", "strategy"],
        "advanced_metrics": True,
        "opponent_data": True,
        "tactical_analysis": True
    },
    UserRole.PLAYER: {
        "data_scope": ["personal", "team", "game"],
        "advanced_metrics": True,
        "opponent_data": False,
        "tactical_analysis": False
    },
    # ... other roles
}
```

### Security Enforcement Points

1. **Router Level**: Tool access validation
2. **Data Level**: Query filtering and scoping
3. **Response Level**: Content filtering and sanitization
4. **Audit Level**: Complete request tracking

### Data Privacy

- **User Context Isolation**: Each request processed with specific user permissions
- **Data Scoping**: Automatic filtering based on user access rights
- **Audit Trails**: Complete logging of data access and usage
- **Secure Storage**: No persistent storage of user queries or responses

## Performance Architecture

### Optimization Strategies

1. **Async Processing**: Non-blocking I/O operations
2. **Intelligent Caching**: Result caching with TTL management
3. **Parallel Execution**: Concurrent tool execution where possible
4. **Memory Management**: Efficient data structure usage
5. **Connection Pooling**: Reuse of database connections

### Monitoring and Metrics

```python
# Performance Tracking
- Processing time per query
- Tool execution times
- Cache hit/miss ratios
- Error rates by component
- User query patterns
- Resource utilization
```

### Scalability Considerations

- **Horizontal Scaling**: Multiple orchestrator instances
- **Load Balancing**: Distributed query processing
- **Resource Isolation**: Component-level resource management
- **Circuit Breakers**: Prevent cascading failures

## Error Handling Architecture

### Error Categories

1. **Configuration Errors**: Missing API keys, invalid settings
2. **Network Errors**: Service unavailability, timeouts
3. **Data Errors**: Missing files, corrupted data
4. **Processing Errors**: Analysis failures, model errors
5. **Permission Errors**: Access denied, insufficient privileges

### Error Recovery Strategies

```python
# Fallback Hierarchy
1. Primary Service (e.g., SageMaker endpoint)
2. Secondary Service (e.g., OpenAI API)
3. Template Response (static fallback)
4. Error Response (graceful failure)
```

### Error Handling Features

- **Graceful Degradation**: Partial functionality when components fail
- **Retry Logic**: Automatic retry for transient failures
- **Circuit Breakers**: Prevent resource exhaustion
- **User-Friendly Messages**: Clear error communication

## Integration Architecture

### External System Integration

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SageMaker     │    │    Pinecone     │    │    Parquet      │
│   Endpoint      │    │    Vector DB    │    │    Data Files   │
│                 │    │                 │    │                 │
│ Fine-tuned      │    │ Hockey Domain   │    │ Statistical     │
│ DeepSeek-R1-Distill-Qwen-32B   │    │ Knowledge       │    │ Analytics       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   HeartBeat     │
                    │  Orchestrator   │
                    └─────────────────┘
```

### API Integration Points

1. **SageMaker Runtime**: Model inference endpoint
2. **Pinecone API**: Vector search and retrieval
3. **File System**: Parquet data access
4. **OpenAI API**: Fallback model access
5. **AWS Services**: Authentication and logging

## Future Architecture Enhancements

### Planned Improvements

1. **True Parallel Processing**: Concurrent tool execution
2. **Advanced Caching**: Multi-level caching strategy
3. **Real-Time Streaming**: Progressive response generation
4. **Model Ensembling**: Multiple model integration
5. **Advanced Analytics**: Machine learning insights

### Extensibility Points

1. **New Node Types**: Easy addition of processing nodes
2. **Custom Tools**: Plugin architecture for new capabilities
3. **Data Sources**: Additional data integration points
4. **Model Integration**: Support for multiple model types
5. **Output Formats**: Multiple response formats

---

**Technical Architecture Team**  
**HeartBeat Engine - Montreal Canadiens Analytics**  
Version 1.0.0
