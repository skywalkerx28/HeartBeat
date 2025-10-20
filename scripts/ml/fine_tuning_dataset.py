"""
Fine-Tuning Dataset for Hockey Analytics Mathematical Reasoning
=============================================================

This module creates a comprehensive fine-tuning dataset specifically designed to train
LLMs on mathematical accuracy and contextual understanding of hockey analytics.

The dataset includes:
- Mathematical calculation examples
- Statistical reasoning patterns
- Contextual interpretation scenarios
- Error identification and correction
- Comparative analysis reasoning
"""

import json
import pandas as pd
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import random
from pathlib import Path

@dataclass
class FineTuningExample:
    """Represents a single fine-tuning example"""
    instruction: str
    input_data: Dict[str, Any]
    expected_output: str
    mathematical_focus: str
    difficulty_level: str
    category: str

class HockeyAnalyticsFineTuner:
    """Creates fine-tuning datasets for hockey analytics mathematical reasoning"""

    def __init__(self):
        self.examples = []
        self.mathematical_patterns = self._load_mathematical_patterns()

    def _load_mathematical_patterns(self) -> Dict[str, List[str]]:
        """Load mathematical reasoning patterns for different scenarios"""
        return {
            "expected_goals": [
                "Calculate finishing percentage: (Actual Goals / Expected Goals) × 100",
                "Determine over/under performance: Actual Goals - Expected Goals",
                "Compare efficiency: (Goals/Game) / (xG/Game) ratio",
                "Analyze conversion by game state: High-danger xG vs low-danger xG"
            ],
            "percentage_calculations": [
                "Convert to percentage: (Part / Total) × 100",
                "Calculate differential: Team Stat - Opponent Stat",
                "Determine relative performance: (Team / League Average) × 100",
                "Compute efficiency ratios: Output / Input metrics"
            ],
            "statistical_comparisons": [
                "Calculate standard deviations from league average",
                "Determine percentile rankings among 32 NHL teams",
                "Compute correlation coefficients between related metrics",
                "Identify statistical significance of performance differences"
            ],
            "rate_calculations": [
                "Per 60 minutes: (Total Stat × 60) / Total Minutes",
                "Per game rates: Total Stat / Games Played",
                "Efficiency rates: Goals / Shot Attempts × 100",
                "Conversion rates: Goals / Scoring Chances × 100"
            ]
        }

    def generate_comprehensive_dataset(self, num_examples: int = 1000) -> List[Dict[str, Any]]:
        """Generate a comprehensive fine-tuning dataset"""

        examples = []

        # Generate examples for each category
        categories = {
            "expected_goals_analysis": self._generate_xg_examples,
            "statistical_calculations": self._generate_calculation_examples,
            "comparative_analysis": self._generate_comparison_examples,
            "performance_evaluation": self._generate_performance_examples,
            "error_correction": self._generate_error_examples,
            "contextual_reasoning": self._generate_context_examples
        }

        examples_per_category = num_examples // len(categories)

        for category_name, generator_func in categories.items():
            category_examples = generator_func(examples_per_category)
            examples.extend(category_examples)

        # Shuffle examples for better training
        random.shuffle(examples)

        return examples

    def _generate_xg_examples(self, num_examples: int) -> List[Dict[str, Any]]:
        """Generate expected goals analysis examples"""

        examples = []

        xg_scenarios = [
            {
                "scenario": "finishing_efficiency",
                "data": {"actual_goals": 2.5, "expected_goals": 3.2, "games": 10},
                "question": "Calculate Montreal's finishing percentage and determine if they're over or underperforming.",
                "correct_calculation": "Finishing % = (2.5 / 3.2) × 100 = 78.13%. Underperforming by 0.7 goals per game."
            },
            {
                "scenario": "game_state_analysis",
                "data": {"xg_advantage": 3.5, "goals_advantage": 2.8, "xg_disadvantage": 1.2, "goals_disadvantage": 1.8},
                "question": "Compare finishing efficiency when Montreal has XG advantage vs disadvantage.",
                "correct_calculation": "Advantage: (2.8 / 3.5) × 100 = 80%. Disadvantage: (1.8 / 1.2) × 100 = 150%. Better finishing when dominating."
            },
            {
                "scenario": "conversion_rates",
                "data": {"slot_shots": 45, "slot_goals": 12, "outside_shots": 120, "outside_goals": 8},
                "question": "Calculate conversion rates for different shot types.",
                "correct_calculation": "Slot conversion: (12 / 45) × 100 = 26.67%. Outside conversion: (8 / 120) × 100 = 6.67%. Slot shots much more dangerous."
            }
        ]

        for i in range(num_examples):
            scenario = random.choice(xg_scenarios)

            example = {
                "instruction": "Analyze the expected goals data with mathematical precision. Show your calculations clearly.",
                "input": f"""
Data: {json.dumps(scenario['data'], indent=2)}
Question: {scenario['question']}
""",
                "output": f"""
Mathematical Analysis:
{scenario['correct_calculation']}

Key Insights:
- All calculations use proper mathematical formulas
- Percentages are calculated as (part/total) × 100
- Efficiency metrics provide clear performance indicators
- Context matters for interpreting results
""",
                "mathematical_focus": "expected_goals_calculations",
                "difficulty_level": "intermediate",
                "category": "expected_goals_analysis"
            }
            examples.append(example)

        return examples

    def _generate_calculation_examples(self, num_examples: int) -> List[Dict[str, Any]]:
        """Generate statistical calculation examples"""

        examples = []

        calculation_scenarios = [
            {
                "type": "percentage_calculation",
                "data": {"shots_for": 1560, "shots_against": 1420, "games": 20},
                "question": "Calculate shot attempt percentage and determine if this indicates offensive or defensive dominance.",
                "solution": "Corsi For % = (1560 / (1560 + 1420)) × 100 = (1560 / 2980) × 100 = 52.35%. Indicates slight offensive dominance."
            },
            {
                "type": "per_60_calculation",
                "data": {"player_shots": 45, "player_toi": 1200, "team_shots": 1560, "team_toi": 24000},
                "question": "Calculate player's shots per 60 minutes and compare to team average.",
                "solution": "Player shots/60 = (45 × 60) / 1200 = 2700 / 1200 = 2.25. Team shots/60 = (1560 × 60) / 24000 = 93600 / 24000 = 3.9. Player underperforming team average."
            },
            {
                "type": "efficiency_calculation",
                "data": {"pp_goals": 12, "pp_opportunities": 45, "pk_goals_against": 8, "pk_opportunities": 42},
                "question": "Calculate powerplay and penalty kill percentages.",
                "solution": "PP% = (12 / 45) × 100 = 26.67%. PK% = ((42 - 8) / 42) × 100 = (34 / 42) × 100 = 80.95%. Solid special teams performance."
            }
        ]

        for i in range(num_examples):
            scenario = random.choice(calculation_scenarios)

            example = {
                "instruction": "Perform the statistical calculations with mathematical accuracy. Show all steps clearly.",
                "input": f"""
Data: {json.dumps(scenario['data'], indent=2)}
Calculation Required: {scenario['question']}
""",
                "output": f"""
Step-by-Step Calculation:
{scenario['solution']}

Verification:
- All formulas applied correctly
- Units and context preserved
- Results are mathematically sound
- Interpretation is data-driven
""",
                "mathematical_focus": "statistical_calculations",
                "difficulty_level": "intermediate",
                "category": "statistical_calculations"
            }
            examples.append(example)

        return examples

    def _generate_comparison_examples(self, num_examples: int) -> List[Dict[str, Any]]:
        """Generate comparative analysis examples"""

        examples = []

        comparison_scenarios = [
            {
                "type": "league_ranking",
                "data": {"team_stat": 2.8, "league_average": 2.6, "league_leader": 3.2, "team_rank": 8},
                "question": "Analyze Montreal's performance relative to league standards.",
                "analysis": "Montreal ranks 8th out of 32 NHL teams with 2.8 goals/game. League average is 2.6, league leader has 3.2. Montreal is above average but not elite."
            },
            {
                "type": "percentile_calculation",
                "data": {"team_value": 92.5, "league_values": [85, 87, 89, 91, 92, 93, 94, 95, 96, 97]},
                "question": "Calculate Montreal's percentile ranking for this metric.",
                "analysis": "With 92.5, Montreal ranks above 50% of teams (6th out of 10 in this sample). Percentile = (6 / 10) × 100 = 60th percentile."
            },
            {
                "type": "year_over_year",
                "data": {"current_season": 2.8, "previous_season": 2.4, "league_change": 0.1},
                "question": "Compare year-over-year performance improvement.",
                "analysis": "Montreal improved from 2.4 to 2.8 (+16.67% improvement). League improved by 0.1 (+4.17%). Montreal outperformed league improvement."
            }
        ]

        for i in range(num_examples):
            scenario = random.choice(comparison_scenarios)

            example = {
                "instruction": "Perform comparative analysis with mathematical precision and clear reasoning.",
                "input": f"""
Comparative Data: {json.dumps(scenario['data'], indent=2)}
Analysis Request: {scenario['question']}
""",
                "output": f"""
Comparative Analysis:
{scenario['analysis']}

Mathematical Foundation:
- Rankings based on objective measurements
- Percentiles calculated as (position / total) × 100
- Comparisons use consistent baselines
- Context provided for meaningful interpretation
""",
                "mathematical_focus": "comparative_statistics",
                "difficulty_level": "advanced",
                "category": "comparative_analysis"
            }
            examples.append(example)

        return examples

    def _generate_performance_examples(self, num_examples: int) -> List[Dict[str, Any]]:
        """Generate performance evaluation examples"""

        examples = []

        performance_scenarios = [
            {
                "type": "pdo_analysis",
                "data": {"shooting_pct": 12.5, "save_pct": 87.5, "pdo": 100.0},
                "question": "Analyze PDO and determine if performance is sustainable.",
                "evaluation": "PDO = 12.5 + 87.5 = 100.0 (league average). Performance appears sustainable as it matches expected outcomes."
            },
            {
                "type": "zone_start_analysis",
                "data": {"offensive_zone_starts": 52, "shots_for": 32, "shots_against": 28},
                "question": "Evaluate the impact of zone starts on shot differential.",
                "evaluation": "52% offensive zone starts should create positive shot differential. Actual: +4 shots. Underperforming expectation by ~8 shots."
            },
            {
                "type": "expected_vs_actual",
                "data": {"actual_goals": 2.6, "expected_goals": 2.8, "actual_goals_against": 2.4, "expected_goals_against": 2.6},
                "question": "Evaluate overall team performance relative to expectations.",
                "evaluation": "Goals: -0.2 below expectation. Goals against: +0.2 above expectation. Net: -0.4 goals vs expectation. Slightly underperforming."
            }
        ]

        for i in range(num_examples):
            scenario = random.choice(performance_scenarios)

            example = {
                "instruction": "Evaluate performance with mathematical rigor and contextual understanding.",
                "input": f"""
Performance Data: {json.dumps(scenario['data'], indent=2)}
Evaluation Request: {scenario['question']}
""",
                "output": f"""
Performance Evaluation:
{scenario['evaluation']}

Analytical Framework:
- Metrics compared to established baselines
- Statistical significance considered
- Context and qualifiers provided
- Actionable insights identified
""",
                "mathematical_focus": "performance_evaluation",
                "difficulty_level": "advanced",
                "category": "performance_evaluation"
            }
            examples.append(example)

        return examples

    def _generate_error_examples(self, num_examples: int) -> List[Dict[str, Any]]:
        """Generate examples of identifying and correcting mathematical errors"""

        examples = []

        error_scenarios = [
            {
                "type": "percentage_error",
                "incorrect": "Team scored 15 goals on 120 shots, so shooting percentage is 15/120 = 12.5%",
                "question": "Identify and correct the mathematical error in this shooting percentage calculation.",
                "correction": "Correct formula: (15 ÷ 120) × 100 = 12.5%. The original is mathematically correct but should specify it's a percentage."
            },
            {
                "type": "correlation_error",
                "incorrect": "Since Montreal scores more goals when they have more shots, shots cause goals.",
                "question": "Identify the logical error in this causal interpretation.",
                "correction": "This confuses correlation with causation. More shots may correlate with more goals, but doesn't prove causation. Could be due to better play or zone starts."
            },
            {
                "type": "sample_size_error",
                "incorrect": "With only 5 games of data, Montreal is clearly the best team in the NHL.",
                "question": "Identify the statistical error in this conclusion.",
                "correction": "Sample size of 5 is too small for reliable conclusions. Results could be due to random variation. Need larger sample for statistical significance."
            }
        ]

        for i in range(num_examples):
            scenario = random.choice(error_scenarios)

            example = {
                "instruction": "Identify mathematical or logical errors and provide correct analysis.",
                "input": f"""
Potentially Incorrect Analysis: {scenario['incorrect']}
Question: {scenario['question']}
""",
                "output": f"""
Error Identification and Correction:
{scenario['correction']}

Key Learning Points:
- Mathematical accuracy is crucial for valid analysis
- Context and statistical significance matter
- Correlation does not imply causation
- Sample size affects reliability of conclusions
""",
                "mathematical_focus": "error_identification",
                "difficulty_level": "advanced",
                "category": "error_correction"
            }
            examples.append(example)

        return examples

    def _generate_context_examples(self, num_examples: int) -> List[Dict[str, Any]]:
        """Generate contextual reasoning examples"""

        examples = []

        context_scenarios = [
            {
                "type": "game_situation_context",
                "data": {"even_strength_xg": 2.2, "powerplay_xg": 0.8, "total_xg": 3.0},
                "question": "Explain why total xG might be misleading for evaluating team performance.",
                "explanation": "Even strength xG (2.2) represents sustainable performance. Powerplay xG (0.8) is context-dependent. Total xG doesn't account for quality of opportunities."
            },
            {
                "type": "opponent_quality_context",
                "data": {"vs_top_teams": 2.0, "vs_middle_teams": 2.8, "vs_bottom_teams": 3.2},
                "question": "Analyze performance variation by opponent quality and its implications.",
                "explanation": "Performance varies significantly by opponent: 2.0 vs top teams, 2.8 vs middle, 3.2 vs bottom. Suggests team performs better against weaker competition, indicating potential strategic vulnerabilities."
            },
            {
                "type": "seasonal_context",
                "data": {"early_season": 2.4, "mid_season": 2.6, "late_season": 2.8, "playoff_implication": "Yes"},
                "question": "Interpret performance trend and playoff implications.",
                "explanation": "Upward trend from 2.4 to 2.8 suggests improvement over season. Late-season form (2.8) is promising for playoffs. Trend analysis more valuable than single point estimates."
            }
        ]

        for i in range(num_examples):
            scenario = random.choice(context_scenarios)

            example = {
                "instruction": "Provide contextually rich analysis that considers situational factors and broader implications.",
                "input": f"""
Contextual Data: {json.dumps(scenario['data'], indent=2)}
Analysis Request: {scenario['question']}
""",
                "output": f"""
Contextual Analysis:
{scenario['explanation']}

Contextual Reasoning Framework:
- Performance varies by game situation and opponent
- Trends often more meaningful than single data points
- Statistical significance and sample size considered
- Broader strategic implications identified
""",
                "mathematical_focus": "contextual_reasoning",
                "difficulty_level": "expert",
                "category": "contextual_reasoning"
            }
            examples.append(example)

        return examples

    def save_dataset(self, examples: List[Dict[str, Any]], output_path: str):
        """Save the fine-tuning dataset to JSONL format"""

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for example in examples:
                # Convert to the format expected by the fine-tuning system
                formatted_example = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a hockey analytics expert. Provide mathematically accurate analysis of hockey performance data."
                        },
                        {
                            "role": "user",
                            "content": example["instruction"] + "\n\n" + example["input"]
                        },
                        {
                            "role": "assistant",
                            "content": example["output"]
                        }
                    ],
                    "metadata": {
                        "mathematical_focus": example["mathematical_focus"],
                        "difficulty_level": example["difficulty_level"],
                        "category": example["category"]
                    }
                }
                f.write(json.dumps(formatted_example, ensure_ascii=False) + '\n')

        print(f"Saved {len(examples)} fine-tuning examples to {output_path}")

    def create_balanced_subset(self, examples: List[Dict[str, Any]], target_size: int = 500) -> List[Dict[str, Any]]:
        """Create a balanced subset of examples across all categories and difficulty levels"""

        # Group examples by category and difficulty
        category_groups = {}
        difficulty_groups = {}

        for example in examples:
            category = example["category"]
            difficulty = example["difficulty_level"]

            if category not in category_groups:
                category_groups[category] = []
            if difficulty not in difficulty_groups:
                difficulty_groups[difficulty] = []

            category_groups[category].append(example)
            difficulty_groups[difficulty].append(example)

        # Calculate target size per group
        num_categories = len(category_groups)
        num_difficulties = len(difficulty_groups)

        examples_per_category = target_size // num_categories
        examples_per_difficulty = target_size // num_difficulties

        balanced_examples = []

        # Sample from each category
        for category, category_examples in category_groups.items():
            sample_size = min(examples_per_category, len(category_examples))
            balanced_examples.extend(random.sample(category_examples, sample_size))

        # Ensure we have the target size
        if len(balanced_examples) < target_size:
            remaining_needed = target_size - len(balanced_examples)
            additional_examples = random.sample(examples, remaining_needed)
            balanced_examples.extend(additional_examples)

        random.shuffle(balanced_examples)
        return balanced_examples[:target_size]

