"""
HeartBeat Engine - Response Synthesizer Node
Montreal Canadiens Advanced Analytics Assistant

Synthesizes final responses using the fine-tuned DeepSeek-R1-Distill-Qwen-32B model,
integrating RAG context, analytics data, and video clips into coherent, evidence-based responses.
Features advanced reasoning capabilities with sophisticated tool orchestration.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import asyncio
import json

try:
    import openai
except ImportError:
    openai = None

from orchestrator.utils.state import (
    AgentState,
    ToolResult,
    ToolType,
    update_state_step,
    add_tool_result,
    add_error,
    has_required_data
)
from orchestrator.config.settings import settings, UserRole

logger = logging.getLogger(__name__)

class ResponseSynthesizerNode:
    """
    Synthesizes final responses using the fine-tuned DeepSeek-R1-Distill-Qwen-32B model.
    
    Advanced Reasoning Capabilities:
    - Multi-step analytical reasoning with tool orchestration
    - Integration of RAG context, analytics data, and video clips
    - Role-appropriate response formatting with hockey linguistics
    - Evidence-based reasoning chains with source attribution
    - Advanced tool management and workflow coordination
    - Montreal Canadiens specific terminology and context
    """
    
    def __init__(self):
        self.model_config = settings.model
        self.orchestration_config = settings.orchestration
        
        # Professional hockey analytics system prompt (consistent across all roles)
        self.base_system_prompt = """You are an elite hockey analytics assistant exclusively for the Montreal Canadiens organization. You serve coaches, players, scouts, analysts, and staff with professional-grade insights combining deep hockey knowledge with advanced data analysis capabilities.

CORE CAPABILITIES:
- Process natural language queries about any aspect of Montreal Canadiens performance
- Combine contextual hockey knowledge with real-time data analysis using dynamic tools
- Generate statistical insights, visualizations, and strategic recommendations
- Analyze play-by-play data, player performance, and opponent matchups dynamically
- Provide video clip analysis and shift breakdowns using authentic hockey terminology

COMMUNICATION STANDARDS:
- Use authentic coach and player terminology that Montreal Canadiens personnel understand
- Provide precise, actionable insights based on comprehensive statistical analysis  
- Maintain professional communication standards (no emojis, clean technical language)
- Structure responses with clear statistical evidence and strategic context

ANALYTICAL APPROACH:
- Leverage real-time data queries when needed for current statistics and trends
- Combine historical patterns with situational analysis for comprehensive insights
- Focus on Montreal-specific strategies, player development, and opponent analysis
- Provide both immediate tactical advice and long-term strategic recommendations

