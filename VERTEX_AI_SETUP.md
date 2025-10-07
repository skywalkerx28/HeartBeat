# Vertex AI Setup Guide for HeartBeat Engine

## Architecture Overview

HeartBeat Engine uses a **dual-model architecture** on Google Cloud Vertex AI:

- **Primary Reasoning**: Qwen3-Next-80B Thinking (MoE, function calling, tool orchestration)
- **Vision Specialist**: Qwen3-VL (on-demand for shot maps, formations, video frames)

## Current Setup Status

### Completed:
- ✅ Google Cloud CLI installed
- ✅ Project configured: `heartbeat-474020`
- ✅ Vertex AI Python client library installed
- ✅ Connection test script created

### Pending Authentication:

**REQUIRED ACTION**: You must complete authentication before proceeding.

## Step-by-Step Authentication

### 1. Authenticate with Application Default Credentials

Run this command in your terminal:

```bash
gcloud auth application-default login
```

**What this does:**
- Opens your browser
- Asks you to sign in with **xabouch@gmail.com**
- Grants permissions for programmatic access
- Stores credentials in `~/.config/gcloud/application_default_credentials.json`

### 2. Enable Vertex AI API

```bash
gcloud services enable aiplatform.googleapis.com --project=heartbeat-474020
```

### 3. Set IAM Permissions

Ensure your account has these roles:
```bash
gcloud projects add-iam-policy-binding heartbeat-474020 \
  --member="user:xabouch@gmail.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding heartbeat-474020 \
  --member="user:xabouch@gmail.com" \
  --role="roles/aiplatform.admin"
```

### 4. Test the Connection

```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat
source venv/bin/activate
python orchestrator/vertex_ai_connection_test.py
```

Expected output:
```
================================================================================
HEARTBEAT ENGINE - VERTEX AI CONNECTION TEST
================================================================================

[1] Initializing Vertex AI...
✓ Successfully initialized Vertex AI
  - Project ID: heartbeat-474020
  - Location: us-central1

[2] Checking authentication...
✓ Authentication successful
  - Authenticated project: heartbeat-474020

[3] Exploring Model Garden...
...

CONNECTION TEST: SUCCESS
```

## Model Deployment Strategy

### Phase 1: Model Garden Access (NEXT)

1. **Navigate to Vertex AI Model Garden:**
   - https://console.cloud.google.com/vertex-ai/model-garden?project=heartbeat-474020

2. **Deploy Qwen3-Next-80B Thinking:**
   - Search for "Qwen3-Next-80B Thinking" in Model Garden
   - Click "Deploy" or "Enable API"
   - Configure:
     - Region: `us-central1`
     - Machine type: Based on quota and cost requirements
     - Scaling: Auto-scaling with min/max instances

3. **Deploy Qwen3-VL (On-Demand):**
   - Search for "Qwen3-VL" in Model Garden
   - Configure for on-demand usage (can start with minimal deployment)
   - Set up for cold-start optimization

### Phase 2: Endpoint Configuration

```python
# Example endpoint configuration
from google.cloud import aiplatform

# Initialize
aiplatform.init(project="heartbeat-474020", location="us-central1")

# Create endpoint for Qwen3-Next-80B Thinking
thinking_endpoint = aiplatform.Endpoint.create(
    display_name="heartbeat-qwen3-thinking-endpoint",
    description="Core reasoning engine for HeartBeat hockey analytics"
)

# Create endpoint for Qwen3-VL
vision_endpoint = aiplatform.Endpoint.create(
    display_name="heartbeat-qwen3-vision-endpoint",
    description="On-demand vision processing for shot maps and formations"
)
```

### Phase 3: Function Calling Setup

Define tool schemas for hockey analytics:

