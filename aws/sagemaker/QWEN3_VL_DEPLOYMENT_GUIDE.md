# HeartBeat Engine - Qwen3-VL-235B-A22B-Thinking Deployment Guide

## Multimodal Hockey Analytics Model Deployment

### Model Overview
**Qwen/Qwen3-VL-235B-A22B-Thinking** is a state-of-the-art multimodal vision-language model that brings revolutionary capabilities to HeartBeat Engine:

- **Architecture**: Mixture-of-Experts (MoE) with 235B total parameters, 22B active per token
- **Context Window**: 256K tokens native, extendable to 1M tokens
- **Multimodal**: Vision-language processing with enhanced spatial reasoning
- **Thinking Mode**: Dual-mode operation for enhanced analytical reasoning
- **Languages**: OCR support across 32 languages
- **Agentic Capabilities**: GUI interpretation and action planning

### Key Advantages for Hockey Analytics
1. **Video Analysis**: Process game footage and extract tactical insights
2. **Rink Visualization**: Interpret shot heatmaps, player positioning diagrams
3. **Statistical Interpretation**: Analyze complex statistical visualizations
4. **Enhanced Reasoning**: Thinking mode provides detailed analytical process
5. **Massive Context**: Handle entire game transcripts and multiple data sources
6. **Spatial Understanding**: Better comprehension of hockey's spatial dynamics

## Deployment Options

### Option 1: Automated Deployment (Recommended)

Run the automated deployment script:

```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat/infrastructure/sagemaker
python deploy_qwen3_vl.py
```

**What this does:**
- Creates optimized SageMaker model with hockey-specific configuration
- Deploys to `ml.g5.2xlarge` instance (optimized for large multimodal models)
- Configures environment variables for hockey analytics optimization
- Runs comprehensive testing suite
- Provides integration details for LangGraph orchestrator

### Option 2: AWS Console Deployment

#### Step 1: Create Model
1. **AWS Console** → **SageMaker** → **Inference** → **Models**
2. Click **"Create model"**
3. Configure:
   - **Model name**: `heartbeat-qwen3-vl-hockey-{timestamp}`
   - **IAM role**: Your SageMaker execution role
   - **Container**: `763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-inference:2.1.0-transformers4.40.0-gpu-py310-cu118-ubuntu20.04`
   - **Model artifacts**: Leave empty (will load from HuggingFace Hub)
   - **Environment variables**:
     ```
     HABS_MODEL_TYPE=qwen3-vl-hockey-analytics
     MODEL_NAME=Qwen/Qwen3-VL-235B-A22B-Thinking
     MAX_SEQUENCE_LENGTH=8192
     TEMPERATURE=0.1
     TOP_P=0.9
     THINKING_MODE=true
     MULTIMODAL_SUPPORT=true
     HOCKEY_CONTEXT=true
     TORCH_DTYPE=bfloat16
     USE_FLASH_ATTENTION=true
     MOE_OPTIMIZATION=true
     EXPERTS_ACTIVE=8
     EXPERTS_TOTAL=128
     ```

#### Step 2: Create Endpoint Configuration
1. **SageMaker** → **Inference** → **Endpoint configurations**
2. Click **"Create endpoint configuration"**
3. Settings:
   - **Name**: `heartbeat-qwen3vl-config-{timestamp}`
   - **Model**: Select the model from Step 1
   - **Instance type**: `ml.g5.2xlarge` (recommended) or `ml.g5.4xlarge` (for higher performance)
   - **Instance count**: `1`
   - **Volume size**: `100 GB`

#### Step 3: Create Endpoint
1. **SageMaker** → **Inference** → **Endpoints**
2. Click **"Create endpoint"**
3. Settings:
   - **Name**: `heartbeat-qwen3vl-analytics-{timestamp}`
   - **Endpoint configuration**: Select config from Step 2

## Instance Type Recommendations

### Production Environment
- **ml.g5.2xlarge** (Recommended)
  - 8 vCPUs, 32 GB RAM, 1x NVIDIA A10G (24GB GPU memory)
  - Cost-effective for most workloads
  - ~$1.50/hour

- **ml.g5.4xlarge** (High Performance)
  - 16 vCPUs, 64 GB RAM, 1x NVIDIA A10G (24GB GPU memory)
  - Better for concurrent requests
  - ~$2.00/hour

### Development/Testing
- **ml.g4dn.2xlarge** (Budget Option)
  - 8 vCPUs, 32 GB RAM, 1x NVIDIA T4 (16GB GPU memory)
  - May have slower response times
  - ~$0.75/hour

## Expected Performance Metrics

### Response Times
- **Text-only queries**: 2-4 seconds
- **Multimodal queries**: 4-7 seconds
- **Complex thinking mode**: 5-10 seconds
- **Large context (>50K tokens)**: 10-15 seconds

### Throughput
- **Concurrent requests**: 2-3 simultaneous requests
- **Peak throughput**: ~0.5 requests/second for complex queries
- **Simple queries**: Up to 1-2 requests/second

### Context Utilization
- **Efficient range**: 8K-32K tokens
- **Extended range**: Up to 256K tokens
- **Maximum**: 1M tokens (use sparingly due to cost)

## Testing and Validation

### Automated Testing
```bash
python test_qwen3_vl_endpoint.py
```

This comprehensive test suite validates:
- Text-only hockey analytics queries
- Multimodal image processing capabilities
- Performance under concurrent load
- Thinking mode functionality
- Hockey domain knowledge accuracy

### Manual Testing Examples

