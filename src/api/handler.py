import json
import os
import boto3
import time
import logging
from urllib.parse import unquote_plus
import base64
import requests

log = logging.getLogger()
log.setLevel(logging.INFO)

# Environment validation
BUCKET = os.environ.get("CURRICULUM_BUCKET")
if not BUCKET:
    raise ValueError("CURRICULUM_BUCKET environment variable required")

INDEX_PREFIX = os.environ.get("INDEX_PREFIX", "indexes/philosophy/sections/")
TOP_K = int(os.environ.get("TOP_K", "20"))
MODEL_ID = os.environ.get("BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Reuse clients across invocations
s3 = boto3.client("s3")
brt = boto3.client("bedrock-runtime", region_name=AWS_REGION)
bedrock = boto3.client("bedrock", region_name=AWS_REGION)


def _parse_body(event):
    """Parse request body with proper validation"""
    body = event.get("body", "")
    if not body:
        return {}

    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    try:
        if "%" in body:
            body = unquote_plus(body)
    except Exception:
        pass

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"raw": body}


def _validate_question(question):
    """Validate and sanitize question input"""
    if not question or not question.strip():
        return None

    question = question.strip()[:1000]  # Limit length
    if len(question) < 3:
        return None

    return question


def _ok(body, code=200):
    return {"statusCode": code,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body)}


def _health_check():
    """Health check with dependency validation"""
    try:
        # Test S3 connectivity
        s3.head_bucket(Bucket=BUCKET)

        # Test Bedrock connectivity
        bedrock.list_foundation_models()

        return {"ok": True, "version": os.environ.get("VERSION", "dev"), "dependencies": "healthy"}
    except Exception as e:
        log.warning(f"Health check dependency issue: {e}")
        # Still return healthy if basic functionality works
        return {"ok": True, "version": os.environ.get("VERSION", "dev"), "dependencies": "partial"}


def _top_sections(bucket, prefix, k, question=""):
    # Get more sections initially for better coverage
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=k*3)
    keys = [o["Key"] for o in resp.get("Contents", [])]
    
    # Fetch all sections
    all_sections = []
    for key in keys:
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            section = json.loads(obj["Body"].read())
            all_sections.append((key, section))
        except Exception:
            continue
    
    # Simple keyword scoring if question provided
    if question:
        keywords = set(question.lower().split())
        scored = []
        for key, section in all_sections:
            text = (section.get("text") or "").lower()
            score = sum(1 for kw in keywords if kw in text and len(kw) > 3)
            scored.append((score, key, section))
        scored.sort(reverse=True)
        # Take top k by score, but ensure we get at least some early sections
        top_scored = scored[:k-2] if len(scored) > k else scored
        early_sections = [(0, k, s) for k, s in all_sections[:2]]
        combined = early_sections + top_scored
        return [k for _, k, _ in combined[:k]], [s for _, _, s in combined[:k]]
    
    # Fallback: just return first k
    return keys[:k], [s for _, s in all_sections[:k]]


def _ask_with_gemini(question, sections):
    """Use Gemini API for answer generation"""
    if not GEMINI_API_KEY:
        return "[No Gemini API key configured]"
    
    context = "\n\n---\n\n".join(
        s.get("text") or s.get("content", "") or "" for s in sections
    )[:30000]

    prompt = f"""Use only the provided curriculum excerpts to answer the question.

Question: {question}

Curriculum Excerpts:
{context}

Instructions:
- Answer based ONLY on the provided excerpts
- If the answer isn't in the excerpts, say you don't have enough information
- Keep the answer concise (2-4 sentences)
- Cite which excerpts you used

Answer:"""

    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 500
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                return data["candidates"][0]["content"]["parts"][0]["text"]
        
        if response.status_code == 429:
            log.warning("Gemini rate limit hit, falling back to Bedrock")
            return None  # Signal to use Bedrock fallback
        
        return f"[Gemini API error: {response.status_code}]"
        
    except Exception as e:
        log.warning(f"Gemini error: {e}, falling back to Bedrock")
        return None  # Signal to use Bedrock fallback


def _ask_with_bedrock(question, sections):
    # Check for mock mode
    if os.environ.get("MOCK_BEDROCK") == "true":
        # Use actual curriculum content for mock answer
        if sections:
            sample_text = sections[0].get('text', '')[:200]
            return f"Based on curriculum content: {sample_text}... [Mock mode - {len(sections)} sections found]"
        return f"Mock answer for: {question}. No curriculum sections found."

    # VERY minimal Claude Haiku invocation with sections concatenated
    context = "\n\n---\n\n".join(
        s.get("text") or s.get("content", "") or "" for s in sections
    )[:12000]  # keep prompt small-ish

    prompt = (
        "Use the provided excerpts only.\n\n"
        f"Question: {question}\n\n"
        f"Excerpts:\n{context}\n\n"
        "Answer:"
    )

    try:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 400,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        }
        resp = brt.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8"),
        )
        body = json.loads(resp["body"].read())
        return "".join(p.get("text", "") for p in body.get("content", []))
    except Exception as e:
        if "ThrottlingException" in str(e) or "Too many tokens" in str(e):
            # Show actual curriculum content when throttled
            if sections:
                sample = sections[0].get('text', '')[:300]
                return f"[Bedrock throttled] From curriculum: {sample}..."
            return f"[Bedrock throttled] Question: {question} - No curriculum data available."
        raise e


def lambda_handler(event, context):
    request_id = context.aws_request_id if context else "local"
    log.info(f"Request {request_id} started")
    
    try:
        # Handle both API Gateway and Function URL formats
        if "requestContext" in event and "http" in event["requestContext"]:
            # Function URL format
            path = event["requestContext"]["http"]["path"]
            method = event["requestContext"]["http"]["method"]
        else:
            # API Gateway format
            path = (event or {}).get("path") or (event or {}).get("rawPath") or "/"
            method = (event or {}).get("httpMethod", "GET")

        # /health
        if path == "/health" and method == "GET":
            return _ok(_health_check())

        # /indexes
        if path == "/indexes" and method == "GET":
            resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="indexes/", MaxKeys=100)
            keys = [o["Key"] for o in resp.get("Contents", [])]
            return _ok({"bucket": BUCKET, "prefix": "indexes/", "count": len(keys), "keys": keys})

        # /ask
        if path == "/ask" and method == "POST":
            t_start = time.time()

            body = _parse_body(event)
            question = _validate_question(body.get("question", ""))
            book_id = body.get("book_id", "philosophy")

            if not question:
                return _ok({"error": "Invalid or missing question"}, 400)

            # Build index prefix based on book_id
            book_index_prefix = f"indexes/{book_id}/sections/"

            # Load and process
            keys, sections = _top_sections(BUCKET, book_index_prefix, TOP_K, question)
            
            # Use Gemini if API key available, otherwise Bedrock
            if GEMINI_API_KEY:
                answer = _ask_with_gemini(question, sections)
                # Fallback to Bedrock if Gemini rate limited
                if answer is None:
                    answer = _ask_with_bedrock(question, sections)
            else:
                answer = _ask_with_bedrock(question, sections)

            duration = int((time.time() - t_start) * 1000)
            log.info(f"Request {request_id} completed in {duration}ms")

            return _ok({
                "question": question,
                "book_id": book_id,
                "answer": answer,
                "sources": [{"s3_key": k} for k in keys],
                "duration_ms": duration
            })

        return _ok({"message": "Use /health, /indexes or /ask"}, 404)

    except Exception as e:
        log.error(f"Request {request_id} failed: {e}")
        return _ok({"error": "Internal server error"}, 500)
