#!/usr/bin/env bash
set -euo pipefail
aws ecs run-task \
  --cluster "$CLUSTER" \
  --launch-type FARGATE \
  --platform-version LATEST \
  --task-definition edubot-indexer \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}"
