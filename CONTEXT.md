# EduBot MVP Context

Overview
- Serverless AI tutor running in AWS Lambda (container image) inside a VPC.
- Retrieval is S3 JSON "indexes" built from curriculum PDFs; answer generation uses Bedrock, with optional Gemini fallback.
- Infra is provisioned via shell scripts under infra/.

Key directories
- src/api/: Lambda container handler (`handler.py`) and API logic.
- lambda/app/: alternate zip-style handlers (health/ask).
- tools/: PDF indexer, ECS entrypoint, local utilities, and a signed-request test page.
- infra/: VPC, KMS/S3, IAM, ECR, Lambda, Function URL, and API Gateway scripts.
- policies/: IAM policy templates and generated policies (account-specific).
- docs/: dev journal + screenshots; SECURITY.md for account-specific file guidance.
- data/: seed-manifest for initial curriculum objects.

API behavior (src/api/handler.py)
- GET /health: basic health with dependency probe.
- GET /indexes: list S3 keys under indexes/.
- POST /ask: load top K section JSONs from S3 and build a prompt.
  - Uses Gemini if GEMINI_API_KEY is set, otherwise Bedrock.
  - Returns answer, sources, and duration_ms.

Indexing pipeline
- tools/indexer.py: PDF -> JSON chunks, outputs indexes/<book_id>/sections/*.json + toc.json.
- tools/indexer.Dockerfile + tools/entrypoint.py: ECS/Fargate task that downloads a PDF from S3 and uploads indexes back to S3 (SSE-KMS).
- tools/run_indexer.sh: ECS run-task wrapper.

Infra scripts (infra/)
- 00-variables.sh: project name, account ID, region, bucket, KMS alias.
- 10-kms-and-s3.sh: create KMS key, S3 bucket, TLS-only policy.
- 10-iam.sh: create roles and policies for Lambda/ECS (includes Bedrock invoke + VPC ENI).
- 20-vpc.sh + 30-vpc-endpoints.sh: VPC + S3/KMS endpoints only.
- 34-sg-lambda.sh: Lambda ENI security group.
- 35-ecr.sh: build and push Lambda image to ECR.
- 60-lambda-api.sh: create/update Lambda with image + VPC config.
- 65-lambda-url.sh: create Function URL (AWS_IAM).
- 70-apigateway-http.sh: HTTP API + routes (/health, /indexes, /ask).
- 40-cloudwatch.sh: dashboard + log retention.

Local tools/testing
- tools/client/signed.html + tools/local/serve-creds.*: browser tester using SigV4 with short-lived STS creds.
- event-ask.json, event-health.json: sample Lambda invoke payloads.
- run_tests.py: minimal unittest runner (no pytest).

Core environment variables
- CURRICULUM_BUCKET: required; S3 bucket for indexes/curriculum.
- INDEX_PREFIX: prefix for section JSONs (default indexes/philosophy/sections/).
- TOP_K: number of sections to include.
- BEDROCK_MODEL: Bedrock model ID.
- GEMINI_API_KEY: enables Gemini API path.
- AWS_REGION: region for AWS clients.
- MOCK_BEDROCK=true: mock Bedrock responses in handler.

Notes
- Two handler implementations exist (src/api/handler.py and lambda/app/ask_handler.py); only one is deployed at a time.
- Account-specific artifacts exist (policies/policy-*.json, ecs-*.json, assume-*.json); see SECURITY.md.
