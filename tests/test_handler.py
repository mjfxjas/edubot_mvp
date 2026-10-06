import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os
import base64
from io import BytesIO

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'api'))

# Set required env vars before importing handler
os.environ['CURRICULUM_BUCKET'] = 'test-bucket'

with patch('boto3.client'):
    import handler

class TestLambdaHandler(unittest.TestCase):
    
    def test_health_endpoint(self):
        event = {"httpMethod": "GET", "path": "/health"}
        context = MagicMock()
        context.aws_request_id = "test-123"
        
        with patch.object(handler, "s3"), patch.object(handler, "bedrock"):
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
        with self.assertRaises(ValueError):
            handler._parse_body(event)

    def test_malformed_requests_return_400_without_aws_calls(self):
        invalid = ["[]", "null", "1", "invalid json", '{"question": 123}',
                   '{"question": ["test"]}', '{"question": "hello", "book_id": "../private"}',
                   '{"question": "hello", "book_id": null}']
        with patch.object(handler, "s3") as client, patch.object(handler, "brt") as model:
            for body in invalid:
                with self.subTest(body=body):
                    response = handler.lambda_handler({"path": "/ask", "httpMethod": "POST", "body": body}, None)
                    self.assertEqual(response["statusCode"], 400)
            client.list_objects_v2.assert_not_called()
            model.invoke_model.assert_not_called()

    def test_percent_encoded_literals_are_preserved_in_json(self):
        self.assertEqual(handler._parse_body({"body": json.dumps({"question": "Explain %20 + 10%"})}),
                         {"question": "Explain %20 + 10%"})

    def test_base64_request_validation(self):
        body = base64.b64encode(b'{"question": "hello"}').decode()
        self.assertEqual(handler._parse_body({"body": body, "isBase64Encoded": True})["question"], "hello")
        response = handler.lambda_handler({"path": "/ask", "httpMethod": "POST", "body": "!invalid!",
                                           "isBase64Encoded": True}, None)
        self.assertEqual(response["statusCode"], 400)

    def test_failed_section_reads_do_not_mislabel_sources(self):
        with patch.object(handler, "s3") as client:
            client.list_objects_v2.return_value = {"Contents": [{"Key": "bad"}, {"Key": "good"}]}
            client.get_object.side_effect = [ValueError("unreadable"), {"Body": BytesIO(b'{"text": "good excerpt"}')}]
            keys, sections = handler._top_sections("bucket", "prefix", 2)
        self.assertEqual(keys, ["good"])
        self.assertEqual(sections, [{"text": "good excerpt"}])

    def test_ranked_sections_have_unique_aligned_sources(self):
        excerpts = ["philosophy introduction", "philosophy basics", "other topic", "philosophy theory"]
        with patch.object(handler, "s3") as client:
            client.list_objects_v2.return_value = {"Contents": [{"Key": str(i)} for i in range(4)]}
            client.get_object.side_effect = [{"Body": BytesIO(json.dumps({"text": text}).encode())} for text in excerpts]
            keys, sections = handler._top_sections("bucket", "prefix", 3, "philosophy")
        self.assertEqual(keys, ["0", "1", "3"])
        self.assertEqual(len(set(keys)), len(keys))
        self.assertEqual([section["text"] for section in sections], [excerpts[int(key)] for key in keys])

if __name__ == '__main__':
    unittest.main()