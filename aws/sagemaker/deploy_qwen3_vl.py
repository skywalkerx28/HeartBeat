#!/usr/bin/env python3
"""
Deploy Qwen3-VL-235B-A22B-Thinking Model to AWS SageMaker
Handles multimodal vision-language model deployment with optimized configuration
"""

import boto3
import json
import time
from datetime import datetime
from sagemaker import get_execution_role
from sagemaker.pytorch import PyTorchModel
from sagemaker.huggingface import HuggingFaceModel
import sagemaker

# Configuration
REGION = 'us-east-1'  # HuggingFace containers available here
MODEL_NAME = 'Qwen/Qwen3-VL-235B-A22B-Thinking'
TIMESTAMP = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

# Deployment configuration
CONFIG = {
    'model_name': f'heartbeat-qwen3-vl-hockey-{TIMESTAMP}',
    'endpoint_config_name': f'heartbeat-qwen3vl-config-{TIMESTAMP}',
    'endpoint_name': f'heartbeat-qwen3vl-analytics-{TIMESTAMP}',
    'instance_type': 'ml.g5.12xlarge',  # Required for 235B model
    'instance_count': 1,
    'volume_size': 200,  # GB - increased for large model
    'max_payload': 50,   # MB - increased for multimodal inputs
    'max_concurrent_transforms': 5
}

def create_sagemaker_model():
    """
    Create SageMaker model with Qwen3-VL configuration
    """
    print(f"Creating SageMaker model: {CONFIG['model_name']}")
    
    # Get execution role
    try:
        role = get_execution_role()
        print(f"Using execution role: {role}")
    except Exception as e:
        # Fallback to HeartBeat specific role
        role = "arn:aws:iam::803243354066:role/HeartBeatSageMakerExecutionRole"
        print(f"Could not get execution role automatically: {e}")
        print(f"Using HeartBeat execution role: {role}")
    
    # Environment variables for optimization
    env_vars = {
        'HABS_MODEL_TYPE': 'qwen3-vl-hockey-analytics',
        'HF_MODEL_ID': MODEL_NAME,  # Required for HuggingFace model loading
        'SM_NUM_GPUS': '4',  # ml.g5.12xlarge has 4 GPUs
        'MAX_SEQUENCE_LENGTH': '8192',  # Reduced from max for efficiency
        'TEMPERATURE': '0.1',
        'TOP_P': '0.9',
        'THINKING_MODE': 'true',
        'MULTIMODAL_SUPPORT': 'true',
        'HOCKEY_CONTEXT': 'true',
        # Memory optimization
        'TORCH_DTYPE': 'bfloat16',
        'USE_FLASH_ATTENTION': 'true',
        'LOW_CPU_MEM_USAGE': 'true',
        # MoE optimization
        'MOE_OPTIMIZATION': 'true',
        'EXPERTS_ACTIVE': '8',
        'EXPERTS_TOTAL': '128',
        # Additional optimization for large model
        'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
        'HF_HOME': '/tmp/huggingface_cache',
        'CUSTOM_IMAGE_URI': "{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/heartbeat-qwen3-vl-inference:latest"
    }
    
    try:
        # Set up SageMaker session with explicit region
        boto_session = boto3.session.Session(region_name=REGION)
        session = sagemaker.Session(boto_session=boto_session)
        
        # Create model referencing custom inference image
        custom_image_uri = env_vars.get('CUSTOM_IMAGE_URI') or "{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/heartbeat-qwen3-vl-inference:latest"
        model = HuggingFaceModel(
            model_data=None,  # Will load from HuggingFace Hub
            role=role,
            entry_point='qwen3_vl_inference.py',
            source_dir='.',
            env=env_vars,
            image_uri=custom_image_uri,
            name=CONFIG['model_name'],
            dependencies=['requirements.txt'],
            sagemaker_session=session
        )
        
        print(f"Model object created successfully")
        return model
        
    except Exception as e:
        print(f"Error creating model: {e}")
        return None

def deploy_model(model):
    """
    Deploy the model to an endpoint with explicit region
    """
    print(f"Deploying model to endpoint: {CONFIG['endpoint_name']}")
    print(f"Region: {REGION}")
    
    try:
        predictor = model.deploy(
            initial_instance_count=CONFIG['instance_count'],
            instance_type=CONFIG['instance_type'],
            endpoint_name=CONFIG['endpoint_name'],
            # volume_size not supported for ml.g5.12xlarge
            model_data_download_timeout=1800,  # 30 minutes for large model
            container_startup_health_check_timeout=1800,  # 30 minutes
            data_capture_config=None,  # Can enable for monitoring
            wait=True  # Wait for deployment to complete
        )
        
        print(f"Model deployed successfully!")
        print(f"Endpoint name: {CONFIG['endpoint_name']}")
        print(f"Instance type: {CONFIG['instance_type']}")
        # Volume size not applicable for this instance type
        
        return predictor
        
    except Exception as e:
        print(f"Deployment failed: {e}")
        return None

