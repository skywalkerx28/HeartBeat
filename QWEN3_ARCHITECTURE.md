# Qwen3 Integration Architecture - HeartBeat Engine

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          HEARTBEAT ENGINE                               │
│                     Montreal Canadiens Analytics                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
            ┌───────▼────────┐            ┌────────▼────────┐
            │  Classic Mode  │            │   Qwen3 Mode    │
            │  (Original)    │            │  (NEW - Active) │
            └───────┬────────┘            └────────┬────────┘
                    │                               │
                    │                               │
        ┌───────────▼──────────────┐    ┌──────────▼──────────────┐
        │ HeartBeat Orchestrator   │    │ HeartBeatQwen3          │
        │                          │    │ Orchestrator            │
        │ • Traditional routing    │    │                         │
        │ • Fixed workflow         │    │ • Qwen3 reasoning       │
        │ • Rule-based decisions   │    │ • Dynamic planning      |
        └───────────┬──────────────┘    │ • Sequential tools      │
                    │                   └──────────┬──────────────┘
                    │                               │
                    │                   ┌───────────▼──────────────┐
                    │                   │ Qwen3ToolCoordinator     │
                    │                   │                          │
                    │                   │ • Intent analysis        │
                    │                   │ • Tool sequencing        │
                    │                   │ • Response synthesis     │
                    │                   └───────────┬──────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │   SHARED INFRASTRUCTURE        │
                    └────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
    ┌───────▼────────┐    ┌────────▼────────┐    ┌───────▼────────┐
    │ Pinecone RAG   │    │ Parquet         │    │ Video Clips    │
    │                │    │ Analytics       │    │                │
    │ • Knowledge    │    │ • Game stats    │    │ • Play footage │
    │ • Context      │    │ • Metrics       │    │ • Analysis     │
    │ • Tactics      │    │ • Queries       │    │                │
    └────────────────┘    └─────────────────┘    └────────────────┘
```

## Qwen3 Sequential Tool Execution Flow

```
USER QUERY: "How effective was Montreal's power play against Toronto?"
     │
     ├─────────────────────────────────────────────────────────────────┐
     │                    Qwen3 Orchestrator                           │
     └─────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │  STEP 1: Intent Analysis        │
                    │  (Qwen3-Next-80B Thinking)      │
                    └───────────────┬────────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  │ Analysis Result:                   │
                  │ • Type: Tactical Analysis          │
                  │ • Needs: Context + Statistics      │
                  │ • First Tool: search_knowledge     │
                  └─────────────────┬─────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │  STEP 2: Tool Execution         │
                    │  (Sequential, one at a time)    │
                    └───────────────┬────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼────────┐         ┌────────▼────────┐       ┌────────▼────────┐
│ Iteration 1    │         │ Iteration 2     │       │ Iteration 3     │
│                │         │                 │       │                 │
│ Qwen3 Requests:│         │ Qwen3 Requests: │       │ Qwen3 Decides:  │
│ search_        │──────▶  │ query_          │──────▶│ Sufficient      │
│ knowledge      │         │ game_data       │       │ data gathered   │
│                │         │                 │       │                 │
│ Executor runs  │         │ Executor runs   │       │ No more tools   │
│ Pinecone       │         │ Parquet query   │       │                 │
│                │         │                 │       │                 │
│ Returns:       │         │ Returns:        │       │                 │
│ • Tactics      │         │ • PP stats      │       │                 │
│ • Context      │         │ • Goals/60      │       │                 │
└────────┬───────┘         └────────┬────────┘       └────────┬────────┘
         │                          │                         │
         └──────────────────────────┴─────────────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │  STEP 3: Response Synthesis     │
                    │  (Qwen3-Next-80B Thinking)      │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────▼────────────────-┐
                    │  FINAL RESPONSE                 │
                    │                                 │
                    │  "Montreal's power play against │
                    │  Toronto has been effective with│
                    │  a 23.5% success rate (above    │
                    │  league average of 20.1%). Key  │
                    │  factors include..."            │
                    │                                 │
                    │  Evidence:                      │
                    │  • PP goal data (game stats)    │
                    │  • Historical context (RAG)     │
                    │  • Strategic analysis           │
                    └─────────────────────────────────┘
