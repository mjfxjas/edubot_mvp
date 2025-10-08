#!/usr/bin/env bash
set -euo pipefail

# Optionally load shared variables (non-fatal if missing)
. ./infra/00-variables.sh 2>/dev/null || true

PROJECT="${PROJECT:-edubot}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
STAGE="${API_STAGE:-prod}"
FN_NAME="${PROJECT}-api-fn"
API_NAME="${API_NAME:-${PROJECT}-api}"
STATEMENT_ID="${PROJECT}-http-api-invoke"

echo "Configuring API Gateway HTTP API for ${FN_NAME}"

ACCOUNT_ID="${ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
FN_ARN=$(aws lambda get-function --function-name "${FN_NAME}" --query 'Configuration.FunctionArn' --output text)

# Create or fetch API
API_ID=$(aws apigatewayv2 get-apis \
  --query "Items[?Name=='${API_NAME}'].ApiId" \
  --output text 2>/dev/null || true)
if [[ -z "${API_ID}" || "${API_ID}" == "None" ]]; then
  API_ID=$(aws apigatewayv2 create-api \
    --name "${API_NAME}" \
    --protocol-type HTTP \
    --description "EduBot HTTP API fronting ${FN_NAME}" \
    --query 'ApiId' \
    --output text)
  echo "Created HTTP API ${API_NAME} (${API_ID})"
else
  echo "Using existing HTTP API ${API_NAME} (${API_ID})"
fi

# Create or fetch Lambda integration
INTEGRATION_ID=$(aws apigatewayv2 get-integrations --api-id "${API_ID}" \
  --query "Items[?IntegrationUri=='${FN_ARN}'].IntegrationId" \
  --output text 2>/dev/null || true)
if [[ -z "${INTEGRATION_ID}" || "${INTEGRATION_ID}" == "None" ]]; then
  INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --api-id "${API_ID}" \
    --integration-type AWS_PROXY \
    --integration-uri "${FN_ARN}" \
    --payload-format-version 2.0 \
    --timeout-in-millis 10000 \
    --query 'IntegrationId' \
    --output text)
  echo "Created integration ${INTEGRATION_ID}"
else
  echo "Using existing integration ${INTEGRATION_ID}"
fi

ensure_route () {
  local route_key="$1"
  local existing
  existing=$(aws apigatewayv2 get-routes --api-id "${API_ID}" \
    --query "Items[?RouteKey=='${route_key}'].RouteId" \
    --output text 2>/dev/null || true)
  if [[ -z "${existing}" || "${existing}" == "None" ]]; then
    aws apigatewayv2 create-route \
      --api-id "${API_ID}" \
      --route-key "${route_key}" \
      --target "integrations/${INTEGRATION_ID}" >/dev/null
    echo "Created route ${route_key}"
  else
    echo "Route ${route_key} already exists"
  fi
}

ensure_route "GET /health"
ensure_route "GET /indexes"
ensure_route "POST /ask"

# Create or update stage
STAGE_EXISTS=$(aws apigatewayv2 get-stage --api-id "${API_ID}" --stage-name "${STAGE}" \
  --query 'StageName' --output text 2>/dev/null || true)
if [[ "${STAGE_EXISTS}" == "${STAGE}" ]]; then
  aws apigatewayv2 update-stage \
    --api-id "${API_ID}" \
    --stage-name "${STAGE}" \
    --auto-deploy >/dev/null
  echo "Updated stage ${STAGE} (auto-deploy enabled)"
else
  aws apigatewayv2 create-stage \
    --api-id "${API_ID}" \
    --stage-name "${STAGE}" \
    --auto-deploy >/dev/null
  echo "Created stage ${STAGE}"
fi

# Allow API Gateway to invoke Lambda (ignore if already present)
SOURCE_ARN="arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*/*/*"
if ! aws lambda add-permission \
  --function-name "${FN_NAME}" \
  --statement-id "${STATEMENT_ID}" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "${SOURCE_ARN}" >/dev/null 2>&1; then
  echo "Lambda permission ${STATEMENT_ID} already exists or could not be added (continuing)"
fi

BASE_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com/${STAGE}"
echo "HTTP API ready at: ${BASE_URL}"
