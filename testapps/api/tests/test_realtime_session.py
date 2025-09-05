import os
import sys
import json
import unittest
from unittest.mock import AsyncMock, MagicMock

# Ensure apps/api/src is on sys.path for package imports
TESTS_DIR = os.path.dirname(__file__)
API_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(API_DIR, "..", ".."))
API_SRC = os.path.join(REPO_ROOT, "apps", "api", "src")
if API_SRC not in sys.path:
    sys.path.insert(0, API_SRC)

from realtime.realtime_session import RealtimeSession  # type: ignore
from realtime.realtime_common import RealtimeConfig  # type: ignore


class DummyWebSocket:
    def __init__(self):
        self.sent_text = []
        self.sent_bytes = []
        self._queue = []

    async def receive(self):
        if not self._queue:
            raise RuntimeError("No messages queued")
        return self._queue.pop(0)

    async def send_text(self, text):
        self.sent_text.append(text)

    async def send_bytes(self, b):
        self.sent_bytes.append(b)

    # helpers
    def queue_text(self, text: str):
        self._queue.append({"text": text})

    def queue_bytes(self, b: bytes):
        self._queue.append({"bytes": b})

    def queue_disconnect(self):
        self._queue.append({"type": "websocket.disconnect"})


class TestRealtimeSession(unittest.TestCase):
    def make_cfg(self) -> RealtimeConfig:
        return RealtimeConfig(api_key="k", endpoint="https://api.openai.com", deployment="d", api_version="v")

    def test_handle_client_text_json_and_nonjson(self):
        ws = DummyWebSocket()
        cfg = self.make_cfg()
        sess = RealtimeSession(ws, cfg)
        # mock upstream websocket
        sess.ws_openai = AsyncMock()

        # JSON text should be forwarded as-is
        import asyncio
        asyncio.run(sess._handle_client_text(json.dumps({"type": "hello"})))
        self.assertTrue(sess.ws_openai.send.await_count >= 1)

        # Non-JSON text should be wrapped
        asyncio.run(sess._handle_client_text("hi there"))
        # total sends should be >= 2 now
        self.assertTrue(sess.ws_openai.send.await_count >= 2)

    def test_handle_client_bytes(self):
        ws = DummyWebSocket()
        cfg = self.make_cfg()
        sess = RealtimeSession(ws, cfg)
        sess.ws_openai = AsyncMock()

        import asyncio
        asyncio.run(sess._handle_client_bytes(b"\x00\x01\x02"))
        self.assertTrue(sess.ws_openai.send.await_count >= 1)

    def test_forward_upstream_message(self):
        ws = DummyWebSocket()
        cfg = self.make_cfg()
        # Allow all upstream messages for this test
        cfg.allowed_event_patterns = ["*"]
        sess = RealtimeSession(ws, cfg)

        import asyncio
        asyncio.run(sess._forward_upstream_message(b"abc"))
        asyncio.run(sess._forward_upstream_message("{\"ok\":true}"))

        self.assertEqual(ws.sent_bytes, [b"abc"])
        self.assertEqual(ws.sent_text, ["{\"ok\":true}"])

    def test_forward_upstream_message_filtering_defaults(self):
        # By default only response.text.delta and response.text.done are allowed
        ws = DummyWebSocket()
        cfg = self.make_cfg()  # default patterns
        # Force the expected default patterns explicitly to avoid ambient env interference
        cfg.allowed_event_patterns = ["response.text.delta", "response.text.done"]
        # Ensure extraction is disabled for this baseline test
        cfg.extract_json_from_text_types = []
        sess = RealtimeSession(ws, cfg)

        import asyncio
        # Not allowed: non-JSON binary, and unrelated JSON types
        asyncio.run(sess._forward_upstream_message(b"binary"))
        asyncio.run(sess._forward_upstream_message(json.dumps({"type": "response.content_part.done"})))
        asyncio.run(sess._forward_upstream_message(json.dumps({"type": "input_audio_buffer.append"})))

        # Allowed: response.text.delta and response.text.done
        asyncio.run(sess._forward_upstream_message(json.dumps({"type": "response.text.delta", "delta": "hi"})))
        asyncio.run(sess._forward_upstream_message(json.dumps({"type": "response.text.done"})))

        self.assertEqual(ws.sent_bytes, [])
        # Expect exactly the two allowed messages to be forwarded
        forwarded_types = [json.loads(t).get("type") for t in ws.sent_text]
        # Expect the two streamed events forwarded untouched
        self.assertIn("response.text.delta", forwarded_types)
        self.assertIn("response.text.done", forwarded_types)
        self.assertEqual(len(forwarded_types), 2)

    def test_forward_upstream_message_allow_only_done(self):
        ws = DummyWebSocket()
        cfg = self.make_cfg()
        cfg.allowed_event_patterns = ["response.text.done"]
        cfg.extract_json_from_text_types = []
        sess = RealtimeSession(ws, cfg)

        import asyncio
        # Send both delta and done
        asyncio.run(sess._forward_upstream_message(json.dumps({"type": "response.text.delta", "delta": "hi"})))
        asyncio.run(sess._forward_upstream_message(json.dumps({"type": "response.text.done"})))

        forwarded_types = [json.loads(t).get("type") for t in ws.sent_text]
        # Only done should pass
        self.assertEqual(forwarded_types, ["response.text.done"])

    def test_session_update_builds_turn_detection_and_audio_format(self):
        ws = DummyWebSocket()
        cfg = RealtimeConfig(api_key="k", endpoint="https://api.openai.com", deployment="d", api_version="v")
        cfg.turn_detection_type = "server_vad"
        cfg.turn_detection_server_threshold = 0.5
        cfg.turn_detection_server_prefix_padding_ms = 300
        cfg.turn_detection_server_silence_duration_ms = 500
        sess = RealtimeSession(ws, cfg)
        # mock upstream websocket
        class FakeWS:
            def __init__(self):
                self.sent = []

            async def send(self, data):
                self.sent.append(json.loads(data))

            async def close(self):
                pass

        sess.ws_openai = FakeWS()

        import asyncio
        asyncio.run(sess.send_session_update())
        payload = sess.ws_openai.sent[-1]
        self.assertEqual(payload["type"], "session.update")
        self.assertIn("input_audio_format", payload["session"])  # pcm16
        td = payload["session"].get("turn_detection")
        self.assertEqual(td.get("type"), "server_vad")
        self.assertEqual(td.get("threshold"), 0.5)
        self.assertEqual(td.get("prefix_padding_ms"), 300)
        self.assertEqual(td.get("silence_duration_ms"), 500)

    def test_autoclose_on_completion(self):
        ws = DummyWebSocket()
        cfg = self.make_cfg()
        sess = RealtimeSession(ws, cfg)

        import asyncio
        should_close = asyncio.run(sess._autoclose_on_completion(json.dumps({"type": "response.done"})))
        self.assertTrue(should_close)
        should_not_close = asyncio.run(sess._autoclose_on_completion("{\"type\":\"other\"}"))
        self.assertFalse(should_not_close)

    def test_extract_json_from_text_done_fenced_replace(self):
        # Configure extraction for response.text.done with fenced json
        ws = DummyWebSocket()
        cfg = self.make_cfg()
        cfg.extract_json_from_text_types = ["response.text.done"]
        cfg.extract_fields_map = {"response.text.done": ["text"]}
        cfg.extract_json_strategy = "fenced_or_bare"
        cfg.extract_output_mode = "replace"

        sess = RealtimeSession(ws, cfg)

        payload = {
            "type": "response.text.done",
            "text": "```json\n{\n  \"ok\": true, \"n\": 1\n}\n```"
        }

        import asyncio
        asyncio.run(sess._forward_upstream_message(json.dumps(payload)))

        # Expect only the extracted JSON object
        self.assertEqual(len(ws.sent_text), 1)
        obj = json.loads(ws.sent_text[0])
        self.assertEqual(obj.get("type"), "response.text.done")
        self.assertEqual(obj.get("content"), {"ok": True, "n": 1})

    def test_extract_json_from_text_done_bare_replace(self):
        # Bare JSON in text field should be extracted
        ws = DummyWebSocket()
        cfg = self.make_cfg()
        cfg.extract_json_from_text_types = ["response.text.done"]
        cfg.extract_fields_map = {"response.text.done": ["text"]}
        cfg.extract_json_strategy = "fenced_or_bare"
        cfg.extract_output_mode = "replace"

        sess = RealtimeSession(ws, cfg)

        payload = {
            "type": "response.text.done",
            "text": "{\n  \"items\": [1,2,3]\n} trailing commentary"
        }

        import asyncio
        asyncio.run(sess._forward_upstream_message(json.dumps(payload)))

        self.assertEqual(len(ws.sent_text), 1)
        obj = json.loads(ws.sent_text[0])
        self.assertEqual(obj.get("type"), "response.text.done")
        self.assertEqual(obj.get("content"), {"items": [1, 2, 3]})

    def test_extract_json_from_delta_field(self):
        # Map response.text.delta to the 'delta' field
        ws = DummyWebSocket()
        cfg = self.make_cfg()
        cfg.extract_json_from_text_types = ["response.text.delta"]
        cfg.extract_fields_map = {"response.text.delta": ["delta"]}
        cfg.extract_json_strategy = "first_object"
        cfg.extract_on_fail = "drop"

        sess = RealtimeSession(ws, cfg)

        payload = {
            "type": "response.text.delta",
            "delta": "prefix {\"a\": 1} suffix"
        }

        import asyncio
        asyncio.run(sess._forward_upstream_message(json.dumps(payload)))

        self.assertEqual(len(ws.sent_text), 1)
        obj = json.loads(ws.sent_text[0])
        self.assertEqual(obj.get("type"), "response.text.delta")
        self.assertEqual(obj.get("content"), {"a": 1})

    def test_extract_on_fail_forward(self):
        # When extraction fails and policy=forward, original event is forwarded
        ws = DummyWebSocket()
        cfg = self.make_cfg()
        cfg.extract_json_from_text_types = ["response.text.done"]
        cfg.extract_fields_map = {"response.text.done": ["text"]}
        cfg.extract_json_strategy = "strict_fence"  # require fence
        cfg.extract_on_fail = "forward"

        sess = RealtimeSession(ws, cfg)

        payload = {"type": "response.text.done", "text": "no json here"}

        import asyncio
        asyncio.run(sess._forward_upstream_message(json.dumps(payload)))

        self.assertEqual(len(ws.sent_text), 1)
        roundtrip = json.loads(ws.sent_text[0])
        self.assertEqual(roundtrip["type"], "response.text.done")

    def test_extract_wrap_mode(self):
        # Wrap mode emits an envelope with payload
        ws = DummyWebSocket()
        cfg = self.make_cfg()
        cfg.extract_json_from_text_types = ["response.text.done"]
        cfg.extract_fields_map = {"response.text.done": ["text"]}
        cfg.extract_output_mode = "wrap"

        sess = RealtimeSession(ws, cfg)

        payload = {
            "type": "response.text.done",
            "text": "```json\n{\n  \"x\": 42\n}\n```"
        }

        import asyncio
        asyncio.run(sess._forward_upstream_message(json.dumps(payload)))

        self.assertEqual(len(ws.sent_text), 1)
        env = json.loads(ws.sent_text[0])
        self.assertEqual(env.get("type"), "response.text.done")
        self.assertEqual(env.get("content"), {"x": 42})


if __name__ == "__main__":
    unittest.main()
