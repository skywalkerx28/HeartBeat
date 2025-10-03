#!/usr/bin/env python3
"""
Comprehensive Diagnosis for SageMaker Endpoint Deployment Failures
Analyzes common issues with DeepSeek-R1-32B model deployment
"""

import boto3
import json

def diagnose_deployment_failure():
    """Analyze potential causes of endpoint deployment failure"""
    
    ENDPOINT_NAME = "heartbeat-hockey-analytics-2025-09-23"
    MODEL_NAME = "heartbeat-deepseek-r1-hockey-2025-09-23"
    REGION = "ca-central-1"
    
    print("🔬 HeartBeat Engine Deployment Failure Diagnosis")
    print("=" * 55)
    
    sagemaker = boto3.client('sagemaker', region_name=REGION)
    
    # Check endpoint details
    try:
        endpoint_resp = sagemaker.describe_endpoint(EndpointName=ENDPOINT_NAME)
        print(f"📊 Endpoint Status: {endpoint_resp['EndpointStatus']}")
        
        if 'FailureReason' in endpoint_resp:
            print(f"❌ Failure Reason: {endpoint_resp['FailureReason']}")
        
        # Check endpoint configuration
        config_name = endpoint_resp['EndpointConfigName']
        config_resp = sagemaker.describe_endpoint_config(EndpointConfigName=config_name)
        
        for variant in config_resp['ProductionVariants']:
            print(f"\n📋 Production Variant Analysis:")
            print(f"   Instance Type: {variant['InstanceType']}")
            print(f"   Initial Count: {variant['InitialInstanceCount']}")
            print(f"   Model: {variant['ModelName']}")
            
            # Check if instance type is appropriate for DeepSeek-R1-32B
            instance_type = variant['InstanceType']
            analyze_instance_compatibility(instance_type)
            
        # Check model details
        model_resp = sagemaker.describe_model(ModelName=MODEL_NAME)
        container = model_resp['PrimaryContainer']
        
        print(f"\n🤖 Model Configuration:")
        print(f"   Image: {container['Image']}")
        print(f"   Model Data: {container.get('ModelDataUrl', 'Not specified')}")
        
        # Analyze environment variables
        env_vars = container.get('Environment', {})
        print(f"\n🌐 Environment Variables:")
        for key, value in env_vars.items():
            print(f"   {key}: {value}")
            
        analyze_environment_variables(env_vars)
        
    except Exception as e:
        print(f"❌ Error accessing endpoint details: {e}")
    
    print("\n🔍 COMMON CAUSES & SOLUTIONS:")
    print("=" * 40)
    
    print("\n1. 🧠 MODEL SIZE ISSUES:")
    print("   Problem: DeepSeek-R1-32B is a 32B parameter model (~64GB)")
    print("   Solution: Use larger instance type (ml.g4dn.2xlarge or ml.p3.2xlarge)")
    
    print("\n2. 🕐 STARTUP TIMEOUT:")
    print("   Problem: Model loading exceeds health check timeout (10 minutes)")
    print("   Solution: Increase timeout or optimize model loading")
    
    print("\n3. 📦 DEPENDENCY ISSUES:")
    print("   Problem: Missing transformers, torch, or other dependencies")
    print("   Solution: Check inference.py imports and container image")
    
    print("\n4. 🌍 REGION-SPECIFIC ISSUES:")
    print("   Problem: ca-central-1 may have different container availability")
    print("   Solution: Try us-east-1 or verify container image in ca-central-1")
    
    print("\n5. 💾 INFERENCE CODE ERRORS:")
    print("   Problem: Bugs in inference.py script")
    print("   Solution: Test inference code locally or simplify implementation")
    
    # Specific recommendations
    print("\n🎯 RECOMMENDED IMMEDIATE ACTIONS:")
    print("=" * 40)
    print("1. Run: python debug_logs.py (check CloudWatch logs)")
    print("2. Try larger instance: ml.g4dn.2xlarge or ml.p3.2xlarge") 
    print("3. Simplify inference code (remove flash_attention_2)")
    print("4. Consider using us-east-1 region for better compatibility")
    print("5. Test with a smaller model first")

