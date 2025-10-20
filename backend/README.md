# HeartBeat Engine - FastAPI Backend

**API Gateway for Python ML/AI Backend**  
FastAPI wrapper around your existing Python orchestrator, maintaining all current functionality.

## 🏗️ Architecture

```
backend/
├── api/
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── query.py          # Main Stanley query endpoint
│   │   ├── analytics.py      # Direct analytics endpoints  
│   │   ├── players.py        # Player-specific endpoints
│   │   ├── teams.py          # Team analytics endpoints
│   │   └── auth.py           # Authentication routes
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py       # Pydantic request models
│   │   ├── responses.py      # Pydantic response models
│   │   └── hockey.py         # Hockey-specific data models
│   └── services/
│       ├── __init__.py
│       ├── orchestrator.py   # Wrapper for your orchestrator
│       ├── auth.py           # Authentication service
│       └── cache.py          # Response caching
├── main.py                   # FastAPI application entry point
├── config.py                 # Configuration settings
└── requirements.txt          # API-specific dependencies
```

## 🔗 Integration Strategy

### Your Existing Code (Unchanged)
```
HeartBeat/
├── orchestrator/            # Keep as-is
├── app/                     # Keep for internal use
├── data/                    # Keep all data processing
├── scripts/                 # Keep all scripts
└── sagemaker_training_src/  # Keep training code
```

### New FastAPI Layer (Thin Wrapper)
```python
# backend/api/services/orchestrator.py
from orchestrator.agents.heartbeat_orchestrator import HeartBeatOrchestrator
from orchestrator.config.settings import UserRole
from orchestrator.utils.state import UserContext

class OrchestrationService:
    def __init__(self):
        self.orchestrator = HeartBeatOrchestrator()
    
    async def process_query(self, query: str, user_role: str, user_id: str):
        user_context = UserContext(
            user_id=user_id,
            role=UserRole(user_role),
            name="Web User",
            team_access=["MTL"]
        )
        
        # Your existing orchestrator (no changes needed)
        return await self.orchestrator.process_query(
            query=query,
            user_context=user_context
        )
```

## 🚀 API Endpoints

### Core Query Endpoint
```
POST /api/v1/query
```
**Request:**
```json
{
  "query": "How is Suzuki performing this season?",
  "user_role": "coach",
  "user_id": "coach_martin",
  "team_access": ["MTL"]
}
```

**Response:**
```json
{
  "success": true,
  "response": "Based on current season data...",
  "tool_results": [...],
  "processing_time_ms": 1250,
  "evidence": [...],
  "visualizations": [...]
}
```

### Direct Analytics Endpoints
```
GET  /api/v1/players/{player_id}/stats
GET  /api/v1/teams/MTL/analytics  
GET  /api/v1/games/{game_id}/analysis
POST /api/v1/compare/players
POST /api/v1/visualizations/shot-map
```

### Streaming Endpoint (for real-time responses)
```
POST /api/v1/query/stream
Content-Type: text/event-stream
```

## 🔒 Authentication Integration

### Role-Based Access
```python
# backend/api/models/requests.py
from pydantic import BaseModel
from enum import Enum

class UserRole(str, Enum):
    COACH = "coach"
    PLAYER = "player" 
    ANALYST = "analyst"
    SCOUT = "scout"
    STAFF = "staff"

class QueryRequest(BaseModel):
    query: str
    user_role: UserRole = UserRole.ANALYST
    user_id: str
    team_access: list[str] = ["MTL"]
```

### Middleware
```python
# backend/api/middleware/auth.py
async def verify_user_role(request: Request):
    # Integrate with your existing auth system
    # Return user context for orchestrator
    pass
```

## 📊 Response Models

### Standardized Response Format
```python
# backend/api/models/responses.py
from pydantic import BaseModel
from typing import List, Optional, Any

class ToolResult(BaseModel):
    tool: str
    success: bool
    data: Optional[Any] = None
    processing_time_ms: int

class QueryResponse(BaseModel):
    success: bool
    response: str
    tool_results: List[ToolResult]
    processing_time_ms: int
    evidence: List[str] = []
    visualizations: List[dict] = []
    user_role: str
    query_type: Optional[str] = None
```

## 🚄 Performance Features

### Response Caching
```python
# backend/api/services/cache.py
from functools import lru_cache
import redis

class ResponseCache:
    def __init__(self):
        self.redis_client = redis.Redis()
    
    async def get_cached_response(self, query_hash: str):
        # Cache frequent queries for faster responses
        pass
```

### Streaming Responses
```python
# backend/api/routes/query.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

@app.post("/api/v1/query/stream")
async def stream_query(request: QueryRequest):
    async def generate_response():
        # Stream tokens as they're generated
        async for token in orchestrator.stream_query(request.query):
            yield f"data: {token}\n\n"
    
    return StreamingResponse(generate_response(), media_type="text/event-stream")
```

## 🔧 Development Setup

### Installation
```bash
cd backend
pip install fastapi uvicorn python-multipart redis
```

### Environment Variables
```bash
# .env
FASTAPI_ENV=development
REDIS_URL=redis://localhost:6379
CORS_ORIGINS=http://localhost:3000
```

### Run Development Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📡 CORS Configuration

### Frontend Integration
```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🧪 Testing

### API Testing
```python
# backend/tests/test_query.py
import pytest
from fastapi.testclient import TestClient

def test_query_endpoint():
    response = client.post("/api/v1/query", json={
        "query": "How is Suzuki performing?",
        "user_role": "coach"
    })
    assert response.status_code == 200
    assert "success" in response.json()
```

---

## Benefits of This Architecture

1. **Zero Changes to Existing Code**: Your Python orchestrator, data processing, and ML code stays exactly the same
2. **Modern API**: RESTful endpoints with automatic OpenAPI documentation
3. **Type Safety**: Pydantic models ensure data validation
4. **Performance**: Caching, streaming, and async support
5. **Scalability**: Easy to add new endpoints and features
6. **Frontend Flexibility**: Next.js frontend can consume clean, typed APIs

**Your existing Python backend becomes a world-class API with minimal effort.**
