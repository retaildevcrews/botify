from __future__ import annotations

# Moved from apps/api/realtime_common.py into src/realtime (renamed from realtime_api)

import asyncio
import base64
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional, Tuple
from urllib.parse import urlparse
import wave
from array import array

import websockets
from dotenv import load_dotenv
from jinja2 import BaseLoader, Environment, Undefined

load_dotenv()

# Module logger for this package
logger = logging.getLogger("realtime-common")


# -------------------------
# Config and templating
# -------------------------


@dataclass
class RealtimeConfig:
    """
    Configuration for the realtime API client.

    This dataclass holds all configuration parameters required to connect to and interact with the realtime API.
    Most parameters can be set via environment variables, with sensible defaults for optional parameters.

    Required parameters (must be set via environment variables or explicitly):
        - api_key (str): API key for authentication. (AZURE_OPENAI_API_KEY or OPENAI_API_KEY)
        - endpoint (str): API endpoint URL. (AZURE_OPENAI_ENDPOINT or OPENAI_ENDPOINT)
        - deployment (str): Deployment/model name. (AZURE_OPENAI_DEPLOYMENT or OPENAI_MODEL)
        - api_version (str): API version string. (AZURE_OPENAI_API_VERSION or OPENAI_API_VERSION)

    Optional parameters (can be set via environment variables, otherwise defaults are used):
        - text_only (bool): If True, disables audio features. Default: False. (REALTIME_TEXT_ONLY)
        - auto_close (bool): If True, closes connection automatically. Default: True. (REALTIME_AUTO_CLOSE)
        - voice (Optional[str]): Voice model to use. Default: "alloy". (REALTIME_VOICE)
        - heartbeat_sec (int): Heartbeat interval in seconds. Default: 10. (REALTIME_HEARTBEAT_SEC)
        - max_msg_mb (int): Maximum message size in MB. Default: 15. (REALTIME_MAX_MSG_MB)
        - menu_path (str): Path to menu file. Default: "menu/menu.ts". (REALTIME_MENU_PATH)
        - template_path (str): Path to prompt template. Default: "prompt_templates/template.txt". (REALTIME_TEMPLATE_PATH)
        - schema_path (Optional[str]): Path to optional schema file. (REALTIME_SCHEMA_PATH)

    Usage example:
        >>> config = RealtimeConfig(
        ...     api_key="sk-...",
        ...     endpoint="https://api.openai.com/v1",
        ...     deployment="gpt-4",
        ...     api_version="2023-05-15"
        ... )

    Or, to use environment variables for all parameters:
        >>> config = _ensure_env()
    """
    api_key: str
    endpoint: str
    deployment: str
    api_version: str

    text_only: bool = os.getenv("REALTIME_TEXT_ONLY", "false").lower() == "true"
    auto_close: bool = os.getenv("REALTIME_AUTO_CLOSE", "true").lower() == "true"
    voice: Optional[str] = os.getenv("REALTIME_VOICE", "alloy")
    heartbeat_sec: int = int(os.getenv("REALTIME_HEARTBEAT_SEC", "10"))
    max_msg_mb: int = int(os.getenv("REALTIME_MAX_MSG_MB", "15"))

    # paths are resolved relative to the original apps/api directory for backwards compatibility
    menu_path: str = os.getenv("REALTIME_MENU_PATH", "menu/menu.ts")
    template_path: str = os.getenv("REALTIME_TEMPLATE_PATH", "prompt_templates/template.txt")
    # Optional schema
    schema_path: Optional[str] = os.getenv("REALTIME_SCHEMA_PATH")

    # Upstream -> client event filtering
    # Comma-separated list of allowed event type patterns (supports '*' glob).
    # Special token "<binary>" controls whether raw binary frames are forwarded.
    # Default: only forward text stream events (delta + done).
    allowed_event_patterns: list[str] = field(
        default_factory=lambda: [
            s.strip()
            for s in os.getenv(
                "REALTIME_ALLOWED_EVENT_TYPES",
                "response.text.done,response.text.delta",
            ).split(",")
            if s.strip()
        ]
    )

    # Extraction configuration (feature disabled by default)
    # These flags control optional transformation of upstream events into extracted JSON payloads.
    # If extract_json_from_text_types is empty, no extraction is attempted.
    extract_json_from_text_types: list[str] = field(
        default_factory=lambda: [
            s.strip() for s in os.getenv("REALTIME_EXTRACT_JSON_FROM_TEXT_TYPES", "").split(",") if s.strip()
        ]
    )
    # Global fallback field name to read text from (if no per-event mapping applies)
    extract_json_text_field: str = os.getenv("REALTIME_EXTRACT_JSON_TEXT_FIELD", "text")
    # Strategy to extract JSON from text: fenced_or_bare | strict_fence | first_object
    extract_json_strategy: str = os.getenv("REALTIME_EXTRACT_JSON_STRATEGY", "fenced_or_bare")
    # Output mode for successful extraction: replace | wrap
    extract_output_mode: str = os.getenv("REALTIME_EXTRACT_OUTPUT_MODE", "replace")
    # Behavior when extraction fails: drop | forward | error
    extract_on_fail: str = os.getenv("REALTIME_EXTRACT_ON_FAIL", "drop")
    # Per-event fields mapping (pattern -> ordered list of candidate fields). Parsed from env string.
    # Format example: "response.text.done:text;response.text.delta:delta"
    extract_fields_map: dict[str, list[str]] = field(
        default_factory=lambda: _parse_fields_map_env(os.getenv("REALTIME_EXTRACT_FIELDS_MAP", ""))
    )

    # Turn detection (VAD) configuration
    # Supported values include: "server_vad", "semantic_vad", "none" (or unset)
    # Default is None (unset) which means no turn_detection section is sent.
    turn_detection_type: Optional[str] = os.getenv("REALTIME_TURN_DETECTION_TYPE")
    # Server VAD tuning
    turn_detection_server_threshold: Optional[float] = (
        float(os.getenv("REALTIME_TURN_DETECTION_SERVER_THRESHOLD"))
        if os.getenv("REALTIME_TURN_DETECTION_SERVER_THRESHOLD") is not None
        else None
    )
    turn_detection_server_prefix_padding_ms: Optional[int] = (
        int(os.getenv("REALTIME_TURN_DETECTION_SERVER_PREFIX_PADDING_MS"))
        if os.getenv("REALTIME_TURN_DETECTION_SERVER_PREFIX_PADDING_MS") is not None
        else None
    )
    turn_detection_server_silence_duration_ms: Optional[int] = (
        int(os.getenv("REALTIME_TURN_DETECTION_SERVER_SILENCE_DURATION_MS"))
        if os.getenv("REALTIME_TURN_DETECTION_SERVER_SILENCE_DURATION_MS") is not None
        else None
    )
    # Common conversation mode flags (optional; upstream may ignore outside conversation mode)
    turn_detection_create_response: Optional[bool] = (
        os.getenv("REALTIME_TURN_DETECTION_CREATE_RESPONSE", "").lower() in {"1", "true", "yes"}
        if os.getenv("REALTIME_TURN_DETECTION_CREATE_RESPONSE") is not None
        else None
    )
    turn_detection_interrupt_response: Optional[bool] = (
        os.getenv("REALTIME_TURN_DETECTION_INTERRUPT_RESPONSE", "").lower() in {"1", "true", "yes"}
        if os.getenv("REALTIME_TURN_DETECTION_INTERRUPT_RESPONSE") is not None
        else None
    )
    # Semantic VAD tuning
    turn_detection_semantic_eagerness: Optional[str] = os.getenv("REALTIME_TURN_DETECTION_SEMANTIC_EAGERNESS")


