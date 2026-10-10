import sys
import types
import unittest
from unittest.mock import patch

from nexus.openai_extensions import OpenAIToolRegistry, load_openai_extensions

def tool(name="read_extension_data"):
    return {"type":"function","name":name,"description":"Read project-scoped extension data",
        "parameters":{"type":"object","properties":{"project_id":{"type":"string"}},
                      "required":["project_id"],"additionalProperties":False},"strict":True}

class OpenAIExtensionTests(unittest.TestCase):
    def test_registers_project_scoped_read_tool(self):
        registry=OpenAIToolRegistry()
        handler=lambda args: {"project_id":args["project_id"]}
        registry.register(tool(),handler)
        self.assertEqual(registry.tools[0]["name"],"read_extension_data")
        self.assertIs(registry.handlers["read_extension_data"],handler)

    def test_rejects_side_effecting_extensions(self):
        with self.assertRaisesRegex(ValueError,"SIDE_EFFECTS_DISABLED"):
            OpenAIToolRegistry().register(tool(),lambda args:None,risk="write")

    def test_rejects_reserved_duplicate_and_invalid_names(self):
        registry=OpenAIToolRegistry()
        with self.assertRaisesRegex(ValueError,"DUPLICATE_TOOL"):
            registry.register(tool("nexus_get_task"),lambda args:None)
        registry.register(tool(),lambda args:None)
        with self.assertRaisesRegex(ValueError,"DUPLICATE_TOOL"):
            registry.register(tool(),lambda args:None)
        with self.assertRaisesRegex(ValueError,"INVALID_TOOL_NAME"):
            OpenAIToolRegistry().register(tool("invalid name"),lambda args:None)

    def test_requires_strict_closed_schema_and_project_scope(self):
        registry=OpenAIToolRegistry()
        bad=tool(); bad["strict"]=False
        with self.assertRaisesRegex(ValueError,"STRICT_MODE"):
            registry.register(bad,lambda args:None)
        bad=tool(); bad["parameters"]["additionalProperties"]=True
        with self.assertRaisesRegex(ValueError,"CLOSED_OBJECT"):
            registry.register(bad,lambda args:None)
        bad=tool(); bad["parameters"]["properties"]={"query":{"type":"string"}}; bad["parameters"]["required"]=["query"]
        with self.assertRaisesRegex(ValueError,"PROJECT_ID_REQUIRED"):
            registry.register(bad,lambda args:None)

    def test_loads_many_trusted_modules_without_fixed_count_cap(self):
        modules={}
        names=[f"test_openai_extension_{i}" for i in range(25)]
        for name in names:
            module=types.ModuleType(name)
            module.register_openai_tools=lambda registry, n=name: registry.register(tool(n.replace("test_openai_extension_","read_")),lambda args:{"ok":True})
            modules[name]=module
        with patch.dict(sys.modules,modules):
            registry=load_openai_extensions(names)
        self.assertEqual(registry.module_names,names)
        self.assertEqual(len(registry.tools),25)

    def test_duplicate_module_config_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError,"Duplicate module"):
            load_openai_extensions("sample.tools,sample.tools")

    def test_missing_entrypoint_and_import_error_fail_closed(self):
        module=types.ModuleType("test_openai_extension_no_entry")
        with patch.dict(sys.modules,{module.__name__:module}):
            with self.assertRaisesRegex(RuntimeError,"must define register_openai_tools"):
                load_openai_extensions([module.__name__])
        with self.assertRaisesRegex(RuntimeError,"Unable to import OpenAI extension"):
            load_openai_extensions(["module_that_does_not_exist_for_nexus"])

if __name__=="__main__": unittest.main()
