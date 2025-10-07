"""
Qwen3 Reasoning-First Synthesis
Simple approach that trusts the model's reasoning abilities

Instead of constraining the model with rigid prompts, we:
1. Give it the user's question
2. Give it ALL the data we retrieved
3. Give it context about time and team
4. Let it REASON and answer naturally
"""

import json
from typing import Dict, List, Any
from orchestrator.utils.state import AgentState, ToolResult


def build_reasoning_synthesis_prompt(
    state: AgentState,
    query: str,
    tool_results: List[ToolResult],
    rag_context: str = ""
) -> str:
    """
    Build a simple, natural prompt that lets Qwen3 Thinking reason freely.
    
    This is the PRODUCTION approach - minimal constraints, maximum reasoning.
    """
    
    # Time context
    current_date = state.get("current_date", "")
    current_season = state.get("current_season", "2025-2026")
    
    # Build natural data section
    data_available = []
    
    import logging
    logger = logging.getLogger(__name__)
    
    for result in tool_results:
        if not result.success or not result.data:
            continue
        
        tool_name = result.tool_type.value if hasattr(result.tool_type, 'value') else str(result.tool_type)
        
        # SMART DATA PRESENTATION: Show summary + key metrics, not full JSON
        if isinstance(result.data, dict):
            data = result.data
            analysis_type = data.get("analysis_type", "")
            logger.info(f"Synthesis formatting: analysis_type={analysis_type}, keys={list(data.keys())[:10]}")
            
            # Build concise summary based on type
            if analysis_type == "comprehensive_matchup":
                # NEW: Combined matchup + game results
                summary = f"MTL vs {data.get('opponent')} ({data.get('season')}) - COMPLETE VIEW:\n\n"
                
                # Game Results (W/L record)
                game_results = data.get("game_results", {})
                if game_results.get("total_games", 0) > 0:
                    summary += f"RECORD: {game_results.get('record_string', 'N/A')}\n"
                    summary += f"  Games: {game_results.get('total_games')} | W: {game_results.get('wins')} | L: {game_results.get('losses')} | OTL: {game_results.get('ot_losses', 0)}\n\n"
                
                # Matchup Metrics
                matchup_metrics = data.get("matchup_metrics", {})
                if matchup_metrics.get("key_metrics"):
                    summary += "KEY PERFORMANCE METRICS:\n"
                    for metric_name, values in list(matchup_metrics["key_metrics"].items())[:8]:
                        mtl = values.get("mtl", 0)
                        opp = values.get("opponent", 0)
                        diff = values.get("difference", mtl - opp)
                        advantage = "MTL+" if diff > 0 else f"{data.get('opponent')}+"
                        summary += f"  - {metric_name}: MTL {mtl:.2f} vs {data.get('opponent')} {opp:.2f} ({advantage} {abs(diff):.2f})\n"
                
                data_str = summary
            
            elif analysis_type == "matchup":
                # Legacy matchup (metrics only)
                summary = f"Matchup vs {data.get('opponent')} ({data.get('season')}): {data.get('total_matchup_rows')} metrics\n"
                if data.get("key_metrics"):
                    summary += "Top Metrics:\n"
                    for metric_name, values in list(data["key_metrics"].items())[:8]:
                        mtl = values.get("mtl", 0)
                        opp = values.get("opponent", 0)
                        diff = values.get("difference", mtl - opp)
                        summary += f"  - {metric_name}: MTL {mtl:.2f}, {data.get('opponent')} {opp:.2f} (diff: {diff:+.2f})\n"
                data_str = summary
            
            elif analysis_type == "power_play":
                summary = f"Power Play ({data.get('season')}): {data.get('total_pp_units')} units\n"
                if data.get("top_unit"):
                    top = data["top_unit"]
                    summary += f"Top Unit: {top.get('Players', '')[:100]}\n"
                    summary += f"  - TOI: {top.get('TOI', 0)} min, XGF%: {top.get('XGF%', 0):.3f}\n"
                data_str = summary
            
            elif analysis_type == "season_results":
                summary = f"Season {data.get('season')}: {data.get('total_games')} games\n"
                if data.get("record"):
                    summary += f"Record: {data['record'].get('record_string', '')}\n"
                data_str = summary
            
            elif analysis_type == "player_stats":
                # COMPLETE STATS ACCESS - give model EVERYTHING, let it reason
                all_stats = data.get('all_stats', {})
                
                # Build comprehensive data dump (model decides what to highlight)
                summary = f"PLAYER: {data.get('player_name')} - {data.get('position')} - Season {data.get('season')}\n"
                summary += f"Data Source: {data.get('data_source')}\n\n"
                summary += f"FULL STATISTICS AVAILABLE ({len(all_stats)} metrics):\n"
                
                # Show ALL stats as key-value pairs (let model see EVERYTHING)
                stat_lines = []
                for stat_name, value in all_stats.items():
                    # Skip metadata columns
                    if any(x in stat_name for x in ['Jersey', 'Current Team', 'Player ID']):
                        continue
                    
                    # Include ALL stats (not just first 30!)
                    if isinstance(value, (int, float)):
                        stat_lines.append(f"{stat_name}: {value}")
                    elif isinstance(value, str) and value.strip():
                        stat_lines.append(f"{stat_name}: {value}")
                
                # Show comprehensive stats (truncate if > 3000 chars to avoid token limits)
                stats_text = "\n".join(stat_lines)
                if len(stats_text) > 3000:
                    # Show stats but truncate if massive
                    summary += stats_text[:3000] + f"\n\n[Plus {len(stats_text) - 3000} more characters of data]"
                else:
                    summary += stats_text
                
                summary += f"\n\nInstructions: Analyze these stats and highlight what's most relevant to the user's question."
                data_str = summary
            
            else:
                # Generic: Show type + try to serialize safely
                try:
                    # Deep filter to remove all non-serializable objects
                    def make_serializable(obj):
                        if isinstance(obj, (str, int, float, bool, type(None))):
                            return obj
                        elif isinstance(obj, dict):
                            return {k: make_serializable(v) for k, v in obj.items() if not k.startswith('_')}
                        elif isinstance(obj, list):
                            return [make_serializable(item) for item in obj[:10]]  # Limit list size
                        else:
                            return str(obj)  # Convert objects to string
                    
                    serializable_data = make_serializable(data)
                    data_str = f"{analysis_type}: " + json.dumps(serializable_data)[:400]
                except Exception as e:
                    # Ultimate fallback - just show type and summary
                    data_str = f"{analysis_type}: Data retrieved (serialization issue)"
        else:
            data_str = str(result.data)[:300]
        
        data_available.append(f"\nTool: {tool_name}\n{data_str}")
    
    # Build simple, natural prompt
    prompt = f"""You are STANLEY, Montreal Canadiens AI analytics assistant.

Today is {current_date}. Current NHL season: {current_season}.

Scope: You are Montreal-focused but have access to league-wide NHL player data for context, comparisons, and scouting.

User Question:
{query}

Data Retrieved:
{"".join(data_available)}

{f"Expert Hockey Context:{rag_context}" if rag_context else ""}

Instructions:
- Answer the user's question using the data above
- Be professional (NO EMOJIS)
- Cite specific numbers
- Use your hockey expertise to interpret the metrics
- If data is incomplete, acknowledge it

Your analysis:"""
    
    return prompt


def extract_data_summary_simple(tool_results: List[ToolResult]) -> str:
    """
    Extract key numbers from tool results for quick reference.
    Used when we need ultra-simple prompts.
    """
    summary_parts = []
    
    for result in tool_results:
        if not result.success or not isinstance(result.data, dict):
            continue
        
        data = result.data
        
        # Extract key numbers based on analysis type
        if data.get("analysis_type") == "matchup" and data.get("key_metrics"):
            for metric_name, values in list(data["key_metrics"].items())[:5]:
                mtl = values.get("mtl", 0)
                opp = values.get("opponent", 0)
                summary_parts.append(f"{metric_name}: MTL {mtl:.2f} vs {opp:.2f}")
        
        elif data.get("total_pp_units"):
            summary_parts.append(f"{data['total_pp_units']} PP units analyzed")
        
        elif data.get("player_name"):
            player = data['player_name']
            stats = data.get("stats", {})
            summary_parts.append(f"{player}: {stats}")
    
    return " | ".join(summary_parts) if summary_parts else "Data retrieved"