```

## Component Interaction Detail

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    QWEN3 TOOL COORDINATOR                               │
│                  (agents/qwen3_coordinator.py)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼────────┐         ┌────────▼────────┐       ┌────────▼────────┐
│ analyze_intent │         │ execute_tool_   │       │ synthesize_     │
│                │         │ sequence        │       │ response        │
│ • Parse query  │         │                 │       │                 │
│ • Classify type│         │ • Multi-turn    │       │ • Combine data  │
│ • Plan tools   │────────▶│ • One tool/turn │──────▶│ • Generate resp │
│                │         │ • Result gather │       │ • Add evidence  │
└────────────────┘         └────────┬────────┘       └─────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │  _execute_single_tool           │
                    │                                 │
                    │  Maps function calls to nodes:  │
                    └─────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼────────────┐     ┌────────▼────────────┐   ┌────────▼────────┐
│ search_hockey_     │     │ query_game_data     │   │ calculate_      │
│ knowledge          │     │                     │   │ metrics         │
│ ↓                  │     │ ↓                   │   │ ↓               │
│ Pinecone           │     │ Parquet             │   │ Parquet         │
│ RetrieverNode      │     │ AnalyzerNode        │   │ AnalyzerNode    │
└────────────────────┘     └─────────────────────┘   └─────────────────┘
```

## State Management (LangGraph Integration)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AgentState                                    
│                    (utils/state.py - Unchanged)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  user_context: UserContext        # Who is asking                       │
│  original_query: str              # The question                        │
│  query_type: QueryType            # Classification                      │
│                                                                         │
│  required_tools: List[ToolType]   # What tools needed                   │
│  tool_results: List[ToolResult]   # Results gathered                    │
│                                                                         │
│  intent_analysis: Dict            # Qwen3 reasoning                     │
│  evidence_chain: List[str]        # Citations                           │
│  final_response: str              # Answer                              │
│                                                                         │
│  iteration_count: int             # Tool loops                          │
│  processing_time_ms: int          # Performance                         │
│  error_messages: List[str]        # Issues                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Flows through all nodes
                                    │
                    ┌───────────────▼────────────────┐
                    │   All nodes read/write state   │
                    │   Maintains full compatibility │
                    └────────────────────────────────┘
```

## Vertex AI Integration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GOOGLE CLOUD VERTEX AI                               │
│                      Project: heartbeat-474020                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼────────────┐     ┌────────▼────────────┐   ┌────────▼────────┐
│ Qwen3-Next-80B     │     │ Qwen3-VL            │   │ Model Garden    │
│ Thinking MaaS      │     │ (Future)            │   │                 │
│                    │     │                     │   │ • Discovery     │
│ • Reasoning        │     │ • Shot maps         │   │ • Deployment    │
│ • Planning         │     │ • Formations        │   │ • Management    │
│ • Function calling │     │ • Video frames      │   │                 │
│                    │     │                     │   │                 │
│ Location: global   │     │ Location: global    │   │                 │
│ Billing: Per token │     │ Billing: Per token  │   │                 │
└────────────────────┘     └─────────────────────┘   └─────────────────┘
```

## Data Flow Summary

```
1. USER → Query + Context
          ↓
2. QWEN3 ORCHESTRATOR → Routes to Qwen3 mode
          ↓
3. INTENT ANALYSIS → Qwen3 classifies and plans
          ↓
4. TOOL SEQUENCE → Execute tools one by one
          ├→ Pinecone RAG → Hockey context
          ├→ Parquet SQL → Game statistics
          └→ Calculate → Advanced metrics
          ↓
5. SYNTHESIS → Qwen3 combines all data
          ↓
6. RESPONSE → Professional hockey analysis
          ↓
7. USER ← Answer + Evidence + Metrics
```

## Key Design Decisions

### 1. Sequential Tool Execution

**Why?** Qwen3 MaaS limitation: One function declaration at a time.

**Benefit:** Forces step-by-step reasoning, improves quality.

Parallel Enhancement (Flagged)
- We now support bounded parallel execution of independent tools (e.g., `search_hockey_knowledge`, `query_game_data`, roster lookups) within a single model turn.
- Controlled via `settings.orchestration.enable_parallel_tools` with `max_parallel_tools` and `tool_timeout_seconds` guardrails.
- Dependency-aware: calculations/visualizations run after data tools complete; falls back to sequential on errors.

Declarative Tool Metadata & Scheduling
- Each tool now has a `ToolSpec` (name, consumes, produces, parallel_ok, resource_group, timeout) defined in `orchestrator/agents/tool_registry.py`.
- The orchestrator builds a DAG per turn from the requested function calls using `consumes/produces` tags and prior state (already-satisfied data).
- Batches of independent tools run in parallel; dependent tools execute in the next batch(s). Ordering is deterministic when merging outputs and citations.

### 2. Dual Orchestrator

