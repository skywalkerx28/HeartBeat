"""
Metadata System for Context Preservation Across Data Chunks
==========================================================

This module implements a comprehensive metadata system that preserves mathematical
relationships, contextual information, and data integrity across chunks in the RAG system.

Key Features:
- Relationship mapping between chunks
- Mathematical dependency tracking
- Contextual metadata enrichment
- Cross-chunk query optimization
- Data reconstruction support
"""

import json
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import pandas as pd
from pathlib import Path
import networkx as nx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ChunkMetadata:
    """Comprehensive metadata for a data chunk"""
    chunk_id: str
    data_type: str
    chunk_type: str
    chunk_sequence: int
    total_chunks: int
    data_shape: Tuple[int, int]
    columns: List[str]
    data_types: Dict[str, str]
    statistical_summary: Dict[str, Any]
    relationships: Dict[str, List[str]]
    dependencies: Dict[str, Any]
    context: Dict[str, Any]
    validation_status: Dict[str, Any]
    created_timestamp: str
    hash_value: str

@dataclass
class RelationshipGraph:
    """Graph representing relationships between chunks"""
    nodes: Dict[str, ChunkMetadata]
    edges: List[Tuple[str, str, Dict[str, Any]]]
    graph_metadata: Dict[str, Any]

class MetadataManager:
    """Manages metadata for data chunks with relationship tracking"""

    def __init__(self, metadata_store_path: str = "data/processed/metadata"):
        self.store_path = Path(metadata_store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.relationship_graph = RelationshipGraph({}, [], {})

    def create_chunk_metadata(self,
                            chunk_id: str,
                            data: pd.DataFrame,
                            data_type: str,
                            chunk_type: str,
                            chunk_sequence: int = 0,
                            total_chunks: int = 1,
                            context: Optional[Dict[str, Any]] = None,
                            overlap_info: Optional[Dict[str, Any]] = None) -> ChunkMetadata:
        """Create comprehensive metadata for a data chunk"""

        # Calculate data statistics
        statistical_summary = self._calculate_statistical_summary(data)

        # Generate hash for integrity checking
        hash_value = hashlib.md5(data.to_csv().encode()).hexdigest()

        # Identify relationships and dependencies
        relationships = self._identify_relationships(data, data_type, chunk_type)
        dependencies = self._identify_dependencies(data, data_type, context)

        # Create validation status
        validation_status = self._validate_chunk_integrity(data, data_type)

        # Build context information
        chunk_context = self._build_context_info(data, data_type, context, overlap_info)

        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            data_type=data_type,
            chunk_type=chunk_type,
            chunk_sequence=chunk_sequence,
            total_chunks=total_chunks,
            data_shape=data.shape,
            columns=list(data.columns),
            data_types={col: str(data[col].dtype) for col in data.columns},
            statistical_summary=statistical_summary,
            relationships=relationships,
            dependencies=dependencies,
            context=chunk_context,
            validation_status=validation_status,
            created_timestamp=datetime.now().isoformat(),
            hash_value=hash_value
        )

        # Add to relationship graph
        self._add_to_relationship_graph(metadata)

        return metadata

    def _calculate_statistical_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate comprehensive statistical summary of the chunk"""

        summary = {
            "numeric_stats": {},
            "categorical_stats": {},
            "data_quality": {},
            "mathematical_properties": {}
        }

        # Numeric column statistics
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            col_data = data[col].dropna()
            if len(col_data) > 0:
                summary["numeric_stats"][col] = {
                    "count": len(col_data),
                    "mean": float(col_data.mean()),
                    "median": float(col_data.median()),
                    "std": float(col_data.std()),
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "quartiles": {
                        "25%": float(col_data.quantile(0.25)),
                        "75%": float(col_data.quantile(0.75))
                    }
                }

                # Identify potential mathematical relationships
                summary["mathematical_properties"][col] = self._analyze_mathematical_properties(col_data)

        # Categorical column statistics
        categorical_cols = data.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            value_counts = data[col].value_counts().head(10).to_dict()
            summary["categorical_stats"][col] = {
                "unique_values": data[col].nunique(),
                "most_common": value_counts,
                "distribution": {k: v for k, v in value_counts.items()}
            }

        # Data quality metrics
        summary["data_quality"] = {
            "total_rows": len(data),
            "total_columns": len(data.columns),
            "null_counts": data.isnull().sum().to_dict(),
            "null_percentages": (data.isnull().sum() / len(data) * 100).to_dict(),
            "duplicate_rows": data.duplicated().sum(),
            "completeness_score": (1 - data.isnull().sum().sum() / (data.shape[0] * data.shape[1]))
        }

        return summary

    def _analyze_mathematical_properties(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze mathematical properties of a numeric series"""

        properties = {
            "distribution_type": "unknown",
            "outliers": False,
            "correlation_candidates": [],
            "mathematical_relationships": []
        }

        # Check for normal distribution (simplified)
        if len(series) >= 10:
            skewness = series.skew()
            kurtosis = series.kurtosis()

            if abs(skewness) < 0.5 and abs(kurtosis) < 0.5:
                properties["distribution_type"] = "approximately_normal"
            elif skewness > 1:
                properties["distribution_type"] = "right_skewed"
            elif skewness < -1:
                properties["distribution_type"] = "left_skewed"

        # Check for outliers using IQR method
        if len(series) >= 4:
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outliers = series[(series < lower_bound) | (series > upper_bound)]
            properties["outliers"] = len(outliers) > 0
            properties["outlier_count"] = len(outliers)

        return properties

    def _identify_relationships(self, data: pd.DataFrame, data_type: str, chunk_type: str) -> Dict[str, List[str]]:
        """Identify relationships with other chunks"""

        relationships = {
            "depends_on": [],
            "provides_context_for": [],
            "related_chunks": [],
            "mathematical_links": []
        }

        # Data type specific relationships
        if data_type == "xg_benchmarks":
            relationships["provides_context_for"].extend(["performance_analysis", "strategic_planning"])
            relationships["mathematical_links"].extend(["expected_goals_calculations", "efficiency_metrics"])

        elif data_type == "play_by_play":
            relationships["depends_on"].append("game_metadata")
            relationships["provides_context_for"].extend(["event_analysis", "game_reconstruction"])
            relationships["mathematical_links"].extend(["temporal_analysis", "sequence_patterns"])

        elif data_type == "season_reports":
            relationships["provides_context_for"].extend(["comparative_analysis", "trend_analysis"])
            relationships["mathematical_links"].extend(["ranking_calculations", "percentile_analysis"])

        # Chunk type specific relationships
        if "temporal" in chunk_type:
            relationships["depends_on"].append("chronological_order")
            relationships["related_chunks"].append("adjacent_time_chunks")

        if "performance_splits" in str(data.columns):
            relationships["mathematical_links"].extend(["conditional_analysis", "situation_specific_metrics"])

        return relationships

    def _identify_dependencies(self, data: pd.DataFrame, data_type: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify mathematical and contextual dependencies"""

        dependencies = {
            "required_context": [],
            "mathematical_prerequisites": [],
            "data_dependencies": [],
            "temporal_dependencies": []
        }

        # Check for mathematical dependencies
        if any(col in data.columns for col in ["ES Expected Goals For", "ES Actual Goals"]):
            dependencies["mathematical_prerequisites"].append("expected_goals_methodology")

        if "Below" in data.columns and "Above" in data.columns:
            dependencies["mathematical_prerequisites"].append("performance_split_analysis")

        if any("60" in str(col) for col in data.columns):
            dependencies["mathematical_prerequisites"].append("per_60_minute_calculations")

        # Contextual dependencies
        if context:
            if context.get("team_name"):
                dependencies["required_context"].append(f"team_context_{context['team_name']}")

            if context.get("season"):
                dependencies["required_context"].append(f"season_context_{context['season']}")

        # Temporal dependencies for time-series data
        if any(col in data.columns for col in ["game_time", "period", "Game ID"]):
            dependencies["temporal_dependencies"].append("game_sequence_integrity")

        return dependencies

    def _build_context_info(self, data: pd.DataFrame, data_type: str, context: Optional[Dict[str, Any]], overlap_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build comprehensive context information"""

        context_info = {
            "domain": "hockey_analytics",
            "data_type": data_type,
            "business_context": {},
            "analytical_context": {},
            "usage_context": {}
        }

        # Business context
        if data_type == "xg_benchmarks":
            context_info["business_context"] = {
                "purpose": "Performance analysis across different expected goals situations",
                "stakeholders": ["coaches", "analysts", "management"],
                "decision_types": ["strategic_planning", "player_evaluation", "tactical_adjustments"]
            }

        elif data_type == "play_by_play":
            context_info["business_context"] = {
                "purpose": "Granular event analysis for tactical insights",
                "stakeholders": ["coaches", "scouts", "performance_analysts"],
                "decision_types": ["in_game_adjustments", "player_development", "strategic_planning"]
            }

        # Analytical context
        context_info["analytical_context"] = {
            "mathematical_framework": self._identify_mathematical_framework(data, data_type),
            "statistical_methods": self._identify_statistical_methods(data),
            "analytical_scope": self._determine_analytical_scope(data, data_type)
        }

        # Usage context
        context_info["usage_context"] = {
            "query_types": self._identify_query_types(data_type),
            "response_formats": ["analytical_reports", "visualizations", "recommendations"],
            "interaction_patterns": ["comparative_analysis", "trend_identification", "performance_diagnosis"]
        }

        # Add overlap information if provided
        if overlap_info:
            context_info["overlap_info"] = overlap_info

        # Add provided context
        if context:
            context_info["external_context"] = context

        return context_info

    def _identify_mathematical_framework(self, data: pd.DataFrame, data_type: str) -> str:
        """Identify the mathematical framework used"""

        if data_type == "xg_benchmarks":
            return "expected_goals_methodology"
        elif any("60" in str(col) for col in data.columns):
            return "rate_based_analytics"
        elif any("percentage" in str(col).lower() for col in data.columns):
            return "proportional_analysis"
        else:
            return "descriptive_statistics"

    def _identify_statistical_methods(self, data: pd.DataFrame) -> List[str]:
        """Identify statistical methods applicable to this data"""

        methods = ["descriptive_statistics"]

        if data.select_dtypes(include=[np.number]).shape[1] > 3:
            methods.append("correlation_analysis")

        if len(data) > 30:
            methods.append("inferential_statistics")

        if any("time" in str(col).lower() for col in data.columns):
            methods.append("time_series_analysis")

        return methods

    def _determine_analytical_scope(self, data: pd.DataFrame, data_type: str) -> str:
        """Determine the analytical scope of the data"""

        if data_type == "play_by_play":
            return "micro_analysis"
        elif data_type == "season_reports":
            return "macro_analysis"
        elif data_type == "xg_benchmarks":
            return "situational_analysis"
        else:
            return "performance_analysis"

    def _identify_query_types(self, data_type: str) -> List[str]:
        """Identify types of queries this data supports"""

        query_mapping = {
            "xg_benchmarks": ["performance_comparison", "situational_analysis", "efficiency_calculation"],
            "play_by_play": ["event_analysis", "sequence_identification", "tactical_insights"],
            "season_reports": ["trend_analysis", "comparative_evaluation", "performance_summary"],
            "team_stats": ["performance_diagnosis", "strategic_planning", "player_evaluation"]
        }

        return query_mapping.get(data_type, ["general_analysis"])

    def _validate_chunk_integrity(self, data: pd.DataFrame, data_type: str) -> Dict[str, Any]:
        """Validate the integrity of the chunk"""

        validation = {
            "integrity_checks": [],
            "warnings": [],
            "errors": [],
            "quality_score": 1.0
        }

        # Check for data consistency
        if data.empty:
            validation["errors"].append("Chunk contains no data")
            validation["quality_score"] *= 0.1

        # Check for null values
        null_percentage = data.isnull().sum().sum() / (data.shape[0] * data.shape[1])
        if null_percentage > 0.5:
            validation["warnings"].append(f"High null percentage: {null_percentage:.1%}")
            validation["quality_score"] *= 0.8

        # Check for duplicate rows
        duplicate_percentage = data.duplicated().sum() / len(data)
        if duplicate_percentage > 0.1:
            validation["warnings"].append(f"High duplicate percentage: {duplicate_percentage:.1%}")
            validation["quality_score"] *= 0.9

        # Data type specific validation
        if data_type == "xg_benchmarks":
            if not all(col in data.columns for col in ["Below", "Average", "Above"]):
                validation["errors"].append("XG benchmarks missing required performance split columns")
                validation["quality_score"] *= 0.5

        validation["integrity_checks"].append("basic_structure_check")
        validation["integrity_checks"].append("null_value_assessment")
        validation["integrity_checks"].append("duplicate_detection")

        return validation

    def _add_to_relationship_graph(self, metadata: ChunkMetadata):
        """Add chunk to the relationship graph"""

        # Add node
        self.relationship_graph.nodes[metadata.chunk_id] = metadata

        # Add edges based on relationships
        for relationship_type, related_chunks in metadata.relationships.items():
            for related_chunk in related_chunks:
                edge_data = {
                    "relationship_type": relationship_type,
                    "strength": 1.0,
                    "created_timestamp": metadata.created_timestamp
                }
                self.relationship_graph.edges.append((metadata.chunk_id, related_chunk, edge_data))

    def save_metadata(self, metadata: ChunkMetadata, output_path: Optional[str] = None):
        """Save metadata to file"""

        if output_path is None:
            output_path = self.store_path / f"{metadata.chunk_id}_metadata.json"

        metadata_dict = asdict(metadata)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved metadata for chunk {metadata.chunk_id} to {output_path}")

    def load_metadata(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """Load metadata from file"""

        metadata_path = self.store_path / f"{chunk_id}_metadata.json"

        if not metadata_path.exists():
            return None

        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata_dict = json.load(f)

        # Convert back to ChunkMetadata object
        return ChunkMetadata(**metadata_dict)

    def find_related_chunks(self, chunk_id: str, relationship_type: Optional[str] = None) -> List[str]:
        """Find chunks related to the given chunk"""

        related_chunks = []

        # Check direct relationships in metadata
        if chunk_id in self.relationship_graph.nodes:
            metadata = self.relationship_graph.nodes[chunk_id]
            for rel_type, chunks in metadata.relationships.items():
                if relationship_type is None or rel_type == relationship_type:
                    related_chunks.extend(chunks)

        # Check graph edges
        for source, target, edge_data in self.relationship_graph.edges:
            if source == chunk_id:
                if relationship_type is None or edge_data["relationship_type"] == relationship_type:
                    related_chunks.append(target)

        return list(set(related_chunks))  # Remove duplicates

    def get_context_for_query(self, query_type: str, data_types: List[str]) -> Dict[str, Any]:
        """Get relevant context information for a specific query type"""

        context = {
            "query_type": query_type,
            "relevant_data_types": data_types,
            "required_chunks": [],
            "mathematical_context": {},
            "business_context": {}
        }

        # Map query types to required chunks and context
        if query_type == "performance_analysis":
            context["required_chunks"] = ["xg_benchmarks", "season_reports"]
            context["mathematical_context"] = {
                "key_metrics": ["expected_goals", "corsi", "pdo", "finishing_percentage"],
                "analysis_framework": "situational_performance_analysis"
            }
            context["business_context"] = {
                "purpose": "Evaluate team and player performance",
                "stakeholders": ["coaches", "analysts"],
                "decisions": ["line_combinations", "strategic_adjustments"]
            }

        elif query_type == "comparative_analysis":
            context["required_chunks"] = ["season_reports", "team_stats"]
            context["mathematical_context"] = {
                "key_metrics": ["percentiles", "standard_deviations", "ranking_differences"],
                "analysis_framework": "league_comparison_framework"
            }

        elif query_type == "tactical_analysis":
            context["required_chunks"] = ["play_by_play", "xg_benchmarks"]
            context["mathematical_context"] = {
                "key_metrics": ["zone_entries", "shot_quality", "defensive_coverage"],
                "analysis_framework": "situational_tactics_analysis"
            }

        return context

    def optimize_chunk_retrieval(self, query_context: Dict[str, Any]) -> List[str]:
        """Optimize chunk retrieval based on query context"""

        required_chunks = query_context.get("required_chunks", [])
        query_type = query_context.get("query_type", "")

        # Find all chunks that match the required types
        matching_chunks = []
        for node_id, metadata in self.relationship_graph.nodes.items():
            if metadata.data_type in required_chunks:
                matching_chunks.append(node_id)

        # Prioritize chunks based on relevance to query type
        prioritized_chunks = self._prioritize_chunks(matching_chunks, query_type)

        return prioritized_chunks

    def _prioritize_chunks(self, chunks: List[str], query_type: str) -> List[str]:
        """Prioritize chunks based on relevance to query type"""

        # Simple prioritization based on chunk metadata
        prioritized = []

        for chunk_id in chunks:
            if chunk_id in self.relationship_graph.nodes:
                metadata = self.relationship_graph.nodes[chunk_id]

                # Boost priority for chunks with relevant relationships
                if query_type in str(metadata.relationships):
                    prioritized.insert(0, chunk_id)  # Add to front
                else:
                    prioritized.append(chunk_id)

        return prioritized

    def export_relationship_graph(self, output_path: str):
        """Export the relationship graph for visualization or analysis"""

        graph_data = {
            "nodes": {node_id: asdict(metadata) for node_id, metadata in self.relationship_graph.nodes.items()},
            "edges": self.relationship_graph.edges,
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_nodes": len(self.relationship_graph.nodes),
                "total_edges": len(self.relationship_graph.edges)
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported relationship graph to {output_path}")

def main():
    """Example usage of the metadata system"""

    # Create sample data
    sample_data = pd.DataFrame({
        "Metric Label": ["ES Expected Goals For", "ES Actual Goals", "ES Corsi For"],
        "Below": [1.5, 1.2, 45.0],
        "Average": [2.5, 2.1, 52.0],
        "Above": [3.5, 3.0, 58.0]
    })

    # Create metadata manager
    manager = MetadataManager()

    # Create metadata for sample chunk
    metadata = manager.create_chunk_metadata(
        chunk_id="xg_benchmarks_sample_0",
        data=sample_data,
        data_type="xg_benchmarks",
        chunk_type="section_complete",
        chunk_sequence=0,
        total_chunks=1,
        context={"team": "Montreal Canadiens", "season": "2024-25"}
    )

    # Save metadata
    manager.save_metadata(metadata)

    # Demonstrate relationship finding
    related = manager.find_related_chunks("xg_benchmarks_sample_0")
    print(f"Related chunks: {related}")

    # Demonstrate context retrieval
    query_context = manager.get_context_for_query("performance_analysis", ["xg_benchmarks"])
    print(f"Query context: {query_context}")

    # Export relationship graph
    manager.export_relationship_graph("data/processed/metadata/relationship_graph.json")

    print("Metadata system demonstration completed!")

if __name__ == "__main__":
    main()
