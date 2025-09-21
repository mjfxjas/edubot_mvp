#!/usr/bin/env bash
set -euo pipefail
: "${VPC_ID:?export VPC_ID first (your custom VPC)}"
SG_NAME="sg-edubot-lambda"

LAMBDA_SG_ID="$(aws ec2 create-security-group \
  --group-name "$SG_NAME" \
  --description "Lambda ENI SG" \
  --vpc-id "$VPC_ID" \
  --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$SG_NAME}]" \
  --query GroupId --output text 2>/dev/null || true)"

if [ -z "$LAMBDA_SG_ID" ] || [ "$LAMBDA_SG_ID" = "None" ]; then
  LAMBDA_SG_ID="$(aws ec2 describe-security-groups \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=$SG_NAME" \
    --query "SecurityGroups[0].GroupId" --output text)"
fi

echo "LAMBDA_SG_ID=$LAMBDA_SG_ID"

aws ec2 authorize-security-group-egress \
  --group-id "$LAMBDA_SG_ID" \
  --ip-permissions 'IpProtocol=-1,IpRanges=[{CidrIp=0.0.0.0/0}]' >/dev/null 2>&1 || true
