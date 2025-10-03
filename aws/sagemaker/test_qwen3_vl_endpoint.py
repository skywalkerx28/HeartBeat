#!/usr/bin/env python3
"""
Test Qwen3-VL Hockey Analytics Endpoint
Comprehensive testing including multimodal capabilities and hockey-specific scenarios
"""

import boto3
import json
import time
import base64
from PIL import Image, ImageDraw
import io
import requests
from datetime import datetime

# Configuration
REGION = 'us-east-1'
ENDPOINT_NAME = None  # Will be set based on latest deployment

def get_latest_endpoint():
    """
    Get the latest Qwen3-VL endpoint
    """
    sagemaker = boto3.client('sagemaker', region_name=REGION)
    
    try:
        response = sagemaker.list_endpoints(
            SortBy='CreationTime',
            SortOrder='Descending',
            NameContains='heartbeat-qwen3vl'
        )
        
        for endpoint in response['Endpoints']:
            if endpoint['EndpointStatus'] == 'InService':
                print(f"✅ Found active endpoint: {endpoint['EndpointName']}")
                return endpoint['EndpointName']
        
        print("❌ No active Qwen3-VL endpoints found")
        return None
        
    except Exception as e:
        print(f"❌ Error listing endpoints: {e}")
        return None

def create_test_rink_image():
    """
    Create a simple hockey rink diagram for testing
    """
    # Create a simple rink representation
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw rink outline
    draw.rectangle([20, 20, 380, 180], outline='black', width=3)
    
    # Draw center line
    draw.line([200, 20, 200, 180], fill='red', width=2)
    
    # Draw face-off circles
    draw.ellipse([80, 70, 120, 110], outline='blue', width=2)
    draw.ellipse([280, 70, 320, 110], outline='blue', width=2)
    
    # Draw goals
    draw.rectangle([20, 90, 30, 110], outline='red', width=3)
    draw.rectangle([370, 90, 380, 110], outline='red', width=3)
    
    # Add some sample shot locations
    shots = [(60, 100), (150, 80), (250, 120), (340, 95)]
    for x, y in shots:
        draw.ellipse([x-3, y-3, x+3, y+3], fill='red')
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"

def invoke_endpoint(endpoint_name, payload):
    """
    Invoke the SageMaker endpoint
    """
    runtime = boto3.client('sagemaker-runtime', region_name=REGION)
    
    try:
        response = runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        result = json.loads(response['Body'].read().decode())
        return result
        
    except Exception as e:
        print(f"❌ Endpoint invocation failed: {e}")
        return {'error': str(e)}

