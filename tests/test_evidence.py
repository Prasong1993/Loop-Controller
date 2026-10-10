import unittest
from nexus.evidence import EvidenceFetchError, verify_source_quote, _validate_public_https_url

class EvidenceVerificationTests(unittest.TestCase):
    def test_exact_quote_match_passes(self):
        result=verify_source_quote("https://docs.example.com/page","official policy",fetcher=lambda url:"This is the official policy for this service.")
        self.assertEqual(result["method"],"exact normalized quote match")

    def test_quote_mismatch_fails(self):
        with self.assertRaises(EvidenceFetchError):
            verify_source_quote("https://docs.example.com/page","claim not present",fetcher=lambda url:"Different source text.")


    def test_non_https_url_is_rejected(self):
        with self.assertRaises(EvidenceFetchError):
            _validate_public_https_url("http://example.com")

    def test_localhost_url_is_rejected_without_fetch(self):
        with self.assertRaises(EvidenceFetchError):
            _validate_public_https_url("https://localhost/private")

    def test_empty_quote_fails(self):
        with self.assertRaises(EvidenceFetchError):
            verify_source_quote("https://docs.example.com/page"," ",fetcher=lambda url:"source")

if __name__ == "__main__":
    unittest.main()