def _ensure_env() -> RealtimeConfig:
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("OPENAI_MODEL")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION") or os.getenv("OPENAI_API_VERSION")

    missing = [
        ("AZURE_OPENAI_API_KEY or OPENAI_API_KEY", api_key),
        ("AZURE_OPENAI_ENDPOINT or OPENAI_ENDPOINT", endpoint),
        ("AZURE_OPENAI_DEPLOYMENT or OPENAI_MODEL", deployment),
        ("AZURE_OPENAI_API_VERSION or OPENAI_API_VERSION", api_version),
    ]
    not_set = [name for name, val in missing if not val]
    if not_set:
        raise RuntimeError(f"Missing required env vars: {', '.join(not_set)}")

    cfg = RealtimeConfig(
        api_key=api_key, endpoint=endpoint.rstrip("/"), deployment=deployment, api_version=api_version
    )
    try:
        parsed = urlparse(cfg.endpoint)
        safe_endpoint = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        safe_endpoint = cfg.endpoint
    logger.info(
        "Env loaded: endpoint=%s deployment=%s api_version=%s text_only=%s voice=%s vad=%s",
        safe_endpoint,
        cfg.deployment,
        cfg.api_version,
        cfg.text_only,
        cfg.voice,
        (cfg.turn_detection_type or "<unset>")
    )
    return cfg