Your responses should demonstrate the analytical depth of a world-class hockey consultant while remaining accessible to coaches and players in game-planning and performance review contexts."""

        # Role-specific focus areas and communication styles
        self.role_templates = {
            UserRole.COACH: {
                "style": "tactical_strategic",
                "focus": ["strategy", "matchups", "deployment", "adjustments", "video_analysis", "shift_patterns"],
                "context": "Focus on game planning, lineup decisions, and tactical adjustments with strategic depth."
            },
            UserRole.PLAYER: {
                "style": "performance_focused",
                "focus": ["individual_performance", "improvement", "comparisons", "goals", "shift_analysis", "video_clips"],
                "context": "Focus on personal performance insights, skill development, and actionable feedback using hockey terminology players understand."
            },
            UserRole.ANALYST: {
                "style": "analytical_comprehensive",
                "focus": ["statistics", "trends", "correlations", "predictions", "video_analytics", "advanced_metrics"],
                "context": "Focus on comprehensive data-driven insights with statistical depth, advanced metrics, and predictive analysis."
            },
            UserRole.STAFF: {
                "style": "operational_clear",
                "focus": ["team_operations", "player_welfare", "logistics", "communication", "shift_scheduling"],
                "context": "Focus on clear, accessible insights for team operations, player welfare, and organizational efficiency."
            },
            UserRole.SCOUT: {
                "style": "evaluative_detailed",
                "focus": ["player_evaluation", "comparisons", "potential", "fit_assessment", "shift_effectiveness", "video_scouting"],
                "context": "Focus on detailed player evaluation, comparative analysis, and recruitment assessment using video and statistical evidence."
            }
        }
    
    async def process(self, state: AgentState) -> AgentState:
        """Process response synthesis using fine-tuned model"""
        
        state = update_state_step(state, "response_synthesis")
        start_time = datetime.now()
        
        try:
            # Validate we have sufficient data for response
            if not has_required_data(state):
                return self._handle_insufficient_data(state, start_time)
            
            # Extract synthesis parameters
            user_context = state["user_context"]
            query = state["original_query"]
            retrieved_context = state.get("retrieved_context", [])
            analytics_data = state.get("analytics_data", {})
            tool_results = state.get("tool_results", [])
            
            logger.info(f"Synthesizing response for {user_context.role.value}: {query[:100]}...")
            
            # Build comprehensive prompt
            synthesis_prompt = self._build_synthesis_prompt(
                user_context=user_context,
                query=query,
                retrieved_context=retrieved_context,
                analytics_data=analytics_data,
                tool_results=tool_results
            )
            
            # Generate response using model
            response = await self._generate_response(synthesis_prompt, user_context, state)
            
            # Post-process and validate response
            final_response = self._post_process_response(
                response, state, user_context
            )
            
            # Calculate execution time
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Create tool result
            tool_result = ToolResult(
                tool_type=ToolType.PARQUET_QUERY,  # Represents synthesis
                success=len(final_response.strip()) > 0,
                data={"response": final_response, "word_count": len(final_response.split())},
                execution_time_ms=execution_time,
                citations=state.get("evidence_chain", [])
            )
            
            # Update state
            state["final_response"] = final_response
            state = add_tool_result(state, tool_result)
            
            logger.info(f"Response synthesis completed in {execution_time}ms ({len(final_response.split())} words)")
            
        except Exception as e:
            logger.error(f"Error in response synthesis: {str(e)}")
            state = add_error(state, f"Response synthesis failed: {str(e)}")
            
            # Provide fallback response
            state["final_response"] = self._generate_fallback_response(state, user_context)
            
            # Add failed tool result
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            tool_result = ToolResult(
                tool_type=ToolType.PARQUET_QUERY,
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
            state = add_tool_result(state, tool_result)
        
        return state
    
    def _build_synthesis_prompt(
        self,
        user_context,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        analytics_data: Dict[str, Any],
        tool_results: List[ToolResult]
    ) -> str:
        """Build comprehensive prompt for response synthesis using DeepSeek-R1-Distill-Qwen-32B"""
        
        role_config = self.role_templates.get(
            user_context.role, 
            self.role_templates[UserRole.STAFF]
        )
        
        # Build context sections
        context_section = self._format_retrieved_context(retrieved_context)
        analytics_section = self._format_analytics_data(analytics_data)
        clips_section = self._format_video_clips(analytics_data)
        evidence_section = self._format_evidence_chain(tool_results)
        
        # Construct synthesis prompt
        synthesis_prompt = f"""
{self.base_system_prompt}

ROLE-SPECIFIC CONTEXT: {role_config['context']}

TOOL ORCHESTRATION CAPABILITIES:
- [TOOL: vector_search] - Hockey knowledge, rules, strategic context, and historical insights
- [TOOL: parquet_query] - Real-time player/team statistics, game data, and performance metrics
- [TOOL: clip_retrieval] - Video clips, player shifts, highlights, and visual game analysis
- [TOOL: calculate_advanced_metrics] - xG, Corsi, zone analysis, possession metrics, and advanced analytics  
- [TOOL: matchup_analysis] - Opponent analysis, head-to-head comparisons, and tactical recommendations
- [TOOL: visualization] - Statistical charts, heatmaps, and data visualizations

RESPONSE REQUIREMENTS:
- Demonstrate sophisticated analytical reasoning with multi-step analysis
- Integrate data from all available tools meaningfully and comprehensively
- Provide clear evidence chains and source attribution for all insights
- Use authentic Montreal Canadiens hockey terminology and communication style
- Focus on: {', '.join(role_config['focus'])}
- Maintain professional standards with precise, actionable insights

USER QUERY: {query}

HOCKEY CONTEXT RETRIEVED:
{context_section}

STATISTICAL ANALYTICS:
{analytics_section}

VIDEO CLIPS & SHIFTS:
{clips_section}

EVIDENCE SOURCES:
{evidence_section}

ANALYTICAL INSTRUCTIONS:
1. Process the query using multi-step reasoning appropriate for a {user_context.role.value}
2. Synthesize insights from hockey context, statistical data, and video analysis
3. Provide comprehensive analysis that leverages all available tool outputs
4. Structure response with clear reasoning chains and strategic/tactical depth
5. Include specific data points, shift analysis, and video references where relevant
6. Ensure actionable recommendations suitable for Montreal Canadiens operations
7. Maintain focus on: {role_config['context']}

