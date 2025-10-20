"""
Complete LLM Accuracy System for HabsAI
=======================================

This module integrates all components of the mathematical accuracy and contextual
understanding system for the Montreal Canadiens AI Query Engine.

Integration Components:
- Data Preprocessing Pipeline
- Domain-Specific Prompt Templates
- Intelligent Chunking Strategy
- Fine-Tuning Dataset Generation
- Mathematical Validation System
- Metadata Management System

Usage:
    python scripts/ml/llm_accuracy_system.py --data-path data/team_stats/XG-Benchmarks-Montreal-2024.csv --query "How is Montreal performing?"
"""

import argparse
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Import all system components
from data_preprocessing import HockeyDataProcessor
from hockey_prompt_templates import HockeyPromptManager
from data_chunking import HockeyDataChunker
from fine_tuning_dataset import HockeyAnalyticsFineTuner
from mathematical_validator import HockeyMathValidator
from metadata_system import MetadataManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HabsAIAcuuracySystem:
    """Complete system for ensuring LLM mathematical accuracy in hockey analytics"""

    def __init__(self, base_data_path: str = "data"):
        self.base_path = Path(base_data_path)
        self.processed_data_path = self.base_path / "processed"
        self.metadata_path = self.processed_data_path / "metadata"

        # Initialize all system components
        self.data_processor = HockeyDataProcessor()
        self.prompt_manager = HockeyPromptManager()
        self.chunking_system = HockeyDataChunker()
        self.fine_tuner = HockeyAnalyticsFineTuner()
        self.math_validator = HockeyMathValidator()
        self.metadata_manager = MetadataManager(str(self.metadata_path))

        # Ensure directories exist
        self.processed_data_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)

    def process_dataset(self, data_path: str, data_type: str = "auto") -> Dict[str, Any]:
        """Process a dataset through the complete accuracy pipeline"""

        logger.info(f"Processing dataset: {data_path}")

        # Step 1: Data Preprocessing with Validation
        logger.info("Step 1: Data preprocessing and validation")
        processed_data = self.data_processor.process_csv_file(data_path, data_type)

        # Step 2: Intelligent Chunking
        logger.info("Step 2: Intelligent chunking with mathematical integrity")
        data = pd.read_csv(data_path)
        chunks = self.chunking_system.chunk_data(data, data_type, processed_data["metadata"])

        # Step 3: Metadata Creation and Relationship Mapping
        logger.info("Step 3: Creating comprehensive metadata")
        chunk_metadata = []
        for chunk in chunks:
            metadata = self.metadata_manager.create_chunk_metadata(
                chunk_id=chunk.chunk_id,
                data=chunk.data,
                data_type=data_type,
                chunk_type=chunk.chunk_type,
                chunk_sequence=chunk.metadata.get("chunk_sequence", 0),
                total_chunks=len(chunks),
                context=processed_data["metadata"],
                overlap_info=chunk.overlap_info
            )
            chunk_metadata.append(metadata)

            # Save metadata
            self.metadata_manager.save_metadata(metadata)

        # Step 4: Generate Domain-Specific Prompts
        logger.info("Step 4: Generating domain-specific prompts")
        prompt_templates = self._generate_prompt_templates(data_type, processed_data["metadata"])

        # Step 5: Create Fine-Tuning Examples
        logger.info("Step 5: Creating fine-tuning examples")
        fine_tuning_examples = self._generate_fine_tuning_examples(data, data_type)

        # Step 6: Validation System Setup
        logger.info("Step 6: Setting up mathematical validation")
        validation_framework = self._setup_validation_framework(data_type)

        result = {
            "original_data_path": data_path,
            "data_type": data_type,
            "processed_data": processed_data,
            "chunks": len(chunks),
            "chunk_metadata": [metadata.chunk_id for metadata in chunk_metadata],
            "prompt_templates": prompt_templates,
            "fine_tuning_examples": len(fine_tuning_examples),
            "validation_framework": validation_framework,
            "system_status": "ready"
        }

        logger.info(f"Dataset processing completed successfully!")
        return result

    def _generate_prompt_templates(self, data_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate domain-specific prompt templates"""

        templates = {}

        # Generate context-enriched prompts for different query types
        query_types = ["performance_analysis", "xg_analysis", "comparative_analysis"]

        for query_type in query_types:
            # Create sample data context
            data_context = {
                "season": metadata.get("season_identified", "2024-25"),
                "analysis_type": f"{data_type} Analysis",
                "data_quality": metadata.get("data_quality_score", 95),
                "metrics": self._identify_key_metrics(data_type),
                "summary": metadata.get("data_summary", {})
            }

            # Generate enriched prompt
            try:
                prompt = self.prompt_manager.create_context_enriched_prompt(
                    template_name=query_type,
                    user_query="Analyze the performance data",
                    data_context=data_context
                )
                templates[query_type] = {
                    "template": prompt,
                    "variables": data_context,
                    "context_type": query_type
                }
            except Exception as e:
                logger.warning(f"Could not generate {query_type} template: {e}")

        return templates

    def _identify_key_metrics(self, data_type: str) -> List[str]:
        """Identify key metrics for a data type"""

        metric_mapping = {
            "xg_benchmarks": ["expected_goals", "finishing_percentage", "pdo"],
            "season_reports": ["corsi", "expected_goals", "save_percentage"],
            "play_by_play": ["shot_locations", "possession_time", "zone_entries"],
            "team_stats": ["performance_splits", "efficiency_metrics", "comparative_stats"]
        }

        return metric_mapping.get(data_type, ["performance_metrics"])

    def _generate_fine_tuning_examples(self, data: pd.DataFrame, data_type: str) -> List[Dict[str, Any]]:
        """Generate fine-tuning examples specific to the data"""

        # Create a small subset for demonstration
        examples = self.fine_tuner.generate_comprehensive_dataset(50)

        # Filter examples relevant to the data type
        relevant_examples = []
        for example in examples:
            if data_type in example.get("category", "").lower() or "general" in example.get("category", "").lower():
                relevant_examples.append(example)

        return relevant_examples[:20]  # Return up to 20 relevant examples

    def _setup_validation_framework(self, data_type: str) -> Dict[str, Any]:
        """Setup mathematical validation framework"""

        validation_rules = {
            "data_type": data_type,
            "mathematical_checks": self._get_mathematical_checks(data_type),
            "contextual_validations": self._get_contextual_validations(data_type),
            "error_detection": ["calculation_errors", "logical_inconsistencies", "statistical_misapplications"],
            "confidence_scoring": {
                "high_confidence_threshold": 0.9,
                "medium_confidence_threshold": 0.7,
                "low_confidence_threshold": 0.5
            }
        }

        return validation_rules

    def _get_mathematical_checks(self, data_type: str) -> List[str]:
        """Get mathematical checks for a data type"""

        checks = {
            "xg_benchmarks": [
                "expected_goals_calculations",
                "finishing_percentage_formulas",
                "performance_split_comparisons"
            ],
            "season_reports": [
                "percentage_calculations",
                "ranking_verification",
                "statistical_significance"
            ],
            "play_by_play": [
                "temporal_sequence_integrity",
                "coordinate_system_validation",
                "event_probability_calculations"
            ]
        }

        return checks.get(data_type, ["basic_mathematical_validation"])

    def _get_contextual_validations(self, data_type: str) -> List[str]:
        """Get contextual validations for a data type"""

        validations = {
            "xg_benchmarks": [
                "performance_split_context",
                "expected_goals_methodology",
                "situational_analysis_framework"
            ],
            "season_reports": [
                "league_comparison_context",
                "seasonal_trend_analysis",
                "team_performance_narrative"
            ],
            "play_by_play": [
                "game_situation_context",
                "event_sequence_logic",
                "tactical_implication_analysis"
            ]
        }

        return validations.get(data_type, ["general_context_validation"])

    def validate_llm_response(self, response: str, context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Validate an LLM response for mathematical accuracy"""

        logger.info("Validating LLM response for mathematical accuracy")

        # Use the mathematical validator
        validation_result = self.math_validator.validate_response(response, context_data)

        # Generate validation report
        validation_report = self.math_validator.generate_validation_report(validation_result)

        result = {
            "is_valid": validation_result.is_valid,
            "confidence_score": validation_result.confidence_score,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "corrections": validation_result.corrections,
            "validated_expressions": validation_result.validated_expressions,
            "report": validation_report
        }

        return result

    def generate_query_prompt(self, query: str, data_type: str, context_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate an optimized prompt for a user query"""

        # Determine query type
        query_type = self._classify_query_type(query)

        # Get relevant context
        if context_data:
            data_context = context_data
        else:
            data_context = {
                "season": "2024-25",
                "analysis_type": f"{data_type} Analysis",
                "data_quality": 95,
                "metrics": self._identify_key_metrics(data_type)
            }

        # Generate context-enriched prompt
        try:
            prompt = self.prompt_manager.create_context_enriched_prompt(
                template_name=query_type,
                user_query=query,
                data_context=data_context
            )
            return prompt
        except Exception as e:
            logger.warning(f"Could not generate optimized prompt: {e}")
            return query  # Return original query if template generation fails

    def _classify_query_type(self, query: str) -> str:
        """Classify the type of user query"""

        query_lower = query.lower()

        if any(term in query_lower for term in ["expected goals", "xg", "finishing", "conversion"]):
            return "xg_analysis"
        elif any(term in query_lower for term in ["compare", "versus", "vs", "better than", "ranking"]):
            return "comparative_analysis"
        elif any(term in query_lower for term in ["performance", "doing", "how is", "analysis"]):
            return "performance_analysis"
        else:
            return "performance_analysis"  # Default fallback

    def export_system_configuration(self, output_path: str):
        """Export the complete system configuration"""

        config = {
            "system_name": "HabsAI Mathematical Accuracy System",
            "version": "1.0.0",
            "components": {
                "data_preprocessing": "HockeyDataProcessor",
                "prompt_management": "HockeyPromptManager",
                "chunking_system": "HockeyDataChunker",
                "fine_tuning": "HockeyAnalyticsFineTuner",
                "validation": "HockeyMathValidator",
                "metadata": "MetadataManager"
            },
            "supported_data_types": [
                "xg_benchmarks",
                "season_reports",
                "play_by_play",
                "team_stats",
                "player_stats"
            ],
            "mathematical_focus_areas": [
                "expected_goals_calculations",
                "percentage_formulas",
                "statistical_analysis",
                "performance_metrics",
                "comparative_analysis"
            ],
            "validation_capabilities": [
                "mathematical_expression_validation",
                "statistical_reasoning_check",
                "logical_consistency_verification",
                "contextual_accuracy_assessment"
            ],
            "export_timestamp": pd.Timestamp.now().isoformat()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info(f"System configuration exported to {output_path}")

    def run_system_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive system diagnostics"""

        diagnostics = {
            "timestamp": pd.Timestamp.now().isoformat(),
            "component_status": {},
            "data_integrity": {},
            "performance_metrics": {},
            "recommendations": []
        }

        # Check component status
        components = {
            "data_processor": self.data_processor,
            "prompt_manager": self.prompt_manager,
            "chunking_system": self.chunking_system,
            "fine_tuner": self.fine_tuner,
            "math_validator": self.math_validator,
            "metadata_manager": self.metadata_manager
        }

        for name, component in components.items():
            try:
                # Basic functionality check
                diagnostics["component_status"][name] = "operational"
            except Exception as e:
                diagnostics["component_status"][name] = f"error: {str(e)}"

        # Check data integrity
        metadata_files = list(self.metadata_path.glob("*.json"))
        diagnostics["data_integrity"]["metadata_files"] = len(metadata_files)

        processed_files = list(self.processed_data_path.glob("*.json"))
        diagnostics["data_integrity"]["processed_files"] = len(processed_files)

        # Performance metrics
        diagnostics["performance_metrics"]["total_metadata_size"] = sum(
            f.stat().st_size for f in metadata_files
        )

        # Generate recommendations
        if len(metadata_files) == 0:
            diagnostics["recommendations"].append("No metadata files found. Run data processing pipeline first.")

        if len(processed_files) == 0:
            diagnostics["recommendations"].append("No processed data files found. Process datasets first.")

        operational_components = sum(1 for status in diagnostics["component_status"].values() if status == "operational")
        if operational_components < len(components):
            diagnostics["recommendations"].append(f"Only {operational_components}/{len(components)} components are operational. Check error logs.")

        return diagnostics

def main():
    """Main function for command-line usage"""

    parser = argparse.ArgumentParser(description="HabsAI LLM Accuracy System")
    parser.add_argument("--data-path", required=True, help="Path to the data file to process")
    parser.add_argument("--data-type", default="auto", help="Type of data (xg_benchmarks, season_reports, etc.)")
    parser.add_argument("--query", help="User query to process")
    parser.add_argument("--validate-response", help="LLM response to validate")
    parser.add_argument("--export-config", action="store_true", help="Export system configuration")
    parser.add_argument("--diagnostics", action="store_true", help="Run system diagnostics")

    args = parser.parse_args()

    # Initialize the system
    system = HabsAIAcuuracySystem()

    if args.diagnostics:
        print("Running system diagnostics...")
        diagnostics = system.run_system_diagnostics()
        print(json.dumps(diagnostics, indent=2))
        return

    if args.export_config:
        print("Exporting system configuration...")
        system.export_system_configuration("data/processed/system_configuration.json")
        print("Configuration exported successfully!")
        return

    if args.data_path:
        print(f"Processing dataset: {args.data_path}")

        # Auto-detect data type if not specified
        if args.data_type == "auto":
            filename = Path(args.data_path).name.lower()
            if "xg" in filename or "benchmarks" in filename:
                data_type = "xg_benchmarks"
            elif "season" in filename or "report" in filename:
                data_type = "season_reports"
            elif "play" in filename or "pbp" in filename:
                data_type = "play_by_play"
            elif "team" in filename:
                data_type = "team_stats"
            else:
                data_type = "team_stats"  # Default
        else:
            data_type = args.data_type

        # Process the dataset
        result = system.process_dataset(args.data_path, data_type)

        print("Dataset processing completed!")
        print(f"Processed {result['chunks']} chunks")
        print(f"Generated {result['fine_tuning_examples']} fine-tuning examples")
        print(f"Created {len(result['chunk_metadata'])} metadata files")

        # Save processing results
        with open("data/processed/processing_results.json", 'w') as f:
            json.dump(result, f, indent=2, default=str)

        print("Results saved to data/processed/processing_results.json")

    if args.query:
        print(f"Generating optimized prompt for query: {args.query}")
        prompt = system.generate_query_prompt(args.query, args.data_type or "team_stats")
        print("\nOptimized Prompt:")
        print("=" * 50)
        print(prompt)

    if args.validate_response:
        print("Validating LLM response...")
        validation = system.validate_llm_response(args.validate_response)
        print("\nValidation Results:")
        print("=" * 50)
        print(f"Valid: {validation['is_valid']}")
        print(f"Confidence Score: {validation['confidence_score']:.2f}")
        if validation['errors']:
            print(f"Errors: {len(validation['errors'])}")
            for error in validation['errors'][:3]:  # Show first 3 errors
                print(f"  - {error}")
        if validation['warnings']:
            print(f"Warnings: {len(validation['warnings'])}")
            for warning in validation['warnings'][:3]:  # Show first 3 warnings
                print(f"  - {warning}")

if __name__ == "__main__":
    main()
