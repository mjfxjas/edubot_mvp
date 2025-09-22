# lambda/app/ask_handler.py
import os
import json
import base64
import boto3
from urllib.parse import unquote_plus

# ---- Globals (init once per container) ----
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
CURRICULUM_BUCKET = os.environ["CURRICULUM_BUCKET"]
INDEX_PREFIX = os.environ.get("INDEX_PREFIX", "indexes/philosophy/sections/")
TOP_K = int(os.environ.get("TOP_K", "5"))
BEDROCK_MODEL = os.environ.get("BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")

s3 = boto3.client("s3", region_name=AWS_REGION)
brt = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# ---- Utilities ----
def ok(body: dict, code: int = 200):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}

def bad_request(msg: str, code: int = 400):
    return ok({"error": msg}, code)

def parse_event_body(event):
    """API Gateway/Lambda Function URL compatible body parser."""
    body = event.get("body", "")
    if not body:
        return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    # Some clients URL-encode; be forgiving
    try:
        if "%" in body:
            body = unquote_plus(body)
    except Exception:
        pass
    try:
        return json.loads(body)
    except Exception:
        # last resort: raw string
        return {"raw": body}

def list_index_objects(prefix: str, limit: int = 500):
    """List index jsons under S3 prefix (non-recursive)."""
    keys = []
    kwargs = {"Bucket": CURRICULUM_BUCKET, "Prefix": prefix}
    while True:
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            if obj["Key"].endswith(".json"):
                keys.append(obj["Key"])
                if len(keys) >= limit:
                    return keys
        token = resp.get("NextContinuationToken")
        if not token:
            break
        kwargs["ContinuationToken"] = token
    return keys

def get_json(key: str):
    obj = s3.get_object(Bucket=CURRICULUM_BUCKET, Key=key)
    return json.loads(obj["Body"].read())

def retrieve_top_k(book_id: str, k: int):
    """
    Minimal retrieval: read json blobs under INDEX_PREFIX; each contains
    fields like { "id", "text", "page_start", "page_end", ... } and possibly a stored score.
    If no score stored, we’ll rank by a simple heuristic: longer chunks first.
    """
    prefix = INDEX_PREFIX
    keys = list_index_objects(prefix, limit=2000)
    items = []
    for key in keys:
        data = get_json(key)
        text = data.get("text", "")
        score = float(data.get("score", 0.0)) or float(len(text)) / 1000.0
        items.append({
            "s3_key": key,
            "section_id": data.get("id") or data.get("section_id") or key.rsplit("/", 1)[-1].replace(".json",""),
            "title": data.get("title") or "section",
            "page_start": data.get("page_start"),
            "page_end": data.get("page_end"),
            "score": round(score, 3),
            "text": text[:8000]  # safety cap per chunk
        })
    items.sort(key=lambda x: x["score"], reverse=True)
    return items[:k]

# ---- Bedrock call ----
def call_bedrock(prompt: str) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "temperature": 0.2,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }
        ],
    }
    resp = brt.invoke_model(
        modelId=BEDROCK_MODEL,
        body=json.dumps(body),
        accept="application/json",
        contentType="application/json",
    )
    payload = json.loads(resp["body"].read())
    # Anthropics on Bedrock returns: {"content":[{"type":"text","text":"..."}], ...}
    parts = [c.get("text","") for c in payload.get("content", []) if c.get("type") == "text"]
    return "".join(parts).strip()

def build_prompt(question: str, contexts: list) -> str:
    """Stitch TOP_K contexts into a grounded prompt."""
    context_blocks = []
    for i, c in enumerate(contexts, 1):
        meta = f"{c.get('title','section')} (pp. {c.get('page_start')}–{c.get('page_end')})  [{c['s3_key']}]"
        context_blocks.append(f"[{i}] {meta}\n{c['text']}\n")
    context_text = "\n\n".join(context_blocks)[:120000]  # global cap

    system_rules = (
        "You are a helpful tutor. Answer ONLY using the provided textbook excerpts. "
        "If the answer is not in the excerpts, say you don’t have enough information."
    )
    prompt = (
        f"{system_rules}\n\n"
        f"QUESTION:\n{question}\n\n"
        f"TEXTBOOK EXCERPTS:\n{context_text}\n\n"
        f"INSTRUCTIONS:\n"
        f"- Cite the excerpt numbers you used like [1], [3].\n"
        f"- Keep it concise (2-6 sentences).\n"
    )
    return prompt

# ---- Router ----
def lambda_handler(event, context):
    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("path") or event.get("rawPath") or "/"

    if method == "GET" and path == "/health":
        return ok({"ok": True, "version": os.environ.get("VERSION", "dev")})

    if method == "POST" and path == "/ask":
        body = parse_event_body(event)
        question = (body.get("question") or "").strip()
        book_id = (body.get("book_id") or "philosophy").strip()

        if not question:
            return bad_request("Missing 'question' in body.")

        # retrieve contexts
        top_k = TOP_K
        contexts = retrieve_top_k(book_id, top_k)

        # build prompt & call model
        prompt = build_prompt(question, contexts)
        answer = call_bedrock(prompt)

        # prepare sources (no raw text)
        sources = [
            {
                "s3_key": c["s3_key"],
                "section_id": c["section_id"],
                "title": c["title"],
                "page_start": c.get("page_start"),
                "page_end": c.get("page_end"),
                "score": c["score"],
            } for c in contexts
        ]

        return ok({
            "question": question,
            "book_id": book_id,
            "answer": answer,
            "sources": sources,
        })

    # default 404
    return ok({"error": f"No route for {method} {path}"}, 404)
