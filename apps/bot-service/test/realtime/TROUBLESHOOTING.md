# Realtime Voice API Troubleshooting Guide

## Common Issues and Solutions

### Internal Server Error

If you encounter an "Internal server error" with error details like:

```json
OpenAI Realtime API error: {'message': 'Internal server error', 'type': 'server_error', 'code': 'internal_error', 'param': 'turn_detection', 'event_id': 'abc123'}
```

**Possible causes and solutions:**

1. **Turn Detection Configuration**
   - The error may occur due to incompatible turn detection settings
   - For `azure_semantic_vad`, only certain parameters are supported:
     - `threshold` - Recommended value: 0.2
     - `silence_duration_ms` - Recommended value: 500
   - **Important**: When using `azure_semantic_vad`, you must also configure noise reduction:

     ```json
     "input_audio_noise_reduction": {
         "type": "azure_deep_noise_suppression"
     }
     ```

   - Our system now automatically uses a simplified configuration for this type

2. **Audio Format Issues**
   - Ensure your audio is using the right format (PCM16 mono, 16kHz)
   - Audio must be properly base64 encoded
   - Audio data must be in the correct field format (`audio` at root level)

3. **Connection Configuration**
   - Verify that the WebSocket connection is properly established
   - Check that the proper API endpoint is being used
   - Validate that the API key has proper permissions

### WebSocket Connection Issues

If you're having trouble with WebSocket connections:

1. **Check server logs** for detailed information about connection issues
2. **Verify WebSocket libraries** are properly installed
3. **Check environment variables**:
   - `AZURE_SPEECH_SERVICES_VAD_THRESHOLD` - Controls sensitivity of voice detection
   - `AZURE_SPEECH_SERVICES_VAD_SILENCE_DURATION_MS` - Controls how long silence must be to end a turn
   - `REALTIME_TURN_DETECTION_TYPE` - The type of turn detection to use (`server_vad`, `azure_semantic_vad`, or `cascaded`)
4. **Test with the simplified test client** in `/test/realtime/test_with_error_monitoring.py`

### Error Types and Recovery

| Error Type | Error Code | Description | Recovery |
|------------|------------|-------------|----------|
| `server_error` | `internal_error` | Internal server error from Azure OpenAI | Automatic retry with simplified config |
| `client_error` | `invalid_request_error` | Issue with client request format | Fix message format on client |
| `configuration_error` | Various | Misconfiguration in server settings | Change server environment variables |

### Message Format

Ensure your audio messages follow this format:

```json
{
  "type": "input_audio_buffer.append",
  "audio": "base64EncodedAudioData"
}
```

Followed by a flush message:

```json
{
  "type": "input_audio_buffer.flush"
}
```

## Testing Tools

Several test scripts are available to help verify your connection:

- `test_real_audio.py` - Tests with realistic audio data
- `test_with_error_monitoring.py` - Provides detailed error information
- `test_audio_format.py` - Tests basic audio transmission

## Recent Fixes

Recent updates have improved:

1. Turn detection configuration for `azure_semantic_vad`:
   - Added proper parameter filtering for different turn detection types
   - Included automatic noise reduction configuration when needed
   - Added recovery mechanism for configuration errors

2. Enhanced error handling and reporting:
   - More detailed error logs with parameter, event ID, and error type information
   - Improved client-side error display and handling
   - Added reconnection suggestions for configuration errors

3. Recovery mechanisms for internal server errors:
   - System now attempts to recover with simplified configuration
   - Event logging for tracking recovery attempts and success
   - Improved client error information:

4. WebSocket client enhancements:
   - Client now shows detailed error information
   - Troubleshooting suggestions are provided in the UI

If you encounter any other issues, please refer to the detailed logs which now include more diagnostic information.

## Reconnection Strategy

The system implements an automatic reconnection strategy:

1. For temporary network issues - automatic retry up to 3 times
2. For configuration errors - suggestion to reconnect with updated settings
3. For persistent server errors - fallback to simplified configuration

## Audio Format Requirements

For best results:

- Use PCM16 format audio
- Sample rate: 16kHz
- Channels: Mono (1 channel)
- Chunk size: 4096 samples recommended
