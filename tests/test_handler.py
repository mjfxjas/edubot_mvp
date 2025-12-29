import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'api'))

# Set required env vars before importing handler
os.environ['CURRICULUM_BUCKET'] = 'test-bucket'

import handler

class TestLambdaHandler(unittest.TestCase):
    
    def test_health_endpoint(self):
        event = {"httpMethod": "GET", "path": "/health"}
        context = MagicMock()
        context.aws_request_id = "test-123"
        
        result = handler.lambda_handler(event, context)
        
        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertTrue(body['ok'])
    
    def test_validate_question(self):
        # Valid question
        self.assertEqual(handler._validate_question("What is AI?"), "What is AI?")
        
        # Empty/invalid questions
        self.assertIsNone(handler._validate_question(""))
        self.assertIsNone(handler._validate_question("  "))
        self.assertIsNone(handler._validate_question("hi"))
        
        # Long question truncation
        long_q = "x" * 1500
        result = handler._validate_question(long_q)
        self.assertEqual(len(result), 1000)
    
    def test_parse_body(self):
        # JSON body
        event = {"body": '{"question": "test"}'}
        result = handler._parse_body(event)
        self.assertEqual(result["question"], "test")
        
        # Empty body
        event = {"body": ""}
        result = handler._parse_body(event)
        self.assertEqual(result, {})
        
        # Invalid JSON
        event = {"body": "invalid json"}
        result = handler._parse_body(event)
        self.assertEqual(result["raw"], "invalid json")

if __name__ == '__main__':
    unittest.main()