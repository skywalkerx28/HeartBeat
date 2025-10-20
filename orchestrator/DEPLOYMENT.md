# HeartBeat Engine - Deployment Guide

**Montreal Canadiens Advanced Analytics Assistant**

## Deployment Overview

This guide covers deploying the HeartBeat orchestrator in production environments, from development testing to enterprise-grade deployments.

## Prerequisites

### System Requirements

- **Python**: 3.11 or higher
- **Memory**: Minimum 4GB RAM, recommended 8GB+
- **Storage**: 10GB+ for data and model caching
- **Network**: Reliable internet connection for external services

### External Services

- **AWS Account**: For SageMaker model hosting
- **Pinecone Account**: For vector database services
- **OpenAI Account**: Optional, for development fallback

### Dependencies

```bash
# Core dependencies
langgraph>=0.0.40
langchain>=0.1.0
langchain-community>=0.0.20

# Data processing
pandas>=2.0.0
pyarrow>=10.0.0
fastparquet>=0.8.0

# Vector database
pinecone>=3.0.0

# Model integration
openai>=1.0.0
boto3>=1.28.0

# Async support
asyncio
aiohttp
```

## Installation Methods

### Method 1: Direct Installation

```bash
# Clone or copy the orchestrator directory
cp -r orchestrator/ /path/to/your/project/

# Install dependencies
pip install -r orchestrator/requirements.txt

# Set environment variables
export PINECONE_API_KEY="your-pinecone-key"
export OPENAI_API_KEY="your-openai-key"  # Optional
```

### Method 2: Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy orchestrator code
COPY orchestrator/ ./orchestrator/

# Set environment variables
ENV PYTHONPATH=/app
ENV PINECONE_API_KEY=""
ENV OPENAI_API_KEY=""

# Expose port for health checks
EXPOSE 8000

CMD ["python", "-m", "orchestrator.health_check"]
```

### Method 3: Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: heartbeat-orchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: heartbeat-orchestrator
  template:
    metadata:
      labels:
        app: heartbeat-orchestrator
    spec:
      containers:
      - name: orchestrator
        image: heartbeat-orchestrator:latest
        ports:
        - containerPort: 8000
        env:
        - name: PINECONE_API_KEY
          valueFrom:
            secretKeyRef:
              name: orchestrator-secrets
              key: pinecone-api-key
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: orchestrator-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

## Configuration

### Environment Variables

```bash
# Required
export PINECONE_API_KEY="your-pinecone-api-key"

# Optional - for development fallback
export OPENAI_API_KEY="your-openai-api-key"

# AWS Configuration (if using SageMaker)
export AWS_ACCESS_KEY_ID="your-aws-access-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
export AWS_DEFAULT_REGION="ca-central-1"

# Data Configuration
export HEARTBEAT_DATA_DIR="/path/to/parquet/data"
export HEARTBEAT_CACHE_DIR="/path/to/cache"

# Logging
export HEARTBEAT_LOG_LEVEL="INFO"
export HEARTBEAT_LOG_FILE="/var/log/heartbeat.log"
```

### Configuration File

Create `orchestrator/config/production.py`:

```python
import os
from orchestrator.config.settings import OrchestratorSettings

class ProductionSettings(OrchestratorSettings):
    def __init__(self):
        super().__init__()
        
        # Model configuration
        self.model.primary_model_endpoint = os.getenv(
            "SAGEMAKER_ENDPOINT", 
            ""
        )
        self.model.fallback_api_key = os.getenv("OPENAI_API_KEY", "")
        
        # Pinecone configuration
        self.pinecone.api_key = os.getenv("PINECONE_API_KEY", "")
        self.pinecone.index_name = os.getenv(
            "PINECONE_INDEX", 
            "heartbeat-unified"
        )
        
        # Data configuration
        self.parquet.data_directory = os.getenv(
            "HEARTBEAT_DATA_DIR", 
            "/data/processed"
        )
        
        # Performance tuning
        self.orchestration.timeout_seconds = 60
        self.orchestration.max_parallel_tools = 5
        
        # Production optimizations
        self.orchestration.enable_debug_logging = False
        self.parquet.cache_enabled = True
        self.parquet.cache_ttl_seconds = 600  # 10 minutes

# Use production settings
settings = ProductionSettings()
```

## Deployment Environments

### Development Environment

```bash
# Quick setup for development
git clone <repository>
cd orchestrator/
pip install -e .

# Set minimal configuration
export PINECONE_API_KEY="dev-key"
export OPENAI_API_KEY="dev-key"

# Run tests
python test_orchestrator.py
```

### Staging Environment

```bash
# Production-like setup with monitoring
docker-compose -f docker-compose.staging.yml up -d

# Verify deployment
curl http://localhost:8000/health
```

```yaml
# docker-compose.staging.yml
version: '3.8'
services:
  orchestrator:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - HEARTBEAT_LOG_LEVEL=INFO
    volumes:
      - ./data:/data
      - ./logs:/var/log
    restart: unless-stopped
    
  monitoring:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
