#!/bin/bash
set -euo pipefail

source "$(dirname "$0")/00-variables.sh"

FUNCTION_NAME="${PROJECT_NAME}-api-fn"
ALARM_PREFIX="${PROJECT_NAME}-alarm"

echo "Setting up CloudWatch alarms for $FUNCTION_NAME"

# Error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "${ALARM_PREFIX}-error-rate" \
  --alarm-description "Lambda error rate > 5%" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME"

# Duration alarm  
aws cloudwatch put-metric-alarm \
  --alarm-name "${ALARM_PREFIX}-duration" \
  --alarm-description "Lambda duration > 10s" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Average \
  --period 300 \
  --threshold 10000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME"

echo "CloudWatch alarms created"