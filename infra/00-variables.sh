#!/bin/bash

# ===== Project Variables =====
PROJECT_NAME="edubot-mvp"
AWS_REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# ===== Resource Names =====
S3_BUCKET="${PROJECT_NAME}-private-bucket-${ACCOUNT_ID}"
KMS_KEY_ALIAS="alias/${PROJECT_NAME}-kms"

echo "Project: $PROJECT_NAME"
echo "Region:  $AWS_REGION"
echo "Account: $ACCOUNT_ID"
echo "Bucket:  $S3_BUCKET"
echo "KMS Key: $KMS_KEY_ALIAS"