Generate your professional hockey analytics response:
"""
        
        return synthesis_prompt
    
    async def _generate_response(
        self, 
        synthesis_prompt: str, 
        user_context,
        state: AgentState = None
    ) -> str:
        """Generate response using the fine-tuned model or fallback"""
        
        # Try primary model (SageMaker endpoint) first
        if self.model_config.primary_model_endpoint:
            try:
                return await self._call_sagemaker_endpoint(synthesis_prompt)
            except Exception as e:
                logger.warning(f"SageMaker endpoint failed, falling back: {str(e)}")
        
        # Fallback to OpenAI for development/testing
        if self.model_config.fallback_api_key and openai:
            try:
                return await self._call_openai_fallback(synthesis_prompt)
            except Exception as e:
                logger.warning(f"OpenAI fallback failed: {str(e)}")
        
        # Final fallback to template-based response
        return self._generate_template_response(synthesis_prompt, user_context, state)
    
    async def _call_sagemaker_endpoint(self, prompt: str) -> str:
        """Call the SageMaker endpoint for the fine-tuned DeepSeek-R1-Distill-Qwen-32B model"""
        
        # This would implement actual SageMaker endpoint calling
        # For now, return a placeholder indicating the integration point
        
        logger.info("Calling SageMaker endpoint for DeepSeek-R1-Distill-Qwen-32B model")
        
        # Simulate processing time for advanced reasoning model
        await asyncio.sleep(0.2)
        
        return "SageMaker endpoint response placeholder - integrate with actual fine-tuned DeepSeek-R1-Distill-Qwen-32B model"
    
    async def _call_openai_fallback(self, prompt: str) -> str:
        """Call OpenAI API as fallback during development (supporting DeepSeek-R1 functionality)"""
        
        if not openai:
            raise Exception("OpenAI library not available")
        
        try:
            client = openai.AsyncOpenAI(api_key=self.model_config.fallback_api_key)
            
            response = await client.chat.completions.create(
                model=self.model_config.fallback_model,
                messages=[
                    {"role": "system", "content": self.base_system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.model_config.temperature,
                max_tokens=self.model_config.max_tokens,
                top_p=self.model_config.top_p
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise
    
    def _generate_template_response(
        self, 
        synthesis_prompt: str, 
        user_context,
        state: AgentState = None
    ) -> str:
        """Generate template-based response as final fallback with clip data integration"""
        
        # Extract clip data from state tool results (more reliable than parsing prompt)
        clip_data = self._extract_clip_data_from_state(state) if state else []
        
        role_config = self.role_templates.get(
            user_context.role,
            self.role_templates[UserRole.STAFF]
        )
        
        # Generate response based on whether we have clip data
        if clip_data and len(clip_data) > 0:
            return self._generate_clip_response(clip_data, user_context, role_config)
        else:
            return self._generate_standard_fallback(user_context, role_config)
    
    def _extract_clip_data_from_state(self, state: AgentState) -> List[Dict[str, Any]]:
        """Extract clip data directly from agent state tool results"""
        
        if not state or "tool_results" not in state:
            return []
        
        # Find clip retrieval tool results
        for tool_result in state["tool_results"]:
            if (tool_result.tool_type == ToolType.CLIP_RETRIEVAL and 
                tool_result.success and 
                tool_result.data):
                
                clips_list = tool_result.data.get("clips", [])
                return clips_list
        
        # Also check analytics_data for clips
        analytics_data = state.get("analytics_data", {})
        if "clips" in analytics_data:
            return analytics_data["clips"]
        
        return []
    
    def _extract_clip_data_from_prompt(self, synthesis_prompt: str) -> List[Dict[str, Any]]:
        """Extract clip data from synthesis prompt"""
        
        # Look for the VIDEO CLIPS & SHIFTS section in the prompt
        import re
        
        clip_section_match = re.search(
            r'VIDEO CLIPS & SHIFTS:\s*(.*?)(?=\n\n|\nEVIDENCE|\nANALYTICAL|$)', 
            synthesis_prompt, 
            re.DOTALL
        )
        
        if not clip_section_match:
            return []
        
        clip_section = clip_section_match.group(1)
        
        # Extract clip information using regex
        clip_pattern = r'(\d+)\.\s+(.*?)\s+-\s+(.*?)\s+\((.*?)\)(?:\s+\|\s+(.*?))?(?:\s+\|\s+([\d.]+)s)?'
        matches = re.findall(clip_pattern, clip_section)
        
        clips = []
        for match in matches:
            clips.append({
                "title": match[1].strip(),
                "player_name": match[2].strip(),
                "event_type": match[3].strip(),
                "game_info": match[4].strip() if len(match) > 4 and match[4] else "",
                "duration": float(match[5]) if len(match) > 5 and match[5] else 0.0
            })
        
        return clips
    
    def _generate_clip_response(
        self, 
        clip_data: List[Dict[str, Any]], 
        user_context, 
        role_config: Dict[str, Any]
    ) -> str:
        """Generate response when clip data is available"""
        
        clips_count = len(clip_data)
        
        # Create personalized greeting based on role
        if user_context.role == UserRole.PLAYER:
            greeting = f"Here are your video highlights, {user_context.name or 'player'}:"
        elif user_context.role == UserRole.COACH:
            greeting = f"Here are the requested video clips for analysis:"
        else:
            greeting = f"Here are the video clips from your query:"
        
        # Format clip information
        clip_details = []
        
        for i, clip in enumerate(clip_data, 1):
            title = clip.get('title', f'Clip {i}')
            player = clip.get('player_name', 'Unknown Player')
            event = clip.get('event_type', 'shift')
            game_info = clip.get('game_info', '')
            duration = clip.get('duration', 0)
            
            detail = f"{i}. {title}"
            if game_info:
                detail += f" | {game_info}"
            if duration > 0:
                detail += f" | {duration}s"
            
            clip_details.append(detail)
        
        # Create comprehensive response
        response = f"""{greeting}

