"""
Direct test of data nodes without legacy orchestration
Tests that Parquet and Vertex-backed vector nodes can execute queries
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from orchestrator.nodes.parquet_analyzer import ParquetAnalyzerNode
from orchestrator.nodes.vector_retriever import VectorRetrieverNode
from orchestrator.utils.state import create_initial_state, UserContext, QueryType, ToolType
from orchestrator.config.settings import UserRole

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_parquet_node():
    """Test Parquet analyzer node directly"""
    
    print("\n" + "=" * 80)
    print("TEST 1: Parquet Analyzer Node (Direct)")
    print("=" * 80)
    
    # Create test state
    user_context = UserContext(
        user_id="test_analyst",
        role=UserRole.ANALYST,
        team_access=["MTL"]
    )
    
    state = create_initial_state(
        query="How many goals did Montreal score against Toronto?",
        user_context=user_context
    )
    
    state["query_type"] = QueryType.MATCHUP_COMPARISON
    state["required_tools"] = [ToolType.PARQUET_QUERY]
    state["intent_analysis"] = {
        "query_type": QueryType.MATCHUP_COMPARISON,
        "reasoning": "Test matchup query"
    }
    
    # Test Parquet node
    try:
        node = ParquetAnalyzerNode()
        print("\n✓ Parquet node initialized")
        print(f"  Data directory: {node.data_directory}")
        print(f"  Available files: {len(node.data_files)}")
        
        # Execute query
        print("\nExecuting parquet query...")
        result_state = await node.process(state)
        
        print(f"\n✓ Query executed")
        print(f"  Tool results: {len(result_state['tool_results'])}")
        
        if result_state['tool_results']:
            for result in result_state['tool_results']:
                print(f"\n  Result:")
                print(f"    Success: {result.success}")
                print(f"    Tool: {result.tool_type.value}")
                if result.data:
                    print(f"    Data preview: {str(result.data)[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        logger.error(f"Parquet test failed", exc_info=True)
        return False


async def test_vector_node():
    """Test Vertex-backed vector retriever node directly"""
    
    print("\n" + "=" * 80)
    print("TEST 2: Vector Retriever Node (Direct)")
    print("=" * 80)
    
    # Create test state
    user_context = UserContext(
        user_id="test_analyst",
        role=UserRole.ANALYST,
        team_access=["MTL"]
    )
    
    state = create_initial_state(
        query="What is power play effectiveness?",
        user_context=user_context
    )
    
    state["query_type"] = QueryType.GENERAL_HOCKEY
    state["required_tools"] = [ToolType.VECTOR_SEARCH]
    state["intent_analysis"] = {
        "query_type": QueryType.GENERAL_HOCKEY,
        "reasoning": "Test knowledge query"
    }
    
    # Test vector node
    try:
        node = VectorRetrieverNode()
        print("\n✓ Vector node initialized")
        
        # Execute query
        print("\nExecuting vector search...")
        result_state = await node.process(state)
        
        print(f"\n✓ Query executed")
        print(f"  Tool results: {len(result_state['tool_results'])}")
        
        if result_state['tool_results']:
            for result in result_state['tool_results']:
                print(f"\n  Result:")
                print(f"    Success: {result.success}")
                print(f"    Tool: {result.tool_type.value}")
                if result.data:
                    print(f"    Data preview: {str(result.data)[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        logger.error(f"Vector node test failed", exc_info=True)
        return False


async def main():
    """Run all direct node tests"""
    
    print("\n" + "=" * 80)
    print("HEARTBEAT ENGINE - DIRECT DATA NODE TESTS")
    print("Testing nodes WITHOUT Qwen3 orchestration")
    print("=" * 80)
    
    results = []
    
    # Test Parquet node
    results.append(("Parquet Analyzer", await test_parquet_node()))
    
    # Test vector node
    results.append(("Vector Retriever", await test_vector_node()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n✓ All data nodes functional!")
    else:
        print("\n⚠ Some nodes need configuration (API keys, data files)")
    
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