**Why?** Maintain backward compatibility and flexibility.

**Benefit:** Can switch modes, A/B test, fallback options.

### 3. Shared Infrastructure

**Why?** Reuse existing nodes and tools.

**Benefit:** Minimal code changes, faster deployment.

### 4. State Compatibility

**Why?** Keep existing `AgentState` structure.

**Benefit:** Works with all existing code and monitoring.

## Performance Characteristics

```
┌──────────────────────┬──────────────┬──────────────┬──────────────┐
│ Component            │ Typical Time │ Token Cost   │ Bottleneck   │
├──────────────────────┼──────────────┼──────────────┼──────────────┤
│ Intent Analysis      │ 200-400ms    │ ~300 tokens  │ API latency  │
│ Tool Execution (1x)  │ 200-600ms    │ ~150 tokens  │ Node speed   │
│ Tool Execution (3x)  │ 600-1800ms   │ ~450 tokens  │ Node speed   │
│ Response Synthesis   │ 400-800ms    │ ~600 tokens  │ API latency  │
├──────────────────────┼──────────────┼──────────────┼──────────────┤
│ TOTAL (Simple)       │ 800-1800ms   │ ~1050 tokens │              │
│ TOTAL (Complex)      │ 1400-3000ms  │ ~1500 tokens │              │
└──────────────────────┴──────────────┴──────────────┴──────────────┘
```

## Security & Access Control

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        USER CONTEXT                                      │
│                  (Flows through all operations)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  user_id: str            # Identity                                     │
│  role: UserRole          # Permission level                             │
│  team_access: List[str]  # Data scope (e.g., ["MTL"])                   │
│                                                                          │
│  Enforced at:                                                           │
│  • Query intake                                                         │
│  • Tool execution (data filtering)                                      │
│  • Response generation (role-appropriate language)                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

**Architecture Status**: **COMPLETE**

**Integration**: **PRODUCTION READY**

**Documentation**: **COMPREHENSIVE**

**Next Step**: Deploy to FastAPI backend and test with live data

---

## Recent Progress: Reasoning–Tool Duality (Qwen3)

We have established a durable duality between Qwen3’s autonomous reasoning and our orchestrator’s guided tool use for advanced hockey analysis. This balance is now the default mode for complex questions and has materially improved precision, evidence coverage, and reliability.

- Model-first planning, orchestrator guardrails: The model plans and requests tools; we constrain the surface to typed, domain-safe tools and deterministic parameters.
- Sequential execution by design: Qwen3 MaaS supports one function per turn; our coordinator manages a multi-turn plan → execute → verify → synthesize loop.
- Hockey-specialized toolchain: Parquet analytics for real statistics, Pinecone RAG for domain context, with state-carrying citations to ground analysis.
- Observed improvements: Higher accuracy on special teams (PP/PK) queries, opponent matchups, and zone-entry/exit breakdowns; reduced hallucinations via evidence gating and explicit citations.

Reference implementation:
- `orchestrator/agents/qwen3_coordinator.py` (production coordinator)
- `orchestrator/agents/qwen3_best_practices_orchestrator.py` (full best-practice pattern, all tools visible to the model)
- Nodes and tools: `orchestrator/nodes/{pinecone_retriever,parquet_analyzer}.py`, `orchestrator/tools/*`

Example (end-to-end): “How effective was Montreal’s power play vs Toronto?”
- Intent → classify as team PP vs opponent
- Tools → `query_game_data` for PP events/stats; optional `calculate_metrics` for xGF/60; `search_hockey_knowledge` for tactical context
- Synthesis → sample-size guardrails, explicit numbers with units, citations `[source:category]`

Last Updated: 2025-10-08

## Canonical Tooling Surface (for models)

These are the canonical function names exposed to Qwen3. Use exactly as named; do not invent parameters. Some code paths may reference `calculate_hockey_metrics`—treat it as an alias of `calculate_metrics` in future updates.

- `search_hockey_knowledge`: Retrieve hockey concepts, tactics, rules, and definitions.
- `query_game_data`: Query Montreal statistics and play-by-play from Parquet-backed analytics.
- `calculate_metrics`: Compute advanced metrics (e.g., Corsi, xG, zone entries/exits, per-60 rates) when required.
- `generate_visualization` (planned): Shot maps, heatmaps, charts.

Constraints and guidelines:
- One function call per turn (Qwen3 MaaS). Plan sequentially.
- Prefer the minimal toolset to answer the question completely.
- Check preconditions (season/opponent) and reuse state to avoid redundant calls.
- Honor timeouts/backoff; keep arguments deterministic and schema-valid.

