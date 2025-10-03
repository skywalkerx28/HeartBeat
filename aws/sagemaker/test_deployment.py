#!/usr/bin/env python3
"""
Quick Test Script for HeartBeat Engine SageMaker Endpoint
Run this once your endpoint is InService to validate deployment
"""

import boto3
import json
import time

def test_hockey_endpoint():
    """Test the deployed hockey analytics endpoint"""
    
    # Your endpoint details (FINAL endpoint with fine-tuned model)
    ENDPOINT_NAME = "heartbeat-hockey-analytics-FINAL"
    REGION = "ca-central-1"
    
    # Initialize SageMaker runtime
    runtime = boto3.client('sagemaker-runtime', region_name=REGION)
    
    print("Testing HeartBeat Engine Hockey Analytics Endpoint")
    print("=" * 55)
    print(f"Endpoint: {ENDPOINT_NAME}")
    print(f"Region: {REGION}")
    print()
    
    # Test queries for hockey analytics
    test_queries = [
        {
            "name": "Basic Hockey Query",
            "query": "How did Nick Suzuki perform in the last game?",
            "expected_time": 3.0
        },
        {
            "name": "Team Statistics",
            "query": "What is Montreal's power play efficiency this season?",
            "expected_time": 3.0
        },
        {
            "name": "Advanced Analytics",
            "query": "Analyze Caufield's expected goals in the offensive zone.",
            "expected_time": 3.0
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_queries, 1):
        print(f"Test {i}/3: {test['name']}")
        
        payload = {
            "inputs": test["query"],
            "parameters": {
                "max_length": 2048,
                "temperature": 0.1,
                "top_p": 0.9,
                "do_sample": True,
                "return_full_text": False
            }
        }
        
        start_time = time.time()
        
        try:
            response = runtime.invoke_endpoint(
                EndpointName=ENDPOINT_NAME,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            
            end_time = time.time()
            response_time = round(end_time - start_time, 3)
            
            result = json.loads(response['Body'].read().decode())
            
            # Check if response contains hockey-related content
            response_text = result.get('generated_text', '').lower()
            hockey_keywords = ['hockey', 'montreal', 'canadiens', 'habs', 'suzuki', 'caufield', 'goal', 'assist', 'shot']
            hockey_relevance = any(keyword in response_text for keyword in hockey_keywords)
            
            success = response_time <= test['expected_time'] and len(response_text) > 10
            
            print(f"  ⏱️  Response Time: {response_time}s {'✅' if response_time <= test['expected_time'] else '⚠️'}")
            print(f"  🏒 Hockey Relevance: {'✅' if hockey_relevance else '⚠️'}")
            print(f"  📝 Response Length: {len(response_text)} chars")
            print(f"  🎯 Overall: {'✅ PASS' if success else '⚠️ REVIEW NEEDED'}")
            
            if len(response_text) > 0:
                preview = response_text[:150] + "..." if len(response_text) > 150 else response_text
                print(f"  💬 Preview: {preview}")
            
            results.append({
                'test': test['name'],
                'success': success,
                'response_time': response_time,
                'hockey_relevance': hockey_relevance,
                'response_length': len(response_text)
            })
            
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append({
                'test': test['name'],
                'success': False,
                'error': str(e)
            })
        
        print()
    
    # Summary
    successful_tests = sum(1 for r in results if r.get('success', False))
    avg_response_time = sum(r.get('response_time', 0) for r in results) / len(results)
    
    print("📊 DEPLOYMENT VALIDATION SUMMARY")
    print("=" * 40)
    print(f"✅ Successful Tests: {successful_tests}/{len(test_queries)}")
    print(f"⏱️  Average Response Time: {avg_response_time:.2f}s")
    print(f"🎯 Performance Target (<3s): {'✅ MET' if avg_response_time < 3.0 else '⚠️ NEEDS OPTIMIZATION'}")
    
    if successful_tests == len(test_queries):
        print("\n🚀 ENDPOINT READY FOR LANGGRAPH INTEGRATION!")
        print("Next steps:")
        print("  1. Update your LangGraph orchestrator with endpoint details")
        print("  2. Test integration with your hockey analytics tools")
        print("  3. Run comprehensive testing suite")
    else:
        print("\n🔧 DEPLOYMENT NEEDS ATTENTION")
        print("Review failed tests and adjust configuration as needed.")
    
    return results

if __name__ == "__main__":
    test_hockey_endpoint()