def _parse_fields_map_env(raw: str) -> dict[str, list[str]]:
    """Parse REALTIME_EXTRACT_FIELDS_MAP env into a dict of pattern -> [fields...].

    Expected format:
        "pattern1:fieldA,fieldB;pattern2:fieldX"
    Whitespace around tokens is ignored. Invalid entries are skipped.
    """
    mapping: dict[str, list[str]] = {}
    raw = (raw or "").strip()
    if not raw:
        return mapping
    try:
        rules = [r.strip() for r in raw.split(";") if r.strip()]
        for rule in rules:
            if ":" not in rule:
                continue
            pat, fields_str = rule.split(":", 1)
            pat = pat.strip()
            fields = [f.strip() for f in fields_str.split(",") if f.strip()]
            if pat and fields:
                mapping[pat] = fields
    except Exception:
        # Be resilient to malformed input; return whatever was parsed
        pass
    return mapping


def _read_text(path: str) -> str:
    # Resolve relative to apps/api regardless of src package location
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    full = os.path.join(base_dir, path)
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


def build_template(template_path: str, **kwargs: Any) -> str:
    logger.debug("Rendering template from: %s (keys=%s)", template_path, sorted(list(kwargs.keys())))
    template_text = _read_text(template_path)
    env = Environment(
        loader=BaseLoader(),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=Undefined,
    )
    template = env.from_string(template_text)
    rendered = template.render(**kwargs)
    logger.debug("Rendered template length=%d", len(rendered))
    return rendered


def _build_system_instructions(cfg: RealtimeConfig) -> str:
    ctx: dict[str, Any] = {}
    try:
        ctx["menu"] = _read_text(cfg.menu_path)
    except Exception:
        logger.warning("Could not read menu at %s", cfg.menu_path)
        ctx["menu"] = ""

    if cfg.schema_path:
        try:
            ctx["response_schema"] = _read_text(cfg.schema_path)
        except Exception:
            logger.warning("Could not read schema at %s", cfg.schema_path)
    logger.debug(
        "Building system instructions using template=%s (menu=%s, schema=%s)",
        cfg.template_path,
        os.path.basename(cfg.menu_path) if cfg.menu_path else None,
        os.path.basename(cfg.schema_path) if cfg.schema_path else None,
    )
    return build_template(cfg.template_path, **ctx)


