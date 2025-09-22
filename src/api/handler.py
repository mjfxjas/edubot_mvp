import json, os, boto3, time, logging

log = logging.getLogger()
log.setLevel(logging.INFO)

BUCKET = os.environ.get("CURRICULUM_BUCKET") or os.environ.get("BUCKET", "")
INDEX_PREFIX = os.environ.get("INDEX_PREFIX", "indexes/philosophy/sections/")
TOP_K = int(os.environ.get("TOP_K", "5"))
MODEL_ID = os.environ.get("BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

s3 = boto3.client("s3")
brt = boto3.client("bedrock-runtime", region_name=AWS_REGION)

def _ok(body, code=200):
    return {"statusCode": code,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body)}

def _timed(label):
    t0 = time.time()
    def done():
        log.info(f"{label} took {int((time.time()-t0)*1000)} ms")
    return done

def _top_sections(bucket, prefix, k):
    # naive: list first K section files under prefix and fetch them
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=k)
    keys = [o["Key"] for o in resp.get("Contents", [])][:k]
    out = []
    for key in keys:
        obj = s3.get_object(Bucket=bucket, Key=key)
        out.append(json.loads(obj["Body"].read()))
    return keys, out

def _ask_with_bedrock(question, sections):
    # VERY minimal Claude Haiku invocation with sections concatenated
    context = "\n\n---\n\n".join(
        s.get("text") or s.get("content","") or "" for s in sections
    )[:12000]  # keep prompt small-ish

    prompt = (
        "Use the provided excerpts only.\n\n"
        f"Question: {question}\n\n"
        f"Excerpts:\n{context}\n\n"
        "Answer:"
    )

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 400,
        "temperature": 0.2,
        "messages": [{"role":"user","content":[{"type":"text","text":prompt}]}],
    }
    resp = brt.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload).encode("utf-8"),
    )
    body = json.loads(resp["body"].read())
    # Claude on Bedrock returns {content:[{type:"text",text:"..."}], ...}
    return "".join(p.get("text","") for p in body.get("content", []))

def lambda_handler(event, context):
    path = (event or {}).get("path") or (event or {}).get("rawPath") or "/"
    method = (event or {}).get("httpMethod","GET")

    # /health
    if path == "/health" and method == "GET":
        return _ok({"ok": True})

    # /indexes (your existing S3 list)
    if path == "/indexes" and method == "GET":
        if not BUCKET:
            return _ok({"error": "BUCKET env var not set"}, 500)
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="indexes/", MaxKeys=100)
        keys = [o["Key"] for o in resp.get("Contents", [])]
        return _ok({"bucket": BUCKET, "prefix": "indexes/", "count": len(keys), "keys": keys})

    # /ask
    if path == "/ask" and method == "POST":
        t_all = time.time()

        # parse
        t = _timed("parse_event")
        body = event.get("body") or "{}"
        if isinstance(body, str):
            body = json.loads(body)
        question = body.get("question","").strip()
        book_id  = body.get("book_id","philosophy")
        t()

        if not question:
            return _ok({"error":"missing 'question'"}, 400)
        if not BUCKET:
            return _ok({"error":"CURRICULUM_BUCKET not set"}, 500)

        # load sections
        t = _timed("load_top_sections")
        keys, sections = _top_sections(BUCKET, INDEX_PREFIX, TOP_K)
        t()

        # bedrock
        t = _timed("bedrock_invoke")
        answer = _ask_with_bedrock(question, sections)
        t()

        # format
        log.info(f"TOTAL took {int((time.time()-t_all)*1000)} ms")
        return _ok({
            "question": question,
            "book_id": book_id,
            "answer": answer,
            "sources": [{"s3_key": k} for k in keys],
        })

    # default
    return _ok({"message": "Use /health, /indexes or /ask"}, 200)
