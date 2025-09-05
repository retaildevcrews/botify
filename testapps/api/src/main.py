from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse

from realtime.realtime_common import (
    _ensure_env,
)
from realtime.realtime_session import RealtimeSession

app = FastAPI(title="Realtime Proxy")

# Module-level logger
logger = logging.getLogger("api.realtime.main")

# Initialize root logging so our module loggers emit to the terminal.
# Honours LOG_LEVEL env (e.g., INFO or DEBUG). Defaults to INFO.
_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
_level = getattr(logging, _level_name, logging.INFO)
try:
    # If Uvicorn configured logging, piggyback on its error handlers so our loggers emit.
    uvicorn_error = logging.getLogger("uvicorn.error")
    for name in ("api.realtime.main", "realtime-common", "realtime_session"):
        lg = logging.getLogger(name)
        if not lg.handlers and uvicorn_error.handlers:
            for h in uvicorn_error.handlers:
                lg.addHandler(h)
            lg.propagate = False
        lg.setLevel(_level)
    # Also set root level (in case no handlers are present, basicConfig as fallback)
    root = logging.getLogger()
    root.setLevel(_level)
    if not root.handlers:
        logging.basicConfig(
            level=_level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
    logger.info("Logging configured with level %s", _level_name)
except Exception:
    # Fallback minimal config
    logging.basicConfig(level=_level)
    logger.info("Logging configured (fallback) with level %s", _level_name)


@app.get("/healthz")
async def healthz():
    try:
        _ = _ensure_env()
        return JSONResponse({"ok": True})
    except Exception as ex:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(ex)}, status_code=500)


@app.websocket("/realtime")
async def realtime_ws(ws: WebSocket):
    await ws.accept()
    # Log connection accepted with client address (if available)
    try:
        client_host = getattr(getattr(ws, "client", None), "host", "?")
        client_port = getattr(getattr(ws, "client", None), "port", "?")
        logger.info("[realtime] WebSocket connected from %s:%s", client_host, client_port)
    except Exception:  # noqa: BLE001
        # Do not fail the connection on logging error
        pass
    try:
        cfg = _ensure_env()
    except Exception as ex:  # noqa: BLE001
        logger.error("[realtime] Env initialization failed: %s", ex)
        await ws.send_text(json.dumps({"type": "error", "error": str(ex)}))
        await ws.close(code=1011)
        return
    session = RealtimeSession(ws, cfg)
    try:
        await session.connect_openai()
        logger.info("[realtime] Connected to upstream realtime service")
        await session.send_session_update()
        logger.debug("[realtime] Sent initial session.update to upstream")
        to_upstream = asyncio.create_task(session.pump_client_to_openai())
        to_client = asyncio.create_task(session.pump_openai_to_client())
        logger.debug("[realtime] Started forwarding tasks: client->upstream and upstream->client")
        await asyncio.wait({to_upstream, to_client}, return_when=asyncio.FIRST_COMPLETED)
        # Log which direction completed first and any exception
        if to_upstream.done():
            exc = to_upstream.exception()
            if exc:
                logger.error("[realtime] client->upstream forwarding terminated with error: %s", exc)
            else:
                logger.debug("[realtime] client->upstream forwarding completed")
        if to_client.done():
            exc = to_client.exception()
            if exc:
                logger.error("[realtime] upstream->client forwarding terminated with error: %s", exc)
            else:
                logger.debug("[realtime] upstream->client forwarding completed")
    finally:
        logger.info("[realtime] Cleaning up session")
        await session.cleanup()
