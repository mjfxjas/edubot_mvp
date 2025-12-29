# EduBot

**A serverless AI-powered Q&A system for educational institutions**

EduBot provides curriculum-specific answers using retrieval-augmented generation (RAG) with Amazon Bedrock. Students ask questions and receive answers based exclusively on their school's textbooks and course materials.

## Features

- **Curriculum-Based Answers**: Responses drawn only from uploaded course materials
- **Serverless Architecture**: AWS Lambda with container deployment
- **Secure & Private**: All data stays within your AWS account
- **RAG Pipeline**: Intelligent document retrieval + AI generation
- **Production Ready**: CI/CD, monitoring, error handling, and tests

## Architecture

- **API**: Python Lambda function with REST endpoints
- **Storage**: S3 for curriculum documents and processed indexes
- **AI**: Amazon Bedrock (Claude Haiku) for answer generation
- **Security**: IAM roles, VPC isolation, KMS encryption
- **Monitoring**: CloudWatch metrics and custom dashboards
- **Deployment**: GitHub Actions CI/CD pipeline

## Quick Start

### Prerequisites
- AWS CLI configured
- Docker installed
- Python 3.12+

### 1. Deploy Infrastructure
```bash
git clone https://github.com/YOUR_USERNAME/edubot_mvp.git
cd edubot_mvp

# Set up AWS resources
source infra/00-variables.sh
./infra/10-kms-and-s3.sh
./infra/10-iam.sh
./infra/60-lambda-api.sh
```

### 2. Upload Curriculum
```bash
# Process and upload textbooks
python tools/indexer.py \
  --pdf /path/to/textbook.pdf \
  --book-id philosophy \
  --subject philosophy \
  --s3-bucket $CURRICULUM_BUCKET
```

### 3. Test the API
```bash
# Health check
curl https://your-lambda-url/health

# Ask a question
curl -X POST https://your-lambda-url/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is philosophy?", "book_id": "philosophy"}'
```

## API Endpoints

- `GET /health` - System health and dependency status
- `GET /indexes` - List available curriculum indexes
- `POST /ask` - Ask questions based on curriculum

## Development

### Local Testing
```bash
# Set environment
export CURRICULUM_BUCKET=your-bucket-name

# Run tests
python run_tests.py

# Test locally with mock mode
MOCK_BEDROCK=true python -c "
import sys; sys.path.append('src/api')
import handler, json
event = {'httpMethod': 'POST', 'path': '/ask', 'body': json.dumps({'question': 'test'})}
print(handler.lambda_handler(event, None))
"
```

### CI/CD Pipeline
Push to main branch triggers:
1. Automated testing
2. Code quality checks
3. Docker build and ECR push
4. Lambda function update

## Configuration

### Environment Variables
- `CURRICULUM_BUCKET` - S3 bucket for curriculum data
- `INDEX_PREFIX` - S3 prefix for processed indexes
- `TOP_K` - Number of sections to retrieve (default: 5)
- `BEDROCK_MODEL` - AI model ID (default: claude-3-haiku)
- `MOCK_BEDROCK` - Enable mock mode for development

### Security
- All curriculum data encrypted with KMS
- IAM roles with minimal required permissions
- VPC isolation for Lambda function
- No data leaves your AWS account

## Monitoring

- CloudWatch metrics for invocations, errors, and latency
- Custom dashboard for system health
- Structured logging with request tracking
- Automated alerts for error rates and performance

## Production Considerations

- **Scaling**: Lambda auto-scales based on demand
- **Cost**: Pay-per-request pricing model
- **Reliability**: Multi-AZ deployment with AWS managed services
- **Backup**: S3 versioning and cross-region replication
- **Updates**: Blue/green deployments via CI/CD pipeline

## Documentation

- [API Documentation](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Security Considerations](SECURITY.md)

## License

MIT License - see LICENSE file for details.