def run_text_tests(endpoint_name):
    """
    Run comprehensive text-only tests
    """
    print("\n📝 Running Text-Only Tests")
    print("=" * 50)
    
    test_cases = [
        {
            'name': 'Basic Hockey Query',
            'payload': {
                'text': 'Explain the concept of expected goals (xG) in hockey analytics.',
                'thinking_mode': True,
                'temperature': 0.1
            },
            'expected_keywords': ['expected goals', 'xG', 'probability', 'shot quality']
        },
        {
            'name': 'Montreal Canadiens Specific',
            'payload': {
                'text': 'What are the key strategic considerations for the Montreal Canadiens power play?',
                'thinking_mode': True,
                'hockey_context': True
            },
            'expected_keywords': ['power play', 'Montreal', 'Canadiens', 'strategy']
        },
        {
            'name': 'Advanced Analytics',
            'payload': {
                'text': 'How do Corsi and Fenwick metrics help evaluate player performance?',
                'thinking_mode': False,
                'max_new_tokens': 800
            },
            'expected_keywords': ['Corsi', 'Fenwick', 'shot attempts', 'possession']
        },
        {
            'name': 'Zone Analysis',
            'payload': {
                'text': 'Analyze the importance of zone entry success rates for defensemen.',
                'thinking_mode': True,
                'temperature': 0.2
            },
            'expected_keywords': ['zone entry', 'defensemen', 'possession', 'transition']
        },
        {
            'name': 'Performance Comparison',
            'payload': {
                'text': 'What metrics would you use to compare the effectiveness of different line combinations?',
                'thinking_mode': True,
                'hockey_context': True
            },
            'expected_keywords': ['line combinations', 'metrics', 'effectiveness', 'chemistry']
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        
        start_time = time.time()
        result = invoke_endpoint(endpoint_name, test_case['payload'])
        end_time = time.time()
        
        response_time = end_time - start_time
        
        if 'error' in result:
            print(f"❌ Failed: {result['error']}")
            results.append({'test': test_case['name'], 'success': False, 'error': result['error']})
            continue
        
        response_text = result.get('response', '')
        thinking_text = result.get('thinking', '')
        
        print(f"⏱️  Response time: {response_time:.2f}s")
        print(f"📝 Response length: {len(response_text)} chars")
        
        if thinking_text:
            print(f"🤔 Thinking length: {len(thinking_text)} chars")
        
        # Check for expected keywords
        found_keywords = []
        for keyword in test_case['expected_keywords']:
            if keyword.lower() in response_text.lower():
                found_keywords.append(keyword)
        
        keyword_score = len(found_keywords) / len(test_case['expected_keywords'])
        print(f"🎯 Keyword relevance: {keyword_score:.1%} ({len(found_keywords)}/{len(test_case['expected_keywords'])})")
        
        # Show response preview
        print(f"📋 Preview: {response_text[:150]}...")
        
        results.append({
            'test': test_case['name'],
            'success': True,
            'response_time': response_time,
            'response_length': len(response_text),
            'thinking_length': len(thinking_text),
            'keyword_relevance': keyword_score,
            'has_thinking': bool(thinking_text)
        })
    
    return results

def run_multimodal_tests(endpoint_name):
    """
    Run multimodal tests with images
    """
    print("\n🖼️  Running Multimodal Tests")
    print("=" * 50)
    
    # Create test rink image
    rink_image = create_test_rink_image()
    
    test_cases = [
        {
            'name': 'Rink Diagram Analysis',
            'payload': {
                'text': 'Analyze this hockey rink diagram. What do the red dots represent and what can you tell me about their distribution?',
                'image': rink_image,
                'thinking_mode': True,
                'hockey_context': True
            }
        },
        {
            'name': 'Strategic Analysis',
            'payload': {
                'text': 'Based on this rink layout, what strategic insights can you provide about shot selection and scoring opportunities?',
                'image': rink_image,
                'thinking_mode': True,
                'temperature': 0.1
            }
        },
        {
            'name': 'Visual Pattern Recognition',
            'payload': {
                'text': 'Describe the visual elements in this hockey diagram and their significance in game analysis.',
                'image': rink_image,
                'thinking_mode': False,
                'max_new_tokens': 1000
            }
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        
        start_time = time.time()
        result = invoke_endpoint(endpoint_name, test_case['payload'])
        end_time = time.time()
        
        response_time = end_time - start_time
        
        if 'error' in result:
            print(f"❌ Failed: {result['error']}")
            results.append({'test': test_case['name'], 'success': False, 'error': result['error']})
            continue
        
        response_text = result.get('response', '')
        thinking_text = result.get('thinking', '')
        is_multimodal = result.get('multimodal', False)
        
        print(f"⏱️  Response time: {response_time:.2f}s")
        print(f"📝 Response length: {len(response_text)} chars")
        print(f"🖼️  Multimodal processing: {'Yes' if is_multimodal else 'No'}")
        
        if thinking_text:
            print(f"🤔 Thinking length: {len(thinking_text)} chars")
        
        # Show response preview
        print(f"📋 Preview: {response_text[:150]}...")
        
        results.append({
            'test': test_case['name'],
            'success': True,
            'response_time': response_time,
            'response_length': len(response_text),
            'thinking_length': len(thinking_text),
            'multimodal': is_multimodal,
            'has_thinking': bool(thinking_text)
        })
    
    return results

def run_performance_tests(endpoint_name):
    """
    Run performance and stress tests
    """
    print("\n⚡ Running Performance Tests")
    print("=" * 50)
    
    # Concurrent requests test
    print("🔄 Testing concurrent requests...")
    
    concurrent_payload = {
        'text': 'What factors contribute to successful penalty killing in hockey?',
        'thinking_mode': False,
        'max_new_tokens': 500
    }
    
    concurrent_results = []
    num_concurrent = 3
    
    import threading
    
    def make_request(request_id):
        start = time.time()
        result = invoke_endpoint(endpoint_name, concurrent_payload)
        end = time.time()
        concurrent_results.append({
            'id': request_id,
            'time': end - start,
            'success': 'error' not in result,
            'length': len(result.get('response', '')) if 'error' not in result else 0
        })
    
    # Launch concurrent threads
    threads = []
    start_time = time.time()
    
    for i in range(num_concurrent):
        thread = threading.Thread(target=make_request, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    
    successful_requests = [r for r in concurrent_results if r['success']]
    
    print(f"✅ Concurrent requests: {len(successful_requests)}/{num_concurrent} successful")
    print(f"⏱️  Total time: {total_time:.2f}s")
    
    if successful_requests:
        avg_response_time = sum(r['time'] for r in successful_requests) / len(successful_requests)
        print(f"📊 Average response time: {avg_response_time:.2f}s")
        print(f"🚀 Throughput: {len(successful_requests) / total_time:.2f} req/s")
    
    return {
        'concurrent_success_rate': len(successful_requests) / num_concurrent,
        'average_response_time': avg_response_time if successful_requests else 0,
        'throughput': len(successful_requests) / total_time if total_time > 0 else 0
    }

def generate_test_report(text_results, multimodal_results, performance_results):
    """
    Generate comprehensive test report
    """
    print("\nTest Report Summary")
    print("=" * 60)
    
    # Text tests summary
    text_successful = [r for r in text_results if r['success']]
    if text_successful:
        avg_text_time = sum(r['response_time'] for r in text_successful) / len(text_successful)
        avg_keyword_relevance = sum(r['keyword_relevance'] for r in text_successful) / len(text_successful)
        thinking_enabled = sum(1 for r in text_successful if r['has_thinking']) / len(text_successful)
    else:
        avg_text_time = 0.0
        avg_keyword_relevance = 0.0
        thinking_enabled = 0.0
    print(f"📝 Text Tests: {len(text_successful)}/{len(text_results)} successful")
    if text_successful:
        print(f"   Average response time: {avg_text_time:.2f}s")
        print(f"   Average keyword relevance: {avg_keyword_relevance:.1%}")
        print(f"   Thinking mode usage: {thinking_enabled:.1%}")
    else:
        print(f"   Average response time: n/a")
        print(f"   Average keyword relevance: n/a")
        print(f"   Thinking mode usage: n/a")
 
    # Multimodal tests summary
    multimodal_successful = [r for r in multimodal_results if r['success']]
    if multimodal_successful:
        avg_multimodal_time = sum(r['response_time'] for r in multimodal_successful) / len(multimodal_successful)
        multimodal_processing = sum(1 for r in multimodal_successful if r['multimodal']) / len(multimodal_successful)
    else:
        avg_multimodal_time = 0.0
        multimodal_processing = 0.0
    print(f"🖼️  Multimodal Tests: {len(multimodal_successful)}/{len(multimodal_results)} successful")
    if multimodal_successful:
        print(f"   Average response time: {avg_multimodal_time:.2f}s")
        print(f"   Multimodal processing rate: {multimodal_processing:.1%}")
    else:
        print(f"   Average response time: n/a")
        print(f"   Multimodal processing rate: n/a")
 
    # Performance summary
    if performance_results:
        print(f"⚡ Performance Tests:")
        print(f"   Concurrent success rate: {performance_results['concurrent_success_rate']:.1%}")
        print(f"   Average response time: {performance_results['average_response_time']:.2f}s")
        print(f"   Throughput: {performance_results['throughput']:.2f} req/s")
    else:
        print(f"⚡ Performance Tests:")
        print(f"   Concurrent success rate: n/a")
        print(f"   Average response time: n/a")
        print(f"   Throughput: n/a")
 
    # Overall assessment
    total_tests = len(text_results) + len(multimodal_results)
    total_successful = len(text_successful) + len(multimodal_successful)
 
    overall_rate = (total_successful / total_tests) if total_tests else 0
    print(f"\n🎯 Overall Success Rate: {total_successful}/{total_tests} ({overall_rate:.1%})")
 
    # Recommendations
    print(f"\n💡 Recommendations:")
 
    if text_successful and avg_text_time > 5:
        print(f"   ⚠️  Text response time high ({avg_text_time:.1f}s) - consider optimizing prompts")
    elif text_successful:
        print(f"   ✅ Text response time acceptable ({avg_text_time:.1f}s)")
    else:
        print(f"   ⚠️  No successful text responses - check endpoint logs")
 
    if len(multimodal_successful) > 0:
        print(f"   ✅ Multimodal capabilities working")
    else:
        print(f"   ⚠️  Multimodal capabilities need attention")
 
    if text_successful and avg_keyword_relevance > 0.7:
        print(f"   ✅ Hockey domain knowledge strong ({avg_keyword_relevance:.1%})")
    elif text_successful:
        print(f"   ⚠️  Consider improving hockey domain prompts")
    else:
        print(f"   ⚠️  Consider improving hockey domain prompts")

def main():
    """
    Main testing workflow
    """
    print("🏒 HeartBeat Engine - Qwen3-VL Endpoint Testing")
    print("=" * 60)
    
    # Find active endpoint
    global ENDPOINT_NAME
    ENDPOINT_NAME = get_latest_endpoint()
    
    if not ENDPOINT_NAME:
        print("❌ No active endpoint found. Please deploy the model first.")
        return
    
    print(f"🎯 Testing endpoint: {ENDPOINT_NAME}")
    print(f"📅 Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all test suites
    text_results = run_text_tests(ENDPOINT_NAME)
    multimodal_results = run_multimodal_tests(ENDPOINT_NAME)
    performance_results = run_performance_tests(ENDPOINT_NAME)
    
    # Generate report
    generate_test_report(text_results, multimodal_results, performance_results)
    
    print(f"\n🎉 Testing Complete!")
    print(f"📍 Endpoint ready for LangGraph integration: {ENDPOINT_NAME}")

if __name__ == "__main__":
    main()
