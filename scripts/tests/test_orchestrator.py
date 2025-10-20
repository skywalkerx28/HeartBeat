#!/usr/bin/env python3
"""
HeartBeat Engine - Orchestrator Test Script
Montreal Canadiens Advanced Analytics Assistant

Test script to validate the LangGraph orchestrator implementation.
"""

import asyncio
import logging
from orchestrator import orchestrator, UserContext, UserRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_orchestrator():
    """Test the HeartBeat orchestrator with sample queries"""
    
    print("=== HeartBeat Engine - Orchestrator Test ===\n")
    
    # Create test user context
    test_user = UserContext(
        user_id="test_coach_001",
        role=UserRole.COACH,
        name="Test Coach",
        team_access=["MTL"],
        session_id="test_session_001"
    )
    
    # Test queries for different scenarios
    test_queries = [
        {
            "query": "How is Suzuki performing this season?",
            "description": "Player analysis query"
        },
        {
            "query": "What are our powerplay statistics compared to league average?",
            "description": "Team performance query"
        },
        {
            "query": "Analyze our last game against Toronto",
            "description": "Game analysis query"
        },
        {
            "query": "Compare Caufield's shooting percentage to other wingers",
            "description": "Matchup comparison query"
        }
    ]
    
    # Process each test query
    for i, test_case in enumerate(test_queries, 1):
        print(f"--- Test {i}: {test_case['description']} ---")
        print(f"Query: {test_case['query']}")
        
        try:
            # Process the query
            result = await orchestrator.process_query(
                query=test_case["query"],
                user_context=test_user
            )
            
            # Display results
            print(f"Success: {result.get('success', True)}")
            print(f"Query Type: {result.get('query_type', 'unknown')}")
            print(f"Processing Time: {result.get('processing_time_ms', 0)}ms")
            print(f"Tools Used: {len(result.get('tool_results', []))}")
            
            if result.get('errors'):
                print(f"Errors: {result['errors']}")
            
            print(f"Response: {result.get('response', 'No response')[:200]}...")
            
        except Exception as e:
            print(f"Error: {str(e)}")
        
        print()
    
    print("=== Test Complete ===")

def test_configuration():
    """Test configuration validation"""
    
    print("=== Configuration Test ===")
    
    from orchestrator.config.settings import settings
    
    # Test configuration validation
    is_valid = settings.validate_config()
    print(f"Configuration valid: {is_valid}")
    
    # Test role permissions
    coach_permissions = settings.get_user_permissions(UserRole.COACH)
    print(f"Coach permissions: {coach_permissions}")
    
    player_permissions = settings.get_user_permissions(UserRole.PLAYER)
    print(f"Player permissions: {player_permissions}")
    
    print()

def test_state_management():
    """Test state management functions"""
    
    print("=== State Management Test ===")
    
    from orchestrator.utils.state import create_initial_state, QueryType
    
    # Create test user context
    test_user = UserContext(
        user_id="test_001",
        role=UserRole.ANALYST,
        name="Test Analyst"
    )
    
    # Create initial state
    initial_state = create_initial_state(
        user_context=test_user,
        query="Test query for state management",
        query_type=QueryType.STATISTICAL_QUERY
    )
    
    print(f"Initial state created successfully")
    print(f"Query type: {initial_state['query_type']}")
    print(f"Current step: {initial_state['current_step']}")
    print(f"User role: {initial_state['user_context'].role}")
    
    print()

async def main():
    """Main test function"""
    
    print("HeartBeat Engine - LangGraph Orchestrator Tests\n")
    
    # Run configuration tests
    test_configuration()
    
    # Run state management tests
    test_state_management()
    
    # Run orchestrator tests
    await test_orchestrator()

if __name__ == "__main__":
    asyncio.run(main())
