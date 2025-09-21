#!/usr/bin/env bash
set -euo pipefail

# Load shared variables (PROJECT_NAME, AWS_REGION, ACCOUNT_ID, S3_BUCKET, KMS_KEY_ALIAS)
source "$(dirname "$0")/00-variables.sh"

echo "==> Using account: $ACCOUNT_ID, region: $AWS_REGION"
echo "==> Target bucket: $S3_BUCKET"
echo "==> KMS alias:     $KMS_KEY_ALIAS"

# 1) Create (or find) a CMK and alias for SSE-KMS
KEY_ID=$(aws kms create-key \
  --description "${PROJECT_NAME} CMK for S3 SSE-KMS" \
  --query KeyMetadata.KeyId --output text 2>/dev/null || true)

if [[ -z "${KEY_ID:-}" ]]; then
  # If create-key failed because one exists, look it up via the alias (in case it's already there)
  KEY_ID=$(aws kms list-aliases \
    --query "Aliases[?AliasName=='${KMS_KEY_ALIAS}'].TargetKeyId" --output text || true)
fi

# Create alias if it doesn't exist yet
aws kms create-alias --alias-name "$KMS_KEY_ALIAS" --target-key-id "$KEY_ID" 2>/dev/null || true

KEY_ARN=$(aws kms describe-key --key-id "$KEY_ID" --query KeyMetadata.Arn --output text)
echo "==> KMS Key ARN: $KEY_ARN"

# 2) Create the S3 bucket (idempotent-ish)
if aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
  echo "==> Bucket exists, skipping create."
else
  if [[ "$AWS_REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$S3_BUCKET"
  else
    aws s3api create-bucket --bucket "$S3_BUCKET" \
      --create-bucket-configuration LocationConstraint="$AWS_REGION"
  fi
  echo "==> Bucket created."
fi

# 3) Block all public access at bucket level
aws s3api put-public-access-block --bucket "$S3_BUCKET" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
echo "==> Public access blocked."

# 4) Enforce SSE-KMS default encryption
aws s3api put-bucket-encryption --bucket "$S3_BUCKET" \
  --server-side-encryption-configuration "{
    \"Rules\": [{
      \"ApplyServerSideEncryptionByDefault\": {
        \"SSEAlgorithm\": \"aws:kms\",
        \"KMSMasterKeyID\": \"${KEY_ARN}\"
      }
    }]}
  "
echo "==> Default SSE-KMS enabled."

# 5) Deny non-HTTPS (require TLS)
cat > /tmp/tls-only.json <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyInsecureTransport",
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": ["arn:aws:s3:::${S3_BUCKET}", "arn:aws:s3:::${S3_BUCKET}/*"],
    "Condition": {"Bool": {"aws:SecureTransport": "false"}}
  }]
}
POLICY

aws s3api put-bucket-policy --bucket "$S3_BUCKET" --policy file:///tmp/tls-only.json
echo "==> TLS-only bucket policy applied."

echo "==> DONE: KMS + S3 hardened."
echo "Bucket: s3://${S3_BUCKET}"
echo "KMS alias: ${KMS_KEY_ALIAS}"
