# Botify Realtime API Endpoint

This document provides information on using the realtime WebSocket endpoint for voice interactions with the Botify service.

## Overview

The realtime endpoint enables real-time audio streaming communications between the client and the AI model, using the Azure OpenAI Realtime API. This allows for a more dynamic and interactive experience with voice capabilities.

## Endpoints

- WebSocket: `/realtime` - Main WebSocket endpoint for realtime voice interactions
- REST: `/realtime-info` - Information endpoint for the realtime API (documented in Swagger UI)

## Swagger Documentation

The realtime API is now documented in the Swagger UI. To access the documentation:

1. Open your browser and navigate to: `http://localhost:8080/docs`
2. Look for the "GET /realtime-info" endpoint in the API documentation
3. Click "Try it out" to see the response format and available options

The Swagger documentation provides detailed information about:

- Available voice options
- Required environment variables
- Message formats
- Testing resources

## Required Environment Variables

To use the realtime endpoint, the following environment variables must be configured:

- `AZURE_OPENAI_API_KEY`: API key for Azure OpenAI
- `AZURE_OPENAI_ENDPOINT`: Endpoint URL for Azure OpenAI
- `AZURE_OPENAI_REALTIME_DEPLOYMENT`: The deployment name for the Azure OpenAI realtime model
- `SPEECH_ENGINE`: Either "openai" or "azure" (defaults to "openai" if not set)
- `AZURE_OPENAI_REALTIME_VOICE_CHOICE`: Voice to use for the assistant (defaults to "coral" if not set)

If using the Azure Speech Services as the engine:

- `AZURE_SPEECH_SERVICES_KEY`: API key for Azure Speech Services
- `AZURE_SPEECH_SERVICES_ENDPOINT`: Endpoint URL for Azure Speech Services

## Configuration Options

Additional configuration options for the realtime functionality:

- `DEBOUNCE_DELAY`: Time in seconds to wait before generating a response (default: 1.5)
- `THROTTLE_MIN_INTERVAL`: Minimum time in seconds between responses (default: 4)
- `AZURE_OPENAI_REALTIME_VAD_THRESHOLD`: Voice activity detection threshold (default: 0.2)
- `AZURE_OPENAI_REALTIME_VAD_SILENCE_DURATION_MS`: Silence duration in milliseconds to trigger end of utterance (default: 500)

## Client Integration

To connect to the realtime endpoint from a client application:

1. Establish a WebSocket connection to the `/realtime` endpoint
2. Send audio data using the appropriate message format (see example below)
3. Process responses as they arrive from the server

## Message Format

### Client to Server (example)

```json
{
  "type": "input_audio_buffer.append",
  "data": "BASE64_ENCODED_AUDIO_DATA"
}
```

### Server to Client

The server will forward messages from the Azure OpenAI Realtime API to the client, including:

- Transcription updates
- Audio transcript deltas
- Tool calls and results
- Error messages

## Using with Search Functionality

The realtime endpoint integrates with the same search tools used by the rest of the Botify service, ensuring consistent responses across all interaction methods.

## Example Client Implementation

For a reference client implementation, see the sample code in the `apps/sample-realtime` directory.
