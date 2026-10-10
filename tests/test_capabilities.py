import unittest
from nexus.capabilities import CAPABILITY_REGISTRY, resolve_optional_tools
from nexus.code_proposal import SUPPORTED_CODE_MODELS

class CapabilityRegistryTests(unittest.TestCase):
    def test_every_capability_has_valid_activation_state(self):
        allowed={"ENABLED","DISABLED","BLOCKED","OUT_OF_SCOPE"}
        self.assertTrue(CAPABILITY_REGISTRY)
        for name,spec in CAPABILITY_REGISTRY.items():
            with self.subTest(capability=name):
                self.assertIn(spec.get("status"),allowed)
                self.assertTrue(spec.get("kind"))
                self.assertTrue(spec.get("risk"))

    def test_web_search_is_limited_to_explicitly_reviewed_models(self):
        spec=CAPABILITY_REGISTRY["web_search"]
        self.assertEqual(spec["status"],"ENABLED")
        self.assertTrue(spec["supported_models"])
        for model in spec["supported_models"]:
            self.assertEqual(resolve_optional_tools(["web_search"],model),[{"type":"web_search"}])
        with self.assertRaisesRegex(ValueError,"not verified"):
            resolve_optional_tools(["web_search"],"unreviewed-model")

    def test_non_enabled_provider_tools_cannot_be_resolved(self):
        for capability in ("file_search","code_interpreter","computer_use","shell","apply_patch"):
            with self.subTest(capability=capability):
                with self.assertRaisesRegex(ValueError,"not enabled"):
                    resolve_optional_tools([capability],"gpt-6-astra")

    def test_code_models_are_allowlisted_separately_from_execution(self):
        self.assertEqual(SUPPORTED_CODE_MODELS,{"gpt-6-astra","gpt-6.1-sol"})
        self.assertNotIn("code_interpreter",SUPPORTED_CODE_MODELS)
        self.assertEqual(CAPABILITY_REGISTRY["code_generation"]["status"],"ENABLED")
        self.assertEqual(CAPABILITY_REGISTRY["code_interpreter"]["status"],"BLOCKED")

if __name__=="__main__":
    unittest.main()
