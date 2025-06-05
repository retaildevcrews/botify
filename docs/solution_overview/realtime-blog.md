# Supercharge Your Python Apps with Real-Time AI Interactions

Ever wanted your applications to respond instantly, engaging users in natural, flowing conversations or providing live transcriptions? The Azure OpenAI Real-Time API makes this possible, offering low-latency, streaming capabilities for your AI models. If you're looking to build dynamic conversational AI, live assistants, or real-time transcription services, you're in the right place.

This post will guide you through an opinionated approach to integrating this powerful API into your Python backend, enabling you to get a demo up and running or kickstart your project quickly, even if you're new to real-time APIs.

### Why Go Real-Time?

Traditional API calls often involve waiting for the full response before processing. Real-time APIs, however, stream data, meaning:
- Reduced Wait Times: Users receive incremental outputs as they're generated.
- Interactive Experiences: Perfect for voice assistants, live chat, and other applications where immediate feedback is key.
- Versatile Inputs: Handle both text and audio, opening doors for speech-to-text and voice-enabled features.

Our solution leverages these benefits to create a responsive and engaging user experience. We've developed a Python class, [BotifyRealtime](../../apps/bot-service/api/realtime.py), designed to manage the complexities of interacting with the Azure OpenAI Real-Time API. It handles WebSocket connections, session configurations, message forwarding, and even tool integration.

Let's dive into some key components:

### Establishing the Connection

First, we need to connect to the Real-Time API endpoint using WebSockets. The `connect_to_realtime_api` method handles this:

```python

async def connect_to_realtime_api(self):
    headers = {"api-key": self.api_key}
    base_url = self.endpoint.replace("https://", "wss://")
    url = f"{base_url}/openai/realtime?api-version={self.api_version}&deployment={self.deployment}"

    try:
        self.session = aiohttp.ClientSession()
        self.ws_openai = await self.session.ws_connect(url, headers=headers, timeout=30)
        await self.send_session_config()
    except Exception as e:
        logger.error("Failed to connect to Azure OpenAI: %s", str(e))
        if self.session and not self.session.closed:
            await self.session.close()
        raise ConnectionError(f"Cannot connect to Azure OpenAI Realtime API: {str(e)}")

```

This snippet shows how we use `aiohttp` to establish an asynchronous WebSocket connection, passing necessary headers like the API key.

### Configuring the Session

Once connected, we need to tell the API how we want to interact. This is done by sending a session configuration. The `send_session_config` method prepares and sends this configuration:

```python

async def send_session_config(self):
    # Simple prompt without JSON filtering
    prompt_text = self.promptgen.generate_prompt(
        self.app_settings.prompt_template_paths, schema=ResponseSchema().get_response_schema()
    )

    # Basic realtime instructions
    enhanced_prompt = (
        "Use the Search-Tool for any information requests. "
        "Provide conversational responses with source links as markdown. " + prompt_text
    )

    # Simple session configuration
    config = {
        "type": "session.update",
        "session": {
            "modalities": ["text", "audio"], # We want both text and audio
            "instructions": enhanced_prompt, # System prompt for the model
            "voice": self.voice_choice,      # Preferred voice for audio output
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {"model": "whisper-1"},
            "turn_detection": {"type": "server_vad", "threshold": 0.2, "silence_duration_ms": 500},
            "tools": ( # Define any tools the model can use
                [
                    {
                        "type": "function",
                        "name": "Search-Tool",
                        "description": "Search the knowledge base for information",
                        "parameters": {
                            "type": "object",
                            "properties": {"query": {"type": "string", "description": "Search query"}},
                            "required": ["query"],
                        },
                    }
                ]
                if self.search_tool
                else []
            ),
            "tool_choice": "auto",
        },
    }

    await self.ws_openai.send_json(config)

```

