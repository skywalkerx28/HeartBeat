"""
HabsAI Data Preprocessing Pipeline for LLM Mathematical Accuracy
==============================================================

This module ensures that all hockey analytics data is properly formatted,
mathematically validated, and contextually enriched for LLM consumption.

Key Features:
- Mathematical validation of all metrics
- Domain-specific context injection
- Statistical integrity preservation
- Metadata enrichment for better LLM understanding
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MetricValidation:
    """Validation rules for hockey metrics"""
    name: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    expected_type: str = "numeric"
    unit: Optional[str] = None
    description: str = ""
    category: str = "general"

class HockeyDataValidator:
    """Validates hockey analytics data for mathematical accuracy"""

    def __init__(self):
        self.validation_rules = self._load_validation_rules()

    def _load_validation_rules(self) -> Dict[str, MetricValidation]:
        """Load validation rules for hockey metrics"""
        return {
            # Expected Goals Metrics
            "ES Expected Goals For": MetricValidation(
                name="ES Expected Goals For",
                min_value=0.0,
                max_value=10.0,
                unit="goals per game",
                description="Expected goals scored at even strength",
                category="expected_goals"
            ),
            "ES Expected Goals Against": MetricValidation(
                name="ES Expected Goals Against",
                min_value=0.0,
                max_value=10.0,
                unit="goals per game",
                description="Expected goals allowed at even strength",
                category="expected_goals"
            ),

            # Percentage Metrics
            "ES% Shot Attempts On Net": MetricValidation(
                name="ES% Shot Attempts On Net",
                min_value=0.0,
                max_value=100.0,
                unit="percentage",
                description="Percentage of shot attempts that reach the net",
                category="shooting"
            ),
            "Goalie ES Save%": MetricValidation(
                name="Goalie ES Save%",
                min_value=0.0,
                max_value=100.0,
                unit="percentage",
                description="Even strength save percentage",
                category="goaltending"
            ),

            # Rate Metrics (per game)
            "ES Shot Attempts For": MetricValidation(
                name="ES Shot Attempts For",
                min_value=0.0,
                max_value=100.0,
                unit="attempts per game",
                description="Shot attempts generated at even strength",
                category="shooting"
            ),
            "ES Shot Attempts Against": MetricValidation(
                name="ES Shot Attempts Against",
                min_value=0.0,
                max_value=100.0,
                unit="attempts per game",
                description="Shot attempts allowed at even strength",
                category="defense"
            ),

            # Time-based Metrics
            "ES OZ Possession Time": MetricValidation(
                name="ES OZ Possession Time",
                min_value=0.0,
                max_value=1200.0,  # 20 minutes in seconds
                unit="seconds",
                description="Offensive zone possession time at even strength",
                category="possession"
            )
        }

    def validate_metric(self, metric_name: str, value: Any) -> Dict[str, Any]:
        """Validate a single metric value"""
        if metric_name not in self.validation_rules:
            return {
                "valid": True,
                "warnings": [f"Unknown metric: {metric_name}"],
                "suggestions": ["Consider adding validation rule for this metric"]
            }

        rule = self.validation_rules[metric_name]
        result = {"valid": True, "warnings": [], "errors": []}

        # Type validation
        if rule.expected_type == "numeric":
            try:
                numeric_value = float(value)
            except (ValueError, TypeError):
                result["valid"] = False
                result["errors"].append(f"Expected numeric value, got {type(value)}")
                return result

            # Range validation
            if rule.min_value is not None and numeric_value < rule.min_value:
                result["warnings"].append(
                    f"Value {numeric_value} below expected minimum {rule.min_value}"
                )

            if rule.max_value is not None and numeric_value > rule.max_value:
                result["warnings"].append(
                    f"Value {numeric_value} above expected maximum {rule.max_value}"
                )

        return result

class HockeyDataProcessor:
    """Processes hockey data with mathematical and contextual enrichment"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.validator = HockeyDataValidator()
        self.context_templates = self._load_context_templates()

    def _load_context_templates(self) -> Dict[str, str]:
        """Load context templates for different data types"""
        return {
            "team_stats": """
This data represents {team_name}'s performance metrics for the {season} NHL season.
All values are calculated per game unless otherwise specified.
Context: {global_context}
Key interpretation rules:
- Higher values are generally better unless specified as "against" metrics
- Percentages are out of 100
- Time-based metrics are in seconds
- Expected Goals (xG) represent quality scoring opportunities
""",

            "xg_benchmarks": """
XG Benchmarks analysis showing {team_name}'s performance split by expected goals advantage:
- 'Below': Performance when {team_name}'s ES Expected Goals For % < 50% (out-produced by opponents)
- 'Average': Overall performance across all situations
- 'Above': Performance when {team_name}'s ES Expected Goals For % > 50% (out-producing opponents)
This reveals strategic patterns in different game states.
""",

            "player_stats": """
Individual player performance data for {team_name}.
Metrics are calculated per 60 minutes of ice time unless otherwise specified.
Advanced metrics like Corsi and Expected Goals provide deeper performance insights.
""",

            "season_reports": """
Comprehensive season summary for {team_name} including rankings against all NHL teams.
Rank 1 = best in league, Rank 32 = worst in league.
League median represents average NHL team performance.
"""
        }

    def process_csv_file(self, file_path: str, context_type: str = "general") -> Dict[str, Any]:
        """Process a CSV file with validation and context enrichment"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read the CSV file
        df = pd.read_csv(file_path)

        # Validate data
        validation_results = self._validate_dataframe(df)

        # Add metadata and context
        metadata = self._generate_metadata(df, file_path, context_type)

        # Create LLM-ready format
        processed_data = {
            "original_file": str(file_path),
            "metadata": metadata,
            "validation_results": validation_results,
            "data_summary": self._generate_data_summary(df),
            "llm_context": self._generate_llm_context(df, context_type, metadata),
            "processed_records": self._process_records_for_llm(df)
        }

        return processed_data

    def _validate_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate entire dataframe"""
        validation_summary = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "validation_errors": [],
            "validation_warnings": [],
            "validated_metrics": 0
        }

        # Validate each cell
        for idx, row in df.iterrows():
            for col in df.columns:
                if col in ['Section', 'Metric Label', 'Against']:  # Skip non-numeric columns
                    continue

                value = row[col]
                if pd.notna(value):  # Only validate non-null values
                    validation = self.validator.validate_metric(col, value)
                    if not validation["valid"]:
                        validation_summary["validation_errors"].extend(validation["errors"])
                    if validation["warnings"]:
                        validation_summary["validation_warnings"].extend(validation["warnings"])

                    validation_summary["validated_metrics"] += 1

        return validation_summary

    def _generate_metadata(self, df: pd.DataFrame, file_path: Path, context_type: str) -> Dict[str, Any]:
        """Generate comprehensive metadata for the dataset"""
        return {
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
            "data_shape": df.shape,
            "columns": list(df.columns),
            "data_types": {col: str(df[col].dtype) for col in df.columns},
            "null_counts": df.isnull().sum().to_dict(),
            "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
            "context_type": context_type,
            "processing_timestamp": pd.Timestamp.now().isoformat(),
            "team_identified": self._identify_team(df),
            "season_identified": self._identify_season(df),
            "data_quality_score": self._calculate_data_quality_score(df)
        }

    def _identify_team(self, df: pd.DataFrame) -> Optional[str]:
        """Identify the team from the data"""
        # Look for team names in various columns
        team_indicators = ['Montreal', 'Canadiens', 'MTL', 'Habs']

        for col in df.columns:
            for cell in df[col].astype(str):
                for indicator in team_indicators:
                    if indicator.lower() in cell.lower():
                        return "Montreal Canadiens"
        return "Montreal Canadiens"  # Default assumption

    def _identify_season(self, df: pd.DataFrame) -> Optional[str]:
        """Identify the season from the data"""
        season_patterns = ['2024', '2025', '2023-24', '2024-25']

        for col in df.columns:
            for cell in df[col].astype(str):
                for pattern in season_patterns:
                    if pattern in cell:
                        return "2024-25"
        return "2024-25"  # Default assumption

    def _calculate_data_quality_score(self, df: pd.DataFrame) -> float:
        """Calculate a data quality score (0-100)"""
        score = 100.0

        # Penalize for null values
        null_percentage = df.isnull().sum().sum() / (df.shape[0] * df.shape[1])
        score -= null_percentage * 30

        # Penalize for non-numeric values in numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            non_numeric = pd.to_numeric(df[col], errors='coerce').isnull().sum()
            if len(df) > 0:
                score -= (non_numeric / len(df)) * 20

        return max(0.0, min(100.0, score))

    def _generate_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate statistical summary of the data"""
        summary = {
            "numeric_summary": {},
            "categorical_summary": {},
            "key_insights": []
        }

        # Numeric columns summary
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            summary["numeric_summary"][col] = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max())
            }

        # Categorical columns summary
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            value_counts = df[col].value_counts().head(10).to_dict()
            summary["categorical_summary"][col] = value_counts

        # Generate key insights
        summary["key_insights"] = self._generate_key_insights(df)

        return summary

    def _generate_key_insights(self, df: pd.DataFrame) -> List[str]:
        """Generate key insights from the data"""
        insights = []

        # Look for XG-related insights if present
        if 'ES Expected Goals For' in df.columns:
            xg_cols = [col for col in df.columns if 'Expected Goals' in col and 'ES' in col]
            if len(xg_cols) >= 2:
                # Find rows with XG data
                xg_rows = df[df['Metric Label'].str.contains('Expected Goals', na=False)]
                if not xg_rows.empty:
                    insights.append("This dataset contains Expected Goals (xG) analysis, measuring quality of scoring opportunities")

        # Look for performance splits
        if 'Below' in df.columns and 'Above' in df.columns:
            insights.append("Data shows performance splits by game state (advantage vs disadvantage situations)")

        # General insights
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            insights.append(f"Dataset contains {len(numeric_cols)} numeric metrics for performance analysis")

        return insights

    def _generate_llm_context(self, df: pd.DataFrame, context_type: str, metadata: Dict) -> str:
        """Generate comprehensive context for LLM consumption"""
        team_name = metadata.get("team_identified", "Montreal Canadiens")
        season = metadata.get("season_identified", "2024-25")

        # Get base context template
        base_context = self.context_templates.get(context_type, self.context_templates["team_stats"])

        # Add global context
        global_context = f"""
