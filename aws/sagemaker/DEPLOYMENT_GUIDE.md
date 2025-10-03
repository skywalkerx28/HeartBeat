# HeartBeat Engine - SageMaker Deployment Guide

## DeepSeek-R1 Hockey Analytics Model Deployment

### Quick Start: Using the AWS Console

#### Step 1: Create Model (YOU ARE HERE)
1. Click **"Create model"** button (top right)
2. Configure the model settings:
   - **Model name**: `heartbeat-deepseek-r1-hockey-2025-09-23`
   - **IAM role**: Use your SageMaker execution role
   - **Container**: Will auto-populate from training job
   - **Environment variables**: Add these for hockey optimization:
     ```
     HABS_MODEL_TYPE=deepseek-r1-hockey-analytics
     MAX_SEQUENCE_LENGTH=4096
     TEMPERATURE=0.1
     TOP_P=0.9
     ```

#### Step 2: Create Endpoint Configuration
1. Go to **Inference → Endpoint configurations**
2. Click **"Create endpoint configuration"**
3. Settings:
   - **Name**: `heartbeat-hockey-config-2025-09-23`
   - **Production variant**: Select your model
   - **Instance type**: `ml.g4dn.xlarge` (recommended for cost/performance)
   - **Instance count**: `1`

#### Step 3: Create Endpoint
1. Go to **Inference → Endpoints**
2. Click **"Create endpoint"**
3. Settings:
   - **Name**: `heartbeat-hockey-analytics-2025-09-23`
   - **Endpoint configuration**: Select the config from Step 2
   - **Tags**: Add project tags

### Alternative: Automated Deployment Script

You can also use the Python deployment script I created:

```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat/infrastructure/sagemaker
python deploy_model.py
```

But you'll need to update the configuration first.

## DEPLOYMENT STATUS: IN PROGRESS

**Current Status**: Model Created → Endpoint Deploying → Waiting for InService

Your HeartBeat Engine is currently deploying! Here's what to do while you wait:

### While Endpoint is Deploying (10-15 minutes):

#### Option 1: Monitor with Script
```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat/infrastructure/sagemaker
python monitor_deployment.py
```

#### Option 2: Manual Monitoring
Check the AWS Console endpoint status or run:
```bash
aws sagemaker describe-endpoint --endpoint-name heartbeat-hockey-analytics-2025-09-23
```

### Once Endpoint is InService:

#### 1. Validate Deployment
```bash
python test_deployment.py
```
Tests response time, hockey relevance, and model performance.

#### 2. Test LangGraph Integration
```bash
python langgraph_integration.py
```
Validates integration with your HeartBeat orchestrator.

#### 3. Integration Details
- **Endpoint Name**: `heartbeat-hockey-analytics-2025-09-23`
- **Region**: `us-east-1`  
- **Instance**: `ml.g4dn.xlarge`
- **Expected Response Time**: <3 seconds
- **Ready for**: LangGraph orchestrator integration

### Key Deployment Information

**Training Job**: `heartbeat-deepseek-r1-qwen-32b-2025-09-23-10-03-58` 
**Model**: `heartbeat-deepseek-r1-hockey-2025-09-23` 
**Endpoint**: `heartbeat-hockey-analytics-2025-09-23` 
**Hockey Optimizations**: Environment variables configured  
**Performance Target**: <3s response time for complex analytics 
