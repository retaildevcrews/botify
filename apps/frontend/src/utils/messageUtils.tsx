import { StreamingResponse } from '../types';

export const playSpeechResponse = async (response: any, speechService: any, useTextToSpeech: boolean) => {
  if (!useTextToSpeech) {
    console.log('Text to Speech is disabled, skipping audio playback');
    return;
  }

  try {
    const voiceSummary = speechService.extractVoiceSummaryFromResponse(response);
    if (voiceSummary) {
      await speechService.synthesizeSpeech(voiceSummary);
    } else if (response.inputMessage.content && typeof response.content === 'string') {
      await speechService.synthesizeSpeech(response.inputMessage.content);
    } else if (response.output?.displayResponse) {
      await speechService.synthesizeSpeech(response.output.displayResponse);
    }
  } catch (error) {
    console.error('Error playing voice response:', error);
  }
};

export const handleStreamingChunk = (
  chunk: string,
  updateOrAddBotMessage: (content: string) => void
) => {
  // Skip empty chunks
  if (!chunk || chunk.trim() === '') return;

  // Log the chunk for debugging
  console.log('Processing chunk:', chunk);

  try {
    // Update messages with chunk
    updateOrAddBotMessage(chunk);
  } catch (error) {
    console.error('Error handling streaming chunk:', error);
  }
};

export const handleStreamingComplete = async (
  json: StreamingResponse | null,
  speechService: any,
  speechEnabled: boolean = false,
  setIsListening?: (isListening: boolean) => void,
  processUserSpeech?: (transcript: string) => Promise<void>
) => {
  if (json !== null) {
    console.log('Streaming completed with JSON:', json);

    // Play voice summary if available
    try {
      const voiceSummary = speechService.extractVoiceSummaryFromResponse(json);
      if (voiceSummary) {
        await speechService.synthesizeSpeech(voiceSummary, speechEnabled);

        // Add auto-listening functionality for streaming mode
        if (speechEnabled) {
          console.log('Auto-starting microphone after streaming speech synthesis');
          // Calculate approximate speech duration (average reading speed: ~150 words per minute)
          // Add a minimum delay of 1 second plus roughly the time needed to speak the text
          const words = voiceSummary.trim().split(/\s+/).length;
          const estimatedDurationMs = Math.max(1000, words * 400); // 400ms per word = 150 words per minute
          console.log(`Estimated speech duration: ${estimatedDurationMs}ms for ${words} words`);

          // Wait for the estimated duration to ensure playback completes
          await new Promise(resolve => setTimeout(resolve, estimatedDurationMs));
          console.log('Speech playback should now be complete, activating microphone');

          setIsListening?.(true);

          // Start auto-listening and wait for result
          const autoDetectedSpeech = await speechService.autoStartListening(5000);

          setIsListening?.(false);

          // Process detected speech if any
          if (autoDetectedSpeech && autoDetectedSpeech.trim() && processUserSpeech) {
            console.log('Auto-detected speech input from streaming mode:', autoDetectedSpeech);
            await processUserSpeech(autoDetectedSpeech);
          }
        }
      }
    } catch (speechError) {
      console.error('Error playing voice response:', speechError);
      // Make sure to reset listening state in case of error
      if (setIsListening) {
        setIsListening(false);
      }
    }
  }
};
