#!/usr/bin/env python3
"""
Deploy Qwen3-VL-235B-A22B-Thinking using PyTorch container approach
More reliable than HuggingFace containers for custom models
"""

import boto3
import json
import time
import tarfile
import os
from datetime import datetime
from sagemaker.pytorch import PyTorchModel
import sagemaker

# Configuration
REGION = 'us-east-1'
MODEL_NAME = 'Qwen/Qwen3-VL-235B-A22B-Thinking'
TIMESTAMP = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

# Deployment configuration
CONFIG = {
    'model_name': f'heartbeat-qwen3-vl-pytorch-{TIMESTAMP}',
    'endpoint_config_name': f'heartbeat-qwen3vl-pytorch-config-{TIMESTAMP}',
    'endpoint_name': f'heartbeat-qwen3vl-pytorch-{TIMESTAMP}',
    'instance_type': 'ml.g5.12xlarge',  # Required for 235B model
    'instance_count': 1,
    'volume_size': 200,  # GB
    'max_payload': 50,   # MB
}

def create_model_artifacts():
    """
    Create model.tar.gz with inference code
    """
    print("📦 Creating model artifacts...")
    
    # Create model directory
    os.makedirs('/tmp/model', exist_ok=True)
    
    # Copy inference script
    import shutil
    shutil.copy('qwen3_vl_inference.py', '/tmp/model/inference.py')
    shutil.copy('requirements.txt', '/tmp/model/requirements.txt')
    
    # Create code directory structure
    code_dir = '/tmp/model/code'
    os.makedirs(code_dir, exist_ok=True)
    
    # Copy files to code directory
    shutil.copy('qwen3_vl_inference.py', f'{code_dir}/inference.py')
    shutil.copy('requirements.txt', f'{code_dir}/requirements.txt')
    
    # Create model.tar.gz
    model_path = '/tmp/model.tar.gz'
    with tarfile.open(model_path, 'w:gz') as tar:
        tar.add('/tmp/model', arcname='.')
    
    print(f"✅ Model artifacts created: {model_path}")
    return model_path

def upload_to_s3(model_path):
    """
    Upload model artifacts to S3
    """
    print("☁️  Uploading model artifacts to S3...")
    
    bucket = 'heartbeat-sagemaker-models'  # You may need to create this
    key = f'qwen3-vl/{TIMESTAMP}/model.tar.gz'
    
    s3 = boto3.client('s3', region_name=REGION)
    
    try:
        # Check if bucket exists, create if not
        try:
            s3.head_bucket(Bucket=bucket)
        except:
            print(f"Creating S3 bucket: {bucket}")
            s3.create_bucket(Bucket=bucket)
        
        # Upload model
        s3.upload_file(model_path, bucket, key)
        s3_path = f's3://{bucket}/{key}'
        
        print(f"✅ Model uploaded to: {s3_path}")
        return s3_path
        
    except Exception as e:
        print(f"❌ S3 upload failed: {e}")
        return None

def create_pytorch_model(model_data_url):
    """
    Create SageMaker PyTorch model
    """
    print("🚀 Creating PyTorch model...")
    
    # Set up session
    boto_session = boto3.session.Session(region_name=REGION)
    session = sagemaker.Session(boto_session=boto_session)
    
    # Environment variables
    env_vars = {
        'HABS_MODEL_TYPE': 'qwen3-vl-hockey-analytics',
        'HF_MODEL_ID': MODEL_NAME,
        'SM_NUM_GPUS': '4',  # ml.g5.12xlarge has 4 GPUs
        'MAX_SEQUENCE_LENGTH': '8192',
        'TEMPERATURE': '0.1',
        'TOP_P': '0.9',
        'THINKING_MODE': 'true',
        'MULTIMODAL_SUPPORT': 'true',
        'HOCKEY_CONTEXT': 'true',
        'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
        'HF_HOME': '/tmp/huggingface_cache',
        # PyTorch specific
        'SM_MODEL_DIR': '/opt/ml/model',
        'SM_FRAMEWORK': 'pytorch',
    }
    
    try:
        # Create PyTorch model with proven working versions
        model = PyTorchModel(
            model_data=model_data_url,
            role="arn:aws:iam::803243354066:role/HeartBeatSageMakerExecutionRole",
            entry_point='inference.py',
            framework_version='2.0.1',  # Proven working version
            py_version='py310',
            env=env_vars,
            name=CONFIG['model_name'],
            sagemaker_session=session
        )
        
        print("✅ PyTorch model created successfully")
        return model
        
    except Exception as e:
        print(f"❌ PyTorch model creation failed: {e}")
        return None