def build_turn_detection_object(cfg: RealtimeConfig, turn_type_override: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Build a full turn_detection object based on config and optional override.

    Behavior:
    - If type is None/empty -> return None (do not include field in session.update)
    - If type is "none" -> return {"type": "none"}
    - If type is "server_vad", include optional threshold/prefix_padding_ms/silence_duration_ms
    - If type is "semantic_vad", include optional eagerness
    - For both modes, include optional create_response and interrupt_response if configured
    - Any other non-empty type is passed through as {"type": value}
    """
    t = (turn_type_override or cfg.turn_detection_type or "").strip().lower()
    if t == "":
        logger.debug("turn_detection: unset -> omitting field")
        return None
    if t == "none":
        logger.debug("turn_detection: explicit none -> {'type': 'none'}")
        return {"type": "none"}
    obj: dict[str, Any] = {"type": t}
    if t == "server_vad":
        if cfg.turn_detection_server_threshold is not None:
            obj["threshold"] = cfg.turn_detection_server_threshold
        if cfg.turn_detection_server_prefix_padding_ms is not None:
            obj["prefix_padding_ms"] = cfg.turn_detection_server_prefix_padding_ms
        if cfg.turn_detection_server_silence_duration_ms is not None:
            obj["silence_duration_ms"] = cfg.turn_detection_server_silence_duration_ms
    elif t == "semantic_vad":
        if cfg.turn_detection_semantic_eagerness:
            eag = cfg.turn_detection_semantic_eagerness.strip().lower()
            # allow only known values if provided; otherwise pass-through
            if eag in {"low", "medium", "high", "auto"}:
                obj["eagerness"] = eag
            else:
                obj["eagerness"] = eag
    # Common optional flags
    if cfg.turn_detection_create_response is not None:
        obj["create_response"] = cfg.turn_detection_create_response
    if cfg.turn_detection_interrupt_response is not None:
        obj["interrupt_response"] = cfg.turn_detection_interrupt_response
    logger.debug(
        "turn_detection: built object type=%s fields=%s",
        obj.get("type"),
        sorted([k for k in obj.keys() if k != "type"]),
    )
    return obj


# -------------------------
# Upstream connection
# -------------------------


def _build_upstream_url(cfg: RealtimeConfig) -> str:
    base = cfg.endpoint.rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme in ("http", "https"):
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        base = f"{ws_scheme}://{parsed.netloc}{parsed.path}"
    elif parsed.scheme in ("ws", "wss"):
        base = base
    else:
        base = f"wss://{base}"

    url = f"{base}/openai/realtime?api-version={cfg.api_version}&deployment={cfg.deployment}"
    logger.debug("Constructed upstream URL: %s", url)
    return url


def _build_headers(cfg: RealtimeConfig) -> dict[str, str]:
    is_azure = "azure.com" in cfg.endpoint.lower()
    headers = {
        ("api-key" if is_azure else "Authorization"): (cfg.api_key if is_azure else f"Bearer {cfg.api_key}"),
        "OpenAI-Beta": "realtime=v1",
    }
    # Do not log secrets; only log scheme choice
    logger.debug("Using Azure header scheme: %s", is_azure)
    return headers


async def openai_connect(cfg: RealtimeConfig) -> websockets.WebSocketClientProtocol:
    url = _build_upstream_url(cfg)
    headers = _build_headers(cfg)
    logger.info("Connecting to Realtime: %s", url)
    return await websockets.connect(
        url,
        extra_headers=headers,
        max_size=cfg.max_msg_mb * 1024 * 1024,
        ping_interval=cfg.heartbeat_sec,
    )


class RealtimeClient:
    """Lightweight upstream client for Realtime WS."""

    def __init__(self, cfg: RealtimeConfig):
        self.cfg = cfg
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

    async def connect(self) -> None:
        logger.debug("RealtimeClient.connect invoked")
        self.ws = await openai_connect(self.cfg)

    async def send_session_update(self, *, turn_detection_type: Optional[str] = None, force_audio: bool = False) -> None:
        assert self.ws is not None
        instructions = _build_system_instructions(self.cfg)
        # If force_audio is True, ensure we advertise audio+text
        text_only = False if force_audio else self.cfg.text_only
        payload: dict[str, Any] = {
            "type": "session.update",
            "session": {
                "modalities": ["text"] if text_only else ["audio", "text"],
                "instructions": instructions,
                "input_audio_format": "pcm16",
            },
        }
        # Determine turn detection from parameter override or config default
        td = build_turn_detection_object(self.cfg, turn_type_override=turn_detection_type)
        if td is not None:
            payload["session"]["turn_detection"] = td
        if self.cfg.voice and not text_only:
            payload["session"]["voice"] = self.cfg.voice
        # Log a compact summary to avoid leaking instruction contents
        logger.debug(
            "Sending session.update: modalities=%s voice=%s td=%s force_audio=%s instr_len=%d",
            payload["session"]["modalities"],
            payload["session"].get("voice"),
            (payload["session"].get("turn_detection", {}) or {}).get("type"),
            force_audio,
            len(instructions) if isinstance(instructions, str) else -1,
        )
        await self.ws.send(json.dumps(payload))

    async def send_json(self, obj: dict[str, Any]) -> None:
        assert self.ws is not None
        try:
            msg_type = obj.get("type")
        except Exception:
            msg_type = None
        logger.debug("send_json type=%s", msg_type)
        await self.ws.send(json.dumps(obj))

    async def recv(self) -> Any:
        assert self.ws is not None
        return await self.ws.recv()

    async def close(self) -> None:
        try:
            if self.ws:
                logger.info("Closing upstream websocket")
                await self.ws.close()
        except Exception:
            pass


# -------------------------
# Audio helpers
# -------------------------


def _normalize_wav_to_pcm16_mono_16k(wav_path: str) -> Tuple[bytes, int]:
    """Return (pcm16_mono_16k_bytes, sample_rate) using only stdlib.

    Steps:
    - Read WAV frames
    - Convert to mono by averaging channels
    - Convert sample width to 16-bit signed little-endian
    - Resample to 16kHz using simple linear interpolation if needed
    """
    try:
        with wave.open(wav_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()  # bytes per sample
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
    except FileNotFoundError as e:
        raise RuntimeError(f"Could not open WAV file '{wav_path}': file not found.") from e
    except wave.Error as e:
        raise RuntimeError(f"Invalid WAV file format for '{wav_path}': {e}") from e
    except Exception as e:
        raise RuntimeError(f"Error reading WAV file '{wav_path}': {e}") from e
    # Convert raw bytes to list of samples per channel
    if sampwidth == 2:
        # 16-bit signed little-endian
        samples = array("h")
        samples.frombytes(raw)
    elif sampwidth == 1:
        # 8-bit unsigned PCM -> convert to signed int16 range by shifting
        u8 = array("B")
        u8.frombytes(raw)
        samples = array("h", [(int(b) - 128) * 256 for b in u8])
    else:
        raise RuntimeError(
            f"Unsupported WAV sample width: {sampwidth * 8} bits. "
            "Please convert your audio file to 16-bit PCM using a tool like ffmpeg. "
            "For example: ffmpeg -i input.wav -ac 1 -ar 16000 -sample_fmt s16 output.wav"
        )

    total_samples = len(samples)
    if n_channels > 1:
        # Average channels to mono
        frames = total_samples // n_channels
        mono = array("h")
        mono.extend(0 for _ in range(frames))
        idx = 0
        for f in range(frames):
            s = 0
            for c in range(n_channels):
                s += samples[idx]
                idx += 1
            mono[f] = int(s / n_channels)
        samples = mono
        n_channels = 1

    target_rate = 16000
    if framerate != target_rate:
        src = samples
        src_n = len(src)
        if src_n == 0:
            return b"", target_rate
        dst_n = int(round(src_n * (target_rate / framerate)))
        if dst_n <= 1:
            dst_n = 1
        if src_n == 1:
            out = array("h", [src[0]] * dst_n)
        else:
            out = array("h")
            out.extend(0 for _ in range(dst_n))
            scale = (src_n - 1) / (dst_n - 1)
            for j in range(dst_n):
                x = j * scale
                i = int(x)
                if i >= src_n - 1:
                    val = src[src_n - 1]
                else:
                    frac = x - i
                    s0 = src[i]
                    s1 = src[i + 1]
                    val = int(s0 + (s1 - s0) * frac)
                if val < -32768:
                    val = -32768
                elif val > 32767:
                    val = 32767
                out[j] = val
        samples = out
        framerate = target_rate

    return samples.tobytes(), framerate


async def stream_pcm_to_realtime(client: RealtimeClient, pcm_bytes: bytes, sample_rate: int, chunk_ms: int = 100) -> None:
    """Chunk PCM16 mono bytes and send to upstream as input_audio_buffer.append + commit."""
    assert sample_rate == 16000, "sample_rate must be 16000 after normalization"
    bytes_per_sample = 2  # 16-bit
    samples_per_chunk = int(sample_rate * (chunk_ms / 1000.0))
    chunk_size = samples_per_chunk * bytes_per_sample

    logger.debug(
        "Streaming PCM: bytes=%d sample_rate=%d chunk_ms=%d", len(pcm_bytes), sample_rate, chunk_ms
    )
    pos = 0
    total = len(pcm_bytes)
    while pos < total:
        chunk = pcm_bytes[pos : pos + chunk_size]
        pos += len(chunk)
        if not chunk:
            break
        b64 = base64.b64encode(chunk).decode("ascii")
        await client.send_json({"type": "input_audio_buffer.append", "audio": b64})

    await client.send_json({"type": "input_audio_buffer.commit"})
    logger.debug("PCM streaming complete: committed buffer")


async def run_audio_e2e(wav_path: str, *, chunk_ms: int = 100, timeout_sec: int = 90) -> int:
    """Run a single-shot audio E2E stream to Realtime; returns exit code 0/1."""
    cfg = _ensure_env()
    cfg.text_only = False
    client = RealtimeClient(cfg)
    await client.connect()
    try:
        logger.info("Starting audio E2E run: wav=%s chunk_ms=%d timeout=%d", wav_path, chunk_ms, timeout_sec)
        await client.send_session_update(turn_detection_type="none", force_audio=True)

        pcm, rate = _normalize_wav_to_pcm16_mono_16k(wav_path)
        logger.debug("WAV normalized: bytes=%d sample_rate=%d", len(pcm), rate)
        await stream_pcm_to_realtime(client, pcm, rate, chunk_ms=chunk_ms)

        await client.send_json({"type": "response.create"})
        logger.debug("Sent response.create")

        done_types = {"response.completed", "response.done"}
        try:
            async def _recv_loop():
                while True:
                    msg = await client.recv()
                    if isinstance(msg, (bytes, bytearray)):
                        print(f"[upstream-bytes] {len(msg)} bytes")
                        continue
                    print(f"[upstream] {msg}")
                    try:
                        obj = json.loads(msg)
                        if obj.get("type") in done_types:
                            return 0
                    except Exception:
                        pass

            rc = await asyncio.wait_for(_recv_loop(), timeout=timeout_sec)
            logger.info("Audio E2E completed with rc=%d", rc)
            return rc
        except asyncio.TimeoutError:
            logger.error("Timed out waiting for response completion")
            return 1
    finally:
        await client.close()


# Backwards-compat aliases for proxy imports
ensure_env = _ensure_env
build_system_instructions = _build_system_instructions
