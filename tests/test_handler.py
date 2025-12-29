import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'api'))

class TestLambdaHandler(unittest.TestCase):
    
    @patch.dict(os.environ, {
        'CURRICULUM_BUCKET': 'test-bucket',
        'INDEX_PREFIX': 'test-prefix/',
        'TOP_K': '3'
    })
    def setUp(self):
        # Import after setting env vars
        global handler
        import handler
        self.handler = handler
    
    def test_health_endpoint(self):
        event = {"httpMethod": "GET", "path": "/health"}
        context = MagicMock()
        context.aws_request_id = "test-123"
        
        with patch.object(self.handler, 's3') as mock_s3, \
             patch.object(self.handler, 'brt') as mock_brt:
            
            mock_s3.head_bucket.return_value = {}
            mock_brt.list_foundation_models.return_value = {}
            
            result = self.handler.lambda_handler(event, context)
            
            self.assertEqual(result['statusCode'], 200)
            body = json.loads(result['body'])
            self.assertTrue(body['ok'])
    
    def test_validate_question(self):
        # Valid question
        self.assertEqual(self.handler._validate_question("What is AI?"), "What is AI?")
        
        # Empty/invalid questions
        self.assertIsNone(self.handler._validate_question(""))
        self.assertIsNone(self.handler._validate_question("  "))
        self.assertIsNone(self.handler._validate_question("hi"))
        
        # Long question truncation
        long_q = "x" * 1500
        result = self.handler._validate_question(long_q)
        self.assertEqual(len(result), 1000)
    
    def test_parse_body(self):
        # JSON body
        event = {"body": '{"question": "test"}'}
        result = self.handler._parse_body(event)
        self.assertEqual(result["question"], "test")
        
        # Empty body
        event = {"body": ""}
        result = self.handler._parse_body(event)
        self.assertEqual(result, {})
        
        # Invalid JSON
        event = {"body": "invalid json"}
        result = self.handler._parse_body(event)
        self.assertEqual(result["raw"], "invalid json")

if __name__ == '__main__':
    unittest.main()