"""Meaningful offline checks for the caller-to-harness trust boundary."""
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import MagicMock, patch

from harness_client import bind_session, build_request, invoke, load_profile, sdk_validate


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "sessions.sqlite3"
        self.profile_path = Path(__file__).with_name("profile.dev.json")
        self.profile = load_profile(self.profile_path)

    def test_caller_overrides_are_rejected(self):
        for field in ("model", "systemPrompt", "skills", "tools", "allowedTools", "actorId", "messages", "maxIterations"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                build_request(self.profile, {"message": "hello", field: {}}, str(uuid.uuid4()), "actor")

    def test_tool_blocks_and_nontext_are_rejected(self):
        for message in ({"toolUse": {"name": "shell"}}, ["hello"], "", "x" * 20001):
            with self.subTest(message_type=type(message)), self.assertRaises(ValueError):
                build_request(self.profile, {"message": message}, str(uuid.uuid4()), "actor")

    def test_session_cannot_cross_users(self):
        session, _ = bind_session(self.database, "alice", "knowledge")
        with self.assertRaises(ValueError):
            bind_session(self.database, "bob", "knowledge", session)

    def test_session_cannot_cross_profiles(self):
        session, _ = bind_session(self.database, "alice", "knowledge")
        with self.assertRaises(ValueError):
            bind_session(self.database, "alice", "operations", session)

    def test_same_user_can_resume_after_new_connection(self):
        session, actor = bind_session(self.database, "alice", "knowledge")
        self.assertEqual((session, actor), bind_session(self.database, "alice", "knowledge", session))

    def test_short_session_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            bind_session(self.database, "alice", "knowledge", "short")

    def test_defaults_generate_sdk_valid_bounded_request(self):
        request = build_request(self.profile, {"message": "hello"}, str(uuid.uuid4()), "actor")
        sdk_validate(request)
        self.assertEqual(request["maxIterations"], 12)
        self.assertEqual(request["messages"], [{"role": "user", "content": [{"text": "hello"}]}])
        self.assertNotIn("skills", request)
        self.assertNotIn("model", request)

    def write_modified_profile(self, **changes):
        profile = {**self.profile, **changes}
        path = Path(self.temp.name) / "profile.json"
        path.write_text(json.dumps(profile))
        return path

    def test_broad_or_shell_tools_are_rejected(self):
        for tools in (["*"], ["@builtin"], ["@builtin/shell"], ["@enterprise/read_*"], ["@enterprise/commit_ticket"]):
            with self.subTest(tools=tools), self.assertRaises(ValueError):
                load_profile(self.write_modified_profile(allowedTools=tools))

    def test_production_and_business_write_profiles_are_rejected(self):
        for changes in ({"environment": "production"}, {"businessWritesEnabled": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                load_profile(self.write_modified_profile(**changes))

    def test_raised_or_boolean_limits_are_rejected(self):
        for limits in ({"maxIterations": 13, "timeoutSeconds": 120, "maxTokens": 4096},
                       {"maxIterations": True, "timeoutSeconds": 120, "maxTokens": 4096}):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                load_profile(self.write_modified_profile(limits=limits))

    def test_live_rejects_unresolved_or_wrong_region_arn(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                load_profile(self.profile_path, live=True)
        arn = "arn:aws:bedrock-agentcore:us-west-2:111122223333:harness/Example-AbCdEf0123"
        with patch.dict("os.environ", {"HARNESS_ARN": arn}):
            with self.assertRaises(ValueError):
                load_profile(self.profile_path, live=True)

    def test_named_endpoint_is_required(self):
        with self.assertRaises(ValueError):
            load_profile(self.write_modified_profile(endpointName="DEFAULT"))

    def invoke_events(self, events):
        stream = MagicMock()
        stream.__iter__.return_value = iter(events)
        client = MagicMock()
        client.invoke_harness.return_value = {"stream": stream}
        request = build_request(self.profile, {"message": "hello"}, str(uuid.uuid4()), "actor")
        with patch("boto3.Session") as session:
            session.return_value.client.return_value = client
            result = invoke(self.profile, request)
        stream.close.assert_called_once()
        return result

    def test_raw_reasoning_tool_results_and_metadata_are_not_returned(self):
        result = self.invoke_events([
            {"contentBlockDelta": {"delta": {"reasoningContent": {"text": "private reasoning"}}}},
            {"contentBlockDelta": {"delta": {"toolResult": {"text": "raw tool payload"}}}},
            {"contentBlockDelta": {"delta": {"text": "Grounded answer"}}},
            {"metadata": {"usage": {"inputTokens": 10}, "other": "private telemetry"}},
            {"messageStop": {"stopReason": "end_turn"}},
        ])
        self.assertEqual(result["text"], "Grounded answer")
        self.assertNotIn("private", json.dumps(result))
        self.assertNotIn("raw tool", json.dumps(result))

    def test_incomplete_and_inline_handoff_outputs_are_withheld(self):
        for reason in ("timeout_exceeded", "tool_use", None):
            events = [{"contentBlockDelta": {"delta": {"text": "partial"}}}]
            if reason:
                events.append({"messageStop": {"stopReason": reason}})
            with self.subTest(reason=reason), self.assertRaises(RuntimeError):
                self.invoke_events(events)

    def test_service_error_payload_is_not_printed(self):
        with self.assertRaisesRegex(RuntimeError, r"runtimeClientError") as caught:
            self.invoke_events([{"runtimeClientError": {"message": "sensitive service payload"}}])
        self.assertNotIn("sensitive", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