This data contributes to a comprehensive analysis of {team_name}'s performance over the {season} NHL season.
The dataset includes {metadata['data_shape'][0]} metrics across {metadata['data_shape'][1]} categories,
providing insights into team performance, player contributions, and strategic patterns against NHL opponents.
Data quality score: {metadata.get('data_quality_score', 'N/A'):.1f}/100.
"""

        # Format the context
        llm_context = base_context.format(
            team_name=team_name,
            season=season,
            global_context=global_context
        )

        # Add data-specific context
        if context_type == "xg_benchmarks":
            llm_context += f"\nData Quality: {metadata.get('validation_results', {}).get('validation_warnings', [])} warnings found."

        return llm_context

    def _process_records_for_llm(self, df: pd.DataFrame, max_records: int = 100) -> List[Dict[str, Any]]:
        """Process records into LLM-friendly format"""
        processed_records = []

        # Convert to records but limit size for LLM consumption
        records = df.to_dict('records')

        for i, record in enumerate(records[:max_records]):
            processed_record = {
                "record_id": i,
                "data": record,
                "interpretation_guide": self._generate_interpretation_guide(record)
            }
            processed_records.append(processed_record)

        return processed_records

    def _generate_interpretation_guide(self, record: Dict[str, Any]) -> str:
        """Generate interpretation guide for a specific record"""
        guide = "Interpretation: "

        # Look for common patterns
        if 'Below' in record and 'Above' in record:
            guide += "This metric shows performance in three contexts: "
            guide += "Below = disadvantage situation, "
            guide += "Average = overall performance, "
            guide += "Above = advantage situation. "

        if 'ES' in str(record.get('Metric Label', '')):
            guide += "ES = Even Strength play. "

        if '%' in str(record.get('Metric Label', '')):
            guide += "Value is a percentage (0-100). "

        if any(term in str(record.get('Metric Label', '')).lower() for term in ['attempts', 'shots']):
            guide += "Higher values generally indicate better performance unless specified as 'against'. "

        return guide

def main():
    """Main processing function"""
    processor = HockeyDataProcessor()

    # Process XG Benchmarks file
    try:
        xg_file = "data/team_stats/XG-Benchmarks-Montreal-2024.csv"
        result = processor.process_csv_file(xg_file, context_type="xg_benchmarks")

        # Save processed data
        output_file = "data/processed/xg_benchmarks_processed.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        logger.info(f"Successfully processed {xg_file}")
        logger.info(f"Validation results: {result['validation_results']}")

    except Exception as e:
        logger.error(f"Error processing file: {e}")

if __name__ == "__main__":
    main()
