from __future__ import annotations

import base64
import json
import logging
from typing import Any, Optional

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from realtime.realtime_common import (
    RealtimeConfig,
    _build_headers,
    _build_system_instructions,
    _build_upstream_url,
    build_turn_detection_object,
)


logger = logging.getLogger("realtime_session")


class RealtimeSession:
    """Manages a single client <-> OpenAI Realtime session bridge."""

    def __init__(self, ws_client: WebSocket, cfg: RealtimeConfig):
        self.ws_client = ws_client
        self.cfg = cfg
        self.ws_openai: Optional[websockets.WebSocketClientProtocol] = None
        self._closing = False

    async def connect_openai(self) -> None:
        """Connect to the upstream OpenAI Realtime websocket."""
        url = _build_upstream_url(self.cfg)
        headers = _build_headers(self.cfg)
        logger.info("Connecting to Realtime: %s", url)
        self.ws_openai = await websockets.connect(
            url,
            extra_headers=headers,
            max_size=self.cfg.max_msg_mb * 1024 * 1024,
            ping_interval=self.cfg.heartbeat_sec,
        )

    async def send_session_update(self) -> None:
        """Send the initial session update to configure modalities and instructions."""
        assert self.ws_openai is not None
        system_prompt = _build_system_instructions(self.cfg)
        session: dict[str, Any] = {
            "type": "session.update",
            "session": {
                "modalities": ["text"] if self.cfg.text_only else ["audio", "text"],
                "instructions": system_prompt,
                "input_audio_format": "pcm16",
            },
        }
        # Include optional voice and optional turn_detection (VAD)
        if self.cfg.voice and not self.cfg.text_only:
            session["session"]["voice"] = self.cfg.voice
        td = build_turn_detection_object(self.cfg)
        if td is not None:
            session["session"]["turn_detection"] = td
        logger.info("Sending session.update: %s", session)
        await self.ws_openai.send(json.dumps(session))

    async def pump_client_to_openai(self) -> None:  # noqa: C901
        """Read events from the client and forward them to the upstream websocket."""
        assert self.ws_openai is not None
        while True:
            try:
                ev = await self.ws_client.receive()
            except WebSocketDisconnect:
                logger.info("Client disconnected")
                await self.cleanup()
                break
            except Exception as ex:  # noqa: BLE001
                logger.exception("Error reading from client: %s", ex)
                await self.cleanup()
                break

            if ev.get("type") == "websocket.disconnect":
                logger.info("Client ws disconnect event")
                await self.cleanup()
                break

            text = ev.get("text")
            if text is not None:
                if await self._handle_client_text(text):
                    continue
                else:
                    break

            data = ev.get("bytes")
            if data is not None:
                if await self._handle_client_bytes(data):
                    continue
                else:
                    break

    async def pump_openai_to_client(self) -> None:
        """Read messages from upstream and forward to the client; auto-close on completion."""
        assert self.ws_openai is not None
        while True:
            try:
                message = await self.ws_openai.recv()
            except Exception as ex:  # noqa: BLE001
                logger.info("Upstream closed: %s", ex)
                await self.cleanup()
                break

            try:
                await self._forward_upstream_message(message)

                if self.cfg.auto_close and await self._autoclose_on_completion(message):
                    await self.cleanup()
                    break
            except Exception as ex:  # noqa: BLE001
                logger.exception("Failed to send to client: %s", ex)
                await self.cleanup()
                break

    async def cleanup(self) -> None:
        if getattr(self, "_closing", False):
            return
        self._closing = True
        try:
            if self.ws_openai:
                await self.ws_openai.close()
        except Exception:  # noqa: BLE001
            pass

    # -------------------------
    # Internal helpers
    # -------------------------

    async def _handle_client_text(self, text: str) -> bool:
        """Forward text to upstream; wrap non-JSON as input_text.

        Returns True to continue loop, False to break on failure.
        """
        assert self.ws_openai is not None
        try:
            json.loads(text)
            await self.ws_openai.send(text)
            return True
        except Exception:
            evt = {"type": "input_text", "text": text}
            try:
                await self.ws_openai.send(json.dumps(evt))
                return True
            except Exception as ex:  # noqa: BLE001
                logger.exception("Failed to forward text payload: %s", ex)
                await self.cleanup()
                return False

    async def _handle_client_bytes(self, data: bytes) -> bool:
        """Forward binary audio from client to upstream as input_audio_buffer.append."""
        assert self.ws_openai is not None
        try:
            encoded = base64.b64encode(data).decode("ascii")
            evt = {"type": "input_audio_buffer.append", "audio": encoded}
            await self.ws_openai.send(json.dumps(evt))
            return True
        except Exception as ex:  # noqa: BLE001
            logger.exception("Failed to forward binary payload: %s", ex)
            await self.cleanup()
            return False

    async def _forward_upstream_message(self, message: Any) -> None:
        """Forward upstream bytes or text to the client."""
        if isinstance(message, (bytes, bytearray)):
            await self.ws_client.send_bytes(message)
        else:
            await self.ws_client.send_text(message)

    async def _autoclose_on_completion(self, message: Any) -> bool:
        """Return True if message indicates completion and we should auto-close."""
        if not isinstance(message, str):
            return False
        try:
            obj = json.loads(message)
        except Exception:  # noqa: BLE001
            return False
        if obj.get("type") in {"response.completed", "response.done"}:
            logger.info("Auto-close on %s", obj.get("type"))
            return True
        return False