## State-of-the-Art Standards (Reasoning, Tools, Agents)

Reasoning standards
- Plan briefly (1–3 steps) before acting; do not expose internal chain-of-thought to users.
- Prefer data over prior knowledge when both exist; verify every numeric claim against tool outputs.
- Always include citations when tools are used; avoid unsupported claims.
- Stop once sufficient evidence is gathered; avoid unnecessary tool calls.

Tool usage standards
- Single-call constraint: plan → call → verify → repeat as needed.
- Parameter hygiene: only documented fields, correct types, stable units.
- Determinism: avoid randomness; identical inputs produce identical outputs.
- Evidence-first: prefer `parquet_analyzer` for stats; use Pinecone for definitions and context, not numbers.
- Budgeting: bounded iterations (≤15), explicit timeouts, and early exit on sufficiency.

Agent/orchestrator standards
- Coordinator controls flow; model selects tools. We enforce role boundaries: retrieval vs analytics vs synthesis.
- Separation of concerns: `Qwen3ToolCoordinator` (today) and `Qwen3BestPracticesOrchestrator` (target) keep tool selection autonomous while preserving typed contracts.
- Output contract: numeric results with units, short methodology, citations, and hockey-appropriate tone.
- Safety posture: no speculative claims; request clarification only when essential inputs are missing.

## Training & Finetuning Best Practices (Alignment with Top AI Standards)

Data and governance
- Curate domain SFT datasets from internal, licensed hockey analytics content; strip PII and respect licenses.
- Include tool traces (inputs/outputs) to teach function calling and evidence grounding.
- Maintain clean train/dev/test splits; keep a frozen holdout for regression.

Methods
- Prefer parameter-efficient finetuning (LoRA/PEFT) over full weights, especially for tool-use and output style.
- Use SFT for behavior and schema adherence; optionally add preference tuning (e.g., DPO/RLHF) focusing on evidence-grounded answers and numeric accuracy.
- Do not train on user data without consent; document data lineage and approvals.

Evaluation
- Build an offline eval suite for hockey questions spanning: PP/PK efficiency, opponent matchups, zone entries/exits, player comp, temporal queries.
- Metrics: exactness on categorical fields, numeric tolerance (e.g., ±0.5% absolute for rates), evidence coverage, citation validity, latency, tool count, and token cost.
- Run evals pre/post finetune; gate deployment on non-regression thresholds.

Deployment
- Canary releases with logs on tool usage, error rates, and numeric deltas vs ground truth.
- Rollback plan; maintain model and prompt versioning.

Related docs: `MATHEMATICAL_ACCURACY_SYSTEM.md`, `HEARTBEAT_ENGINE_ROADMAP.md`

## Hockey Advanced QA Playbook (Tool Sequencing)

Use these default sequences; adapt as needed to minimize calls while ensuring completeness.

- Power play vs specific opponent
  - `query_game_data` (PP events/stats by opponent, season)
  - `calculate_metrics` (xGF/60, PP% if not returned)
  - `search_hockey_knowledge` (definitions/tactics as needed)

- Zone entries/exits (last 10 games)
  - `query_game_data` (filtered by timeframe and events)
  - `calculate_metrics` (entry/exit success, controlled entries, turnovers)
  - Optional knowledge retrieval for definitions only

- Player vs opponent matchup
  - `query_game_data` (on-ice metrics vs opponent; TOI for sample-size context)
  - Optional `search_hockey_knowledge` for matchup concepts

- Last-change rotations / TOI patterns
  - `query_game_data` (line combos, deployment, shift starts)
  - `calculate_metrics` (rates per 60, situational usage)

Expected synthesis
- Provide explicit numbers with units and timeframe; call out sample size when small.
- Include 1–3 citations `[source:category]`; summarize method briefly.
- Maintain professional coaching/analytics tone (no emojis).

## Development Guardrails (For Future Improvements)

- Consistency: If adding tools, register canonical names here and align schemas across backend and prompts.
- Minimal prompts for function calling: rely on typed schemas; avoid verbose instructions that trigger safety filters.
- Observability: Log tool parameters, execution time, and citation sets; never log raw PII.
- Regression safety: Changes to prompts, tools, or finetuning must pass the offline eval suite before release.

## Versioning & Ownership

- This file is the canonical AI context for reasoning, tool use, agent behavior, and training standards. Update alongside any orchestrator/tool changes.
- Owners: Orchestrator team. Keep in sync with `orchestrator/ARCHITECTURE.md`, API references, and related system docs.
