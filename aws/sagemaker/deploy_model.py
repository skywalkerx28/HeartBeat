#!/usr/bin/env python3
"""
SageMaker Model Deployment Script for DeepSeek-R1-Distill-Qwen-32B
HeartBeat Engine - Hockey Analytics Platform
"""

import boto3
import json
from datetime import datetime
from typing import Dict, Any, Optional
import time

class DeepSeekModelDeployer:
    """
    Handles deployment of fine-tuned DeepSeek model to SageMaker inference endpoint
    """
    
    def __init__(self, region_name: str = "us-east-1"):
        """
        Initialize SageMaker client and configuration
        
        Args:
            region_name: AWS region for deployment
        """
        self.sagemaker_client = boto3.client('sagemaker', region_name=region_name)
        self.region = region_name
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        # HeartBeat Engine specific configuration
        self.model_name_prefix = "heartbeat-deepseek-r1"
        self.endpoint_name_prefix = "heartbeat-hockey-analytics"
        
    def create_model(self, 
                     model_artifacts_s3_uri: str,
                     execution_role_arn: str,
                     model_name: Optional[str] = None) -> str:
        """
        Create SageMaker model from trained artifacts
        
        Args:
            model_artifacts_s3_uri: S3 URI of trained model artifacts (model.tar.gz)
            execution_role_arn: IAM role ARN for SageMaker execution
            model_name: Custom model name (optional)
            
        Returns:
            str: Created model name
        """
        if not model_name:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            model_name = f"{self.model_name_prefix}-{timestamp}"
        
        # Hugging Face Deep Learning Container for inference
        # Using the latest PyTorch inference container that supports transformers
        image_uri = f"763104351884.dkr.ecr.{self.region}.amazonaws.com/huggingface-pytorch-inference:2.0.0-transformers4.28.1-gpu-py310-cu118-ubuntu20.04"
        
        model_config = {
            'ModelName': model_name,
            'ExecutionRoleArn': execution_role_arn,
            'PrimaryContainer': {
                'Image': image_uri,
                'ModelDataUrl': model_artifacts_s3_uri,
                'Environment': {
                    'SAGEMAKER_PROGRAM': 'inference.py',
                    'SAGEMAKER_SUBMIT_DIRECTORY': '/opt/ml/code',
                    'TRANSFORMERS_CACHE': '/tmp/transformers_cache',
                    'HF_DATASETS_CACHE': '/tmp/datasets_cache',
                    'PYTORCH_TRANSFORMERS_CACHE': '/tmp/transformers_cache',
                    # Hockey-specific environment variables
                    'HABS_MODEL_TYPE': 'deepseek-r1-hockey-analytics',
                    'MAX_SEQUENCE_LENGTH': '4096',
                    'TEMPERATURE': '0.1',  # Low temperature for consistent hockey analysis
                    'TOP_P': '0.9'
                }
            },
            'Tags': [
                {'Key': 'Project', 'Value': 'HeartBeat-Engine'},
                {'Key': 'Model', 'Value': 'DeepSeek-R1-Hockey-Analytics'},
                {'Key': 'Team', 'Value': 'Montreal-Canadiens'},
                {'Key': 'Environment', 'Value': 'Production'}
            ]
        }
        
        print(f"Creating SageMaker model: {model_name}")
        try:
            response = self.sagemaker_client.create_model(**model_config)
            print(f"✓ Model created successfully: {model_name}")
            return model_name
        except Exception as e:
            print(f"✗ Error creating model: {str(e)}")
            raise
    
    def create_endpoint_config(self,
                             model_name: str,
                             instance_type: str = "ml.g4dn.xlarge",
                             endpoint_config_name: Optional[str] = None) -> str:
        """
        Create endpoint configuration for hockey analytics workload
        
        Args:
            model_name: Name of the SageMaker model
            instance_type: EC2 instance type for inference
            endpoint_config_name: Custom config name (optional)
            
        Returns:
            str: Created endpoint configuration name
        """
        if not endpoint_config_name:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            endpoint_config_name = f"{self.endpoint_name_prefix}-config-{timestamp}"
        
        # Optimized for hockey analytics workload
        config = {
            'EndpointConfigName': endpoint_config_name,
            'ProductionVariants': [{
                'VariantName': 'primary-variant',
                'ModelName': model_name,
                'InstanceType': instance_type,
                'InitialInstanceCount': 1,
                'InitialVariantWeight': 1,
                # Hockey analytics performance optimization
                'ModelDataDownloadTimeoutInSeconds': 900,  # 15 minutes for large model
                'ContainerStartupHealthCheckTimeoutInSeconds': 600,  # 10 minutes
                'VolumeSizeInGB': 30,  # Extra storage for transformers cache
            }],
            'Tags': [
                {'Key': 'Project', 'Value': 'HeartBeat-Engine'},
                {'Key': 'Workload', 'Value': 'Hockey-Analytics'},
                {'Key': 'ResponseTime-Target', 'Value': '<3-seconds'}
            ]
        }
        
        print(f"Creating endpoint configuration: {endpoint_config_name}")
        try:
            self.sagemaker_client.create_endpoint_config(**config)
            print(f"✓ Endpoint configuration created: {endpoint_config_name}")
            return endpoint_config_name
        except Exception as e:
            print(f"✗ Error creating endpoint configuration: {str(e)}")
            raise
    
    def create_endpoint(self,
                       endpoint_config_name: str,
                       endpoint_name: Optional[str] = None) -> str:
        """
        Create and deploy the inference endpoint
        
        Args:
            endpoint_config_name: Name of the endpoint configuration
            endpoint_name: Custom endpoint name (optional)
            
        Returns:
            str: Created endpoint name
        """
        if not endpoint_name:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            endpoint_name = f"{self.endpoint_name_prefix}-{timestamp}"
        
        config = {
            'EndpointName': endpoint_name,
            'EndpointConfigName': endpoint_config_name,
            'Tags': [
                {'Key': 'Project', 'Value': 'HeartBeat-Engine'},
                {'Key': 'Usage', 'Value': 'LangGraph-Orchestrator'},
                {'Key': 'Target-Users', 'Value': 'Coaches-Analysts-Players'}
            ]
        }
        
        print(f"Creating endpoint: {endpoint_name}")
        print("⏳ This may take 10-15 minutes for initial deployment...")
        
        try:
            self.sagemaker_client.create_endpoint(**config)
            print(f"✓ Endpoint creation initiated: {endpoint_name}")
            return endpoint_name
        except Exception as e:
            print(f"✗ Error creating endpoint: {str(e)}")
            raise
    
    def wait_for_endpoint(self, endpoint_name: str, timeout_minutes: int = 20) -> bool:
        """
        Wait for endpoint to be in service
        
        Args:
            endpoint_name: Name of the endpoint to monitor
            timeout_minutes: Maximum time to wait
            
        Returns:
            bool: True if endpoint is ready, False if timeout
        """
        print(f"⏳ Waiting for endpoint {endpoint_name} to be ready...")
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            try:
                response = self.sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
                status = response['EndpointStatus']
                
                print(f"Status: {status}", end='\r')
                
                if status == 'InService':
                    print(f"\n✓ Endpoint {endpoint_name} is ready for inference!")
                    return True
                elif status == 'Failed':
                    print(f"\n✗ Endpoint deployment failed")
                    failure_reason = response.get('FailureReason', 'Unknown error')
                    print(f"Failure reason: {failure_reason}")
                    return False
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"\n✗ Error checking endpoint status: {str(e)}")
                return False
        
        print(f"\n⚠️  Timeout waiting for endpoint after {timeout_minutes} minutes")
        return False
    
    def deploy_full_pipeline(self,
                           model_artifacts_s3_uri: str,
                           execution_role_arn: str,
                           instance_type: str = "ml.g4dn.xlarge") -> Dict[str, str]:
        """
        Complete deployment pipeline for HeartBeat Engine
        
        Args:
            model_artifacts_s3_uri: S3 URI of trained model
            execution_role_arn: IAM role for SageMaker
            instance_type: Instance type for inference
            
        Returns:
            Dict[str, str]: Deployment details (model, config, endpoint names)
        """
        print("🏒 Starting HeartBeat Engine Model Deployment Pipeline...")
        print("=" * 60)
        
        try:
            # Step 1: Create model
            model_name = self.create_model(model_artifacts_s3_uri, execution_role_arn)
            
            # Step 2: Create endpoint configuration
            config_name = self.create_endpoint_config(model_name, instance_type)
            
            # Step 3: Create endpoint
            endpoint_name = self.create_endpoint(config_name)
            
            # Step 4: Wait for deployment
            if self.wait_for_endpoint(endpoint_name):
                print("🎉 Deployment completed successfully!")
                
                deployment_info = {
                    'model_name': model_name,
                    'endpoint_config_name': config_name,
                    'endpoint_name': endpoint_name,
                    'instance_type': instance_type,
                    'region': self.region,
                    'status': 'ready'
                }
                
                # Save deployment info for LangGraph integration
                with open('/tmp/heartbeat_deployment_info.json', 'w') as f:
                    json.dump(deployment_info, f, indent=2)
                
                print(f"📝 Deployment info saved to /tmp/heartbeat_deployment_info.json")
                return deployment_info
            else:
                raise Exception("Endpoint deployment failed or timed out")
                
        except Exception as e:
            print(f"✗ Deployment pipeline failed: {str(e)}")
            raise

def main():
    """
    Example deployment script
    Update these values with your specific configuration
    """
    # TODO: Update these values with your specific configuration
    MODEL_ARTIFACTS_S3_URI = "s3://your-bucket/path/to/model.tar.gz"
    EXECUTION_ROLE_ARN = "arn:aws:iam::YOUR_ACCOUNT:role/SageMakerExecutionRole"
    
    deployer = DeepSeekModelDeployer(region_name="us-east-1")
    
    deployment_info = deployer.deploy_full_pipeline(
        model_artifacts_s3_uri=MODEL_ARTIFACTS_S3_URI,
        execution_role_arn=EXECUTION_ROLE_ARN,
        instance_type="ml.g4dn.xlarge"  # Good balance of cost/performance for DeepSeek
    )
    
    print("\n🏒 HeartBeat Engine Deployment Complete!")
    print("=" * 50)
    print(f"Endpoint Name: {deployment_info['endpoint_name']}")
    print(f"Region: {deployment_info['region']}")
    print(f"Instance Type: {deployment_info['instance_type']}")
    print("\nReady for LangGraph integration! 🚀")

if __name__ == "__main__":
    main()