```python
# Example function schema for Pinecone search
pinecone_search_schema = {
    "name": "search_hockey_knowledge",
    "description": "Search hockey context and historical knowledge from Pinecone RAG system",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query for hockey context"},
            "top_k": {"type": "integer", "description": "Number of results to return"},
            "filters": {"type": "object", "description": "Optional metadata filters"}
        },
        "required": ["query"]
    }
}

# Example function schema for Parquet queries
parquet_query_schema = {
    "name": "query_game_data",
    "description": "Execute SQL query on MTL game statistics Parquet files",
    "parameters": {
        "type": "object",
        "properties": {
            "sql_query": {"type": "string", "description": "SQL query to execute"},
            "filters": {"type": "object", "description": "Additional filters"}
        },
        "required": ["sql_query"]
    }
}
```

## Cost Optimization Strategy

### MoE Efficiency
- Qwen3-Next-80B Thinking uses Mixture-of-Experts
- Only subset of 80B parameters activate per token
- Cost per token is significantly lower than dense 80B models

### Vision Model Usage
- Qwen3-VL invoked **only when necessary**
- Text-only queries: 0% vision cost
- Visual analysis queries: Selective activation
- Estimated 5-10% of queries require vision

### Quota Management
- Set up budget alerts in Google Cloud Console
- Configure quota limits per endpoint
- Monitor usage via Cloud Monitoring

## Integration with LangGraph

### Architecture Flow

```
User Query
    ↓
LangGraph Orchestrator
    ↓
Intent Analysis Node (Qwen3-Next-80B)
    ↓
Router Node (determines RAG/Parquet/Vision needs)
    ↓
Tool Execution Nodes
    ├── Pinecone Search
    ├── Parquet SQL Query
    ├── Analytics Calculation
    └── Vision Delegate (conditional → Qwen3-VL)
    ↓
Synthesis Node (Qwen3-Next-80B)
    ↓
Response with Evidence
```

### Example Integration Code

```python
from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel, Tool

# Initialize models
thinking_model = GenerativeModel("qwen3-next-80b-thinking")
vision_model = GenerativeModel("qwen3-vl")

# Define tools for function calling
tools = [
    Tool(function_declarations=[
        pinecone_search_schema,
        parquet_query_schema,
        # ... other tools
    ])
]

# Query with function calling
response = thinking_model.generate_content(
    "How effective was Montreal's power play against Toronto in 3rd periods?",
    tools=tools,
    generation_config={"temperature": 0.2, "max_output_tokens": 2048}
)

# Process function calls
for candidate in response.candidates:
    for part in candidate.content.parts:
        if hasattr(part, 'function_call'):
            # Execute the tool
            result = execute_tool(part.function_call)
            # Continue conversation with result
```

## Next Steps

1. **Complete authentication** (see above)
2. **Run connection test** to verify setup
3. **Deploy models** from Model Garden
4. **Configure endpoints** for both models
5. **Test function calling** with sample queries
6. **Integrate with LangGraph** orchestrator
7. **Set up monitoring** and cost tracking

## Troubleshooting

### Common Issues

**Issue**: "You do not currently have an active account selected"
- **Solution**: Run `gcloud auth application-default login`

**Issue**: "Permission denied on Vertex AI API"
- **Solution**: Enable API and check IAM roles (see Step 2 & 3 above)

**Issue**: "Model not found in Model Garden"
- **Solution**: Qwen models may need to be enabled via MaaS (Model-as-a-Service). Check Model Garden catalog.

**Issue**: "Quota exceeded"
- **Solution**: Request quota increase in Google Cloud Console → IAM & Admin → Quotas

## Useful Commands

```bash
# Check current configuration
gcloud config list

# List enabled APIs
gcloud services list --enabled --project=heartbeat-474020

# List available models
gcloud ai models list --region=us-central1 --project=heartbeat-474020

# List endpoints
gcloud ai endpoints list --region=us-central1 --project=heartbeat-474020

# Check IAM permissions
gcloud projects get-iam-policy heartbeat-474020 \
  --flatten="bindings[].members" \
  --filter="bindings.members:xabouch@gmail.com"
```

## Resources

- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Qwen3 Model Documentation](https://huggingface.co/Qwen)
- [Function Calling Guide](https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/function-calling)
- [Model Garden](https://console.cloud.google.com/vertex-ai/model-garden?project=heartbeat-474020)

---

**Status**: Ready for authentication. Complete steps 1-4 above, then we can proceed with model deployment.

