"""
HeartBeat Engine - CBA Lookup Tool

Provides typed access to CBA rule objects in BigQuery.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from google.cloud import bigquery
import logging

logger = logging.getLogger(__name__)


@dataclass
class CBALookupResult:
    rules: List[Dict[str, Any]]
    category: Optional[str]
    as_of_date: Optional[str]


def _infer_category_and_filters(query: str) -> tuple[Optional[str], Dict[str, str]]:
    q = query.lower()
    category = None
    extra = {}

    if any(k in q for k in ["cap", "ceiling", "floor", "upper limit", "lower limit"]):
        category = "Salary Cap"
        if any(k in q for k in ["ceiling", "upper", "max", "upper limit"]):
            extra["rule_type"] = "Upper Limit"
        if any(k in q for k in ["floor", "lower", "min", "lower limit"]):
            extra["rule_type"] = "Lower Limit"
    elif "waiver" in q or "waivers" in q:
        category = "Waivers"
    elif "bonus" in q or "performance" in q:
        category = "Performance Bonuses"
    elif "roster" in q:
        category = "Roster Limits"
    elif "ufa" in q or "rfa" in q or "free agent" in q:
        category = "Age/Service"
    elif "trade" in q:
        category = "Trade Deadline"

    return category, extra


def lookup_cba_rule(
    query: str,
    as_of_date: Optional[str] = None,
    project_id: str = "heartbeat-474020",
    dataset: str = "cba",
) -> Dict[str, Any]:
    """Lookup CBA rules from ontology views in BigQuery.

    Args:
        query: free-text query (e.g., "cap ceiling", "waiver eligibility")
        as_of_date: optional YYYY-MM-DD date for temporal lookup
        project_id, dataset: BigQuery identifiers
    """
    client = bigquery.Client(project=project_id)

    category, extra = _infer_category_and_filters(query)
    use_point_in_time = bool(as_of_date)

    if use_point_in_time:
        base_table = f"`{project_id}.{dataset}.objects_cba_rule`"
        date_clause = (
            f"effective_from <= DATE('{as_of_date}') AND (effective_to IS NULL OR effective_to > DATE('{as_of_date}'))"
        )
    else:
        base_table = f"`{project_id}.{dataset}.objects_cba_rule_current`"
        date_clause = "is_currently_active = TRUE"

    where = [date_clause]
    if category:
        where.append(f"rule_category = '{category}'")
    if extra.get("rule_type"):
        where.append(f"rule_type = '{extra['rule_type']}'")

    # Fallback fuzzy search on rule_name/value_text if no category inferred
    if not category:
        safe = query.replace("'", "")
        where.append(f"(LOWER(rule_name) LIKE LOWER('%{safe}%') OR LOWER(value_text) LIKE LOWER('%{safe}%'))")

    sql = f"""
    SELECT 
      rule_id, rule_category, rule_type, rule_name, value_numeric, value_text,
      effective_from, effective_to, source_document, source_article, change_summary
    FROM {base_table}
    WHERE {' AND '.join(where)}
    ORDER BY rule_category, rule_type, rule_id
    LIMIT 100
    """

    logger.info(f"CBA lookup SQL: {sql}")
    df = client.query(sql).to_dataframe()

    return {
        "rules": df.to_dict("records"),
        "category": category,
        "as_of_date": as_of_date,
        "sql": sql,
    }

