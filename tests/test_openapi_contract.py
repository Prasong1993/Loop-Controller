import unittest
from pathlib import Path
import yaml
from nexus.version import VERSION

SPEC_PATH=Path(__file__).resolve().parents[1]/"openapi.yaml"

class OpenAPIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))

    def test_openapi_yaml_parses_and_version_matches_runtime(self):
        self.assertIsInstance(self.spec,dict)
        self.assertEqual(self.spec["openapi"],"3.1.0")
        self.assertEqual(self.spec["info"]["version"],VERSION)

    def test_all_controller_endpoints_are_documented(self):
        required={
            "/health":{"get"},
            "/projects":{"post"},
            "/projects/{project_id}/status":{"get"},
            "/tasks":{"post"},
            "/tasks/{task_id}":{"get"},
            "/tasks/{task_id}/dependencies":{"get","post"},
            "/tasks/{task_id}/transition":{"post"},
            "/tasks/{task_id}/verification":{"get","post"},
            "/tasks/{task_id}/checkpoint":{"post"},
            "/tasks/{task_id}/restore":{"post"},
            "/evidence":{"post"},
            "/evidence/verify":{"post"},
            "/projects/{project_id}/audit":{"get"},
            "/records/search":{"get"},
            "/policy/route":{"post"},
            "/ai/plan":{"post"},
            "/ai/code-proposal":{"post"},
            "/ai/run":{"post"},
        }
        for path,methods in required.items():
            with self.subTest(path=path):
                self.assertIn(path,self.spec["paths"])
                for method in methods:
                    self.assertIn(method,self.spec["paths"][path])

    def test_direct_evidence_contract_cannot_mark_verified(self):
        statuses=self.spec["paths"]["/evidence"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]["status"]["enum"]
        self.assertNotIn("VERIFIED",statuses)

    def test_code_proposal_contract_is_explicitly_proposal_only_and_path_scoped(self):
        operation=self.spec["paths"]["/ai/code-proposal"]["post"]
        self.assertIn("proposal",operation["responses"]["200"]["description"].casefold())
        schema=operation["requestBody"]["content"]["application/json"]["schema"]["properties"]["allowed_paths"]
        self.assertEqual(schema["minItems"],1)
        self.assertEqual(schema["maxItems"],20)

if __name__=="__main__": unittest.main()