def deploy_pytorch_model(model):
    """
    Deploy PyTorch model to endpoint
    """
    print(f"🚀 Deploying PyTorch model to: {CONFIG['endpoint_name']}")
    
    try:
        predictor = model.deploy(
            initial_instance_count=CONFIG['instance_count'],
            instance_type=CONFIG['instance_type'],
            endpoint_name=CONFIG['endpoint_name'],
            volume_size=CONFIG['volume_size'],
            model_data_download_timeout=1800,  # 30 minutes
            container_startup_health_check_timeout=1800,  # 30 minutes
            wait=True
        )
        
        print("🎉 PyTorch model deployed successfully!")
        print(f"📊 Endpoint: {CONFIG['endpoint_name']}")
        print(f"🖥️  Instance: {CONFIG['instance_type']}")
        print(f"📍 Region: {REGION}")
        
        return predictor
        
    except Exception as e:
        print(f"❌ PyTorch deployment failed: {e}")
        return None

def test_pytorch_endpoint():
    """
    Test the deployed PyTorch endpoint
    """
    print("🧪 Testing PyTorch endpoint...")
    
    runtime = boto3.client('sagemaker-runtime', region_name=REGION)
    
    test_payload = {
        "inputs": "Analyze Montreal Canadiens power play effectiveness.",
        "parameters": {
            "thinking_mode": True,
            "hockey_context": True,
            "temperature": 0.1,
            "max_new_tokens": 512
        }
    }
    
    try:
        response = runtime.invoke_endpoint(
            EndpointName=CONFIG['endpoint_name'],
            ContentType='application/json',
            Body=json.dumps(test_payload)
        )
        
        result = json.loads(response['Body'].read().decode())
        
        print("✅ PyTorch endpoint test successful!")
        print(f"📝 Response: {str(result)[:200]}...")
        
        return result
        
    except Exception as e:
        print(f"❌ PyTorch endpoint test failed: {e}")
        return None

def main():
    """
    Main PyTorch deployment workflow
    """
    print("🏒 HeartBeat Engine - Qwen3-VL PyTorch Deployment")
    print("=" * 60)
    print(f"Model: {MODEL_NAME}")
    print(f"Endpoint: {CONFIG['endpoint_name']}")
    print(f"Instance: {CONFIG['instance_type']}")
    print(f"Region: {REGION}")
    print("=" * 60)
    
    # Step 1: Create model artifacts
    model_path = create_model_artifacts()
    
    # Step 2: Upload to S3
    s3_url = upload_to_s3(model_path)
    if not s3_url:
        print("❌ Failed to upload model artifacts")
        return
    
    # Step 3: Create PyTorch model
    model = create_pytorch_model(s3_url)
    if not model:
        print("❌ Failed to create PyTorch model")
        return
    
    # Step 4: Deploy model
    predictor = deploy_pytorch_model(model)
    if not predictor:
        print("❌ Failed to deploy PyTorch model")
        return
    
    # Step 5: Test endpoint
    test_result = test_pytorch_endpoint()
    
    if test_result:
        print("\n🎉 PyTorch Deployment Complete!")
        print("=" * 60)
        print(f"✅ Endpoint: {CONFIG['endpoint_name']}")
        print(f"✅ Region: {REGION}")
        print(f"✅ Model: Qwen3-VL-235B-A22B-Thinking")
        print(f"✅ Framework: PyTorch 2.0.1")
        
        print("\n🔧 LangGraph Integration:")
        print(f"   endpoint_name = '{CONFIG['endpoint_name']}'")
        print(f"   region = '{REGION}'")
        print(f"   framework = 'pytorch'")
        
        print("\n📚 Next Steps:")
        print("1. Update LangGraph orchestrator with endpoint details")
        print("2. Test multimodal hockey analytics capabilities")
        print("3. Optimize prompts for Montreal Canadiens use cases")

if __name__ == "__main__":
    main()
