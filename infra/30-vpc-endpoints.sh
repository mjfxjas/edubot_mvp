#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/00-variables.sh"

# Look up IDs (assumes VPC + subnet already created by 20-vpc.sh)
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=${PROJECT_NAME}-vpc" --query "Vpcs[0].VpcId" --output text)
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=${PROJECT_NAME}-subnet" --query "Subnets[0].SubnetId" --output text)
RT_ID=$(aws ec2 describe-route-tables --filters "Name=tag:Name,Values=${PROJECT_NAME}-rt" --query "RouteTables[0].RouteTableId" --output text)
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=${PROJECT_NAME}-sg" --query "SecurityGroups[0].GroupId" --output text)

echo "VPC: $VPC_ID"
echo "Subnet: $SUBNET_ID"
echo "RT: $RT_ID"
echo "SG: $SG_ID"

# 1) S3 Gateway Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id "$VPC_ID" \
  --service-name "com.amazonaws.${AWS_REGION}.s3" \
  --route-table-ids "$RT_ID" \
  --vpc-endpoint-type Gateway

echo "==> S3 Gateway endpoint created."

# 2) KMS Interface Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id "$VPC_ID" \
  --service-name "com.amazonaws.${AWS_REGION}.kms" \
  --vpc-endpoint-type Interface \
  --subnet-ids "$SUBNET_ID" \
  --security-group-ids "$SG_ID"

echo "==> KMS Interface endpoint created."