```

### Production Environment

#### AWS ECS Deployment

```json
{
  "family": "heartbeat-orchestrator",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/heartbeatTaskRole",
  "containerDefinitions": [
    {
      "name": "orchestrator",
      "image": "your-registry/heartbeat-orchestrator:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "PINECONE_API_KEY",
          "value": "#{PINECONE_API_KEY}"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:ssm:region:account:parameter/heartbeat/openai-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/heartbeat-orchestrator",
          "awslogs-region": "ca-central-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Kubernetes Production Deployment

```yaml
# Production namespace
apiVersion: v1
kind: Namespace
metadata:
  name: heartbeat-prod

---
# ConfigMap for non-sensitive configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: orchestrator-config
  namespace: heartbeat-prod
data:
  PINECONE_INDEX: "heartbeat-unified"
  HEARTBEAT_LOG_LEVEL: "INFO"
  HEARTBEAT_DATA_DIR: "/data/processed"

---
# Secret for sensitive configuration
apiVersion: v1
kind: Secret
metadata:
  name: orchestrator-secrets
  namespace: heartbeat-prod
type: Opaque
data:
  pinecone-api-key: <base64-encoded-key>
  openai-api-key: <base64-encoded-key>

---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: heartbeat-orchestrator
  namespace: heartbeat-prod
spec:
  replicas: 5
  selector:
    matchLabels:
      app: heartbeat-orchestrator
  template:
    metadata:
      labels:
        app: heartbeat-orchestrator
    spec:
      containers:
      - name: orchestrator
        image: heartbeat-orchestrator:v1.0.0
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: orchestrator-config
        env:
        - name: PINECONE_API_KEY
          valueFrom:
            secretKeyRef:
              name: orchestrator-secrets
              key: pinecone-api-key
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: orchestrator-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# Service
apiVersion: v1
kind: Service
metadata:
  name: orchestrator-service
  namespace: heartbeat-prod
spec:
  selector:
    app: heartbeat-orchestrator
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP

---
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orchestrator-hpa
  namespace: heartbeat-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: heartbeat-orchestrator
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Health Checks and Monitoring

### Health Check Endpoint

Create `orchestrator/health_check.py`:

```python
import asyncio
import json
from datetime import datetime
from orchestrator.config.settings import settings
from orchestrator import orchestrator, UserContext, UserRole

async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "checks": {}
    }
    
    try:
        # Configuration check
        config_valid = settings.validate_config()
        health_status["checks"]["configuration"] = {
            "status": "pass" if config_valid else "fail",
            "details": "Configuration validation"
        }
        
        # Basic orchestrator test
        test_user = UserContext(
            user_id="health_check",
            role=UserRole.STAFF
        )
        
        start_time = datetime.now()
        result = await orchestrator.process_query(
            "Test query for health check",
            test_user
        )
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        health_status["checks"]["orchestrator"] = {
            "status": "pass" if result else "fail",
            "processing_time_ms": int(processing_time),
            "details": "Basic orchestrator functionality"
        }
        
        # External services check
        # Add specific checks for Pinecone, SageMaker, etc.
        
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
    
    return health_status

if __name__ == "__main__":
    result = asyncio.run(health_check())
    print(json.dumps(result, indent=2))
```

### Monitoring Configuration

#### Prometheus Metrics

```python
# orchestrator/monitoring.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
query_counter = Counter('heartbeat_queries_total', 'Total queries processed', ['user_role', 'query_type'])
processing_time = Histogram('heartbeat_processing_seconds', 'Query processing time')
active_queries = Gauge('heartbeat_active_queries', 'Currently active queries')
error_counter = Counter('heartbeat_errors_total', 'Total errors', ['error_type'])

class MetricsCollector:
    def __init__(self):
        self.start_time = None
    
    def start_query(self, user_role, query_type):
        self.start_time = time.time()
        active_queries.inc()
        query_counter.labels(user_role=user_role, query_type=query_type).inc()
    
    def end_query(self):
        if self.start_time:
            processing_time.observe(time.time() - self.start_time)
        active_queries.dec()
    
    def record_error(self, error_type):
        error_counter.labels(error_type=error_type).inc()
```

#### Logging Configuration

```python
# orchestrator/logging_config.py
import logging
import os
from datetime import datetime

def setup_logging():
    log_level = os.getenv('HEARTBEAT_LOG_LEVEL', 'INFO')
    log_file = os.getenv('HEARTBEAT_LOG_FILE', '/var/log/heartbeat.log')
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=[file_handler, console_handler]
    )
    
    # Configure specific loggers
    logging.getLogger('orchestrator').setLevel(logging.INFO)
    logging.getLogger('pinecone').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)

if __name__ == "__main__":
    setup_logging()
```

## Security Considerations

### API Key Management

```bash
# Use AWS Secrets Manager
aws secretsmanager create-secret \
    --name "heartbeat/pinecone-key" \
    --description "Pinecone API key for HeartBeat" \
    --secret-string "your-pinecone-key"

# Use Kubernetes secrets
kubectl create secret generic orchestrator-secrets \
    --from-literal=pinecone-api-key="your-key" \
    --from-literal=openai-api-key="your-key"
