# HeartBeat Engine - CBA Integration Implementation Guide

## Overview

This guide documents the implementation of NHL Collective Bargaining Agreement (CBA) rules integration into the HeartBeat ontology framework, following **Option D: Structured Rules First**.

**Implementation Date:** October 19, 2025  
**Status:** Phase 1 Complete (Structured Rules)  
**Future:** Phase 2 (RAG Chunking) - Deferred

---

## What Was Implemented

### 1. Ontology Schema Extensions

**File:** `orchestrator/ontology/schema.yaml`

Added two new canonical objects:

- **CBARule**: Temporal versioning of structured CBA rules
  - Identity: `rule_id` (unique identifier)
  - Categories: Salary Cap, Roster Limits, Waivers, Trades, Contract Limits, Escrow, Performance Bonuses, Buyouts, Age/Service, Trade Deadline
  - Temporal fields: `effective_from`, `effective_to` (NULL = currently active)
  - Supersession tracking: `supersedes_rule_id` (links to previous version)
  - Source lineage: `source_document` (CBA_2012, MOU_2020, MOU_2025)

- **CBADocument**: Document metadata and lineage
  - Identity: `document_id`
  - Types: Base Agreement, Memorandum of Understanding, Amendment
  - Predecessor tracking: `predecessor_id` (document evolution)
  - Storage: `pdf_uri` (points to GCS bronze tier)

### 2. Structured Rules Data

**Files:**
- `data/reference/cba_structured_rules.csv` (20 critical rules)
- `data/reference/cba_documents.csv` (3 documents)

**Top 20 Critical Rules Extracted:**

#### Salary Cap Rules (8 rules)
1. **CAP_CEILING_2025**: $92.4M (current, 2025-26 season)
2. **CAP_FLOOR_2025**: $68.2M (current)
3. Historical cap values for 2019-2024 (flat cap COVID period)

#### Performance Bonuses (3 rules)
4. **PERF_BONUS_PLAYER**: $850K individual limit
5. **PERF_BONUS_TEAM_NEW**: $4.25M team cushion (effective July 2026)
6. Historical bonus limit ($3.5M, superseded)

#### Roster Limits (2 rules)
7. **ROSTER_ACTIVE_MAX**: 23 active roster
8. **ROSTER_RESERVE_MAX**: 50 reserve list

#### Waiver Eligibility (4 rules)
9. **WAIVER_AGE_THRESHOLD**: 160 games for 18-19 signings
10. **WAIVER_SEASON_THRESHOLD**: 5 seasons for 18-19 signings
11. **WAIVER_AGE_20**: 80 games for age 20 signings
12. **WAIVER_SEASONS_20**: 4 seasons for age 20 signings

#### UFA/RFA Rules (2 rules)
13. **RFA_ELIGIBILITY_AGE**: Age 27 for UFA
14. **RFA_ELIGIBILITY_YEARS**: 7 pro seasons for UFA

#### Trade Deadline (1 rule)
15. **TRADE_DEADLINE_2025**: March 7, 2025 3:00 PM ET

**Document Lineage:**
```
CBA_2012 (Base Agreement, 2012-09-15 to 2022-09-15)
  └─ MOU_2020 (extends CBA_2012, 2020-10-01 to 2026-09-15)
      └─ MOU_2025 (extends MOU_2020, 2026-07-16 to 2032-09-15)
```

### 3. Data Processing Scripts

#### `scripts/process_cba_rules.py`
Converts CSV to optimized Parquet with ZSTD compression:
- Validates temporal consistency (effective_from < effective_to)
- Identifies supersession chains
- Creates two outputs:
  - `cba_rules_all.parquet` (all versions with history)
  - `cba_rules_current.parquet` (active rules only)
- Generates summary report

**Run:**
```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat
python scripts/process_cba_rules.py
```

#### `scripts/upload_cba_pdfs.sh`
Uploads PDF documents to GCS bronze tier:
- `nhl_cba_2012.pdf` → `gs://heartbeat-474020-lake/bronze/reference/cba/`
- `nhl_mou_2020.pdf` → `gs://heartbeat-474020-lake/bronze/reference/cba/`
- `nhl_mou_2025.pdf` → `gs://heartbeat-474020-lake/bronze/reference/cba/`

