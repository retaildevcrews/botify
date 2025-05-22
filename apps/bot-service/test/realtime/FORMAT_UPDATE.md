# Botify Realtime API Format Change

## Important Message Format Update

As of May 22, 2025, the format for sending audio data to the Botify Realtime API has changed to match the requirements of the Azure OpenAI Realtime API.

### Old Format (No Longer Supported)

```json
{
  "type": "input_audio_buffer.append",
  "data": {
    "audio": "base64EncodedAudioData"
  }
}
```

### New Format (Required)

```json
{
  "type": "input_audio_buffer.append",
  "audio": "base64EncodedAudioData"
}
```

## Why This Change Was Made

This format change was made to ensure compatibility with the Azure OpenAI Realtime API, which expects the `audio` field to be at the root level of the message. The previous nested format caused errors like:

```
API Error: {'input_audio_buffer.append.audio': [{'type': 'missing', 'msg': 'Field required'}]
```

## Tools for Testing

To help you test the new format, we've provided several tools:

1. **Format Test Client**: Use `/test/realtime/format_test.html` to test both formats and see the results
2. **Test Script**: Run `/test/realtime/test_audio_format.sh` to execute automated tests
3. **Documentation**: See `/test/realtime/AUDIO_FORMAT.md` for detailed format information

## Updating Custom Clients

If you're using a custom client to connect to the Botify Realtime API, you'll need to update your message format:

### JavaScript Example

```javascript
// Old format (no longer works)
const message = {
  type: 'input_audio_buffer.append',
  data: {
    audio: base64Data
  }
};

// New format (required)
const message = {
  type: 'input_audio_buffer.append',
  audio: base64Data
};
```

## Testing Your Connection

You can test your connection using the provided test client or with the following command:

```bash
python3 -c '
import json
import base64
import websocket

# Create a simple test message
audio_data = base64.b64encode(b"test_audio_data").decode("utf-8")
message = {
    "type": "input_audio_buffer.append",
    "audio": audio_data
}

# Connect and send the message
ws = websocket.create_connection("ws://localhost:8080/realtime")
ws.send(json.dumps(message))
response = ws.recv()
print(f"Response: {response[:100]}...")
ws.close()
'
```

## Questions or Issues?

If you're experiencing any issues with the new format, please refer to the documentation or contact the development team for assistance.
