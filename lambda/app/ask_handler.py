import os, json, math, re, time, boto3
from urllib.parse import unquote_plus

S3          = boto3.client("s3")
BUCKET      = os.environ["CURRICULUM_BUCKET"]                 # e.g. edubot-mvp-...-curriculum
BOOK_ID     = os.environ.get("BOOK_ID", "philosophy")         # default for dev
INDEX_PREFIX= os.environ.get("INDEX_PREFIX", f"indexes/{BOOK_ID}/sections/")
MAX_OBJS    = int(os.environ.get("MAX_SECTIONS", "200"))      # cap read cost/time
TOP_K       = int(os.environ.get("TOP_K", "5"))

# ---------------- text utils ----------------
TOKEN_RE = re.compile(r"[A-Za-z0-9']+")
def tokenize(s: str):
    return [t.lower() for t in TOKEN_RE.findall(s)]

def bm25_score(query_tokens, doc_tokens, avgdl, k1=1.2, b=0.75):
    # precompute tf and dl
    tf = {}
    for t in doc_tokens:
        tf[t] = tf.get(t, 0) + 1
    dl = len(doc_tokens)
    # idf via query-only approx (no corpus DF); use pseudo-idf that favors matches
    # If you later keep DF stats in toc.json, swap this for real idf.
    scores = 0.0
    for q in query_tokens:
        f = tf.get(q, 0)
        if f == 0:
            continue
        idf = 1.5  # constant “presence boost”
        denom = f + k1 * (1 - b + b * (dl / (avgdl or 1)))
        scores += idf * (f * (k1 + 1)) / (denom or 1)
    return scores

def best_excerpt(text: str, query_tokens, window_chars=320):
    # return a short excerpt centered around first hit
    text_lc = text.lower()
    hit_pos = min([text_lc.find(q) for q in set(query_tokens) if q in text_lc] or [-1])
    if hit_pos < 0:
        return text[:window_chars].strip()
    start = max(0, hit_pos - window_chars // 3)
    end   = min(len(text), start + window_chars)
    return text[start:end].strip()

# ---------------- s3 helpers ----------------
def list_section_keys(bucket: str, prefix: str, limit: int):
    keys = []
    continuation = None
    while True:
        kw = dict(Bucket=bucket, Prefix=prefix, MaxKeys=min(1000, limit - len(keys)))
        if continuation:
            kw["ContinuationToken"] = continuation
        resp = S3.list_objects_v2(**kw)
        for o in resp.get("Contents", []):
            if o["Key"].endswith(".json"):
                keys.append(o["Key"])
                if len(keys) >= limit:
                    return keys
        if not resp.get("IsTruncated"):
            break
        continuation = resp.get("NextContinuationToken")
    return keys

def get_json(bucket: str, key: str):
    body = S3.get_object(Bucket=bucket, Key=key)["Body"].read()
    return json.loads(body)

# ---------------- handler ----------------
def handler(event, context):
    t0 = time.time()
    try:
        if event.get("httpMethod") == "GET" and event.get("path", "").endswith("/health"):
            return _resp(200, {"ok": True, "version": os.environ.get("VERSION", "dev")})

        body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64
            body = base64.b64decode(body).decode("utf-8", errors="ignore")
        payload = json.loads(body)
        question = (payload.get("question") or "").strip()
        book_id  = payload.get("book_id", BOOK_ID)

        if not question:
            return _resp(400, {"error": "Missing 'question'."})

        prefix = f"indexes/{book_id}/sections/"
        keys = list_section_keys(BUCKET, prefix, MAX_OBJS)
        if not keys:
            return _resp(404, {"error": f"No index sections under s3://{BUCKET}/{prefix}"})

        # load docs (cap for latency)
        docs = []
        total_tokens = 0
        for k in keys:
            j = get_json(BUCKET, k)
            txt = (j.get("text") or "")[:8000]  # safety cutoff per section
            toks = tokenize(txt)
            docs.append((k, j, toks))
            total_tokens += len(toks)
        avgdl = (total_tokens / max(1, len(docs)))

        q_tokens = tokenize(question)
        scored = []
        for k, j, toks in docs:
            score = bm25_score(q_tokens, toks, avgdl)
            if score > 0:
                scored.append((score, k, j, toks))
        scored.sort(reverse=True, key=lambda x: x[0])
        top = scored[:TOP_K] if scored else []

        # build answer
        sources = []
        answer_bits = []
        for score, key, meta, toks in top:
            excerpt = best_excerpt(meta["text"], q_tokens)
            answer_bits.append(excerpt)
            sources.append({
                "s3_key": key,
                "section_id": meta.get("section_id"),
                "title": meta.get("title"),
                "page_start": meta.get("page_start"),
                "page_end": meta.get("page_end"),
                "score": round(float(score), 3)
            })

        answer = "\n\n---\n\n".join(answer_bits[:3]) if answer_bits else \
                 "I couldn’t find a relevant passage in the indexed sections."

        latency_ms = int((time.time() - t0) * 1000)
        out = {
            "question": question,
            "book_id": book_id,
            "answer": answer,
            "sources": sources,
            "latency_ms": latency_ms
        }
        return _resp(200, out)

    except Exception as e:
        # minimal error surface; logs go to CW
        return _resp(500, {"error": str(e)})

def _resp(code, obj):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(obj)
    }

# AWS entrypoint alias
lambda_handler = handler
