#!/usr/bin/env bash
set -euo pipefail
. ./infra/00-variables.sh 2>/dev/null || true

PROJECT="${PROJECT:-edubot}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
REPO="${PROJECT}-api"

# create if missing
if ! aws ecr describe-repositories --repository-names "$REPO" >/dev/null 2>&1; then
  aws ecr create-repository --repository-name "$REPO" >/dev/null
  echo "Created ECR repo: $REPO"
fi

aws ecr get-login-password --region "$REGION" \
| docker login --username AWS --password-stdin "${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"

IMAGE="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${REPO}:v0.1"
docker build -t "$REPO:local" -f src/api/Dockerfile .
docker tag "$REPO:local" "$IMAGE"
docker push "$IMAGE"

echo "IMAGE=$IMAGE"
