from __future__ import annotations

import base64
import json
import logging
from typing import Any, Optional
import re

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


def _extract_json_from_text(text: str, strategy: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Try to extract a JSON object from text.

    Returns (obj, error) where obj is a dict on success, else None and an error reason.
    Strategies:
    - fenced_or_bare: try ```json fenced code block first; else first balanced object
    - strict_fence: require ```json fenced block only
    - first_object: scan for first balanced JSON object ignoring quoted braces
    """
    strategy = (strategy or "").strip().lower() or "fenced_or_bare"

    # 1) Fenced block extractor
    def extract_fenced(src: str) -> Optional[str]:
        # Match ```json ... ``` or ``` ... ``` blocks; prefer json-tagged
        # Use DOTALL to capture newlines
        fence_pattern_tagged = re.compile(r"```\s*json\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
        m = fence_pattern_tagged.search(src)
        if m:
            return m.group(1).strip()
        fence_pattern_any = re.compile(r"```\s*\n(.*?)\n```", re.DOTALL)
        m2 = fence_pattern_any.search(src)
        if m2:
            return m2.group(1).strip()
        return None

    # 2) First balanced object extractor
    def extract_first_object(src: str) -> Optional[str]:
        # Scan for first balanced {...} while skipping strings and escapes
        i = 0
        n = len(src)
        depth = 0
        start = -1
        in_str = False
        esc = False
        while i < n:
            ch = src[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == '}':
                    if depth > 0:
                        depth -= 1
                        if depth == 0 and start != -1:
                            return src[start : i + 1]
            i += 1
        return None

    def parse_obj(s: Optional[str]) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        if not s:
            return None, "no_candidate"
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return obj, None
            else:
                return None, "not_object"
        except Exception as ex:  # noqa: BLE001
            return None, f"json_error:{type(ex).__name__}"

    if strategy in {"fenced_or_bare", "strict_fence"}:
        fenced = extract_fenced(text)
        if fenced is not None:
            obj, err = parse_obj(fenced)
            if obj is not None:
                return obj, None
            # fall through on parse failure; err captured below if strict
            last_err = err
        else:
            last_err = "no_fence"
        if strategy == "strict_fence":
            return None, last_err
        # try bare first object
        bare = extract_first_object(text)
        return parse_obj(bare)

    # first_object only
    bare = extract_first_object(text)
    return parse_obj(bare)


class RealtimeSession:
    """Manages a single client <-> OpenAI Realtime session bridge."""

    def __init__(self, ws_client: WebSocket, cfg: RealtimeConfig):
        self.ws_client = ws_client
        self.cfg = cfg
        self.ws_openai: Optional[websockets.WebSocketClientProtocol] = None
        self._closing = False
        # Track upstream state so we don't attempt to forward after closure
        self._upstream_closed: bool = False
        self._upstream_close_reason: Optional[str] = None

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
                # Mark upstream closed and notify client (best effort)
                reason = getattr(ex, "reason", None) or str(ex)
                self._upstream_closed = True
                self._upstream_close_reason = reason
                logger.info("Upstream closed: %s", reason)
                await self._notify_client_upstream_closed(reason)
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
        # Attempt to close client side so browser gets a close signal instead of hanging
        try:
            await self.ws_client.close()
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
        if self._upstream_closed:
            # Inform client they are sending after upstream closed
            await self._notify_client_upstream_closed(self._upstream_close_reason or "upstream_closed")
            return False
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
        if self._upstream_closed:
            await self._notify_client_upstream_closed(self._upstream_close_reason or "upstream_closed")
            return False
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
        """Forward upstream bytes or text to the client with filtering.

        Filtering Rules:
        - If message is bytes/bytearray, only forward when "<binary>" is present
          in cfg.allowed_event_patterns. Otherwise, drop it silently.
        - If message is text (JSON), parse and check the "type" field against the
          glob patterns in cfg.allowed_event_patterns. If any pattern matches,
          forward the message; otherwise drop.
        - If parsing fails or "type" is missing, the message is dropped unless
          a catch-all pattern "*" is present.
        """
        # Bytes handling
        if isinstance(message, (bytes, bytearray)):
            if any(pat == "<binary>" or pat == "*" for pat in self.cfg.allowed_event_patterns):
                await self.ws_client.send_bytes(message)
            else:
                logger.debug("Dropped binary upstream frame due to filter")
            return

        # Text / JSON handling
        try:
            obj = json.loads(message)
            msg_type = obj.get("type")
        except Exception:
            msg_type = None

        # If extraction is configured and type matches, attempt extraction first
        if msg_type and self.cfg.extract_json_from_text_types:
            from fnmatch import fnmatch

            do_extract = any(fnmatch(msg_type, pat) for pat in self.cfg.extract_json_from_text_types)
            if do_extract:
                extracted = None
                error_reason: Optional[str] = None

                # Build candidate fields list: mapping for the matched pattern(s), then global fallback
                candidate_fields: list[str] = []
                try:
                    for pat, fields in self.cfg.extract_fields_map.items():
                        if fnmatch(msg_type, pat):
                            for f in fields:
                                if f not in candidate_fields:
                                    candidate_fields.append(f)
                except Exception:
                    pass
                if self.cfg.extract_json_text_field and self.cfg.extract_json_text_field not in candidate_fields:
                    candidate_fields.append(self.cfg.extract_json_text_field)

                # Try each candidate field present in the object
                for field in candidate_fields:
                    val = obj.get(field)
                    if isinstance(val, str) and val:
                        extracted, error_reason = _extract_json_from_text(val, self.cfg.extract_json_strategy)
                        if extracted is not None:
                            break

                if extracted is not None:
                    # Success: Unified envelope output
                    # Always wrap as {"type": <original event type>, "content": <extracted JSON object>}
                    out = {"type": msg_type, "content": extracted}
                    await self.ws_client.send_text(json.dumps(out))
                    return
                else:
                    # Handle on-fail policy
                    policy = (self.cfg.extract_on_fail or "drop").lower()
                    if policy == "forward":
                        await self.ws_client.send_text(message)
                    elif policy == "error":
                        err = {
                            "type": "extracted.json.error",
                            "source_type": msg_type,
                            "reason": error_reason or "no_json_found",
                        }
                        await self.ws_client.send_text(json.dumps(err))
                    else:
                        logger.debug("Dropped event after failed extraction type=%s", msg_type)
                    return

        # Match against allowed patterns; allow "*" to pass anything
        allow_all = any(p == "*" for p in self.cfg.allowed_event_patterns)
        is_allowed = allow_all
        if not is_allowed and msg_type:
            for pat in self.cfg.allowed_event_patterns:
                try:
                    # simple glob match
                    from fnmatch import fnmatch

                    if fnmatch(msg_type, pat):
                        is_allowed = True
                        break
                except Exception:
                    continue

        if is_allowed:
            await self.ws_client.send_text(message)
        else:
            # Keep logs concise at DEBUG level to avoid noise
            logger.debug("Dropped upstream event type=%s due to filter", msg_type)

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

    async def _notify_client_upstream_closed(self, reason: Optional[str]) -> None:
        """Send a single upstream closed notification to client (best effort)."""
        try:
            await self.ws_client.send_json({
                "type": "upstream.closed",
                "reason": reason,
            })
        except Exception:  # noqa: BLE001
            pass
