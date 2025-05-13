import { sendMessageToBot } from './botservice';
import { playSpeechResponse, handleStreamingChunk } from '../utils/messageUtils';
import { InputMessage } from '../types';

export const processUserInput = async (
  userInput: string,
  useStreaming: boolean,
  {
    addUserMessage,
    updateOrAddBotMessage,
    resetWaitingStates,
    setWaitingForBot
  }: any,
  useTextToSpeech: boolean = false
) => {
  if (!userInput.trim()) return;

  // Add user message
  const allMessages: InputMessage[] = addUserMessage(userInput);

  // Set states
  setWaitingForBot();

  try {
    const sessionId = "session-id-placeholder";
    const userId = "user-id-placeholder";
    const speechService = await import('./speechService');

    if (!useStreaming) {
      // Non-streaming mode
      const response = await sendMessageToBot(allMessages, useStreaming, sessionId, userId);
      if (response) {
        // Add the bot message with content (this was missing)
        updateOrAddBotMessage(response.inputMessage.content || '');

        // Play speech response
        await playSpeechResponse(response, speechService, useTextToSpeech);
      }
      resetWaitingStates();
    } else {
      // Streaming mode
      await sendMessageToBot(
        allMessages,
        useStreaming,
        sessionId,
        userId,
        // Chunk handler for streaming text
        (chunk: string) => {
          handleStreamingChunk(
            chunk,
            updateOrAddBotMessage
          );
        },
      );
    }
  } catch (error) {
    console.error('Error processing message:', error);
    resetWaitingStates();
  }
};
