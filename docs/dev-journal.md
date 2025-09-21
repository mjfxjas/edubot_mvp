# Dev Journal – EduBot MVP

## 2025-09-20
- Created base repo structure (docs/, infra/, adr/, screenshots/)
- Committed initial .gitkeep placeholders
- Added screenshot documenting repo structure
- Added dev-journal.md and documented process

Commit: 7927d5c

## 2025-09-20
- Added infra/00-variables.sh for project-wide constants
- Added infra/20-vpc.sh to create private VPC, subnet, SG, route table

Commit: 3f969e2

## 2025-09-20
- Added KMS + S3 hardening script; verified SSE-KMS, public-block, TLS-only

Commit: 5bbcb51


## 2025-09-20
- Added infra/30-vpc-endpoints.sh (creates VPC endpoints for S3 + KMS)

Commit: dcb08d7

## 2025-09-20
- Verified endpoints (available) and S3 route in route table

Commit: 3a79ebb

## 2025-09-21
- Completed hardened storage layer: 
  - S3 bucket: `edubot-mvp-private-bucket-147795258921`
  - KMS key: `alias/edubot-mvp-kms`
  - Policies: BlockPublicAccess, TLS-only, SSE-KMS default

- IAM scaffolding:
  - Roles: `edubot-app-lambda`, `edubot-indexer-ecs`, `edubot-indexer-exec`
  - Customer-managed policies: `edubot-app-s3-kms`, `edubot-indexer-s3-kms`
  - Tested assume-role path (user → role) and validated S3/KMS op

SPRINT 1 Complete: Infrastructure in place and verified working! 




