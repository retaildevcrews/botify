import os
import sys
import json
import tempfile
import asyncio
import wave
from array import array
import unittest
from unittest.mock import patch

# Ensure apps/api/src is on sys.path for package imports
TESTS_DIR = os.path.dirname(__file__)
API_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(API_DIR, "..", ".."))
API_SRC = os.path.join(REPO_ROOT, "apps", "api", "src")
if API_SRC not in sys.path:
    sys.path.insert(0, API_SRC)

from realtime.realtime_common import (  # type: ignore
    _ensure_env,
    _build_headers,
    _build_upstream_url,
    _normalize_wav_to_pcm16_mono_16k,
    stream_pcm_to_realtime,
    RealtimeConfig,
    RealtimeClient,
    build_turn_detection_object,
)


class TestRealtimeCommon(unittest.TestCase):
    def test_ensure_env_success(self):
        with patch.dict(os.environ, {
            "AZURE_OPENAI_API_KEY": "key",
            "AZURE_OPENAI_ENDPOINT": "https://contoso.ai",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
            "AZURE_OPENAI_API_VERSION": "2024-10-01-preview",
        }, clear=True):
            cfg = _ensure_env()
            self.assertIsInstance(cfg, RealtimeConfig)
            self.assertEqual(cfg.api_key, "key")
            self.assertEqual(cfg.endpoint, "https://contoso.ai")
            self.assertEqual(cfg.deployment, "gpt-4o")
            self.assertEqual(cfg.api_version, "2024-10-01-preview")

    def test_ensure_env_missing_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                _ensure_env()
            msg = str(ctx.exception)
            self.assertIn("Missing required env vars", msg)

    def test_build_upstream_url_https_to_wss(self):
        cfg = RealtimeConfig(
            api_key="k",
            endpoint="https://example.com",
            deployment="dep",
            api_version="v1",
        )
        url = _build_upstream_url(cfg)
        self.assertTrue(url.startswith("wss://example.com/openai/realtime"))
        self.assertIn("api-version=v1", url)
        self.assertIn("deployment=dep", url)

    def test_build_headers_for_azure(self):
        cfg = RealtimeConfig(api_key="k", endpoint="https://foo.azure.com", deployment="d", api_version="v")
        headers = _build_headers(cfg)
        self.assertIn("api-key", headers)
        self.assertEqual(headers.get("api-key"), "k")
        self.assertEqual(headers.get("OpenAI-Beta"), "realtime=v1")

    def test_build_headers_for_openai(self):
        cfg = RealtimeConfig(api_key="k", endpoint="https://api.openai.com", deployment="d", api_version="v")
        headers = _build_headers(cfg)
        self.assertIn("Authorization", headers)
        self.assertEqual(headers.get("Authorization"), "Bearer k")

    def test_normalize_wav_to_pcm16_mono_16k_resamples(self):
        # Create a small 8kHz mono 16-bit WAV and ensure it resamples to 16kHz
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tf:
            framerate = 8000
            duration_s = 0.1
            n_frames = int(framerate * duration_s)
            samples = array("h", [int(10000 * ((i % 20) - 10) / 10) for i in range(n_frames)])
            with wave.open(tf.name, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(framerate)
                wf.writeframes(samples.tobytes())

            pcm, rate = _normalize_wav_to_pcm16_mono_16k(tf.name)
            self.assertEqual(rate, 16000)
            self.assertIsInstance(pcm, (bytes, bytearray))
            self.assertGreater(len(pcm), 0)

    def test_stream_pcm_to_realtime_chunks_and_commit(self):
        class FakeClient:
            def __init__(self):
                self.sent = []

            async def send_json(self, obj):
                self.sent.append(obj)

        # 10000 bytes at 16kHz, chunk_ms=100 -> chunk_size = 3200 bytes => 4 chunks (last partial)
        data = bytes(10000)
        client = FakeClient()
        import asyncio

        asyncio.run(stream_pcm_to_realtime(client, data, 16000, chunk_ms=100))
        # Expect several append events then a commit
        self.assertGreaterEqual(len(client.sent), 2)
        self.assertTrue(all(evt.get("type") == "input_audio_buffer.append" for evt in client.sent[:-1]))
        self.assertEqual(client.sent[-1].get("type"), "input_audio_buffer.commit")

    def test_send_session_update_turn_detection_and_audio_format(self):
        cfg = RealtimeConfig(api_key="k", endpoint="https://api.openai.com", deployment="d", api_version="v")
        cfg.text_only = False
        # Ensure default case isn't affected by env: unset turn detection type
        cfg.turn_detection_type = None
        client = RealtimeClient(cfg)

        class FakeWS:
            def __init__(self):
                self.sent = []

            async def send(self, data):
                self.sent.append(json.loads(data))

        # inject fake ws
        client.ws = FakeWS()

        # No turn_detection (default)
        asyncio.run(client.send_session_update())
        payload = client.ws.sent[-1]
        self.assertEqual(payload["type"], "session.update")
        self.assertIn("input_audio_format", payload["session"])  # pcm16
        self.assertNotIn("turn_detection", payload["session"])  # default None

        # Explicit semantic_vad
        asyncio.run(client.send_session_update(turn_detection_type="semantic_vad"))
        payload = client.ws.sent[-1]
        self.assertEqual(payload["session"].get("turn_detection"), {"type": "semantic_vad"})

        # Explicit none -> turn_detection present with type none
        asyncio.run(client.send_session_update(turn_detection_type="none"))
        payload = client.ws.sent[-1]
        self.assertEqual(payload["session"].get("turn_detection"), {"type": "none"})

    def test_build_turn_detection_object_server_and_semantic(self):
        # Server VAD with tuning
        cfg = RealtimeConfig(api_key="k", endpoint="https://api.openai.com", deployment="d", api_version="v")
        cfg.turn_detection_type = "server_vad"
        cfg.turn_detection_server_threshold = 0.4
        cfg.turn_detection_server_prefix_padding_ms = 250
        cfg.turn_detection_server_silence_duration_ms = 600
        cfg.turn_detection_create_response = True
        cfg.turn_detection_interrupt_response = True
        obj = build_turn_detection_object(cfg)
        self.assertEqual(obj.get("type"), "server_vad")
        self.assertEqual(obj.get("threshold"), 0.4)
        self.assertEqual(obj.get("prefix_padding_ms"), 250)
        self.assertEqual(obj.get("silence_duration_ms"), 600)
        self.assertTrue(obj.get("create_response"))
        self.assertTrue(obj.get("interrupt_response"))

        # Semantic VAD with eagerness
        cfg2 = RealtimeConfig(api_key="k", endpoint="https://api.openai.com", deployment="d", api_version="v")
        cfg2.turn_detection_type = "semantic_vad"
        cfg2.turn_detection_semantic_eagerness = "high"
        obj2 = build_turn_detection_object(cfg2)
        self.assertEqual(obj2.get("type"), "semantic_vad")
        self.assertEqual(obj2.get("eagerness"), "high")

    def test_build_turn_detection_object_none_and_unset(self):
        cfg = RealtimeConfig(api_key="k", endpoint="https://api.openai.com", deployment="d", api_version="v")
        # Ensure unset: override any env-provided defaults
        cfg.turn_detection_type = None
        # Unset returns None
        self.assertIsNone(build_turn_detection_object(cfg))
        # Explicit empty returns None
        self.assertIsNone(build_turn_detection_object(cfg, turn_type_override=""))
        # Explicit none returns an object with type none
        obj = build_turn_detection_object(cfg, turn_type_override="none")
        self.assertEqual(obj, {"type": "none"})


if __name__ == "__main__":
    unittest.main()
