#!/usr/bin/env bash
set -euo pipefail
PROJECT="${PROJECT:-edubot}"
FN="${PROJECT}-api-fn"

# create if not exists
URL=$(aws lambda get-function-url-config --function-name "$FN" --query FunctionUrl --output text 2>/dev/null || true)
if [ "$URL" = "None" ] || [ -z "$URL" ]; then
  URL=$(aws lambda create-function-url-config --function-name "$FN" --auth-type AWS_IAM --query FunctionUrl --output text)
  # add invoke permission for your account principals (tighten later as needed)
  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  aws lambda add-permission \
    --function-name "$FN" \
    --action lambda:InvokeFunctionUrl \
    --principal "*" \
    --function-url-auth-type AWS_IAM \
    --statement-id allow-iam-invoke
fi
echo "FUNCTION_URL=$URL"