Found {clips_count} video clip{'s' if clips_count != 1 else ''} matching your request:

{chr(10).join(clip_details)}

The clips are now loaded in the video player below. You can use the playback controls to review your performance and analyze key moments from the game.

Note: Our full DeepSeek-R1-Distill-Qwen-32B analytics model is currently in training. Once available, you'll receive even more detailed analysis combining these video clips with advanced statistical insights and tactical recommendations."""
        
        return response
    
    def _generate_standard_fallback(self, user_context, role_config: Dict[str, Any]) -> str:
        """Generate standard fallback when no clips are available"""
        
        return f"""
I understand you're asking about hockey analytics from a {user_context.role.value} perspective for the Montreal Canadiens.

Based on the available data and context, I can provide insights focused on {', '.join(role_config['focus'])}.

However, I'm currently operating in fallback mode. For the most comprehensive analysis with our fine-tuned DeepSeek-R1-Distill-Qwen-32B analytics model, please ensure:

1. The SageMaker endpoint for our DeepSeek-R1 model is properly configured
2. All data sources (RAG, Parquet, video clips) are available  
3. Network connectivity is established

I'm designed to provide sophisticated multi-step reasoning analysis combining:
- Hockey domain knowledge from our RAG system
- Real-time statistics from Parquet data files
- Video clip analysis and shift breakdowns  
- Advanced metrics calculations and predictive insights
- Role-specific insights tailored for Montreal Canadiens personnel

Please try your query again once the full HeartBeat Engine system is available.
"""
    
    def _format_retrieved_context(
        self, 
        retrieved_context: List[Dict[str, Any]]
    ) -> str:
        """Format retrieved context for prompt integration"""
        
        if not retrieved_context:
            return "No specific hockey context retrieved."
        
        formatted_context = []
        
        for i, context in enumerate(retrieved_context[:3], 1):  # Limit to top 3
            content = context.get("content", "")
            source = context.get("source", "unknown")
            category = context.get("category", "general")
            
            formatted_context.append(
                f"{i}. [{source}:{category}] {content[:200]}..."
            )
        
        return "\n".join(formatted_context)
    
    def _format_analytics_data(self, analytics_data: Dict[str, Any]) -> str:
        """Format analytics data for prompt integration"""
        
        if not analytics_data:
            return "No analytics data available."
        
        analysis_type = analytics_data.get("analysis_type", "unknown")
        
        if "error" in analytics_data:
            return f"Analytics error: {analytics_data['error']}"
        
        # Format based on analysis type
        if analysis_type == "player_performance":
            return self._format_player_analytics(analytics_data)
        elif analysis_type == "team_performance":
            return self._format_team_analytics(analytics_data)
        else:
            return f"Analytics type: {analysis_type}\nData: {str(analytics_data)[:300]}..."
    
    def _format_player_analytics(self, data: Dict[str, Any]) -> str:
        """Format player analytics data"""
        
        players = data.get("players", [])
        metrics = data.get("metrics", {})
        
        formatted = f"Player Analysis: {', '.join(players)}\n"
        
        for player, stats in metrics.items():
            formatted += f"- {player}: {stats.get('points', 0)} points in {stats.get('games_played', 0)} games\n"
        
        return formatted
    
    def _format_team_analytics(self, data: Dict[str, Any]) -> str:
        """Format team analytics data"""
        
        team = data.get("team", "MTL")
        metrics = data.get("metrics", {})
        
        record = metrics.get("record", {})
        formatted = f"Team Analysis: {team}\n"
        formatted += f"- Record: {record.get('wins', 0)}-{record.get('losses', 0)}-{record.get('overtime', 0)}\n"
        formatted += f"- Goals For/Against: {metrics.get('goals_for', 0)}/{metrics.get('goals_against', 0)}\n"
        
        return formatted
    
    def _format_video_clips(self, analytics_data: Dict[str, Any]) -> str:
        """Format video clips and shifts data for prompt integration"""
        
        clips = analytics_data.get("clips", [])
        
        if not clips:
            return "No video clips or shifts available."
        
        formatted_clips = []
        
        for i, clip in enumerate(clips[:5], 1):  # Limit to top 5 clips
            if isinstance(clip, dict):
                title = clip.get("title", f"Clip {i}")
                player = clip.get("player_name", "Unknown Player")
                game_info = clip.get("game_info", "")
                event_type = clip.get("event_type", "shift")
                duration = clip.get("duration", 0)
                
                formatted_clips.append(
                    f"{i}. {title} - {player} ({event_type})"
                    f"{f' | {game_info}' if game_info else ''}"
                    f"{f' | {duration}s' if duration > 0 else ''}"
                )
        
        if formatted_clips:
            return f"Available video clips/shifts ({len(clips)} total):\n" + "\n".join(formatted_clips)
        else:
            return "Video clips found but formatting unavailable."
    
    def _format_evidence_chain(self, tool_results: List[ToolResult]) -> str:
        """Format evidence chain from tool results"""
        
        if not tool_results:
            return "No evidence chain available."
        
        evidence_items = []
        
        for result in tool_results:
            if result.success and result.citations:
                evidence_items.extend(result.citations)
        
        if evidence_items:
            return "Evidence sources: " + ", ".join(set(evidence_items))
        else:
            return "Evidence chain in development."
    
    def _post_process_response(
        self, 
        response: str, 
        state: AgentState, 
        user_context
    ) -> str:
        """Post-process and validate the generated response"""
        
        # Ensure response length is appropriate
        if len(response) > self.orchestration_config.max_response_length:
            response = response[:self.orchestration_config.max_response_length] + "..."
        
        # Add citations if required and available
        if self.orchestration_config.require_citations:
            citations = state.get("evidence_chain", [])
            if citations and not any(cite in response for cite in citations):
                response += f"\n\nSources: {', '.join(set(citations))}"
        
        return response.strip()
    
    def _handle_insufficient_data(
        self, 
        state: AgentState, 
        start_time: datetime
    ) -> AgentState:
        """Handle case when insufficient data is available"""
        
        logger.warning("Insufficient data for response synthesis")
        
        fallback_response = """
I apologize, but I don't have sufficient data to provide a comprehensive analysis for your query. 

This could be due to:
- Data sources being temporarily unavailable
- Query requiring data outside my current scope
- Network connectivity issues

Please try rephrasing your question or check back shortly. I'm designed to provide detailed hockey analytics combining contextual knowledge with real-time statistics.
"""
        
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        tool_result = ToolResult(
            tool_type=ToolType.PARQUET_QUERY,
            success=False,
            error="Insufficient data for synthesis",
            execution_time_ms=execution_time
        )
        
        state["final_response"] = fallback_response
        state = add_tool_result(state, tool_result)
        
        return state
    
    def _generate_fallback_response(self, state: AgentState, user_context) -> str:
        """Generate a fallback response when synthesis fails"""
        
        # Check if we have clip data even when synthesis fails
        clip_data = self._extract_clip_data_from_state(state)
        
        if clip_data and len(clip_data) > 0:
            role_config = self.role_templates.get(
                user_context.role,
                self.role_templates[UserRole.STAFF]
            )
            return self._generate_clip_response(clip_data, user_context, role_config)
        
        query = state.get("original_query", "your query")
        
        return f"""
I encountered an issue processing your request about "{query[:100]}...". 

I'm designed to provide comprehensive hockey analytics by combining:
- Domain expertise from hockey knowledge base
- Real-time statistics and performance data
- Video clip analysis and shift breakdowns
- Advanced metrics and comparative analysis

Please try your question again, or contact support if the issue persists.
"""
