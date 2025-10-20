#!/usr/bin/env python3
"""
Training Session 2 Dataset Generation Framework
HeartBeat Engine - Montreal Canadiens Analytics Platform

Generates sophisticated training examples for LangGraph integration
with tool orchestration, multi-step reasoning, and identity-aware responses.
"""

import json
import random
from typing import Dict, List, Any
from dataclasses import dataclass
from pathlib import Path

@dataclass 
class TrainingExample:
    """Structure for training examples with metadata"""
    category: str
    user_role: str
    complexity: str
    tools_used: List[str]
    messages: List[Dict[str, str]]

class Session2DatasetGenerator:
    """Generates sophisticated training examples for Mistral Session 2"""
    
    def __init__(self):
        self.enhanced_system_prompt = """You are an elite hockey analytics orchestrator for the Montreal Canadiens organization. You serve coaches, players, scouts, analysts, and staff with professional-grade insights by intelligently coordinating multiple analytical tools and data sources.

CORE CAPABILITIES:
- Orchestrate complex multi-step analysis workflows using RAG retrieval and real-time data tools
- Process natural language queries by determining optimal tool sequences and data requirements  
- Generate evidence-based insights with clear source attribution from all tool outputs
- Adapt communication style and data scope based on user role (coach/player/analyst/staff)
- Handle identity-aware data access and permission-based information filtering

TOOL ORCHESTRATION:
- Use [TOOL: vector_search] for hockey knowledge, rules, and strategic context
- Use [TOOL: parquet_query] for real-time player/team statistics and game data
- Use [TOOL: calculate_advanced_metrics] for xG, Corsi, zone analysis, and possession metrics
- Use [TOOL: matchup_analysis] for opponent analysis and tactical recommendations
- Use [TOOL: visualization] for heatmaps, charts, and statistical displays
- Always specify tool usage clearly and integrate results meaningfully

COMMUNICATION STANDARDS:
- Provide multi-step reasoning that shows your analytical workflow
- Back all insights with specific data points and source attribution
- Use authentic coach and player terminology appropriate for Montreal Canadiens personnel
- Structure responses with clear evidence chains and actionable recommendations
- Maintain professional communication standards with clean technical language

Your responses should demonstrate sophisticated analytical orchestration while remaining accessible to hockey personnel in operational and strategic contexts."""

        # Montreal Canadiens current roster and context
        self.mtl_players = [
            "Suzuki", "Caufield", "Slafkovsky", "Dach", "Newhook", "Hutson", "Guhle", 
            "Matheson", "Savard", "Barron", "Xhekaj", "Evans", "Gallagher", "Anderson",
            "Armia", "Dvorak", "Pezzetta", "Struble", "Primeau", "Montembeault"
        ]
        
        self.opponents = [
            "Toronto", "Boston", "Tampa Bay", "Florida", "Buffalo", "Ottawa", "Detroit",
            "New York Rangers", "New Jersey", "Philadelphia", "Washington", "Carolina"
        ]
        
        # Tool categories with realistic usage patterns
        self.tool_patterns = {
            "statistical_analysis": ["parquet_query", "calculate_advanced_metrics"],
            "opponent_study": ["matchup_analysis", "vector_search", "parquet_query"],
            "player_development": ["player_analysis", "calculate_advanced_metrics", "development_focus"],
            "tactical_planning": ["matchup_analysis", "vector_search", "visualization"],
            "performance_review": ["parquet_query", "calculate_advanced_metrics", "comparison_analysis"]
        }

    def generate_tool_integration_example(self) -> TrainingExample:
        """Generate sophisticated tool orchestration examples"""
        
        scenarios = [
            {
                "query": f"Compare {random.choice(self.mtl_players)}'s zone exit success when paired with different defensemen over the last 15 games",
                "tools": ["parquet_query", "calculate_zone_stats", "matchup_analysis"],
                "complexity": "multi-step"
            },
            {
                "query": f"Analyze our power play efficiency against {random.choice(self.opponents)}'s penalty kill system",
                "tools": ["parquet_query", "vector_search", "matchup_analysis", "visualization"],
                "complexity": "complex"
            },
            {
                "query": f"What's the impact of {random.choice(self.mtl_players)}'s line combinations on our defensive zone coverage?",
                "tools": ["parquet_query", "calculate_advanced_metrics", "defensive_analysis"],
                "complexity": "advanced"
            }
        ]
        
        scenario = random.choice(scenarios)
        
        # Generate realistic tool-based response
        response = self._generate_tool_response(scenario["query"], scenario["tools"])
        
        return TrainingExample(
            category="tool_integration",
            user_role="coach",
            complexity=scenario["complexity"],
            tools_used=scenario["tools"],
            messages=[
                {"role": "system", "content": self.enhanced_system_prompt},
                {"role": "user", "content": scenario["query"]},
                {"role": "assistant", "content": response}
            ]
        )

    def generate_multi_turn_conversation(self) -> List[TrainingExample]:
        """Generate multi-turn analytical conversations"""
        
        conversation_starters = [
            "How has our penalty kill evolved since the coaching change?",
            "What are the patterns in our power play struggles?", 
            "Which line combinations are working best for us?",
            "How do we match up against playoff teams?"
        ]
        
        starter = random.choice(conversation_starters)
        
        # First turn
        turn_1 = TrainingExample(
            category="multi_turn",
            user_role="analyst",
            complexity="baseline",
            tools_used=["parquet_query", "calculate_advanced_metrics"],
            messages=[
                {"role": "system", "content": self.enhanced_system_prompt},
                {"role": "user", "content": starter},
                {"role": "assistant", "content": self._generate_analytical_response(starter)}
            ]
        )
        
        # Follow-up turn
        follow_ups = [
            "Which specific opponents have we struggled against in this area?",
            "What tactical adjustments would you recommend?",
            "How does this compare to our performance last season?",
            "Which players are driving these trends?"
        ]
        
        follow_up = random.choice(follow_ups)
        
        turn_2 = TrainingExample(
            category="multi_turn_followup",
            user_role="analyst", 
            complexity="deepdive",
            tools_used=["opponent_analysis", "tactical_breakdown", "comparison_analysis"],
            messages=[
                {"role": "system", "content": self.enhanced_system_prompt},
                {"role": "user", "content": follow_up},
                {"role": "assistant", "content": self._generate_followup_response(follow_up)}
            ]
        )
        
        return [turn_1, turn_2]

    def generate_role_specific_example(self, role: str) -> TrainingExample:
        """Generate role-specific responses (coach/player/analyst)"""
        
        role_prompts = {
            "coach": "You are responding to a Montreal Canadiens coach. Provide strategic insights with tactical depth suitable for game planning and lineup decisions.",
            "player": "You are responding to a Montreal Canadiens player. Provide personal performance insights with actionable development focus areas.",
            "analyst": "You are responding to a Montreal Canadiens analyst. Provide detailed statistical insights with methodological rigor suitable for front office evaluation."
        }
        
        role_queries = {
            "coach": [
                f"How should we handle {random.choice(self.opponents)}'s top line in our building?",
                "What defensive pairing adjustments should we make for the next game?",
                "Which power play units are most effective against different penalty kill systems?"
            ],
            "player": [
                "How can I improve my faceoff performance in high-pressure situations?",
                "What areas of my defensive game need the most work?",
                "How effective am I in different line combinations?"
            ],
            "analyst": [
                "What's our actual shot quality differential compared to league average?",
                "How do our underlying metrics compare in back-to-back games?",
                "Which advanced statistics best predict our future performance?"
            ]
        }
        
        query = random.choice(role_queries[role])
        system_prompt = role_prompts[role]
        
        return TrainingExample(
            category="role_specific",
            user_role=role,
            complexity="targeted",
            tools_used=["parquet_query", "calculate_advanced_metrics", "role_analysis"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
                {"role": "assistant", "content": self._generate_role_response(query, role)}
            ]
        )

    def generate_evidence_based_example(self) -> TrainingExample:
        """Generate examples emphasizing source attribution and evidence"""
        
        evidence_queries = [
            "Is our improved record actually sustainable based on underlying metrics?",
            "Are we actually better defensively or just facing weaker opposition?", 
            "What's driving our power play improvement - personnel or system changes?",
            "How much of our recent success is due to goaltending vs team defense?"
        ]
        
        query = random.choice(evidence_queries)
        
        return TrainingExample(
            category="evidence_based",
            user_role="analyst",
            complexity="methodical",
            tools_used=["parquet_query", "statistical_analysis", "strength_adjustment"],
            messages=[
                {"role": "system", "content": "Always provide evidence-based responses with clear source attribution from tools and data queries."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": self._generate_evidence_response(query)}
            ]
        )

    def generate_error_handling_example(self) -> TrainingExample:
        """Generate examples of graceful error handling and clarification requests"""
        
        ambiguous_queries = [
            "How did we do in that overtime game?",
            "What about our power play against Boston?",
            "Can you check Smith's stats?",
            "How are we doing lately?"
        ]
        
        query = random.choice(ambiguous_queries)
        
        return TrainingExample(
            category="error_handling",
            user_role="general",
            complexity="clarification",
            tools_used=["clarification_request"],
            messages=[
                {"role": "system", "content": "Handle incomplete data gracefully and ask clarifying questions when needed."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": self._generate_clarification_response(query)}
            ]
        )

    def _generate_tool_response(self, query: str, tools: List[str]) -> str:
        """Generate realistic tool-based analytical response"""
        
        response_parts = [
            f"I'll analyze this query using a multi-step approach:",
            "",
            f"**Step 1: [TOOL: {tools[0]}]** - {self._get_tool_description(tools[0])}",
            f"- {self._generate_realistic_stat()}",
            f"- {self._generate_realistic_stat()}",
            "",
            f"**Step 2: [TOOL: {tools[1]}]** - {self._get_tool_description(tools[1])}",
            f"- {self._generate_advanced_metric()}",
            f"- {self._generate_advanced_metric()}",
            "",
            "**Key Insights:**",
            f"1. {self._generate_insight()}",
            f"2. {self._generate_tactical_note()}",
            f"3. {self._generate_recommendation()}",
            "",
            f"**Recommendation**: {self._generate_strategic_recommendation()}"
        ]
        
        return "\n".join(response_parts)

    def _generate_analytical_response(self, query: str) -> str:
        """Generate detailed analytical response with metrics"""
        return f"**[TOOL: parquet_query]** - Analyzing recent performance trends:\n\n{self._generate_performance_analysis()}\n\n**[TOOL: calculate_advanced_metrics]** - Advanced statistical breakdown:\n{self._generate_advanced_analysis()}\n\n**Key Findings:**\n{self._generate_key_findings()}"

    def _generate_followup_response(self, query: str) -> str:
        """Generate follow-up response with deeper analysis"""
        return f"**[TOOL: opponent_analysis]** - Detailed breakdown by opponent:\n\n{self._generate_opponent_breakdown()}\n\n**[TOOL: tactical_breakdown]** - Strategic implications:\n{self._generate_tactical_implications()}\n\n**Recommendation**: {self._generate_specific_recommendation()}"

    def _generate_role_response(self, query: str, role: str) -> str:
        """Generate role-specific response"""
        if role == "coach":
            return f"**[TOOL: matchup_analysis]** - Tactical assessment:\n\n{self._generate_coach_analysis()}\n\n**Strategic Game Plan:**\n{self._generate_game_plan()}"
        elif role == "player":
            return f"**[TOOL: player_analysis]** - Your performance breakdown:\n\n{self._generate_player_feedback()}\n\n**Development Focus:**\n{self._generate_development_plan()}"
        else:  # analyst
            return f"**[TOOL: statistical_analysis]** - Comprehensive metrics analysis:\n\n{self._generate_analytical_breakdown()}\n\n**Methodology Notes:**\n{self._generate_methodology()}"

    def _generate_evidence_response(self, query: str) -> str:
        """Generate evidence-heavy response with citations"""
        return f"**[TOOL: parquet_query]** - Performance analysis with context:\n\n{self._generate_evidence_analysis()}\n\n**[SOURCE: Statistical validation]** - Strength-adjusted metrics:\n{self._generate_source_attribution()}\n\n**Conclusion**: {self._generate_evidence_conclusion()}"

    def _generate_clarification_response(self, query: str) -> str:
        """Generate clarification request"""
        return f"I'd be happy to help with that analysis, but I need clarification:\n\n**Which specific {self._get_clarification_aspect()} are you referring to?**\n- Option 1: {self._generate_option()}\n- Option 2: {self._generate_option()}\n\n**Or would you prefer:**\n- {self._generate_alternative()}\n\nOnce you specify, I can use appropriate tools to provide detailed insights."

    # Helper methods for realistic content generation
    def _get_tool_description(self, tool: str) -> str:
        descriptions = {
            "parquet_query": "Retrieving real-time player statistics and game data",
            "calculate_advanced_metrics": "Computing xG, Corsi, and possession analytics",
            "matchup_analysis": "Opponent analysis and tactical breakdown",
            "vector_search": "Hockey knowledge and strategic context retrieval"
        }
        return descriptions.get(tool, "Analytical tool execution")

    def _generate_realistic_stat(self) -> str:
        stats = [
            f"Shot attempts: {random.randint(15, 35)}, Goals: {random.randint(2, 8)} ({random.randint(8, 25)}% shooting %)",
            f"Zone exit success: {random.randint(55, 75)}% (league average: {random.randint(58, 68)}%)",
            f"Expected goals: {random.uniform(1.2, 3.8):.1f} (actual: {random.randint(1, 5)})",
            f"Possession time: {random.randint(45, 65)}% in offensive zone"
        ]
        return random.choice(stats)

    def _generate_advanced_metric(self) -> str:
        metrics = [
            f"Corsi For %: {random.randint(48, 58)}% (vs team average: {random.randint(50, 55)}%)",
            f"Expected Goals For %: {random.randint(47, 62)}% at 5v5 play",
            f"High-danger chances: {random.uniform(1.8, 3.2):.1f} per 60 minutes",
            f"Shot quality index: {random.uniform(0.08, 0.12):.3f} xG per shot attempt"
        ]
        return random.choice(metrics)

    def _generate_insight(self) -> str:
        insights = [
            "Performance shows consistent improvement in high-pressure situations",
            "Underlying metrics support sustainable success trends",
            "System changes are driving statistical improvements", 
            "Personnel deployment optimizing strengths effectively"
        ]
        return random.choice(insights)

    def _generate_tactical_note(self) -> str:
        notes = [
            "Zone entry success correlates with increased offensive zone time",
            "Matchup advantages created through strategic line deployment",
            "Positioning adjustments yielding measurable defensive improvements",
            "Power play efficiency gains through better puck movement"
        ]
        return random.choice(notes)

    def _generate_recommendation(self) -> str:
        recommendations = [
            "Continue current tactical approach with minor adjustments",
            "Focus on maintaining possession in high-value areas",
            "Deploy successful pairings in key game situations",
            "Emphasize system consistency over individual adjustments"
        ]
        return random.choice(recommendations)

    def _generate_strategic_recommendation(self) -> str:
        return f"Based on the analysis, focus on {random.choice(['maintaining current momentum', 'tactical adjustments in key areas', 'player development priorities', 'system optimization'])} while monitoring {random.choice(['opponent adjustments', 'performance sustainability', 'injury impacts', 'schedule demands'])}."

    # Additional helper methods would continue here...
    def _generate_performance_analysis(self) -> str:
        return f"Recent 10-game performance: {random.randint(6, 8)} wins, {random.uniform(2.1, 3.4):.1f} goals per game, {random.randint(78, 88)}% penalty kill success"

    def _generate_advanced_analysis(self) -> str:
        return f"Expected goals differential: +{random.uniform(0.3, 1.2):.1f} per game, Corsi For: {random.randint(52, 58)}%, High-danger chances: {random.uniform(2.2, 3.1):.1f} per 60"

    def _generate_key_findings(self) -> str:
        return f"1. {random.choice(['Improved', 'Consistent', 'Strong'])} performance in {random.choice(['defensive zone', 'special teams', 'even strength'])}\n2. {random.choice(['Statistical', 'Tactical', 'Personnel'])} indicators support {random.choice(['continued success', 'system effectiveness', 'player development'])}"

    def _generate_opponent_breakdown(self) -> str:
        return f"vs Top-10 teams: {random.randint(3, 6)}-{random.randint(2, 4)} record\nvs Division rivals: {random.uniform(1.8, 2.9):.1f} goals against per game"

    def _generate_tactical_implications(self) -> str:
        return f"System adjustments show {random.randint(12, 28)}% improvement in {random.choice(['zone exits', 'power play entries', 'defensive coverage'])}"

    def _generate_specific_recommendation(self) -> str:
        return f"Focus on {random.choice(['maintaining', 'adjusting', 'optimizing'])} {random.choice(['current approach', 'tactical systems', 'personnel usage'])} for upcoming {random.choice(['playoff push', 'divisional games', 'road trip'])}"

    def _generate_coach_analysis(self) -> str:
        return f"Opponent strengths: {random.choice(['Cycle game', 'Transition speed', 'Power play'])} dominance\nOur advantages: {random.choice(['Defensive depth', 'Special teams', 'Home ice'])}"

    def _generate_game_plan(self) -> str:
        return f"1. Deploy {random.choice(['Matheson-Barron', 'Guhle-Savard'])} vs top line\n2. Use {random.choice(['last change', 'timeout strategy'])} for optimal matchups"

    def _generate_player_feedback(self) -> str:
        return f"Current performance: {random.randint(60, 85)}th percentile among similar players\nStrengths: {random.choice(['Defensive positioning', 'Shot selection', 'Faceoff technique'])}"

    def _generate_development_plan(self) -> str:
        return f"Priority 1: {random.choice(['Consistency', 'Decision-making', 'Physical strength'])}\nPractice focus: {random.choice(['Positioning drills', 'Pressure situations', 'System execution'])}"

    def _generate_analytical_breakdown(self) -> str:
        return f"Statistical significance: {random.choice(['High', 'Moderate', 'Limited'])} (n={random.randint(15, 45)} games)\nPerformance vs expectation: +{random.uniform(0.1, 0.8):.1f} goals above expected"

    def _generate_methodology(self) -> str:
        return f"Sample size: {random.randint(800, 1200)} events, Confidence level: {random.randint(85, 95)}%, Adjusted for opponent strength"

    def _generate_evidence_analysis(self) -> str:
        return f"Raw metrics: {random.choice(['Above', 'Below', 'At'])} league average\nContext-adjusted: {random.choice(['Significantly better', 'Marginally improved', 'Consistent with'])} expected performance"

    def _generate_source_attribution(self) -> str:
        return f"[SOURCE: {random.choice(['Shot attempt data', 'Opponent strength metrics', 'Situational performance'])}] Adjusted performance: +{random.uniform(0.05, 0.25):.2f}"

    def _generate_evidence_conclusion(self) -> str:
        return f"Evidence suggests {random.choice(['genuine improvement', 'sustainable performance', 'system effectiveness'])} based on {random.choice(['underlying metrics', 'context-adjusted analysis', 'multiple data sources'])}"

    def _get_clarification_aspect(self) -> str:
        return random.choice(["game", "player", "time period", "statistic"])

    def _generate_option(self) -> str:
        options = [
            f"{random.choice(self.opponents)} game on {random.choice(['March 15', 'February 28', 'January 12'])}",
            f"{random.choice(['Last 5 games', 'Season average', 'Recent homestand'])} performance",
            f"{random.choice(['Power play', 'Even strength', 'Penalty kill'])} specific analysis"
        ]
        return random.choice(options)

    def _generate_alternative(self) -> str:
        alternatives = [
            "Season summary with key trends",
            "Comparison to specific opponent or time period", 
            "Focus on particular aspect of performance"
        ]
        return random.choice(alternatives)

def main():
    """Generate sample training dataset for Session 2"""
    
    generator = Session2DatasetGenerator()
    output_dir = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/llm_model/training/fine_tuning")
    
    # Generate examples across categories
    examples = []
    
    print("Generating Training Session 2 dataset samples...")
    
    # Tool Integration Examples (40% target)
    print("- Tool integration examples...")
    for _ in range(20):  # Sample size - scale up for full dataset
        examples.append(generator.generate_tool_integration_example())
    
    # Multi-turn Conversations (25% target)
    print("- Multi-turn conversations...")
    for _ in range(6):  # Each generates 2 examples
        examples.extend(generator.generate_multi_turn_conversation())
    
    # Role-specific Examples (20% target)
    print("- Role-specific responses...")
    for role in ["coach", "player", "analyst"]:
        for _ in range(3):
            examples.append(generator.generate_role_specific_example(role))
    
    # Evidence-based Examples (10% target)
    print("- Evidence-based analysis...")
    for _ in range(5):
        examples.append(generator.generate_evidence_based_example())
    
    # Error Handling Examples (5% target)
    print("- Error handling examples...")
    for _ in range(3):
        examples.append(generator.generate_error_handling_example())
    
    # Convert to JSONL format
    output_file = output_dir / "mistral_training_session_2_generated.jsonl"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in examples:
            json.dump(example.messages, f, ensure_ascii=False)
            f.write('\n')
    
    print(f"\n✅ Generated {len(examples)} training examples")
    print(f"📁 Saved to: {output_file}")
    
    # Generate statistics
    category_counts = {}
    for example in examples:
        category_counts[example.category] = category_counts.get(example.category, 0) + 1
    
    print("\n📊 Category Distribution:")
    for category, count in category_counts.items():
        print(f"   {category}: {count} examples")
    
    print(f"\n🚀 Ready for Mistral fine-tuning!")
    print("📋 Scale up generation parameters for full 2,000+ example dataset")

if __name__ == "__main__":
    main()
