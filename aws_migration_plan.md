# AWS Migration Plan for RetailFlow Backend

## Current Issues with Railway Free Tier
- **Performance**: Slow response times due to resource constraints
- **Reliability**: Intermittent request failures during high load
- **Cold Starts**: Instances sleep causing delays for login/initial requests
- **Resource Limits**: 512MB RAM, shared CPU insufficient for production load

## AWS Free Tier Migration Strategy

### Phase 1: Infrastructure Setup
**Services to Use:**
- **EC2 t2.micro**: 1GB RAM, better performance (750 hours/month free)
- **Elastic Beanstalk**: Easy deployment with auto-scaling
- **ElastiCache**: Redis for caching (750 hours/month free)
- **CloudWatch**: Monitoring and logging
- **Route 53**: DNS management (if needed)

### Phase 2: Migration Steps

#### 1. Docker Container Preparation
```bash
# Build optimized Docker image
docker build -t retailflow-backend .
docker tag retailflow-backend:latest [AWS_ACCOUNT_ID].dkr.ecr.[REGION].amazonaws.com/retailflow-backend
```

#### 2. AWS Setup
```bash
# Create ECR repository
aws ecr create-repository --repository-name retailflow-backend

# Push to ECR
aws ecr get-login-password --region [REGION] | docker login --username AWS --password-stdin [AWS_ACCOUNT_ID].dkr.ecr.[REGION].amazonaws.com
docker push [AWS_ACCOUNT_ID].dkr.ecr.[REGION].amazonaws.com/retailflow-backend:latest
```

#### 3. Elastic Beanstalk Deployment
```bash
# Create EB application
eb init retailflow-backend --platform "Docker running on 64bit Amazon Linux 2"

# Create environment
eb create production --instance-type t2.micro --min-instances 1 --max-instances 2
```

### Phase 3: Environment Configuration

#### Production Environment Variables
```bash
# EB environment variables
eb setenv MONGO_URL=mongodb+srv://[USERNAME]:[PASSWORD]@cluster.mongodb.net/retailflow
eb setenv DATABASE_NAME=retailflow
eb setenv SECRET_KEY=[JWT_SECRET]
eb setenv ENVIRONMENT=production
eb setenv REDIS_URL=[ELASTICACHE_ENDPOINT]
eb setenv DEBUG=false
```

#### Security Configuration
- **Security Groups**: Restrict access to necessary ports only
- **IAM Roles**: Least privilege access for EC2 instances
- **SSL/TLS**: Enable HTTPS with AWS Certificate Manager
- **VPC**: Isolate resources in private subnets

### Phase 4: Performance Optimizations

#### 1. Enable Redis Caching
```python
# Update app/core/config.py
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_ENABLED = True  # Enable in AWS
```

#### 2. Database Connection Pooling
```python
# Optimize MongoDB connection for AWS
MONGO_OPTIONS = {
    "maxPoolSize": 50,
    "minPoolSize": 5,
    "maxIdleTimeMS": 30000,
    "serverSelectionTimeoutMS": 5000,
    "socketTimeoutMS": 10000
}
```

#### 3. Auto-scaling Configuration
```yaml
# .ebextensions/autoscaling.config
Resources:
  AWSEBAutoScalingGroup:
    Type: "AWS::AutoScaling::AutoScalingGroup"
    Properties:
      MinSize: 1
      MaxSize: 4
      DesiredCapacity: 2
      MetricsCollection:
        - Granularity: "1Minute"
```

### Phase 5: Monitoring & Logging

#### CloudWatch Setup
```python
# Add CloudWatch logging
import boto3
cloudwatch = boto3.client('cloudwatch')

# Custom metrics for API performance
def log_api_metrics(endpoint, response_time, status_code):
    cloudwatch.put_metric_data(
        Namespace='RetailFlow/API',
        MetricData=[
            {
                'MetricName': 'ResponseTime',
                'Value': response_time,
                'Unit': 'Milliseconds'
            },
            {
                'MetricName': 'RequestCount',
                'Value': 1,
                'Unit': 'Count'
            }
        ]
    )
```

#### Health Checks
```python
# Enhanced health endpoint for AWS
@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "database": await check_db_connection(),
        "cache": await check_redis_connection(),
        "memory": get_memory_usage(),
        "version": "1.0.0",
        "timestamp": datetime.utcnow()
    }
```

### Phase 6: DNS & SSL

#### Route 53 Configuration
```bash
# Create hosted zone
aws route53 create-hosted-zone --name retailflow-api.com

# Create A record for EB environment
aws route53 change-resource-record-sets --hosted-zone-id [ZONE_ID] --change-batch file://dns-config.json
```

#### SSL Certificate
```bash
# Request SSL certificate
aws acm request-certificate --domain-name retailflow-api.com --validation-method DNS

# Validate with Route 53 records
```

### Phase 7: Testing & Migration

#### 1. Load Testing
```bash
# Use Artillery.js for load testing
artillery run load-test.yml https://staging.retailflow-api.com
```

#### 2. Blue-Green Deployment
- Deploy to staging environment first
- Run full test suite
- Switch DNS gradually
- Monitor performance metrics

#### 3. Rollback Plan
- Keep Railway running for 48 hours
- Monitor error rates and response times
- Quick rollback if issues detected

### Cost Optimization (Free Tier)

**Monthly Costs After Free Tier:**
- **EC2**: $0 (within 750 hours)
- **ElastiCache**: $0 (within 750 hours) 
- **Data Transfer**: $0 (15GB free)
- **CloudWatch**: $0 (10 custom metrics free)
- **Estimated Total**: $0-10/month (if exceeding limits)

### Timeline
- **Week 1**: AWS account setup and infrastructure preparation
- **Week 2**: Docker optimization and ECR setup
- **Week 3**: Staging deployment and testing
- **Week 4**: Production migration and monitoring

### Success Metrics
- **Response Time**: <200ms (vs current 800ms+)
- **Uptime**: >99.9% (vs current ~95%)
- **Error Rate**: <0.1% (vs current 2-5%)
- **Login Success**: >99.5% (vs current intermittent failures)

## Next Steps
1. Create AWS account if not exists
2. Review and approve this plan
3. Start Phase 1 implementation
4. Test new features in AWS environment