#### Text-Only Query
```python
import boto3
import json

runtime = boto3.client('sagemaker-runtime', region_name='us-east-1')

payload = {
    "text": "Analyze the effectiveness of Montreal's power play system",
    "thinking_mode": True,
    "hockey_context": True,
    "temperature": 0.1
}

response = runtime.invoke_endpoint(
    EndpointName='your-endpoint-name',
    ContentType='application/json',
    Body=json.dumps(payload)
)

result = json.loads(response['Body'].read().decode())
print(result['response'])
```

#### Multimodal Query
```python
# Include base64 encoded image
payload = {
    "text": "Analyze this shot heatmap and provide tactical insights",
    "image": "data:image/png;base64,iVBOR...",
    "thinking_mode": True,
    "hockey_context": True
}

response = runtime.invoke_endpoint(
    EndpointName='your-endpoint-name',
    ContentType='application/json',
    Body=json.dumps(payload)
)
```

## LangGraph Integration

### Endpoint Configuration
Update your LangGraph orchestrator configuration:

```python
# orchestrator/config.py
QWEN3_VL_CONFIG = {
    'endpoint_name': 'heartbeat-qwen3vl-analytics-{your-timestamp}',
    'region': 'us-east-1',
    'model_type': 'qwen3-vl-multimodal',
    'supports_images': True,
    'supports_thinking': True,
    'max_context': 256000,
    'optimal_context': 8192
}
```

### Integration Example
```python
from langchain_community.llms import SagemakerEndpoint
from langchain_community.llms.sagemaker_endpoint import LLMContentHandler

class Qwen3VLContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"
    
    def transform_input(self, prompt: str, model_kwargs: dict) -> bytes:
        input_str = json.dumps({
            "text": prompt,
            **model_kwargs
        })
        return input_str.encode('utf-8')
    
    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json.get("response", "")

# Initialize LLM
llm = SagemakerEndpoint(
    endpoint_name="heartbeat-qwen3vl-analytics-{timestamp}",
    region_name="us-east-1",
    content_handler=Qwen3VLContentHandler(),
    model_kwargs={
        "thinking_mode": True,
        "hockey_context": True,
        "temperature": 0.1
    }
)
```

## Monitoring and Optimization

### CloudWatch Metrics to Monitor
- **InvocationLatency**: Response time per request
- **ModelLatency**: Model processing time
- **OverheadLatency**: Container overhead
- **Invocations**: Total request count
- **InvocationErrors**: Error rate

### Cost Optimization Strategies
1. **Instance Scaling**: Use auto-scaling for variable workloads
2. **Context Management**: Limit context size for routine queries
3. **Caching**: Implement response caching for similar queries
4. **Batch Processing**: Group similar queries when possible

### Performance Tuning
- **Temperature**: Lower (0.1) for consistent analytics, higher (0.3) for creative insights
- **Context Length**: Use 8K tokens for efficiency, scale up only when needed
- **Thinking Mode**: Enable for complex analysis, disable for simple queries
- **Image Resolution**: Resize images to optimal dimensions (800x600) for faster processing

## Troubleshooting

### Common Issues

#### 1. Model Loading Timeout
**Symptom**: Endpoint stuck in "Creating" status
**Solution**: 
- Increase `container_startup_health_check_timeout` to 30 minutes
- Ensure sufficient instance memory (use g5.2xlarge or higher)

#### 2. Out of Memory Errors
**Symptom**: 500 errors during inference
**Solutions**:
- Reduce context length in requests
- Use smaller batch sizes
- Upgrade to g5.4xlarge instance

#### 3. Slow Response Times
**Symptom**: Responses taking >30 seconds
**Solutions**:
- Reduce `max_new_tokens` parameter
- Disable thinking mode for simple queries
- Use optimized image sizes for multimodal requests

#### 4. Multimodal Processing Errors
**Symptom**: Images not being processed correctly
**Solutions**:
- Ensure images are base64 encoded correctly
- Check image format (PNG, JPG supported)
- Verify image size (<10MB recommended)

## Security Considerations

### Data Privacy
- All data processed within AWS infrastructure
- No data stored persistently on endpoints
- Montreal Canadiens data remains within Canadian AWS regions (if using ca-central-1)

### Access Control
- Use IAM roles for endpoint access
- Implement request logging for audit trails
- Consider VPC endpoints for enhanced security

## Deployment Checklist

### Pre-Deployment
- [ ] AWS credentials configured
- [ ] SageMaker execution role created
- [ ] Region selected (us-east-1 recommended for availability)
- [ ] Instance type decided based on performance needs

### Deployment
- [ ] Model created successfully
- [ ] Endpoint configuration created
- [ ] Endpoint deployed and InService
- [ ] Test suite passed successfully

### Post-Deployment
- [ ] LangGraph integration configured
- [ ] Monitoring dashboards set up
- [ ] Cost alerts configured
- [ ] Performance baselines established
- [ ] Documentation updated with endpoint details

## Next Steps

1. **Deploy the Model**: Use automated script or manual steps above
2. **Run Tests**: Validate all capabilities with test suite
3. **Integrate with LangGraph**: Update orchestrator configuration
4. **Optimize Prompts**: Fine-tune prompts for hockey-specific use cases
5. **Monitor Performance**: Set up CloudWatch dashboards and alerts

## Support and Maintenance

### Regular Tasks
- **Weekly**: Review performance metrics and costs
- **Monthly**: Update model to latest version if available
- **Quarterly**: Optimize instance types based on usage patterns

### Contact Information
- **Technical Issues**: Check CloudWatch logs and AWS support
- **Model Performance**: Iterate on prompts and parameters
- **Cost Optimization**: Review usage patterns and scaling policies

---

**🎉 Your HeartBeat Engine is ready for advanced multimodal hockey analytics with Qwen3-VL-235B-A22B-Thinking!**
