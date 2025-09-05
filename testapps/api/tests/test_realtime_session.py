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
        sess = RealtimeSession(ws, cfg)

        import asyncio
        asyncio.run(sess._forward_upstream_message(b"abc"))
        asyncio.run(sess._forward_upstream_message("{\"ok\":true}"))

        self.assertEqual(ws.sent_bytes, [b"abc"])
        self.assertEqual(ws.sent_text, ["{\"ok\":true}"])

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


if __name__ == "__main__":
    unittest.main()