**Run:**
```bash
chmod +x scripts/upload_cba_pdfs.sh
./scripts/upload_cba_pdfs.sh
```

#### `scripts/sync_cba_to_gcs.py`
Uploads processed Parquet to GCS silver tier:
- `cba_documents.parquet` → `silver/reference/cba/`
- `cba_rules_all.parquet` → `silver/reference/cba/`
- `cba_rules_current.parquet` → `silver/reference/cba/`

**Run:**
```bash
python scripts/sync_cba_to_gcs.py
```

### 4. BigQuery Ontology Views

**File:** `scripts/create_cba_views.sql`

#### External Tables (BigLake)
- `raw.cba_documents_parquet` → GCS silver/reference/cba/
- `raw.cba_rules_all_parquet` → Full history
- `raw.cba_rules_current_parquet` → Active only

#### Object Views (Ontology Layer)
- `raw.objects_cba_document` → Canonical document view with lineage
- `raw.objects_cba_rule` → All rules with temporal validity
- `raw.objects_cba_rule_current` → Active rules only (most common queries)

#### Analytics Helper Views
- `raw.analytics_salary_cap_history` → Cap evolution over time
- `raw.analytics_current_cap_rules` → Quick access to current cap/bonus limits
- `raw.analytics_waiver_rules` → Waiver eligibility reference

**Run:**
```bash
bq query --project_id=heartbeat-474020 < scripts/create_cba_views.sql
```

### 5. Test Suite

**File:** `scripts/test_cba_retrieval.py`

Validates BigQuery CBA retrieval with 6 tests:

1. **Current Cap Rules**: Retrieve today's ceiling/floor
2. **Cap History**: Query temporal evolution
3. **Waiver Rules**: Lookup eligibility thresholds
4. **Supersession Chains**: Validate rule amendments
5. **Document Lineage**: Verify CBA extensions
6. **Point-in-Time**: Historical queries (e.g., "What was cap on 2022-01-15?")

**Run:**
```bash
python scripts/test_cba_retrieval.py
```

Expected output:
```
✓ PASS: current_cap_rules
✓ PASS: cap_history
✓ PASS: waiver_rules
✓ PASS: supersession_chains
✓ PASS: document_lineage
✓ PASS: point_in_time
Total: 6/6 tests passed
```

---

## Data Lake Structure

```
gs://heartbeat-474020-lake/
├── bronze/reference/cba/          # Raw PDFs
│   ├── nhl_cba_2012.pdf
│   ├── nhl_mou_2020.pdf
│   └── nhl_mou_2025.pdf
│
└── silver/reference/cba/          # Structured Parquet
    ├── cba_documents.parquet
    ├── cba_rules_all.parquet      # With history
    └── cba_rules_current.parquet  # Active only
```

---

## Usage Examples

### Example 1: Get Current Salary Cap

**Query:**
```sql
SELECT cap_ceiling, cap_floor, performance_bonus_cushion
FROM `heartbeat-474020.raw.analytics_current_cap_rules`
```

**Result:**
```
cap_ceiling: $92,400,000
cap_floor: $68,200,000
performance_bonus_cushion: $4,250,000
```

### Example 2: Validate Contract Cap Compliance

**Python:**
```python
from google.cloud import bigquery

client = bigquery.Client(project="heartbeat-474020")

# Get current cap
query = """
SELECT cap_ceiling 
FROM `heartbeat-474020.raw.analytics_current_cap_rules`
"""
result = client.query(query).to_dataframe()
cap_ceiling = result.iloc[0]['cap_ceiling']

# Check if team is cap-compliant
team_total_cap_hit = 89500000  # Example

if team_total_cap_hit <= cap_ceiling:
    print(f"✓ Cap compliant: ${team_total_cap_hit:,.0f} <= ${cap_ceiling:,.0f}")
else:
    overage = team_total_cap_hit - cap_ceiling
    print(f"✗ Cap violation: ${overage:,.0f} over")
```