def test_endpoint(predictor=None):
    """
    Test the deployed endpoint with sample queries
    """
    print("🧪 Testing endpoint with sample queries...")
    
    if not predictor:
        # Create runtime client for testing
        runtime = boto3.client('sagemaker-runtime', region_name=REGION)
        endpoint_name = CONFIG['endpoint_name']
    else:
        runtime = None
        endpoint_name = predictor.endpoint_name
    
    # Test cases
    test_cases = [
        {
            'name': 'Basic Hockey Query',
            'payload': {
                'text': 'Analyze Montreal Canadiens power play efficiency',
                'thinking_mode': True,
                'hockey_context': True
            }
        },
        {
            'name': 'Advanced Analytics Query',
            'payload': {
                'text': 'What are the key factors affecting zone entry success for young defensemen?',
                'temperature': 0.2,
                'max_new_tokens': 1024
            }
        },
        {
            'name': 'Performance Comparison Query',
            'payload': {
                'text': 'Compare the impact of different line combinations on xG differential',
                'thinking_mode': True,
                'hockey_context': True
            }
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        
        try:
            start_time = time.time()
            
            if runtime:
                response = runtime.invoke_endpoint(
                    EndpointName=endpoint_name,
                    ContentType='application/json',
                    Body=json.dumps(test_case['payload'])
                )
                result = json.loads(response['Body'].read().decode())
            else:
                result = predictor.predict(test_case['payload'])
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"⏱️  Response time: {response_time:.2f}s")
            print(f"📝 Response preview: {result.get('response', 'No response')[:200]}...")
            
            if result.get('thinking'):
                print(f"🤔 Thinking mode: Enabled ({len(result['thinking'])} chars)")
            
            results.append({
                'test': test_case['name'],
                'success': True,
                'response_time': response_time,
                'response_length': len(result.get('response', '')),
                'has_thinking': bool(result.get('thinking'))
            })
            
        except Exception as e:
            print(f"Test failed: {e}")
            results.append({
                'test': test_case['name'],
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\nTest Summary:")
    successful_tests = [r for r in results if r['success']]
    print(f"Successful tests: {len(successful_tests)}/{len(results)}")
    
    if successful_tests:
        avg_response_time = sum(r['response_time'] for r in successful_tests) / len(successful_tests)
        print(f"Average response time: {avg_response_time:.2f}s")
    
    return results

def cleanup_resources():
    """
    Cleanup function to delete endpoints if needed
    """
    print("🧹 Cleanup function available if needed:")
    print(f"aws sagemaker delete-endpoint --endpoint-name {CONFIG['endpoint_name']}")
    print(f"aws sagemaker delete-endpoint-config --endpoint-config-name {CONFIG['endpoint_config_name']}")
    print(f"aws sagemaker delete-model --model-name {CONFIG['model_name']}")

def main():
    """
    Main deployment workflow
    """
    print("HeartBeat Engine - Qwen3-VL Model Deployment")
    print("=" * 60)
    print(f"Model: {MODEL_NAME}")
    print(f"Target endpoint: {CONFIG['endpoint_name']}")
    print(f"Instance type: {CONFIG['instance_type']}")
    print("=" * 60)
    
    # Step 1: Create model
    model = create_sagemaker_model()
    if not model:
        print("Model creation failed. Exiting.")
        return
    
    # Step 2: Deploy model
    predictor = deploy_model(model)
    if not predictor:
        print("Model deployment failed. Exiting.")
        return
    
    # Step 3: Test endpoint
    print("\n⏳ Waiting for endpoint to be in service...")
    time.sleep(60)  # Wait a bit before testing
    
    test_results = test_endpoint(predictor)
    
    # Step 4: Deployment summary
    print("\nDeployment Complete!")
    print("=" * 60)
    print(f"Model: {CONFIG['model_name']}")
    print(f"Endpoint: {CONFIG['endpoint_name']}")
    print(f"Region: {REGION}")
    print(f"Instance: {CONFIG['instance_type']}")
    print(f"Multimodal support: Enabled")
    print(f"Thinking mode: Enabled")
    print(f"Hockey context: Optimized for Montreal Canadiens")
    
    print(f"\nIntegration Details:")
    print(f"Endpoint URL: https://runtime.sagemaker.{REGION}.amazonaws.com/endpoints/{CONFIG['endpoint_name']}/invocations")
    print(f"Model parameters: 235B total, ~22B active per token")
    print(f"Context window: 256K tokens (8K optimized for efficiency)")
    
    print(f"\nNext Steps:")
    print(f"1. Update your LangGraph orchestrator with the new endpoint")
    print(f"2. Test multimodal capabilities with hockey images/videos")
    print(f"3. Fine-tune prompts for optimal hockey analytics")
    
    cleanup_resources()

if __name__ == "__main__":
    main()
