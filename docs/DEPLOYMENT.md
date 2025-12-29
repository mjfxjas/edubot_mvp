# EduBot Deployment Guide

## Prerequisites
- AWS CLI configured with appropriate permissions
- Docker installed
- Python 3.12+
- Git

## Quick Deploy

### 1. Environment Setup
```bash
cp .env.template .env
# Edit .env with your AWS account details
```

### 2. Infrastructure Deployment
```bash
# Set variables
source infra/00-variables.sh

# Create KMS and S3
./infra/10-kms-and-s3.sh

# Create IAM roles and policies  
./infra/10-iam.sh

# Create VPC (optional)
./infra/20-vpc.sh

# Create Lambda function
./infra/60-lambda-api.sh

# Set up monitoring
./infra/45-monitoring.sh
```

### 3. Build and Deploy Code
```bash
# Build Docker image
docker buildx build --platform linux/amd64 \
  -f src/api/Dockerfile \
  -t $ECR_REGISTRY/$ECR_REPOSITORY:latest --push .

# Update Lambda function
aws lambda update-function-code \
  --function-name edubot-mvp-api-fn \
  --image-uri "$ECR_REGISTRY/$ECR_REPOSITORY:latest"
```

### 4. Upload Curriculum Data
```bash
# Process PDF and upload indexes
python tools/indexer.py \
  --pdf /path/to/textbook.pdf \
  --book-id philosophy \
  --subject philosophy \
  --s3-bucket $CURRICULUM_BUCKET
```

### 5. Test Deployment
```bash
# Test health endpoint
aws lambda invoke --function-name edubot-mvp-api-fn \
  --payload fileb://event-health.json health.json

# Test ask endpoint  
aws lambda invoke --function-name edubot-mvp-api-fn \
  --payload fileb://event-ask.json ask.json
```

## Environment Variables

Required Lambda environment variables:
- `CURRICULUM_BUCKET`: S3 bucket name
- `INDEX_PREFIX`: S3 prefix for indexes
- `TOP_K`: Number of sections to retrieve (default: 5)
- `BEDROCK_MODEL`: Model ID (default: claude-3-haiku)
- `AWS_REGION`: AWS region

## Troubleshooting

### Common Issues
1. **Permission denied**: Check IAM roles have correct policies attached
2. **VPC timeout**: Ensure VPC endpoints configured for Bedrock/S3
3. **Image not found**: Verify ECR repository exists and image pushed
4. **No curriculum data**: Run indexer to process and upload PDFs

### Logs
```bash
# View Lambda logs
aws logs tail /aws/lambda/edubot-mvp-api-fn --follow

# View specific error
aws logs filter-log-events \
  --log-group-name /aws/lambda/edubot-mvp-api-fn \
  --filter-pattern "ERROR"
```

## Production Considerations
- Enable API Gateway with authentication
- Set up CloudWatch alarms and notifications
- Implement request throttling
- Use multiple AZs for high availability
- Enable S3 versioning and backup