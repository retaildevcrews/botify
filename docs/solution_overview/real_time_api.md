# Real Time API

## Overview

The Real Time API enables applications to interact with AI models and data sources instantly, supporting low-latency, high-throughput scenarios. Leveraging Azure and OpenAI services, this API provides secure, scalable endpoints for real-time inference, chat, and data processing. Key features include:

- **Low Latency:** Optimized for rapid response, suitable for conversational AI, live analytics, and interactive applications.
- **Scalability:** Built on Azure infrastructure, supporting dynamic scaling to handle varying workloads.
- **Security:** Integrates with Azure Active Directory and supports role-based access control, ensuring secure data handling.
- **Flexibility:** Supports multiple AI models, including OpenAI GPT and Azure Cognitive Services, with customizable endpoints.
- **Monitoring:** Provides logging, metrics, and diagnostics through Azure Monitor for operational visibility.

Typical use cases include chatbots, real-time content moderation, live recommendations, and interactive virtual assistants.

For more details, see the [Azure OpenAI Service documentation on real-time inference](https://learn.microsoft.com/en-us/azure/ai-services/openai/realtime-audio-quickstart).

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
