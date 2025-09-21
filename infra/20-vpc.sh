#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/00-variables.sh"

# Names
VPC_NAME="${PROJECT_NAME}-vpc"
SUBNET_NAME="${PROJECT_NAME}-subnet"
SG_NAME="${PROJECT_NAME}-sg"
RT_NAME="${PROJECT_NAME}-rt"

echo "==> Creating VPC: $VPC_NAME in $AWS_REGION"

# 1) VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --query Vpc.VpcId --output text)
aws ec2 create-tags --resources "$VPC_ID" --tags Key=Name,Value="$VPC_NAME"
echo "VPC: $VPC_ID"

# 2) Subnet
SUBNET_ID=$(aws ec2 create-subnet \
  --vpc-id "$VPC_ID" \
  --cidr-block 10.0.1.0/24 \
  --availability-zone "${AWS_REGION}a" \
  --query Subnet.SubnetId --output text)
aws ec2 create-tags --resources "$SUBNET_ID" --tags Key=Name,Value="$SUBNET_NAME"
echo "Subnet: $SUBNET_ID"

# 3) Security Group
SG_ID=$(aws ec2 create-security-group \
  --group-name "$SG_NAME" \
  --description "Security group for $PROJECT_NAME" \
  --vpc-id "$VPC_ID" \
  --query GroupId --output text)
aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" --protocol -1 --cidr 10.0.0.0/16
echo "SG: $SG_ID"

# 4) Route table
RT_ID=$(aws ec2 create-route-table \
  --vpc-id "$VPC_ID" \
  --query RouteTable.RouteTableId --output text)
aws ec2 associate-route-table \
  --route-table-id "$RT_ID" --subnet-id "$SUBNET_ID"
aws ec2 create-tags --resources "$RT_ID" --tags Key=Name,Value="$RT_NAME"
echo "Route table: $RT_ID"
