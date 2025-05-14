import { InputMessage, Message } from '../App';
import { makeStreamingJsonRequest } from "http-streaming-request";

const backendApiPrefix = import.meta.env.VITE_BACKEND_API_ENDPOINT_PREFIX;

if (!backendApiPrefix) {
  console.error('VITE_BACKEND_API_ENDPOINT_PREFIX is not defined in the environment variables.');
}

// Define the streaming chunk type based on backend response
export interface StreamingBotChunk {
  displayResponse?: string;
  [key: string]: unknown;
}

export const sendMessageToBot = async (
  inputMessages: InputMessage[],
  useStreaming: boolean,
  sessionId: string,
  userId: string,
  onStreamChunk?: (chunk: string) => void,
  onStreamEnd?: (chunk: StreamingBotChunk | null) => void,
): Promise<Message | null> => {
  const apiUrl = useStreaming
    ? `${backendApiPrefix}/stream_events`
    : `${backendApiPrefix}/invoke`;

  try {
    if (useStreaming) {
      let lastDisplay = "";
      let jsonResponse: StreamingBotChunk | null = null;
      for await (const chunk of makeStreamingJsonRequest<StreamingBotChunk>({
        url: import.meta.env.VITE_BACKEND_API_ENDPOINT_PREFIX + "/stream_events",
        method: "POST",
        payload: {
          input: { messages: inputMessages },
          config: {
            configurable: {
              session_id: sessionId,
              user_id: userId,
            },
          },
        },
      })){
          jsonResponse=chunk;
          if (chunk && chunk.displayResponse) {
            // Only append new text
            const newText = chunk.displayResponse.slice(lastDisplay.length);
            if (newText) {
              lastDisplay = lastDisplay + newText;
              onStreamChunk?.(newText);
            }
          }
      }
      onStreamEnd?.(jsonResponse);
      return null; // No single message to return for streaming
      }

      else {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input: { messages: inputMessages },
          config: {
            configurable: {
              session_id: sessionId,
              user_id: userId,
            },
          },
        }),
      });

      const data = await response.json();
      const botResponse = JSON.parse(data.messages?.[data.messages.length - 1].content);
      const displayResponse = botResponse?.displayResponse;

      return {
        inputMessage: {
          role: 'ai',
          content: displayResponse
        },
        timestamp: new Date().toISOString()
      };
    }
  } catch (error) {
    console.error('Error sending message to bot:', error);
    return null;
  }
};
