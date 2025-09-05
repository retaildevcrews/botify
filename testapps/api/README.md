# FastAPI Realtime Proxy

A lightweight WebSocket proxy to Azure/OpenAI Realtime that mirrors the prompt-loading approach used in `gotaglio/gpt_completions/menu_pipeline.py`.

## Endpoints

- GET /healthz — simple health check
- WS /realtime — WebSocket that proxies audio/text frames to Azure/OpenAI Realtime and streams events back

## Environment

Create a `.env` at the repo root (or use environment variables) with:

- AZURE_OPENAI_API_KEY=...
- AZURE_OPENAI_ENDPOINT=...           # e.g. <https://my-aoai.openai.azure.com>
- AZURE_OPENAI_DEPLOYMENT=...         # e.g. gpt-4o-realtime-preview
- AZURE_OPENAI_API_VERSION=2024-10-01 # or appropriate
- REALTIME_TEXT_ONLY=false             # true to disable audio input/outputs
- REALTIME_AUTO_CLOSE=true             # end session after first response.done
- REALTIME_VOICE=alloy                 # optional voice
- REALTIME_HEARTBEAT_SEC=10            # heartbeat interval
- REALTIME_MAX_MSG_MB=15               # max message size
- REALTIME_MENU_PATH=menu/menu.ts      # resolved relative to apps/api
- REALTIME_TEMPLATE_PATH=prompt_templates/template.txt
  - REALTIME_SCHEMA_PATH (optional) can be supplied if you want to inject a schema placeholder

## Local run

Use Poetry to ensure dependencies are installed, then run uvicorn:

```bash
poetry install
uvicorn main:app --app-dir apps/api/src --reload --host 0.0.0.0 --port 8000
```

Then connect a WS client to ws://localhost:8000/realtime.

## Docker

- A Dockerfile is provided to run the API in a container.
- The docker-compose file at `apps/docker-compose.yml` loads environment variables from `apps/api/.env`.
  - Create `apps/api/.env` (or copy from `.env.example`) when using Compose.

## Event filtering

By default, the proxy only forwards the streaming text events from upstream back to the client:

- response.text.delta
- response.text.done

You can override this with an allowlist using `REALTIME_ALLOWED_EVENT_TYPES`, which accepts a comma-separated list of glob patterns matching the `type` field of upstream JSON events. A special token `<binary>` controls forwarding of non-JSON binary frames.

Examples:

- `REALTIME_ALLOWED_EVENT_TYPES=response.text.*` — forward all text stream events
- `REALTIME_ALLOWED_EVENT_TYPES=*` — forward everything
- `REALTIME_ALLOWED_EVENT_TYPES=response.*.done,response.*.delta` — only done/delta of any response subtype
- `REALTIME_ALLOWED_EVENT_TYPES=<binary>,response.*` — forward binary audio and any `response.*` JSON events

## JSON extraction (optional)

You can configure the proxy to extract and forward only the JSON payload embedded in upstream text events (e.g., from `response.text.done`). This is disabled by default; when enabled, the proxy will parse JSON from the chosen text field and send either the JSON alone (replace) or a small envelope (wrap).

Environment flags:

- `REALTIME_EXTRACT_JSON_FROM_TEXT_TYPES` — comma-separated glob patterns of event types to extract from (e.g., `response.text.done`)
- `REALTIME_EXTRACT_FIELDS_MAP` — semicolon-separated per-type field mapping. Format: `type_glob:fieldA[,fieldB];type2:fieldX`
  - Example: `response.text.done:text;response.text.delta:delta`
- `REALTIME_EXTRACT_JSON_TEXT_FIELD` — global fallback field if no per-type mapping applies (default: `text`)
- `REALTIME_EXTRACT_JSON_STRATEGY` — `fenced_or_bare` (default), `strict_fence`, `first_object`
- `REALTIME_EXTRACT_OUTPUT_MODE` — `replace` (send only JSON) or `wrap` (envelope with `payload`)
- `REALTIME_EXTRACT_ON_FAIL` — `drop` (default), `forward` (send original event), or `error` (send `{type:"extracted.json.error", ...}`)

Minimal example (emit only the JSON object from `response.text.done`):

```bash
REALTIME_ALLOWED_EVENT_TYPES=response.text.done
REALTIME_EXTRACT_JSON_FROM_TEXT_TYPES=response.text.done
REALTIME_EXTRACT_FIELDS_MAP=response.text.done:text
REALTIME_EXTRACT_JSON_STRATEGY=fenced_or_bare
REALTIME_EXTRACT_OUTPUT_MODE=replace
REALTIME_EXTRACT_ON_FAIL=drop
```

Wrap mode example (envelope with metadata):

```bash
REALTIME_EXTRACT_OUTPUT_MODE=wrap
```
