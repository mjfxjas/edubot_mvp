#!/usr/bin/env python3
"""Simple test runner for EduBot - no pytest required"""

import sys
import os
import unittest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'api'))

# Set required env vars for testing
os.environ['CURRICULUM_BUCKET'] = 'test-bucket'

class TestEduBot(unittest.TestCase):
    
    def setUp(self):
        import handler
        self.handler = handler
    
    def test_validate_question(self):
        """Test question validation"""
        # Valid question
        self.assertEqual(self.handler._validate_question("What is AI?"), "What is AI?")
        
        # Invalid questions
        self.assertIsNone(self.handler._validate_question(""))
        self.assertIsNone(self.handler._validate_question("hi"))
        
        # Long question truncation
        long_q = "x" * 1500
        result = self.handler._validate_question(long_q)
        self.assertEqual(len(result), 1000)
    
    def test_parse_body(self):
        """Test request body parsing"""
        # JSON body
        event = {"body": '{"question": "test"}'}
        result = self.handler._parse_body(event)
        self.assertEqual(result["question"], "test")
        
        # Empty body
        event = {"body": ""}
        result = self.handler._parse_body(event)
        self.assertEqual(result, {})
    
    def test_health_endpoint(self):
        """Test health endpoint"""
        event = {"httpMethod": "GET", "path": "/health"}
        result = self.handler.lambda_handler(event, None)
        
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('ok', result['body'])

if __name__ == '__main__':
    print("Running EduBot tests...")
    unittest.main(verbosity=2)