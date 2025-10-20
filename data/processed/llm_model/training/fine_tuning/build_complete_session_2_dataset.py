#!/usr/bin/env python3
"""
Complete Session 2 Dataset Builder
HeartBeat Engine - Direct dataset generation without shell dependencies
"""

import json
import random
from pathlib import Path

# Enhanced system prompt for Session 2
ENHANCED_SYSTEM_PROMPT = """You are an elite hockey analytics orchestrator for the Montreal Canadiens organization. You serve coaches, players, scouts, analysts, and staff with professional-grade insights by intelligently coordinating multiple analytical tools and data sources.

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

def generate_complete_dataset():
    """Generate the complete Training Session 2 dataset"""
    
    # Montreal players and context
    mtl_forwards = ["Suzuki", "Caufield", "Slafkovsky", "Dach", "Newhook", "Evans", "Gallagher", "Anderson", "Armia", "Dvorak"]
    mtl_defense = ["Hutson", "Guhle", "Matheson", "Savard", "Barron", "Xhekaj", "Struble"]
    opponents = ["Toronto", "Boston", "Tampa Bay", "Florida", "Buffalo", "Ottawa", "Detroit", "New York Rangers"]
    
    examples = []
    
    # CATEGORY 1: TOOL INTEGRATION (880 examples - 40%)
    print("Generating tool integration examples...")
    
    tool_integration_templates = [
        # Complex analytical workflows
        ("Compare {player1}'s {metric} when paired with {player2} vs {player3} over the last {days} games", "advanced"),
        ("Analyze our {system} effectiveness against {opponent}'s {counter_system}", "intermediate"),
        ("What's the impact of {player}'s line placement on our overall {team_metric}?", "intermediate"),
        ("How do our power play entries succeed against {opponent}'s penalty kill pressure?", "advanced"),
        ("Evaluate {player}'s zone exit efficiency in different game situations", "basic"),
        ("What tactical adjustments maximize our success against {opponent}'s forechecking system?", "expert"),
        ("Compare our defensive coverage when {player} is on ice vs off ice", "intermediate"),
        ("How effective is our cycle game in the offensive zone against physical teams?", "advanced"),
        # More complex scenarios
        ("Analyze the correlation between our faceoff performance and subsequent scoring chances", "expert"),
        ("What's our shot quality differential in back-to-back games vs regular rest?", "advanced"),
        ("How does our penalty kill formation change based on opponent power play style?", "expert"),
        ("Compare our neutral zone transition speed when using different defensive pairings", "advanced"),
        ("What's the impact of crowd noise on our home ice faceoff performance?", "intermediate"),
        ("Analyze our goaltending performance correlation with defensive zone coverage efficiency", "expert"),
        ("How do our line combinations perform in different periods of the game?", "intermediate"),
        ("What's our success rate on zone entries when trailing vs leading?", "advanced")
    ]
    
    for i in range(880):
        template, complexity = random.choice(tool_integration_templates)
        
        # Populate template
        query = template.format(
            player1=random.choice(mtl_forwards + mtl_defense),
            player2=random.choice(mtl_forwards + mtl_defense), 
            player3=random.choice(mtl_forwards + mtl_defense),
            player=random.choice(mtl_forwards + mtl_defense),
            opponent=random.choice(opponents),
            metric=random.choice(["shot quality", "zone exit success", "faceoff percentage", "Corsi differential"]),
            system=random.choice(["forecheck", "neutral zone trap", "power play"]),
            counter_system=random.choice(["penalty kill", "defensive coverage", "breakout system"]),
            team_metric=random.choice(["possession time", "scoring chance creation", "defensive efficiency"]),
            days=random.randint(8, 15)
        )
        
        # Generate response based on complexity
        if complexity == "basic":
            response = f"**[TOOL: parquet_query]** - Retrieving performance data:\n- Recent performance: {random.randint(55, 75)}% success rate\n- League comparison: {random.choice(['Above', 'Below', 'At'])} average\n\n**[TOOL: calculate_advanced_metrics]** - Advanced analysis:\n- Expected performance: {random.uniform(1.8, 2.9):.1f} per game\n- Efficiency rating: {random.randint(68, 84)}%\n\n**Key Insight**: {random.choice(['Consistent improvement', 'Stable performance', 'Area for development'])} with {random.choice(['tactical adjustments', 'continued focus', 'system refinement'])} recommended."
        
        elif complexity == "intermediate":
            response = f"I'll analyze this using a multi-step approach:\n\n**Step 1: [TOOL: parquet_query]** - Base performance data\n- Primary metric: {random.randint(45, 85)}% efficiency\n- Sample size: {random.randint(15, 30)} games\n- Context: {random.choice(['Improving trend', 'Consistent performance', 'Mixed results'])}\n\n**Step 2: [TOOL: calculate_advanced_metrics]** - Situational breakdown\n- Expected value: {random.uniform(1.2, 3.4):.1f}\n- Performance differential: +{random.uniform(0.1, 0.8):.1f}\n- League ranking: {random.randint(8, 24)}th\n\n**Key Insights:**\n1. {random.choice(['Strong correlation', 'Moderate relationship', 'Significant impact'])} between variables\n2. {random.choice(['Tactical advantage', 'System effectiveness', 'Personnel optimization'])} showing positive results\n\n**Recommendation**: {random.choice(['Continue current approach', 'Minor adjustments needed', 'Focus on consistency'])} with monitoring of {random.choice(['key metrics', 'opponent adjustments', 'player development'])}."
        
        elif complexity == "advanced":
            response = f"I'll conduct a comprehensive multi-dimensional analysis:\n\n**Step 1: [TOOL: parquet_query]** - Primary data retrieval\n- Core metrics: {random.randint(52, 78)}% success rate over {random.randint(18, 25)} games\n- Situational breakdown: {random.randint(48, 82)}% in high-pressure situations\n- Comparison baseline: League average {random.randint(56, 71)}%\n\n**Step 2: [TOOL: calculate_advanced_metrics]** - Advanced statistical analysis\n- Expected performance: {random.uniform(1.9, 3.6):.1f} per 60 minutes\n- Quality-adjusted metrics: {random.uniform(0.85, 1.25):.2f} multiplier\n- Predictive indicators: {random.randint(72, 89)}% correlation with success\n\n**Step 3: [TOOL: matchup_analysis]** - Contextual effectiveness assessment\n- vs Elite opposition: {random.randint(58, 74)}% maintained effectiveness\n- vs Similar-style teams: {random.randint(65, 85)}% success rate\n- Home vs road differential: {random.randint(3, 12)}% advantage\n\n**Key Strategic Insights:**\n1. **System Integration**: {random.choice(['Excellent', 'Strong', 'Developing'])} adaptation to new tactical approach\n2. **Performance Sustainability**: Underlying metrics support {random.choice(['continued success', 'gradual improvement', 'maintained effectiveness'])}\n3. **Competitive Advantage**: Creates {random.choice(['systematic edge', 'matchup flexibility', 'tactical unpredictability'])} vs opponents\n\n**Tactical Implications:**\n- Personnel deployment optimized for {random.choice(['speed advantage', 'skill utilization', 'defensive reliability'])}\n- System creates {random.randint(8, 18)}% improvement in {random.choice(['transition efficiency', 'possession retention', 'scoring chance creation'])}\n- Sustainable long-term approach with {random.choice(['minor refinements', 'tactical evolution', 'continued development'])} needed\n\n**Recommendation**: {random.choice(['Maintain current system', 'Implement targeted adjustments', 'Continue tactical evolution'])} while preparing for opponent counter-adjustments. The {random.choice(['foundation is excellent', 'system is effective', 'approach is sound'])} - focus on execution consistency."
        
        else:  # expert
            response = f"I'll execute a comprehensive multi-layered analysis across all relevant dimensions:\n\n**Step 1: [TOOL: parquet_query]** - Comprehensive data aggregation\n- Primary performance indicators: {random.randint(58, 81)}% efficiency across {random.randint(22, 35)} game sample\n- Multi-situational breakdown: {random.randint(45, 75)}% high-pressure, {random.randint(62, 88)}% standard situations\n- Temporal analysis: {random.choice(['Improving', 'Stable', 'Variable'])} trend over time\n\n**Step 2: [TOOL: calculate_advanced_metrics]** - Advanced statistical modeling\n- Predictive model accuracy: {random.randint(78, 94)}% (R² = {random.uniform(0.65, 0.89):.2f})\n- Multi-variate analysis: {random.randint(3, 7)} significant predictive factors identified\n- Effect size measurements: {random.choice(['Large', 'Medium', 'Significant'])} impact (Cohen's d = {random.uniform(0.4, 1.2):.1f})\n\n**Step 3: [TOOL: vector_search]** - Strategic context and best practices\n- Elite performance benchmarks: Top teams achieve {random.randint(72, 88)}% in similar contexts\n- Historical precedent: Similar tactical approaches yield {random.randint(12, 28)}% improvement rates\n- Strategic evolution: Approach aligns with modern NHL tactical trends\n\n**Step 4: [TOOL: matchup_analysis]** - Competitive landscape assessment\n- Division rival comparison: {random.randint(15, 35)}% performance advantage in key metrics\n- Playoff team benchmark: {random.choice(['Meeting', 'Exceeding', 'Approaching'])} typical standards\n- Opponent adaptation timeline: {random.randint(4, 8)} game lag for counter-adjustments\n\n**Step 5: [TOOL: visualization]** - Performance trend analysis\n- Visual confirmation: {random.choice(['Clear upward', 'Stable positive', 'Consistently strong'])} trajectory\n- Correlation mapping: {random.randint(67, 89)}% of success factors identified and validated\n- Predictive modeling: {random.randint(72, 91)}% accuracy for future performance projection\n\n**Comprehensive Strategic Assessment:**\n\n**1. Multi-Dimensional Excellence:**\n- Statistical significance across {random.randint(4, 7)} independent measurement categories\n- Cross-validation confirms {random.choice(['genuine improvement', 'systematic advantage', 'sustainable success'])}\n- Methodology robustness: {random.randint(85, 96)}% confidence in findings\n\n**2. Competitive Positioning:**\n- Performance differential: +{random.uniform(0.15, 0.45):.2f} goals per game impact\n- Strategic advantage duration: {random.randint(8, 15)} game window before adaptation\n- Long-term sustainability: {random.choice(['High', 'Excellent', 'Strong'])} based on underlying factors\n\n**3. Optimization Opportunities:**\n- Primary enhancement area: {random.choice(['Execution consistency', 'Personnel rotation', 'Situational adaptation'])}\n- Secondary development: {random.choice(['Counter-adjustment preparation', 'Advanced tactical elements', 'System refinement'])}\n- Risk mitigation: {random.choice(['Opponent scouting', 'Injury contingencies', 'Performance monitoring'])}\n\n**Executive Recommendation**: Deploy comprehensive monitoring and optimization protocol combining continued tactical evolution with proactive counter-adjustment preparation. The analytical evidence strongly supports sustained competitive advantage through systematic execution excellence and strategic adaptability."
        
        example = {
            "messages": [
                {"role": "system", "content": ENHANCED_SYSTEM_PROMPT},
                {"role": "user", "content": query},
                {"role": "assistant", "content": response}
            ]
        }
        examples.append(example)
    
    print(f"Generated {len(examples)} tool integration examples")
    
    # CATEGORY 2: MULTI-TURN CONVERSATIONS (550 examples - 25%)
    print("Generating multi-turn conversation examples...")
    
    conversation_starters = [
        "How has our penalty kill evolved since the coaching change?",
        "What are the patterns in our power play success this season?",
        "Which line combinations are creating the best chemistry?",
        "How effective is our neutral zone transition game?",
        "What's our defensive zone coverage efficiency lately?",
        "How sustainable is our recent goal scoring improvement?",
        "What adjustments have we made to our forechecking system?",
        "How do our young players compare to league averages?",
        "What's driving our recent special teams success?",
        "How has our goaltending stability affected team confidence?"
    ]
    
    followups = [
        "Which specific opponents have we struggled against in this area?",
        "What tactical adjustments would you recommend based on this analysis?",
        "How does this compare to our performance last season?",
        "Which players are driving these trends?",
        "What's the underlying cause of these patterns?",
        "How sustainable are these improvements?",
        "What should we be concerned about going forward?",
        "Which metrics are most predictive of future success?",
        "How have opponents adjusted to counter our approach?",
        "What personnel changes could optimize this further?"
    ]
    
    for i in range(275):  # 275 conversations × 2 turns = 550 examples
        starter = random.choice(conversation_starters)
        followup = random.choice(followups)
        
        # First turn
        first_response = f"**[TOOL: parquet_query]** - Recent performance analysis:\n\n{random.choice(['Significant improvement', 'Consistent performance', 'Mixed results'])} over last {random.randint(10, 20)} games:\n- Key metric: {random.randint(65, 85)}% success rate\n- Trend: {random.choice(['Upward', 'Stable', 'Variable'])}\n- League comparison: {random.choice(['Above', 'At', 'Below'])} average\n\n**[TOOL: calculate_advanced_metrics]** - Advanced breakdown:\n- Expected performance: {random.uniform(1.8, 3.2):.1f}\n- Quality indicators: {random.randint(72, 89)}% efficiency\n- Predictive factors: {random.randint(3, 6)} key variables identified\n\n**Key Findings:**\n1. {random.choice(['Systematic improvement', 'Personnel optimization', 'Tactical evolution'])} driving results\n2. {random.choice(['Sustainable approach', 'Positive trajectory', 'Strong foundation'])} established\n3. {random.choice(['Continued focus', 'Minor adjustments', 'System refinement'])} recommended"
        
        examples.append({
            "messages": [
                {"role": "system", "content": ENHANCED_SYSTEM_PROMPT},
                {"role": "user", "content": starter},
                {"role": "assistant", "content": first_response}
            ]
        })
        
        # Follow-up turn
        followup_response = f"**[TOOL: opponent_analysis]** - Detailed breakdown by competition:\n\nvs {random.choice(opponents)}: {random.randint(3, 7)}-{random.randint(1, 4)} record\nvs Division rivals: {random.uniform(2.1, 3.8):.1f} differential per game\nvs Playoff teams: {random.randint(58, 76)}% of expected performance\n\n**[TOOL: tactical_breakdown]** - Strategic implications:\n- Adjustment timeline: {random.randint(3, 8)} games for opponent counter-measures\n- System vulnerability: {random.choice(['Minimal', 'Moderate', 'Manageable'])} exposure\n- Optimization potential: {random.randint(8, 22)}% additional improvement possible\n\n**Recommendation**: {random.choice(['Maintain current approach', 'Implement tactical adjustments', 'Prepare counter-measures'])} while {random.choice(['monitoring opposition', 'optimizing execution', 'developing contingencies'])}."
        
        examples.append({
            "messages": [
                {"role": "system", "content": ENHANCED_SYSTEM_PROMPT},
                {"role": "user", "content": followup},
                {"role": "assistant", "content": followup_response}
            ]
        })
    
    print(f"Generated {len(examples)} total examples so far")
    
    # Continue with remaining categories...
    # CATEGORY 3: ROLE-BASED RESPONSES (440 examples - 20%)
    print("Generating role-based examples...")
    
    role_queries = {
        "coach": [
            "How should we handle {opponent}'s top line in our building?",
            "What defensive pairing gives us the best matchup against {opponent}?",
            "Which power play formation works best against aggressive penalty kills?", 
            "How can we exploit {opponent}'s weak-side coverage?",
            "What's our optimal fourth line deployment for energy and momentum?",
            "How should we use our timeout strategically against {opponent}?",
            "Which players should we emphasize in pre-game preparation?",
            "What line matching strategy gives us the best advantage?"
        ],
        "player": [
            "How can I improve my effectiveness in board battles?",
            "What should I focus on to increase my ice time?",
            "How can I be more consistent in my shot selection?",
            "What positioning adjustments will help my defensive game?",
            "How can I better support my linemates in the offensive zone?",
            "What's the best way to prepare for facing elite opponents?",
            "How can I improve my faceoff technique in key situations?",
            "What development areas will help me reach the next level?"
        ],
        "analyst": [
            "What's our shot quality differential adjusted for opponent strength?",
            "How significant is our improvement in advanced metrics?",
            "Which underlying statistics best predict our playoff chances?",
            "What's our expected goals performance in clutch situations?",
            "How do our possession metrics compare across different game states?",
            "What methodology should we use for player development tracking?",
            "How reliable are our small-sample defensive improvements?", 
            "Which metrics correlate most strongly with our wins?"
        ]
    }
    
    for role in ["coach", "player", "analyst"]:
        role_system = f"You are responding to a Montreal Canadiens {role}. Provide {'strategic insights with tactical depth' if role == 'coach' else 'personal performance insights with development focus' if role == 'player' else 'detailed statistical insights with methodological rigor'} suitable for {'game planning and lineup decisions' if role == 'coach' else 'skill improvement and growth' if role == 'player' else 'front office evaluation'}."
        
        for i in range(147):  # ~440/3 = 147 per role
            query_template = random.choice(role_queries[role])
            query = query_template.format(
                opponent=random.choice(opponents),
                player=random.choice(mtl_forwards + mtl_defense)
            )
            
            if role == "coach":
                response = f"**[TOOL: matchup_analysis]** - Tactical assessment:\n\n**Opposition Analysis:**\n- Key strengths: {random.choice(['Cycle game', 'Transition speed', 'Physical play'])}\n- Primary weakness: {random.choice(['Neutral zone coverage', 'Defensive zone exits', 'Special teams'])}\n- Success rate against: {random.randint(45, 75)}%\n\n**Our Advantages:**\n- {random.choice(['Speed differential', 'Skill advantage', 'System superiority'])}\n- {random.choice(['Home ice factor', 'Lineup depth', 'Tactical flexibility'])}\n\n**Strategic Game Plan:**\n1. Deploy {random.choice(['Matheson-Barron', 'Guhle-Savard'])} as primary matchup\n2. Use {random.choice(['aggressive forecheck', 'neutral zone trap'])} to exploit weakness\n3. {random.choice(['Quick line changes', 'Timeout strategy'])} for optimal deployment\n\n**Key Focus**: {random.choice(['Deny zone entries', 'Control neutral zone', 'Pressure their breakout'])} to limit their {random.choice(['time and space', 'offensive opportunities', 'system execution'])}."
            
            elif role == "player":
                response = f"**[TOOL: player_analysis]** - Your performance breakdown:\n\n**Current Metrics:**\n- Performance rating: {random.randint(65, 88)}th percentile\n- Key strength: {random.choice(['Positioning', 'Decision-making', 'Compete level'])}\n- Development area: {random.choice(['Consistency', 'Timing', 'Technique'])}\n\n**Specific Focus Areas:**\n1. **{random.choice(['Technical refinement', 'Situational awareness', 'Physical preparation'])}**\n   - Current level: {random.choice(['Developing', 'Solid', 'Advanced'])}\n   - Target improvement: {random.randint(8, 18)}%\n   - Practice emphasis: {random.choice(['Repetition', 'Game situations', 'Video study'])}\n\n2. **{random.choice(['Game application', 'Consistency factors', 'Pressure response'])}**\n   - Opportunity for growth in {random.choice(['high-stakes moments', 'routine execution', 'leadership presence'])}\n   - Development timeline: {random.randint(2, 6)} weeks focused training\n\n**Next Game Focus**: {random.choice(['Trust your instincts', 'Apply coaching points', 'Maintain compete level'])} while emphasizing {random.choice(['system execution', 'individual excellence', 'team contribution'])}."
            
            else:  # analyst
                response = f"**[TOOL: statistical_analysis]** - Comprehensive metrics evaluation:\n\n**Statistical Significance:**\n- Sample size: {random.randint(35, 65)} games (robust)\n- Confidence level: {random.randint(88, 96)}%\n- Effect size: {random.choice(['Medium', 'Large', 'Significant'])}\n\n**Performance vs Expectation:**\n- Adjusted for opponent strength: +{random.uniform(0.12, 0.48):.2f}\n- Context-normalized: {random.randint(52, 78)}% above baseline\n- Predictive accuracy: {random.randint(74, 91)}%\n\n**Methodology Notes:**\n- Adjustment factors: {random.choice(['Score state', 'Opponent quality', 'Home/road'])}\n- Confidence intervals: ±{random.uniform(0.08, 0.25):.2f}\n- Cross-validation: {random.randint(82, 95)}% model reliability\n\n**Key Findings:**\n{random.choice(['Statistically significant', 'Methodologically sound', 'Analytically robust'])} evidence of {random.choice(['improvement', 'consistency', 'effectiveness'])} with {random.choice(['high confidence', 'strong reliability', 'excellent validity'])}."
            
            examples.append({
                "messages": [
                    {"role": "system", "content": role_system},
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": response}
                ]
            })
    
    print(f"Generated {len(examples)} total examples so far")
    
    # CATEGORY 4: EVIDENCE-BASED ANALYSIS (220 examples - 10%)
    print("Generating evidence-based examples...")
    
    evidence_templates = [
        "Is our {metric} improvement actually sustainable based on underlying numbers?",
        "Are we genuinely better at {aspect} or just facing easier {opposition}?",
        "What's really driving our {trend} - {factor1} or {factor2}?",
        "How much of our {success} is {primary_cause} vs {secondary_cause}?",
        "What does the data actually show about our {narrative}?",
        "How statistically reliable is our {performance_change}?",
        "Which metrics best predict our {outcome_measure}?",
        "What's the real story behind our {season_narrative}?"
    ]
    
    for i in range(220):
        template = random.choice(evidence_templates)
        query = template.format(
            metric=random.choice(["power play", "penalty kill", "even strength", "defensive"]),
            aspect=random.choice(["defending", "scoring", "special teams"]),
            opposition=random.choice(["opposition", "schedule", "matchups"]),
            trend=random.choice(["success", "improvement", "consistency"]),
            factor1=random.choice(["system changes", "personnel", "health"]),
            factor2=random.choice(["opponent strength", "luck", "effort"]),
            success=random.choice(["recent wins", "goal scoring", "defensive play"]),
            primary_cause=random.choice(["goaltending", "offense", "defense"]),
            secondary_cause=random.choice(["special teams", "depth", "coaching"]),
            narrative=random.choice(["turnaround", "development", "system"]),
            performance_change=random.choice(["improvement", "decline", "consistency"]),
            outcome_measure=random.choice(["playoff chances", "future success", "development"]),
            season_narrative=random.choice(["youth movement", "system change", "competitive improvement"])
        )
        
        response = f"**[TOOL: parquet_query]** - Comprehensive data analysis:\n\n**Raw Performance Data:**\n- Current metrics: {random.choice(['Above', 'Below', 'At'])} league average\n- Sample size: {random.randint(25, 55)} games\n- Trend direction: {random.choice(['Improving', 'Stable', 'Variable'])}\n\n**[TOOL: statistical_analysis]** - Strength-adjusted evaluation:\n\n**[SOURCE: Opponent quality data]**\n- Strength of schedule: {random.uniform(0.92, 1.08):.2f} (league average = 1.00)\n- Quality-adjusted performance: {random.choice(['Significantly better', 'Marginally improved', 'Consistent with'])} expectations\n- Context-normalized ranking: {random.randint(8, 24)}th in NHL\n\n**[SOURCE: {random.choice(['Game state analysis', 'Situational data', 'Performance tracking'])}]**\n- Contributing factors breakdown: {random.randint(35, 65)}% {random.choice(['system', 'personnel', 'execution'])}, {random.randint(25, 45)}% {random.choice(['health', 'chemistry', 'development'])}\n- Underlying metrics: {random.choice(['Support', 'Question', 'Validate'])} surface-level improvements\n- Regression potential: {random.choice(['Low', 'Moderate', 'Minimal'])}\n\n**Statistical Significance:**\n- Confidence level: {random.randint(85, 95)}%\n- Effect size: {random.choice(['Small', 'Medium', 'Large'])}\n- Sample adequacy: {random.choice(['Sufficient', 'Limited', 'Robust'])}\n\n**Evidence-Based Conclusion**: Analysis indicates {random.choice(['genuine improvement', 'sustainable trend', 'systematic change'])} supported by {random.choice(['multiple indicators', 'underlying metrics', 'contextual factors'])}. {random.choice(['High confidence', 'Strong evidence', 'Reliable data'])} suggests {random.choice(['continued success', 'maintained performance', 'positive trajectory'])}."
        
        examples.append({
            "messages": [
                {"role": "system", "content": "Always provide evidence-based responses with clear source attribution from tools and data queries."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": response}
            ]
        })
    
    print(f"Generated {len(examples)} total examples so far")
    
    # CATEGORY 5: ERROR HANDLING (110 examples - 5%)
    print("Generating error handling examples...")
    
    ambiguous_queries = [
        "How did we do in that overtime game?",
        "What about our power play against Boston?",
        "Can you check Smith's stats?",
        "How are we doing lately?",
        "What's the story with the lineup changes?",
        "How did that play work out?",
        "Any updates on the defensive situation?",
        "What do you think about our recent performance?",
        "How's the team looking?",
        "What about those line combinations?"
    ]
    
    for i in range(110):
        query = random.choice(ambiguous_queries)
        
        clarification_element = random.choice(["game", "player", "metric", "time period", "situation"])
        
        response = f"I'd be happy to help with that analysis, but I need clarification to provide accurate insights:\n\n**Which specific {clarification_element} are you referring to?**\n- {random.choice(opponents)} on {random.choice(['March 15', 'February 22', 'January 18'])}\n- Last {random.randint(5, 12)} games performance summary\n- {random.choice(['Power play', 'Even strength', 'Penalty kill'])} specific analysis\n\n**Or would you prefer:**\n- Season overview with key trends and patterns\n- Comparison to specific opponent or benchmark\n- Focus on particular aspect of {random.choice(['team performance', 'individual metrics', 'tactical execution'])}\n\n**Available Analysis Tools:**\nOnce you specify, I can use:\n- [TOOL: parquet_query] for detailed statistics and game data\n- [TOOL: calculate_advanced_metrics] for advanced performance analysis\n- [TOOL: matchup_analysis] for opponent-specific insights\n- [TOOL: visualization] for performance charts and trends\n\nPlease let me know what specific aspect interests you most, and I'll provide comprehensive analysis with relevant metrics and actionable insights."
        
        examples.append({
            "messages": [
                {"role": "system", "content": "Handle incomplete data gracefully and ask clarifying questions when needed."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": response}
            ]
        })
    
    print(f"Generated {len(examples)} total examples - COMPLETE!")
    
    return examples

# Generate and save the complete dataset
print("=" * 60)
print("TRAINING SESSION 2 - COMPLETE DATASET GENERATION")
print("=" * 60)

complete_examples = generate_complete_dataset()

# Shuffle for variety
random.shuffle(complete_examples)

# Split into training (80%) and validation (20%)
total = len(complete_examples)
split_point = int(total * 0.8)

training_data = complete_examples[:split_point]
validation_data = complete_examples[split_point:]

# Save training dataset
training_path = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/llm_model/training/fine_tuning/mistral_training_dataset_session_2.jsonl")
with open(training_path, 'w', encoding='utf-8') as f:
    for example in training_data:
        json.dump(example, f, ensure_ascii=False)
        f.write('\n')

# Save validation dataset  
validation_path = Path("/Users/xavier.bouchard/Desktop/HeartBeat/data/processed/llm_model/training/fine_tuning/mistral_validation_dataset_session_2.jsonl")
with open(validation_path, 'w', encoding='utf-8') as f:
    for example in validation_data:
        json.dump(example, f, ensure_ascii=False)
        f.write('\n')

print(f"\n✅ COMPLETE DATASET GENERATED!")
print(f"📊 Total Examples: {total:,}")
print(f"📁 Training: {len(training_data):,} examples")
print(f"📁 Validation: {len(validation_data):,} examples")
print(f"💾 Files saved to training/fine_tuning/")
print(f"🚀 Ready for Mistral Training Session 2!")
