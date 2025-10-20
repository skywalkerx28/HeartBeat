"""
HeartBeat Engine - Intent Analyzer Node
Montreal Canadiens Advanced Analytics Assistant

Analyzes user queries to determine intent, required tools, and processing approach.
"""

import re
from typing import Dict, List, Any
import logging

from orchestrator.utils.state import AgentState, QueryType, ToolType, update_state_step
from orchestrator.config.settings import settings

logger = logging.getLogger(__name__)

class IntentAnalyzerNode:
    """
    Analyzes user intent to determine:
    1. Query type (player analysis, game analysis, etc.)
    2. Required tools (Pinecone RAG, Parquet analytics, etc.)
    3. Data scope and permissions needed
    """
    
    def __init__(self):
        self.query_patterns = {
            QueryType.PLAYER_ANALYSIS: [
                r'\b(player|skater|goalie|forward|defenseman|center|wing)\b',
                r'\b(performance|stats|analytics|metrics)\b',
                r'\b(suzuki|caufield|hutson|slafkovsky|guhle|matheson)\b'
            ],
            QueryType.TEAM_PERFORMANCE: [
                r'\b(team|canadiens|habs|mtl|montreal)\b',
                r'\b(record|standings|performance|season)\b',
                r'\b(powerplay|penalty kill|special teams)\b'
            ],
            QueryType.GAME_ANALYSIS: [
                r'\b(game|match|vs|against)\b',
                r'\b(recap|analysis|breakdown|review)\b',
                r'\b(last game|tonight|yesterday)\b'
            ],
            QueryType.MATCHUP_COMPARISON: [
                r'\b(compare|vs|versus|against)\b',
                r'\b(matchup|head to head|h2h)\b',
                r'\b(better|worse|advantage)\b'
            ],
            QueryType.TACTICAL_ANALYSIS: [
                r'\b(strategy|tactics|system|scheme)\b',
                r'\b(zone entry|exit|forecheck|backcheck)\b',
                r'\b(line combinations|deployment)\b'
            ],
            QueryType.STATISTICAL_QUERY: [
                r'\b(stats|statistics|numbers|data)\b',
                r'\b(xG|corsi|fenwick|PDO|shooting percentage)\b',
                r'\b(how many|what is|show me)\b'
            ],
            QueryType.CLIP_RETRIEVAL: [
                r'\b(clips?|highlights?|video|footage|replay|shifts?)\b',
                r'\b(show me|watch|see|display)\b.*\b(clips?|video|shifts?)\b',
                r'\b(my clips?|my highlights?|my video|my shifts?)\b',
                r'\b(from last game|last \d+ games)\b.*\b(clips?|video|shifts?)\b'
            ]
        }
        
        self.tool_indicators = {
            ToolType.VECTOR_SEARCH: [
                r'\b(explain|what is|how does|definition|rules)\b',
                r'\b(context|background|history)\b',
                r'\b(hockey|NHL|strategy|tactics)\b'
            ],
            ToolType.PARQUET_QUERY: [
                r'\b(stats|statistics|numbers|data|metrics)\b',
                r'\b(last \d+ games|this season|career)\b',
                r'\b(goals|assists|points|shots|hits)\b'
            ],
            ToolType.CALCULATE_METRICS: [
                r'\b(xG|expected goals|corsi|fenwick|PDO)\b',
                r'\b(shooting percentage|save percentage)\b',
                r'\b(zone entry|exit|possession)\b'
            ],
            ToolType.MATCHUP_ANALYSIS: [
                r'\b(vs|versus|against|compared to)\b',
                r'\b(matchup|head to head|opponent)\b',
                r'\b(advantage|disadvantage|better|worse)\b'
            ],
            ToolType.VISUALIZATION: [
                r'\b(show|chart|graph|plot|heatmap)\b',
                r'\b(visualize|display|see)\b'
            ],
            ToolType.CLIP_RETRIEVAL: [
                r'\b(clips?|highlights?|video|footage|replay|shifts?)\b',
                r'\b(show me|watch|see|display)\b.*\b(clips?|video|highlights?|shifts?)\b',
                r'\b(my clips?|my highlights?|my video|my shifts?)\b',
                r'\b(from last game|last \d+ games)\b.*\b(clips?|video|shifts?)\b',
                r'\b(goals?|assists?|saves?|hits?)\b.*\b(clips?|video|shifts?)\b'
            ]
        }
    
    def process(self, state: AgentState) -> AgentState:
        """Process intent analysis for the user query"""
        
        state = update_state_step(state, "intent_analysis")
        query = state["original_query"].lower()
        user_context = state["user_context"]
        
        logger.info(f"Analyzing intent for query: {query[:100]}...")
        
        # Determine query type
        query_type = self._classify_query_type(query)
        state["query_type"] = query_type
        
        # Identify required tools
        required_tools = self._identify_required_tools(query, user_context.role)
        state["required_tools"] = required_tools
        
        # Create intent analysis summary
        intent_analysis = {
            "query_type": query_type.value,
            "complexity": self._assess_complexity(query),
            "requires_context": self._needs_hockey_context(query),
            "requires_data": self._needs_analytical_data(query),
            "user_permissions": settings.get_user_permissions(user_context.role),
            "estimated_tools": len(required_tools),
            "processing_approach": self._determine_approach(query_type, required_tools)
        }
        
        state["intent_analysis"] = intent_analysis
        
        logger.info(f"Intent analysis complete: {query_type.value}, {len(required_tools)} tools required")
        
        return state
    
    def _classify_query_type(self, query: str) -> QueryType:
        """Classify the query into a specific type"""
        
        scores = {}
        
        for query_type, patterns in self.query_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, query, re.IGNORECASE))
                score += matches
            scores[query_type] = score
        
        # Return the highest scoring type, or GENERAL_HOCKEY if no clear match
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            return QueryType.GENERAL_HOCKEY
    
    def _identify_required_tools(self, query: str, user_role) -> List[ToolType]:
        """Identify which tools are needed for this query"""
        
        required_tools = []
        
        # First pass: Pattern-based tool detection
        for tool_type, patterns in self.tool_indicators.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    required_tools.append(tool_type)
                    break  # Avoid duplicates
        
        # Enhanced clip detection logic
        clip_keywords = [
            'clips?', 'highlights?', 'video', 'footage', 'replay', 'shifts?',
            'my clips?', 'my highlights?', 'my shifts?', 'my video'
        ]
        
        # Check if any clip keywords are present
        query_has_clips = any(re.search(rf'\b{keyword}\b', query, re.IGNORECASE) 
                             for keyword in clip_keywords)
        
        # Also check for event + visual context combinations
        event_visual_patterns = [
            r'\b(goals?|assists?|saves?|hits?)\b.*\b(show|display|watch|see)\b',
            r'\b(show|display|watch|see)\b.*\b(goals?|assists?|saves?|hits?)\b'
        ]
        
        has_event_visual = any(re.search(pattern, query, re.IGNORECASE) 
                              for pattern in event_visual_patterns)
        
        # Add clip retrieval if detected
        if ((query_has_clips or has_event_visual) and 
            ToolType.CLIP_RETRIEVAL not in required_tools):
            required_tools.append(ToolType.CLIP_RETRIEVAL)
        
        # Always include vector search for context unless it's a pure statistical query
        if (ToolType.VECTOR_SEARCH not in required_tools and 
            not self._is_pure_stats_query(query)):
            required_tools.append(ToolType.VECTOR_SEARCH)
        
        # Add parquet query for most analytical requests
        if (any(word in query for word in ['stats', 'performance', 'analysis', 'compare']) and
            ToolType.PARQUET_QUERY not in required_tools):
            required_tools.append(ToolType.PARQUET_QUERY)
        
        return required_tools
    
    def _assess_complexity(self, query: str) -> str:
        """Assess query complexity level"""
        
        complexity_indicators = {
            "simple": [r'\b(what is|who is|when)\b'],
            "moderate": [r'\b(how|why|compare|analyze)\b'],
            "complex": [r'\b(strategy|tactical|multi-step|correlation|trend)\b']
        }
        
        for level, patterns in complexity_indicators.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return level
        
        # Default based on query length and structure
        if len(query.split()) > 15 or '?' in query and 'and' in query:
            return "complex"
        elif len(query.split()) > 8:
            return "moderate"
        else:
            return "simple"
    
    def _needs_hockey_context(self, query: str) -> bool:
        """Determine if query needs hockey domain context"""
        context_indicators = [
            r'\b(explain|what is|how does|definition|rules|strategy|tactics)\b',
            r'\b(why|context|background|meaning)\b'
        ]
        
        return any(re.search(pattern, query, re.IGNORECASE) 
                  for pattern in context_indicators)
    
    def _needs_analytical_data(self, query: str) -> bool:
        """Determine if query needs real-time analytical data"""
        data_indicators = [
            r'\b(stats|statistics|numbers|metrics|data)\b',
            r'\b(performance|analysis|compare|vs)\b',
            r'\b(last \d+ games|this season|career)\b'
        ]
        
        return any(re.search(pattern, query, re.IGNORECASE) 
                  for pattern in data_indicators)
    
    def _is_pure_stats_query(self, query: str) -> bool:
        """Check if this is purely a statistical lookup"""
        pure_stats_patterns = [
            r'^\s*(what|how many|show me).*\b(goals|assists|points|games)\b',
            r'^\s*\b(stats|statistics)\b.*\b(for|of)\b'
        ]
        
        return any(re.search(pattern, query, re.IGNORECASE) 
                  for pattern in pure_stats_patterns)
    
    def _determine_approach(self, query_type: QueryType, required_tools: List[ToolType]) -> str:
        """Determine the processing approach based on analysis"""
        
        if len(required_tools) == 1:
            return "single_tool"
        elif ToolType.VECTOR_SEARCH in required_tools and len(required_tools) > 1:
            return "context_then_analysis"
        elif query_type in [QueryType.TACTICAL_ANALYSIS, QueryType.MATCHUP_COMPARISON]:
            return "multi_step_analysis"
        else:
            return "parallel_processing"