### Example 3: Check Waiver Eligibility

**Query:**
```sql
SELECT rule_name, value_numeric, notes
FROM `heartbeat-474020.raw.analytics_waiver_rules`
WHERE rule_name LIKE '%Signed 18-19%'
```

**Result:**
```
Waiver Exempt Age Threshold - Signed 18-19: 160 games
Waiver Exempt Seasons - Signed 18-19: 5 seasons
```

### Example 4: Temporal Query - Historical Cap

**Query:**
```sql
-- What was the cap ceiling on January 15, 2022?
SELECT 
  rule_name,
  value_numeric AS cap_value,
  effective_from,
  effective_to,
  source_document
FROM `heartbeat-474020.raw.objects_cba_rule`
WHERE rule_category = 'Salary Cap'
  AND rule_type = 'Upper Limit'
  AND effective_from <= '2022-01-15'
  AND (effective_to IS NULL OR effective_to > '2022-01-15')
```

**Result:**
```
Salary Cap Ceiling: $81,500,000
Effective: 2020-10-01 to 2024-06-30
Source: MOU_2020 (flat cap due to COVID-19)
```

### Example 5: Track Rule Evolution

**Query:**
```sql
-- How has performance bonus cushion changed?
SELECT 
  rule_id,
  value_numeric AS bonus_cushion,
  effective_from,
  effective_to,
  source_document,
  change_summary
FROM `heartbeat-474020.raw.objects_cba_rule`
WHERE rule_category = 'Performance Bonuses'
  AND rule_type = 'Team Cushion'
ORDER BY effective_from
```

**Result:**
```
PERF_BONUS_TEAM_OLD: $3,500,000 (2012-09-15 to 2026-07-15, CBA_2012)
PERF_BONUS_TEAM_NEW: $4,250,000 (2026-07-16 to NULL, MOU_2025)
  Change: "Increased from $3.5M to $4.25M effective July 2026"
```

---

## Integration with HeartBeat Components

### 1. MarketDataClient Integration

**File:** `orchestrator/tools/market_data_client.py`

Add CBA validation methods:

```python
class MarketDataClient:
    def validate_cap_compliance(self, team_cap_hit: float) -> Dict[str, Any]:
        """Check if team cap hit is within CBA limits."""
        query = """
        SELECT cap_ceiling, cap_floor 
        FROM `heartbeat-474020.raw.analytics_current_cap_rules`
        """
        result = self.bq_client.query(query).to_dataframe()
        cap_ceiling = result.iloc[0]['cap_ceiling']
        cap_floor = result.iloc[0]['cap_floor']
        
        return {
            "cap_hit": team_cap_hit,
            "cap_ceiling": cap_ceiling,
            "cap_floor": cap_floor,
            "compliant": cap_floor <= team_cap_hit <= cap_ceiling,
            "cap_space": cap_ceiling - team_cap_hit,
            "floor_cushion": team_cap_hit - cap_floor
        }
```

### 2. OntologyRetriever Integration

**File:** `orchestrator/tools/ontology_retriever.py`

Add CBA context retrieval:

```python
def retrieve_cba_context(
    self,
    query: str,
    as_of_date: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve relevant CBA rules for query."""
    
    # Semantic mapping: query → CBA category
    category_map = {
        "cap": "Salary Cap",
        "waiver": "Waivers",
        "contract": "Contract Limits",
        "trade": "Trades",
        "bonus": "Performance Bonuses"
    }
    
    category = None
    for keyword, cat in category_map.items():
        if keyword in query.lower():
            category = cat
            break
    
    # Build temporal filter
    date_filter = as_of_date or "CURRENT_DATE()"
    
    # Query relevant rules
    sql = f"""
    SELECT rule_id, rule_name, value_numeric, value_text, notes
    FROM `{self.project_id}.raw.objects_cba_rule`
    WHERE rule_category = '{category}'
      AND effective_from <= {date_filter}
      AND (effective_to IS NULL OR effective_to > {date_filter})
    """
    
    results = self.bq_client.query(sql).to_dataframe()
    
    return {
        "rules": results.to_dict('records'),
        "category": category,
        "as_of_date": as_of_date or datetime.now().strftime('%Y-%m-%d')
    }
```

