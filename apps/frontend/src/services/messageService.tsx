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
  setIsListening?: (isListening: boolean) => void
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

        // First play the speech response without setting the listening state
        // This way the microphone doesn't show as listening while the AI is speaking
        await playSpeechResponse(response, speechService, useTextToSpeech);

        // After speech synthesis is complete, reset the waiting states
        resetWaitingStates();

        let autoDetectedSpeech: string | null = null;

        // Only start auto-listening if speech is enabled
        if (useTextToSpeech) {
          // Only after speech has finished, set the listening state to true
          if (setIsListening) {
            console.log('Setting microphone to listening state for auto-listening');
            setIsListening(true);
          }

          // Start auto-listening and wait for result
          autoDetectedSpeech = await speechService.autoStartListening(5000);

          // Reset listening state after auto-listening completes
          if (setIsListening) {
            console.log('Auto-listening complete, resetting microphone state');
            setIsListening(false);
          }

          // If speech was detected, process it
          if (autoDetectedSpeech && autoDetectedSpeech.trim()) {
            console.log('Auto-detected speech input:', autoDetectedSpeech);

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
          console.log('Auto-detected speech input:', autoDetectedSpeech);
          // Reset states before processing the new input to avoid UI confusion
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
            sessionId
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
              console.log('Processing auto-detected speech from streaming mode:', transcript);

              // Process the auto-detected speech as a new user message
              await processUserInput(
                transcript,
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
