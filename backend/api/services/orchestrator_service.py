"""
HeartBeat Engine - Orchestrator Service
Montreal Canadiens Advanced Analytics Assistant

Service layer that wraps the LangGraph orchestrator for API use.
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

from orchestrator.agents.qwen3_best_practices_orchestrator import Qwen3BestPracticesOrchestrator
from orchestrator.utils.state import UserContext, QueryType
from orchestrator.config.settings import UserRole

logger = logging.getLogger(__name__)

class OrchestrationService:
    """
    Service layer that provides a clean interface to the LangGraph orchestrator.
    
    This service:
    - Handles query processing through the orchestrator
    - Manages user context and permissions
    - Formats responses for API consumption
    - Provides caching and error handling
    """
    
    def __init__(self, orchestrator: Qwen3BestPracticesOrchestrator):
        self.orchestrator = orchestrator
        self.query_cache = {}  # Simple in-memory cache
    
    async def process_hockey_query(
        self,
        query: str,
        user_context: UserContext,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a hockey analytics query through the orchestrator.
        
        Args:
            query: User's hockey question
            user_context: User identity and permissions
            context: Optional additional context
            
        Returns:
            Structured response with analytics data
        """
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing query for {user_context.role.value}: {query[:100]}...")
            
            # Check cache first (simple implementation)
            cache_key = f"{user_context.user_id}:{hash(query)}"
            if cache_key in self.query_cache:
                logger.info("Returning cached response")
                return self.query_cache[cache_key]
            
            # Process through orchestrator
            result = await self.orchestrator.process_query(
                query=query,
                user_context=user_context
            )
            
            # Add processing metadata
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            result["api_processing_time_ms"] = int(processing_time)
            result["user_role"] = user_context.role.value
            result["timestamp"] = datetime.now().isoformat()
            
            # Cache successful results (simple TTL would be better)
            if result.get("success", False) and len(self.query_cache) < 100:
                self.query_cache[cache_key] = result
            
            logger.info(f"Query processed successfully in {processing_time:.0f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Error in orchestration service: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an error processing your request. Please try again or rephrase your question.",
                "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                "user_role": user_context.role.value,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_user_permissions(self, user_role: UserRole) -> Dict[str, Any]:
        """Get permissions for a user role"""
        from orchestrator.config.settings import settings
        return settings.get_user_permissions(user_role)
    
    def validate_user_access(
        self, 
        user_context: UserContext, 
        requested_data: Dict[str, Any]
    ) -> bool:
        """
        Validate if user has access to requested data.
        
        Args:
            user_context: User identity and permissions
            requested_data: Data the user is trying to access
            
        Returns:
            True if access is allowed, False otherwise
        """
        
        permissions = self.get_user_permissions(user_context.role)
        
        # Check team access
        requested_teams = requested_data.get("teams", user_context.team_access)
        for team in requested_teams:
            if team not in user_context.team_access:
                return False
        
        # Check data scope permissions
        data_scope = requested_data.get("scope", "team")
        if data_scope not in permissions.get("data_scope", []):
            return False
        
        # Check advanced metrics access
        if requested_data.get("advanced_metrics", False) and not permissions.get("advanced_metrics", False):
            return False
        
        # Check opponent data access
        if requested_data.get("opponent_data", False) and not permissions.get("opponent_data", False):
            return False
        
        return True
    
    def clear_cache(self):
        """Clear the query cache"""
        self.query_cache.clear()
        logger.info("Query cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.query_cache),
            "cache_keys": list(self.query_cache.keys())[:10]  # First 10 keys
        }
