import json, os, boto3, time

BUCKET = os.environ.get("BUCKET", "")
s3 = boto3.client("s3")

def _ok(body, code=200):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}

def lambda_handler(event, context):
    # basic router
    path = (event or {}).get("rawPath") or (event or {}).get("path") or "/"
    if path == "/health":
        return _ok({"ok": True, "ts": int(time.time())})
    if path == "/indexes":
        if not BUCKET:
            return _ok({"error": "BUCKET env var not set"}, 500)
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="indexes/", MaxKeys=100)
        keys = [o["Key"] for o in resp.get("Contents", [])]
        return _ok({"bucket": BUCKET, "prefix": "indexes/", "count": len(keys), "keys": keys})
    # default
    return _ok({"message": "Use /health or /indexes"}, 200)
