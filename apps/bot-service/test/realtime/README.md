# Testing the Botify Realtime API

This guide walks you through the process of testing the Botify Realtime API endpoint.

## Prerequisites

- Docker and Docker Compose installed
- Access to the Botify development environment
- A modern web browser with microphone access
- Required environment variables set in `credentials.env`

## Starting the Services

1. Navigate to the Botify apps directory:

   ```bash
   cd /workspaces/botify/apps
   ```

2. Ensure the credentials.env file contains all required environment variables for the realtime API (see below).

3. Start the services using Docker Compose:

   ```bash
   docker-compose up -d
   ```

4. Verify that the bot-service container is running:

   ```bash
   docker-compose ps
   ```

## Required Environment Variables

Ensure these variables are set in your credentials.env file:

```
# Realtime API Configuration
AZURE_OPENAI_REALTIME_DEPLOYMENT="gpt-4o-mini"
AZURE_OPENAI_REALTIME_VOICE_CHOICE="coral"
AZURE_SPEECH_SERVICES_KEY="your-speech-services-key"
AZURE_SPEECH_SERVICES_ENDPOINT="your-speech-services-endpoint"
# Use "server_vad" for standard voice activity detection or "cascaded" if you need end-of-utterance detection
AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE="server_vad"
AZURE_SPEECH_SERVICES_VAD_THRESHOLD="0.2"
AZURE_SPEECH_SERVICES_VAD_SILENCE_DURATION_MS="500"
AZURE_OPENAI_REALTIME_VAD_THRESHOLD="0.2"
AZURE_OPENAI_REALTIME_VAD_SILENCE_DURATION_MS="500"
DEBOUNCE_DELAY="1.5"
THROTTLE_MIN_INTERVAL="4"
GPT4O_DEPLOYMENT_NAME="gpt-4o-mini"
```

### Note on Turn Detection Types

There are several turn detection types available:

1. **server_vad** (default): Basic voice activity detection that uses silence detection to determine when a user has finished speaking.

2. **azure_semantic_vad**: Advanced semantic detection for better turn detection accuracy.

3. **azure_semantic_vad_en**: English-only version of semantic detection.

4. **azure_semantic_vad_multilingual**: Multilingual version of semantic detection.

5. **server_sd**: Simple silence detection.

6. **none**: No turn detection.

**Important Note**: Although the Azure OpenAI documentation suggests that certain turn detection types support end-of-utterance detection, our testing indicates that attempting to use this feature results in errors. We've disabled end-of-utterance detection in our implementation to maintain stability.

## Using the Test Client

1. Open the test client in your browser:

   ```bash
   $BROWSER /workspaces/botify/apps/bot-service/test/realtime/index.html
   ```

   Or navigate to the file in VS Code and use the "Open with Live Server" extension if available.

2. Configure the connection settings:
   - Host: The hostname or IP address of the Botify server (default: localhost)
   - Port: The port number of the Botify server (default: 8080)
   - Path: The WebSocket endpoint path (default: /realtime)

3. In the test client:
   - Click "Connect" to establish a WebSocket connection to the server.
   - Click "Start Recording" to begin capturing audio from your microphone.
   - Speak into your microphone to ask questions.
   - Click "Stop Recording" when you're done speaking.
   - The transcription of your speech and the assistant's responses will appear in the Messages section.

## Troubleshooting

### WebSocket Connection Issues

- Verify that the bot-service container is running.
- Check that port 8080 is accessible and not blocked by a firewall.
- Examine the bot-service logs for errors:

  ```bash
  docker-compose logs -f bot-service
  ```

### Common WebSocket Errors

If you see "WebSocket error: undefined" or "Disconnected from server" messages:

1. **Missing WebSocket Library**: The bot-service container might be missing the required WebSocket library. Check the logs for:

   ```
   No supported WebSocket library detected. Please use "pip install 'uvicorn[standard]'", or install 'websockets' or 'wsproto' manually.
   ```

   To fix this, rebuild the bot-service container:

   ```bash
   docker-compose build bot-service
   docker-compose up -d
   ```

2. **CORS Issues**: The server may be rejecting the connection due to CORS policies. Check the server logs.

3. **Connection Refused**: Make sure the server is running on port 8080 and the WebSocket endpoint is properly set up.

3. **Network Configuration**: If you're running in a container or VM, ensure port forwarding is correctly configured.

4. **Custom WebSocket Configuration**: You can customize the WebSocket connection in three ways:
   - Use the connection settings form in the test client UI
   - Pass URL parameters: `?host=your-host&port=9090&path=/custom-path`
   - Use the full server parameter: `?server=ws://your-server:port/realtime`

5. **Check Required Environment Variables**: Make sure all required environment variables are set in the credentials.env file:

   ```bash
   docker-compose exec bot-service env | grep AZURE_OPENAI
   ```

6. **Inspect Network Traffic**: Use the browser's developer tools (Network tab) to see WebSocket connection attempts and errors.

### Audio Recording Issues

- Ensure your browser has permission to access your microphone.
- Try using a different browser if you encounter microphone access issues.
- Check the browser console for any errors related to audio capture.

### Response Issues

- Verify that all required environment variables are properly set.
- Check that the Azure OpenAI Realtime deployment is available and functioning.
- Examine the logs for any errors during tool or model invocation.

## New Testing Tools

We've added several new testing tools to make it easier to diagnose and fix issues with the Realtime API:

### Quick Test Script

For a quick connectivity test without browser setup:

```bash
cd /workspaces/botify/apps/bot-service/test/realtime
./quick_test.py
```

This script sends a simple audio packet and verifies that the connection works properly.

### Error Monitoring Test

For detailed error diagnostics:

```bash
./test_with_error_monitoring.py --debug
```

This enhanced test provides:

- Detailed error information including error type, code, parameters, and event IDs
- Server status checking
- Configuration validation
- Turn detection compatibility testing

### Command-Line Options

All test scripts support these options:

```bash
--host HOST     Hostname to connect to (default: localhost)
--port PORT     Port to connect to (default: 8080)
--path PATH     WebSocket path (default: /realtime)
--debug         Enable debug logging (where supported)
```

## Improved Error Handling

The latest updates include enhanced error handling in both the server and client components:

1. **Server-side recovery**: The server now attempts to recover from internal errors by:
   - Detecting configuration incompatibilities
   - Adjusting turn detection settings automatically
   - Providing detailed error information to the client

2. **Client-side handling**: The test client now:
   - Displays formatted error information with type, code, and parameters
   - Suggests troubleshooting steps based on the error type
   - Offers automatic reconnection after configuration errors

## Common Error Types

| Error Type | Description | Resolution |
|------------|-------------|------------|
| `internal_error` | Server-side issue in Azure OpenAI | Check turn detection settings and server logs |
| `invalid_request_error` | Client request format problem | Ensure correct message format and audio encoding |
| `configuration_error` | Server misconfiguration | Check environment variables |

For detailed troubleshooting steps, see the [TROUBLESHOOTING.md](TROUBLESHOOTING.md) guide.

## Advanced Testing

For more advanced testing and debugging:

1. Modify the test client code to add more logging or customize the behavior.
2. Use browser developer tools to inspect WebSocket traffic.
3. Test with different audio inputs to ensure the system responds appropriately.

## Next Steps

After confirming that the realtime API works with the test client, you can:

1. Integrate the realtime API into your main application frontend.
2. Customize the prompts and tools available through the realtime interface.
3. Optimize performance by adjusting the configuration parameters.
