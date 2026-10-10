import unittest
from nexus.evidence import EvidenceFetchError, verify_source_quote

class EvidenceVerificationTests(unittest.TestCase):
    def test_exact_quote_match_passes(self):
        result=verify_source_quote("https://docs.example.com/page","official policy",fetcher=lambda url:"This is the official policy for this service.")
        self.assertEqual(result["method"],"exact normalized quote match")

    def test_quote_mismatch_fails(self):
        with self.assertRaises(EvidenceFetchError):
            verify_source_quote("https://docs.example.com/page","claim not present",fetcher=lambda url:"Different source text.")

    def test_empty_quote_fails(self):
        with self.assertRaises(EvidenceFetchError):
            verify_source_quote("https://docs.example.com/page"," ",fetcher=lambda url:"source")

if __name__ == "__main__":
    unittest.main()
