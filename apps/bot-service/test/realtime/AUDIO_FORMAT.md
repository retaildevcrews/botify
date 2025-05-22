# Audio Data Format for Azure OpenAI Realtime API

This document details the correct format for sending audio data to the Azure OpenAI Realtime API through the Botify service.

## WebSocket Message Format

When sending audio data to the WebSocket endpoint, the message should have the following structure:

```json
{
  "type": "input_audio_buffer.append",
  "audio": "<base64-encoded-audio-data>"
}
```

### Important Notes

1. The `audio` field must be at the root level of the message, not nested inside a `data` object.
2. The audio data must be base64-encoded.
3. The audio should be in PCM16 format, 16kHz mono for optimal compatibility.

## Common Errors

### Missing Audio Field

If you encounter this error:

```
'input_audio_buffer.append.audio': [{'type': 'missing', 'msg': 'Field required'}]
```

This means your message is not formatted correctly. Make sure:

1. Your message has the correct structure as shown above
2. The `audio` field is at the root level of the message
3. The base64-encoded audio data is properly formatted

### Incorrect Format (Nested Data)

⚠️ The following format is **NO LONGER SUPPORTED** and will result in errors:

```json
{
  "type": "input_audio_buffer.append",
  "data": {
    "audio": "<base64-encoded-audio-data>"
  }
}
```

### Invalid Audio Data

If you encounter errors relating to invalid audio data:

1. Ensure you're using a supported audio format (PCM16 is recommended)
2. Check that the base64 encoding is correct
3. Verify the audio sample rate (16kHz is recommended)

## Example Code (JavaScript)

```javascript
// Example of correctly formatting audio data
const fileReader = new FileReader();
fileReader.onload = function() {
  const base64Data = fileReader.result.split(',')[1];
  const message = {
    type: 'input_audio_buffer.append',
    audio: base64Data  // Note: audio is at root level, not inside a data object
  };

  // Send the message
  socket.send(JSON.stringify(message));
};
fileReader.readAsDataURL(audioBlob);
```