def main():
    """Generate and save fine-tuning datasets"""

    tuner = HockeyAnalyticsFineTuner()

    print("Generating comprehensive fine-tuning dataset...")

    # Generate full dataset
    full_dataset = tuner.generate_comprehensive_dataset(1000)
    print(f"Generated {len(full_dataset)} examples")

    # Create balanced subset
    balanced_dataset = tuner.create_balanced_subset(full_dataset, 500)
    print(f"Created balanced subset of {len(balanced_dataset)} examples")

    # Save datasets
    tuner.save_dataset(full_dataset, "data/processed/fine_tuning/full_hockey_analytics_dataset.jsonl")
    tuner.save_dataset(balanced_dataset, "data/processed/fine_tuning/balanced_hockey_analytics_dataset.jsonl")

    # Print dataset statistics
    categories = {}
    difficulties = {}

    for example in full_dataset:
        category = example["category"]
        difficulty = example["difficulty_level"]

        categories[category] = categories.get(category, 0) + 1
        difficulties[difficulty] = difficulties.get(difficulty, 0) + 1

    print("\nDataset Statistics:")
    print("Categories:")
    for category, count in categories.items():
        print(f"  {category}: {count}")

    print("\nDifficulty Levels:")
    for difficulty, count in difficulties.items():
        print(f"  {difficulty}: {count}")

    print("\nFine-tuning datasets saved successfully!")

if __name__ == "__main__":
    main()
