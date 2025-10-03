#!/usr/bin/env python3
"""
LangGraph Integration Configuration for HeartBeat Engine
SageMaker Endpoint Integration for Hockey Analytics
"""

import boto3
import json
from typing import Dict, Any, Optional
import asyncio
from dataclasses import dataclass

@dataclass
class EndpointConfig:
    """Configuration for the deployed SageMaker endpoint"""
    endpoint_name: str = "heartbeat-hockey-analytics-FINAL"
    region: str = "ca-central-1"
    max_tokens: int = 1024
    temperature: float = 0.1
    top_p: float = 0.9

class HockeyAnalyticsLLM:
    """
    LangGraph-compatible LLM wrapper for HeartBeat Engine SageMaker endpoint
    Optimized for Montreal Canadiens hockey analytics
    """
    
    def __init__(self, config: EndpointConfig):
        """
        Initialize the hockey analytics LLM
        
        Args:
            config: Endpoint configuration
        """
        self.config = config
        self.runtime = boto3.client('sagemaker-runtime', region_name=config.region)
        self.endpoint_ready = False
        
    async def check_endpoint_status(self) -> bool:
        """
        Check if the SageMaker endpoint is ready for inference
        
        Returns:
            bool: True if endpoint is InService
        """
        try:
            sagemaker = boto3.client('sagemaker', region_name=self.config.region)
            response = sagemaker.describe_endpoint(EndpointName=self.config.endpoint_name)
            status = response['EndpointStatus']
            
            self.endpoint_ready = (status == 'InService')
            return self.endpoint_ready
            
        except Exception as e:
            print(f"Error checking endpoint status: {e}")
            return False
    
    async def generate_hockey_response(self, 
                                     query: str,
                                     context: Optional[str] = None,
                                     user_role: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate hockey analytics response using the deployed model
        
        Args:
            query: Hockey analytics query
            context: Additional context from RAG or tools
            user_role: User role for identity-aware processing
            
        Returns:
            dict: Generated response with metadata
        """
        if not self.endpoint_ready:
            if not await self.check_endpoint_status():
                raise Exception(f"Endpoint {self.config.endpoint_name} is not ready")
        
        # Format hockey-specific prompt
        formatted_query = self._format_hockey_query(query, context, user_role)
        
        payload = {
            "inputs": formatted_query,
            "parameters": {
                "max_new_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "do_sample": True,
                "return_full_text": False,
                "repetition_penalty": 1.1,
                "length_penalty": 1.0
            }
        }
        
        try:
            response = self.runtime.invoke_endpoint(
                EndpointName=self.config.endpoint_name,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            
            result = json.loads(response['Body'].read().decode())
            
            # Extract and clean the generated text
            generated_text = result.get('generated_text', '')
            cleaned_response = self._post_process_response(generated_text)
            
            return {
                'response': cleaned_response,
                'metadata': {
                    'model': 'deepseek-r1-hockey-analytics',
                    'endpoint': self.config.endpoint_name,
                    'generation_time': result.get('generation_time', 0),
                    'input_length': result.get('input_length', 0),
                    'output_length': result.get('output_length', 0),
                    'hockey_context': True
                }
            }
            
        except Exception as e:
            raise Exception(f"Error generating hockey response: {str(e)}")
    
    def _format_hockey_query(self, 
                           query: str, 
                           context: Optional[str] = None,
                           user_role: Optional[str] = None) -> str:
        """
        Format query with hockey analytics context
        
        Args:
            query: User query
            context: RAG context or tool results
            user_role: User role (coach, analyst, player, scout)
            
        Returns:
            str: Formatted prompt for the model
        """
        role_context = ""
        if user_role:
            role_contexts = {
                'coach': 'Provide strategic insights suitable for coaching decisions.',
                'analyst': 'Focus on detailed statistical analysis and trends.',
                'player': 'Emphasize actionable individual performance insights.',
                'scout': 'Highlight player evaluation and comparison metrics.'
            }
            role_context = role_contexts.get(user_role.lower(), '')
        
        context_section = f"\n\nRelevant Context:\n{context}" if context else ""
        role_section = f"\n\nUser Role Guidance: {role_context}" if role_context else ""
        
        return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are HabsAI, the Montreal Canadiens' advanced hockey analytics assistant. You provide expert analysis of hockey data, statistics, and strategic insights specifically focused on the Montreal Canadiens.

Key Instructions:
- Focus on Montreal Canadiens data and analysis
- Provide clear, actionable insights for coaches, players, and analysts
- Use hockey terminology accurately and professionally
- Support responses with specific data when available
- Consider game context (score, period, opponent, situation)
- Highlight both strengths and areas for improvement
- Be concise but thorough in explanations{role_section}<|eot_id|><|start_header_id|>user<|end_header_id|>

{query}{context_section}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
    
    def _post_process_response(self, response: str) -> str:
        """
        Clean and format the model response
        
        Args:
            response: Raw model response
            
        Returns:
            str: Cleaned response
        """
        # Remove any special tokens
        cleaned = response.replace('<|eot_id|>', '').replace('<|end_of_text|>', '')
        cleaned = cleaned.replace('<|start_header_id|>', '').replace('<|end_header_id|>', '')
        
        # Clean whitespace
        cleaned = cleaned.strip()
        
        # Ensure minimum response quality
        if len(cleaned) < 10:
            cleaned = "I apologize, but I couldn't generate a complete response to your hockey analytics query. Please try rephrasing your question."
        
        return cleaned

# LangGraph Node Functions
async def hockey_llm_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for hockey analytics LLM processing
    
    Args:
        state: LangGraph state containing query and context
        
    Returns:
        dict: Updated state with LLM response
    """
    config = EndpointConfig()
    llm = HockeyAnalyticsLLM(config)
    
    query = state.get('query', '')
    context = state.get('context', '')
    user_role = state.get('user_role', 'analyst')
    
    try:
        result = await llm.generate_hockey_response(query, context, user_role)
        
        state.update({
            'llm_response': result['response'],
            'generation_metadata': result['metadata'],
            'processing_status': 'success'
        })
        
    except Exception as e:
        state.update({
            'llm_response': f"Error generating response: {str(e)}",
            'processing_status': 'error',
            'error': str(e)
        })
    
    return state

# Integration Test Function
async def test_langgraph_integration():
    """Test the LangGraph integration"""
    print("🏒 Testing LangGraph Integration for HeartBeat Engine")
    print("=" * 55)
    
    # Mock LangGraph state
    test_state = {
        'query': 'How did Nick Suzuki perform in the last game against Toronto?',
        'context': 'Nick Suzuki had 2 assists and 4 shots on goal in a 3-2 victory.',
        'user_role': 'coach'
    }
    
    # Test the node
    result_state = await hockey_llm_node(test_state)
    
    print(f"Query: {test_state['query']}")
    print(f"Context: {test_state['context']}")
    print(f"User Role: {test_state['user_role']}")
    print()
    print(f"Status: {result_state['processing_status']}")
    
    if result_state['processing_status'] == 'success':
        print(f"Response: {result_state['llm_response']}")
        print(f"Generation Time: {result_state['generation_metadata'].get('generation_time', 0)}s")
        print("\n✅ LangGraph integration ready!")
    else:
        print(f"Error: {result_state.get('error', 'Unknown error')}")
        print("\n⚠️ Integration needs attention")

if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_langgraph_integration())
