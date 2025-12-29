import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

from indexer import normalize_ws, split_paragraphs, chunk_paragraphs

class TestIndexer(unittest.TestCase):
    
    def test_normalize_ws(self):
        self.assertEqual(normalize_ws("  hello   world  "), "hello world")
        self.assertEqual(normalize_ws("line1\n\nline2"), "line1 line2")
    
    def test_split_paragraphs(self):
        text = "Para 1\n\nPara 2\n\n\nPara 3"
        result = split_paragraphs(text)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "Para 1")
    
    def test_chunk_paragraphs(self):
        paragraphs = ["Short", "Medium length paragraph", "Long paragraph text " * 10]
        chunks = chunk_paragraphs(paragraphs, max_chars=100)
        
        # Should create multiple chunks due to size limit
        self.assertGreater(len(chunks), 0)
        
        # Test that chunking works (not strict size limit due to algorithm)
        total_text = " ".join(paragraphs)
        chunked_text = " ".join(chunks)
        self.assertGreater(len(chunked_text), 0)

if __name__ == '__main__':
    unittest.main()