#!/usr/bin/env python3
"""
Test script for ClipRetrieverNode integration
Tests the complete flow: NL query -> event search -> clip cutting -> results
"""

import asyncio
import logging
from pathlib import Path
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.nodes.clip_retriever import ClipRetrieverNode
from orchestrator.utils.state import create_initial_state, UserContext, UserRole


async def test_clip_retrieval():
    """Test the complete clip retrieval flow"""
    
    print("\n" + "="*60)
    print("Testing ClipRetrieverNode - Complete Integration")
    print("="*60 + "\n")
    
    # Initialize node
    node = ClipRetrieverNode()
    
    # Create user context (using WSH player for testing with clean video)
    user_context = UserContext(
        user_id="test_analyst",
        name="Test Analyst",
        role=UserRole.ANALYST,  # Use analyst role for broader access during testing
        team_access=["WSH", "NYR"],
        preferences={"player_id": "8478463"}
    )
    
    # Create proper initial state
    query = "Show me d-zone exits from the WSH vs NYR game"
    state = create_initial_state(user_context, query)
    
    # Add required fields for clip retrieval
    state["intent_analysis"] = {"intent": "clip_retrieval"}
    state["required_tools"] = ["clip_retrieval"]
    
    print(f"Query: {query}")
    print(f"User: {user_context.name} ({user_context.role.value})")
    print()
    
    # Process the query
    result_state = await node.process(state)
    
    # Display results
    print("\n" + "-"*60)
    print("Results:")
    print("-"*60 + "\n")
    
    if result_state.get('errors'):
        print(f"Errors: {result_state['errors']}")
    
    tool_results = result_state.get('tool_results', [])
    if tool_results:
        for tool_result in tool_results:
            print(f"Tool: {tool_result.tool_type}")
            print(f"Success: {tool_result.success}")
            print(f"Execution time: {tool_result.execution_time_ms}ms")
            
            if tool_result.success and tool_result.data:
                clips = tool_result.data.get('clips', [])
                print(f"\nFound {len(clips)} clips:")
                
                for i, clip in enumerate(clips, 1):
                    print(f"\n  {i}. {clip.get('title', 'Untitled')}")
                    print(f"     ID: {clip.get('clip_id')}")
                    print(f"     Player: {clip.get('player_name', clip.get('player_id'))}")
                    print(f"     Event: {clip.get('event_type')} ({clip.get('outcome', 'N/A')})")
                    print(f"     Game: {clip.get('game_id')} - Period {clip.get('period')}")
                    print(f"     Duration: {clip.get('duration', 0):.1f}s")
                    print(f"     File: {clip.get('file_path')}")
                    print(f"     Thumbnail: {clip.get('thumbnail_path')}")
                    print(f"     URL: {clip.get('file_url')}")
                
                print(f"\nTotal clips generated: {len(clips)}")
                print(f"Citations: {tool_result.citations}")
    
    # Check analytics_data
    analytics = result_state.get('analytics_data', {})
    if analytics.get('clips'):
        print(f"\nAnalytics data populated with {len(analytics['clips'])} clips")
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_clip_retrieval())

