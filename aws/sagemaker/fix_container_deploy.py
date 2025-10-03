#!/usr/bin/env python3
"""
Fix Container Issue - Deploy with Inference Container
"""

import boto3
import json
from datetime import datetime

def deploy_corrected_endpoint():
    print('Creating CORRECTED Model with Inference Container')
    print('=' * 55)

    sagemaker = boto3.client('sagemaker', region_name='ca-central-1')
    account_id = boto3.client('sts').get_caller_identity()['Account']

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    corrected_model_name = f'heartbeat-corrected-{timestamp}'
    config_name = f'heartbeat-corrected-config-{timestamp}'
    endpoint_name = f'heartbeat-corrected-{timestamp}'

    print('🎯 THE FIX: Change from TRAINING container to INFERENCE container')
    print()

    try:
        # Create corrected model with INFERENCE container
        corrected_model_config = {
            'ModelName': corrected_model_name,
            'ExecutionRoleArn': f'arn:aws:iam::{account_id}:role/HeartBeatSageMakerExecutionRole',
            'PrimaryContainer': {
                # KEY FIX: Use INFERENCE container instead of training container
                'Image': '763104351884.dkr.ecr.ca-central-1.amazonaws.com/huggingface-pytorch-inference:2.0.0-transformers4.28.1-gpu-py310-cu118-ubuntu20.04',
                
                # YOUR model artifacts (same as original)
                'ModelDataUrl': 's3://heartbeat-ml-llama33-70b-skywalkerx/llm/deepseek-r1-qwen-32b/models/heartbeat-deepseek-r1-qwen-32b-2025-09-23-10-03-58/heartbeat-deepseek-r1-qwen-32b-2025-09-23-10-03-58/output/model.tar.gz',
                
                # Simplified environment (let HF handle loading)
                'Environment': {
                    'HF_TASK': 'text-generation',
                    'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
                    'MAX_SEQUENCE_LENGTH': '4096', 
                    'TEMPERATURE': '0.1',
                    'TOP_P': '0.9',
                    'SAGEMAKER_MODEL_SERVER_TIMEOUT': '600'
                }
            }
        }

        print('📦 Creating corrected model...')
        sagemaker.create_model(**corrected_model_config)
        print(f'✅ Corrected model created: {corrected_model_name}')

        # Create endpoint config
        print('⚙️  Creating endpoint config...')
        config = {
            'EndpointConfigName': config_name,
            'ProductionVariants': [{
                'VariantName': 'primary',
                'ModelName': corrected_model_name,
                'InstanceType': 'ml.g4dn.xlarge',
                'InitialInstanceCount': 1,
                'InitialVariantWeight': 1.0,
                'ModelDataDownloadTimeoutInSeconds': 1200,
                'ContainerStartupHealthCheckTimeoutInSeconds': 900
            }]
        }

        sagemaker.create_endpoint_config(**config)
        print(f'✅ Config created: {config_name}')

        # Create endpoint
        print('🚀 Creating endpoint...')
        sagemaker.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=config_name
        )

        print(f'✅ Endpoint creation started: {endpoint_name}')
        print()
        print('🎯 This corrected endpoint:')
        print('   ✅ Uses YOUR fine-tuned model artifacts')
        print('   ✅ Uses INFERENCE container (has serve command)')
        print('   ✅ Uses HuggingFace built-in inference')
        print('   ✅ Should actually work!')
        print()

        # Save final endpoint info
        final_info = {
            'endpoint_name': endpoint_name,
            'model_name': corrected_model_name,
            'original_finetuned_model': 'heartbeat-deepseek-r1-hockeyV1-2025-09-23',
            'fix_applied': 'inference_container',
            'container_type': 'inference_not_training',
            'timestamp': timestamp,
            'uses_your_training': True
        }

        with open('/Users/xavier.bouchard/Desktop/HeartBeat/final_endpoint.json', 'w') as f:
            json.dump(final_info, f, indent=2)

        print(f'💾 Final endpoint info: final_endpoint.json')
        print('⏳ Deployment: 10-15 minutes')
        print('🏒 This WILL use your expensive training investment!')
        
        return endpoint_name

    except Exception as e:
        print(f'❌ Error: {e}')
        return None

if __name__ == "__main__":
    endpoint_name = deploy_corrected_endpoint()
    if endpoint_name:
        print(f"\n🎉 SUCCESS! Monitor deployment at: {endpoint_name}")
    else:
        print("\n❌ Deployment failed")
