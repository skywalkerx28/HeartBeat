#!/usr/bin/env python3
"""
HeartBeat Engine - Model Deployment Pipeline
Montreal Canadiens Advanced Analytics Assistant

Automated deployment pipeline for the fine-tuned DeepSeek-R1-Distill-Qwen-32B model.
"""

import asyncio
import boto3
import json
import logging
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.sagemaker_endpoint import SageMakerEndpointManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class ModelDeploymentPipeline:
    """
    Automated deployment pipeline for HeartBeat models.
    
    Features:
    - Automated model deployment from S3
    - Endpoint configuration and scaling
    - Health checks and validation
    - Integration with orchestrator
    """
    
    def __init__(self):
        self.endpoint_manager = SageMakerEndpointManager()
        self.sagemaker_client = boto3.client('sagemaker', region_name='ca-central-1')
    
    async def deploy_latest_model(self, training_job_name: str) -> Dict[str, Any]:
        """
        Deploy the latest trained model to inference endpoint.
        
        Args:
            training_job_name: Name of the completed training job
            
        Returns:
            Deployment result and endpoint information
        """
        
        print("=== HeartBeat Engine - Model Deployment Pipeline ===")
        print(f"Deploying model from training job: {training_job_name}")
        
        try:
            # Step 1: Get training job details and model artifacts
            model_artifacts = await self._get_model_artifacts(training_job_name)
            
            if not model_artifacts["success"]:
                return model_artifacts
            
            print(f"✅ Model artifacts located: {model_artifacts['s3_path']}")
            
            # Step 2: Deploy model to endpoint
            deployment_result = await self.endpoint_manager.deploy_model_endpoint(
                model_s3_path=model_artifacts["s3_path"]
            )
            
            if deployment_result["success"]:
                print(f"✅ Model deployment initiated")
                print(f"   Endpoint: {deployment_result['endpoint_name']}")
                print(f"   Status: {deployment_result['endpoint_status']}")
                
                # Step 3: Update orchestrator configuration
                await self._update_orchestrator_config(deployment_result)
                
                # Step 4: Run health checks
                health_result = await self._run_health_checks(deployment_result["endpoint_name"])
                
                return {
                    "success": True,
                    "deployment": deployment_result,
                    "health_checks": health_result,
                    "endpoint_name": deployment_result["endpoint_name"]
                }
            else:
                print(f"❌ Model deployment failed: {deployment_result['error']}")
                return deployment_result
                
        except Exception as e:
            logger.error(f"Deployment pipeline failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_model_artifacts(self, training_job_name: str) -> Dict[str, Any]:
        """Get model artifacts from completed training job"""
        
        try:
            # Describe training job
            response = self.sagemaker_client.describe_training_job(
                TrainingJobName=training_job_name
            )
            
            # Check if training job completed successfully
            status = response['TrainingJobStatus']
            
            if status != 'Completed':
                return {
                    "success": False,
                    "error": f"Training job status: {status}. Must be 'Completed' to deploy."
                }
            
            # Get model artifacts S3 path
            model_artifacts_s3 = response['ModelArtifacts']['S3ModelArtifacts']
            
            return {
                "success": True,
                "s3_path": model_artifacts_s3,
                "training_job_name": training_job_name,
                "training_status": status,
                "creation_time": response['CreationTime'],
                "training_end_time": response['TrainingEndTime']
            }
            
        except Exception as e:
            logger.error(f"Failed to get model artifacts: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_orchestrator_config(self, deployment_result: Dict[str, Any]) -> None:
        """Update orchestrator configuration with new endpoint"""
        
        try:
            endpoint_name = deployment_result["endpoint_name"]
            
            # Update orchestrator settings
            from orchestrator.config.settings import settings
            settings.model.primary_model_endpoint = endpoint_name
            
            logger.info(f"Orchestrator updated with endpoint: {endpoint_name}")
            
        except Exception as e:
            logger.error(f"Failed to update orchestrator config: {str(e)}")
    
    async def _run_health_checks(self, endpoint_name: str) -> Dict[str, Any]:
        """Run health checks on deployed endpoint"""
        
        try:
            # Test inference with simple prompt
            test_prompt = "Test prompt for HeartBeat Engine health check"
            
            inference_result = await self.endpoint_manager.invoke_endpoint(
                prompt=test_prompt,
                max_tokens=50,
                temperature=0.1
            )
            
            if inference_result["success"]:
                return {
                    "success": True,
                    "inference_test": "passed",
                    "inference_time_ms": inference_result["inference_time_ms"],
                    "endpoint_responsive": True
                }
            else:
                return {
                    "success": False,
                    "inference_test": "failed",
                    "error": inference_result["error"]
                }
                
        except Exception as e:
            logger.error(f"Health checks failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_latest_training_job(self) -> Optional[str]:
        """Get the name of the latest HeartBeat training job"""
        
        try:
            # List training jobs with HeartBeat prefix
            response = self.sagemaker_client.list_training_jobs(
                NameContains="heartbeat-deepseek-r1-qwen-32b",
                StatusEquals='Completed',
                SortBy='CreationTime',
                SortOrder='Descending',
                MaxResults=1
            )
            
            training_jobs = response.get('TrainingJobSummaries', [])
            
            if training_jobs:
                return training_jobs[0]['TrainingJobName']
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to get latest training job: {str(e)}")
            return None
    
    async def deploy_when_ready(self, check_interval_minutes: int = 5) -> Dict[str, Any]:
        """
        Monitor for completed training job and deploy automatically.
        
        Args:
            check_interval_minutes: How often to check for completion
            
        Returns:
            Deployment result when training completes
        """
        
        print("=== Monitoring Training Job for Auto-Deployment ===")
        
        while True:
            try:
                # Check for completed training job
                latest_job = self.get_latest_training_job()
                
                if latest_job:
                    print(f"✅ Found completed training job: {latest_job}")
                    
                    # Deploy the model
                    deployment_result = await self.deploy_latest_model(latest_job)
                    
                    return deployment_result
                
                else:
                    print(f"⏳ No completed training jobs found. Checking again in {check_interval_minutes} minutes...")
                    await asyncio.sleep(check_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Error in auto-deployment monitoring: {str(e)}")
                await asyncio.sleep(check_interval_minutes * 60)

async def main():
    """Main deployment script"""
    
    pipeline = ModelDeploymentPipeline()
    
    # Check for latest completed training job
    latest_job = pipeline.get_latest_training_job()
    
    if latest_job:
        print(f"Found completed training job: {latest_job}")
        
        # Deploy immediately
        result = await pipeline.deploy_latest_model(latest_job)
        
        if result["success"]:
            print("Model deployment successful!")
            print(f"Endpoint: {result['endpoint_name']}")
        else:
            print(f"❌ Deployment failed: {result['error']}")
    
    else:
        print("No completed training jobs found.")
        
        # Ask user if they want to monitor for completion
        monitor = input("Monitor for training completion and auto-deploy? (y/n): ")
        
        if monitor.lower() == 'y':
            result = await pipeline.deploy_when_ready()
            
            if result["success"]:
                print("Auto-deployment successful!")
            else:
                print(f"❌ Auto-deployment failed: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
