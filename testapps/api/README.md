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