def analyze_instance_compatibility(instance_type):
    """Analyze if instance type is suitable for DeepSeek-R1-32B"""
    print(f"\n🖥️  Instance Type Analysis: {instance_type}")
    
    instance_specs = {
        'ml.g4dn.xlarge': {'gpu_memory': '16GB', 'ram': '16GB', 'suitable': False},
        'ml.g4dn.2xlarge': {'gpu_memory': '16GB', 'ram': '32GB', 'suitable': True},
        'ml.g4dn.4xlarge': {'gpu_memory': '16GB', 'ram': '64GB', 'suitable': True},
        'ml.p3.2xlarge': {'gpu_memory': '16GB', 'ram': '61GB', 'suitable': True},
        'ml.p3.8xlarge': {'gpu_memory': '64GB', 'ram': '244GB', 'suitable': True},
    }
    
    spec = instance_specs.get(instance_type, {'suitable': False})
    
    if spec['suitable']:
        print(f"   ✅ Likely suitable for DeepSeek-R1-32B")
        print(f"   📊 GPU Memory: {spec.get('gpu_memory', 'Unknown')}")
        print(f"   💾 RAM: {spec.get('ram', 'Unknown')}")
    else:
        print(f"   ⚠️  May be too small for DeepSeek-R1-32B")
        print(f"   💡 Recommendation: Upgrade to ml.g4dn.2xlarge or ml.p3.2xlarge")

def analyze_environment_variables(env_vars):
    """Check environment variables for potential issues"""
    print(f"\n🔬 Environment Variable Analysis:")
    
    required_vars = ['HABS_MODEL_TYPE', 'MAX_SEQUENCE_LENGTH', 'TEMPERATURE']
    missing_vars = [var for var in required_vars if var not in env_vars]
    
    if missing_vars:
        print(f"   ⚠️  Missing variables: {missing_vars}")
    else:
        print(f"   ✅ All hockey optimization variables present")
    
    # Check for problematic values
    if 'MAX_SEQUENCE_LENGTH' in env_vars:
        max_len = int(env_vars['MAX_SEQUENCE_LENGTH'])
        if max_len > 4096:
            print(f"   ⚠️  MAX_SEQUENCE_LENGTH ({max_len}) might be too large")

def create_fixed_inference_code():
    """Generate a simplified inference.py for debugging"""
    simplified_code = '''#!/usr/bin/env python3
"""
Simplified Inference Script for DeepSeek-R1 Debugging
Removes complex optimizations to isolate issues
"""

import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def model_fn(model_dir):
    """Simplified model loading"""
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    
    print("Model loaded successfully!")
    return {'model': model, 'tokenizer': tokenizer}

def input_fn(request_body, content_type='application/json'):
    """Simplified input processing"""
    input_data = json.loads(request_body)
    return input_data.get('inputs', '')

def predict_fn(input_data, model_components):
    """Simplified prediction"""
    model = model_components['model']
    tokenizer = model_components['tokenizer']
    
    inputs = tokenizer(input_data, return_tensors="pt", max_length=1024, truncation=True)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.1,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return {'generated_text': generated_text}

def output_fn(prediction, accept='application/json'):
    """Simplified output formatting"""
    return json.dumps(prediction)
'''
    
    with open('/Users/xavier.bouchard/Desktop/HeartBeat/infrastructure/sagemaker/inference_simplified.py', 'w') as f:
        f.write(simplified_code)
    
    print("\n📝 Created simplified inference code: inference_simplified.py")
    print("   Use this for debugging if the original inference.py has issues")

if __name__ == "__main__":
    diagnose_deployment_failure()
    create_fixed_inference_code()
