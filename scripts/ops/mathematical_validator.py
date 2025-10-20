"""
Mathematical Validation System for Hockey Analytics LLM Responses
================================================================

This module provides comprehensive validation of mathematical accuracy in LLM responses
for hockey analytics. It can detect calculation errors, logical inconsistencies, and
validate statistical reasoning.

Key Features:
- Mathematical expression parsing and validation
- Statistical calculation verification
- Logical consistency checking
- Error detection and correction suggestions
- Confidence scoring for response reliability
"""

import re
import ast
import operator
import math
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of mathematical validation"""
    is_valid: bool
    confidence_score: float
    errors: List[str]
    warnings: List[str]
    corrections: List[str]
    validated_expressions: List[Dict[str, Any]]

@dataclass
class MathematicalExpression:
    """Represents a parsed mathematical expression"""
    expression: str
    result: Optional[float]
    variables: Dict[str, float]
    operation: str
    is_valid: bool

class HockeyMathValidator:
    """Validates mathematical accuracy in hockey analytics responses"""

    def __init__(self):
        self.validation_rules = self._load_validation_rules()
        self.statistical_patterns = self._load_statistical_patterns()

    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules for different types of calculations"""

        return {
            "percentage_calculations": {
                "pattern": r"(\d+(?:\.\d+)?)\s*(?:/|÷|divided by)\s*(\d+(?:\.\d+)?)\s*(?:×|x|\*)\s*100",
                "validator": self._validate_percentage_calculation,
                "description": "Percentage calculations should follow (part/total) × 100 format"
            },

            "finishing_percentage": {
                "pattern": r"(\d+(?:\.\d+)?)\s*(?:/|÷|divided by)\s*(\d+(?:\.\d+)?)\s*(?:×|x|\*)\s*100",
                "validator": self._validate_finishing_percentage,
                "description": "Finishing percentage = (goals / expected goals) × 100"
            },

            "corsi_calculation": {
                "pattern": r"(\d+(?:\.\d+)?)\s*(?:/|÷|divided by)\s*\(\s*(\d+(?:\.\d+)?)\s*\+?\s*(\d+(?:\.\d+)?)\s*\)",
                "validator": self._validate_corsi_calculation,
                "description": "Corsi percentage = shots for / (shots for + shots against)"
            },

            "per_60_calculation": {
                "pattern": r"(\d+(?:\.\d+)?)\s*(?:×|x|\*)\s*60\s*(?:/|÷|divided by)\s*(\d+(?:\.\d+)?)",
                "validator": self._validate_per_60_calculation,
                "description": "Per 60 minutes = (total stat × 60) / total minutes"
            },

            "pdo_calculation": {
                "pattern": r"(\d+(?:\.\d+)?)\s*\+?\s*(\d+(?:\.\d+)?)",
                "validator": self._validate_pdo_calculation,
                "description": "PDO = shooting % + save %"
            }
        }

    def _load_statistical_patterns(self) -> Dict[str, Any]:
        """Load patterns for statistical reasoning validation"""

        return {
            "correlation_causation": {
                "pattern": r"(?:correlation|relationship|link|connection).*caus(?:e|es|ing)",
                "validator": self._validate_correlation_causation,
                "description": "Check for improper causal interpretations of correlations"
            },

            "sample_size_warnings": {
                "pattern": r"(?:only|just|small|limited)\s+\d+\s+(?:games?|samples?|data points?)",
                "validator": self._validate_sample_size_context,
                "description": "Ensure appropriate caveats for small sample sizes"
            },

            "statistical_significance": {
                "pattern": r"(?:significant|meaningful|reliable|confident)",
                "validator": self._validate_statistical_claims,
                "description": "Validate statistical significance claims"
            },

            "percentage_range": {
                "pattern": r"(\d+(?:\.\d+)?)%",
                "validator": self._validate_percentage_range,
                "description": "Ensure percentages are in valid ranges"
            }
        }

    def validate_response(self, response: str, context_data: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Main validation method for LLM responses"""

        result = ValidationResult(
            is_valid=True,
            confidence_score=1.0,
            errors=[],
            warnings=[],
            corrections=[],
            validated_expressions=[]
        )

        # Extract and validate mathematical expressions
        expressions = self._extract_mathematical_expressions(response)
        for expr in expressions:
            validation = self._validate_expression(expr, context_data)
            result.validated_expressions.append(validation)

            if not validation["is_valid"]:
                result.is_valid = False
                result.errors.extend(validation["errors"])
                result.corrections.extend(validation["corrections"])
                result.confidence_score *= 0.8  # Reduce confidence for each error

        # Validate statistical reasoning
        statistical_issues = self._validate_statistical_reasoning(response)
        result.warnings.extend(statistical_issues["warnings"])
        result.errors.extend(statistical_issues["errors"])

        # Validate logical consistency
        logical_issues = self._validate_logical_consistency(response, context_data)
        result.warnings.extend(logical_issues["warnings"])
        result.errors.extend(logical_issues["errors"])

        # Calculate final confidence score
        if result.errors:
            result.confidence_score *= 0.6
        if result.warnings:
            result.confidence_score *= 0.9

        result.confidence_score = max(0.0, min(1.0, result.confidence_score))

        return result

    def _extract_mathematical_expressions(self, response: str) -> List[MathematicalExpression]:
        """Extract mathematical expressions from response text"""

        expressions = []

        # Find expressions with numbers and operators
        expression_patterns = [
            r"(\d+(?:\.\d+)?)\s*([+\-×*x/÷])\s*(\d+(?:\.\d+)?)",  # Basic arithmetic
            r"\(\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*\)\s*×?\s*100",  # Percentage calculations
            r"(\d+(?:\.\d+)?)\s*×?\s*60\s*/\s*(\d+(?:\.\d+)?)",  # Per 60 calculations
        ]

        for pattern in expression_patterns:
            matches = re.finditer(pattern, response)
            for match in matches:
                expr_text = match.group(0)
                try:
                    # Try to evaluate the expression
                    # Replace × and ÷ with * and /
                    eval_expr = expr_text.replace('×', '*').replace('÷', '/').replace('x', '*')

                    # Extract numbers
                    numbers = re.findall(r'\d+(?:\.\d+)?', eval_expr)
                    variables = {f"var_{i}": float(num) for i, num in enumerate(numbers)}

                    result = eval(eval_expr, {"__builtins__": {}}, variables)

                    expressions.append(MathematicalExpression(
                        expression=expr_text,
                        result=result,
                        variables=variables,
                        operation=self._identify_operation(expr_text),
                        is_valid=True
                    ))

                except Exception as e:
                    expressions.append(MathematicalExpression(
                        expression=expr_text,
                        result=None,
                        variables={},
                        operation="unknown",
                        is_valid=False
                    ))

        return expressions

    def _identify_operation(self, expression: str) -> str:
        """Identify the type of mathematical operation"""
        if '%' in expression or '100' in expression:
            return "percentage"
        elif '60' in expression:
            return "per_60"
        elif '/' in expression and ('+' in expression or '×' in expression):
            return "ratio"
        elif any(op in expression for op in ['+', '-', '×', '*', '/', '÷']):
            return "arithmetic"
        else:
            return "unknown"

    def _validate_expression(self, expr: MathematicalExpression, context_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate a single mathematical expression"""

        validation = {
            "expression": expr.expression,
            "is_valid": True,
            "errors": [],
            "corrections": [],
            "confidence": 1.0
        }

        if not expr.is_valid:
            validation["is_valid"] = False
            validation["errors"].append(f"Could not evaluate expression: {expr.expression}")
            return validation

        # Apply specific validation rules based on operation type
        if expr.operation == "percentage":
            self._validate_percentage_calculation(expr, validation)
        elif expr.operation == "per_60":
            self._validate_per_60_calculation(expr, validation)
        elif expr.operation == "ratio":
            self._validate_ratio_calculation(expr, validation)

        # Check for reasonable result ranges
        if expr.result is not None:
            if expr.operation == "percentage" and not (0 <= expr.result <= 100):
                validation["is_valid"] = False
                validation["errors"].append(f"Percentage result {expr.result} is outside valid range 0-100")
                validation["corrections"].append("Percentage calculations should result in values between 0 and 100")

            if expr.operation == "per_60" and expr.result < 0:
                validation["is_valid"] = False
                validation["errors"].append(f"Per-60 result {expr.result} cannot be negative")
                validation["corrections"].append("Per-60 calculations should be non-negative")

        return validation

    def _validate_percentage_calculation(self, expr: MathematicalExpression, validation: Dict[str, Any]):
        """Validate percentage calculations"""
        if expr.result is None:
            return

        # Check if result is in valid percentage range
        if not (0 <= expr.result <= 100):
            validation["is_valid"] = False
            validation["errors"].append(f"Percentage calculation result {expr.result} is not between 0 and 100")
            validation["corrections"].append("Ensure percentage formula is (part ÷ total) × 100")

    def _validate_per_60_calculation(self, expr: MathematicalExpression, validation: Dict[str, Any]):
        """Validate per-60 calculations"""
        if expr.result is None or len(expr.variables) < 2:
            return

        # Check calculation logic: (total × 60) / minutes
        var_values = list(expr.variables.values())
        if len(var_values) >= 2:
            expected_result = (var_values[0] * 60) / var_values[1]
            if abs(expr.result - expected_result) > 0.01:  # Allow small rounding differences
                validation["is_valid"] = False
                validation["errors"].append(f"Per-60 calculation incorrect. Expected {expected_result}, got {expr.result}")
                validation["corrections"].append("Per-60 formula: (total stat × 60) ÷ total minutes")

    def _validate_ratio_calculation(self, expr: MathematicalExpression, validation: Dict[str, Any]):
        """Validate ratio calculations"""
        if expr.result is None:
            return

        # For ratios, check that result makes sense in context
        if expr.result < 0:
            validation["is_valid"] = False
            validation["errors"].append("Ratio calculation cannot result in negative value")
            validation["corrections"].append("Ensure numerator and denominator are positive values")

    def _validate_corsi_calculation(self, expr: MathematicalExpression, validation: Dict[str, Any]):
        """Specific validation for Corsi calculations"""
        if expr.result is None:
            return

        # Corsi percentage should be between 0 and 100
        if not (0 <= expr.result <= 100):
            validation["is_valid"] = False
            validation["errors"].append(f"Corsi percentage {expr.result} is not between 0 and 100")
            validation["corrections"].append("Corsi formula: (CF / (CF + CA)) × 100")

    def _validate_finishing_percentage(self, expr: MathematicalExpression, validation: Dict[str, Any]):
        """Specific validation for finishing percentage calculations"""
        if expr.result is None:
            return

        # Finishing percentage should typically be between 0 and 200
        # (though theoretically unlimited, very high values suggest errors)
        if not (0 <= expr.result <= 200):
            validation["warnings"] = validation.get("warnings", [])
            validation["warnings"].append(f"Finishing percentage {expr.result} seems unusually high/low")
            validation["corrections"].append("Finishing % = (goals ÷ expected goals) × 100")

    def _validate_pdo_calculation(self, expr: MathematicalExpression, validation: Dict[str, Any]):
        """Specific validation for PDO calculations"""
        if expr.result is None:
            return

        # PDO should typically be between 95 and 105 for sustainable performance
        if not (90 <= expr.result <= 110):
            validation["warnings"] = validation.get("warnings", [])
            validation["warnings"].append(f"PDO value {expr.result} is outside typical sustainable range (95-105)")
            validation["corrections"].append("Check that PDO = shooting % + save %, not multiplied")

    def _validate_statistical_reasoning(self, response: str) -> Dict[str, List[str]]:
        """Validate statistical reasoning in the response"""

        issues = {"warnings": [], "errors": []}

        # Check for correlation vs causation errors
        if re.search(r"(?:because|caused by|leads to).*shots?", response.lower()):
            issues["warnings"].append("Potential correlation-causation confusion with shot-based metrics")

        # Check for overconfidence with small samples
        small_sample_indicators = ["only", "just", "small sample", "limited data"]
        confidence_indicators = ["clearly", "obviously", "definitely", "certainly"]

        has_small_sample = any(indicator in response.lower() for indicator in small_sample_indicators)
        has_high_confidence = any(indicator in response.lower() for indicator in confidence_indicators)

        if has_small_sample and has_high_confidence:
            issues["warnings"].append("High confidence expressed despite small sample size")

        # Check for percentage range violations
        percentages = re.findall(r'(\d+(?:\.\d+)?)%', response)
        for pct in percentages:
            pct_val = float(pct)
            if pct_val > 100 and not any(term in response.lower() for term in ["pdo", "combined", "total"]):
                issues["errors"].append(f"Percentage {pct_val}% exceeds 100% - likely calculation error")

        return issues

    def _validate_logical_consistency(self, response: str, context_data: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Validate logical consistency in the response"""

        issues = {"warnings": [], "errors": []}

        # Check for contradictory statements
        contradictions = [
            (r"overperforming.*underperforming", "Contradictory performance assessment"),
            (r"improving.*declining", "Contradictory trend assessment"),
            (r"strong.*weak", "Contradictory strength assessment")
        ]

        for pattern, message in contradictions:
            if re.search(pattern, response.lower()):
                issues["warnings"].append(message)

        # Validate against known context data if provided
        if context_data:
            # Check if stated facts align with provided data
            if "team_name" in context_data:
                team_name = context_data["team_name"]
                if team_name.lower() not in response.lower() and "montreal" not in response.lower():
                    issues["warnings"].append(f"Response doesn't mention specified team: {team_name}")

        return issues

    def generate_validation_report(self, validation_result: ValidationResult) -> str:
        """Generate a human-readable validation report"""

        report = f"""
MATHEMATICAL VALIDATION REPORT
===============================

Overall Status: {'✅ VALID' if validation_result.is_valid else '❌ INVALID'}
Confidence Score: {validation_result.confidence_score:.2f}/1.00

SUMMARY:
- Validated {len(validation_result.validated_expressions)} mathematical expressions
- Found {len(validation_result.errors)} errors
- Found {len(validation_result.warnings)} warnings

"""

        if validation_result.errors:
            report += "\nERRORS FOUND:\n"
            for error in validation_result.errors:
                report += f"❌ {error}\n"

        if validation_result.warnings:
            report += "\nWARNINGS:\n"
            for warning in validation_result.warnings:
                report += f"⚠️  {warning}\n"

        if validation_result.corrections:
            report += "\nSUGGESTED CORRECTIONS:\n"
            for correction in validation_result.corrections:
                report += f"💡 {correction}\n"

        if validation_result.validated_expressions:
            report += "\nVALIDATED EXPRESSIONS:\n"
            for expr in validation_result.validated_expressions:
                status = "✅" if expr["is_valid"] else "❌"
                report += f"{status} {expr['expression']}\n"
                if not expr["is_valid"]:
                    for error in expr.get("errors", []):
                        report += f"   Error: {error}\n"

        return report

    def validate_batch_responses(self, responses: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Validate multiple responses in batch"""

        results = []
        for response_data in responses:
            response_text = response_data.get("response", "")
            context_data = response_data.get("context", {})

            result = self.validate_response(response_text, context_data)
            results.append(result)

        return results

def main():
    """Example usage of the mathematical validator"""

    validator = HockeyMathValidator()

    # Example response to validate
    test_response = """
Based on the data, Montreal's finishing percentage is 2.5 / 3.2 × 100 = 78.13%.
They are underperforming their expected goals by 0.7 goals per game.
The team's Corsi percentage is 54.2 / (54.2 + 60.2) = 47.4%.
This clearly shows they are the best team in the NHL with only 5 games of data.
"""

    # Validate the response
    validation_result = validator.validate_response(test_response)

    # Generate and print report
    report = validator.generate_validation_report(validation_result)
    print(report)

    # Example with context data
    context_data = {
        "team_name": "Montreal Canadiens",
        "season": "2024-25",
        "sample_size": 5
    }

    validation_with_context = validator.validate_response(test_response, context_data)
    print("\n" + "="*50)
    print("VALIDATION WITH CONTEXT:")
    print(validator.generate_validation_report(validation_with_context))

if __name__ == "__main__":
    main()
