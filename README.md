# EduBot MVP

**EduBot** is a serverless prototype that delivers a private, school-specific Q&A chatbot.  
It uses AWS Lambda, Bedrock, and S3 to let schools query their own copyrighted or private materials in a secure VPC — without exposing data to the public internet.

This project is primarily a **learning and portfolio build** toward the [AWS Solutions Architect Associate](https://aws.amazon.com/certification/certified-solutions-architect-associate/) certification. It demonstrates hands-on AWS skills, infrastructure orchestration, and applied AI use cases.

## Features

- **Serverless API**  
  Python API packaged into AWS Lambda (container image).

- **Private Q&A**  
  Students can ask questions. Answers are retrieved from school-specific documents (indexes stored in S3).

- **Indexing Pipeline**  
  Local/ECS tool for chunking + embedding curriculum data into per-section JSON indexes.

- **Secure Storage**  
  Buckets and IAM policies restrict access to curriculum and indexes.

- **Monitoring**  
  CloudWatch dashboard shows API health, invocation counts, errors, and latency.

## Architecture 

[ Student Question ]
|
v
API Gateway (planned) → Lambda (edubot-api-fn, containerized Python)
|
v
S3 Bucket(s)
├── Curriculum PDFs / Text
└── JSON Section Indexes

- **Compute:** AWS Lambda (container image built with Docker, pushed to ECR).  
- **Storage:** S3 for curriculum + index data.  
- **Networking:** VPC with subnets & security groups.  
- **IAM:** Minimal-scope roles for Lambda + S3 access.  
- **Monitoring:** CloudWatch metrics + custom dashboard.  

## Repo Structure

edubot_mvp/
├── src/
│   └── api/             # API Lambda (Dockerfile, handler.py, requirements.txt)
├── lambda/
│   └── app/             # ask_handler.py (core Q&A logic)
├── tools/
│   └── indexer.py       # Builds per-section JSON indexes
├── policies/            # IAM policy JSONs
├── docs/
│   └── dev-journal.md   # Build log, notes, screenshots
├── indexes/             # Example generated index files
└── README.md


## Quickstart (Local Dev)

> Pre-reqs: Docker, AWS CLI configured, Python 3.12
# clone repo
git clone https://github.com/YOURNAME/edubot_mvp.git
cd edubot_mvp

# build + push Lambda image
docker buildx build --platform linux/amd64 \
  -f src/api/Dockerfile \
  -t $IMAGE_URI --push .

# update Lambda with new image
aws lambda update-function-code \
  --function-name edubot-api-fn \
  --image-uri "$IMAGE_URI"

# test health endpoint
cat > event-health.json <<'JSON'
{"httpMethod":"GET","path":"/health","isBase64Encoded":false}
JSON

aws lambda invoke --function-name edubot-api-fn \
  --payload fileb://event-health.json health.json \
  && cat health.json | jq


## CloudWatch Dashboard
Custom dashboard: EduBot-MVP
	•	Lambda invocations & errors
	•	Latency (p95)
	•	Topology map of service connections
	•	Logs for request/response inspection

## Security Considerations
	•	All curriculum stored in private S3 buckets
	•	Access limited via IAM role → Lambda only
	•	Runs inside VPC subnets for isolation
	•	No data leaves AWS account

## Roadmap
	•	Add API Gateway for HTTPS access
	•	ECS/Fargate job for indexer.py (currently local)
	•	Integrate Bedrock foundation models for answer synthesis
	•	Terraform/CDK rewrite (infra as code)
	•	Add unit tests & CI/CD pipeline

About
	•	Built by: Jonathan Schimpf
	•	Purpose: Hands-on AWS learning for SAA exam + portfolio
	•	Status: MVP working, expanding
