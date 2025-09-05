# Realtime Webapp (Vite + React + Tailwind)

This web app connects to the FastAPI realtime websocket at /realtime and streams microphone audio while rendering streaming text responses.

## Scripts

- dev: run the Vite dev server on port 5173
- build: type-check and build production assets

## Setup

- Install deps and run with Yarn:

```
# from apps/webapp
yarn install
yarn dev
```

Then open the URL printed (default <http://localhost:5173>). Configure the websocket URL to point to your FastAPI server (defaults to ws://localhost:8000/realtime).

If you see permission prompts for microphone access, allow them.

## Notes

- Audio is captured and resampled to 24kHz PCM16 base64 chunks before being sent as input_audio_buffer.append events.
- After stopping, the client sends input_audio_buffer.commit and response.create to request a response.
