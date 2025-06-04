# Real Time API

## Overview

The Real Time API allows applications to interact with Azure OpenAI models for low-latency, streaming inference. It is designed for scenarios where immediate responses are critical, such as conversational AI, live transcription, and interactive assistants. The API supports both text and audio inputs, enabling real-time chat and speech-to-text capabilities.

Key features include:

- **Streaming Responses:** Receive model outputs incrementally as they are generated, reducing wait times for users.
- **Low Latency:** Optimized for fast, interactive experiences, suitable for voice assistants and live chat.
- **Audio and Text Support:** Accepts audio input for speech-to-text and text input for chat or completion tasks.
- **Scalable and Secure:** Built on Azure infrastructure, supporting enterprise-grade security and compliance.
- **Flexible Integration:** Easily integrates with existing applications using REST APIs and SDKs.

Common use cases include real-time transcription, voice-enabled chatbots, live content moderation, and interactive virtual agents.

For more information, refer to the [Azure OpenAI Service real-time inference quickstart](https://learn.microsoft.com/azure/ai-services/openai/realtime-audio-quickstart).

## Opinions & Feedback

- The system prompt must be much more explicit to ensure the model calls search tools, unlike previous behavior without the Real Time API. See [Tool Usage Guidelines](../common.md#tool-usage-guidelines) for best practices.
- Model availability is more limited in terms of supported locations. See the [official list of supported regions for the Azure OpenAI Real Time API](https://learn.microsoft.com/azure/ai-services/openai/concepts/models#model-region-availability) for details.
- Currently experiencing a bug where the model sometimes responds in a different language than the input.
- End-to-end testing with audio introduces additional complexity but is necessary for comprehensive validation.

## Front End Changes to Support Real Time API

- Retained the existing interface and introduced a "Hands Free Mode" section.
- In Hands Free Mode, the text input field is disabled.
- Conversations in Hands Free Mode are transcribed in the same pane as invoke and streaming conversations.

## Next Steps

- Test this pattern in a more complex application with additional lang graph steps, a larger search index, and a significantly larger prompt to evaluate performance improvements.

## Contributors

| Name                | Contact                                  |
|---------------------|------------------------------------------|
| **Siva Mullapudi**  | 📧 [sivamu@microsoft.com](mailto:sivamu@microsoft.com)         |
| **Alfredo Hernandez** | 📧 [alfredoch@microsoft.com](mailto:alfredoch@microsoft.com) |
