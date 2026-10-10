import json
import unittest
from types import SimpleNamespace
from nexus.openai_adapter import OpenAIResponsesWorker, OpenAIWorkerError

class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []
    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.outputs.pop(0)

class FakeClient:
    def __init__(self, outputs):
        self.responses = FakeResponses(outputs)

def response(output, text=""):
    return SimpleNamespace(output=output, output_text=text, id="resp-test")

def call(name, args, call_id="call-1"):
    return SimpleNamespace(type="function_call", name=name, arguments=json.dumps(args), call_id=call_id)

TOOL = [{"type":"function","name":"read_status","description":"read status",
         "parameters":{"type":"object","properties":{},"additionalProperties":False}}]

class OpenAIWorkerTests(unittest.TestCase):
    def test_policy_allow_executes_registered_tool(self):
        client=FakeClient([response([call("read_status", {})]), response([], "done")])
        seen=[]
        worker=OpenAIResponsesWorker(model="test-model", client=client)
        result=worker.run(prompt="status", tools=TOOL,
            tool_handlers={"read_status":lambda args:{"state":"INTAKE"}},
            policy_check=lambda name,args:{"decision":"ALLOW","reason_code":"READ_ALLOWED"},
            record=lambda **r:seen.append(r))
        self.assertEqual(result["output_text"],"done")
        self.assertEqual(result["tool_calls"][0]["outcome"],"executed")
        self.assertTrue(any(x["record_type"]=="decision" for x in seen))

    def test_policy_deny_never_calls_handler(self):
        client=FakeClient([response([call("read_status", {})]), response([], "blocked")])
        called=[]
        worker=OpenAIResponsesWorker(model="test-model", client=client)
        result=worker.run(prompt="status", tools=TOOL,
            tool_handlers={"read_status":lambda args:called.append(args)},
            policy_check=lambda name,args:{"decision":"BLOCK","reason_code":"NO_PERMISSION"})
        self.assertEqual(called,[])
        self.assertEqual(result["policy_decisions"][0]["reason_code"],"NO_PERMISSION")

    def test_unregistered_tool_is_blocked(self):
        client=FakeClient([response([call("other_tool", {})]), response([], "no")])
        called=[]
        worker=OpenAIResponsesWorker(model="test-model", client=client)
        worker.run(prompt="go", tools=TOOL,
            tool_handlers={"other_tool":lambda args:called.append(args)},
            policy_check=lambda n,a:{"decision":"ALLOW"})
        self.assertEqual(called,[])

    def test_policy_exception_fails_closed(self):
        client=FakeClient([response([call("read_status", {})]), response([], "blocked")])
        called=[]
        worker=OpenAIResponsesWorker(model="test-model", client=client)
        result=worker.run(prompt="status", tools=TOOL,
            tool_handlers={"read_status":lambda args:called.append(args)},
            policy_check=lambda n,a:(_ for _ in ()).throw(RuntimeError("policy failure")))
        self.assertEqual(called,[])
        self.assertEqual(result["policy_decisions"][0]["reason_code"],"POLICY_CHECK_FAILED")

    def test_tool_round_limit(self):
        client=FakeClient([response([call("read_status", {}, f"call-{i}")]) for i in range(3)])
        worker=OpenAIResponsesWorker(model="test-model", client=client, max_tool_rounds=1)
        with self.assertRaises(OpenAIWorkerError):
            worker.run(prompt="status", tools=TOOL, tool_handlers={"read_status":lambda a:{}},
                policy_check=lambda n,a:{"decision":"ALLOW"})

    def test_rejects_blank_prompt(self):
        worker=OpenAIResponsesWorker(model="test-model", client=FakeClient([]))
        with self.assertRaises(ValueError):
            worker.run(prompt=" ", tools=[], tool_handlers={}, policy_check=lambda n,a:{"decision":"ALLOW"})

if __name__ == "__main__":
    unittest.main()
