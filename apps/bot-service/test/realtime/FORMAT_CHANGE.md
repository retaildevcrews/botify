# WebSocket Format Changes

## Update (2025-05-22)

The format for sending audio data to the real-time API has changed. Previously, the audio data was sent in a nested format:

```json
{
  "type": "input_audio_buffer.append",
  "data": {
    "audio": "BASE64_ENCODED_AUDIO_DATA"
  }
}
```

This format is no longer supported. The new format places the audio data directly at the root level:

```json
{
  "type": "input_audio_buffer.append",
  "audio": "BASE64_ENCODED_AUDIO_DATA"
}
```

## Why This Changed

This change was made to be compatible with the Azure OpenAI Realtime API format requirements. Using the incorrect format will result in an error like:

```
API Error: {'input_audio_buffer.append.audio': [{'type': 'missing', 'msg': 'Field required'}]
```

## Updating Your Code

If you're using a custom client, update your message formatting to use the new format. The test client in `/workspaces/botify/apps/bot-service/test/realtime/index.html` has been updated already.

For more information, see the [AUDIO_FORMAT.md](./AUDIO_FORMAT.md) file.
