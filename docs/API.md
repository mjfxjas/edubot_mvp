# EduBot API Documentation

## Overview
EduBot provides a serverless API for curriculum-based Q&A using Amazon Bedrock and retrieval-augmented generation (RAG).

## Base URL
```
https://your-lambda-url.lambda-url.us-east-1.on.aws/
```

## Authentication
No authentication required for this MVP. In production, implement API keys or IAM-based auth.

## Endpoints

### GET /health
Health check endpoint with dependency validation.

**Response:**
```json
{
  "ok": true,
  "version": "v0.2-sprint2",
  "dependencies": "healthy"
}
```

**Error Response:**
```json
{
  "ok": false,
  "error": "dependency_failure"
}
```

### GET /indexes
List available curriculum indexes.

**Response:**
```json
{
  "bucket": "edubot-curriculum-bucket",
  "prefix": "indexes/",
  "count": 25,
  "keys": ["indexes/philosophy/sections/section-1.json", "..."]
}
```

### POST /ask
Ask a question based on curriculum content.

**Request Body:**
```json
{
  "question": "What is the meaning of life according to Aristotle?",
  "book_id": "philosophy"
}
```

**Response:**
```json
{
  "question": "What is the meaning of life according to Aristotle?",
  "book_id": "philosophy", 
  "answer": "According to Aristotle, the meaning of life is eudaimonia...",
  "sources": [
    {
      "s3_key": "indexes/philosophy/sections/aristotle-ethics.json"
    }
  ],
  "duration_ms": 1250
}
```

**Error Responses:**
```json
{
  "error": "Invalid or missing question"
}
```

## Request Validation
- Questions must be 3-1000 characters
- book_id defaults to "philosophy"
- Requests timeout after 30 seconds

## Rate Limits
No rate limits in MVP. Implement throttling for production.

## Error Codes
- 200: Success
- 400: Bad Request (invalid input)
- 404: Not Found (invalid endpoint)
- 500: Internal Server Error

## Examples

### cURL Examples
```bash
# Health check
curl https://your-url/health

# Ask question
curl -X POST https://your-url/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is philosophy?", "book_id": "philosophy"}'
```

### Python Example
```python
import requests

response = requests.post('https://your-url/ask', json={
    'question': 'What is the categorical imperative?',
    'book_id': 'philosophy'
})

data = response.json()
print(f"Answer: {data['answer']}")
```