```

### Network Security

```yaml
# Network policies for Kubernetes
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: orchestrator-network-policy
  namespace: heartbeat-prod
spec:
  podSelector:
    matchLabels:
      app: heartbeat-orchestrator
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-system
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to: []  # Allow all egress for external API calls
    ports:
    - protocol: TCP
      port: 443  # HTTPS
    - protocol: TCP
      port: 80   # HTTP
```

### Data Security

- **Encryption at Rest**: Encrypt data files and caches
- **Encryption in Transit**: Use HTTPS/TLS for all communications
- **Access Control**: Implement proper RBAC and user authentication
- **Audit Logging**: Log all data access and modifications

## Performance Tuning

### Memory Optimization

```python
# orchestrator/config/performance.py
import gc
from orchestrator.config.settings import OrchestratorSettings

class PerformanceSettings(OrchestratorSettings):
    def __init__(self):
        super().__init__()
        
        # Memory management
        self.parquet.cache_enabled = True
        self.parquet.cache_ttl_seconds = 300
        self.parquet.max_query_results = 1000
        
        # Concurrent processing
        self.orchestration.max_parallel_tools = 5
        self.orchestration.timeout_seconds = 45
        
        # Model optimization
        self.model.max_tokens = 2048  # Reduce for faster responses
        self.model.temperature = 0.1   # Lower for more consistent responses

def optimize_memory():
    """Force garbage collection and optimize memory usage"""
    gc.collect()
```

### Caching Strategy

```python
# orchestrator/cache.py
import redis
import json
import hashlib
from datetime import datetime, timedelta

class DistributedCache:
    def __init__(self, redis_url="redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.ttl = 600  # 10 minutes default
    
    def get_cache_key(self, query, user_context):
        """Generate cache key from query and user context"""
        key_data = {
            "query": query,
            "user_role": user_context.role.value,
            "team_access": sorted(user_context.team_access)
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get(self, query, user_context):
        """Get cached result"""
        key = self.get_cache_key(query, user_context)
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    def set(self, query, user_context, result):
        """Cache result"""
        key = self.get_cache_key(query, user_context)
        self.redis.setex(key, self.ttl, json.dumps(result))
```

## Troubleshooting

### Common Issues

#### 1. Configuration Errors

```bash
# Check configuration
python -c "from orchestrator.config.settings import settings; print(settings.validate_config())"

# Common fixes
export PINECONE_API_KEY="your-key"
export HEARTBEAT_DATA_DIR="/correct/path/to/data"
```

#### 2. Memory Issues

```bash
# Monitor memory usage
docker stats heartbeat-orchestrator

# Increase memory limits
kubectl patch deployment heartbeat-orchestrator -p '{"spec":{"template":{"spec":{"containers":[{"name":"orchestrator","resources":{"limits":{"memory":"8Gi"}}}]}}}}'
```

#### 3. Performance Issues

```bash
# Check processing times
kubectl logs -f deployment/heartbeat-orchestrator | grep "processing_time"

# Scale up replicas
kubectl scale deployment heartbeat-orchestrator --replicas=10
```

#### 4. External Service Issues

```bash
# Test Pinecone connectivity
python -c "from pinecone import Pinecone; pc = Pinecone(api_key='your-key'); print(pc.list_indexes())"

# Test SageMaker endpoint
aws sagemaker-runtime invoke-endpoint --endpoint-name your-endpoint --body '{"inputs":"test"}' /tmp/output.json
```

### Debugging Tools

```python
# orchestrator/debug.py
import logging
import json
from datetime import datetime

class DebugLogger:
    def __init__(self):
        self.logger = logging.getLogger('orchestrator.debug')
        self.logger.setLevel(logging.DEBUG)
    
    def log_query_start(self, query, user_context):
        self.logger.debug(f"Query started: {query[:100]}... for {user_context.role.value}")
    
    def log_tool_execution(self, tool_type, execution_time, success):
        self.logger.debug(f"Tool {tool_type.value}: {execution_time}ms, success: {success}")
    
    def log_state_transition(self, old_step, new_step, state_size):
        self.logger.debug(f"State: {old_step} -> {new_step}, size: {state_size}")

# Enable debug logging
debug_logger = DebugLogger()
```

## Maintenance

### Regular Maintenance Tasks

1. **Log Rotation**: Set up log rotation to prevent disk space issues
2. **Cache Cleanup**: Regularly clean expired cache entries
3. **Metric Collection**: Monitor and analyze performance metrics
4. **Security Updates**: Keep dependencies updated
5. **Backup**: Regular backup of configuration and data

### Update Procedures

```bash
# Rolling update in Kubernetes
kubectl set image deployment/heartbeat-orchestrator orchestrator=heartbeat-orchestrator:v1.1.0

# Verify deployment
kubectl rollout status deployment/heartbeat-orchestrator

# Rollback if needed
kubectl rollout undo deployment/heartbeat-orchestrator
```

---

**Deployment Guide**  
**HeartBeat Engine - Montreal Canadiens Analytics**  
Version 1.0.0
