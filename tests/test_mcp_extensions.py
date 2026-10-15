import sys
import types
import unittest
from unittest.mock import patch

from nexus.mcp_extensions import load_mcp_extensions


class DummyMCP:
    pass


class McpExtensionLoaderTests(unittest.TestCase):
    def test_no_configured_extensions_preserves_builtin_only_mode(self):
        with patch.dict("os.environ", {"NEXUS_MCP_EXTENSION_MODULES": ""}):
            self.assertEqual(load_mcp_extensions(DummyMCP(), lambda fn: fn), [])

    def test_registry_scales_without_arbitrary_extension_count_cap(self):
        modules = {}
        registered = []
        names = [f"test_nexus_extension_{index}" for index in range(25)]
        for name in names:
            module = types.ModuleType(name)
            module.register_mcp_tools = (
                lambda mcp, tracker, module_name=name:
                registered.append(module_name)
            )
            modules[name] = module
        with patch.dict(sys.modules, modules):
            loaded = load_mcp_extensions(DummyMCP(), lambda fn: fn, names)
        self.assertEqual(loaded, names)
        self.assertEqual(registered, names)

    def test_duplicate_module_configuration_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "Duplicate module"):
            load_mcp_extensions(DummyMCP(), lambda fn: fn, "example.tools, example.tools")

    def test_missing_registration_entrypoint_fails_closed(self):
        module = types.ModuleType("test_nexus_extension_without_entrypoint")
        with patch.dict(sys.modules, {module.__name__: module}):
            with self.assertRaisesRegex(RuntimeError, "must define register_mcp_tools"):
                load_mcp_extensions(DummyMCP(), lambda fn: fn, [module.__name__])

    def test_import_failure_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "Unable to import configured MCP extension"):
            load_mcp_extensions(DummyMCP(), lambda fn: fn, ["no_such_nexus_extension_module"])


if __name__ == "__main__":
    unittest.main()