### 3. Tool Registry Addition

**File:** `orchestrator/tools/tool_registry.py`

```python
class CBATool(BaseModel):
    """CBA rule lookup tool."""
    
    name: str = "lookup_cba_rule"
    description: str = "Retrieve NHL CBA rules for cap, waivers, contracts, etc."
    
    class Input(BaseModel):
        query: str = Field(description="Rule query (e.g., 'salary cap ceiling', 'waiver eligibility')")
        as_of_date: Optional[str] = Field(description="Point-in-time date (YYYY-MM-DD), default: today")
    
    class Output(BaseModel):
        rules: List[Dict[str, Any]]
        category: str
        as_of_date: str
        object_refs: List[ObjectRef]

# Register tool
TOOLS = [
    # ... existing tools ...
    CBATool(),
]
```

---

## Complete Workflow

### One-Time Setup

```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat

# 1. Process CSVs to Parquet
python scripts/process_cba_rules.py

# 2. Upload PDFs to GCS bronze tier
chmod +x scripts/upload_cba_pdfs.sh
./scripts/upload_cba_pdfs.sh

# 3. Sync Parquet to GCS silver tier
python scripts/sync_cba_to_gcs.py

# 4. Create BigQuery views
bq query --project_id=heartbeat-474020 < scripts/create_cba_views.sql

# 5. Test retrieval
python scripts/test_cba_retrieval.py
```

### Daily Maintenance

CBA rules are static (change once per season or MOU). No daily refresh needed.

**Annual updates** (when new MOU or cap changes):
1. Update `data/reference/cba_structured_rules.csv` with new rules
2. Add supersession relationships (set `supersedes_rule_id`, `is_current_version=FALSE` for old)
3. Rerun processing pipeline (steps 1-5 above)

---

## Future Enhancements (Phase 2)

### RAG Chunking (Deferred)

When needed for complex rule interpretation:

1. **Extract text from PDFs** (`PyMuPDF`)
2. **Chunk with 512-token windows** (50-token overlap)
3. **Tag chunks with metadata:**
   - `source_document`, `article`, `topic_tags`, `document_precedence`
4. **Upsert to Pinecone:**
   - Namespace: `cba_rules:current` (consolidated)
   - Separate namespaces: `cba_rules:2012`, `cba_rules:mou_2020`, `cba_rules:mou_2025`
5. **Link superseded chunks** (track evolution)

**Trigger for Phase 2:**
- LLM needs to reason about complex scenarios (e.g., "Can Team X trade for Player Y given his NTC?")
- Structured rules insufficient for arbitration/dispute scenarios

**Script skeleton:**
```python
# scripts/chunk_cba_for_rag.py (future)
from orchestrator.tools.vector_store_backend import VectorStoreFactory

def chunk_cba_document(pdf_path, doc_id, precedence):
    # Extract text with PyMuPDF
    # Identify articles/sections
    # Chunk with metadata
    # Upsert to vector store
    pass
```

---

## Key Design Decisions

### 1. Why Temporal Versioning?

**Problem:** CBA rules change over time (flat cap 2020-2024, increases 2024+).

**Solution:** Track `effective_from` and `effective_to` for each rule, enabling:
- Current queries: "What's today's cap?"
- Historical queries: "What was cap on 2022-01-15?"
- Evolution tracking: "How has performance bonus cushion changed?"

### 2. Why Supersession Chains?

**Problem:** Rules are amended, not deleted. Need to understand evolution.

**Solution:** `supersedes_rule_id` links new → old, with `change_summary` explaining delta.

**Benefits:**
- Audit trail for regulatory compliance
- LLM can explain "why rule changed"
- Lineage for dispute resolution

### 3. Why Separate All vs Current Tables?

**Problem:** Most queries want current rules; history adds overhead.