Key parts of this configuration include:
- modalities: Specifies if you're using text, audio, or both.
- instructions: The system prompt to guide the AI's behavior.
- voice: The desired voice for text-to-speech output.
- tools: Defines functions the AI can call, like our custom search-tool that retrieves the necessary information from the internal knowledge base using a search query.

### Handling Bi-Directional Messaging

With WebSockets, communication is bi-directional. Our _forward_messages method orchestrates two concurrent tasks:

`_from_client_to_openai`: Listens for messages (e.g., audio chunks, text input) from your application's client and forwards them to the Azure OpenAI API.
`_from_openai_to_client`: Listens for messages (e.g., transcribed text, AI responses, audio output) from the API and forwards them to your client.
This asynchronous handling is crucial for a smooth, real-time flow.

### Integrating Tools: The Search-Tool Example

A powerful feature is the ability for the AI to use tools. In our setup, we've defined a search-tool, which searches an internal knowledge base and retrieves the relevant results for a given query. When the AI decides to use this tool, the API sends a function call request. Our `_handle_function_call` method processes this:

```python

async def _handle_function_call(self, function_call):
    """Simple function call handling"""
    tool_name = function_call["name"]
    arguments = json.loads(function_call["arguments"])
    tool_call_id = function_call["call_id"]

    if tool_name == "Search-Tool" and self.search_tool:
        try:
            query = arguments.get("query", "")
            result = await self.search_tool._arun(query) # Execute the search

            # Use custom serialization for tool results
            serialized_result = self._serialize_tool_result(result)

            tool_result = { # Send the result back to the API
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": tool_call_id,
                    "output": json.dumps(serialized_result),
                },
            }
            await self.ws_openai.send_json(tool_result)

            # Tell the API to continue generating a response
            continue_response = {
                "type": "response.create",
                "response": {"modalities": ["text", "audio"]},
            }
            await self.ws_openai.send_json(continue_response)

```

This method extracts the tool name and arguments, executes the tool (e.g., performs a search), and sends the results back to the API so it can formulate a final response.

### Approaching the Frontend

There are several ways you can build a component in your UI to capture voice input and playing back the bot response audio but the key feature is to establish a websocket/WebRTC connection with the Realtime API.

In our case, the `bot-service` application serves as a backend that connects to the Azure OpenAI Realtime API with additional processing like the search tools. We had the frontend connect to the `bot-service` application (via WebSocket) instead. However, any requests/responses are forwarded accordingly between the frontend to the bot-service and ultimately to AOAI seamlessly.

This is a simple layout of how the end-to-end connection looks like:

```
    Azure OpenAI Realtime API <-----------> Bot-Service <-----------> Frontend UI <-----------> User Input
```

Alternatively, you could also skip this proxy step and directly connect to the realtime API from the frontend. 

Here are some example frontend application/utilities by the OpenAI community that you can use as a reference in building out the frontend:
- [Realtime Solar System](https://github.com/openai/openai-realtime-solar-system/tree/main) - WebRTC connection to Realtime API
- [Realtime Console](https://github.com/openai/openai-realtime-console) - WebSocket and WebRTC options available
- [JS Realtime API Library](https://github.com/openai/openai-realtime-api-beta) - Reference Client to use OpenAI Realtime API

### Important Considerations

Based on our experience integrating this API, these are the key takeaways:

- Explicit Prompts for Tools: Be very clear in your system prompts to guide the model on when and how to use tools like the search-tool.
- Model Availability: Real-time models might have different regional availability compared to other Azure OpenAI models. Always check the [official documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/realtime-audio).
- End-to-End Testing: If using audio, remember that end-to-end testing becomes more complex but is vital for validating the full user experience.

### Next Steps

Integrating the Azure OpenAI Real-Time API can significantly enhance your applications. By leveraging a structured approach like the BotifyRealtime class, you can manage the complexities of real-time, bi-directional communication and tool usage effectively.

We encourage you to explore this API further. Consider testing its performance with more complex prompts or investigating alternative connection methods like WebRTC for potentially different performance characteristics.

Happy building!