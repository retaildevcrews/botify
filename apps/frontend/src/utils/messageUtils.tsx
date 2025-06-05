import { StreamingResponse } from '../types';

export const playSpeechResponse = async (
  response: any,
  speechService: any,
  useTextToSpeech: boolean,
  setIsListening: (isListening: boolean) => void,
) => {
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

    // Only start auto-listening AFTER speech synthesis is fully complete
    if (useTextToSpeech) {
      // Calculate approximate speech duration (average reading speed: ~150 words per minute)
      const words = voiceSummary.trim().split(/\s+/).length;
      const estimatedDurationMs = Math.max(1000, 300 + (words * 400)); // 400ms per word = 150 words per minute
      await new Promise(resolve => setTimeout(resolve, estimatedDurationMs));

      setIsListening(true);
      const autoDetectedSpeech = await speechService.autoStartListening(5000);
      setIsListening(false);

      return autoDetectedSpeech;
    }
  } catch (error) {
    console.error('Error playing voice response:', error);
  }

  return null;
};

export const handleStreamingChunk = (
  chunk: string,
  updateOrAddBotMessage: (content: string) => void
) => {
  // Skip empty chunks
  if (!chunk || chunk.trim() === '') return;

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
  useTextToSpeech: boolean = false,
  setIsListening: (isListening: boolean) => void,
  processUserSpeech?: (transcript: string) => Promise<void>
) => {
  if (json !== null) {
    // Play voice summary and handle auto-listening if enabled
    try {
      const autoDetectedSpeech = await playSpeechResponse(json, speechService, useTextToSpeech, setIsListening);

      // Process detected speech if any
      if (autoDetectedSpeech && autoDetectedSpeech.trim()) {
        await processUserSpeech?.(autoDetectedSpeech);
      }
    } catch (speechError) {
      console.error('Error playing voice response:', speechError);
      // Make sure to reset listening state in case of error
      setIsListening?.(false);
    }
  }
};
