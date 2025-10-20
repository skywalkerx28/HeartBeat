"""
Test script for Qwen3-enhanced HeartBeat Orchestrator

Tests the complete integration of Qwen3-Next-80B Thinking with LangGraph orchestration.
"""

import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from datetime import datetime

from orchestrator.agents.qwen3_best_practices_orchestrator import qwen3_best_practices_orchestrator as qwen3_orchestrator
from orchestrator.utils.state import UserContext
from orchestrator.config.settings import UserRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_qwen3_orchestrator():
    """Test the Qwen3-enhanced orchestrator with a hockey analytics query."""
    
    print("=" * 80)
    print("HEARTBEAT ENGINE - QWEN3 ORCHESTRATOR TEST")
    print("=" * 80)
    
    # Create test user context
    user_context = UserContext(
        user_id="test_analyst_001",
        role=UserRole.ANALYST,
        name="Test Analyst",
        team_access=["MTL"],
        session_id="test_session_001"
    )
    
    # Test query
    test_query = "How effective was Montreal's power play against Toronto this season?"
    
    print(f"\nUser: {user_context.name} ({user_context.role.value})")
    print(f"Query: {test_query}")
    print("\nProcessing with Qwen3-Next-80B Thinking...\n")
    
    try:
        # Process query
        start_time = datetime.now()
        response = await qwen3_orchestrator.process_query(
            query=test_query,
            user_context=user_context
        )
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Display results
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        
        print(f"\nQuery Type: {response['query_type']}")
        print(f"Processing Time: {processing_time:.0f}ms")
        print(f"Iterations: {response.get('iterations', 0)}")
        print(f"Model: {response.get('model', 'unknown')}")
        
        print("\n" + "-" * 80)
        print("TOOL EXECUTIONS")
        print("-" * 80)
        
        for i, tool_result in enumerate(response['tool_results'], 1):
            print(f"\n{i}. {tool_result['tool']}")
            print(f"   Status: {'SUCCESS' if tool_result['success'] else 'FAILED'}")
            print(f"   Time: {tool_result['processing_time_ms']}ms")
            if tool_result.get('error'):
                print(f"   Error: {tool_result['error']}")
            if tool_result.get('citations'):
                print(f"   Citations: {len(tool_result['citations'])}")
        
        print("\n" + "-" * 80)
        print("FINAL RESPONSE")
        print("-" * 80)
        print(f"\n{response['response']}")
        
        if response.get('evidence_chain'):
            print("\n" + "-" * 80)
            print("EVIDENCE CHAIN")
            print("-" * 80)
            for evidence in response['evidence_chain'][:3]:  # Show first 3
                print(f"  - {evidence[:100]}...")
        
        if response.get('errors'):
            print("\n" + "-" * 80)
            print("ERRORS")
            print("-" * 80)
            for error in response['errors']:
                print(f"  - {error}")
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        
        # Summary
        success = response.get('success', True) and not response.get('error')
        print(f"\nStatus: {'✓ SUCCESS' if success else '✗ FAILED'}")
        print(f"Tools Used: {len(response['tool_results'])}")
        print(f"Total Time: {processing_time:.0f}ms")
        
        return response
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def test_multi_query_scenarios():
    """Test multiple query scenarios to validate orchestrator behavior."""
    
    print("\n" + "=" * 80)
    print("MULTI-QUERY SCENARIO TEST")
    print("=" * 80)
    
    user_context = UserContext(
        user_id="test_coach_001",
        role=UserRole.COACH,
        name="Test Coach",
        team_access=["MTL"]
    )
    
    test_queries = [
        "What are the key principles of effective zone exits in hockey?",  # Context query
        "Show me Montreal's shot statistics from the last 5 games",  # Data query
        "Compare Suzuki's performance to other centers in the league"  # Complex query
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'-' * 80}")
        print(f"Scenario {i}/3")
        print(f"{'-' * 80}")
        print(f"Query: {query}")
        
        try:
            response = await qwen3_orchestrator.process_query(
                query=query,
                user_context=user_context
            )
            
            print(f"  ✓ Type: {response['query_type']}")
            print(f"  ✓ Tools: {len(response['tool_results'])}")
            print(f"  ✓ Time: {response['processing_time_ms']}ms")
            print(f"  ✓ Response: {response['response'][:100]}...")
            
        except Exception as e:
            print(f"  ✗ Failed: {str(e)}")
    
    print("\n" + "=" * 80)
    print("MULTI-QUERY TEST COMPLETE")
    print("=" * 80)


async def main():
    """Run all tests."""
    
    print("\n🏒 HeartBeat Engine - Qwen3 Orchestrator Test Suite\n")
    
    # Test 1: Single query
    await test_qwen3_orchestrator()
    
    # Test 2: Multiple scenarios (optional - comment out if too slow)
    # await test_multi_query_scenarios()
    
    print("\n✓ All tests complete!\n")
    print("Next steps:")
    print("1. Connect to Vertex for RAG searches")
    print("2. Implement Parquet query execution")
    print("3. Add visualization generation")
    print("4. Deploy Qwen3-VL for visual analysis")
    print()


if __name__ == "__main__":
    asyncio.run(main())
