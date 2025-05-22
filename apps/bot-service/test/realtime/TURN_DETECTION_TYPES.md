# Azure OpenAI Realtime API - Turn Detection Types

This document provides a reference for the available turn detection types in the Azure OpenAI Realtime API.

## Available Turn Detection Types

| Type | Description | End-of-Utterance Support |
|------|-------------|--------------------------|
| `server_vad` | Basic voice activity detection based on silence | No |
| `azure_semantic_vad` | Advanced semantic voice activity detection | No* |
| `azure_semantic_vad_en` | English-only semantic voice activity detection | No* |
| `azure_semantic_vad_multilingual` | Multilingual semantic voice activity detection | No* |
| `server_sd` | Simple silence detection | No |
| `none` | No turn detection | No |

**Note:** While the API documentation suggests these types support end-of-utterance detection, our testing indicates that it doesn't currently work and produces errors. We've disabled this feature in our implementation to ensure stability.

## Common Issues

### End-of-Utterance Detection Error

If you encounter this error:

```
End of utterance detection is only supported for cascaded pipelines
```

Or:

```
Input tag 'cascaded' found using 'type' does not match any of the expected tags
```

**Solution:**
Change your `AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE` to `azure_semantic_vad` in your credentials.env file. This type supports end-of-utterance detection.

## How to Change Turn Detection Type

You can use the `update_turn_detection.sh` script to change the turn detection type:

```bash
cd /workspaces/botify/apps/bot-service/test/realtime
./update_turn_detection.sh
```

Or manually update the AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE in your credentials.env file:

```
AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE="azure_semantic_vad"
```

Remember to restart the bot-service after making changes:

```bash
cd /workspaces/botify/apps
docker-compose restart bot-service
```
