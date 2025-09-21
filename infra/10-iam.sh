#!/usr/bin/env bash
set -euo pipefail

# ====== CONFIG ======
PROJECT="${PROJECT:-edubot}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${BUCKET:-edubot-corpus}"                # change if yours differs
KMS_KEY_ARN="${KMS_KEY_ARN:-arn:aws:kms:${REGION}:${ACCOUNT}:key/REPLACE-WITH-YOUR-KEY-ID}"

POLICY_DIR="${POLICY_DIR:-policies}"
mkdir -p "${POLICY_DIR}"

# Role names
LAMBDA_ROLE="${PROJECT}-app-lambda"
ECS_TASK_ROLE="${PROJECT}-indexer-ecs"
ECS_EXEC_ROLE="${PROJECT}-indexer-exec"

# Policy names (customer-managed)
APP_POL="${PROJECT}-app-s3-kms"
INDEXER_POL="${PROJECT}-indexer-s3-kms"

# ====== HELPERS ======
role_exists() { aws iam get-role --role-name "$1" >/dev/null 2>&1; }
policy_arn()  { aws iam list-policies --scope Local --query "Policies[?PolicyName=='$1'].Arn | [0]" --output text; }
policy_exists(){ [[ "$(policy_arn "$1")" != "None" ]]; }

create_or_update_policy() {
  local name="$1" file="$2"
  if policy_exists "$name"; then
    local arn; arn="$(policy_arn "$name")"
    echo "Updating policy $name ($arn)"
    aws iam create-policy-version --policy-arn "$arn" --policy-document "file://${file}" --set-as-default >/dev/null
  else
    echo "Creating policy $name"
    aws iam create-policy --policy-name "$name" --policy-document "file://${file}" >/dev/null
  fi
}

attach_policy_once() {
  local role="$1" pol_arn="$2"
  if ! aws iam list-attached-role-policies --role-name "$role" \
      --query "AttachedPolicies[?PolicyArn=='${pol_arn}'] | length(@)" --output text | grep -q '^1$'; then
    aws iam attach-role-policy --role-name "$role" --policy-arn "$pol_arn" >/dev/null
  fi
}

# ====== TRUST POLICIES (generate if missing) ======
LAMBDA_TRUST="${POLICY_DIR}/trust-${PROJECT}-app-lambda.json"
ECS_TRUST="${POLICY_DIR}/trust-${PROJECT}-indexer-ecs.json"

[[ -f "$LAMBDA_TRUST" ]] || cat > "$LAMBDA_TRUST" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "lambda.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
JSON

[[ -f "$ECS_TRUST" ]] || cat > "$ECS_TRUST" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "ecs-tasks.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
JSON

# ====== PERMISSION POLICIES (templated with your BUCKET/KMS) ======
APP_PERMS="${POLICY_DIR}/policy-${PROJECT}-app-s3-kms.json"
INDEXER_PERMS="${POLICY_DIR}/policy-${PROJECT}-indexer-s3-kms.json"

cat > "$APP_PERMS" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3ReadIndexes",
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::${BUCKET}",
        "arn:aws:s3:::${BUCKET}/indexes/*"
      ]
    },
    {
      "Sid": "KmsDecrypt",
      "Effect": "Allow",
      "Action": ["kms:Decrypt","kms:DescribeKey","kms:GenerateDataKey"],
      "Resource": "${KMS_KEY_ARN}"
    },
    {
      "Sid": "Logs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
      "Resource": "*"
    }
  ]
}
JSON

cat > "$INDEXER_PERMS" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3ReadRaw",
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::${BUCKET}",
        "arn:aws:s3:::${BUCKET}/raw/*"
      ]
    },
    {
      "Sid": "S3WriteProcessedAndIndexes",
      "Effect": "Allow",
      "Action": ["s3:PutObject","s3:AbortMultipartUpload","s3:GetBucketLocation","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::${BUCKET}",
        "arn:aws:s3:::${BUCKET}/processed/*",
        "arn:aws:s3:::${BUCKET}/indexes/*"
      ]
    },
    {
      "Sid": "KmsUse",
      "Effect": "Allow",
      "Action": ["kms:Encrypt","kms:Decrypt","kms:GenerateDataKey","kms:DescribeKey"],
      "Resource": "${KMS_KEY_ARN}"
    },
    {
      "Sid": "Logs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
      "Resource": "*"
    }
  ]
}
JSON

# ====== CREATE ROLES ======
if ! role_exists "$LAMBDA_ROLE"; then
  echo "Creating role: $LAMBDA_ROLE"
  aws iam create-role \
    --role-name "$LAMBDA_ROLE" \
    --assume-role-policy-document "file://${LAMBDA_TRUST}" >/dev/null

  # Basic logging for Lambda
  aws iam attach-role-policy --role-name "$LAMBDA_ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole >/dev/null
fi

if ! role_exists "$ECS_TASK_ROLE"; then
  echo "Creating role: $ECS_TASK_ROLE (task role)"
  aws iam create-role \
    --role-name "$ECS_TASK_ROLE" \
    --assume-role-policy-document "file://${ECS_TRUST}" >/dev/null
fi

if ! role_exists "$ECS_EXEC_ROLE"; then
  echo "Creating role: $ECS_EXEC_ROLE (execution role)"
  aws iam create-role \
    --role-name "$ECS_EXEC_ROLE" \
    --assume-role-policy-document "file://${ECS_TRUST}" >/dev/null

  # Standard execution perms: pull from ECR, write logs, get secrets
  aws iam attach-role-policy --role-name "$ECS_EXEC_ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy >/dev/null
fi

# ====== CREATE / UPDATE CUSTOMER-MANAGED POLICIES ======
create_or_update_policy "$APP_POL" "$APP_PERMS"
create_or_update_policy "$INDEXER_POL" "$INDEXER_PERMS"

# ====== ATTACH POLICIES ======
APP_ARN="$(policy_arn "$APP_POL")"
INDEXER_ARN="$(policy_arn "$INDEXER_POL")"

attach_policy_once "$LAMBDA_ROLE" "$APP_ARN"
attach_policy_once "$ECS_TASK_ROLE" "$INDEXER_ARN"

# ====== OUTPUT ======
echo "==== IAM ready ===="
echo "Lambda role:        $LAMBDA_ROLE"
echo "ECS task role:      $ECS_TASK_ROLE"
echo "ECS exec role:      $ECS_EXEC_ROLE"
echo "App policy ARN:     $APP_ARN"
echo "Indexer policy ARN: $INDEXER_ARN"
