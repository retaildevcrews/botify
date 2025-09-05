# Apps Tools

This directory contains canonical CLI tools for the project.

## Realtime audio E2E CLI

Headless CLI to stream a local WAV file to the upstream Realtime API (Azure/OpenAI) without running the web proxy.

- Script: `apps/tools/test_realtime_audio.py`
- Requirements: `AZURE_OPENAI_*` or `OPENAI_*` environment variables; optional `REALTIME_*` flags

Example:

```bash
python3 apps/tools/test_realtime_audio.py \
  --wav /workspaces/starbucks_menu/audio/orders1/segment_008.wav \
  --chunk-ms 100 \
  --timeout 90
```

What it does:

- Renders system instructions from Jinja template and menu text
- Opens a WebSocket to the Realtime endpoint (Azure or OpenAI)
- Normalizes audio to PCM16 mono 16 kHz and streams in ~100 ms chunks
- Commits the buffer and sends `response.create`
- Prints upstream events until `response.done`

Optional pytest:

```bash
RUN_REALTIME_E2E=1 pytest -q tests/test_realtime_audio.py
```
