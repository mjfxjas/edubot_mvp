#!/usr/bin/env bash
set -euo pipefail
# optional shared vars
. ./infra/00-variables.sh 2>/dev/null || true

PROJECT="${PROJECT:-edubot}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
ROLE_ARN="$(aws iam get-role --role-name ${PROJECT}-app-lambda --query Role.Arn --output text)"

# REQUIRED: set these (env or 00-variables.sh)
: "${PRIVATE_SUBNET_IDS:?comma-separated private subnet ids}"
: "${LAMBDA_SG_ID:?lambda security group in same vpc}"
: "${BUCKET:?target S3 bucket name}"

# Image: use env IMAGE if provided or default to v0.1 in ECR
REPO="${PROJECT}-api"
IMAGE="${IMAGE:-${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${REPO}:v0.1}"

FN="${PROJECT}-api-fn"

if aws lambda get-function --function-name "$FN" >/dev/null 2>&1; then
  echo "Updating $FN to image $IMAGE"
  aws lambda update-function-code --function-name "$FN" --image-uri "$IMAGE" >/dev/null
  aws lambda update-function-configuration \
    --function-name "$FN" \
    --role "$ROLE_ARN" \
    --timeout 10 --memory-size 512 \
    --vpc-config SubnetIds=$(echo "$PRIVATE_SUBNET_IDS" | sed 's/,/ /g'),SecurityGroupIds=$LAMBDA_SG_ID \
    --environment "Variables={BUCKET=$BUCKET}" >/dev/null
else
  echo "Creating $FN"
  aws lambda create-function \
    --function-name "$FN" \
    --package-type Image \
    --code ImageUri="$IMAGE" \
    --role "$ROLE_ARN" \
    --timeout 10 --memory-size 512 \
    --vpc-config SubnetIds=$(echo "$PRIVATE_SUBNET_IDS" | sed 's/,/ /g'),SecurityGroupIds=$LAMBDA_SG_ID \
    --environment "Variables={BUCKET=$BUCKET}" >/dev/null
fi

echo "OK: $FN -> $IMAGE"
