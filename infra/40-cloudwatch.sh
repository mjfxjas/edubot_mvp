#!/usr/bin/env bash
# CloudWatch dashboard + log retention for edubot-api-fn
# idempotent; safe to re-run
set -eo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
[ -f "$HERE/00-variables.sh" ] && . "$HERE/00-variables.sh"

# Allow missing vars; set sane defaults, then re-enable nounset
set +u
PROJECT="${PROJECT:-edubot-mvp}"
REGION="${REGION:-us-east-1}"
ACCOUNT="${ACCOUNT:-$(aws sts get-caller-identity --query Account --output text)}"
FN_NAME="${FN_NAME:-edubot-api-fn}"
DASHBOARD_NAME="${DASHBOARD_NAME:-EduBot-MVP}"
LOG_GROUP="/aws/lambda/${FN_NAME}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
set -u

echo "Project: $PROJECT"
echo "Region:  $REGION"
echo "Account: $ACCOUNT"
echo "Lambda:  $FN_NAME"
echo

# 1) Dashboard JSON (uses $REGION/$FN_NAME injected below)
cat > /tmp/dashboard.json <<JSON
{
  "widgets": [
    {
      "type": "metric", "x": 0, "y": 0, "width": 12, "height": 6,
      "properties": {
        "title": "Lambda API Invocations & Errors",
        "region": "$REGION",
        "metrics": [
          [ "AWS/Lambda", "Invocations", "FunctionName", "$FN_NAME", { "stat": "Sum" } ],
          [ ".", "Errors", ".", ".", { "stat": "Sum", "yAxis": "right" } ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "period": 300
      }
    },
    {
      "type": "metric", "x": 0, "y": 6, "width": 12, "height": 6,
      "properties": {
        "title": "Lambda Duration (p95)",
        "region": "$REGION",
        "metrics": [
          [ "AWS/Lambda", "Duration", "FunctionName", "$FN_NAME", { "stat": "p95" } ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "period": 300
      }
    }
  ]
}
JSON

echo "==> Creating/Updating CloudWatch dashboard: $DASHBOARD_NAME"
aws cloudwatch put-dashboard \
  --dashboard-name "$DASHBOARD_NAME" \
  --dashboard-body "file:///tmp/dashboard.json" >/dev/null

# 2) Log retention
echo "==> Setting log retention ($RETENTION_DAYS days) on $LOG_GROUP"
aws logs put-retention-policy \
  --log-group-name "$LOG_GROUP" \
  --retention-in-days "$RETENTION_DAYS" >/dev/null || true

echo
echo "==== CloudWatch ready ===="
echo "Dashboard: https://$REGION.console.aws.amazon.com/cloudwatch/home?region=$REGION#dashboards:name=$DASHBOARD_NAME"
echo "Log group: $LOG_GROUP (retention: ${RETENTION_DAYS}d)"
