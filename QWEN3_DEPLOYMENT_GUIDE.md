# Qwen3-Next-80B Thinking Deployment Guide

## Current Status: Model Found! 

You've successfully located **Qwen3-Next-80B-A3B-Thinking MaaS** in Vertex AI Model Garden.

**URL**: https://console.cloud.google.com/vertex-ai/publishers/qwen/model-garden/qwen3-next-80b-a3b-thinking-maas?hl=en&project=heartbeat-474020

## Deployment Options

### Option 1: MaaS (Model-as-a-Service) - RECOMMENDED 

**Advantages:**
- No infrastructure management
- Pay per million tokens (cost-efficient)
- Instant availability via API
- Auto-scaling built-in
- Perfect for development and production

**Pricing:** Billed per million tokens (check pricing page for current rates)

### Option 2: Dedicated Endpoint

**Advantages:**
- Lower latency for high-volume use
- Predictable per-hour pricing
- More control over hardware

**Requirements:**
- Machine type: `g2-standard-12`
- Accelerator: NVIDIA L4 (1x)
- Higher baseline cost

## Quick Start: Enable MaaS API (5 minutes)

### Step 1: Enable the API

On the Model Garden page you're currently viewing:

1. **Click the blue "Enable" button**
2. Accept the EULA if prompted
3. Wait 30-60 seconds for activation

### Step 2: Test the Integration

After enabling, run our integration test:

```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat
source venv/bin/activate
python3 orchestrator/qwen3_thinking_integration.py
```

**Expected Output:**
```
================================================================================
HEARTBEAT ENGINE - QWEN3 THINKING TEST
================================================================================

✓ Initialized Qwen3-Next-80B Thinking
  Project: heartbeat-474020
  Location: us-central1
  Model: qwen/qwen3-next-80b-a3b-thinking

[Test Query]
Query: How effective was Montreal's power play against Toronto in the 3rd period?

[Qwen3 Response]

Thinking/Planning:
[Model's reasoning process about which tools to use]

Function Calls Requested: 2
  - search_hockey_knowledge
    Args: {
      "query": "Montreal power play statistics Toronto 3rd period"
    }
  - query_game_data
    Args: {
      "sql_query": "SELECT ... WHERE team='MTL' AND opponent='TOR' AND period=3"
    }

================================================================================
TEST SUCCESSFUL
================================================================================
```

### Step 3: Verify API Access

You can also test via gcloud CLI (after enabling):

```bash
# List available models
gcloud ai models list --region=us-central1 --project=heartbeat-474020

# Or use curl to test the endpoint
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://us-central1-aiplatform.googleapis.com/v1/projects/heartbeat-474020/locations/us-central1/publishers/qwen/models/qwen3-next-80b-a3b-thinking:predict" \
  -d '{"instances": [{"prompt": "What is hockey?"}]}'
```

## Integration Architecture

### HeartBeat Engine Flow

```
User Query
    ↓
Qwen3-Next-80B Thinking (Intent Analysis)
    ↓
Multi-Step Planning & Tool Selection
    ↓
Function Calls (Strict JSON)
    ├── search_hockey_knowledge() → Pinecone RAG
    ├── query_game_data() → Parquet SQL
    ├── calculate_hockey_metrics() → Advanced stats
    └── generate_visualization() → Chart specs
    ↓
Execute Tools → Return Results
    ↓
Qwen3-Next-80B Thinking (Synthesis)
    ↓
Evidence-Based Response
```

### Function Calling Tools Implemented

✅ **1. search_hockey_knowledge**
- Searches Pinecone RAG for hockey context
- Returns relevant chunks about tactics, strategies, concepts

✅ **2. query_game_data**
- Executes SQL on Parquet game statistics  
- Returns real-time MTL performance data

✅ **3. calculate_hockey_metrics**
- Computes Corsi, xG, zone analysis, possession
- Returns advanced analytics

✅ **4. generate_visualization**
- Creates shot maps, heatmaps, charts
- Can delegate to Qwen3-VL for visual rendering

## Cost Estimation

### MaaS Pricing Model

**Typical Query Cost:**
- Input: ~500 tokens (query + tools + context)
- Output: ~1000 tokens (reasoning + function calls + response)
- **Total per query**: ~1,500 tokens

**Monthly Estimates (varies by pricing):**
- 1,000 queries/month: Low cost
- 10,000 queries/month: Moderate cost
- 100,000 queries/month: Production-scale cost

**MoE Efficiency:** Only subset of 80B parameters activate per token, significantly reducing costs vs dense models.

## Next Steps After Enabling

### 1. Test Basic Connectivity
```bash
python3 orchestrator/qwen3_thinking_integration.py
```

### 2. Implement Tool Executors
Create functions to actually execute the tool calls:
- Connect to Pinecone for RAG searches
- Query Parquet files for game data
- Calculate advanced metrics
- Generate visualizations

### 3. Integrate with LangGraph
Connect Qwen3 Thinking to your LangGraph orchestrator nodes:
- Intent Analysis Node
- Router Node  
- Tool Execution Nodes
- Synthesis Node

### 4. Add Qwen3-VL (Vision)
Deploy Qwen3-VL for visual analysis tasks:
- Shot map generation
- Formation diagrams
- Video frame analysis

### 5. Production Optimization
- Set up monitoring and logging
- Configure rate limits
- Implement caching strategies
- Add error handling and retries

## Troubleshooting

### Issue: "Model not found"
**Solution:** Wait 30-60 seconds after clicking "Enable" for API activation

### Issue: "Permission denied"
**Solution:** 
```bash
gcloud projects add-iam-policy-binding heartbeat-474020 \
  --member="user:xabouch@gmail.com" \
  --role="roles/aiplatform.user"
```

### Issue: "Quota exceeded"
**Solution:** Request quota increase in Cloud Console → IAM & Admin → Quotas

### Issue: "Billing not enabled"
**Solution:** Enable billing for project at console.cloud.google.com/billing

## Resources

- **Model Documentation**: Check Model Garden page for latest docs
- **Vertex AI Python SDK**: https://cloud.google.com/python/docs/reference/aiplatform/latest
- **Function Calling Guide**: https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/function-calling
- **HeartBeat Setup**: See `VERTEX_AI_SETUP.md`

---

**Ready to enable?** Click that blue "Enable" button and let's test it! 🚀

