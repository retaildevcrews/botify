import { sendMessageToBot } from './botservice';
import { playSpeechResponse, handleStreamingChunk, handleStreamingComplete } from '../utils/messageUtils';
import { InputMessage, StreamingResponse } from '../types';

export const processUserInput = async (
  userInput: string,
  useStreaming: boolean,
  {
    addUserMessage,
    updateOrAddBotMessage,
    resetWaitingStates,
    setWaitingForBot,
    setStreamComplete
  }: any,
  useTextToSpeech: boolean = false,
  sessionId: string,
  setIsListening: (isListening: boolean) => void
) => {
  if (!userInput.trim()) return;

  // Add user message
  const allMessages: InputMessage[] = addUserMessage(userInput);

  // Set states
  setWaitingForBot();

  try {
    const userId = "user-id-placeholder";
    const speechService = await import('./speechService');

    if (!useStreaming) {
      // Non-streaming mode
      const response = await sendMessageToBot(allMessages, useStreaming, sessionId, userId);
      if (response) {
        // Add the bot message with content (this was missing)
        updateOrAddBotMessage(response.inputMessage.content || '');

        // After speech synthesis is complete, reset the waiting states
        resetWaitingStates();

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
              {
                addUserMessage,
                updateOrAddBotMessage,
                resetWaitingStates,
                setWaitingForBot,
              },
              useTextToSpeech,
              sessionId,
              setIsListening
            );
            return; // Exit to avoid duplicate resetWaitingStates call
          }
        } else {
          // If speech is disabled, no need to wait for auto-listening
          resetWaitingStates();
        }

        // If we got auto-detected speech after the AI response, process it as a new user input
        if (autoDetectedSpeech && autoDetectedSpeech.trim()) {
          resetWaitingStates();

          // Process the auto-detected speech as a new user message
          await processUserInput(
            autoDetectedSpeech,
            useStreaming,
            {
              addUserMessage,
              updateOrAddBotMessage,
              resetWaitingStates,
              setWaitingForBot,
            },
            useTextToSpeech,
            sessionId,
            setIsListening
          );
          return; // Exit to avoid duplicate resetWaitingStates call
        }
      }
      resetWaitingStates();
    } else {
      setStreamComplete(false);

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
        // JSON handler for final response
        async (json: StreamingResponse | null) => {
          setStreamComplete(true);

          // Create a function to process speech detected after streaming
          const processUserSpeech = async (transcript: string) => {
            if (transcript.trim()) {
              // Process the auto-detected speech as a new user message
              await processUserInput(
                transcript,
                useStreaming,
                {
                  addUserMessage,
                  updateOrAddBotMessage,
                  resetWaitingStates,
                  setWaitingForBot,
                  setStreamComplete
                },
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

          resetWaitingStates();
        }
      );
    }
  } catch (error) {
    console.error('Error processing message:', error);
    resetWaitingStates();
  }
};
