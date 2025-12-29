# EduBot MVP Context

Purpose: serverless AI tutor using Bedrock + S3-hosted textbook indexes (RAG-style).

Key paths
- src/api/handler.py: Lambda container entrypoint (function URL/API routes).
- lambda/app/ask_handler.py: alternate Lambda handler (zip-style); overlaps with src/api.
- tools/indexer.py: local PDF -> JSON chunk indexer.
- tools/entrypoint.py: ECS/Fargate entrypoint that downloads PDF from S3 and runs indexer.
- infra/*.sh: AWS provisioning scripts (VPC, KMS/S3, IAM, Lambda, API Gateway).

Runtime flow (container)
- /health: basic health.
- /indexes: lists S3 keys under indexes/ (requires CURRICULUM_BUCKET/BUCKET env).
- /ask: loads top sections from S3, builds prompt, calls Bedrock.

Index layout
- Output: indexes/<book_id>/sections/*.json plus indexes/<book_id>/toc.json.
- Each section JSON includes: book_id, subject, section_id, title, page_start/end, text, source_pdf.

Key environment variables
- CURRICULUM_BUCKET or BUCKET: S3 bucket for curriculum/indexes.
- INDEX_PREFIX: S3 prefix for section JSONs (default indexes/philosophy/sections/).
- TOP_K: number of sections to include in a prompt.
- BEDROCK_MODEL: Bedrock model ID.
- AWS_REGION: region for S3/Bedrock.

Notes
- There are two ask handlers (src/api/handler.py and lambda/app/ask_handler.py); deploy one.
- Retrieval is currently naive (no embeddings); indexes are pre-chunked JSON files.
