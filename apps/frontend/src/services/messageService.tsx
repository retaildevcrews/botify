import { sendMessageToBot } from './botservice';
import { playSpeechResponse, handleStreamingChunk, handleStreamingComplete } from '../utils/messageUtils';
import { InputMessage, StreamingResponse } from '../types';
import { MessageManager } from '../hooks/useMessageManager';

export const processUserInput = async (
  userInput: string,
  useStreaming: boolean,
  messageManager: MessageManager,
  useTextToSpeech: boolean = false,
  sessionId: string,
  setIsListening: (isListening: boolean) => void
) => {
  if (!userInput.trim()) return;

  // Add user message
  const allMessages: InputMessage[] = messageManager.addUserMessage(userInput);

  // Set states
  messageManager.setWaitingForBot();

  try {
    const userId = "user-id-placeholder";
    const speechService = await import('./speechService');

    if (!useStreaming) {
      // Non-streaming mode
      const response = await sendMessageToBot(allMessages, useStreaming, sessionId, userId);
      if (response) {
        // Add the bot message with content (this was missing)
        messageManager.updateOrAddBotMessage(response.inputMessage.content || '');

        // After speech synthesis is complete, reset the waiting states
        messageManager.resetWaitingStates();

        // First play the speech response without setting the listening state
        // This way the microphone doesn't show as listening while the AI is speaking
        const autoDetectedSpeech = await playSpeechResponse(response, speechService, useTextToSpeech, setIsListening);

        // Only start auto-listening if speech is enabled
        if (useTextToSpeech) {
          // If speech was detected, process it
          if (autoDetectedSpeech && autoDetectedSpeech.trim()) {
            // Process the auto-detected speech as a new user message
            await processUserInput(
              autoDetectedSpeech,
              useStreaming,
              messageManager,
              useTextToSpeech,
              sessionId,
              setIsListening
            );
            return; // Exit to avoid duplicate resetWaitingStates call
          }
        } else {
          // If speech is disabled, no need to wait for auto-listening
          messageManager.resetWaitingStates();
        }

        // If we got auto-detected speech after the AI response, process it as a new user input
        if (autoDetectedSpeech && autoDetectedSpeech.trim()) {
          messageManager.resetWaitingStates();

          // Process the auto-detected speech as a new user message
          await processUserInput(
            autoDetectedSpeech,
            useStreaming,
            messageManager,
            useTextToSpeech,
            sessionId,
            setIsListening
          );
          return; // Exit to avoid duplicate resetWaitingStates call
        }
      }
      messageManager.resetWaitingStates();
    } else {
      messageManager.setStreamComplete(false);

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
            messageManager.updateOrAddBotMessage
          );
        },
        // JSON handler for final response
        async (json: StreamingResponse | null) => {
          messageManager.setStreamComplete(true);

          // Create a function to process speech detected after streaming
          const processUserSpeech = async (transcript: string) => {
            if (transcript.trim()) {
              // Process the auto-detected speech as a new user message
              await processUserInput(
                transcript,
                useStreaming,
                messageManager,
                useTextToSpeech,
                sessionId,
                setIsListening
              );
            }
          };

          await handleStreamingComplete(
            json,
            speechService,
            useTextToSpeech,
            setIsListening,
            processUserSpeech
          );

          messageManager.resetWaitingStates();
        }
      );
    }
  } catch (error) {
    console.error('Error processing message:', error);
    messageManager.resetWaitingStates();
  }
};