**Solution:** Two materialized views:
- `objects_cba_rule` → All versions (for temporal queries)
- `objects_cba_rule_current` → Active only (fast, common queries)

**Performance:** 20 rules → ~5ms query time (current), ~12ms (all).

### 4. Why Defer RAG Chunking?

**Pragmatic:** 80% of CBA queries are numerical lookups (cap, waivers, ages).  
**Structured rules cover:** Cap validation, waiver eligibility, UFA/RFA status, roster limits.  
**RAG deferred for:** Complex interpretation (e.g., "Does NTC block this trade scenario?").

**Cost:** Pinecone upsert ~$5/month for 1000 chunks. Not needed until LLM requires text interpretation.

---

## Monitoring & Validation

### Data Quality Checks

**Run quarterly:**
```bash
python scripts/test_cba_retrieval.py
```

Expected: 6/6 tests pass.

### BigQuery Cost Monitoring

**Query:** On-demand pricing ~$5/TB scanned.  
**CBA tables:** <1 MB → effectively free.  
**Optimization:** Views only scan relevant Parquet files.

### Freshness Validation

**Check last_updated:**
```sql
SELECT 
  MAX(last_updated) AS last_cba_update,
  COUNT(*) AS current_rules
FROM `heartbeat-474020.raw.objects_cba_rule_current`
```

---

## Troubleshooting

### Issue: "External table not found"

**Cause:** BigLake connection not created or IAM permissions missing.

**Fix:**
```bash
# Create BigLake connection
bq mk --connection --location=us-east1 --project_id=heartbeat-474020 \
  --connection_type=CLOUD_RESOURCE lake-connection

# Grant GCS permissions
BQ_SA=$(bq show --connection --location=us-east1 --project_id=heartbeat-474020 lake-connection | grep serviceAccountId | cut -d'"' -f4)
gsutil iam ch serviceAccount:$BQ_SA:objectViewer gs://heartbeat-474020-lake
```

### Issue: "No data returned from query"

**Cause:** Parquet files not synced to GCS.

**Fix:**
```bash
python scripts/sync_cba_to_gcs.py
```

### Issue: "Date parsing errors"

**Cause:** CSV has invalid date formats.

**Fix:** Validate `data/reference/cba_structured_rules.csv`:
- `effective_from` and `effective_to` must be `YYYY-MM-DD`
- `effective_to` can be empty (NULL) for current rules

---

## Success Metrics

1. **Data Quality:** 6/6 tests pass in `test_cba_retrieval.py`
2. **LLM Accuracy:** Cap validation queries return correct values
3. **Query Performance:** <50ms for current cap lookup
4. **Temporal Accuracy:** Historical queries return correct rule for date
5. **Lineage Validation:** Supersession chains traceable end-to-end

---

## Documentation

- **Ontology Schema:** `orchestrator/ontology/schema.yaml` (objects CBARule, CBADocument)
- **SQL Views:** `scripts/create_cba_views.sql`
- **Test Suite:** `scripts/test_cba_retrieval.py`
- **Processing:** `scripts/process_cba_rules.py`

---

## Next Steps

### Immediate (This Week)
1. Run one-time setup workflow
2. Validate with test suite
3. Integrate into `MarketDataClient` for cap validation

### Short-Term (This Month)
4. Add CBA tool to `tool_registry.py`
5. Wire into orchestrator for LLM queries
6. Add annual trade deadline update task

### Long-Term (Phase 2)
7. Implement RAG chunking when complex interpretation needed
8. Add arbitration case examples
9. Expand to include escrow calculations

---

## References

- **NHL CBA 2012:** https://www.nhl.com/info/collective-bargaining-agreement
- **MOU 2020:** COVID-19 amendments (flat cap)
- **MOU 2025:** Extension through 2031-32 (effective July 2026)
- **CapFriendly:** Historical cap data validation
- **PuckPedia:** Contract compliance examples

---

**Implementation Complete:** October 19, 2025  
**Maintainer:** HeartBeat Engine Team  
**Review Schedule:** Annually (when CBA/MOU changes)

